"""T061 — verdict matrix and precedence for both Spec 004 profiles (FR-040, SC-001).

RESTORE_FAILED → INCONCLUSIVE; direct FAIL; same-fact conflict → INCONCLUSIVE:EVIDENCE_CONFLICT; insufficient evidence
or precondition → INCONCLUSIVE; all PASS → PASS.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from engine.executors.report_lanes import judge_spec004_run, unassessed
from engine.models import (
    AssertionResult,
    AssertionStatus,
    InconclusiveReason,
    RunState,
    Verdict,
)
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters
from tests.fixtures.fake_spec004 import FakeSpec004Adapters, use_spec004_fixture


def _judgement(tmp_path, scenario, **options):
    adapters, _ = make_adapters(spec004=FakeSpec004Adapters(**options))
    use_spec004_fixture(adapters)
    runner = build_profile_runner(load(f"scenarios/{scenario}.yaml"), adapters, tmp_path, clock=FakeClock())
    run, judgement, _ = runner.execute(runner.preflight("whyyou-local"))
    return run, judgement


@pytest.mark.parametrize(
    "scenario,options,verdict,reason",
    [
        ("E-01", {"removal_indicator": "score_null"}, Verdict.PASS, None),
        ("E-01", {}, Verdict.FAIL, None),
        ("E-01", {"removal_indicator": "score_null", "citation_storage": "STORE_AS_EMITTED"}, Verdict.FAIL, None),
        ("E-01", {"restore_mismatch": True}, Verdict.INCONCLUSIVE, InconclusiveReason.INSUFFICIENT_EVIDENCE),
        ("E-01", {"removal_indicator": "score_null", "emissions_available": False},
         Verdict.INCONCLUSIVE, InconclusiveReason.INSUFFICIENT_EVIDENCE),
        ("E-01", {"removal_indicator": "score_null", "refuse_lanes": frozenset({"E01_CITATION_MATRIX"})},
         Verdict.INCONCLUSIVE, InconclusiveReason.INSUFFICIENT_EVIDENCE),
        ("E-02", {}, Verdict.PASS, None),
        ("E-02", {"report_mutates_after_change": True}, Verdict.FAIL, None),
        ("E-02", {"report_mutates_after_change": True, "teardown_fails": True},
         Verdict.INCONCLUSIVE, InconclusiveReason.INSUFFICIENT_EVIDENCE),
        ("E-02", {"second_version_binding_wrong": True},
         Verdict.INCONCLUSIVE, InconclusiveReason.INSUFFICIENT_EVIDENCE),
    ],
)
def test_profile_verdict_matrix(tmp_path, scenario, options, verdict, reason) -> None:
    run, judgement = _judgement(tmp_path, scenario, **options)
    assert judgement.verdict is verdict, [(a.assertion_id, a.status, a.detail) for a in judgement.assertion_results]
    assert judgement.reason_code is reason
    if options.get("restore_mismatch") or options.get("teardown_fails"):
        assert run.state is RunState.RESTORE_FAILED


def _result(assertion_id, status, reason=None):
    return AssertionResult(
        assertion_id=assertion_id,
        subject_ref="matrix",
        status=status,
        expected={},
        actual={},
        reason_code=reason,
        detail="matrix",
        source_requirements=("FR-040",),
    )


def _aggregate(results, state=RunState.COMPLETED):
    return judge_spec004_run(
        run_id=uuid4(),
        scenario_id="E-02",
        assertion_ids=("E02-A1", "E02-A2", "E02-A3"),
        assertion_results=results,
        run_state=state,
        decided_at=datetime.now(UTC),
    )


def test_precedence_restore_failed_over_fail_over_conflict() -> None:
    fail = _result("E02-A1", AssertionStatus.FAIL)
    conflict = _result("E02-A2", AssertionStatus.INCONCLUSIVE, InconclusiveReason.EVIDENCE_CONFLICT)
    passed = _result("E02-A3", AssertionStatus.PASS)
    assert _aggregate((fail, conflict, passed), RunState.RESTORE_FAILED).verdict is Verdict.INCONCLUSIVE
    assert _aggregate((fail, conflict, passed)).verdict is Verdict.FAIL
    mixed = _aggregate((_result("E02-A1", AssertionStatus.PASS), conflict, passed))
    assert (mixed.verdict, mixed.reason_code) == (Verdict.INCONCLUSIVE, InconclusiveReason.EVIDENCE_CONFLICT)


def test_missing_assertion_is_unassessed_not_pass() -> None:
    judgement = _aggregate((_result("E02-A1", AssertionStatus.PASS),))
    assert judgement.verdict is Verdict.INCONCLUSIVE
    assert set(judgement.missing_evidence) == {"E02-A2", "E02-A3"}
    placeholder = unassessed("E02-A2", "x", "PRECONDITION_NOT_MET: x", ("FR-031",))
    assert placeholder.status is AssertionStatus.INCONCLUSIVE
