from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import pytest

from engine.judges.n02 import (
    N02BaselinePreconditionError,
    N02BypassCase,
    judge_n02_bypass,
)
from engine.models import (
    AssertionStatus,
    N02EffectGroup,
    N02LaneId,
    Phase,
    Presence,
    ProcessingAttemptReceipt,
    ProcessingEntryKind,
    ProcessingResponseClass,
    ProtectedEffectSnapshot,
    ProtectedPathId,
    utcnow,
)


def _effect(path, lane, *, status=Presence.ABSENT, new=()):
    if new and status is Presence.ABSENT:
        status = Presence.PRESENT
    return ProtectedEffectSnapshot(
        run_id=RUN_ID,
        lane_id=lane,
        subject_ref=f"synthetic-{lane.value.casefold()}",
        path_id=path,
        phase=Phase.BASELINE if lane is N02LaneId.PRISTINE_BASELINE else Phase.INJECTED,
        step_id="fixture",
        attempt=1,
        effect_group=N02EffectGroup(path.value),
        current_effect_ids=new,
        new_effect_ids=new,
        source_status=status,
        source_error_code="DB_TIMEOUT" if status is Presence.UNAVAILABLE else None,
        state_digest="a" * 64,
        captured_at=utcnow(),
    )


def _attempt(path, lane, response=ProcessingResponseClass.DENIED):
    return ProcessingAttemptReceipt(
        run_id=RUN_ID,
        lane_id=lane,
        subject_ref=f"synthetic-{lane.value.casefold()}",
        path_id=path,
        entry_kind=(
            ProcessingEntryKind.DOMAIN_EVENT
            if path is ProtectedPathId.AI_ASSESSMENT
            else ProcessingEntryKind.HTTP
        ),
        operation_id=path.value,
        request_id=str(uuid4()),
        trace_id_digest="b" * 64,
        sent_at=utcnow(),
        response_at=utcnow(),
        response_class=response,
        status_code=403 if path is not ProtectedPathId.AI_ASSESSMENT else None,
        sanitized_reason_code="CONSENT_REQUIRED",
        source_ref="fixture",
    )


RUN_ID = uuid4()
LANES = {
    ProtectedPathId.DOCUMENT_ANALYSIS: N02LaneId.DOCUMENT_BYPASS,
    ProtectedPathId.RECORDING: N02LaneId.RECORDING_BOUNDARY_PROBE,
    ProtectedPathId.AI_ASSESSMENT: N02LaneId.ASSESSMENT_BOUNDARY_PROBE,
}


def _inputs():
    baseline = tuple(
        _effect(path, N02LaneId.PRISTINE_BASELINE) for path in ProtectedPathId
    )
    cases = tuple(
        N02BypassCase(
            path_id=path,
            lane_id=lane,
            attempt=_attempt(path, lane),
            effects=_effect(path, lane),
        )
        for path, lane in LANES.items()
    )
    return baseline, cases


def test_a1_to_a4_pass_only_for_pristine_and_denied_zero_delta() -> None:
    results = judge_n02_bypass(*_inputs())
    assert [item.assertion_id for item in results] == [f"N02-A{i}" for i in range(1, 5)]
    assert all(item.status is AssertionStatus.PASS for item in results)


@pytest.mark.parametrize("index", range(3))
def test_each_prohibited_effect_is_a_direct_fail(index: int) -> None:
    baseline, cases = _inputs()
    changed = list(cases)
    changed[index] = replace(
        changed[index],
        effects=_effect(changed[index].path_id, changed[index].lane_id, new=("new-1",)),
    )
    results = judge_n02_bypass(baseline, tuple(changed))
    assert results[index + 1].status is AssertionStatus.FAIL


def test_missing_post_effect_is_inconclusive() -> None:
    baseline, cases = _inputs()
    changed = list(cases)
    changed[0] = replace(
        changed[0],
        effects=_effect(
            ProtectedPathId.DOCUMENT_ANALYSIS,
            N02LaneId.DOCUMENT_BYPASS,
            status=Presence.UNAVAILABLE,
        ),
    )
    assert judge_n02_bypass(baseline, tuple(changed))[1].status is AssertionStatus.INCONCLUSIVE


def test_invalid_pristine_baseline_aborts_before_bypass_attempts() -> None:
    baseline, cases = _inputs()
    with pytest.raises(N02BaselinePreconditionError):
        judge_n02_bypass(
            (
                _effect(
                    ProtectedPathId.DOCUMENT_ANALYSIS,
                    N02LaneId.PRISTINE_BASELINE,
                    new=("x",),
                ),
                *baseline[1:],
            ),
            cases,
        )
