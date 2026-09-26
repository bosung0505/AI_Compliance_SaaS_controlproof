"""WhyYou bindings for the deterministic H-03 pending-report seed."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from sqlalchemy import create_engine, text

from engine.adapters.base import AdapterResult
from engine.config import Settings
from seeds.h03_pending_report import (
    PendingReportSeed,
    apply_pending,
    build_pending_report_fixture,
    check_pending_invariants,
    teardown_pending,
    trigger_event,
    trigger_sql,
)


class WhyYouSeedAdapter:
    def __init__(
        self,
        settings: Settings,
        transaction_factory: Callable[[], AbstractContextManager] | None = None,
    ) -> None:
        self.settings = settings
        self._engine = None
        if transaction_factory is None:
            self._engine = create_engine(settings.whyyou_database_url)
            transaction_factory = self._engine.begin
        self._transaction_factory = transaction_factory
        self._seeds: dict[str, PendingReportSeed] = {}

    def seed(self, *, run_id: str, subject_ref: str) -> AdapterResult:
        seed = build_pending_report_fixture(run_id, subject_ref=subject_ref)
        problems = check_pending_invariants(seed)
        if problems:
            return AdapterResult(False, "SEED_INVARIANT_FAILED", {"problems": problems})
        try:
            with self._transaction_factory() as connection:
                apply_pending(connection, seed)
        except Exception as exc:  # noqa: BLE001 - transaction adapter normalizes driver errors
            return AdapterResult(False, "SEED_WRITE_FAILED", detail=type(exc).__name__)
        self._seeds[run_id] = seed
        correlation = seed.correlation
        return AdapterResult(
            True,
            "SUBJECT_SEEDED",
            {
                "subject_ref": subject_ref,
                "synthetic": True,
                "seed_correlation_id": correlation["seed_correlation_id"],
                "company_id": correlation["company_id"],
                "company_user_id": correlation["reviewer_id"],
                "position_id": correlation["position_id"],
                "invitation_id": correlation[f"invitation_id:{subject_ref}"],
                "interview_session_id": correlation[f"interview_session_id:{subject_ref}"],
                "target_stage_id": str(
                    seed.fixture.of("recruiting_stage")[0]["recruiting_stage_id"]
                ),
                "pipeline_row_version": 1,
            },
        )

    def trigger(self, *, run_id: str, subject: dict[str, Any]) -> AdapterResult:
        seed = self._seeds.get(run_id)
        if seed is None:
            return AdapterResult(False, "SEED_NOT_FOUND")
        event = trigger_event(seed, run_id=run_id)
        sql, params = trigger_sql(event)
        try:
            with self._transaction_factory() as connection:
                connection.execute(text(sql), params)
        except Exception as exc:  # noqa: BLE001 - transaction adapter normalizes driver errors
            return AdapterResult(False, "TRIGGER_WRITE_FAILED", detail=type(exc).__name__)
        return AdapterResult(True, "REPORTING_TRIGGERED", event)

    def teardown(self, *, run_id: str, subject: dict[str, Any]) -> AdapterResult:
        seed = self._seeds.get(run_id)
        if seed is None:
            return AdapterResult(True, "NOTHING_TO_TEARDOWN")
        try:
            with self._transaction_factory() as connection:
                teardown_pending(connection, seed)
        except Exception as exc:  # noqa: BLE001 - cleanup reports a safe result envelope
            return AdapterResult(False, "TEARDOWN_FAILED", detail=type(exc).__name__)
        self._seeds.pop(run_id, None)
        return AdapterResult(
            True,
            "TEARDOWN_COMPLETE",
            {"seed_correlation_id": seed.correlation["seed_correlation_id"]},
        )
