"""T046 — E-01 removal/probe journey with always-run restores (US2, FR-022, FR-041, SC-002).

RED until T048 adds the removal and storage-probe steps to `engine/executors/e01.py`.
"""

from __future__ import annotations

import json

import pytest

from engine.models import AssertionStatus, RunState, Verdict
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters
from tests.fixtures.fake_spec004 import FakeSpec004Adapters, use_spec004_fixture


def _runner(tmp_path, fake, clock=None):
    adapters, _ = make_adapters(spec004=fake)
    use_spec004_fixture(adapters)
    return build_profile_runner(
        load("scenarios/E-01.yaml"), adapters, tmp_path, clock=clock or FakeClock()
    )


def _run(tmp_path, fake, clock=None):
    runner = _runner(tmp_path, fake, clock)
    readiness = runner.preflight("whyyou-local")
    assert readiness.status.value == "READY", readiness
    run, judgement, bundle = runner.execute(readiness)
    return runner, run, judgement, bundle


def _results(judgement):
    return {item.assertion_id: item for item in judgement.assertion_results}


def _segments_back(fake) -> bool:
    return set(fake.segments) == fake.present_segments


def test_exposed_removal_and_restore_pass_and_d1_is_diagnostic(tmp_path) -> None:
    fake = FakeSpec004Adapters(removal_indicator="score_null")
    _, run, judgement, bundle = _run(tmp_path, fake)
    results = _results(judgement)
    for assertion_id in ("E01-A1", "E01-A2", "E01-A3", "E01-A4"):
        assert results[assertion_id].status is AssertionStatus.PASS, results[assertion_id].detail
    assert judgement.verdict is Verdict.PASS
    assert run.state is RunState.COMPLETED
    probe = json.loads((bundle / "storage-probe.json").read_text(encoding="utf-8"))
    assert probe["diagnostic_id"] == "E01-D1"
    assert {row["mode"] for row in probe["exposure"]} == {"EMPTY", "NONEXISTENT", "OTHER_APPLICANT"}
    assert "E01-D1" not in results
    assert _segments_back(fake) and fake.torn_down


def test_p1_shape_fails_a3(tmp_path) -> None:
    _, _, judgement, _ = _run(tmp_path, FakeSpec004Adapters())
    assert _results(judgement)["E01-A3"].status is AssertionStatus.FAIL
    assert judgement.verdict is Verdict.FAIL


@pytest.mark.parametrize("option", ["restore_mismatch", "probe_restore_fails"])
def test_unsafe_restore_is_restore_failed_and_blocks(tmp_path, option) -> None:
    fake = FakeSpec004Adapters(removal_indicator="score_null", **{option: True})
    runner, run, judgement, _ = _run(tmp_path, fake)
    assert run.state is RunState.RESTORE_FAILED
    assert judgement.verdict is Verdict.INCONCLUSIVE
    with pytest.raises(RuntimeError, match="blocked"):
        runner.execute(runner.preflight("whyyou-local"))


def test_exception_after_removal_still_restores(tmp_path) -> None:
    fake = FakeSpec004Adapters(removal_indicator="score_null")
    original = fake.read_api

    def broken(*, lane, phase, include_timeline=False):
        if phase == "POST_REMOVAL":
            raise ConnectionError("synthetic read failure")
        return original(lane=lane, phase=phase, include_timeline=include_timeline)

    fake.read_api = broken
    _, run, judgement, _ = _run(tmp_path, fake)
    assert _results(judgement)["E01-A3"].status is AssertionStatus.INCONCLUSIVE
    assert run.state is RunState.COMPLETED
    assert _segments_back(fake) and fake.torn_down


def test_cancellation_restores_then_propagates(tmp_path) -> None:
    fake = FakeSpec004Adapters(removal_indicator="score_null")
    original = fake.read_api

    def cancelled(*, lane, phase, include_timeline=False):
        if phase == "POST_REMOVAL":
            raise KeyboardInterrupt
        return original(lane=lane, phase=phase, include_timeline=include_timeline)

    fake.read_api = cancelled
    runner = _runner(tmp_path, fake)
    with pytest.raises(KeyboardInterrupt):
        runner.execute(runner.preflight("whyyou-local"))
    assert _segments_back(fake) and fake.torn_down


def test_deadline_skips_reads_but_not_restore_and_budget_counts_restore_only(tmp_path) -> None:
    fake = FakeSpec004Adapters(removal_indicator="score_null")
    clock = FakeClock()
    original = fake.remove_segment

    def slow(**kwargs):
        clock.sleep(1000)  # apply work, not restore work
        return original(**kwargs)

    fake.remove_segment = slow
    runner, run, judgement, _ = _run(tmp_path, fake, clock)
    assert _results(judgement)["E01-A3"].status is AssertionStatus.INCONCLUSIVE
    assert run.state is RunState.COMPLETED
    timing = runner.timing_report()
    assert timing["environment_restore_within_deadline"] is True
    assert timing["environment_restore_seconds"] < 120
    assert _segments_back(fake) and fake.torn_down
