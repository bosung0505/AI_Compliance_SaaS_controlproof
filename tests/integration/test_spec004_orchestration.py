"""T068 — complete deterministic E-01 and E-02 Runs: sealed, verified, projected (SC-001~SC-004).

Each Run is sealed and verified by the executor; this re-verifies independently and checks the review projection
reads the same facts as the judgement.
"""

from __future__ import annotations

import pytest

from engine.evidence import verify_bundle
from engine.presentation import load_bundle_summary
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters
from tests.fixtures.fake_spec004 import FakeSpec004Adapters, use_spec004_fixture


@pytest.mark.parametrize(
    "scenario,options,expected",
    [
        ("E-01", {"removal_indicator": "score_null"}, "PASS"),
        ("E-01", {}, "FAIL"),
        ("E-02", {}, "PASS"),
        ("E-02", {"stored_overall_offset": 1}, "FAIL"),
    ],
)
def test_complete_run_is_sealed_verified_and_projected(tmp_path, scenario, options, expected) -> None:
    adapters, _ = make_adapters(spec004=FakeSpec004Adapters(**options))
    use_spec004_fixture(adapters)
    runner = build_profile_runner(load(f"scenarios/{scenario}.yaml"), adapters, tmp_path, clock=FakeClock())
    run, judgement, bundle = runner.execute(runner.preflight("whyyou-local"))
    verified = verify_bundle(bundle)
    assert verified["bundle_status"] == "VERIFIED", verified
    assert verified["cross_reference_errors"] == [] and verified["redaction_violations"] == []
    summary = load_bundle_summary(bundle)
    assert summary["verdict"] == judgement.verdict.value == expected
    assert summary["run_id"] == str(run.run_id)
    assert summary["execution_profile"] == run.execution_profile.value
    assert summary["failed_assertions"] == [
        item.assertion_id for item in judgement.assertion_results if item.status.value == "FAIL"
    ]
    timing = runner.timing_report()
    assert timing["environment_restore_within_deadline"] is True
    assert timing["bundle_verify_within_budget"] is True
