"""Atomic WhyYou seed/teardown adapter for the Spec 004 report lanes.

Rows come from `seeds/spec004_subjects.py`; insertion, FK-catalog dependent cleanup and the local credential
handoff reuse the N-02 helpers (ID-003-12: only rows reachable from this Run's own seeded rows are removed).
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from uuid import UUID

from sqlalchemy import create_engine, text

from engine.adapters.base import AdapterResult
from engine.adapters.whyyou.n02_seed import (
    N02CredentialStore,
    _delete_dependents,
    _delete_row,
    _insert_row,
)
from engine.config import Settings
from engine.models import ReportLane
from seeds.n02_subjects import SeedRow
from seeds.spec004_subjects import e02_position_rows, lane_credential, lane_rows


class WhyYouSpec004SeedAdapter:
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
        self._rows: dict[str, list[SeedRow]] = {}
        self._lanes: dict[str, dict[str, ReportLane]] = {}

    @property
    def _company(self) -> UUID:
        return UUID(self.settings.whyyou_company_id)

    @property
    def _reviewer(self) -> UUID:
        return UUID(self.settings.whyyou_company_user_id)

    def _write(self, run_id: str, rows: tuple[SeedRow, ...], code: str) -> AdapterResult | None:
        try:
            with self._transaction_factory() as connection:
                for row in rows:
                    _insert_row(connection, row)
        except Exception as exc:  # noqa: BLE001 - normalized without provider detail
            return AdapterResult(False, code, detail=type(exc).__name__)
        self._rows.setdefault(run_id, []).extend(rows)
        return None

    def seed_position(self, *, run_id: str, position_id: str) -> AdapterResult:
        rows = e02_position_rows(UUID(run_id), company_id=self._company, reviewer_id=self._reviewer)
        if str(rows[0].values["position_id"]) != str(UUID(position_id)):
            return AdapterResult(False, "SPEC004_POSITION_NOT_RUN_OWNED")
        failure = self._write(run_id, rows, "SPEC004_POSITION_WRITE_FAILED")
        return failure or AdapterResult(True, "SPEC004_POSITION_SEEDED", {"row_count": len(rows)})

    def seed_lanes(self, *, run_id: str, lanes: tuple[ReportLane, ...]) -> AdapterResult:
        if any(str(lane.run_id) != str(UUID(run_id)) for lane in lanes):
            return AdapterResult(False, "SPEC004_LANE_RUN_MISMATCH")
        rows = tuple(
            row
            for lane in lanes
            for row in lane_rows(lane, company_id=self._company, reviewer_id=self._reviewer)
        )
        failure = self._write(run_id, rows, "SPEC004_SEED_WRITE_FAILED")
        if failure:
            return failure
        owned = self._lanes.setdefault(run_id, {})
        for lane in lanes:
            owned[lane.lane_id.value] = lane
            self.credentials.put(lane.subject_ref, lane_credential(lane))
        return AdapterResult(
            True,
            "SPEC004_LANES_SEEDED",
            {
                "row_count": len(rows),
                "fixture_digests": {lane.lane_id.value: lane.fixture_digest for lane in lanes},
            },
        )

    def teardown(
        self, *, run_id: str, lanes: tuple[ReportLane, ...], position_ids: tuple[str, ...]
    ) -> AdapterResult:
        owned = self._lanes.get(run_id, {})
        if run_id not in self._rows or any(lane.lane_id.value not in owned for lane in lanes):
            return AdapterResult(False, "SPEC004_SEED_NOT_OWNED")
        rows = self._rows[run_id]
        try:
            with self._transaction_factory() as connection:
                connection.execute(text("SELECT :run_id"), {"run_id": run_id})
                # Reports reference sessions without an FK, so the catalog walk cannot find
                # them. Start only from sessions registered by this adapter for this Run.
                for row in rows:
                    if row.table != "interview_sessions":
                        continue
                    reports = (
                        connection.execute(
                            text(
                                "SELECT * FROM reports WHERE company_id=:company_id "
                                "AND interview_session_id=:interview_session_id"
                            ),
                            {
                                "company_id": row.values["company_id"],
                                "interview_session_id": row.values["interview_session_id"],
                            },
                        )
                        .mappings()
                        .all()
                    )
                    for report in reports:
                        _delete_dependents(connection, "reports", dict(report))
                        _delete_row(
                            connection,
                            SeedRow(
                                "reports",
                                {
                                    "company_id": report["company_id"],
                                    "report_id": report["report_id"],
                                },
                            ),
                        )
                for row in reversed(rows):
                    _delete_dependents(connection, row.table, row.values)
                    _delete_row(connection, row)
        except Exception as exc:  # noqa: BLE001 - cleanup result remains sanitized
            return AdapterResult(False, "SPEC004_TEARDOWN_FAILED", detail=type(exc).__name__)
        for lane in owned.values():
            self.credentials.remove(lane.subject_ref)
        self._rows.pop(run_id, None)
        self._lanes.pop(run_id, None)
        return AdapterResult(True, "SPEC004_TEARDOWN_COMPLETE", {"removed_rows": len(rows)})
