from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from engine.models import (
    Observation,
    Phase,
    Presence,
    Run,
    Source,
    TargetSnapshot,
    TargetSourceKind,
)

MODEL_FIXTURE_ID = "h03-report-v1"
MODEL_FIXTURE_DIGEST = hashlib.sha256(b"controlproof:h03-report-v1").hexdigest()


@pytest.fixture(autouse=True)
def deterministic_environment(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Keep all tests local, isolated, deterministic, and credential-free."""
    run_root = tmp_path / "runs"
    fault_root = tmp_path / "faults"
    monkeypatch.setenv("CONTROLPROOF_RUN_ROOT", str(run_root))
    monkeypatch.setenv("CONTROLPROOF_FAULT_ROOT", str(fault_root))
    monkeypatch.setenv("CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED", "true")
    monkeypatch.setenv("CONTROLPROOF_MODEL_FIXTURE_ID", MODEL_FIXTURE_ID)
    monkeypatch.setenv("CONTROLPROOF_MODEL_FIXTURE_DIGEST", MODEL_FIXTURE_DIGEST)
    monkeypatch.setenv("NO_PROXY", "*")
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    run_root.mkdir()
    fault_root.mkdir()
    return {"run_root": run_root, "fault_root": fault_root}


@pytest.fixture
def target_snapshot():
    digest = "a" * 64
    return TargetSnapshot(
        target_id="whyyou-local",
        source_kind=TargetSourceKind.GIT_WORKTREE,
        git_commit_sha="b" * 40,
        git_dirty=False,
        openapi_digest=digest,
        schema_migration_head="head-v1",
        schema_signature_digest=digest,
        model_fixture_id=MODEL_FIXTURE_ID,
        model_fixture_digest=MODEL_FIXTURE_DIGEST,
        captured_at=datetime(2026, 9, 24, tzinfo=UTC),
    )


@pytest.fixture
def run_factory(target_snapshot):
    def create(**updates):
        data = {
            "scenario_id": "H-03",
            "scenario_version": "1.0.0",
            "scenario_digest": "c" * 64,
            "target_id": "whyyou-local",
            "target_version": target_snapshot.target_version,
            "model_fixture_id": MODEL_FIXTURE_ID,
            "model_fixture_digest": MODEL_FIXTURE_DIGEST,
        }
        data.update(updates)
        return Run(**data)

    return create


@pytest.fixture
def observation_factory():
    def create(**updates):
        data = {
            "run_id": uuid4(),
            "subject_ref": "candidate-01",
            "phase": Phase.BASELINE,
            "step_id": "fixture",
            "attempt": 1,
            "key": "fixture.key",
            "presence": Presence.PRESENT,
            "value": True,
            "source_type": Source.SYSTEM,
            "source_ref": "fixture",
        }
        data.update(updates)
        return Observation(**data)

    return create
