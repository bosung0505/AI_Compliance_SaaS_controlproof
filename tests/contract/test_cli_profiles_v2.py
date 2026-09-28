from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from engine import cli
from engine.models import ExecutionProfile, RunState, Verdict
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters


def _runner(tmp_path, profile: ExecutionProfile, **adapter_options):
    scenario_file = {
        ExecutionProfile.H03_DLQ_V2: "scenarios/H-03-DLQ.yaml",
        ExecutionProfile.E03_BEFORE_V2: "scenarios/E-03-BEFORE.yaml",
        ExecutionProfile.E03_AFTER_V2: "scenarios/E-03-AFTER.yaml",
    }[profile]
    if profile is ExecutionProfile.E03_AFTER_V2:
        adapter_options.setdefault("injected_reporting_present", True)
    adapters, _ = make_adapters(**adapter_options)
    return build_profile_runner(
        load(scenario_file), adapters, tmp_path, clock=FakeClock()
    )


def test_e03_requires_explicit_profile_and_does_not_guess_variant(capsys):
    assert cli.main(["preflight", "E-03", "--target", "whyyou-local", "--json"]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["schema_version"] == "controlproof.cli.v1"
    assert output["error"] == "PROFILE_REQUIRED"


def test_v2_run_keeps_v1_envelope_and_adds_profile_scope(
    tmp_path, monkeypatch, capsys
):
    runner = _runner(
        tmp_path,
        ExecutionProfile.E03_AFTER_V2,
        dlq_presence="ABSENT",
    )
    monkeypatch.setattr(cli, "_settings", lambda _args: SimpleNamespace(run_root=tmp_path))
    monkeypatch.setattr(cli, "create_runtime", lambda _settings, _path: runner)

    exit_code = cli.main(
        [
            "run",
            "E-03",
            "--profile",
            "E03_AFTER_V2",
            "--target",
            "whyyou-local",
            "--json",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["schema_version"] == "controlproof.cli.v1"
    assert output["projection_schema_version"] == "controlproof.review.v1"
    assert output["execution_profile"] == "E03_AFTER_V2"
    assert output["fault_variant"] == "AFTER_RESULT_DURABLE_BEFORE_COMPLETION"
    assert output["claim_scope"] == "EXECUTED_SCENARIO_AND_EVIDENCE_ONLY"
    assert output["environment_kind"] == "LOCAL_EMULATED"
    assert output["aws_deployment_status"] == "NOT_RUN"
    assert output["evaluated_assertions"] == ["E03-A1", "E03-A5", "E03-A6", "E03-A8"]
    assert output["remaining_variant_coverage"] == [
        "E03-A2",
        "E03-A3",
        "E03-A4",
        "E03-A7",
    ]
    assert "certif" not in json.dumps(output).casefold()


def test_verify_projects_profile_contract_and_exact_evidence_set(tmp_path, capsys):
    runner = _runner(
        tmp_path,
        ExecutionProfile.E03_AFTER_V2,
        dlq_presence="ABSENT",
    )
    bundle = runner.execute(runner.preflight("whyyou-local"))[2]

    assert cli.main(["verify", str(bundle), "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["execution_profile"] == "E03_AFTER_V2"
    assert output["profile_contract"] == "controlproof.bundle-profile.spec002.v1"
    assert output["checked_evidence_requirements"] == [
        "EV2-01",
        "EV2-02",
        "EV2-03",
        "EV2-04",
        "EV2-09",
        "EV2-10",
        "EV2-12",
    ]


def test_exit_codes_stay_stable_and_semantic_overrides_are_not_options():
    assert cli._run_exit(RunState.COMPLETED, Verdict.PASS) == 0
    assert cli._run_exit(RunState.COMPLETED, Verdict.FAIL) == 3
    assert cli._run_exit(RunState.COMPLETED, Verdict.INCONCLUSIVE) == 4
    assert cli._run_exit(RunState.RESTORE_FAILED, Verdict.INCONCLUSIVE) == 6
    with pytest.raises(SystemExit):
        cli._parser().parse_args(
            [
                "run",
                "E-03",
                "--profile",
                "E03_BEFORE_V2",
                "--target",
                "whyyou-local",
                "--fault-variant",
                "AFTER_RESULT_DURABLE_BEFORE_COMPLETION",
            ]
        )
