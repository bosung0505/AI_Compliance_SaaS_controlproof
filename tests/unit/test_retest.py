from __future__ import annotations

import json
from uuid import uuid4

import pytest

from engine.models import TargetSnapshot
from engine.retest import RetestError, assert_parent_unchanged, prepare_retest
from engine.runner import RunOrchestrator
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters


def _parent(tmp_path):
    adapters, _ = make_adapters()
    runner = RunOrchestrator(load("scenarios/H-03.yaml"), adapters, tmp_path, clock=FakeClock())
    run, _, bundle = runner.execute(runner.preflight("whyyou-local"))
    target = TargetSnapshot.model_validate(
        json.loads((bundle / "target.snapshot.json").read_text(encoding="utf-8"))
    )
    return run, bundle, target


def test_prepare_retest_uses_new_child_and_identity_only_target_diff(tmp_path):
    parent, bundle, target = _parent(tmp_path)
    child_id = uuid4()
    changed = target.model_copy(update={"openapi_digest": "d" * 64, "target_version": None})
    changed = TargetSnapshot.model_validate(changed.model_dump(mode="python"))
    original_manifest = (bundle / "manifest.json").read_bytes()
    loaded, digest, records = prepare_retest(
        bundle,
        child_run_id=child_id,
        child_target=changed,
        child_scenario_version=parent.scenario_version,
        child_scenario_digest=parent.scenario_digest,
    )
    assert loaded.run_id == parent.run_id
    assert records["link"]["child_run_id"] == str(child_id)
    assert [item["path"] for item in records["diff"]["target"]["changed_fields"]] == [
        "openapi_digest"
    ]
    assert (bundle / "manifest.json").read_bytes() == original_manifest
    assert_parent_unchanged(bundle, digest)


def test_tampered_parent_is_rejected(tmp_path):
    _, bundle, target = _parent(tmp_path)
    next((bundle / "artifacts").glob("*.json")).write_text("tampered", encoding="utf-8")
    with pytest.raises(RetestError, match="integrity"):
        prepare_retest(
            bundle,
            child_run_id=uuid4(),
            child_target=target,
            child_scenario_version="1.0.0",
            child_scenario_digest="a" * 64,
        )
