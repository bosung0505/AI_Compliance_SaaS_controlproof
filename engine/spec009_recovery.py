"""Recovery of a Spec 009 RESTORE_FAILED Run's owned rows, and the read-only recount behind cleanup-confirm.

The Run's IDs are rebuilt deterministically from its run_id (seeds/spec009_subjects.py), so no raw token is
needed. The sealed bundle is never read for writing and never changed: the Run stays RESTORE_FAILED and the
next verification is a child Run.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine

from engine.adapters.whyyou.n02_seed import _delete_dependents, _delete_row
from engine.adapters.whyyou.spec009_cleanup import (
    TableInfo,
    count_owned_rows,
    delete_owned_rows,
    expand_resources,
    table_inventory,
)
from engine.lifecycle import RestoreBlockStore
from engine.models import ExecutionProfile, utcnow
from seeds.n02_subjects import SeedRow
from seeds.spec009_subjects import Spec009SeedPlan, build_spec009_seed_plan

SCHEMA_VERSION = "controlproof.spec009-recovery.v1"
TARGET_ID = "whyyou-local"
BLOCK_SUBJECTS = {
    "n01-notice": ExecutionProfile.N01_NOTICE_V1,
    "n03-stale-consent": ExecutionProfile.N03_STALE_CONSENT_V1,
}
SUBJECT_FOR = {profile: subject for subject, profile in BLOCK_SUBJECTS.items()}
_RANDOM_KEYS = frozenset({"session_hash", "token_hash"})

Factory = Callable[[], AbstractContextManager]
Inventory = Callable[[Any], Mapping[str, TableInfo]]


class RecoveryError(ValueError):
    pass


def check_block(run_root: Path, *, run_id: str, profile: ExecutionProfile) -> None:
    """The profile's block must name this Run, and the sealed run.json must be that profile."""
    blocks = RestoreBlockStore(Path(run_root))
    path = blocks.path_for(TARGET_ID, SUBJECT_FOR[profile])
    if not path.exists():
        raise RecoveryError("SPEC009_RECOVERY_BLOCK_MISSING")
    if json.loads(path.read_text(encoding="utf-8")).get("run_id") != str(UUID(run_id)):
        raise RecoveryError("SPEC009_RECOVERY_BLOCK_MISMATCH")
    try:
        run = json.loads((Path(run_root) / str(UUID(run_id)) / "run.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RecoveryError("SPEC009_RECOVERY_BUNDLE_MISSING") from exc
    if run.get("execution_profile") != profile.value:
        raise RecoveryError("SPEC009_RECOVERY_PROFILE_MISMATCH")


def plan_for(settings, *, run_id: str, profile: ExecutionProfile) -> Spec009SeedPlan:
    return build_spec009_seed_plan(
        UUID(run_id),
        profile=profile,
        company_id=UUID(str(settings.whyyou_company_id)),
        reviewer_id=UUID(str(settings.whyyou_company_user_id)),
    )


def _factories(settings, transaction_factory: Factory | None, read_factory: Factory | None):
    if transaction_factory is not None and read_factory is not None:
        return transaction_factory, read_factory, None
    engine = create_engine(settings.whyyou_database_url)
    return transaction_factory or engine.begin, read_factory or engine.connect, engine


def recover(
    settings,
    *,
    run_id: str,
    profile: ExecutionProfile,
    transaction_factory: Factory | None = None,
    read_factory: Factory | None = None,
    inventory: Inventory = table_inventory,
) -> dict[str, Any]:
    """Delete owned product rows, then seed rows (missing rows are ignored), then recount on a new connection."""
    check_block(settings.run_root, run_id=run_id, profile=profile)
    plan = plan_for(settings, run_id=run_id, profile=profile)
    # Token and session hashes come from raw values drawn at seed time and cannot be rebuilt; seed rows are
    # identified and deleted by their deterministic IDs only (session_id, invitation_id, applicant_id, ...).
    seed_rows = tuple(
        SeedRow(row.table, {key: value for key, value in row.values.items() if key not in _RANDOM_KEYS})
        for row in plan.rows
    )
    begin, connect, engine = _factories(settings, transaction_factory, read_factory)
    try:
        with begin() as connection:
            tables = inventory(connection)
            removed, resources = delete_owned_rows(
                connection,
                company_id=plan.company_id,
                resources=plan.owned_ids(),
                inventory=tables,
                seed_rows=seed_rows,
            )
            for row in reversed(seed_rows):
                _delete_dependents(connection, row.table, row.values)
                _delete_row(connection, row)
        with connect() as connection:
            counts = count_owned_rows(connection, company_id=plan.company_id, resources=resources, inventory=tables)
    finally:
        if engine is not None:
            engine.dispose()
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(UUID(run_id)),
        "profile": profile.value,
        "status": "SUCCEEDED" if not any(counts.values()) else "FAILED",
        "owned_residue_counts": counts,
        "product_rows_removed": removed,
        "recovered_at": utcnow().isoformat(),
    }


def recount(
    settings,
    *,
    run_id: str,
    profile: ExecutionProfile,
    read_factory: Factory | None = None,
    inventory: Inventory = table_inventory,
) -> dict[str, int]:
    """Read-only: the same owned-row predicate as the teardown recount, no DELETE."""
    plan = plan_for(settings, run_id=run_id, profile=profile)
    engine = None
    if read_factory is None:
        engine = create_engine(settings.whyyou_database_url)
        read_factory = engine.connect
    try:
        with read_factory() as connection:
            tables = inventory(connection)
            resources = expand_resources(
                connection, company_id=plan.company_id, resources=plan.owned_ids(), inventory=tables
            )
            return count_owned_rows(connection, company_id=plan.company_id, resources=resources, inventory=tables)
    finally:
        if engine is not None:
            engine.dispose()
