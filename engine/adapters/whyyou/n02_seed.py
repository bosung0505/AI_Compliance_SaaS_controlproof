"""Atomic WhyYou seed/teardown adapter for the N-02 six-lane profile."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from threading import RLock
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, text

from engine.adapters.base import AdapterResult
from engine.config import Settings
from engine.models import N02LaneId, ProtectedPathId, RunSubjectLane
from seeds.n02_subjects import (
    N02SeedPlan,
    SeedRow,
    build_n02_seed_plan,
    build_probe_overlay_rows,
)


class N02CredentialStore:
    """In-memory, non-serializable local credential handoff between seed and HTTP adapter."""

    def __init__(self) -> None:
        self._values: dict[str, str] = {}
        self._lock = RLock()

    def put(self, subject_ref: str, credential: str) -> None:
        with self._lock:
            self._values[subject_ref] = credential

    def get(self, subject_ref: str) -> str | None:
        with self._lock:
            return self._values.get(subject_ref)

    def remove(self, subject_ref: str) -> None:
        with self._lock:
            self._values.pop(subject_ref, None)


class WhyYouN02SeedAdapter:
    def __init__(
        self,
        settings: Settings,
        transaction_factory: Callable[[], AbstractContextManager] | None = None,
        *,
        credentials: N02CredentialStore | None = None,
    ) -> None:
        self.settings = settings
        self.credentials = credentials or N02CredentialStore()
        self._engine = None
        if transaction_factory is None:
            self._engine = create_engine(settings.whyyou_database_url)
            transaction_factory = self._engine.begin
        self._transaction_factory = transaction_factory
        self._plans: dict[str, N02SeedPlan] = {}
        self._overlays: dict[tuple[str, ProtectedPathId], tuple[SeedRow, ...]] = {}

    @property
    def active_run_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._plans))

    def seed_lanes(self, *, run_id: str) -> tuple[RunSubjectLane, ...] | AdapterResult:
        active_run = UUID(run_id)
        plan = build_n02_seed_plan(
            active_run,
            company_id=UUID(self.settings.whyyou_company_id),
            reviewer_id=UUID(self.settings.whyyou_company_user_id),
        )
        try:
            with self._transaction_factory() as connection:
                for row in plan.rows:
                    _insert_row(connection, row)
        except Exception as exc:  # noqa: BLE001 - normalized without provider detail
            return AdapterResult(False, "N02_SEED_WRITE_FAILED", detail=type(exc).__name__)
        self._plans[run_id] = plan
        for subject in plan.subjects:
            self.credentials.put(subject.subject_ref, subject.raw_session_cookie)
        return plan.lanes

    def subject_for(self, *, run_id: str, lane_id: N02LaneId) -> dict[str, Any]:
        plan = self._plans.get(run_id)
        if plan is None:
            raise LookupError("N-02 seed is not owned by this adapter")
        return plan.subject_payload(lane_id)

    def apply_probe_overlay(
        self, *, subject: Mapping[str, Any], path_id: str
    ) -> AdapterResult:
        try:
            run_id = str(UUID(str(subject["run_id"])))
            lane = N02LaneId(str(subject["lane_id"]))
            path = ProtectedPathId(path_id)
            plan = self._plans[run_id]
            definition = plan.by_lane(lane)
            if lane is not N02LaneId.CONSENT_FAULT_RECOVERY:
                return AdapterResult(False, "N02_OVERLAY_LANE_MISMATCH")
            if definition.invitation_id != UUID(str(subject["invitation_id"])):
                return AdapterResult(False, "N02_OVERLAY_SUBJECT_MISMATCH")
        except (KeyError, TypeError, ValueError):
            return AdapterResult(False, "N02_OVERLAY_SUBJECT_INVALID")
        if path is ProtectedPathId.DOCUMENT_ANALYSIS:
            return AdapterResult(
                True,
                "N02_PROBE_OVERLAY_NOT_REQUIRED",
                {"path_id": path.value, "seed_digest": plan.digest},
            )
        key = (run_id, path)
        if key in self._overlays:
            return AdapterResult(False, "N02_PROBE_OVERLAY_ALREADY_APPLIED")
        rows = tuple(
            build_probe_overlay_rows(
                definition,
                plan.company_id,
                plan.competency_model_version_id,
                plan.criterion_id,
                include_assessment=(path is ProtectedPathId.AI_ASSESSMENT),
            )
        )
        try:
            with self._transaction_factory() as connection:
                for row in rows:
                    _insert_row(connection, row)
        except Exception as exc:  # noqa: BLE001 - normalize target provider details
            return AdapterResult(False, "N02_PROBE_OVERLAY_WRITE_FAILED", detail=type(exc).__name__)
        self._overlays[key] = rows
        return AdapterResult(
            True,
            "N02_PROBE_OVERLAY_APPLIED",
            {
                "path_id": path.value,
                "row_count": len(rows),
                "original_seed_digest": plan.digest,
            },
        )

    def remove_probe_overlay(
        self, *, subject: Mapping[str, Any], path_id: str
    ) -> AdapterResult:
        try:
            run_id = str(UUID(str(subject["run_id"])))
            path = ProtectedPathId(path_id)
            plan = self._plans[run_id]
        except (KeyError, TypeError, ValueError):
            return AdapterResult(False, "N02_OVERLAY_SUBJECT_INVALID")
        key = (run_id, path)
        rows = self._overlays.get(key)
        if rows is None:
            return AdapterResult(
                True,
                "N02_PROBE_OVERLAY_ABSENT",
                {"path_id": path.value, "seed_digest_restored": plan.digest},
            )
        try:
            with self._transaction_factory() as connection:
                for row in reversed(rows):
                    _delete_row(connection, row)
        except Exception as exc:  # noqa: BLE001 - cleanup evidence remains sanitized
            return AdapterResult(False, "N02_PROBE_OVERLAY_REMOVE_FAILED", detail=type(exc).__name__)
        self._overlays.pop(key, None)
        return AdapterResult(
            True,
            "N02_PROBE_OVERLAY_REMOVED",
            {
                "path_id": path.value,
                "seed_digest_restored": plan.digest,
                "remaining_overlay_count": sum(
                    1 for active_run, _path in self._overlays if active_run == run_id
                ),
            },
        )

    def teardown_lanes(
        self, *, run_id: str, lanes: tuple[RunSubjectLane, ...]
    ) -> AdapterResult:
        plan = self._plans.get(run_id)
        if plan is None or plan.lanes != lanes:
            return AdapterResult(False, "N02_SEED_NOT_OWNED")
        try:
            with self._transaction_factory() as connection:
                connection.execute(text("SELECT :run_id"), {"run_id": run_id})
                for (active_run, _path), rows in tuple(self._overlays.items()):
                    if active_run == run_id:
                        for row in reversed(rows):
                            _delete_dependents(connection, row.table, row.values)
                            _delete_row(connection, row)
                for row in reversed(plan.rows):
                    _delete_dependents(connection, row.table, row.values)
                    _delete_row(connection, row)
        except Exception as exc:  # noqa: BLE001 - cleanup result remains sanitized
            return AdapterResult(False, "N02_TEARDOWN_FAILED", detail=type(exc).__name__)
        self._plans.pop(run_id, None)
        self._overlays = {
            key: value for key, value in self._overlays.items() if key[0] != run_id
        }
        for subject in plan.subjects:
            self.credentials.remove(subject.subject_ref)
        return AdapterResult(
            True,
            "N02_LANES_REMOVED",
            {"count": len(plan.lanes), "seed_digest": plan.digest},
        )


_REFERENCING_FOREIGN_KEYS = """
SELECT c.conrelid::regclass::text AS child_table,
       ARRAY(SELECT a.attname FROM unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord)
             JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
             ORDER BY k.ord)::text[] AS child_columns,
       ARRAY(SELECT a.attname FROM unnest(c.confkey) WITH ORDINALITY AS k(attnum, ord)
             JOIN pg_attribute a ON a.attrelid = c.confrelid AND a.attnum = k.attnum
             ORDER BY k.ord)::text[] AS parent_columns
