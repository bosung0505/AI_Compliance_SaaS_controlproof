"""US4 aggregate verdict contract; slice judges are covered separately."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from engine.models import (
    AssertionResult,
    AssertionStatus,
    InconclusiveReason,
    RunState,
    Verdict,
)

ASSERTIONS = tuple(f"N02-A{index}" for index in range(1, 8))
DECIDED_AT = datetime(2026, 10, 2, tzinfo=UTC)


def _assertion(index: int, status: AssertionStatus, reason=None) -> AssertionResult:
    return AssertionResult(
        assertion_id=f"N02-A{index}",
        subject_ref=f"synthetic-lane-{index}",
        status=status,
        expected={"protected": True},
        actual={"protected": status is AssertionStatus.PASS},
        reason_code=reason,
        detail="deterministic fixture result",
        source_requirements=(f"EV3-{index:02d}",),
    )


def _aggregate(assertions, *, state=RunState.COMPLETED, baseline_valid=True, verified=True):
    # T072 consumes this pure result when the six-lane executor is composed.
    from engine.judges.n02 import judge_n02_run

    return judge_n02_run(
        run_id=uuid4(),
        assertion_results=tuple(assertions),
        run_state=state,
        baseline_valid=baseline_valid,
        bundle_verified=verified,
        decided_at=DECIDED_AT,
    )


def test_all_seven_pass_only_with_verified_bundle() -> None:
    assertions = [_assertion(index, AssertionStatus.PASS) for index in range(1, 8)]
    judgement = _aggregate(assertions)
    assert judgement.verdict is Verdict.PASS
    assert tuple(item.assertion_id for item in judgement.assertion_results) == ASSERTIONS

    unverified = _aggregate(assertions, verified=False)
    assert unverified.verdict is Verdict.INCONCLUSIVE
    assert unverified.reason_code is InconclusiveReason.INSUFFICIENT_EVIDENCE


@pytest.mark.parametrize("failed_index", [2, 3, 4, 5, 6, 7])
def test_each_direct_violation_survives_another_missing_assertion(failed_index: int) -> None:
    assertions = [_assertion(index, AssertionStatus.PASS) for index in range(1, 8)]
    assertions[failed_index - 1] = _assertion(failed_index, AssertionStatus.FAIL)
    missing_index = 7 if failed_index != 7 else 2
    assertions[missing_index - 1] = _assertion(
        missing_index,
        AssertionStatus.INCONCLUSIVE,
        InconclusiveReason.INSUFFICIENT_EVIDENCE,
    )
    judgement = _aggregate(assertions)
    assert judgement.verdict is Verdict.FAIL
    by_id = {item.assertion_id: item for item in judgement.assertion_results}
    assert by_id[f"N02-A{failed_index}"].status is AssertionStatus.FAIL
    assert by_id[f"N02-A{missing_index}"].status is AssertionStatus.INCONCLUSIVE


def test_same_fact_conflict_precedes_missing_evidence_without_direct_fail() -> None:
    assertions = [_assertion(index, AssertionStatus.PASS) for index in range(1, 8)]
    assertions[2] = _assertion(
        3, AssertionStatus.INCONCLUSIVE, InconclusiveReason.EVIDENCE_CONFLICT
    )
    assertions[3] = _assertion(
        4, AssertionStatus.INCONCLUSIVE, InconclusiveReason.INSUFFICIENT_EVIDENCE
    )
    judgement = _aggregate(assertions)
    assert judgement.verdict is Verdict.INCONCLUSIVE
    assert judgement.reason_code is InconclusiveReason.EVIDENCE_CONFLICT


def test_invalid_pristine_baseline_aborts_without_product_fail() -> None:
    judgement = _aggregate(
        (_assertion(1, AssertionStatus.FAIL),),
        state=RunState.ABORTED,
        baseline_valid=False,
    )
    assert judgement.verdict is Verdict.INCONCLUSIVE
    assert judgement.reason_code is InconclusiveReason.INSUFFICIENT_EVIDENCE
    assert not any(
        item.status is AssertionStatus.FAIL and item.assertion_id != "N02-A1"
        for item in judgement.assertion_results
    )


def test_restore_failure_is_inconclusive_but_keeps_observed_direct_fail() -> None:
    assertions = [_assertion(index, AssertionStatus.PASS) for index in range(1, 8)]
    assertions[1] = _assertion(2, AssertionStatus.FAIL)
    judgement = _aggregate(assertions, state=RunState.RESTORE_FAILED)
    assert judgement.verdict is Verdict.INCONCLUSIVE
    assert judgement.reason_code is InconclusiveReason.INSUFFICIENT_EVIDENCE
    assert any(item.assertion_id == "N02-A2" and item.status is AssertionStatus.FAIL
               for item in judgement.assertion_results)
