from datetime import UTC, datetime, timedelta

from engine.judge import judge
from engine.models import InconclusiveReason, Observation, Run, Source, Verdict

T0 = datetime(2026, 9, 23, 9, 0, tzinfo=UTC)


def run_of(scenario="H-03"):
    return Run(scenario_id=scenario, started_at=T0, seed_kind="state")


def obs(key, value=None, *, absent=False, at=None, source=Source.API):
    return Observation(key=key, value=value, absent=absent, occurred_at=at, source=source)


def test_state_equals_pass_and_fail():
    rules = [{"type": "state_equals", "subject": "invitation.state", "equals": "completed"}]
    ok = judge(run_of(), rules, [obs("invitation.state", "completed")], decided_at=T0)
    assert ok.verdict is Verdict.PASS

    bad = judge(run_of(), rules, [obs("invitation.state", "reviewed")], decided_at=T0)
    assert bad.verdict is Verdict.FAIL


def test_missing_observation_is_inconclusive_not_pass():
    """관찰하지 못한 것을 통과시키지 않는다. 제품 원칙 16.1."""
    rules = [{"type": "state_equals", "subject": "invitation.state", "equals": "completed"}]
    result = judge(run_of(), rules, [], decided_at=T0)
    assert result.verdict is Verdict.INCONCLUSIVE
    assert result.reason is InconclusiveReason.INSUFFICIENT_EVIDENCE
    assert result.missing_evidence == ("invitation.state",)


def test_event_order_strict():
    rules = [{
        "type": "event_order",
        "before": "event.consent_completed",
        "after": "event.analysis_requested",
        "strict": True,
    }]
    good = judge(run_of("N-02"), rules, [
        obs("event.consent_completed", at=T0),
        obs("event.analysis_requested", at=T0 + timedelta(seconds=3)),
    ], decided_at=T0)
    assert good.verdict is Verdict.PASS

    reversed_ = judge(run_of("N-02"), rules, [
        obs("event.consent_completed", at=T0 + timedelta(seconds=3)),
        obs("event.analysis_requested", at=T0),
    ], decided_at=T0)
    assert reversed_.verdict is Verdict.FAIL


def test_time_limit():
    rules = [{
        "type": "time_limit",
        "from": "event.consent_completed",
        "to": "event.analysis_started",
        "within": "5m",
    }]
    late = judge(run_of("N-02"), rules, [
        obs("event.consent_completed", at=T0),
        obs("event.analysis_started", at=T0 + timedelta(minutes=9)),
    ], decided_at=T0)
    assert late.verdict is Verdict.FAIL


def test_fields_present_absent_list_is_the_real_check():
    """H-03 의 핵심은 '있으면 안 되는 것'이 없는지다."""
    rules = [{
        "type": "fields_present",
        "source": "장애 중 저장 상태",
        "present": ["error.record"],
        "absent": ["human_review.record", "event.stage_moved"],
    }]
    clean = judge(run_of(), rules, [
        obs("error.record", {"code": 503}),
        obs("human_review.record", absent=True, source=Source.LOG),
        obs("event.stage_moved", absent=True, source=Source.LOG),
    ], decided_at=T0)
    assert clean.verdict is Verdict.PASS

    half_saved = judge(run_of(), rules, [
        obs("error.record", {"code": 503}),
        obs("human_review.record", {"decision": "advance"}, source=Source.LOG),
        obs("event.stage_moved", absent=True, source=Source.LOG),
    ], decided_at=T0)
    assert half_saved.verdict is Verdict.FAIL
    assert "있어야" not in half_saved.summary
    assert "없어야" in half_saved.summary


def test_unqueried_absent_key_is_inconclusive():
    """없어야 할 것을 '조회하지 못한' 경우, 없다고 단정하지 않는다."""
    rules = [{"type": "fields_present", "source": "x", "absent": ["human_review.record"]}]
    result = judge(run_of(), rules, [], decided_at=T0)
    assert result.verdict is Verdict.INCONCLUSIVE


def test_fail_beats_inconclusive():
    """관찰된 실패는 다른 증적을 못 얻었다고 사라지지 않는다."""
    rules = [
        {"type": "state_equals", "subject": "invitation.state", "equals": "completed"},
        {"type": "state_equals", "subject": "invitation.stage", "equals": "검토"},
    ]
    result = judge(run_of(), rules, [obs("invitation.state", "reviewed")], decided_at=T0)
    assert result.verdict is Verdict.FAIL


def test_conflicting_observations():
    rules = [{"type": "state_equals", "subject": "invitation.state", "equals": "completed"}]
    result = judge(run_of(), rules, [
        obs("invitation.state", "completed", source=Source.API),
        obs("invitation.state", "reviewed", source=Source.LOG),
    ], decided_at=T0)
    assert result.verdict is Verdict.INCONCLUSIVE
    assert result.reason is InconclusiveReason.EVIDENCE_CONFLICT


def test_no_test_target_skips_rules():
    """대상이 없으면 규칙을 평가하지 않는다. A-01~03 이 여기 해당한다."""
    rules = [{"type": "state_equals", "subject": "invitation.state", "equals": "x"}]
    result = judge(run_of("A-01"), rules, [], decided_at=T0, no_test_target=True)
    assert result.verdict is Verdict.INCONCLUSIVE
    assert result.reason is InconclusiveReason.NO_TEST_TARGET
    assert result.rule_results == ()
