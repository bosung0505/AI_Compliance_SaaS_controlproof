"""Run/session-scoped WhyYou reporting fault marker and receipt adapter."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from engine.adapters.base import AdapterResult
from engine.adapters.whyyou.client import WhyYouClient
from engine.config import Settings
from engine.lifecycle import atomic_write
from engine.models import FaultBoundaryReceipt, FaultVariant, canonical_json_bytes


class WhyYouFaultAdapter:
    def __init__(self, settings: Settings, client: WhyYouClient) -> None:
        self.settings = settings
        self.client = client

    def marker_path(self, session_id: str) -> Path:
        UUID(session_id)
        return self.settings.fault_root / "reporting" / f"{session_id}.json"

    def receipt_path(self, run_id: str) -> Path:
        UUID(run_id)
        return self.settings.fault_root / "receipts" / f"{run_id}.jsonl"

    def apply(
        self,
        *,
        run_id: str,
        subject: dict[str, Any],
        expires_at: datetime,
    ) -> AdapterResult:
        return self._apply_marker(
            run_id=run_id,
            subject=subject,
            expires_at=expires_at,
            fault_type="reporting_handler_timeout_v1",
            fault_variant=FaultVariant.BEFORE_RESULT_DURABLE,
            one_shot=False,
        )

    def apply_after(
        self,
        *,
        run_id: str,
        subject: dict[str, Any],
        expires_at: datetime,
    ) -> AdapterResult:
        return self._apply_marker(
            run_id=run_id,
            subject=subject,
            expires_at=expires_at,
            fault_type="reporting_after_commit_drop_ack_v1",
            fault_variant=FaultVariant.AFTER_RESULT_DURABLE_BEFORE_COMPLETION,
            one_shot=True,
        )

    def _apply_marker(
        self,
        *,
        run_id: str,
        subject: dict[str, Any],
        expires_at: datetime,
        fault_type: str,
        fault_variant: FaultVariant,
        one_shot: bool,
    ) -> AdapterResult:
        UUID(run_id)
        session_id = str(subject["interview_session_id"])
        if expires_at.tzinfo is None:
            return AdapterResult(
                False, "INVALID_EXPIRY", detail="expires_at must include UTC offset"
            )
        now = datetime.now(UTC)
        ttl = (expires_at - now).total_seconds()
        if ttl <= 0 or ttl > 600:
            return AdapterResult(
                False, "INVALID_TTL", detail="fault marker TTL must be 1..600 seconds"
            )
        marker = {
            "schema_version": "controlproof.whyyou-fault.v1",
            "run_id": run_id,
            "interview_session_id": session_id,
            "fault_type": fault_type,
            "fault_variant": fault_variant.value,
            "one_shot": one_shot,
            "issued_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
        }
        path = self.marker_path(session_id)
        atomic_write(path, canonical_json_bytes(marker))
        return AdapterResult(
            True,
            "FAULT_MARKER_APPLIED",
            {
                "marker": marker,
                "relative_path": path.relative_to(self.settings.fault_root).as_posix(),
            },
        )

    def probe_effect(
        self,
        *,
        run_id: str,
        subject: dict[str, Any],
        trigger: dict[str, Any],
    ) -> AdapterResult:
        session_id = str(subject["interview_session_id"])
        event_id = str(trigger["outbox_event_id"])
        path = self.receipt_path(run_id)
        if not path.exists():
            return AdapterResult(False, "TRIGGER_RECEIPT_MISSING")
        malformed = 0
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            try:
                receipt = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if (
                receipt.get("run_id") == run_id
                and receipt.get("session_id") == session_id
                and receipt.get("outbox_event_id") == event_id
                and receipt.get("fault_type") == "reporting_handler_timeout_v1"
                and receipt.get("schema_version")
                == "controlproof.whyyou-fault-receipt.v2"
                and receipt.get("fault_variant")
                == FaultVariant.BEFORE_RESULT_DURABLE.value
                and receipt.get("boundary") == "BEFORE_REPORT_SIDE_EFFECT"
            ):
                return AdapterResult(
                    True,
                    "FAULT_EFFECT_CONFIRMED",
                    {
                        "receipt": receipt,
                        "line_number": line_number,
                        "relative_path": path.relative_to(self.settings.fault_root).as_posix(),
                    },
                )
        return AdapterResult(
            False,
            "TRIGGER_RECEIPT_NOT_MATCHED",
            {"malformed_records": malformed},
        )

    def read_boundary_receipt(
        self,
        *,
        run_id: str,
        source_event_id: str,
        fault_variant: str,
        session_id: str | None = None,
        expected_attempt: int | None = None,
    ) -> FaultBoundaryReceipt | AdapterResult:
        try:
            expected_run = UUID(run_id)
            expected_event = UUID(source_event_id)
            expected_variant = FaultVariant(fault_variant)
            expected_session = UUID(session_id) if session_id is not None else None
            if expected_attempt is not None and expected_attempt < 1:
                raise ValueError
        except ValueError:
            return AdapterResult(False, "INVALID_BOUNDARY_IDENTITY")
        path = self.receipt_path(str(expected_run))
        if not path.exists():
            return AdapterResult(False, "BOUNDARY_RECEIPT_MISSING")
        after_matches: list[FaultBoundaryReceipt] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                payload = json.loads(line)
                if (
                    UUID(str(payload["run_id"])) == expected_run
                    and UUID(str(payload["outbox_event_id"])) == expected_event
                    and payload.get("fault_variant") == expected_variant.value
                    and (
                        expected_session is None
                        or UUID(str(payload["session_id"])) == expected_session
                    )
                    and (
                        expected_attempt is None
                        or int(payload["delivery_attempt"]) == expected_attempt
                    )
                ):
                    receipt = FaultBoundaryReceipt.model_validate(
                        {
                            key: payload[key]
                            for key in (
                                "schema_version",
                                "run_id",
                                "session_id",
                                "outbox_event_id",
                                "delivery_attempt",
                                "fault_variant",
                                "boundary",
                                "triggered_at",
                                "one_shot_consumed",
                            )
                        }
                    )
                    if (
                        expected_variant
                        is FaultVariant.AFTER_RESULT_DURABLE_BEFORE_COMPLETION
                    ):
                        after_matches.append(receipt)
                        continue
                    return receipt
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
        if len(after_matches) == 1:
            return after_matches[0]
        if len(after_matches) > 1:
            return AdapterResult(
                False,
                "AFTER_BOUNDARY_REPEATED",
                {"matching_receipts": len(after_matches)},
            )
        return AdapterResult(False, "BOUNDARY_RECEIPT_NOT_MATCHED")

    def read_duplicate_ack(
        self,
        *,
        run_id: str,
        source_event_id: str,
    ) -> AdapterResult:
        try:
            expected_run = UUID(run_id)
            expected_event = UUID(source_event_id)
        except ValueError:
            return AdapterResult(False, "INVALID_DUPLICATE_ACK_IDENTITY")
        path = self.receipt_path(str(expected_run))
        if not path.exists():
            return AdapterResult(False, "DUPLICATE_ACK_MISSING")
        malformed = 0
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            try:
                payload = json.loads(line)
                if (
                    payload.get("schema_version") == "controlproof.whyyou-duplicate-ack.v1"
                    and UUID(str(payload["run_id"])) == expected_run
                    and UUID(str(payload["outbox_event_id"])) == expected_event
                    and payload.get("consumer_name") == "reporting-worker"
                    and payload.get("handler_skipped") is True
                    and payload.get("acknowledged") is True
                    and int(payload["delivery_attempt"]) >= 2
                ):
                    return AdapterResult(
                        True,
                        "DUPLICATE_ACK_READ",
                        {
                            "receipt": payload,
                            "line_number": line_number,
                            "relative_path": path.relative_to(
                                self.settings.fault_root
                            ).as_posix(),
                        },
                    )
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                malformed += 1
        return AdapterResult(
            False,
            "DUPLICATE_ACK_NOT_MATCHED",
            {"malformed_records": malformed},
        )

    def probe_marker_removed(self, *, subject: dict[str, Any]) -> AdapterResult:
        marker = self.marker_path(str(subject["interview_session_id"]))
        inactive = not marker.exists()
        return AdapterResult(
            inactive,
            "FAULT_MARKER_INACTIVE" if inactive else "FAULT_MARKER_STILL_ACTIVE",
            {"marker_inactive": inactive},
        )

    def restore(self, *, run_id: str, subject: dict[str, Any]) -> AdapterResult:
        marker = self.marker_path(str(subject["interview_session_id"]))
        marker.unlink(missing_ok=True)
        consumed = (
            self.settings.fault_root
            / "consumed"
            / f"{run_id}-{subject['interview_session_id']}.after"
        )
        consumed.unlink(missing_ok=True)
        marker_inactive = not marker.exists()
        try:
            response = self.client.http.get("/health/live")
            worker_healthy = response.status_code == 200
        except Exception:  # noqa: BLE001 - health uncertainty must fail closed
            worker_healthy = False
        try:
            report = self.client.report_status(str(subject["interview_session_id"]))
        except Exception:  # noqa: BLE001 - reporting recovery is independent of marker removal
            report = {"presence": "UNAVAILABLE"}
        if report.get("presence") == "PRESENT":
            recovery = str(report.get("status", "READY")).upper()
            if recovery not in {"READY", "PARTIAL", "FAILED"}:
                recovery = "READY"
        elif report.get("presence") == "UNAVAILABLE":
            recovery = "UNAVAILABLE"
        else:
            recovery = "TIMEOUT"
        ok = marker_inactive and worker_healthy
        return AdapterResult(
            ok,
            "ENVIRONMENT_RESTORED" if ok else "ENVIRONMENT_RESTORE_FAILED",
            {
                "run_id": run_id,
                "marker_inactive": marker_inactive,
                "worker_healthy": worker_healthy,
                "environment_restore": "SUCCEEDED" if ok else "FAILED",
                "report_processing_recovery": recovery,
            },
        )

    def target_safe(self, *, subject_ref: str) -> bool:
        reporting = self.settings.fault_root / "reporting"
        active = list(reporting.glob("*.json")) if reporting.exists() else []
        try:
            healthy = self.client.http.get("/health/live").status_code == 200
        except Exception:  # noqa: BLE001 - health uncertainty must fail closed
            healthy = False
        return not active and healthy
