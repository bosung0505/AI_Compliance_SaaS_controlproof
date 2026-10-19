"""Owned-row cleanup and independent residue recount for Spec 009 lanes.

Same algorithm as ``H01Live.cleanup`` (h01_live.py stays untouched): every catalog table except the
shared company rows is scanned for this Run's root IDs, the candidates are removed children first,
and a separate connection recounts the same predicate after commit. SQL identifiers come only from
the local DB catalog, never from request data.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import inspect, text

from engine.adapters.whyyou.h01_live import OWNED_COLUMNS as H01_OWNED_COLUMNS
from engine.adapters.whyyou.n02_seed import _delete_dependents, _identifier
from seeds.n02_subjects import SeedRow

#: Spec 009 seeds also own a criterion and a recruiting stage.
OWNED_COLUMNS = frozenset(H01_OWNED_COLUMNS | {"criterion_id", "recruiting_stage_id"})
#: Tables the N-01/N-03 judges require in ``owned_residue_counts`` (engine/n01.py ⊇ engine/n03.py).
REQUIRED_RESIDUE_TABLES = frozenset(
    {
        "invitations",
        "applicant_profiles",
        "applicant_access_tokens",
        "applicant_access_sessions",
        "consent_records",
        "invitation_state_history",
        "outbox_events",
        "processed_messages",
        "audit_events",
    }
)
_SHARED_TABLES = frozenset({"companies", "company_users", "alembic_version"})
_EXPANSIONS = (
    ("reports", "invitation_id"),
    ("human_reviews", "target_id"),
    ("outbox_events", "aggregate_id"),
)
_EXPANSION_KEYS = ("report_id", "human_review_id", "outbox_event_id")
_SEED_IDENTITY_KEYS = frozenset({"session_hash", "token_hash"})


@dataclass(frozen=True, slots=True)
class TableInfo:
    columns: frozenset[str]
    primary_key: tuple[str, ...]


def table_inventory(connection: Any) -> dict[str, TableInfo]:
    inspector = inspect(connection)
    return {
        table: TableInfo(
            columns=frozenset(column["name"] for column in inspector.get_columns(table)),
            primary_key=tuple(inspector.get_pk_constraint(table)["constrained_columns"]),
        )
        for table in inspector.get_table_names()
        if table not in _SHARED_TABLES
    }


def _predicate(
    table: str, info: TableInfo, company_id: UUID, resources: Iterable[UUID]
) -> tuple[str, dict[str, Any]] | None:
    selected = sorted(info.columns & OWNED_COLUMNS)
    if not selected or ("company_id" not in info.columns and table != "processed_messages"):
        return None
    params: dict[str, Any] = {
        f"id{index}": str(value) for index, value in enumerate(sorted(resources, key=str))
    }
    if not params:
        return None
    marks = ",".join(":" + key for key in params)
    predicate = "(" + " OR ".join(
        f"CAST({_identifier(column)} AS TEXT) IN ({marks})" for column in selected
    ) + ")"
    if "company_id" in info.columns:
        predicate += " AND company_id=:company"
        params["company"] = company_id
    return predicate, params


def _is_seed_row(table: str, row: Mapping[str, Any], seed_rows: Iterable[SeedRow]) -> bool:
    for seed in seed_rows:
        if seed.table != table:
            continue
        identity = {
            key: value
            for key, value in seed.values.items()
            if (key.endswith("_id") or key in _SEED_IDENTITY_KEYS) and value is not None
        }
        if identity and all(str(row.get(key)) == str(value) for key, value in identity.items()):
            return True
    return False


def expand_resources(
    connection: Any, *, company_id: UUID, resources: Iterable[UUID], inventory: Mapping[str, TableInfo]
) -> frozenset[UUID]:
    """Read-only: add report, human review and outbox event IDs that hang off the owned roots."""
    owned = set(resources)
    for table, column in _EXPANSIONS:
        if table not in inventory:
            continue
        for value in sorted(owned, key=str):
            found = connection.execute(
                text(
                    f"SELECT * FROM {_identifier(table)} WHERE company_id=:company "
                    f"AND CAST({_identifier(column)} AS TEXT)=:value"
                ),
                {"company": company_id, "value": str(value)},
            ).mappings().all()
            for row in found:
                owned.update(UUID(str(row[key])) for key in _EXPANSION_KEYS if row.get(key))
    return frozenset(owned)


def delete_owned_rows(
    connection: Any,
    *,
    company_id: UUID,
    resources: Iterable[UUID],
    inventory: Mapping[str, TableInfo],
    seed_rows: Iterable[SeedRow] = (),
) -> tuple[int, frozenset[UUID]]:
    """Remove product rows owned by ``resources``; seed rows are left for the seed teardown.

    Returns the number of product rows removed and the expanded resource set the recount uses.
    """
    owned = set(expand_resources(connection, company_id=company_id, resources=resources, inventory=inventory))
    seeds = tuple(seed_rows)
    candidates = []
    for table, info in inventory.items():
        scoped = _predicate(table, info, company_id, owned)
        if scoped is None:
            continue
        predicate, params = scoped
        rows = connection.execute(
            text(f"SELECT * FROM {_identifier(table)} WHERE {predicate}"), params
        ).mappings().all()
        for row in rows:
            owned.update(UUID(str(row[key])) for key in _EXPANSION_KEYS if row.get(key))
        product = [dict(row) for row in rows if not _is_seed_row(table, row, seeds)]
        if product:
            candidates.append((table, product))
    removed = 0
    for table, rows in reversed(candidates):
        key = inventory[table].primary_key
        if not key:
            raise RuntimeError(f"owned table has no primary key: {table}")
        for row in rows:
            _delete_dependents(connection, table, row)
            where = " AND ".join(f"{_identifier(column)} = :k{index}" for index, column in enumerate(key))
            connection.execute(
                text(f"DELETE FROM {_identifier(table)} WHERE {where}"),
                {f"k{index}": row[column] for index, column in enumerate(key)},
            )
            removed += 1
    return removed, frozenset(owned)


def count_owned_rows(
    connection: Any,
    *,
    company_id: UUID,
    resources: Iterable[UUID],
    inventory: Mapping[str, TableInfo],
) -> dict[str, int]:
    """Independent recount; required tables missing from the catalog are reported as 0."""
    owned = tuple(resources)
    counts: dict[str, int] = {}
    for table, info in inventory.items():
        scoped = _predicate(table, info, company_id, owned)
        if scoped is None:
            continue
        predicate, params = scoped
        counts[table] = int(
            connection.execute(
                text(f"SELECT COUNT(*) FROM {_identifier(table)} WHERE {predicate}"), params
            ).scalar_one()
        )
    for table in REQUIRED_RESIDUE_TABLES:
        counts.setdefault(table, 0)
    return dict(sorted(counts.items()))
