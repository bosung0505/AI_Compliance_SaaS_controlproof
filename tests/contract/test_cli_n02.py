"""N-02 CLI contracts use synthetic runners and never contact WhyYou."""

from __future__ import annotations

import json
from types import SimpleNamespace

from engine import cli
from engine.models import Judgement, Run
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters
from tests.fixtures.n02_review_bundle import make_review_bundle, reseal_file

PROFILE = "N02_CONSENT_ORDER_V1"
EVIDENCE = [f"EV3-{index:02d}" for index in range(1, 11)]


def _invoke(capsys, argv):
    code = cli.main(argv)
    return code, json.loads(capsys.readouterr().out)


def test_preflight_non_ready_is_actionable_and_side_effect_free(
    tmp_path, monkeypatch, capsys
) -> None:
    adapters, _ = make_adapters(target_exists=False)
    root = tmp_path / "n02-runs"
    runner = build_profile_runner(load("scenarios/N-02.yaml"), adapters, root, clock=FakeClock())
    monkeypatch.setattr(cli, "_settings", lambda _args: SimpleNamespace(run_root=root))
    monkeypatch.setattr(cli, "create_runtime", lambda _settings, _path: runner)
    before = {path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*")}

    code, output = _invoke(capsys, ["preflight", "N-02", "--profile", PROFILE, "--target", "whyyou-local", "--json"])
    after = {path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*")}

    assert code == 2
    assert output["schema_version"] == "controlproof.cli.v1"
    assert output["readiness"] != "READY"
    assert output["operator_action"].strip()
    assert "local-test-token" not in json.dumps(output)
    assert output["claim_scope"] == "EXECUTED_SCENARIO_AND_EVIDENCE_ONLY"
    assert after == before


def test_ready_preflight_lists_only_read_only_paths(tmp_path, monkeypatch, capsys) -> None:
    adapters, _ = make_adapters()
    root = tmp_path / "n02-runs"
    runner = build_profile_runner(load("scenarios/N-02.yaml"), adapters, root, clock=FakeClock())
    monkeypatch.setattr(cli, "_settings", lambda _args: SimpleNamespace(run_root=root))
    monkeypatch.setattr(cli, "create_runtime", lambda _settings, _path: runner)

    code, output = _invoke(capsys, ["preflight", "N-02", "--profile", PROFILE, "--target", "whyyou-local", "--json"])

    assert code == 0
    assert output["readiness"] == "READY"
    assert set(output["protected_paths"]) == {"DOCUMENT_ANALYSIS", "RECORDING", "AI_ASSESSMENT"}
    assert "policy_snapshot_digest" not in output
    assert "lane_manifest_digest" not in output
    assert "path_capability_digest" not in output
    assert not root.exists()


def test_run_projects_all_assertions_paths_and_scope_without_automatic_retest(
    tmp_path, run_factory, target_snapshot, monkeypatch, capsys
) -> None:
    bundle = make_review_bundle(tmp_path, run_factory, target_snapshot)
    run = Run.model_validate(json.loads((bundle / "run.json").read_text(encoding="utf-8")))
    judgement = Judgement.model_validate(json.loads((bundle / "judgement.json").read_text(encoding="utf-8")))
    adapters, _ = make_adapters()
    runner = build_profile_runner(load("scenarios/N-02.yaml"), adapters, tmp_path, clock=FakeClock())
    runner.execute = lambda _readiness, **_kwargs: (run, judgement, bundle)
    monkeypatch.setattr(cli, "_settings", lambda _args: SimpleNamespace(run_root=tmp_path))
    monkeypatch.setattr(cli, "create_runtime", lambda _settings, _path: runner)
    before = {path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*")}

    code, output = _invoke(capsys, ["run", "N-02", "--profile", PROFILE, "--target", "whyyou-local", "--json"])
    after = {path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*")}

    assert code == 4
    assert output["schema_version"] == "controlproof.cli.v1"
    assert output["evaluated_assertions"] == [f"N02-A{index}" for index in range(1, 8)]
    assert set(output["path_results"]) == {"DOCUMENT_ANALYSIS", "RECORDING", "AI_ASSESSMENT"}
    assert output["environment_kind"] == "LOCAL_EMULATED"
    assert output["aws_deployment_status"] == "NOT_RUN"
    assert set(output["unverified_scope"]) == {"AWS", "N-01", "N-03"}
    assert output["policy_snapshot_digest"] == run.policy_snapshot_digest
    assert output["lane_manifest_digest"] == run.lane_manifest_digest
    assert output["path_capability_digest"] == run.path_capability_digest
    assert after == before


def test_show_exposes_n02_review(
    tmp_path, run_factory, target_snapshot, capsys
) -> None:
    bundle = make_review_bundle(tmp_path, run_factory, target_snapshot)
    show_code, show = _invoke(capsys, ["show", str(bundle), "--json"])

    assert show_code == 0
    assert show["execution_profile"] == PROFILE
    assert show["evaluated_assertions"] == [f"N02-A{index}" for index in range(1, 8)]
    assert "n02_review" in show


def test_verify_reports_ev3_contract_and_rejects_unreadable_facts(
    tmp_path, run_factory, target_snapshot, capsys
) -> None:
    bundle = make_review_bundle(tmp_path, run_factory, target_snapshot)
    judgement = json.loads((bundle / "judgement.json").read_text(encoding="utf-8"))
    judgement["verdict"] = "PASS"
    judgement["reason_code"] = None
    for assertion in judgement["assertion_results"]:
        assertion["status"] = "PASS"
        assertion["reason_code"] = None
    reseal_file(bundle, "judgement.json", judgement)
    reseal_file(bundle, "assertions.json", judgement["assertion_results"])
    verify_code, verify = _invoke(capsys, ["verify", str(bundle), "--json"])

    assert verify["profile_contract"] == "controlproof.bundle-profile.spec003.v1"
    assert verify["checked_evidence_requirements"] == EVIDENCE
    assert verify_code == 5
    assert verify["bundle_status"] == "INVALID"
