"""T007 — Spec 009 seed adapter: atomic seed, owned-row cleanup and an independent residue recount.

The database is a fake in-memory table store; no real connection is opened.
"""

from __future__ import annotations

import re
from uuid import UUID, uuid4

import pytest

from engine import n01, n03
from engine.adapters.base import AdapterResult, Spec009SeedPort
from engine.adapters.whyyou.adapter import create_whyyou_adapter
from engine.adapters.whyyou.n02_seed import N02CredentialStore
from engine.adapters.whyyou.spec009_cleanup import REQUIRED_RESIDUE_TABLES, TableInfo
from engine.adapters.whyyou.spec009_seed import WhyYouSpec009SeedAdapter
from engine.models import ExecutionProfile, N01LaneId, N03LaneId

N01 = ExecutionProfile.N01_NOTICE_V1
N03 = ExecutionProfile.N03_STALE_CONSENT_V1
OTHER_COMPANY = UUID("99999999-9999-4999-8999-999999999999")


def _info(*columns: str, pk: tuple[str, ...]) -> TableInfo:
    return TableInfo(columns=frozenset(columns), primary_key=pk)


INVENTORY = {
    "positions": _info("company_id", "position_id", "title", pk=("company_id", "position_id")),
    "competency_model_versions": _info(
        "company_id", "competency_model_version_id", "position_id", pk=("competency_model_version_id",)
    ),
    "evaluation_criteria": _info(
        "company_id", "criterion_id", "competency_model_version_id", pk=("criterion_id",)
    ),
    "recruiting_stages": _info(
        "company_id", "recruiting_stage_id", "position_id", pk=("recruiting_stage_id",)
    ),
    "invitations": _info(
        "company_id", "invitation_id", "applicant_id", "position_id", pk=("company_id", "invitation_id")
    ),
    "applicant_access_tokens": _info(
        "token_hash", "company_id", "invitation_id", "applicant_id", pk=("token_hash",)
    ),
    "applicant_access_sessions": _info(
        "session_hash", "company_id", "invitation_id", "applicant_id", pk=("session_hash",)
    ),
    "applicant_profiles": _info(
        "company_id", "applicant_id", "invitation_id", pk=("company_id", "applicant_id")
    ),
    "consent_records": _info(
        "consent_record_id", "company_id", "invitation_id", "applicant_id", pk=("consent_record_id",)
    ),
    "outbox_events": _info(
        "outbox_event_id", "company_id", "aggregate_id", pk=("outbox_event_id",)
    ),
    "processed_messages": _info("consumer", "event_id", pk=("consumer", "event_id")),
    "audit_events": _info("audit_event_id", "company_id", "resource_id", pk=("audit_event_id",)),
}

_TABLE = re.compile(r'(?:FROM|INTO)\s+"?(\w+)"?')
_EQUALS = re.compile(r'"?(\w+)"?\s*=\s*:(\w+)')


class _Result:
    def __init__(self, rows=(), scalar=None) -> None:
        self._rows, self._scalar = list(rows), scalar

    def mappings(self):
        return self

    def all(self):
        return self._rows

    def scalar_one(self):
        return self._scalar


