from __future__ import annotations

import pytest

from engine.evidence import verify_bundle
from engine.models import Verdict
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters


def _verdict(tmp_path, scenario_file: str, **adapter_options):
    if scenario_file.endswith("E-03-AFTER.yaml"):
        adapter_options.setdefault("injected_reporting_present", True)
    adapters, _ = make_adapters(**adapter_options)
    runner = build_profile_runner(
        load(scenario_file), adapters, tmp_path, clock=FakeClock()
    )
    run, judgement, bundle = runner.execute(runner.preflight("whyyou-local"))
    return run, judgement.verdict, bundle


@pytest.mark.parametrize(
    ("h03_options", "e03_file", "e03_options", "expected"),
    [
        ({}, "scenarios/E-03-BEFORE.yaml", {"decision_path_accepted": True}, ("FAIL", "PASS")),
        (
            {"report_api_status": "failed"},
            "scenarios/E-03-BEFORE.yaml",
            {},
            ("PASS", "FAIL"),
        ),
        (
            {"report_api_status": "failed"},
            "scenarios/E-03-AFTER.yaml",
            {"after_effect": False, "dlq_presence": "ABSENT"},
            ("PASS", "INCONCLUSIVE"),
        ),
        (
            {"report_api_status": "failed"},
            "scenarios/E-03-AFTER.yaml",
            {"dlq_presence": "ABSENT"},
            ("PASS", "PASS"),
        ),
    ],
)
def test_h03_and_e03_verdicts_are_independent(
    tmp_path, h03_options, e03_file, e03_options, expected
):
    _, h03, h03_bundle = _verdict(
        tmp_path, "scenarios/H-03-DLQ.yaml", **h03_options
    )
    _, e03, e03_bundle = _verdict(tmp_path, e03_file, **e03_options)

    assert (h03.value, e03.value) == expected
    for verdict, bundle in ((h03, h03_bundle), (e03, e03_bundle)):
        result = verify_bundle(bundle)
        assert result["bundle_status"] == "VERIFIED"
        if verdict is Verdict.PASS:
            assert result["missing_files"] == []


def test_required_evidence_tamper_never_remains_pass(tmp_path):
    _, verdict, bundle = _verdict(
        tmp_path,
        "scenarios/E-03-AFTER.yaml",
        dlq_presence="ABSENT",
    )
    assert verdict is Verdict.PASS
    assert verify_bundle(bundle)["bundle_status"] == "VERIFIED"
    (bundle / "effects.jsonl").write_text("{}\n", encoding="utf-8")
    assert verify_bundle(bundle)["bundle_status"] == "INVALID"
