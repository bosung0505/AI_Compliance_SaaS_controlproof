"""T085: N-02 timing comes only from the scenario snapshot (SC-006, SC-008, ID-003-10)."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from engine.executors.n02 import N02Executor, N02RunDeadlineExceeded, _Stabilizer
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, FakeN02Adapters, make_adapters


def _timing(scenario, **updates):
    return scenario.timing_policy.model_copy(update=updates)


def _reads(*digests):
    values = iter(SimpleNamespace(state_digest=item) for item in digests)
    calls = []

    def fetch():
        calls.append(1)
        return next(values)

    return fetch, calls


class RecordingClock(FakeClock):
    def __init__(self):
        super().__init__()
        self.sleeps: list[float] = []

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        super().sleep(seconds)


def test_canonical_n02_snapshot_freezes_every_timing_value():
    scenario = load("scenarios/N-02.yaml")
    timing = scenario.snapshot().definition["timing_policy"]
    assert timing["poll_seconds"] == 2
    assert timing["stability_consecutive"] == 3
    assert timing["stability_seconds"] == 4
    assert timing["fault_ttl_seconds"] == 600
    assert timing["environment_restore_deadline_seconds"] == 120
    assert timing["run_deadline_seconds"] == 540
    assert timing["bundle_verify_deadline_seconds"] == 60
    assert timing["run_deadline_seconds"] + timing["bundle_verify_deadline_seconds"] == 600


def test_single_immediate_read_is_never_accepted_as_stable():
    clock = RecordingClock()
    timing = _timing(load("scenarios/N-02.yaml"))
    fetch, calls = _reads("A", "A", "A")

    _Stabilizer(timing, clock, None).read(fetch, lambda v: v.state_digest, "effects")

    assert len(calls) == 3
    assert clock.sleeps == [2, 2]


def test_poll_streak_and_window_follow_a_changed_snapshot_not_constants():
    clock = RecordingClock()
    timing = _timing(
        load("scenarios/N-02.yaml"), poll_seconds=1, stability_consecutive=4, stability_seconds=3
    )
    fetch, calls = _reads("A", "B", "B", "B", "B")

    value = _Stabilizer(timing, clock, None).read(fetch, lambda v: v.state_digest, "effects")

    assert value.state_digest == "B"
    assert len(calls) == 5
    assert clock.sleeps == [1, 1, 1, 1]


def test_unstable_observation_hits_the_snapshot_run_deadline():
    clock = RecordingClock()
    timing = _timing(load("scenarios/N-02.yaml"))
    deadline = clock.now() + timedelta(seconds=5)
    fetch, _calls = _reads(*[str(index) for index in range(100)])

    with pytest.raises(N02RunDeadlineExceeded, match="N02_RUN_DEADLINE_EXCEEDED"):
        _Stabilizer(timing, clock, deadline).read(fetch, lambda v: v.state_digest, "effects")
    assert sum(clock.sleeps) <= 6


@pytest.mark.parametrize("ttl", [600, 90])
def test_consent_fault_marker_ttl_comes_from_the_snapshot(tmp_path, ttl):
    scenario = load("scenarios/N-02.yaml")
    scenario = scenario.model_copy(
        update={"timing_policy": _timing(scenario, fault_ttl_seconds=ttl)}
    )
    fake = FakeN02Adapters()
    applied = []
    original = fake.apply_consent_fault

    def record(*, run_id, subject, expires_at):
        applied.append(expires_at)
        return original(run_id=run_id, subject=subject, expires_at=expires_at)

    fake.apply_consent_fault = record
    adapters, _ = make_adapters()
    adapters = replace(
        adapters,
        n02_seed=fake,
        n02_consent=fake,
        n02_processing=fake,
        n02_causality=fake,
        n02_fault=fake,
        n02_observer=fake,
    )
    clock = FakeClock()
    before = clock.now()
    N02Executor(scenario, adapters, tmp_path, clock=clock).collect_us3(run_id=uuid4())

    assert len(applied) == 1
    assert (applied[0] - before).total_seconds() == pytest.approx(ttl, abs=1)


def _n02_runner(tmp_path, fake, clock, **timing_updates):
    from dataclasses import replace as _replace

    from engine.runner import build_profile_runner

    scenario = load("scenarios/N-02.yaml")
    if timing_updates:
        scenario = scenario.model_copy(update={"timing_policy": _timing(scenario, **timing_updates)})
    adapters, _ = make_adapters()
    adapters = _replace(
        adapters,
        n02_seed=fake,
        n02_consent=fake,
        n02_processing=fake,
        n02_causality=fake,
        n02_fault=fake,
        n02_observer=fake,
    )
    return build_profile_runner(scenario, adapters, tmp_path, clock=clock)


class SlowTeardown(FakeN02Adapters):
    """Teardown that takes `seconds` of the executor clock (T085: restore deadline)."""

    def __init__(self, clock, seconds):
        super().__init__()
        self._clock, self._seconds = clock, seconds

    def teardown_lanes(self, *, run_id: str, lanes):
        self._clock.sleep(self._seconds)
        return super().teardown_lanes(run_id=run_id, lanes=lanes)


@pytest.mark.parametrize(("deadline", "elapsed", "state"), [(120, 130, "RESTORE_FAILED"), (200, 130, "COMPLETED")])
def test_restore_deadline_comes_from_the_snapshot(tmp_path, deadline, elapsed, state):
    from engine.lifecycle import RestoreBlockStore

    clock = FakeClock()
    runner = _n02_runner(tmp_path, SlowTeardown(clock, elapsed), clock, environment_restore_deadline_seconds=deadline)
    run, _judgement, _bundle = runner.execute(runner.preflight("whyyou-local"))

    assert run.state.value == state
    assert RestoreBlockStore(tmp_path).blocked("whyyou-local", "n02-consent-order") is (state == "RESTORE_FAILED")
    timing = runner.timing_report()
    assert timing["environment_restore_deadline_seconds"] == deadline
    assert timing["environment_restore_seconds"] >= elapsed
    assert timing["environment_restore_within_deadline"] is (state == "COMPLETED")


@pytest.mark.parametrize(("budget", "verify_seconds", "within"), [(60, 61, False), (120, 61, True)])
def test_bundle_verify_budget_is_reserved_from_the_snapshot(tmp_path, monkeypatch, budget, verify_seconds, within):
    import engine.executors.n02 as executor_module

    clock = FakeClock()
    real_verify = executor_module.verify_bundle

    def slow_verify(directory):
        clock.sleep(verify_seconds)
        return real_verify(directory)

    monkeypatch.setattr(executor_module, "verify_bundle", slow_verify)
    runner = _n02_runner(tmp_path, FakeN02Adapters(), clock, bundle_verify_deadline_seconds=budget)
    runner.execute(runner.preflight("whyyou-local"))

    timing = runner.timing_report()
    assert timing["bundle_verify_deadline_seconds"] == budget
    assert timing["bundle_verify_seconds"] == verify_seconds
    assert timing["bundle_verify_within_budget"] is within


def test_receipt_pre_wait_is_the_snapshot_poll_interval_not_a_constant():
    from engine.executors.n02 import _StableReads

    class Adapter:
        receipt_wait_seconds = 0.0

    adapter = Adapter()
    timing = _timing(load("scenarios/N-02.yaml"), poll_seconds=3)
    _StableReads(adapter, _Stabilizer(timing, FakeClock(), None))
    assert adapter.receipt_wait_seconds == 3.0
