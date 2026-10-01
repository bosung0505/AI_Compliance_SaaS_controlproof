from uuid import uuid4

import pytest

from engine.judges.n02 import N02BypassCase, judge_n02_bypass
from engine.models import N02LaneId, Phase, ProtectedPathId
from tests.fixtures.fake_adapters import FakeN02Adapters


def test_fixture_effects_are_excluded_from_new_effect_delta() -> None:
    fake = FakeN02Adapters()
    lanes = fake.seed_lanes(run_id=str(uuid4()))
    lane = next(item for item in lanes if item.lane_id is N02LaneId.RECORDING_BOUNDARY_PROBE)
    subject = lane.model_dump(mode="json") | {"allowed_fixture_effect_ids": ["fixture-1"]}
    fake.new_effects[ProtectedPathId.RECORDING] = ("fixture-1",)
    effects = fake.read_effects(
        path_id="RECORDING",
        subject=subject,
        phase=Phase.INJECTED.value,
        step_id="fixture-delta",
    )
    assert effects.fixture_effect_ids == ("fixture-1",)
    assert effects.new_effect_ids == ()


def test_another_lane_cannot_satisfy_a_path_assertion() -> None:
    from tests.unit.test_judge_n02_bypass import _inputs

    baseline, cases = _inputs()
    foreign = N02BypassCase(
        path_id=ProtectedPathId.DOCUMENT_ANALYSIS,
        lane_id=N02LaneId.NORMAL_ORDER,
        attempt=cases[0].attempt,
        effects=cases[0].effects,
    )
    with pytest.raises(ValueError, match="lane"):
        judge_n02_bypass(baseline, (foreign, *cases[1:]))
