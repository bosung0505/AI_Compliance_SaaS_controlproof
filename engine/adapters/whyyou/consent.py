"""Sanitized WhyYou consent policy, commit and durable-state projection for N-02."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from typing import Any
from uuid import UUID, uuid5

import httpx
from sqlalchemy import create_engine, text

from engine.adapters.base import AdapterResult
from engine.adapters.whyyou.n02_seed import N02CredentialStore
from engine.config import Settings
from engine.models import (
    ConsentPolicySnapshot,
    ConsentPurpose,
    ConsentStateSnapshot,
    N02LaneId,
    Phase,
    Presence,
    canonical_json_bytes,
    sha256_bytes,
    utcnow,
)

_CONSENT_NAMESPACE = UUID("891f416c-f6ef-59bb-b92e-e63334418760")

_TARGET_REJECTION_REASONS = {
    "all required consent purposes must be accepted": "REQUIRED_PURPOSES_MISSING",
    "consent policy version or digest is stale": "CONSENT_POLICY_STALE",
    "stale invitation version": "INVITATION_VERSION_STALE",
}


def _target_rejection_reason(response: httpx.Response) -> str:
    """Return only known, non-sensitive WhyYou reasons; never retain response text."""
    try:
        body = response.json()
    except (ValueError, UnicodeError):
        return "UNRECOGNIZED_REJECTION"
    detail = body.get("detail") if isinstance(body, dict) else None
    if not isinstance(detail, str):
        return "UNRECOGNIZED_REJECTION"
    if detail.startswith("cannot transition invitation from "):
        return "INVITATION_TRANSITION_REJECTED"
    return _TARGET_REJECTION_REASONS.get(detail, "UNRECOGNIZED_REJECTION")


class WhyYouConsentAdapter:
    """Collect only the identifiers needed to prove the consent transaction."""

    def __init__(
        self,
        settings: Settings,
        *,
        http_client: httpx.Client | None = None,
        credentials: N02CredentialStore | None = None,
        state_reader: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        transaction_factory: Callable[[], AbstractContextManager] | None = None,
    ) -> None:
        self.settings = settings
        self.credentials = credentials or N02CredentialStore()
        self.http = http_client or httpx.Client(
            base_url=settings.whyyou_base_url,
            timeout=10,
            trust_env=False,
        )
        self._engine = None
        if state_reader is None:
            if transaction_factory is None:
                self._engine = create_engine(settings.whyyou_database_url)
                transaction_factory = self._engine.begin
            self._transaction_factory = transaction_factory
            self._state_reader = self._read_state_projection
        else:
            self._transaction_factory = transaction_factory
            self._state_reader = state_reader

    def read_policy(
        self, *, subject: Mapping[str, Any]
    ) -> ConsentPolicySnapshot | AdapterResult:
        credential = self.credentials.get(str(subject["subject_ref"]))
        if credential is None:
            return AdapterResult(False, "N02_APPLICANT_CREDENTIAL_MISSING")
        request_id = uuid5(
            _CONSENT_NAMESPACE,
            f"{UUID(str(subject['run_id']))}:{subject['lane_id']}:policy",
        )
        try:
            response = self.http.get(
                "/v1/applicant/consents",
                headers={
                    "X-Request-Id": str(request_id),
                    "Cookie": f"iep_applicant_session={credential}",
                },
            )
            response.raise_for_status()
            body = response.json()
            return ConsentPolicySnapshot(
                policy_version=str(body["policy_version"]),
                content_digest=str(body["content_digest"]),
                required_purposes=tuple(
                    ConsentPurpose(value) for value in body["required_purposes"]
                ),
                retention_days=int(body["retention_days"]),
                received_at=utcnow(),
                request_id=request_id,
                source_ref="whyyou:getApplicantConsentPolicy:v1",
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            return AdapterResult(
                False,
                "CONSENT_POLICY_UNAVAILABLE",
                detail=type(exc).__name__,
            )

    def commit(
        self,
        *,
        subject: Mapping[str, Any],
        policy: ConsentPolicySnapshot,
        request_id: str,
        trace_id: str,
    ) -> AdapterResult:
        credential = self.credentials.get(str(subject["subject_ref"]))
        if credential is None:
            return AdapterResult(False, "N02_APPLICANT_CREDENTIAL_MISSING")
        payload = {
            "policy_version": policy.policy_version,
            "accepted_purposes": [purpose.value for purpose in policy.required_purposes],
            "consent_content_digest": policy.content_digest,
        }
        try:
            response = self.http.post(
                "/v1/applicant/consents",
                json=payload,
                headers={
                    "Idempotency-Key": request_id,
                    "X-Trace-Id": trace_id,
                    "Cookie": f"iep_applicant_session={credential}",
                },
            )
        except httpx.TimeoutException as exc:
            return AdapterResult(
                False,
                "CONSENT_COMMIT_RESPONSE_UNKNOWN",
                {"durable_state": "UNKNOWN", "request_id": request_id},
                detail=type(exc).__name__,
            )
        except httpx.HTTPError as exc:
            return AdapterResult(
                False,
                "CONSENT_COMMIT_TRANSPORT_UNAVAILABLE",
                {"durable_state": "UNKNOWN", "request_id": request_id},
                detail=type(exc).__name__,
            )
        if not 200 <= response.status_code < 300:
            target_reason_code = _target_rejection_reason(response)
            code = (
                "CONSENT_POLICY_MISMATCH"
                if target_reason_code in {"CONSENT_POLICY_STALE", "REQUIRED_PURPOSES_MISSING"}
                else "CONSENT_COMMIT_REJECTED"
            )
            return AdapterResult(
                False,
                code,
                {
                    "status_code": response.status_code,
                    "durable_state": "NOT_COMMITTED",
                    "request_id": request_id,
                    "target_reason_code": target_reason_code,
                },
            )
        try:
            body = response.json()
            sanitized = {
                "consent_record_id": str(UUID(str(body["consent_record_id"]))),
                "policy_version": str(body["policy_version"]),
                "accepted_purposes": tuple(
                    sorted(ConsentPurpose(value).value for value in body["accepted_purposes"])
                ),
                "retention_days": int(body["retention_days"]),
                "request_id": request_id,
                "trace_id_digest": hashlib.sha256(trace_id.encode()).hexdigest(),
            }
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            return AdapterResult(
                False,
                "CONSENT_COMMIT_RESPONSE_INVALID",
                {"durable_state": "UNKNOWN", "request_id": request_id},
                detail=type(exc).__name__,
            )
        return AdapterResult(True, "CONSENT_COMMIT_RESPONSE_RECEIVED", sanitized)

    def read_state(
        self, *, subject: Mapping[str, Any], phase: str, step_id: str
    ) -> ConsentStateSnapshot | AdapterResult:
        try:
            projection = dict(self._state_reader(subject))
        except Exception as exc:  # noqa: BLE001 - unavailability is an evidence fact
            projection = {
                "source_status": Presence.UNAVAILABLE.value,
                "error_code": type(exc).__name__.upper(),
            }
        status = Presence(str(projection.get("source_status", Presence.PRESENT.value)))
        base = {
            "run_id": UUID(str(subject["run_id"])),
            "lane_id": N02LaneId(str(subject["lane_id"])),
            "subject_ref": str(subject["subject_ref"]),
            "phase": Phase(phase),
            "step_id": step_id,
            "attempt": 1,
            "invitation_status": str(projection.get("invitation_status", "unknown")),
            "invitation_row_version": int(projection.get("invitation_row_version", 0)),
            "captured_at": utcnow(),
        }
        if status is Presence.UNAVAILABLE:
            return ConsentStateSnapshot(
                **base,
                source_status=status,
                source_error_code=str(projection.get("error_code", "SOURCE_UNAVAILABLE")),
                state_digest=sha256_bytes(b"unavailable"),
            )
        records = tuple(UUID(str(value)) for value in projection.get("consent_record_ids", ()))
        transitions = tuple(
            UUID(str(value)) for value in projection.get("consented_state_change_ids", ())
        )
        events = tuple(
            UUID(str(value)) for value in projection.get("consent_completed_event_ids", ())
        )
        versions = tuple(str(value) for value in projection.get("consent_policy_versions", ()))
        digests = tuple(str(value) for value in projection.get("consent_content_digests", ()))
        purposes = tuple(
            tuple(ConsentPurpose(value) for value in purpose_set)
            for purpose_set in projection.get("accepted_purpose_sets", ())
        )
        trace_digests = tuple(
            value_text
            if len(value_text) == 64 and all(char in "0123456789abcdef" for char in value_text)
            else hashlib.sha256(value_text.encode()).hexdigest()
            for value in projection.get("trace_ids", ())
            for value_text in (str(value),)
        )
        identity = {
            "invitation_status": base["invitation_status"],
            "invitation_row_version": base["invitation_row_version"],
            "records": [str(value) for value in records],
            "transitions": [str(value) for value in transitions],
            "events": [str(value) for value in events],
            "versions": versions,
            "digests": digests,
            "purposes": [[item.value for item in values] for values in purposes],
            "traces": trace_digests,
        }
        present = bool(records or transitions or events)
        return ConsentStateSnapshot(
            **base,
            consent_record_ids=records,
            active_consent_count=int(projection.get("active_consent_count", len(records))),
            consent_policy_versions=versions,
            consent_content_digests=digests,
            accepted_purpose_sets=purposes,
            consented_state_change_ids=transitions,
            consent_completed_event_ids=events,
            trace_ids=trace_digests,
            source_status=Presence.PRESENT if present else Presence.ABSENT,
            state_digest=sha256_bytes(canonical_json_bytes(identity)),
        )

    def _read_state_projection(self, subject: Mapping[str, Any]) -> Mapping[str, Any]:
        if self._transaction_factory is None:
            raise RuntimeError("consent state transaction factory is unavailable")
        params = {
            "company_id": UUID(self.settings.whyyou_company_id),
            "invitation_id": UUID(str(subject["invitation_id"])),
        }
        with self._transaction_factory() as connection:
            invitation = connection.execute(
                text(
                    "SELECT status, row_version FROM invitations "
                    "WHERE company_id=:company_id AND invitation_id=:invitation_id"
                ),
                params,
            ).mappings().first()
            consent_rows = tuple(
                connection.execute(
                    text(
                        "SELECT consent_record_id, policy_version, purposes, evidence_digest, "
                        "withdrawn_at FROM consent_records WHERE company_id=:company_id "
                        "AND invitation_id=:invitation_id ORDER BY accepted_at"
                    ),
                    params,
                ).mappings()
            )
            transitions = tuple(
                connection.execute(
                    text(
                        "SELECT invitation_state_change_id FROM invitation_state_history "
                        "WHERE company_id=:company_id AND invitation_id=:invitation_id "
                        "AND to_status='consented' ORDER BY occurred_at"
                    ),
                    params,
                ).scalars()
            )
            outbox_rows = tuple(
                connection.execute(
                    text(
                        "SELECT outbox_event_id, trace_id FROM outbox_events "
                        "WHERE company_id=:company_id AND aggregate_id=:invitation_id "
                        "AND event_type='invitation.consent_completed' ORDER BY occurred_at"
                    ),
                    params,
                ).mappings()
            )
        active = tuple(row for row in consent_rows if row["withdrawn_at"] is None)
        return {
            "source_status": Presence.PRESENT.value,
            "invitation_status": invitation["status"] if invitation else "missing",
            "invitation_row_version": invitation["row_version"] if invitation else 0,
            "consent_record_ids": [row["consent_record_id"] for row in active],
            "active_consent_count": len(active),
            "consent_policy_versions": [row["policy_version"] for row in active],
            "consent_content_digests": [row["evidence_digest"] for row in active],
            "accepted_purpose_sets": [row["purposes"] for row in active],
            "consented_state_change_ids": transitions,
            "consent_completed_event_ids": [row["outbox_event_id"] for row in outbox_rows],
            "trace_ids": [row["trace_id"] for row in outbox_rows],
        }
