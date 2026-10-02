"""Bounded local/test consent fault marker, receipt and restore adapter."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from engine.adapters.base import AdapterResult
from engine.lifecycle import atomic_write
from engine.models import (
    ConsentFaultBoundary,
    ConsentFaultReceipt,
    ConsentFaultVariant,
    N02LaneId,
    Phase,
    Presence,
    ProtectedPathId,
    canonical_json_bytes,
    sha256_bytes,
    utcnow,
)

_SCHEMA = "controlproof.whyyou-consent-fault.v1"
_RECEIPT_SCHEMA = "controlproof.whyyou-consent-fault-receipt.v1"
_FAULT_TYPE = "consent_after_record_before_state_v1"


class WhyYouConsentFaultAdapter:
    def __init__(
        self,
        settings,
        *,
        consent_adapter=None,
        processing_adapter=None,
        cleanup_counts_reader: Callable[[Mapping[str, Any]], Mapping[str, int]] | None = None,
    ) -> None:
        self.settings = settings
        self.root = Path(settings.fault_root).resolve()
        self.consent_adapter = consent_adapter
        self.processing_adapter = processing_adapter
        self.cleanup_counts_reader = cleanup_counts_reader or self._read_cleanup_counts

    def _read_cleanup_counts(self, subject: Mapping[str, Any]) -> Mapping[str, int]:
        engine = create_engine(self.settings.whyyou_database_url)
        params = {
            "company_id": UUID(self.settings.whyyou_company_id),
            "invitation_id": UUID(str(subject["invitation_id"])),
        }
        try:
            with engine.connect() as connection:
                return {
                    "consent_records": connection.execute(
                        text(
                            "SELECT COUNT(*) FROM consent_records "
                            "WHERE company_id=:company_id AND invitation_id=:invitation_id"
                        ),
                        params,
                    ).scalar_one(),
                    "invitation_events": connection.execute(
                        text(
                            "SELECT COUNT(*) FROM outbox_events "
                            "WHERE company_id=:company_id AND aggregate_id=:invitation_id"
                        ),
                        params,
                    ).scalar_one(),
                }
        finally:
            engine.dispose()

    def target_safe(self, *, subject: Mapping[str, Any]) -> bool:
        """Read the current N-02 fault lane without changing its parent Run."""
        try:
            if N02LaneId(str(subject["lane_id"])) is not N02LaneId.CONSENT_FAULT_RECOVERY:
                return False
            run_id = UUID(str(subject["run_id"]))
            invitation_id = UUID(str(subject["invitation_id"]))
            UUID(str(subject["applicant_id"]))
            marker = self._marker_path(invitation_id)
            consumed = self._consumed_path(run_id, invitation_id)
            self._assert_bounded(marker)
            self._assert_bounded(consumed)
            if marker.exists() or consumed.exists():
                return False
            if self.consent_adapter is None or self.processing_adapter is None:
                return False
            counts = self.cleanup_counts_reader(subject)
            if (
                type(counts.get("consent_records")) is not int
                or counts["consent_records"] != 0
                or type(counts.get("invitation_events")) is not int
                or counts["invitation_events"] != 0
            ):
                return False
            state = self.consent_adapter.read_state(
                subject=subject,
                phase=Phase.RECOVERED.value,
                step_id="cleanup-confirm-safe-state",
            )
            if isinstance(state, AdapterResult) or not (
                state.source_status is Presence.ABSENT
                and state.invitation_status == "identity_verified"
                and state.active_consent_count == 0
                and not state.consent_record_ids
                and not state.consented_state_change_ids
                and not state.consent_completed_event_ids
            ):
                return False
            effects = self.processing_adapter.read_effects(
                path_id=ProtectedPathId.DOCUMENT_ANALYSIS.value,
                subject={**subject, "interview_session_id": str(UUID(int=0))},
                phase=Phase.RECOVERED.value,
                step_id="cleanup-confirm-document-effects",
            )
            return (
                not isinstance(effects, AdapterResult)
                and effects.source_status is Presence.ABSENT
                and not effects.current_effect_ids
            )
        except (OSError, KeyError, TypeError, ValueError, SQLAlchemyError):
            return False

    def apply_consent_fault(
        self,
        *,
        run_id: str,
        subject: Mapping[str, Any],
        expires_at: datetime,
    ) -> AdapterResult:
        try:
            active_run = UUID(run_id)
            if active_run != UUID(str(subject["run_id"])):
                return AdapterResult(False, "CONSENT_FAULT_RUN_MISMATCH")
            lane = N02LaneId(str(subject["lane_id"]))
            if lane is not N02LaneId.CONSENT_FAULT_RECOVERY:
                return AdapterResult(False, "CONSENT_FAULT_LANE_MISMATCH")
            invitation_id = UUID(str(subject["invitation_id"]))
            applicant_id = UUID(str(subject["applicant_id"]))
        except (KeyError, TypeError, ValueError):
            return AdapterResult(False, "CONSENT_FAULT_SUBJECT_INVALID")
        if not self.settings.test_hooks_enabled:
            return AdapterResult(False, "CONSENT_FAULT_HOOK_DISABLED")
        issued_at = utcnow()
        ttl = (expires_at - issued_at).total_seconds()
        if expires_at.tzinfo is None or not 0 < ttl <= 600:
            return AdapterResult(False, "CONSENT_FAULT_TTL_INVALID")
        payload = {
            "schema_version": _SCHEMA,
            "run_id": str(active_run),
            "lane_id": lane.value,
            "subject_ref": str(subject["subject_ref"]),
            "invitation_id": str(invitation_id),
            "applicant_id": str(applicant_id),
            "fault_type": _FAULT_TYPE,
            "fault_variant": ConsentFaultVariant.AFTER_CONSENT_RECORD_BEFORE_STATE.value,
            "issued_at": issued_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "one_shot": True,
        }
        path = self._marker_path(invitation_id)
        try:
            atomic_write(path, canonical_json_bytes(payload))
        except OSError as exc:
            return AdapterResult(False, "CONSENT_FAULT_MARKER_WRITE_FAILED", detail=type(exc).__name__)
        return AdapterResult(
            True,
            "CONSENT_FAULT_MARKER_APPLIED",
            {
                "marker_digest": sha256_bytes(canonical_json_bytes(payload)),
                "expires_at": expires_at.isoformat(),
                "path_kind": "CONSENT_MARKER",
            },
        )

    def read_consent_fault_receipt(
        self, *, run_id: str, subject: Mapping[str, Any]
    ) -> ConsentFaultReceipt | AdapterResult:
        try:
            active_run = UUID(run_id)
            invitation_id = UUID(str(subject["invitation_id"]))
            applicant_id = UUID(str(subject["applicant_id"]))
            lane = N02LaneId(str(subject["lane_id"]))
            subject_ref = str(subject["subject_ref"])
            path = self._receipt_path(active_run)
            lines = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return AdapterResult(False, "CONSENT_FAULT_RECEIPT_ABSENT")
        except (KeyError, TypeError, ValueError, OSError) as exc:
            return AdapterResult(False, "CONSENT_FAULT_RECEIPT_UNAVAILABLE", detail=type(exc).__name__)
        matches = []
        try:
            for line in lines:
                value = json.loads(line)
                if (
                    value.get("schema_version") == _RECEIPT_SCHEMA
                    and value.get("run_id") == str(active_run)
                    and value.get("lane_id") == lane.value
                    and value.get("subject_ref") == subject_ref
                    and value.get("invitation_id") == str(invitation_id)
                    and value.get("applicant_id") == str(applicant_id)
                    and value.get("fault_type") == _FAULT_TYPE
                    and value.get("fault_variant")
                    == ConsentFaultVariant.AFTER_CONSENT_RECORD_BEFORE_STATE.value
                    and value.get("boundary")
                    == ConsentFaultBoundary.AFTER_CONSENT_RECORD_BEFORE_INVITATION_STATE.value
                ):
                    matches.append(value)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            return AdapterResult(False, "CONSENT_FAULT_RECEIPT_INVALID", detail=type(exc).__name__)
        if len(matches) != 1:
            return AdapterResult(False, "CONSENT_FAULT_RECEIPT_CARDINALITY_INVALID")
        value = matches[0]
        try:
            return ConsentFaultReceipt(
                receipt_id=UUID(str(value["receipt_id"])),
                run_id=active_run,
                lane_id=lane,
                subject_ref=subject_ref,
                invitation_id=invitation_id,
                applicant_id=applicant_id,
                fault_variant=ConsentFaultVariant(str(value["fault_variant"])),
                boundary=ConsentFaultBoundary(str(value["boundary"])),
                request_id=str(value["request_id"]),
                triggered_at=datetime.fromisoformat(str(value["triggered_at"])),
                one_shot_consumed=bool(value["one_shot_consumed"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            return AdapterResult(False, "CONSENT_FAULT_RECEIPT_INVALID", detail=type(exc).__name__)

    def restore_consent_fault(
        self, *, run_id: str, subject: Mapping[str, Any]
    ) -> AdapterResult:
        try:
            active_run = UUID(run_id)
            if active_run != UUID(str(subject["run_id"])):
                return _restore_failed("CONSENT_FAULT_RESTORE_RUN_MISMATCH")
            invitation_id = UUID(str(subject["invitation_id"]))
            marker = self._marker_path(invitation_id)
            consumed = self._consumed_path(active_run, invitation_id)
            self._assert_bounded(marker)
            self._assert_bounded(consumed)
            if marker.exists():
                payload = json.loads(marker.read_text(encoding="utf-8"))
                if not self._owns_marker(payload, active_run, subject):
                    return _restore_failed("CONSENT_FAULT_FOREIGN_MARKER")
                marker.unlink()
            if consumed.exists():
                consumed.unlink()
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            return _restore_failed("CONSENT_FAULT_RESTORE_FAILED", type(exc).__name__)

        state_zero: bool | None = None
        if self.consent_adapter is not None:
            state = self.consent_adapter.read_state(
                subject=subject,
                phase=Phase.RECOVERED.value,
                step_id="verify-failed-consent-zero",
            )
            if isinstance(state, AdapterResult):
                return _restore_failed("CONSENT_FAULT_SAFE_STATE_UNAVAILABLE")
            if state.source_status is Presence.UNAVAILABLE:
                return _restore_failed("CONSENT_FAULT_SAFE_STATE_UNAVAILABLE")
            state_zero = (
                state.source_status is Presence.ABSENT
                and state.active_consent_count == 0
                and not state.consented_state_change_ids
                and not state.consent_completed_event_ids
                and state.invitation_status == "identity_verified"
            )
            if not state_zero:
                return _restore_failed("CONSENT_FAULT_PARTIAL_EFFECT_REMAINS")
        return AdapterResult(
            True,
            "CONSENT_FAULT_RESTORED",
            {
                "marker_removed": not marker.exists(),
                "consumed_token_removed": not consumed.exists(),
                "hook_inactive": not marker.exists(),
                "failed_request_effects_zero": state_zero,
                "manual_cleanup_required": False,
            },
        )

    def _marker_path(self, invitation_id: UUID) -> Path:
        return self.root / "consent" / f"{invitation_id}.json"

    def _receipt_path(self, run_id: UUID) -> Path:
        return self.root / "receipts" / f"{run_id}.jsonl"

    def _consumed_path(self, run_id: UUID, invitation_id: UUID) -> Path:
        return self.root / "consumed" / f"{run_id}-{invitation_id}.consent"

    def _assert_bounded(self, path: Path) -> None:
        if not path.resolve().is_relative_to(self.root):
            raise ValueError("fault path escapes configured root")

    @staticmethod
    def _owns_marker(
        payload: Mapping[str, Any], run_id: UUID, subject: Mapping[str, Any]
    ) -> bool:
        return (
            payload.get("schema_version") == _SCHEMA
            and payload.get("run_id") == str(run_id)
            and payload.get("lane_id") == N02LaneId.CONSENT_FAULT_RECOVERY.value
            and payload.get("subject_ref") == str(subject["subject_ref"])
            and payload.get("invitation_id") == str(UUID(str(subject["invitation_id"])))
            and payload.get("applicant_id") == str(UUID(str(subject["applicant_id"])))
            and payload.get("fault_type") == _FAULT_TYPE
            and payload.get("fault_variant")
            == ConsentFaultVariant.AFTER_CONSENT_RECORD_BEFORE_STATE.value
            and payload.get("one_shot") is True
        )


def _restore_failed(code: str, detail: str | None = None) -> AdapterResult:
    return AdapterResult(
        False,
        code,
        {"manual_cleanup_required": True},
        detail=detail,
    )
