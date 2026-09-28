from __future__ import annotations

import json
from uuid import uuid4

import pytest

from engine.evidence import verify_bundle
from engine.models import ExecutionProfile
from engine.retest import RetestError, assert_parent_unchanged, prepare_retest
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters


def _runner(tmp_path, **adapter_options):
    adapter_options.setdefault("injected_reporting_present", True)
    adapters, _ = make_adapters(**adapter_options)
    return build_profile_runner(
        load("scenarios/E-03-AFTER.yaml"), adapters, tmp_path, clock=FakeClock()
    )


def test_retest_inherits_profile_fault_and_preserves_parent_and_origin(tmp_path):
    parent_runner = _runner(tmp_path, dlq_presence="ABSENT")
    parent, _, parent_bundle = parent_runner.execute(
        parent_runner.preflight("whyyou-local")
    )
    parent_bytes = (parent_bundle / "manifest.json").read_bytes()

    child_runner = _runner(tmp_path, dlq_presence="ABSENT")
    readiness = child_runner.preflight("whyyou-local")
    child_id = uuid4()
    child_environment = child_runner.adapters.environment.capture_environment()
    child_queue = child_runner.adapters.queue.capture_topology()
    inherited, parent_digest, records = prepare_retest(
        parent_bundle,
        child_run_id=child_id,
        child_target=readiness.target_snapshot,
        child_scenario_version=child_runner.scenario.version,
        child_scenario_digest=child_runner.scenario.snapshot().digest,
        child_profile=child_runner.scenario.execution_profile,
        child_fault_variant=child_runner.scenario.fault_variant,
        child_environment=child_environment,
        child_queue=child_queue,
    )
    child, _, child_bundle = child_runner.execute(
        readiness,
        parent_run_id=inherited.run_id,
        retest_records=records,
        run_id=child_id,
    )

    assert child.run_id != parent.run_id
    assert child.execution_profile is ExecutionProfile.E03_AFTER_V2
    assert child.fault_variant == parent.fault_variant
    assert (parent_bundle / "manifest.json").read_bytes() == parent_bytes
    assert_parent_unchanged(parent_bundle, parent_digest)
    diff = json.loads((child_bundle / "retest-diff.json").read_text(encoding="utf-8"))
    assert diff["execution_profile"]["changed"] is False
    assert diff["fault_condition"]["changed"] is False
    assert diff["environment"]["changed"] is False
    assert diff["queue_topology"]["changed"] is False
    assert verify_bundle(child_bundle)["bundle_status"] == "VERIFIED"

    next((parent_bundle / "artifacts").glob("*.json")).write_text("{}", encoding="utf-8")
    assert verify_bundle(child_bundle)["bundle_status"] == "INVALID"


def test_retest_rejects_restore_failed_parent(tmp_path):
    runner = _runner(tmp_path, dlq_presence="ABSENT", restore=False)
    parent, _, bundle = runner.execute(runner.preflight("whyyou-local"))
    assert parent.manual_cleanup_required is True
    with pytest.raises(RetestError, match="safe cleanup"):
        prepare_retest(
            bundle,
            child_run_id=uuid4(),
            child_target=runner.preflight("whyyou-local").target_snapshot,
            child_scenario_version=runner.scenario.version,
            child_scenario_digest=runner.scenario.snapshot().digest,
            child_profile=runner.scenario.execution_profile,
            child_fault_variant=runner.scenario.fault_variant,
            child_environment=runner.adapters.environment.capture_environment(),
            child_queue=runner.adapters.queue.capture_topology(),
        )
