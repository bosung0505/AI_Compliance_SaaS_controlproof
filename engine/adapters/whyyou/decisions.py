"""WhyYou company-user decision paths and synthetic-state isolation."""

from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, text

from engine.adapters.base import AdapterResult
from engine.config import Settings
from engine.evidence import redact
from engine.models import DecisionPathCapability, DecisionPathId

FINAL_DECISION_ROUTE = "/v1/invitations/{invitation_id}/final-decisions"
BATCH_MOVE_ROUTE = "/v1/positions/{position_id}/invitations/recruiting-stage"
EXPECTED_OPERATIONS = {
    FINAL_DECISION_ROUTE: ("post", "recordHumanFinalDecision"),
    BATCH_MOVE_ROUTE: ("patch", "moveApplicantsToRecruitingStage"),
}


class DecisionAdapterError(RuntimeError):
    """Sanitized decision adapter failure."""


class DecisionAccessError(DecisionAdapterError):
    pass


class DecisionContractError(DecisionAdapterError):
    pass


class WhyYouDecisionAdapter:
    def __init__(
        self,
        settings: Settings,
        client: Any,
        *,
        source_commit: str | None = None,
        transaction_factory: Callable[[], AbstractContextManager] | None = None,
    ) -> None:
        self.settings = settings
        self.client = client
        self._source_commit = source_commit
        self._engine = None
        self._transaction_factory = transaction_factory

    def probe_operations(self) -> AdapterResult:
        try:
            operations = self._operation_snapshot()
        except DecisionAccessError:
            return AdapterResult(False, "DECISION_OPERATIONS_ACCESS_BLOCKED")
        except DecisionContractError:
            return AdapterResult(False, "DECISION_OPERATIONS_INCOMPLETE")
        return AdapterResult(
            True,
            "DECISION_OPERATIONS_READY",
            {"operations": tuple(sorted(operations.values()))},
        )

    def capabilities(
        self, *, subject: Mapping[str, Any] | None = None
    ) -> tuple[DecisionPathCapability, ...]:
        operations = self._operation_snapshot()
        stages = self._stage_snapshot(subject)
        accept = stages.get("최종합격")
        reject = stages.get("불합격")
        if accept is None or reject is None:
            raise DecisionContractError("canonical final-stage snapshot is incomplete")
        commit = self._commit()
        return (
            DecisionPathCapability(
                path_id=DecisionPathId.FINAL_DECISION,
                operation_id=operations[FINAL_DECISION_ROUTE],
                target_stage_id=accept,
                target_stage_name="최종합격",
                source_commit=commit,
            ),
            DecisionPathCapability(
                path_id=DecisionPathId.BATCH_MOVE_FINAL_ACCEPT,
                operation_id=operations[BATCH_MOVE_ROUTE],
                target_stage_id=accept,
                target_stage_name="최종합격",
                source_commit=commit,
            ),
            DecisionPathCapability(
                path_id=DecisionPathId.BATCH_MOVE_FINAL_REJECT,
                operation_id=operations[BATCH_MOVE_ROUTE],
                target_stage_id=reject,
                target_stage_name="불합격",
                source_commit=commit,
            ),
        )

    def attempt(
        self,
        *,
        path_id: str | DecisionPathId,
        subject: Mapping[str, Any],
        idempotency_key: str | None = None,
    ) -> AdapterResult:
        active_path = DecisionPathId(path_id)
        if str(subject.get("company_user_id")) != str(self.settings.whyyou_company_user_id):
            return AdapterResult(False, "COMPANY_ACTOR_MISMATCH")
        key = idempotency_key or (
            f"controlproof-h03-{active_path.value}-{subject['invitation_id']}"
        )
        key_digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        try:
            capability = next(
                item
                for item in self.capabilities(subject=subject)
                if item.path_id is active_path
            )
            if active_path is DecisionPathId.FINAL_DECISION:
                response = self.client.http.post(
                    f"/v1/invitations/{subject['invitation_id']}/final-decisions",
                    headers={"Idempotency-Key": key},
                    json={
                        "recruiting_stage_id": str(capability.target_stage_id),
                        "expected_pipeline_version": int(subject["pipeline_row_version"]),
                    },
                )
                method = "POST"
                route = FINAL_DECISION_ROUTE
            else:
                response = self.client.http.patch(
                    f"/v1/positions/{subject['position_id']}/invitations/recruiting-stage",
                    headers={"Idempotency-Key": key},
                    json={
                        "target_stage_id": str(capability.target_stage_id),
                        "applicants": [
                            {
                                "invitation_id": str(subject["invitation_id"]),
                                "expected_version": int(subject["pipeline_row_version"]),
                            }
                        ],
                    },
                )
                method = "PATCH"
                route = BATCH_MOVE_ROUTE
        except DecisionAdapterError as exc:
            return AdapterResult(False, "DECISION_PATH_NOT_READY", detail=type(exc).__name__)
        except Exception as exc:  # noqa: BLE001 - normalize network/provider failures
            return AdapterResult(False, "DECISION_ACCESS_FAILED", detail=type(exc).__name__)
        body = _json_body(response)
        if response.status_code in {401, 403}:
            return AdapterResult(False, "DECISION_ACCESS_DENIED")
        accepted = 200 <= response.status_code < 300
        reason_present, reason_code = _explicit_report_refusal(body)
        return AdapterResult(
            True,
            "DECISION_ATTEMPTED",
            {
                "path_id": active_path,
                "operation_id": capability.operation_id,
                "target_stage_id": capability.target_stage_id,
                "target_stage_name": capability.target_stage_name,
                "accepted": accepted,
                "http_status": response.status_code,
                "reason_present": reason_present,
                "reason_code": reason_code,
                "idempotency_key_digest": key_digest,
                "exchange": redact(
                    {
                        "request": {"method": method, "route_template": route},
                        "response": {"status": response.status_code, "body": body},
                    }
                ),
            },
        )

    def capture_reset_token(self, *, subject: Mapping[str, Any]) -> AdapterResult:
        try:
            with self._transaction() as connection:
                invitation = connection.execute(
                    text(
                        "SELECT status, recruiting_stage_id, pipeline_row_version "
                        "FROM invitations WHERE company_id=:company_id "
                        "AND invitation_id=:invitation_id"
                    ),
                    _scope(subject),
                ).mappings().one()
                review_ids = tuple(
                    str(value)
                    for value in connection.execute(
                        text(
                            "SELECT human_review_id FROM human_reviews "
                            "WHERE company_id=:company_id AND target_id=:invitation_id"
                        ),
                        _scope(subject),
                    ).scalars()
                )
                audit_ids = tuple(
                    str(value)
                    for value in connection.execute(
                        text(
                            "SELECT audit_event_id FROM audit_events WHERE company_id=:company_id "
                            "AND action IN ('final_decision.create','applicant_pipeline.moved') "
                            "AND (resource_id=:position_id OR resource_id IN "
                            "(SELECT human_review_id FROM human_reviews WHERE company_id=:company_id "
                            "AND target_id=:invitation_id))"
                        ),
                        _scope(subject),
                    ).scalars()
                )
        except Exception as exc:  # noqa: BLE001 - normalize DB failures
            return AdapterResult(False, "DECISION_RESET_SNAPSHOT_FAILED", detail=type(exc).__name__)
        return AdapterResult(
            True,
            "DECISION_RESET_SNAPSHOT_CAPTURED",
            {
                "invitation_status": str(invitation["status"]),
                "recruiting_stage_id": str(invitation["recruiting_stage_id"]),
                "pipeline_row_version": int(invitation["pipeline_row_version"]),
                "human_review_ids": review_ids,
                "audit_event_ids": audit_ids,
            },
        )

    def reset(
        self,
        *,
        subject: Mapping[str, Any],
        token: Mapping[str, Any],
    ) -> AdapterResult:
        try:
            with self._transaction() as connection:
                current_reviews = set(
                    connection.execute(
                        text(
                            "SELECT human_review_id FROM human_reviews "
                            "WHERE company_id=:company_id AND target_id=:invitation_id"
                        ),
                        _scope(subject),
                    ).scalars()
                )
                current_audits = set(
                    connection.execute(
                        text(
                            "SELECT audit_event_id FROM audit_events WHERE company_id=:company_id "
                            "AND action IN ('final_decision.create','applicant_pipeline.moved') "
                            "AND (resource_id=:position_id OR resource_id IN "
                            "(SELECT human_review_id FROM human_reviews WHERE company_id=:company_id "
                            "AND target_id=:invitation_id))"
                        ),
                        _scope(subject),
                    ).scalars()
                )
                new_audits = current_audits - {
                    UUID(value) for value in token.get("audit_event_ids", ())
                }
                new_reviews = current_reviews - {
                    UUID(value) for value in token.get("human_review_ids", ())
                }
                for audit_id in new_audits:
                    connection.execute(
                        text(
                            "DELETE FROM audit_events WHERE company_id=:company_id "
                            "AND audit_event_id=:audit_event_id"
                        ),
                        {**_scope(subject), "audit_event_id": audit_id},
                    )
                for review_id in new_reviews:
                    connection.execute(
                        text(
                            "DELETE FROM human_reviews WHERE company_id=:company_id "
                            "AND human_review_id=:human_review_id"
                        ),
                        {**_scope(subject), "human_review_id": review_id},
                    )
                connection.execute(
                    text(
                        "UPDATE invitations SET status=:status, "
                        "recruiting_stage_id=:recruiting_stage_id, "
                        "pipeline_row_version=:pipeline_row_version "
                        "WHERE company_id=:company_id AND invitation_id=:invitation_id"
                    ),
                    {
                        **_scope(subject),
                        "status": token["invitation_status"],
                        "recruiting_stage_id": UUID(str(token["recruiting_stage_id"])),
                        "pipeline_row_version": int(token["pipeline_row_version"]),
                    },
                )
        except Exception as exc:  # noqa: BLE001 - reset uncertainty must stay explicit
            return AdapterResult(False, "DECISION_STATE_RESET_FAILED", detail=type(exc).__name__)
        return AdapterResult(True, "DECISION_STATE_RESET")

    def _operation_snapshot(self) -> dict[str, str]:
        try:
            response = self.client.http.get("/openapi.json")
            if response.status_code in {401, 403}:
                raise DecisionAccessError("OpenAPI access denied")
            response.raise_for_status()
            paths = response.json().get("paths", {})
        except DecisionAdapterError:
            raise
        except Exception as exc:
            raise DecisionAccessError("OpenAPI decision operations are unavailable") from exc
        result: dict[str, str] = {}
        for route, (method, expected_operation) in EXPECTED_OPERATIONS.items():
            operation = paths.get(route, {}).get(method, {}).get("operationId")
            if operation != expected_operation:
                raise DecisionContractError("canonical decision operation is missing")
            result[route] = str(operation)
        return result

    def _stage_snapshot(self, subject: Mapping[str, Any] | None) -> dict[str, UUID]:
        params = {"position_id": str(subject["position_id"])} if subject else {}
        try:
            response = self.client.http.get("/v1/recruiting-stages", params=params)
            if response.status_code in {401, 403}:
                raise DecisionAccessError("recruiting-stage access denied")
            response.raise_for_status()
            items = response.json().get("items", ())
        except DecisionAdapterError:
            raise
        except Exception as exc:
            raise DecisionAccessError("recruiting-stage snapshot is unavailable") from exc
        result: dict[str, UUID] = {}
        for item in items if isinstance(items, list) else ():
            if not isinstance(item, Mapping):
                continue
            name = "".join(str(item.get("name", "")).split())
            if name not in {"최종합격", "불합격"}:
                continue
            if subject and str(item.get("position_id")) != str(subject["position_id"]):
                continue
            if name in result:
                raise DecisionContractError("canonical final stage is ambiguous")
            try:
                result[name] = UUID(str(item["recruiting_stage_id"]))
            except (KeyError, ValueError) as exc:
                raise DecisionContractError("canonical final stage is malformed") from exc
        return result

    def _commit(self) -> str:
        if self._source_commit is not None:
            return self._source_commit
        try:
            return subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.settings.whyyou_repo_path,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            ).stdout.strip().casefold()
        except Exception as exc:
            raise DecisionAccessError("WhyYou source commit is unavailable") from exc

    def _transaction(self):
        if self._transaction_factory is None:
            if self._engine is None:
                self._engine = create_engine(self.settings.whyyou_database_url)
            self._transaction_factory = self._engine.begin
        return self._transaction_factory()


def _scope(subject: Mapping[str, Any]) -> dict[str, UUID]:
    return {
        "company_id": UUID(str(subject["company_id"])),
        "position_id": UUID(str(subject["position_id"])),
        "invitation_id": UUID(str(subject["invitation_id"])),
    }


def _json_body(response: Any) -> dict[str, Any]:
    try:
        value = response.json()
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {"value": value}


def _explicit_report_refusal(body: Mapping[str, Any]) -> tuple[bool, str | None]:
    code = body.get("code") or body.get("error_code")
    detail = str(body.get("detail", "")).casefold()
    explicit = code in {"REPORT_NOT_AVAILABLE", "REPORT_REQUIRED"} or (
        "report" in detail
        and any(word in detail for word in ("not available", "not ready", "required"))
    )
    return explicit, "REPORT_NOT_AVAILABLE" if explicit else None
