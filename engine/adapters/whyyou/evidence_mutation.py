"""Run-owned change injections for E-01 (T047, contracts/whyyou-spec004-adapter.md).

`remove_segment` deletes one transcript segment of the lane's own interview session after checking that no other
lane's Evidence cites it, keeps the full row in process memory (never in the bundle) and confirms absence on a
separate connection. `write_probe_axes` rewrites only `report_items.axis_assessments` of a Run-owned item. Both
restores are confirmed by re-reading the row digest on a separate connection; a mismatch is `RESTORE_FAILED`.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from contextlib import AbstractContextManager
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, text

from engine.adapters.base import AdapterResult
from engine.adapters.whyyou.n02_seed import _insert_row
from engine.config import Settings
from engine.models import (
    ChangeInjection,
    ChangeInjectionKind,
    ChangeInjectionState,
    ReportLane,
    RestoreAction,
    canonical_json_bytes,
    sha256_bytes,
    utcnow,
)
from seeds.n02_subjects import SeedRow

_SELECT_SEGMENT = (
    "SELECT * FROM transcript_segments WHERE transcript_segment_id = :transcript_segment_id"
)
_SELECT_OWNED_SEGMENT = _SELECT_SEGMENT + " AND interview_session_id = :session_id"
_SHARED_EVIDENCE = (
    "SELECT count(*) AS shared FROM evidence e "
    "JOIN report_items ri ON ri.company_id = e.company_id AND ri.report_item_id = e.report_item_id "
    "JOIN reports r ON r.company_id = ri.company_id AND r.report_id = ri.report_id "
    "WHERE e.company_id = :company_id AND e.transcript_segment_id = :transcript_segment_id "
    "AND r.interview_session_id <> :session_id"
)
_DELETE_SEGMENT = (
    "DELETE FROM transcript_segments "
    "WHERE company_id = :company_id AND transcript_segment_id = :transcript_segment_id"
)
_SELECT_ITEM = (
    "SELECT ri.company_id, ri.axis_assessments FROM report_items ri "
    "WHERE ri.report_item_id = :report_item_id"
)
_SELECT_OWNED_ITEM = _SELECT_ITEM + (
    " AND EXISTS (SELECT 1 FROM reports r WHERE r.company_id = ri.company_id"
    " AND r.report_id = ri.report_id AND r.interview_session_id = :session_id)"
)
_UPDATE_AXES = (
    "UPDATE report_items SET axis_assessments = CAST(:axes AS json) "
    "WHERE company_id = :company_id AND report_item_id = :report_item_id"
)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _digest(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(_jsonable(value)))


def _axes_value(raw: Any) -> Any:
    return json.loads(raw) if isinstance(raw, str) else raw


class WhyYouEvidenceMutationAdapter:
    def __init__(
        self,
        settings: Settings,
        *,
        transaction_factory: Callable[[], AbstractContextManager] | None = None,
        verify_factory: Callable[[], AbstractContextManager] | None = None,
    ) -> None:
        self.settings = settings
        if transaction_factory is None or verify_factory is None:
            engine = create_engine(settings.whyyou_database_url)
            transaction_factory = transaction_factory or engine.begin
            verify_factory = verify_factory or engine.connect
        self._transaction = transaction_factory
        self._verify = verify_factory
        self._preserved: dict[str, dict[str, Any]] = {}

    # --- evidence segment removal --------------------------------------------------------------

    def remove_segment(
        self, *, lane: ReportLane, transcript_segment_id: str, injection_id: str
    ) -> ChangeInjection | AdapterResult:
        owned = {str(item.transcript_segment_id) for item in lane.criteria}
        if str(transcript_segment_id) not in owned:
            return AdapterResult(False, "SEGMENT_NOT_OWNED_BY_LANE")
        key = {"transcript_segment_id": str(transcript_segment_id)}
        try:
            with self._transaction() as connection:
                rows = connection.execute(
                    text(_SELECT_OWNED_SEGMENT),
                    key | {"session_id": str(lane.interview_session_id)},
                ).mappings().all()
                if len(rows) != 1:
                    return AdapterResult(False, "SEGMENT_NOT_FOUND")
                row = dict(rows[0])
                company = {"company_id": str(row["company_id"])}
                shared = connection.execute(
                    text(_SHARED_EVIDENCE),
                    key | company | {"session_id": str(lane.interview_session_id)},
                ).mappings().first()
                if shared and int(shared["shared"]):
                    return AdapterResult(False, "SEGMENT_SHARED_ACROSS_LANES")
                deleted = connection.execute(text(_DELETE_SEGMENT), key | company)
                if deleted.rowcount != 1:
                    raise RuntimeError("segment delete did not affect exactly one row")
        except Exception as exc:  # noqa: BLE001 - a failed removal is a sanitized precondition
            return AdapterResult(False, "SEGMENT_REMOVAL_FAILED", detail=type(exc).__name__)
        absent = self._read_segment(str(transcript_segment_id)) is None
        self._preserved[str(injection_id)] = {"table": "transcript_segments", "row": row}
        return ChangeInjection(
            injection_id=UUID(str(injection_id)),
            kind=ChangeInjectionKind.EVIDENCE_SEGMENT_REMOVAL,
            run_id=lane.run_id,
            lane_id=lane.lane_id,
            subject_ref=lane.subject_ref,
            target_table="transcript_segments",
            target_ids=(UUID(str(transcript_segment_id)),),
            pre_projection_digest=_digest(row),
            applied_at=utcnow(),
            apply_receipt={"affected_rows": 1, "absence_confirmed": absent},
            restore_action=RestoreAction.REINSERT,
            state=ChangeInjectionState.APPLIED,
        )

    def restore_segment(self, *, injection: ChangeInjection) -> ChangeInjection:
        preserved = self._preserved.get(str(injection.injection_id))
        if preserved is None:
            return _failed(injection, "PRESERVED_ROW_MISSING")
        try:
            with self._transaction() as connection:
                _insert_row(connection, SeedRow("transcript_segments", dict(preserved["row"])))
        except Exception:  # noqa: BLE001 - restore uncertainty becomes RESTORE_FAILED
            return _failed(injection, "RESTORE_WRITE_FAILED")
        current = self._read_segment(str(injection.target_ids[0]))
        return _confirmed(injection, None if current is None else _digest(current))

    def _read_segment(self, segment_id: str) -> dict[str, Any] | None:
        with self._verify() as connection:
            rows = connection.execute(
                text(_SELECT_SEGMENT), {"transcript_segment_id": segment_id}
            ).mappings().all()
        return dict(rows[0]) if rows else None

    # --- storage probe (E01-D1) ----------------------------------------------------------------

    def write_probe_axes(
        self, *, lane: ReportLane, report_item_id: str, axes: Iterable[Mapping[str, Any]],
        injection_id: str,
    ) -> ChangeInjection | AdapterResult:
        written = [_jsonable(axis) for axis in axes]
        params = {"report_item_id": str(report_item_id)}
        try:
            with self._transaction() as connection:
                rows = connection.execute(
                    text(_SELECT_OWNED_ITEM),
                    params | {"session_id": str(lane.interview_session_id)},
                ).mappings().all()
                if len(rows) != 1:
                    return AdapterResult(False, "REPORT_ITEM_NOT_OWNED_BY_LANE")
                row = dict(rows[0])
                original = _axes_value(row["axis_assessments"])
                updated = connection.execute(
                    text(_UPDATE_AXES),
                    params
                    | {
                        "company_id": str(row["company_id"]),
                        "axes": json.dumps(written, sort_keys=True, separators=(",", ":")),
                    },
                )
                if updated.rowcount != 1:
                    raise RuntimeError("probe write did not affect exactly one row")
        except Exception as exc:  # noqa: BLE001 - a failed probe write is a sanitized result
            return AdapterResult(False, "STORAGE_PROBE_WRITE_FAILED", detail=type(exc).__name__)
        self._preserved[str(injection_id)] = {
            "table": "report_items",
            "company_id": str(row["company_id"]),
            "axes": original,
        }
        return ChangeInjection(
            injection_id=UUID(str(injection_id)),
            kind=ChangeInjectionKind.STORAGE_PROBE_WRITE,
            run_id=lane.run_id,
            lane_id=lane.lane_id,
            subject_ref=lane.subject_ref,
            target_table="report_items",
            target_ids=(UUID(str(report_item_id)),),
            pre_projection_digest=_digest(original),
            applied_at=utcnow(),
            apply_receipt={"affected_rows": 1},
            restore_action=RestoreAction.REWRITE,
            state=ChangeInjectionState.APPLIED,
        )

    def restore_probe_axes(self, *, injection: ChangeInjection) -> ChangeInjection:
        preserved = self._preserved.get(str(injection.injection_id))
        if preserved is None:
            return _failed(injection, "PRESERVED_ROW_MISSING")
        item_id = str(injection.target_ids[0])
        try:
            with self._transaction() as connection:
                connection.execute(
                    text(_UPDATE_AXES),
                    {
                        "report_item_id": item_id,
                        "company_id": preserved["company_id"],
                        "axes": json.dumps(
                            preserved["axes"], sort_keys=True, separators=(",", ":")
                        ),
                    },
                )
        except Exception:  # noqa: BLE001 - restore uncertainty becomes RESTORE_FAILED
            return _failed(injection, "RESTORE_WRITE_FAILED")
        current = self._read_axes(item_id)
        return _confirmed(injection, None if current is None else _digest(current))

    def _read_axes(self, report_item_id: str) -> Any:
        with self._verify() as connection:
            rows = connection.execute(
                text(_SELECT_ITEM), {"report_item_id": report_item_id}
            ).mappings().all()
        return _axes_value(rows[0]["axis_assessments"]) if rows else None

    # --- cleanup-confirm (read-only) -----------------------------------------------------------

    def target_safe(self, *, injections: Iterable[Mapping[str, Any]]) -> bool:
        """True when every recorded injection's row reads back with its pre-change digest."""
        for injection in injections:
            kind = str(injection.get("kind"))
            target = str(injection["target_ids"][0])
            if kind == ChangeInjectionKind.EVIDENCE_SEGMENT_REMOVAL.value:
                current = self._read_segment(target)
            elif kind == ChangeInjectionKind.STORAGE_PROBE_WRITE.value:
                current = self._read_axes(target)
            else:
                return False
            if current is None or _digest(current) != injection.get("pre_projection_digest"):
                return False
        return True


def _failed(injection: ChangeInjection, code: str, post: str | None = None) -> ChangeInjection:
    return injection.model_copy(
        update={
            "state": ChangeInjectionState.RESTORE_FAILED,
            "failure_code": code,
            "post_restore_digest": post,
        }
    )


def _confirmed(injection: ChangeInjection, post: str | None) -> ChangeInjection:
    if post is None:
        return _failed(injection, "RESTORED_ROW_ABSENT")
    if post != injection.pre_projection_digest:
        return _failed(injection, "RESTORE_DIGEST_MISMATCH", post)
    return injection.model_copy(
        update={
            "state": ChangeInjectionState.RESTORED,
            "restored_at": utcnow(),
            "post_restore_digest": post,
        }
    )
