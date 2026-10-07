"""T063 — E-01/E-02 CLI contract (contracts/controlproof-cli-v4.md).

RED until T066. The runtime is the deterministic fake; `create_runtime` and settings are patched so nothing reaches
WhyYou.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from engine import cli
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters
from tests.fixtures.fake_spec004 import FakeSpec004Adapters, use_spec004_fixture

LIMITATIONS = ["FIXTURE_INTERVIEW_INPUT", "EXTERNAL_AI_BLOCKED", "FIXED_MODEL_SUBSTITUTE"]
PROFILES = {"E-01": "E01_CITATION_EVIDENCE_V1", "E-02": "E02_SCORING_FREEZE_V1"}


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    state = {"fake": FakeSpec004Adapters(removal_indicator="score_null")}
    run_root = tmp_path / "runs"

    def create(_settings, path):
        adapters, _ = make_adapters(spec004=state["fake"])
        use_spec004_fixture(adapters)
        return build_profile_runner(load(path), adapters, run_root, clock=FakeClock())

    monkeypatch.setattr(cli, "create_runtime", create)
    monkeypatch.setattr(
        cli, "_settings", lambda _args: SimpleNamespace(run_root=run_root, target_id="whyyou-local")
    )
    return SimpleNamespace(state=state, run_root=run_root)


def _call(capsys, *argv):
    code = cli.main(list(argv) + ["--json"])
    return code, json.loads(capsys.readouterr().out)


@pytest.mark.parametrize("scenario,count", [("E-01", 18), ("E-02", 16)])
def test_preflight_reports_capabilities_limitations_and_writes_nothing(
    runtime, capsys, scenario, count
) -> None:
    code, payload = _call(
        capsys, "preflight", scenario, "--profile", PROFILES[scenario], "--target", "whyyou-local"
    )
    assert code == 0, payload
    assert payload["capabilities"] == {"ready": count, "required": count}
    assert payload["limitations"] == LIMITATIONS
    assert payload["unverified_scope"] == ["AWS", "N-01", "N-03"]
    assert payload["model_fixture_id"] == "spec004-report-v1"
    assert payload["environment_kind"] == "LOCAL_EMULATED"
    if scenario == "E-02":
        assert payload["scoring_rule_source"] == {"status": "MATCH", "pinned_blobs": 2}
    assert not runtime.run_root.exists() or not any(runtime.run_root.iterdir())


def test_scoring_drift_is_exit_2_with_an_operator_action(runtime, capsys) -> None:
    runtime.state["fake"] = FakeSpec004Adapters(scoring_source_drift=True)
    code, payload = _call(
        capsys, "preflight", "E-02", "--profile", PROFILES["E-02"], "--target", "whyyou-local"
    )
    assert code == 2
    assert payload["operator_action"]
    assert payload["scoring_rule_source"]["status"] == "DRIFT"


@pytest.mark.parametrize(
    "options,exit_code",
    [
        ({"removal_indicator": "score_null"}, 0),
        ({}, 3),
        ({"removal_indicator": "score_null", "restore_mismatch": True}, 6),
    ],
)
def test_run_exit_codes_and_projection(runtime, capsys, options, exit_code) -> None:
    runtime.state["fake"] = FakeSpec004Adapters(**options)
    code, payload = _call(
        capsys, "run", "E-01", "--profile", PROFILES["E-01"], "--target", "whyyou-local"
    )
    assert code == exit_code, payload
    for key in ("citation_modes", "evidence_removal", "diagnostics", "limitations"):
        assert key in payload
    assert payload["change_injection_restore_status"] in {"SUCCEEDED", "FAILED"}
    # No automatic retest: exactly one Run bundle.
    bundles = [path for path in runtime.run_root.iterdir() if path.is_dir() and path.name != "locks"]
    assert len([path for path in bundles if (path / "run.json").exists()]) == 1


def test_show_and_verify_project_e02(runtime, capsys) -> None:
    runtime.state["fake"] = FakeSpec004Adapters()
    code, run = _call(capsys, "run", "E-02", "--profile", PROFILES["E-02"], "--target", "whyyou-local")
    assert code == 0, run
    code, shown = _call(capsys, "show", run["run_id"], "--run-root", str(runtime.run_root))
    assert code == 0
    for key in ("versions", "first_report_unchanged", "second_report_bound_to", "recompute"):
        assert key in shown
    code, verified = _call(capsys, "verify", run["run_id"], "--run-root", str(runtime.run_root))
    assert code == 0
    assert verified["profile_contract"] == "controlproof.bundle-profile.spec004.v1"
    assert verified["recompute_reexecution"] == "MATCH"
    assert verified["checked_evidence_requirements"] == [
        "EV4-01", "EV4-02", "EV4-04", "EV4-06", "EV4-07", "EV4-08", "EV4-09", "EV4-10",
    ]
    recompute = runtime.run_root / run["run_id"] / "recompute.json"
    document = json.loads(recompute.read_text(encoding="utf-8"))
    document["records"][0]["computed"]["score"] += 1
    recompute.write_text(json.dumps(document), encoding="utf-8")
    code, _ = _call(capsys, "verify", run["run_id"], "--run-root", str(runtime.run_root))
    assert code == 5
