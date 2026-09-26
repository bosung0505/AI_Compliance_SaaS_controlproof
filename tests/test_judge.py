from datetime import UTC, datetime, timedelta

from engine.judge import judge
from engine.models import InconclusiveReason, Observation, Phase, Presence, Source, Verdict

T0 = datetime(2026, 9, 23, 9, 0, tzinfo=UTC)


def obs(run_id, key, value=None, *, presence=Presence.PRESENT, at=None, source=Source.HTTP):
    return Observation(
        run_id=run_id,
        subject_ref="candidate-01",
        phase=Phase.INJECTED,
        step_id="legacy-rule-test",
        attempt=1,
        key=key,
        value=value if presence is Presence.PRESENT else None,
        presence=presence,
        source_type=source,
        source_ref="fixture",
        observed_at=at or T0,
        error_code="UNAVAILABLE" if presence is Presence.UNAVAILABLE else None,
    )


def test_state_equals_pass_and_fail(run_factory):
    run = run_factory()
    rules = [{"type": "state_equals", "subject": "invitation.status", "equals": "completed"}]
    ok = judge(run, rules, [obs(run.run_id, "invitation.status", "completed")], decided_at=T0)
    assert ok.verdict is Verdict.PASS
    bad = judge(run, rules, [obs(run.run_id, "invitation.status", "reviewed")], decided_at=T0)
    assert bad.verdict is Verdict.FAIL


def test_missing_and_unavailable_are_inconclusive(run_factory):
    run = run_factory()
    rules = [{"type": "state_equals", "subject": "invitation.status", "equals": "completed"}]
    missing = judge(run, rules, [], decided_at=T0)
    assert missing.reason_code is InconclusiveReason.INSUFFICIENT_EVIDENCE
    unavailable = judge(
        run,
        rules,
        [obs(run.run_id, "invitation.status", presence=Presence.UNAVAILABLE)],
        decided_at=T0,
    )
    assert unavailable.verdict is Verdict.INCONCLUSIVE


def test_event_order_and_time_limit(run_factory):
    run = run_factory(scenario_id="N-02")
    ordered = judge(
        run,
        [{"type": "event_order", "before": "event.consent", "after": "event.analysis"}],
        [
            obs(run.run_id, "event.consent", True, at=T0),
            obs(run.run_id, "event.analysis", True, at=T0 + timedelta(seconds=3)),
        ],
        decided_at=T0,
    )
    assert ordered.verdict is Verdict.PASS
    late = judge(
        run,
        [{"type": "time_limit", "from": "event.consent", "to": "event.analysis", "within": "5m"}],
        [
            obs(run.run_id, "event.consent", True, at=T0),
            obs(run.run_id, "event.analysis", True, at=T0 + timedelta(minutes=9)),
        ],
        decided_at=T0,
    )
    assert late.verdict is Verdict.FAIL


def test_fields_present_checks_queried_absence(run_factory):
    run = run_factory()
    rules = [{"type": "fields_present", "present": ["error"], "absent": ["decision"]}]
    clean = judge(
        run,
        rules,
        [
            obs(run.run_id, "error", {"code": 503}),
            obs(run.run_id, "decision", presence=Presence.ABSENT, source=Source.DB),
        ],
        decided_at=T0,
    )
    assert clean.verdict is Verdict.PASS


def test_same_dimension_conflict_is_inconclusive(run_factory):
    run = run_factory()
    rules = [{"type": "state_equals", "subject": "invitation.status", "equals": "completed"}]
    result = judge(
        run,
        rules,
        [
            obs(run.run_id, "invitation.status", "completed", source=Source.HTTP),
            obs(run.run_id, "invitation.status", "reviewed", source=Source.DB),
        ],
        decided_at=T0,
    )
    assert result.reason_code is InconclusiveReason.EVIDENCE_CONFLICT


def test_no_test_target_skips_rules(run_factory):
    run = run_factory(scenario_id="A-01")
    result = judge(
        run,
        [{"type": "state_equals", "subject": "x", "equals": "y"}],
        [],
        decided_at=T0,
        no_test_target=True,
    )
    assert result.reason_code is InconclusiveReason.NO_TEST_TARGET
