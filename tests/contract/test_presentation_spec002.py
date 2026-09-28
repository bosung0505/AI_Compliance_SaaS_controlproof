from __future__ import annotations

from engine.models import ExecutionProfile
from engine.presentation import load_bundle_summary, render_human
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters


def _bundle(tmp_path, scenario_file: str, **adapter_options):
    if scenario_file.endswith("E-03-AFTER.yaml"):
        adapter_options.setdefault("injected_reporting_present", True)
    adapters, _ = make_adapters(**adapter_options)
    runner = build_profile_runner(
        load(scenario_file), adapters, tmp_path, clock=FakeClock()
    )
    return runner.execute(runner.preflight("whyyou-local"))[2]


def test_h03_presentation_explains_failure_route_and_decision_path_coverage(tmp_path):
    bundle = _bundle(
        tmp_path,
        "scenarios/H-03-DLQ.yaml",
        report_api_status="failed",
    )
    summary = load_bundle_summary(bundle)

    assert summary["execution_profile"] == ExecutionProfile.H03_DLQ_V2.value
    assert summary["scenario_result"]["scenario_id"] == "H-03"
    assert summary["failure_route"]["route_type"] == "INFRASTRUCTURE_DLQ"
    assert set(summary["decision_path_coverage"]) == {
        "FINAL_DECISION",
        "BATCH_MOVE_FINAL_ACCEPT",
        "BATCH_MOVE_FINAL_REJECT",
    }
    assert summary["implementation_status"] == "IMPLEMENTED"
    assert summary["cloud_verification"]["aws_deployment_status"] == "NOT_RUN"
    assert summary["claim_scope"] == "EXECUTED_SCENARIO_AND_EVIDENCE_ONLY"


def test_e03_presentation_keeps_variant_verdict_and_effect_differences_separate(tmp_path):
    bundle = _bundle(
        tmp_path,
        "scenarios/E-03-AFTER.yaml",
        dlq_presence="ABSENT",
    )
    summary = load_bundle_summary(bundle)
    human = render_human(summary)

    assert summary["scenario_result"] == {
        "scenario_id": "E-03",
        "execution_profile": "E03_AFTER_V2",
        "verdict": "PASS",
    }
    assert summary["evaluated_assertions"] == ["E03-A1", "E03-A5", "E03-A6", "E03-A8"]
    assert summary["remaining_variant_coverage"] == [
        "E03-A2",
        "E03-A3",
        "E03-A4",
        "E03-A7",
    ]
    assert summary["effect_differences"]["changed"] is False
    assert summary["environment_restore_status"] == "SUCCEEDED"
    assert summary["unverified_scope"]
    assert "법적 준수 전체를 인증하거나 보증하지 않습니다" in human
