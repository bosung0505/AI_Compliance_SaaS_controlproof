"""Spec 009 restore-failure recovery: owned-row cleanup script and the cleanup-confirm branch.

The blocked Run is a real RESTORE_FAILED N-03 Run on fakes; the database is the fake table store from
test_spec009_seed_adapter. The sealed bundle is never touched.
"""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from engine import cli, spec009_recovery
from engine.adapters.whyyou.n02_seed import _insert_row
from engine.executors.n03 import N03Executor
from engine.lifecycle import RestoreBlockStore
from engine.models import ExecutionProfile
from engine.scenario import load
from seeds.spec009_subjects import build_spec009_seed_plan
from tests.contract.test_spec009_seed_adapter import INVENTORY, FakeDatabase
from tests.fixtures.fake_spec009 import (
    COMPANY_ID,
    REVIEWER_ID,
    make_spec009_adapters,
    ready,
    spec009_target,
)

N03 = ExecutionProfile.N03_STALE_CONSENT_V1
N01 = ExecutionProfile.N01_NOTICE_V1
SUBJECT = "n03-stale-consent"


@pytest.fixture
def blocked(tmp_path, target_snapshot):
    target = spec009_target(target_snapshot)
    adapters, _backend, _store = make_spec009_adapters(tmp_path, target, teardown="RESIDUE")
    scenario = load("scenarios/N-03.yaml")
    run, _judgement, directory = N03Executor(scenario, adapters, tmp_path / "runs").execute(ready(scenario, target))
    assert run.state.value == "RESTORE_FAILED"
    settings = SimpleNamespace(
        run_root=tmp_path / "runs",
        whyyou_company_id=COMPANY_ID,
        whyyou_company_user_id=REVIEWER_ID,
        whyyou_database_url="postgresql+psycopg://local:local@localhost:5432/whyyou",
    )
    return settings, run, directory


def _hashes(directory):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()}


def _database(run_id, *, residue=False):
    """Seed rows of the Run plus product rows the failed teardown left behind."""
    db = FakeDatabase()
    plan = build_spec009_seed_plan(UUID(str(run_id)), profile=N03, company_id=UUID(COMPANY_ID), reviewer_id=UUID(REVIEWER_ID))
    with db.begin() as connection:
        for row in plan.rows:
            _insert_row(connection, row)
    stale = plan.subjects[0]
    db.tables["consent_records"].append(
        {"consent_record_id": str(uuid4()), "company_id": COMPANY_ID, "invitation_id": str(stale.invitation_id),
         "applicant_id": str(stale.applicant_id)}
    )
    db.tables["audit_events"].append(
        {"audit_event_id": str(uuid4()), "company_id": COMPANY_ID, "resource_id": str(stale.applicant_id)}
    )
    if residue:
        db.sticky = frozenset({"audit_events"})
    return db


def _recover(settings, run_id, db, profile=N03):
    return spec009_recovery.recover(
        settings, run_id=str(run_id), profile=profile,
        transaction_factory=db.begin, read_factory=db.connect, inventory=lambda _connection: INVENTORY,
    )


def test_recovery_removes_owned_rows_without_touching_the_bundle(blocked) -> None:
    settings, run, directory = blocked
    before = _hashes(directory)
    db = _database(run.run_id)
    evidence = _recover(settings, run.run_id, db)
    assert evidence["schema_version"] == "controlproof.spec009-recovery.v1"
    assert (evidence["run_id"], evidence["profile"], evidence["status"]) == (str(run.run_id), N03.value, "SUCCEEDED")
    assert set(evidence["owned_residue_counts"].values()) == {0}
    assert evidence["product_rows_removed"] == 2 and evidence["recovered_at"]
    assert all(not rows for rows in db.tables.values())
    assert _hashes(directory) == before
    again = _recover(settings, run.run_id, db)  # idempotent: nothing left to delete
    assert again["status"] == "SUCCEEDED" and again["product_rows_removed"] == 0


def test_recovery_reports_failed_when_rows_remain(blocked) -> None:
    settings, run, _directory = blocked
    evidence = _recover(settings, run.run_id, _database(run.run_id, residue=True))
    assert evidence["status"] == "FAILED" and evidence["owned_residue_counts"]["audit_events"] == 1


