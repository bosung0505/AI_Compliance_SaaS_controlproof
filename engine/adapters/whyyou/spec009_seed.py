"""Atomic WhyYou seed/teardown adapter for the Spec 009 N-01 and N-03 lanes."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine

from engine.adapters.base import AdapterResult
from engine.adapters.whyyou.n02_seed import (
    N02CredentialStore,
    _delete_dependents,
    _delete_row,
    _insert_row,
)
from engine.adapters.whyyou.spec009_cleanup import (
    TableInfo,
    count_owned_rows,
    delete_owned_rows,
    table_inventory,
)
from engine.config import Settings
from engine.models import (
    SPEC009_PROFILES,
    ExecutionProfile,
    N01LaneId,
    N03LaneId,
    Spec009SubjectLane,
)
from seeds.spec009_subjects import Spec009SeedPlan, build_spec009_seed_plan


def _token_key(subject_ref: str) -> str:
    return f"{subject_ref}:invitation_token"


class WhyYouSpec009SeedAdapter:
    def __init__(
        self,
        settings: Settings,
        transaction_factory: Callable[[], AbstractContextManager] | None = None,
        *,
        credentials: N02CredentialStore,
        read_factory: Callable[[], AbstractContextManager] | None = None,
        inventory: Callable[[Any], Mapping[str, TableInfo]] = table_inventory,
    ) -> None:
        self.settings = settings
        self.credentials = credentials
        self._engine = None
        if transaction_factory is None:
            self._engine = create_engine(settings.whyyou_database_url)
            transaction_factory = self._engine.begin
            read_factory = read_factory or self._engine.connect
        self._transaction_factory = transaction_factory
        # The residue recount runs on its own connection after the cleanup transaction commits.
        self._read_factory = read_factory or transaction_factory
        self._inventory = inventory
        self._plans: dict[str, Spec009SeedPlan] = {}

    @property
    def active_run_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._plans))

    def seed_lanes(
        self, *, run_id: str, profile: ExecutionProfile
    ) -> tuple[Spec009SubjectLane, ...] | AdapterResult:
        if profile not in SPEC009_PROFILES:
            return AdapterResult(False, "SPEC009_PROFILE_UNSUPPORTED")
        plan = build_spec009_seed_plan(
            UUID(run_id),
            profile=profile,
            company_id=UUID(self.settings.whyyou_company_id),
            reviewer_id=UUID(self.settings.whyyou_company_user_id),
        )
        try:
            with self._transaction_factory() as connection:
                for row in plan.rows:
                    _insert_row(connection, row)
        except Exception as exc:  # noqa: BLE001 - normalized without provider detail
            return AdapterResult(False, "SPEC009_SEED_WRITE_FAILED", detail=type(exc).__name__)
        self._plans[run_id] = plan
        for subject in plan.subjects:
            if subject.raw_invitation_token:
                self.credentials.put(_token_key(subject.subject_ref), subject.raw_invitation_token)
            if subject.raw_session_cookie:
                self.credentials.put(subject.subject_ref, subject.raw_session_cookie)
        return plan.lanes

    def subject_for(self, *, run_id: str, lane_id: N01LaneId | N03LaneId) -> dict[str, Any]:
        plan = self._plans.get(run_id)
        if plan is None:
            raise LookupError("Spec 009 seed is not owned by this adapter")
        return plan.subject_payload(lane_id)

    def display_name_for(self, *, run_id: str, lane_id: N01LaneId | N03LaneId) -> str:
        plan = self._plans.get(run_id)
        if plan is None:
            raise LookupError("Spec 009 seed is not owned by this adapter")
        return plan.by_lane(lane_id).display_name

    def teardown_lanes(
        self, *, run_id: str, lanes: tuple[Spec009SubjectLane, ...]
    ) -> AdapterResult:
        plan = self._plans.get(run_id)
        if plan is None or plan.lanes != tuple(lanes):
            return AdapterResult(False, "SPEC009_SEED_NOT_OWNED")
        try:
            with self._transaction_factory() as connection:
                inventory = self._inventory(connection)
                product_rows_removed, resources = delete_owned_rows(
                    connection,
                    company_id=plan.company_id,
                    resources=plan.owned_ids(),
                    inventory=inventory,
                    seed_rows=plan.rows,
                )
                for row in reversed(plan.rows):
                    _delete_dependents(connection, row.table, row.values)
                    _delete_row(connection, row)
        except Exception as exc:  # noqa: BLE001 - cleanup result remains sanitized
            return AdapterResult(False, "SPEC009_TEARDOWN_FAILED", detail=type(exc).__name__)
        try:
            with self._read_factory() as connection:
                counts = count_owned_rows(
                    connection,
                    company_id=plan.company_id,
                    resources=resources,
                    inventory=inventory,
                )
        except Exception as exc:  # noqa: BLE001 - recount failure is not a verified cleanup
            return AdapterResult(False, "SPEC009_RESIDUE_READ_FAILED", detail=type(exc).__name__)
        status = "SUCCEEDED" if not any(counts.values()) else "FAILED"
        data = {
            "status": status,
            "owned_residue_counts": counts,
            "product_rows_removed": product_rows_removed,
            "seed_digest": plan.digest,
        }
        if status != "SUCCEEDED":
            # Ownership stays so a retry can scan the same IDs again.
            return AdapterResult(False, "SPEC009_RESIDUE_REMAINS", data)
        self._plans.pop(run_id, None)
        for subject in plan.subjects:
            self.credentials.remove(_token_key(subject.subject_ref))
            self.credentials.remove(subject.subject_ref)
        return AdapterResult(True, "SPEC009_LANES_REMOVED", data)
