from __future__ import annotations

from engine.executors.e03_after import E03AfterExecutor
from engine.executors.e03_before import E03BeforeExecutor
from engine.executors.h03_dlq import H03DlqExecutor
from engine.models import ExecutionProfile
from engine.runner import PROFILE_REGISTRY, build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters


def test_all_three_spec002_profiles_have_separate_registered_executors(tmp_path):
    adapters, _browser = make_adapters()

    before = build_profile_runner(
        load("scenarios/E-03-BEFORE.yaml"), adapters, tmp_path, clock=FakeClock()
    )
    after = build_profile_runner(
        load("scenarios/E-03-AFTER.yaml"), adapters, tmp_path, clock=FakeClock()
    )
    h03 = build_profile_runner(
        load("scenarios/H-03-DLQ.yaml"), adapters, tmp_path, clock=FakeClock()
    )

    assert isinstance(before, E03BeforeExecutor)
    assert isinstance(after, E03AfterExecutor)
    assert isinstance(h03, H03DlqExecutor)
    assert PROFILE_REGISTRY.registrations[ExecutionProfile.E03_BEFORE_V2] is E03BeforeExecutor
