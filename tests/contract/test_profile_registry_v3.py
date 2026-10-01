from engine.executors.n02 import N02Executor
from engine.models import ExecutionProfile
from engine.runner import PROFILE_REGISTRY


def test_n02_profile_has_a_dedicated_registered_executor() -> None:
    assert PROFILE_REGISTRY.registrations[ExecutionProfile.N02_CONSENT_ORDER_V1] is N02Executor