FROM pg_constraint c
WHERE c.contype = 'f' AND c.confrelid = to_regclass(:parent)
ORDER BY 1, c.conname
"""

_MAX_DEPENDENT_DEPTH = 12


def _identifier(name: str) -> str:
    bare = name.strip('"')
    if not bare.replace("_", "").isalnum():
        raise RuntimeError(f"unexpected catalog identifier: {name!r}")
    return f'"{bare}"'


def _delete_dependents(
    connection: Any, table: str, values: dict[str, Any], *, depth: int = 0
) -> None:
    """Remove target-created rows that reference this run's seeded row (ID-003-12).

    WhyYou foreign keys are ``NO ACTION``: once a Run commits consent, rows such as
    ``invitation_state_history`` and ``consent_records`` reference the seeded invitation and
    the seed delete fails. Only rows reachable through foreign keys from this Run's own seeded
    rows are removed, children first; nothing shared (the company) is ever a starting point.
    """
    if depth > _MAX_DEPENDENT_DEPTH:
        raise RuntimeError("N-02 dependent cleanup exceeded the depth limit")
    references = connection.execute(
        text(_REFERENCING_FOREIGN_KEYS), {"parent": table}
    ).mappings().all()
    for reference in references:
        child = _identifier(str(reference["child_table"]))
        child_columns = [str(item) for item in reference["child_columns"]]
        parent_columns = [str(item) for item in reference["parent_columns"]]
        if any(column not in values or values[column] is None for column in parent_columns):
            continue
        params = {f"k{index}": values[column] for index, column in enumerate(parent_columns)}
        where = " AND ".join(
            f"{_identifier(column)} = :k{index}" for index, column in enumerate(child_columns)
        )
        children = connection.execute(
            text(f"SELECT * FROM {child} WHERE {where}"), params
        ).mappings().all()
        for row in children:
            _delete_dependents(connection, child.strip('"'), dict(row), depth=depth + 1)
        if children:
            connection.execute(text(f"DELETE FROM {child} WHERE {where}"), params)


def _insert_row(connection: Any, row: SeedRow) -> None:
    columns = tuple(row.values)
    names = ", ".join(columns)
    placeholders = ", ".join(
        (
            f"CAST(:{column} AS jsonb)"
            if isinstance(row.values[column], (dict, list))
            else f":{column}"
        )
        for column in columns
    )
    params = {
        column: (
            json.dumps(value, sort_keys=True, separators=(",", ":"))
            if isinstance(value, (dict, list))
            else value
        )
        for column, value in row.values.items()
    }
    connection.execute(
        text(f"INSERT INTO {row.table} ({names}) VALUES ({placeholders})"),
        params,
    )


def _delete_row(connection: Any, row: SeedRow) -> None:
    identity = {
        key: value
        for key, value in row.values.items()
        if key.endswith("_id") or key in {"session_hash"}
    }
    if not identity:
        raise RuntimeError(f"seed row has no allowlisted identity: {row.table}")
    where = " AND ".join(f"{key} = :{key}" for key in identity)
    connection.execute(
        text(f"DELETE FROM {row.table} WHERE {where}"),
        identity,
    )
