from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import pytest

from engine.executors.n02 import N02Executor
from engine.models import (
    AssertionStatus,
    InconclusiveReason,
    ProcessingResponseClass,
    ProtectedPathId,
)
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, FakeN02Adapters, make_adapters


def _run(tmp_path, fake: FakeN02Adapters):
    adapters, _ = make_adapters()
    adapters = replace(
        adapters,
        n02_seed=fake,
        n02_consent=fake,
        n02_processing=fake,
        n02_causality=fake,
    )
    return N02Executor(
        load("scenarios/N-02.yaml"), adapters, tmp_path, clock=FakeClock()
    ).collect_us2(run_id=uuid4())


def test_normal_order_opens_all_three_paths_only_after_durable_consent(tmp_path) -> None:
    fake = FakeN02Adapters()
    result = _run(tmp_path, fake)
    assert result.assertion.status is AssertionStatus.PASS
    assert set(fake.attempted_paths) == set(ProtectedPathId)
    assert all(item.response_class is ProcessingResponseClass.ACCEPTED for item in result.attempts)


def test_equal_times_and_notification_delay_do_not_turn_proven_order_into_fail(tmp_path) -> None:
    result = _run(tmp_path, FakeN02Adapters())
    assert result.assertion.status is AssertionStatus.PASS
    assert "알림" in result.assertion.detail


def test_policy_mismatch_stops_before_any_processing_command(tmp_path) -> None:
    fake = FakeN02Adapters(policy_mismatch=True)
    result = _run(tmp_path, fake)
    assert result.assertion.status is AssertionStatus.FAIL
    assert fake.attempted_paths == []


def test_consent_response_timeout_can_continue_only_when_durable_state_is_known(tmp_path) -> None:
    known = _run(tmp_path, FakeN02Adapters(consent_timeout=True, timeout_state_known=True))
    unknown_fake = FakeN02Adapters(consent_timeout=True, timeout_state_known=False)
    unknown = _run(tmp_path, unknown_fake)
    assert known.assertion.status is AssertionStatus.PASS
    assert unknown.assertion.status is AssertionStatus.INCONCLUSIVE
    assert unknown.assertion.reason_code is InconclusiveReason.INSUFFICIENT_EVIDENCE
    assert unknown_fake.attempted_paths == []


@pytest.mark.parametrize("path", list(ProtectedPathId))
def test_permanently_blocked_post_consent_path_is_fail(tmp_path, path) -> None:
    result = _run(tmp_path, FakeN02Adapters(blocked_paths=frozenset({path})))
    assert result.assertion.status is AssertionStatus.FAIL


def test_causal_evidence_loss_is_inconclusive_not_pass(tmp_path) -> None:
    result = _run(
        tmp_path,
        FakeN02Adapters(causal_missing_path=ProtectedPathId.RECORDING),
    )
    assert result.assertion.status is AssertionStatus.INCONCLUSIVE
    assert result.assertion.reason_code is InconclusiveReason.INSUFFICIENT_EVIDENCE
