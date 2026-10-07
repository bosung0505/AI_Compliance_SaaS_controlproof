"""T045 — E01-A3/A4 and the E01-D1 diagnostic (contracts/scenario-profile-v4.md).

RED until T049 adds `judge_e01_removal`, `judge_e01_restore` and `storage_probe_exposure` to
`engine/judges/e01.py`. H-4 (a): any of the four indicators on every affected axis/item is a PASS.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from engine.adapters.base import AdapterResult
from engine.models import (
    AssertionStatus,
    ChangeInjection,
    ChangeInjectionKind,
    ChangeInjectionState,
    E01LaneId,
    Presence,
    ReportReadSnapshot,
    ReportRecordSnapshot,
    RestoreAction,
)

SEG_A, SEG_B = str(uuid4()), str(uuid4())
EV_A, EV_B = str(uuid4()), str(uuid4())
ITEM_A, ITEM_B = str(uuid4()), str(uuid4())
RUN = uuid4()
NOW = datetime(2026, 10, 7, tzinfo=UTC)


def e01():
    from engine.judges import e01 as module

    return module


def _item(item_id, evidence_id, segment_id, *, score=80):
    return {
        "report_item_id": item_id,
        "criterion_id": str(uuid4()),
        "assessment_state": "confirmed",
        "average_score": score,
        "axis_assessments": [
            {"axis": "correctness", "score": score, "quoted_evidence_ids": [evidence_id]}
        ],
        "evidence": [{"evidence_id": evidence_id, "transcript_segment_id": segment_id}],
    }


ITEMS = [_item(ITEM_A, EV_A, SEG_A), _item(ITEM_B, EV_B, SEG_B, score=70)]


def _read(phase, items=None, *, status=200, unknown=()):
    body = None if status != 200 else {"status": "ready", "items": items or copy.deepcopy(ITEMS)}
    return ReportReadSnapshot(
        phase=phase,
        request_id=uuid4(),
        status_code=status,
        report=body,
        unknown_fields=unknown,
        read_digest="a" * 64,
    )


def _injection(*, confirmed=True, state=ChangeInjectionState.APPLIED, post=None):
    values = {
        "injection_id": uuid4(),
        "kind": ChangeInjectionKind.EVIDENCE_SEGMENT_REMOVAL,
        "run_id": RUN,
        "lane_id": E01LaneId.E01_EVIDENCE_REMOVAL,
        "subject_ref": "removal",
        "target_table": "transcript_segments",
        "target_ids": (UUID(SEG_A),),
        "pre_projection_digest": "b" * 64,
        "applied_at": NOW,
        "apply_receipt": {"affected_rows": 1, "absence_confirmed": confirmed},
        "restore_action": RestoreAction.REINSERT,
        "state": state,
    }
    if state is ChangeInjectionState.RESTORED:
        values |= {"restored_at": NOW, "post_restore_digest": "b" * 64}
    if state is ChangeInjectionState.RESTORE_FAILED:
        values |= {"failure_code": "RESTORE_DIGEST_MISMATCH", "post_restore_digest": post}
    return ChangeInjection(**values)


def _affected(**changes):
    items = copy.deepcopy(ITEMS)
    items[0] |= changes.pop("item", {})
    if "axis" in changes:
        items[0]["axis_assessments"][0] |= changes.pop("axis")
    if "evidence" in changes:
        items[0]["evidence"][0] |= changes.pop("evidence")
    return items


def _a3(post, *, injection=None, pre=None):
    return e01().judge_e01_removal(
        injection=injection or _injection(), pre=pre or _read("PRE_REMOVAL"), post=post
    )


@pytest.mark.parametrize(
    "items",
    [
        _affected(axis={"score": None}),
        _affected(item={"average_score": None}),
        _affected(item={"assessment_state": "insufficient_evidence"}),
        _affected(item={"assessment_state": "needs_follow_up"}),
        _affected(evidence={"playable": False}),
        _affected(evidence={"available": False}),
        _affected(evidence={"transcript_available": False}),
    ],
    ids=["axis-null", "average-null", "insufficient", "follow-up", "playable", "available", "transcript"],
)
def test_each_h4_indicator_passes(items) -> None:
    result = _a3(_read("POST_REMOVAL", items))
    assert result.status is AssertionStatus.PASS, result.detail


def test_unchanged_score_and_citation_fails_as_p1() -> None:
    result = _a3(_read("POST_REMOVAL"))
    assert result.status is AssertionStatus.FAIL
    assert "P1" in result.detail


def test_unaffected_item_change_fails() -> None:
    items = _affected(axis={"score": None})
    items[1]["average_score"] = 10
    assert _a3(_read("POST_REMOVAL", items)).status is AssertionStatus.FAIL


def test_post_removal_5xx_fails() -> None:
    result = _a3(_read("POST_REMOVAL", status=500))
    assert result.status is AssertionStatus.FAIL
    assert "REPORT_UNREADABLE_AFTER_REMOVAL" in result.detail


@pytest.mark.parametrize(
    "case",
    ["unconfirmed", "adapter-refused", "pre-failed", "unknown-fields"],
)
def test_preconditions_and_ambiguity_are_inconclusive(case) -> None:
    post = _read("POST_REMOVAL", _affected(axis={"score": None}))
    kwargs = {}
    if case == "unconfirmed":
        kwargs["injection"] = _injection(confirmed=False)
    elif case == "adapter-refused":
        kwargs["injection"] = AdapterResult(False, "SEGMENT_NOT_FOUND")
    elif case == "pre-failed":
        kwargs["pre"] = _read("PRE_REMOVAL", status=503)
    else:
        post = _read("POST_REMOVAL", _affected(axis={"score": None}), unknown=("new_flag",))
    if case == "adapter-refused":
        result = e01().judge_e01_removal(injection=kwargs["injection"], pre=_read("PRE_REMOVAL"), post=post)
    else:
        result = _a3(post, **kwargs)
    assert result.status is AssertionStatus.INCONCLUSIVE
    assert result.reason_code.value == "INSUFFICIENT_EVIDENCE"


def _record(phase, digest):
    return ReportRecordSnapshot(
        run_id=RUN,
        lane_id=E01LaneId.E01_EVIDENCE_REMOVAL,
        subject_ref="removal",
        phase=phase,
        report_id=uuid4(),
        source_status=Presence.PRESENT,
        state_digest=digest,
    )


def _a4(post_read, *, injection=None, post_digest="c" * 64):
    return e01().judge_e01_restore(
        injection=injection or _injection(state=ChangeInjectionState.RESTORED),
        pre_read=_read("PRE_REMOVAL"),
        post_restore_read=post_read,
        pre_record=_record("PRE_REMOVAL", "c" * 64),
        post_restore_record=_record("POST_RESTORE", post_digest),
    )


def test_restore_returns_the_pre_removal_read() -> None:
    assert _a4(_read("POST_RESTORE")).status is AssertionStatus.PASS


def test_safe_restore_with_a_different_read_fails() -> None:
    assert _a4(_read("POST_RESTORE", _affected(axis={"score": None}))).status is AssertionStatus.FAIL
    assert _a4(_read("POST_RESTORE"), post_digest="d" * 64).status is AssertionStatus.FAIL


def test_restore_failure_is_not_an_a4_verdict() -> None:
    failed = _injection(state=ChangeInjectionState.RESTORE_FAILED, post="9" * 64)
    result = _a4(_read("POST_RESTORE"), injection=failed)
    assert result.status is AssertionStatus.INCONCLUSIVE


def test_storage_probe_exposure_is_recorded_per_mode() -> None:
    written = [
        {"mode": "EMPTY", "axis": "correctness", "score": 80, "quoted_evidence_ids": []},
        {"mode": "NONEXISTENT", "axis": "depth", "score": 80, "quoted_evidence_ids": [str(uuid4())]},
        {"mode": "OTHER_APPLICANT", "axis": "fundamentals", "score": 80, "quoted_evidence_ids": [EV_B]},
    ]
    item = _item(ITEM_A, EV_A, SEG_A)
    item["axis_assessments"] = [
        {"axis": "depth", "score": 80, "quoted_evidence_ids": written[1]["quoted_evidence_ids"]},
        {"axis": "fundamentals", "score": None, "quoted_evidence_ids": [EV_B]},
    ]
    exposure = e01().storage_probe_exposure(
        written_axes=written, read=_read("POST_PROBE", [item]), report_item_id=ITEM_A
    )
    assert {row["mode"]: row["exposure"] for row in exposure} == {
        "EMPTY": "AXIS_DROPPED",
        "NONEXISTENT": "SHOWN_AS_WRITTEN",
        "OTHER_APPLICANT": "SCORE_HIDDEN",
    }
    errors = e01().storage_probe_exposure(
        written_axes=written, read=_read("POST_PROBE", status=500), report_item_id=ITEM_A
    )
    assert {row["exposure"] for row in errors} == {"READ_ERROR"}
