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
from engine.models import canonical_json_bytes


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
            "fault_type": "reporting_handler_timeout_v1",
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

    def restore(self, *, run_id: str, subject: dict[str, Any]) -> AdapterResult:
        marker = self.marker_path(str(subject["interview_session_id"]))
        marker.unlink(missing_ok=True)
        marker_inactive = not marker.exists()
        try:
            response = self.client.http.get("/health")
            worker_healthy = response.status_code == 200
        except Exception:  # noqa: BLE001 - health uncertainty must fail closed
            worker_healthy = False
        report = self.client.report_status(str(subject["interview_session_id"]))
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
            healthy = self.client.http.get("/health").status_code == 200
        except Exception:  # noqa: BLE001 - health uncertainty must fail closed
            healthy = False
        return not active and healthy
