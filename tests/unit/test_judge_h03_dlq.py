from __future__ import annotations

from engine.judges.h03_dlq import judge_h03_dlq
from engine.models import AssertionStatus, InconclusiveReason, Presence
from tests.fixtures.spec002 import delivery_attempt, terminal_failure


def test_h03_a8_passes_only_for_complete_attempt_lineage_and_matching_terminal_failure():
    result = judge_h03_dlq(
        attempts=tuple(delivery_attempt(delivery_attempt=index) for index in range(1, 4)),
        terminal=terminal_failure(),
        dlq_presence=Presence.PRESENT,
        ui_status="final_failed",
        api_status="failed",
        operator_locator="localstack:sqs:iep-reporting-dlq",
    )
    assert result[0].assertion_id == "H03-A8"
    assert result[0].status is AssertionStatus.PASS
    assert result[1].status is AssertionStatus.PASS


def test_missing_or_unlinked_dlq_record_is_fail_not_inconclusive():
    attempts = tuple(delivery_attempt(delivery_attempt=index) for index in range(1, 4))
    absent = judge_h03_dlq(
        attempts=attempts,
        terminal=None,
        dlq_presence=Presence.ABSENT,
        ui_status="final_failed",
        api_status="failed",
        operator_locator=None,
    )
    assert absent[0].status is AssertionStatus.FAIL

    unlinked = judge_h03_dlq(
        attempts=attempts,
        terminal=terminal_failure(source_event_id="00000000-0000-7000-8000-000000009999"),
        dlq_presence=Presence.PRESENT,
        ui_status="final_failed",
        api_status="failed",
        operator_locator="localstack:sqs:iep-reporting-dlq",
    )
    assert unlinked[0].status is AssertionStatus.FAIL


def test_access_loss_is_inconclusive_and_never_guessed_as_absent():
    results = judge_h03_dlq(
        attempts=(),
        terminal=None,
        dlq_presence=Presence.UNAVAILABLE,
        ui_status=None,
        api_status=None,
        operator_locator=None,
    )
    assert results[0].status is AssertionStatus.INCONCLUSIVE
    assert results[0].reason_code is InconclusiveReason.ACCESS_LIMITED

    attempts_unavailable = judge_h03_dlq(
        attempts=(),
        attempts_presence=Presence.UNAVAILABLE,
        terminal=terminal_failure(),
        dlq_presence=Presence.PRESENT,
        ui_status="final_failed",
        api_status="failed",
        operator_locator="localstack:sqs:iep-reporting-dlq",
    )
    assert attempts_unavailable[0].status is AssertionStatus.INCONCLUSIVE
    assert attempts_unavailable[0].reason_code is InconclusiveReason.ACCESS_LIMITED


def test_queued_forever_or_missing_operator_locator_fails_visibility_assertion():
    common = {
        "attempts": tuple(delivery_attempt(delivery_attempt=index) for index in range(1, 4)),
        "terminal": terminal_failure(),
        "dlq_presence": Presence.PRESENT,
        "api_status": "failed",
    }
    queued = judge_h03_dlq(
        **common,
        ui_status="queued_only",
        operator_locator="localstack:sqs:iep-reporting-dlq",
    )
    missing_locator = judge_h03_dlq(
        **common,
        ui_status="final_failed",
        operator_locator=None,
    )
    assert queued[1].status is AssertionStatus.FAIL
    assert missing_locator[1].status is AssertionStatus.FAIL


def test_successful_absent_report_query_fails_visibility_instead_of_becoming_unknown():
    results = judge_h03_dlq(
        attempts=tuple(delivery_attempt(delivery_attempt=index) for index in range(1, 4)),
        terminal=terminal_failure(),
        dlq_presence=Presence.PRESENT,
        ui_status="final_failed",
        api_status="absent",
        operator_locator="localstack:sqs:iep-reporting-dlq",
    )
    assert results[1].status is AssertionStatus.FAIL


def test_conflicting_dlq_evidence_is_inconclusive():
    results = judge_h03_dlq(
        attempts=tuple(delivery_attempt(delivery_attempt=index) for index in range(1, 4)),
        terminal=terminal_failure(),
        dlq_presence=Presence.PRESENT,
        ui_status="final_failed",
        api_status="failed",
        operator_locator="localstack:sqs:iep-reporting-dlq",
        evidence_conflict=True,
    )
    assert all(result.status is AssertionStatus.INCONCLUSIVE for result in results)
    assert all(result.reason_code is InconclusiveReason.EVIDENCE_CONFLICT for result in results)
