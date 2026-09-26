from __future__ import annotations

import json
from dataclasses import replace

from engine.adapters.base import AdapterResult
from engine.runner import RunOrchestrator
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, FakeFault, FakeState, make_adapters


def _read(bundle):
    return [
        json.loads(line)
        for line in (bundle / "checkpoints.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def test_every_scenario_step_has_durable_started_and_terminal_checkpoint(tmp_path):
    adapters, _ = make_adapters()
    scenario = load("scenarios/H-03.yaml")
    runner = RunOrchestrator(scenario, adapters, tmp_path, clock=FakeClock())

    _, _, bundle = runner.execute(runner.preflight("whyyou-local"))

    rows = _read(bundle)
    expected_steps = [step.step_id for step in scenario.steps]
    for step_id in expected_steps:
        outcomes = [row["outcome"] for row in rows if row["step_id"] == step_id]
        assert outcomes[0] == "STARTED"
        assert outcomes[-1] == "SUCCEEDED"
    assert all(
        {"run_id", "subject_ref", "phase", "step_id", "attempt", "outcome", "recorded_at"}
        <= set(row)
        for row in rows
    )


class FailingDecisionState(FakeState):
    def attempt_final_decision(self, *, subject):
        return AdapterResult(False, "DECISION_ENDPOINT_UNAVAILABLE")


class FailingBaselineState(FakeState):
    def snapshot(self, *, subject, phase):
        if phase == "BASELINE":
            return AdapterResult(False, "BASELINE_UNAVAILABLE")
        return super().snapshot(subject=subject, phase=phase)


class FailingPostState(FakeState):
    def snapshot(self, *, subject, phase):
        if phase == "INJECTED":
            return AdapterResult(False, "POST_STATE_UNAVAILABLE")
        return super().snapshot(subject=subject, phase=phase)


class FailingApplyFault(FakeFault):
    def apply(self, *, run_id, subject, expires_at):
        return AdapterResult(False, "FAULT_APPLY_REJECTED")


class RaisingEffectFault(FakeFault):
    def probe_effect(self, *, run_id, subject, trigger):
        raise RuntimeError("receipt reader crashed")


def _outcomes(bundle, step_id):
    return [row["outcome"] for row in _read(bundle) if row["step_id"] == step_id]


def test_checkpoint_identifies_interruption_after_seed(tmp_path):
    adapters, _ = make_adapters()
    adapters = replace(adapters, state=FailingBaselineState())
    runner = RunOrchestrator(load("scenarios/H-03.yaml"), adapters, tmp_path, clock=FakeClock())

    _, _, bundle = runner.execute(runner.preflight("whyyou-local"))

    assert _outcomes(bundle, "seed-pending-report") == ["STARTED", "SUCCEEDED"]
    assert _outcomes(bundle, "capture-baseline") == ["STARTED", "FAILED"]


def test_checkpoint_identifies_interruption_after_baseline(tmp_path):
    adapters, _ = make_adapters()
    adapters = replace(adapters, fault=FailingApplyFault())
    runner = RunOrchestrator(load("scenarios/H-03.yaml"), adapters, tmp_path, clock=FakeClock())

    _, _, bundle = runner.execute(runner.preflight("whyyou-local"))

    assert _outcomes(bundle, "capture-baseline") == ["STARTED", "SUCCEEDED"]
    assert _outcomes(bundle, "apply-reporting-fault") == ["STARTED", "FAILED"]


def test_checkpoint_identifies_interruption_after_trigger(tmp_path):
    adapters, _ = make_adapters()
    adapters = replace(adapters, fault=RaisingEffectFault())
    runner = RunOrchestrator(load("scenarios/H-03.yaml"), adapters, tmp_path, clock=FakeClock())

    _, _, bundle = runner.execute(runner.preflight("whyyou-local"))

    assert _outcomes(bundle, "trigger-reporting") == ["STARTED", "SUCCEEDED"]
    assert _outcomes(bundle, "confirm-fault-effect") == ["STARTED", "FAILED"]
    assert _outcomes(bundle, "restore-environment") == ["STARTED", "SUCCEEDED"]


def test_checkpoint_identifies_interruption_after_decision_attempt(tmp_path):
    adapters, _ = make_adapters()
    adapters = replace(adapters, state=FailingPostState())
    runner = RunOrchestrator(load("scenarios/H-03.yaml"), adapters, tmp_path, clock=FakeClock())

    _, _, bundle = runner.execute(runner.preflight("whyyou-local"))

    assert _outcomes(bundle, "attempt-final-decision") == ["STARTED", "SUCCEEDED"]
    assert _outcomes(bundle, "capture-post-decision-state") == ["STARTED", "FAILED"]


def test_failed_step_checkpoint_survives_aborted_run_and_restore(tmp_path):
    adapters, _ = make_adapters()
    adapters = replace(adapters, state=FailingDecisionState())
    runner = RunOrchestrator(load("scenarios/H-03.yaml"), adapters, tmp_path, clock=FakeClock())

    run, _, bundle = runner.execute(runner.preflight("whyyou-local"))

    rows = _read(bundle)
    failed = [row for row in rows if row["outcome"] == "FAILED"]
    assert failed[-1]["step_id"] == "attempt-final-decision"
    assert failed[-1]["error_code"] == "DECISION_ENDPOINT_UNAVAILABLE"
    restore = [row for row in rows if row["step_id"] == "restore-environment"]
    assert [row["outcome"] for row in restore] == ["STARTED", "SUCCEEDED"]
    assert str(run.run_id) == failed[-1]["run_id"]


class RaisingRestoreFault(FakeFault):
    def restore(self, *, run_id, subject):
        raise RuntimeError("worker health probe crashed")


def test_restore_exception_is_checkpointed_and_sealed_as_restore_failed(tmp_path):
    adapters, _ = make_adapters()
    adapters = replace(adapters, fault=RaisingRestoreFault())
    runner = RunOrchestrator(load("scenarios/H-03.yaml"), adapters, tmp_path, clock=FakeClock())

    run, _, bundle = runner.execute(runner.preflight("whyyou-local"))

    rows = _read(bundle)
    restore = [row for row in rows if row["step_id"] == "restore-environment"]
    assert restore[0]["outcome"] == "STARTED"
    assert restore[-1]["outcome"] == "FAILED"
    assert restore[-1]["error_code"] == "RUNTIMEERROR"
    assert run.state.value == "RESTORE_FAILED"
    assert (bundle / "manifest.json").is_file()
