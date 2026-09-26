from engine.models import Phase, Presence
from engine.observations import conflicting_dimensions


def test_changes_across_phase_step_or_attempt_are_not_conflicts(observation_factory):
    base = observation_factory(key="state", value="before")
    rows = [
        base,
        base.model_copy(update={"phase": Phase.INJECTED, "value": "after"}),
        base.model_copy(update={"step_id": "other", "value": "after"}),
        base.model_copy(update={"attempt": 2, "value": "after"}),
    ]
    assert conflicting_dimensions(rows) == {}


def test_same_dimension_present_absent_is_a_conflict(observation_factory):
    present = observation_factory(key="report", value="queued")
    absent = present.model_copy(update={"presence": Presence.ABSENT, "value": None})
    assert present.dimension in conflicting_dimensions([present, absent])


def test_unavailable_is_missing_evidence_not_a_conflict(observation_factory):
    unavailable = observation_factory(
        key="report",
        value=None,
        presence=Presence.UNAVAILABLE,
        error_code="TIMEOUT",
    )
    assert conflicting_dimensions([unavailable]) == {}