class FakeDatabase:
    """Rows per table; SELECT/COUNT match owned IDs by value, DELETE by column equality."""

    def __init__(self, *, fail_insert_at: int | None = None, sticky: frozenset[str] = frozenset()):
        self.tables: dict[str, list[dict]] = {name: [] for name in INVENTORY}
        self.fail_insert_at, self.sticky = fail_insert_at, sticky
        self.inserts = 0
        self.transactions: list[str] = []

    def begin(self):
        return _Connection(self, "begin")

    def connect(self):
        return _Connection(self, "connect")

    def _owned(self, row: dict, params: dict) -> bool:
        values = {str(value) for key, value in params.items() if key.startswith(("id", "value"))}
        if "company" in params and str(row.get("company_id")) != str(params["company"]):
            return False
        return any(str(value) in values for value in row.values())

    def execute(self, sql: str, params: dict):
        if "pg_constraint" in sql:
            return _Result()
        table = _TABLE.search(sql).group(1)
        if sql.startswith("INSERT"):
            self.inserts += 1
            if self.fail_insert_at == self.inserts:
                raise RuntimeError("synthetic insert failure")
            self.tables.setdefault(table, []).append(dict(params))
            return _Result()
        rows = self.tables.get(table, [])
        if sql.startswith("SELECT COUNT"):
            return _Result(scalar=sum(self._owned(row, params) for row in rows))
        if sql.startswith("SELECT"):
            return _Result([dict(row) for row in rows if self._owned(row, params)])
        if sql.startswith("DELETE"):
            if table in self.sticky:
                return _Result()
            pairs = [(column, params[name]) for column, name in _EQUALS.findall(sql.split("WHERE", 1)[1])]
            self.tables[table] = [
                row for row in rows if not all(str(row.get(c)) == str(v) for c, v in pairs)
            ]
            return _Result()
        raise AssertionError(sql)


class _Connection:
    def __init__(self, db: FakeDatabase, kind: str) -> None:
        self.db, self.kind = db, kind

    def __enter__(self):
        self.db.transactions.append(self.kind)
        self.snapshot = {name: list(rows) for name, rows in self.db.tables.items()}
        return self

    def __exit__(self, kind, _value, _traceback):
        if kind is not None:
            self.db.tables = self.snapshot
        return False

    def execute(self, statement, params=None):
        return self.db.execute(str(statement).strip(), dict(params or {}))


def _adapter(settings, db: FakeDatabase, store: N02CredentialStore | None = None):
    return WhyYouSpec009SeedAdapter(
        settings,
        transaction_factory=db.begin,
        credentials=store or N02CredentialStore(),
        read_factory=db.connect,
        inventory=lambda _connection: INVENTORY,
    )


def test_n01_seed_inserts_rows_and_hands_off_invitation_tokens(settings) -> None:
    db, store = FakeDatabase(), N02CredentialStore()
    adapter = _adapter(settings, db, store)
    run_id = str(uuid4())
    lanes = adapter.seed_lanes(run_id=run_id, profile=N01)
    assert isinstance(lanes, tuple) and [lane.lane_id for lane in lanes] == list(N01LaneId)
    assert len(db.tables["invitations"]) == 2 and len(db.tables["applicant_access_tokens"]) == 2
    for lane in lanes:
        assert store.get(f"{lane.subject_ref}:invitation_token")
        assert store.get(lane.subject_ref) is None
    subject = adapter.subject_for(run_id=run_id, lane_id=N01LaneId.PC)
    assert subject["lane_id"] == "pc" and subject["seed_kind"] == "invited-token"


def test_n03_seed_hands_off_session_cookies(settings) -> None:
    db, store = FakeDatabase(), N02CredentialStore()
    lanes = _adapter(settings, db, store).seed_lanes(run_id=str(uuid4()), profile=N03)
    assert [lane.lane_id for lane in lanes] == list(N03LaneId)
    assert len(db.tables["applicant_access_sessions"]) == 2
    assert all(store.get(lane.subject_ref) for lane in lanes)
    assert all(store.get(f"{lane.subject_ref}:invitation_token") is None for lane in lanes)


def test_seed_write_failure_rolls_back_and_hands_off_nothing(settings) -> None:
    db, store = FakeDatabase(fail_insert_at=5), N02CredentialStore()
    adapter = _adapter(settings, db, store)
    result = adapter.seed_lanes(run_id=str(uuid4()), profile=N01)
    assert isinstance(result, AdapterResult)
    assert (result.ok, result.code) == (False, "SPEC009_SEED_WRITE_FAILED")
    assert all(not rows for rows in db.tables.values())
    assert adapter.active_run_ids == ()
    assert store._values == {}


def test_seed_rejects_a_profile_outside_spec009(settings) -> None:
    result = _adapter(settings, FakeDatabase()).seed_lanes(
        run_id=str(uuid4()), profile=ExecutionProfile.N02_CONSENT_ORDER_V1
    )
    assert (result.ok, result.code) == (False, "SPEC009_PROFILE_UNSUPPORTED")


