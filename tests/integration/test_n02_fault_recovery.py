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
    RecoveryStatus,
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
        n02_fault=fake,
        n02_observer=fake,
    )
    return N02Executor(
        load("scenarios/N-02.yaml"), adapters, tmp_path, clock=FakeClock()
    ).collect_us3(run_id=uuid4())


def test_faulted_consent_rolls_back_blocks_three_paths_then_recovers_same_subject(
    tmp_path,
) -> None:
    result = _run(tmp_path, FakeN02Adapters())

    assert not result.failed_commit.ok
    assert result.fault_receipt is not None
    assert result.fault_receipt.request_id == result.failed_commit.data["request_id"]
    assert result.failed_state.active_consent_count == 0
    assert {item.path_id for item in result.failure_attempts} == set(ProtectedPathId)
    assert all(
        item.response_class is ProcessingResponseClass.DENIED
        for item in result.failure_attempts
    )
    assert all(not item.new_effect_ids for item in result.failure_effects)
    assert result.recovery.restore_status is RecoveryStatus.SUCCEEDED
    assert result.recovery.logical_consent_count == 1
    assert result.recovery.consent_completed_event_count == 1
    assert result.recovery.processing_order_proven is True
    assert result.recovered_order is not None
    assert result.recovered_order.status is AssertionStatus.PASS
    assert [item.status for item in result.assertions] == [
        AssertionStatus.PASS,
        AssertionStatus.PASS,
    ]
    assert result.teardown.ok


def test_missing_trigger_receipt_keeps_a6_inconclusive_without_hiding_safe_cleanup(
    tmp_path,
) -> None:
    result = _run(tmp_path, FakeN02Adapters(fault_triggered=False))
    a6, a7 = result.assertions
    assert result.fault_receipt is None
    assert a6.status is AssertionStatus.INCONCLUSIVE
    assert a6.reason_code is InconclusiveReason.INSUFFICIENT_EVIDENCE
    assert a7.status is AssertionStatus.PASS
    assert result.recovery.restore_status is RecoveryStatus.SUCCEEDED


def test_restore_failure_prevents_retry_and_requires_manual_cleanup(tmp_path) -> None:
    result = _run(tmp_path, FakeN02Adapters(restore_succeeded=False))
    a6, a7 = result.assertions
    assert result.recovery.restore_status is RecoveryStatus.FAILED
    assert result.recovery.manual_cleanup_required is True
    assert result.recovered_order is None
    assert a6.status is AssertionStatus.INCONCLUSIVE
    assert a7.status is AssertionStatus.INCONCLUSIVE
    assert result.teardown.ok


@pytest.mark.parametrize("interruption", [TimeoutError, KeyboardInterrupt])
def test_timeout_or_cancellation_still_restores_overlay_fault_and_lanes(
    tmp_path, interruption
) -> None:
    class InterruptingFake(FakeN02Adapters):
        def __init__(self):
            super().__init__()
            self.restore_calls = 0
            self.teardown_called = False

        def attempt(self, *, path_id: str, subject):
            if str(subject["lane_id"]) == "CONSENT_FAULT_RECOVERY":
                raise interruption("synthetic interruption")
            return super().attempt(path_id=path_id, subject=subject)

        def restore_consent_fault(self, *, run_id: str, subject):
            self.restore_calls += 1
            return super().restore_consent_fault(run_id=run_id, subject=subject)

        def teardown_lanes(self, *, run_id: str, lanes):
            self.teardown_called = True
            return super().teardown_lanes(run_id=run_id, lanes=lanes)

    fake = InterruptingFake()
    with pytest.raises(interruption):
        _run(tmp_path, fake)
    assert fake.restore_calls == 1
    assert fake.teardown_called is True
    assert fake._overlay_paths == set()
    assert fake._fault_active is False
