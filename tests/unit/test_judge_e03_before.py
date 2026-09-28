from __future__ import annotations

from engine.adapters.base import AdapterResult
from engine.judges.e03 import judge_e03_before
from engine.models import AssertionStatus, InconclusiveReason, Phase, Presence
from tests.fixtures.spec002 import (
    EVENT_ID,
    boundary_receipt,
    delivery_attempt,
    redrive_receipt,
    reporting_effect,
    terminal_failure,
)


def _empty_injected(**updates):
    return reporting_effect(
        phase=Phase.INJECTED,
        effects={
            "logical_report_ids": [],
            "projection_document_ids": [],
            "projection_report_ids": [],
            "processed_keys": [],
            "source_outbox_event_ids": [str(EVENT_ID)],
        },
        **updates,
    )


def _restore(ok=True):
    return AdapterResult(
        ok,
        "ENVIRONMENT_RESTORED" if ok else "ENVIRONMENT_RESTORE_FAILED",
        {"marker_inactive": ok, "worker_healthy": ok},
    )


def _judge(**updates):
    values = {
        "source_event_id": EVENT_ID,
        "boundary": boundary_receipt(),
        "attempts": tuple(delivery_attempt(delivery_attempt=i) for i in range(1, 4)),
        "attempts_presence": Presence.PRESENT,
        "terminal": terminal_failure(),
        "dlq_presence": Presence.PRESENT,
        "injected_effects": (_empty_injected(),),
        "recovered_effects": (reporting_effect(),),
        "restore": _restore(),
        "redrive": redrive_receipt(),
        "expected_receive_count": 3,
    }
    values.update(updates)
    return {item.assertion_id: item for item in judge_e03_before(**values)}


def test_complete_before_lineage_and_exact_recovery_passes_a1_to_a4_and_a8():
    result = _judge()
    assert tuple(result) == ("E03-A1", "E03-A2", "E03-A3", "E03-A4", "E03-A8")
    assert all(item.status is AssertionStatus.PASS for item in result.values())


def test_attempt_mismatch_and_partial_effect_during_fault_are_direct_failures():
    mismatch = _judge(
        attempts=(delivery_attempt(delivery_attempt=1), delivery_attempt(delivery_attempt=3))
    )
    assert mismatch["E03-A2"].status is AssertionStatus.FAIL

    partial = _judge(injected_effects=(reporting_effect(phase=Phase.INJECTED),))
    assert partial["E03-A3"].status is AssertionStatus.FAIL


def test_missing_duplicate_or_inconsistent_recovered_effects_fail_a4():
    missing = reporting_effect(
        effects={
            "logical_report_ids": [],
            "projection_document_ids": [],
            "projection_report_ids": [],
            "processed_keys": [],
            "source_outbox_event_ids": [str(EVENT_ID)],
        }
    )
    assert _judge(recovered_effects=(missing,))["E03-A4"].status is AssertionStatus.FAIL

    duplicate = reporting_effect(
        effects={
            "logical_report_ids": ["report-01", "report-01"],
            "projection_document_ids": ["projection-01"],
            "projection_report_ids": ["report-01"],
            "processed_keys": [
                {"consumer_name": "reporting-worker", "event_id": str(EVENT_ID), "event_version": 1},
                {"consumer_name": "reporting-worker", "event_id": str(EVENT_ID), "event_version": 1},
            ],
            "source_outbox_event_ids": [str(EVENT_ID)],
        }
    )
    assert _judge(recovered_effects=(duplicate,))["E03-A4"].status is AssertionStatus.FAIL

    inconsistent = reporting_effect(
        effects={
            "logical_report_ids": ["report-01"],
            "projection_document_ids": ["projection-01"],
            "projection_report_ids": ["another-report"],
            "processed_keys": [
                {"consumer_name": "reporting-worker", "event_id": str(EVENT_ID), "event_version": 1}
            ],
            "source_outbox_event_ids": [str(EVENT_ID)],
        }
    )
    assert _judge(recovered_effects=(inconsistent,))["E03-A4"].status is AssertionStatus.FAIL


def test_access_loss_is_inconclusive_and_restore_uncertainty_blocks_a8():
    unavailable = reporting_effect(
        effects={},
        source_status=Presence.UNAVAILABLE,
        source_error_code="REPORTING_EFFECT_ACCESS_FAILED",
    )
    result = _judge(recovered_effects=(unavailable,))
    assert result["E03-A4"].status is AssertionStatus.INCONCLUSIVE
    assert result["E03-A4"].reason_code is InconclusiveReason.ACCESS_LIMITED

    result = _judge(restore=_restore(False), redrive=None)
    assert result["E03-A8"].status is AssertionStatus.INCONCLUSIVE


def test_unobserved_before_boundary_is_inconclusive_not_product_pass_or_fail():
    result = _judge(boundary=None)
    assert result["E03-A3"].status is AssertionStatus.INCONCLUSIVE
    assert result["E03-A3"].reason_code is InconclusiveReason.INSUFFICIENT_EVIDENCE
