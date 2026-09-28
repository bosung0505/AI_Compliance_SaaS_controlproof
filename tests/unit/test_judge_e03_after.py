from __future__ import annotations

from engine.adapters.base import AdapterResult
from engine.judges.e03 import judge_e03_after
from engine.models import AssertionStatus, FaultBoundary, FaultVariant, Phase, Presence
from tests.fixtures.spec002 import EVENT_ID, boundary_receipt, reporting_effect


def _boundary():
    return boundary_receipt(
        fault_variant=FaultVariant.AFTER_RESULT_DURABLE_BEFORE_COMPLETION,
        boundary=FaultBoundary.AFTER_DB_COMMIT_BEFORE_SQS_ACK,
        one_shot_consumed=True,
    )


def _duplicate(**updates):
    receipt = {
        "outbox_event_id": str(EVENT_ID),
        "delivery_attempt": 2,
        "consumer_name": "reporting-worker",
        "handler_skipped": True,
        "acknowledged": True,
        **updates,
    }
    return AdapterResult(True, "DUPLICATE_ACK_READ", {"receipt": receipt})


def _restore(ok=True):
    return AdapterResult(
        ok,
        "ENVIRONMENT_RESTORED" if ok else "ENVIRONMENT_RESTORE_FAILED",
        {"marker_inactive": ok, "worker_healthy": ok},
    )


def _judge(**updates):
    values = {
        "source_event_id": EVENT_ID,
        "boundary": _boundary(),
        "duplicate_ack": _duplicate(),
        "committed_effects": (reporting_effect(phase=Phase.INJECTED),),
        "final_effects": (reporting_effect(phase=Phase.RECOVERED),),
        "dlq_presence": Presence.ABSENT,
        "restore": _restore(),
    }
    values.update(updates)
    return {item.assertion_id: item for item in judge_e03_after(**values)}


def test_complete_after_lineage_duplicate_ack_and_unchanged_effects_pass():
    result = _judge()
    assert tuple(result) == ("E03-A1", "E03-A5", "E03-A6", "E03-A8")
    assert all(item.status is AssertionStatus.PASS for item in result.values())


def test_handler_rerun_or_missing_duplicate_ack_fails_a6():
    rerun = _judge(duplicate_ack=_duplicate(handler_skipped=False))
    assert rerun["E03-A6"].status is AssertionStatus.FAIL

    missing = _judge(
        duplicate_ack=AdapterResult(False, "DUPLICATE_ACK_MISSING")
    )
    assert missing["E03-A6"].status is AssertionStatus.FAIL


def test_duplicate_or_changed_reporting_effects_fail_a5():
    duplicate = reporting_effect(
        effects={
            "logical_report_ids": ["report-01", "report-01"],
            "projection_document_ids": ["projection-01", "projection-01"],
            "projection_report_ids": ["report-01", "report-01"],
            "processed_keys": [
                {
                    "consumer_name": "reporting-worker",
                    "event_id": str(EVENT_ID),
                    "event_version": 1,
                },
                {
                    "consumer_name": "reporting-worker",
                    "event_id": str(EVENT_ID),
                    "event_version": 1,
                },
            ],
            "source_outbox_event_ids": [str(EVENT_ID)],
        },
        state_digest="f" * 64,
    )
    assert _judge(final_effects=(duplicate,))["E03-A5"].status is AssertionStatus.FAIL


def test_boundary_not_reached_is_inconclusive_for_after_specific_assertions():
    result = _judge(boundary=None)
    assert result["E03-A1"].status is AssertionStatus.INCONCLUSIVE
    assert result["E03-A5"].status is AssertionStatus.INCONCLUSIVE
    assert result["E03-A6"].status is AssertionStatus.INCONCLUSIVE
    assert result["E03-A8"].status is AssertionStatus.INCONCLUSIVE


def test_unexpected_dlq_is_failure_not_expected_after_behavior():
    result = _judge(dlq_presence=Presence.PRESENT)
    assert result["E03-A1"].status is AssertionStatus.FAIL
    assert result["E03-A8"].status is AssertionStatus.FAIL
