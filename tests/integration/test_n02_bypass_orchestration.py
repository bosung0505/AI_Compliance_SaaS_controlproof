from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from engine.executors.n02 import N02Executor
from engine.models import AssertionStatus, ExecutionProfile, ProtectedPathId
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, FakeN02Adapters, make_adapters


def test_n02_us1_runs_three_isolated_bypass_paths_and_always_tears_down(tmp_path) -> None:
    adapters, _ = make_adapters()
    n02 = FakeN02Adapters()
    adapters = replace(adapters, n02_seed=n02, n02_processing=n02)
    executor = N02Executor(load("scenarios/N-02.yaml"), adapters, tmp_path, clock=FakeClock())
    result = executor.collect_us1(run_id=uuid4())
    assert executor.profile is ExecutionProfile.N02_CONSENT_ORDER_V1
    assert {case.path_id for case in result.cases} == set(ProtectedPathId)
    assert all(item.status is AssertionStatus.PASS for item in result.assertions)
    assert result.teardown.ok is True


def test_direct_recording_effect_is_preserved_as_fail(tmp_path) -> None:
    adapters, _ = make_adapters()
    n02 = FakeN02Adapters(
        new_effects={
            ProtectedPathId.DOCUMENT_ANALYSIS: (),
            ProtectedPathId.RECORDING: ("session-created",),
            ProtectedPathId.AI_ASSESSMENT: (),
        }
    )
    adapters = replace(adapters, n02_seed=n02, n02_processing=n02)
    result = N02Executor(
        load("scenarios/N-02.yaml"), adapters, tmp_path, clock=FakeClock()
    ).collect_us1(run_id=uuid4())
    assert result.assertions[2].status is AssertionStatus.FAIL