def test_recovery_refuses_without_matching_block_or_profile(blocked, tmp_path) -> None:
    settings, run, _directory = blocked
    db = _database(run.run_id)
    with pytest.raises(spec009_recovery.RecoveryError, match="SPEC009_RECOVERY_BLOCK_MISMATCH"):
        _recover(settings, uuid4(), db)
    with pytest.raises(spec009_recovery.RecoveryError, match="SPEC009_RECOVERY_BLOCK_MISSING"):
        _recover(settings, run.run_id, db, profile=N01)
    empty = SimpleNamespace(**{**vars(settings), "run_root": tmp_path / "elsewhere"})
    with pytest.raises(spec009_recovery.RecoveryError, match="SPEC009_RECOVERY_BLOCK_MISSING"):
        _recover(empty, run.run_id, db)
    # A block that points at a Run of the other profile is refused through the sealed run.json.
    RestoreBlockStore(settings.run_root).block_run_id("whyyou-local", "n01-notice", run.run_id)
    with pytest.raises(spec009_recovery.RecoveryError, match="SPEC009_RECOVERY_PROFILE_MISMATCH"):
        _recover(settings, run.run_id, db, profile=N01)


def test_script_writes_the_evidence_file(blocked, tmp_path, monkeypatch) -> None:
    settings, run, _directory = blocked
    from scripts import spec009_recover

    calls = []
    monkeypatch.setattr(spec009_recover, "Settings", SimpleNamespace(from_env=lambda: settings))
    monkeypatch.setattr(
        spec009_recover.spec009_recovery, "recover",
        lambda _settings, **kwargs: calls.append(kwargs) or {"status": "SUCCEEDED", "run_id": kwargs["run_id"]},
    )
    out = tmp_path / "evidence" / "n03-recovery.json"
    code = spec009_recover.main(["--run-id", str(run.run_id), "--profile", N03.value, "--out", str(out)])
    assert code == 0 and calls == [{"run_id": str(run.run_id), "profile": N03}]
    assert json.loads(out.read_text(encoding="utf-8"))["status"] == "SUCCEEDED"


def _confirm(settings, run, tmp_path, monkeypatch, *, counts, evidence_overrides=None):
    evidence = {
        "schema_version": "controlproof.spec009-recovery.v1",
        "run_id": str(run.run_id),
        "profile": N03.value,
        "status": "SUCCEEDED",
        "owned_residue_counts": {},
        "product_rows_removed": 2,
        "recovered_at": "2026-10-20T00:00:00+00:00",
    } | (evidence_overrides or {})
    path = tmp_path / "n03-recovery.json"
    path.write_text(json.dumps(evidence), encoding="utf-8")
    calls = []
    monkeypatch.setattr(cli, "_settings", lambda _args: settings)
    monkeypatch.setattr(cli, "create_runtime", lambda *_args: pytest.fail("no runtime for Spec 009 cleanup"))
    monkeypatch.setattr(
        spec009_recovery, "recount", lambda _settings, **kwargs: calls.append(kwargs) or counts
    )
    args = ["cleanup-confirm", "--target", "whyyou-local", "--subject", SUBJECT, "--evidence", str(path), "--json"]
    return cli.main(args), calls


def test_cleanup_confirm_releases_the_block_after_a_zero_recount(blocked, tmp_path, monkeypatch, capsys) -> None:
    settings, run, directory = blocked
    before = _hashes(directory)
    blocks = RestoreBlockStore(settings.run_root)
    code, calls = _confirm(settings, run, tmp_path, monkeypatch, counts={"audit_events": 0, "invitations": 0})
    output = json.loads(capsys.readouterr().out)
    assert code == 0 and output["blocked_run_id"] == str(run.run_id)
    assert calls == [{"run_id": str(run.run_id), "profile": N03}]
    assert not blocks.blocked("whyyou-local", SUBJECT)
    assert _hashes(directory) == before


def test_cleanup_confirm_keeps_the_block_when_rows_remain(blocked, tmp_path, monkeypatch, capsys) -> None:
    settings, run, _directory = blocked
    code, _calls = _confirm(settings, run, tmp_path, monkeypatch, counts={"audit_events": 1})
    output = json.loads(capsys.readouterr().out)
    assert code != 0 and output["error"] == "SPEC009_SAFE_STATE_NOT_CONFIRMED"
    assert RestoreBlockStore(settings.run_root).blocked("whyyou-local", SUBJECT)


@pytest.mark.parametrize(
    "overrides",
    [{"schema_version": "other"}, {"run_id": str(uuid4())}, {"profile": N01.value}],
)
def test_cleanup_confirm_rejects_foreign_evidence(blocked, tmp_path, monkeypatch, capsys, overrides) -> None:
    settings, run, _directory = blocked
    code, calls = _confirm(settings, run, tmp_path, monkeypatch, counts={}, evidence_overrides=overrides)
    output = json.loads(capsys.readouterr().out)
    assert code != 0 and output["error"] == "SPEC009_CLEANUP_EVIDENCE_INVALID"
    assert calls == []
    assert RestoreBlockStore(settings.run_root).blocked("whyyou-local", SUBJECT)
