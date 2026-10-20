"""T012 — Spec 009 harness: environment overrides, API port 8080, applicant app as one node process.

No process, container or socket server is started; Popen, the process inventory and HTTP are replaced.
"""

from __future__ import annotations

import json
import socket
import subprocess

import pytest

from scripts import spec004_local as local
from scripts import spec009_local


def _state(tmp_path):
    why = tmp_path / "whyyou"
    why.mkdir()
    (why / ".env.example").write_text("APP_ENVIRONMENT=local\n", encoding="utf-8")
    root = tmp_path / "evidence"
    (root / "boot-test").mkdir(parents=True)
    return {
        "whyyou_repo": str(why),
        "whyyou_python": str(tmp_path / "python.exe"),
        "root": str(root),
        "boot": "boot-test",
        "instance": "test",
        "pg_port": 15734,
        "aws_port": 14767,
        "api_port": 8080,
        "processes": {"api": {"ProcessId": 11, "ParentProcessId": 1, "Created": "t0"}},
        "ready": True,
        "stopped": False,
    }


@pytest.mark.parametrize("for_cp", [True, False])
def test_environment_pins_fixture_isolation_and_app_url(tmp_path, for_cp) -> None:
    state = _state(tmp_path)
    values = spec009_local.environment(state, for_cp=for_cp)
    assert values["CONTROLPROOF_MODEL_FIXTURE_ID"] == "n02-analysis-v1"
    assert values["CONTROLPROOF_MODEL_FIXTURE_DIGEST"] == (
        "092de5950a39ba3a7255c8696ffb073cddc65cda4615237044e3d910e32f9828"
    )
    assert values["CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED"] == "true"
    assert values["CONTROLPROOF_EXTERNAL_AI_ALLOWED"] == "false"
    assert values["CONTROLPROOF_WHYYOU_PYTHON"] == state["whyyou_python"]
    if for_cp:
        assert values["CONTROLPROOF_APPLICANT_APP_URL"] == "http://127.0.0.1:5174"
        assert values["WHYYOU_BASE_URL"] == "http://127.0.0.1:8080"
    else:
        assert "CONTROLPROOF_APPLICANT_APP_URL" not in values


def test_api_port_defaults_to_8080_and_flag_is_stripped(monkeypatch) -> None:
    seen = []
    monkeypatch.setattr(local, "main", lambda argv: seen.append(list(argv)) or 0)
    monkeypatch.setattr(spec009_local, "_ports_free", lambda *ports: None)
    assert spec009_local.main(["status", "--instance", "x"]) == 0
    assert seen[-1] == ["status", "--instance", "x", "--api-port", "8080"]
    assert spec009_local.main(["up", "--api-port", "18080", "--with-applicant-app"]) == 0
    assert seen[-1] == ["up", "--api-port", "18080"]
    assert local.environment is not spec009_local.environment  # restored after the call


def test_cli_mode_keeps_api_port_before_the_engine_separator(monkeypatch) -> None:
    """Stage 2 preparation: the default port was appended after `--` and reached the engine CLI."""
    seen = []
    monkeypatch.setattr(local, "main", lambda argv: seen.append(list(argv)) or 0)
    command = ["preflight", "N-03", "--profile", "N03_STALE_CONSENT_V1", "--target", "whyyou-local", "--json"]
    assert spec009_local.main(["cli", "--instance", "x", "--state-root", "y", "--", *command]) == 0
    assert seen[-1] == ["cli", "--instance", "x", "--state-root", "y", "--api-port", "8080", "--", *command]
    harness, engine = seen[-1][: seen[-1].index("--")], seen[-1][seen[-1].index("--") + 1 :]
    assert "--api-port" not in engine and harness[-2:] == ["--api-port", "8080"]
    assert spec009_local.main(["cli", "--api-port", "9000", "--", *command]) == 0
    assert seen[-1] == ["cli", "--api-port", "9000", "--", *command]
    # An engine-side argument named like the harness flag does not count as the harness port.
    assert spec009_local.main(["cli", "--", "run", "--api-port", "1"]) == 0
    assert seen[-1] == ["cli", "--api-port", "8080", "--", "run", "--api-port", "1"]


def test_with_applicant_app_is_up_only() -> None:
    with pytest.raises(SystemExit):
        spec009_local.main(["status", "--with-applicant-app"])


