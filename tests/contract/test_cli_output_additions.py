"""T006 — CLI output additions (contracts/cli-output-additions.md; FR-035, SC-010, R-004, R-009, R-010).

RED until T010, T013, T014. Exit-code values never change (D-018 additional decision 1).

Existing expectations reviewed for change (T006 note): `tests/unit/test_redaction_security.py` asserts `redact()` of a
`bundle_path` value keeps `[USER_ROOT]`; `redact()` itself is unchanged, so that test stays as is. No other existing CLI
test asserts the `bundle_path` value, the not-ready `run` command name or a traceback-based H-03 cleanup failure.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from engine import cli
from engine.models import ImplementationStatus, ReadinessStatus, ScenarioReadiness
from engine.runner import RunOrchestrator
from engine.scenario import load
from tests.fixtures import web_bundles as wb
from tests.fixtures.fake_adapters import FakeClock, make_adapters

TARGET = "whyyou-local"


def _call(capsys, argv):
    code = cli.main(argv)
    return code, json.loads(capsys.readouterr().out)


def _real_runtime(monkeypatch, run_root, **options):
    adapters, _ = make_adapters(**options)

    def create(_settings, path):
        return RunOrchestrator(load(path), adapters, run_root, clock=FakeClock())

    monkeypatch.setattr(cli, "create_runtime", create)
    monkeypatch.setattr(
        cli, "_settings", lambda _args: SimpleNamespace(run_root=run_root, target_id=TARGET)
    )


def _not_ready_runtime(monkeypatch, run_root):
    scenario = load("scenarios/H-03.yaml")
    readiness = ScenarioReadiness(
        scenario_id=scenario.scenario_id,
        scenario_version=scenario.version,
        target_id=TARGET,
        implementation_status=ImplementationStatus.IMPLEMENTED,
        status=ReadinessStatus.RUNNER_NOT_READY,
        checks=(),
        operator_action="repair fixture",
    )
    runtime = SimpleNamespace(scenario=scenario, preflight=lambda _t: readiness)
    monkeypatch.setattr(cli, "create_runtime", lambda _s, _p: runtime)
    monkeypatch.setattr(
        cli, "_settings", lambda _args: SimpleNamespace(run_root=run_root, target_id=TARGET)
    )


@pytest.mark.parametrize(
    "options,exit_code", [({}, 0), (wb.CASES["fail"], 3), (wb.CASES["missing"], 4), (wb.CASES["restore_failed"], 6)]
)
def test_run_result_kind_bundle_path_and_unchanged_exit_codes(
    tmp_path, monkeypatch, capsys, options, exit_code
) -> None:
    root = tmp_path / "runs"
    _real_runtime(monkeypatch, root, **options)
    code, payload = _call(capsys, ["run", "H-03", "--target", TARGET, "--json"])
    assert code == exit_code
    assert payload["result_kind"] == "RUN"
    assert payload["bundle_path"] == f"<run_root>/{payload['run_id']}"


def test_preflight_and_not_ready_run_and_retest(tmp_path, monkeypatch, capsys) -> None:
    root = tmp_path / "runs"
    parent = wb.h03_case(root, "fail")
    _not_ready_runtime(monkeypatch, root)
    code, payload = _call(capsys, ["preflight", "H-03", "--target", TARGET, "--json"])
    assert (code, payload["command"], payload["result_kind"]) == (2, "preflight", "READINESS")
    code, payload = _call(capsys, ["run", "H-03", "--target", TARGET, "--json"])
    assert (code, payload["command"], payload["result_kind"]) == (2, "run", "READINESS")
    code, payload = _call(capsys, ["retest", parent.run_id, "--target", TARGET, "--json"])
    assert (code, payload["command"], payload["result_kind"]) == (2, "retest", "READINESS")


def test_show_verify_result_kinds_and_errors(tmp_path, monkeypatch, capsys) -> None:
    root = tmp_path / "runs"
    built = wb.h03_case(root, "pass")
    code, payload = _call(capsys, ["show", built.run_id, "--run-root", str(root), "--json"])
    assert (code, payload["result_kind"]) == (0, "PROJECTION")
    code, payload = _call(capsys, ["verify", built.run_id, "--run-root", str(root), "--json"])
    assert (code, payload["result_kind"]) == (0, "VERIFY")
    wb.tampered(built)
    code, payload = _call(capsys, ["verify", built.run_id, "--run-root", str(root), "--json"])
    assert (code, payload["result_kind"]) == (5, "VERIFY")
    code, payload = _call(capsys, ["show", "00000000-0000-4000-8000-000000000000", "--run-root", str(root), "--json"])
    assert (code, payload["result_kind"], payload["error_kind"]) == (1, "ERROR", "NOT_FOUND")
    code, payload = _call(capsys, ["preflight", "E-03", "--target", TARGET, "--json"])
    assert (code, payload["result_kind"], payload["error_kind"], payload["error"]) == (
        1,
        "ERROR",
        "CONTRACT",
        "PROFILE_REQUIRED",
    )


def test_argument_error_with_json_is_a_json_usage_error_exit_two(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["preflight", "--json"])
    assert exc.value.code == 2
    payload = json.loads(capsys.readouterr().out)
    assert (payload["result_kind"], payload["error_kind"], payload["command"]) == (
        "ERROR",
        "USAGE",
        "preflight",
    )


def test_h03_cleanup_safety_failure_is_json_not_traceback(tmp_path, monkeypatch, capsys) -> None:
    root = tmp_path / "runs"
    wb.h03_case(root, "restore_failed")
    evidence = tmp_path / "cleanup.json"
    evidence.write_text("{}", encoding="utf-8")
    runtime = SimpleNamespace(
        adapters=SimpleNamespace(fault=SimpleNamespace(target_safe=lambda **_k: False))
    )
    monkeypatch.setattr(cli, "create_runtime", lambda _s, _p: runtime)
    monkeypatch.setattr(cli, "_settings", lambda _args: SimpleNamespace(run_root=root))
    code, payload = _call(
        capsys,
        ["cleanup-confirm", "--target", TARGET, "--subject", "candidate-01", "--evidence", str(evidence), "--json"],
    )
    assert code == 1
    assert (payload["result_kind"], payload["error_kind"], payload["error"]) == (
        "ERROR",
        "CONTRACT",
        "H03_SAFE_STATE_NOT_CONFIRMED",
    )


def test_cleanup_success_result_kind(tmp_path, monkeypatch, capsys) -> None:
    root = tmp_path / "runs"
    wb.h03_case(root, "restore_failed")
    evidence = tmp_path / "cleanup.json"
    evidence.write_text("{}", encoding="utf-8")
    runtime = SimpleNamespace(adapters=SimpleNamespace(fault=SimpleNamespace(target_safe=lambda **_k: True)))
    monkeypatch.setattr(cli, "create_runtime", lambda _s, _p: runtime)
    monkeypatch.setattr(cli, "_settings", lambda _args: SimpleNamespace(run_root=root))
    code, payload = _call(
        capsys,
        ["cleanup-confirm", "--target", TARGET, "--subject", "candidate-01", "--evidence", str(evidence), "--json"],
    )
    assert (code, payload["result_kind"]) == (0, "CLEANUP")


def test_show_and_verify_follow_the_run_root_rule(tmp_path, monkeypatch, capsys) -> None:
    env_root = tmp_path / "env-runs"
    flag_root = tmp_path / "flag-runs"
    in_env = wb.h03_case(env_root, "pass")
    in_flag = wb.h03_case(flag_root, "fail")
    monkeypatch.setenv("CONTROLPROOF_RUN_ROOT", str(env_root))
    code, payload = _call(capsys, ["show", in_env.run_id, "--json"])
    assert (code, payload["run_id"]) == (0, in_env.run_id)
    code, payload = _call(capsys, ["verify", in_env.run_id, "--json"])
    assert (code, payload["bundle_status"]) == (0, "VERIFIED")
    code, payload = _call(capsys, ["show", in_flag.run_id, "--run-root", str(flag_root), "--json"])
    assert (code, payload["run_id"]) == (0, in_flag.run_id)