def test_teardown_refuses_a_run_it_does_not_own(settings) -> None:
    adapter = _adapter(settings, FakeDatabase())
    run_id = str(uuid4())
    lanes = adapter.seed_lanes(run_id=run_id, profile=N03)
    foreign = adapter.teardown_lanes(run_id=str(uuid4()), lanes=lanes)
    assert (foreign.ok, foreign.code) == (False, "SPEC009_SEED_NOT_OWNED")
    assert adapter.teardown_lanes(run_id=run_id, lanes=lanes[:1]).code == "SPEC009_SEED_NOT_OWNED"


def _product_rows(db: FakeDatabase, settings, lane) -> None:
    """What the product writes for an N-01 lane: exchange, identity check, consent, events."""
    company = settings.whyyou_company_id
    event = str(uuid4())
    db.tables["applicant_access_sessions"].append(
        {"session_hash": "f" * 64, "company_id": company, "invitation_id": str(lane.invitation_id),
         "applicant_id": str(lane.applicant_id)}
    )
    db.tables["applicant_profiles"].append(
        {"company_id": company, "applicant_id": str(lane.applicant_id), "invitation_id": str(lane.invitation_id)}
    )
    db.tables["consent_records"].append(
        {"consent_record_id": str(uuid4()), "company_id": company,
         "invitation_id": str(lane.invitation_id), "applicant_id": str(lane.applicant_id)}
    )
    db.tables["outbox_events"].append(
        {"outbox_event_id": event, "company_id": company, "aggregate_id": str(lane.invitation_id)}
    )
    db.tables["processed_messages"].append({"consumer": "reporting", "event_id": event})
    db.tables["audit_events"].append(
        {"audit_event_id": str(uuid4()), "company_id": company, "resource_id": str(lane.applicant_id)}
    )


def test_teardown_removes_product_rows_seed_rows_and_credentials(settings) -> None:
    db, store = FakeDatabase(), N02CredentialStore()
    adapter = _adapter(settings, db, store)
    run_id = str(uuid4())
    lanes = adapter.seed_lanes(run_id=run_id, profile=N01)
    for lane in lanes:
        _product_rows(db, settings, lane)
        store.put(lane.subject_ref, "browser-session-cookie")
    unrelated = {"consent_record_id": str(uuid4()), "company_id": str(OTHER_COMPANY),
                 "invitation_id": str(lanes[0].invitation_id), "applicant_id": str(uuid4())}
    db.tables["consent_records"].append(unrelated)

    result = adapter.teardown_lanes(run_id=run_id, lanes=lanes)

    assert (result.ok, result.code) == (True, "SPEC009_LANES_REMOVED")
    assert result.data["status"] == "SUCCEEDED"
    assert result.data["product_rows_removed"] == 12
    assert set(result.data["owned_residue_counts"].values()) == {0}
    assert db.tables["consent_records"] == [unrelated]
    assert all(not rows for name, rows in db.tables.items() if name != "consent_records")
    assert store._values == {}
    assert db.transactions[-1] == "connect"
    assert n01.cleanup_verified(result.data)
    assert adapter.active_run_ids == ()


def test_residue_counts_cover_exactly_the_judges_required_tables(settings) -> None:
    assert REQUIRED_RESIDUE_TABLES == n01.REQUIRED_RESIDUE_TABLES
    assert n03.REQUIRED_RESIDUE_TABLES <= REQUIRED_RESIDUE_TABLES
    inventory = {name: info for name, info in INVENTORY.items() if name != "processed_messages"}
    db = FakeDatabase()
    adapter = WhyYouSpec009SeedAdapter(
        settings, transaction_factory=db.begin, credentials=N02CredentialStore(),
        read_factory=db.connect, inventory=lambda _connection: inventory,
    )
    run_id = str(uuid4())
    lanes = adapter.seed_lanes(run_id=run_id, profile=N03)
    result = adapter.teardown_lanes(run_id=run_id, lanes=lanes)
    counts = result.data["owned_residue_counts"]
    assert REQUIRED_RESIDUE_TABLES <= set(counts)
    assert counts["processed_messages"] == 0  # absent from the catalog: reported as zero
    assert n03.cleanup_verified(result.data)


