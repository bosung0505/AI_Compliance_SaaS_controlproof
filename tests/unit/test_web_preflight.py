"""T024 — web preflight runner (FR-011, FR-012, SC-010, R-007). RED until T030.

The web runs `python -m engine.cli preflight … --json` as a subprocess, stores the CLI JSON as is, and interprets it by
`result_kind`/`error_kind`/`readiness`, never by exit code.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from types import SimpleNamespace

import pytest

from engine.web import preflight
from engine.web.readmodel import load_catalog

READY = {
    "schema_version": "controlproof.cli.v1", "command": "preflight", "result_kind": "READINESS",
    "readiness": "READY", "checked_at": "2026-10-08T10:12:00+00:00", "operator_action": None,
    "capabilities": {"ready": 18, "required": 18}, "target_version": "target-snapshot:sha256:" + "b" * 64,
}


def _fake(payload, code=0, calls=None):
    def run(command, **kwargs):
        if calls is not None:
            calls.append((command, kwargs))
        return SimpleNamespace(returncode=code, stdout=json.dumps(payload), stderr="")

    return run


def _runner(tmp_path, run, **kwargs):
    return preflight.PreflightRunner(
        load_catalog(), preflight.ReadinessStore(tmp_path / "preflight"), target="whyyou-local", run=run, **kwargs
    )


def test_command_is_built_from_catalog_profiles_only(tmp_path) -> None:
    calls = []
    runner = _runner(tmp_path, _fake(READY, calls=calls))
    runner.check("E-01", "E01_CITATION_EVIDENCE_V1")
    command, kwargs = calls[0]
    assert command == [
        sys.executable, "-m", "engine.cli", "preflight", "E-01", "--profile", "E01_CITATION_EVIDENCE_V1",
        "--target", "whyyou-local", "--json",
    ]
    assert kwargs["timeout"] == 120 and kwargs.get("shell") in (None, False)
    for scenario_id, profile in (("E-01", "E02_SCORING_FREEZE_V1"), ("H-01", "H03_MINIMAL_V1"), ("A-01", "X")):
        with pytest.raises(preflight.UnknownProfile):
            runner.check(scenario_id, profile)
    assert len(calls) == 1


def test_ready_record_is_stored_with_payload_checked_at(tmp_path) -> None:
    runner = _runner(tmp_path, _fake(READY))
    record = runner.check("E-01", "E01_CITATION_EVIDENCE_V1")
    assert (record["result_kind"], record["readiness"], record["checked_at"]) == (
        "READINESS", "READY", "2026-10-08T10:12:00+00:00",
    )
    assert record["capabilities"] == {"ready": 18, "required": 18}
    latest = tmp_path / "preflight" / "E-01--E01_CITATION_EVIDENCE_V1.json"
    assert json.loads(latest.read_text(encoding="utf-8"))["readiness"] == "READY"
    history = (tmp_path / "preflight" / "history.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(history) == 1
    assert runner.store.latest("E-01", "E01_CITATION_EVIDENCE_V1")["checked_at"] == record["checked_at"]


def test_exit_code_is_stored_but_not_interpreted(tmp_path) -> None:
    not_ready = dict(READY, readiness="RUNNER_NOT_READY", operator_action="repair fixture")
    record = _runner(tmp_path, _fake(not_ready, code=2)).check("E-01", "E01_CITATION_EVIDENCE_V1")
    assert (record["exit_code"], record["result_kind"], record["readiness"]) == (2, "READINESS", "RUNNER_NOT_READY")
    odd = _runner(tmp_path, _fake(READY, code=7)).check("E-01", "E01_CITATION_EVIDENCE_V1")
    assert (odd["exit_code"], odd["readiness"]) == (7, "READY")


def test_usage_error_is_a_tool_error(tmp_path) -> None:
    usage = {"schema_version": "controlproof.cli.v1", "command": "preflight", "result_kind": "ERROR",
             "error_kind": "USAGE", "error": "USAGE", "detail": "the following arguments are required"}
    record = _runner(tmp_path, _fake(usage, code=2)).check("E-02", "E02_SCORING_FREEZE_V1")
    assert (record["result_kind"], record["error_kind"], record["readiness"]) == ("ERROR", "USAGE", None)
    assert record["checked_at"]


def test_timeout_is_an_unexpected_error(tmp_path) -> None:
    def run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    record = _runner(tmp_path, run).check("H-03", "H03_DLQ_V2")
    assert (record["result_kind"], record["error_kind"], record["readiness"]) == ("ERROR", "UNEXPECTED", None)
    assert record["operator_action"] == "준비 상태 확인 시간이 초과됐습니다"
    assert record["exit_code"] is None


def test_unparseable_output_is_an_unexpected_error(tmp_path) -> None:
    def run(command, **kwargs):
        return SimpleNamespace(returncode=1, stdout="Traceback (most recent call last)", stderr="")

    record = _runner(tmp_path, run).check("H-03", "H03_DLQ_V2")
    assert (record["result_kind"], record["error_kind"]) == ("ERROR", "UNEXPECTED")
    assert "Traceback" not in json.dumps(record)


def test_stored_payload_goes_through_the_output_boundary(tmp_path) -> None:
    leaky = dict(READY, operator_action="see C:\\Users\\alice\\repo and /home/bob/x")
    record = _runner(tmp_path, _fake(leaky)).check("E-01", "E01_CITATION_EVIDENCE_V1")
    text = (tmp_path / "preflight" / "history.jsonl").read_text(encoding="utf-8")
    assert "alice" not in text and "bob" not in text and "alice" not in json.dumps(record)


def test_second_concurrent_request_is_rejected(tmp_path) -> None:
    started, release = threading.Event(), threading.Event()

    def slow(command, **kwargs):
        started.set()
        release.wait(5)
        return SimpleNamespace(returncode=0, stdout=json.dumps(READY), stderr="")

    runner = _runner(tmp_path, slow)
    worker = threading.Thread(target=runner.check, args=("E-01", "E01_CITATION_EVIDENCE_V1"))
    worker.start()
    assert started.wait(5)
    with pytest.raises(preflight.PreflightBusy):
        runner.check("E-02", "E02_SCORING_FREEZE_V1")
    release.set()
    worker.join(5)
    assert runner.check("E-02", "E02_SCORING_FREEZE_V1")["readiness"] == "READY"