def test_up_refuses_when_api_or_app_port_is_in_use(monkeypatch) -> None:
    called = []
    monkeypatch.setattr(local, "main", lambda argv: called.append(argv) or 0)
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        port = busy.getsockname()[1]
        with pytest.raises(RuntimeError, match="SPEC009_PORT_IN_USE"):
            spec009_local.main(["up", "--api-port", str(port)])
    assert called == []


def _launch(tmp_path, monkeypatch, *, node="C:/node/node.exe", vite=True, responses=(200,)):
    state = _state(tmp_path)
    why = tmp_path / "whyyou"
    (why / "apps" / "applicant-interview").mkdir(parents=True)
    if vite:
        (why / "node_modules" / "vite" / "bin").mkdir(parents=True)
        (why / "node_modules" / "vite" / "bin" / "vite.js").write_text("", encoding="utf-8")
    popen = []

    class Process:
        pid = 4242

    def fake_popen(argv, **kwargs):
        popen.append((argv, kwargs))
        return Process()

    answers = iter(responses)
    monkeypatch.setattr(spec009_local.shutil, "which", lambda name: node if name == "node" else None)
    monkeypatch.setattr(spec009_local.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        spec009_local.local,
        "process_snapshot",
        lambda: [{"ProcessId": 4242, "ParentProcessId": 1, "Created": "t1"}],
    )
    monkeypatch.setattr(spec009_local, "_ports_free", lambda *ports: None)
    monkeypatch.setattr(spec009_local.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        spec009_local, "_app_status", lambda url: next(answers, None)
    )
    return state, popen


def test_applicant_app_runs_as_one_node_process_and_is_recorded(tmp_path, monkeypatch) -> None:
    state, popen = _launch(tmp_path, monkeypatch, responses=(None, 503, 200))
    spec009_local.start_applicant_app(state)
    (argv, kwargs), = popen
    why = tmp_path / "whyyou"
    assert argv == ["C:/node/node.exe", str(why / "node_modules" / "vite" / "bin" / "vite.js"), "--strictPort"]
    assert kwargs["cwd"] == why / "apps" / "applicant-interview"
    assert kwargs["creationflags"] == subprocess.CREATE_NO_WINDOW
    assert kwargs["stderr"] == subprocess.STDOUT
    assert state["processes"]["applicant_app"] == {"ProcessId": 4242, "ParentProcessId": 1, "Created": "t1"}
    assert state["processes"]["api"]["ProcessId"] == 11  # existing roots kept, so `stop` ends both
    assert state["applicant_app_url"] == "http://127.0.0.1:5174"
    saved = json.loads((tmp_path / "evidence" / "state.json").read_text(encoding="utf-8"))
    assert saved["processes"]["applicant_app"]["ProcessId"] == 4242 and "pending_process" not in saved
    assert (tmp_path / "evidence" / "boot-test" / "applicant_app.log").exists()


@pytest.mark.parametrize(("node", "vite"), [(None, True), ("C:/node/node.exe", False)])
def test_missing_node_or_vite_fails_without_installing(tmp_path, monkeypatch, node, vite) -> None:
    state, popen = _launch(tmp_path, monkeypatch, node=node, vite=vite)
    with pytest.raises(RuntimeError, match="SPEC009_APPLICANT_APP_DEPENDENCY_MISSING"):
        spec009_local.start_applicant_app(state)
    assert popen == [] and "applicant_app" not in state["processes"]


def test_app_that_never_answers_fails_after_recording_the_pid(tmp_path, monkeypatch) -> None:
    state, _popen = _launch(tmp_path, monkeypatch, responses=())
    with pytest.raises(RuntimeError, match="SPEC009_APPLICANT_APP_NOT_READY"):
        spec009_local.start_applicant_app(state, timeout_seconds=3)
    assert state["processes"]["applicant_app"]["ProcessId"] == 4242  # still owned, so `stop` can end it


def test_up_with_app_starts_the_app_after_the_base_stack(monkeypatch, tmp_path) -> None:
    order = []
    monkeypatch.setattr(spec009_local, "_ports_free", lambda *ports: order.append(("ports", ports)))
    monkeypatch.setattr(spec009_local, "start_applicant_app", lambda state: order.append(("app", state["ready"])))

    def fake_main(argv):
        local.start({"ready": True})
        return 0

    monkeypatch.setattr(local, "main", fake_main)
    base = lambda state: order.append(("base", None))
    monkeypatch.setattr(local, "start", base)
    assert spec009_local.main(["up", "--with-applicant-app"]) == 0
    assert order == [("ports", (8080, 5174)), ("base", None), ("app", True)]
    assert local.start is base  # the wrapper is removed after the call
