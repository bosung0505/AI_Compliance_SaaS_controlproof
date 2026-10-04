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