@pytest.mark.parametrize("profile", [N01, N03])
def test_nonzero_recount_marks_cleanup_failed_and_keeps_ownership(settings, profile) -> None:
    db, store = FakeDatabase(sticky=frozenset({"audit_events"})), N02CredentialStore()
    adapter = _adapter(settings, db, store)
    run_id = str(uuid4())
    lanes = adapter.seed_lanes(run_id=run_id, profile=profile)
    db.tables["audit_events"].append(
        {"audit_event_id": str(uuid4()), "company_id": settings.whyyou_company_id,
         "resource_id": str(lanes[0].invitation_id)}
    )
    result = adapter.teardown_lanes(run_id=run_id, lanes=lanes)
    assert (result.ok, result.code) == (False, "SPEC009_RESIDUE_REMAINS")
    assert result.data["status"] == "FAILED"
    assert result.data["owned_residue_counts"]["audit_events"] == 1
    assert not n01.cleanup_verified(result.data) and not n03.cleanup_verified(result.data)
    assert adapter.active_run_ids == (run_id,)
    assert store._values


def test_read_consent_facts_returns_the_latest_active_record(settings) -> None:
    """T009: stored policy identifiers for N01-A3/N03-A2 come straight from consent_records."""
    db = FakeDatabase()
    db.tables["consent_records"] = []
    adapter = _adapter(settings, db)
    run_id = str(uuid4())
    lanes = adapter.seed_lanes(run_id=run_id, profile=N03)
    subject = adapter.subject_for(run_id=run_id, lane_id=N03LaneId.STALE)
    seen = []

    class _Rows(_Result):
        pass

    def execute(sql, params):
        if "FROM consent_records" in sql and "withdrawn_at IS NULL" in sql:
            seen.append((sql, params))
            from datetime import UTC, datetime

            return _Rows([{
                "consent_record_id": UUID(int=5), "policy_version": "2026-08-v1",
                "evidence_digest": "a" * 64, "accepted_at": datetime(2026, 10, 20, tzinfo=UTC),
            }])
        return FakeDatabase.execute(db, sql, params)

    db.execute = execute
    result = adapter.read_consent_facts(subject=subject)
    assert (result.ok, result.code) == (True, "SPEC009_CONSENT_FACTS_READ")
    assert result.data["record"] == {
        "consent_record_id": str(UUID(int=5)), "policy_version": "2026-08-v1",
        "evidence_digest": "a" * 64, "accepted_at": "2026-10-20T00:00:00+00:00",
    }
    sql, params = seen[0]
    assert "ORDER BY accepted_at DESC" in sql and "LIMIT 1" in sql
    assert str(params["invitation_id"]) == str(lanes[0].invitation_id)
    assert db.transactions[-1] == "connect"

    db.execute = lambda sql, params: _Result()
    empty = adapter.read_consent_facts(subject=subject)
    assert empty.ok and empty.data["record"] is None

    def broken(sql, params):
        raise RuntimeError("database unavailable")

    db.execute = broken
    failed = adapter.read_consent_facts(subject=subject)
    assert (failed.ok, failed.code) == (False, "SPEC009_CONSENT_FACTS_UNAVAILABLE")


def test_composition_shares_one_store_across_spec009_adapters(settings) -> None:
    adapters, _client = create_whyyou_adapter(settings)
    assert isinstance(adapters.spec009_seed, WhyYouSpec009SeedAdapter)
    assert isinstance(adapters.spec009_seed, Spec009SeedPort)
    store = adapters.spec009_seed.credentials
    assert adapters.applicant_browser.credentials is store
    assert adapters.spec009_consent.credentials is store
    assert adapters.n02_consent.credentials is not store
    assert adapters.spec009_consent is not adapters.n02_consent
