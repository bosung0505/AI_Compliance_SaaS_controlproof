from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from engine.models import ComparatorKind, ComparatorPolicy, Observation, Phase, Presence, Source
from engine.observations import conflicting_dimensions, stable_observation, values_equal

T0 = datetime(2026, 9, 24, tzinfo=UTC)


def make(run, value, *, phase=Phase.INJECTED, step="observe", attempt=1, source=Source.HTTP, at=T0):
    return Observation(
        run_id=run.run_id,
        subject_ref="candidate-01",
        phase=phase,
        step_id=step,
        attempt=attempt,
        key="pipeline.row_version",
        presence=Presence.PRESENT,
        value=value,
        source_type=source,
        source_ref=source.value,
        observed_at=at,
    )


def test_absent_and_unavailable_are_distinct(run_factory):
    run = run_factory()
    absent = Observation(
        run_id=run.run_id,
        subject_ref="candidate-01",
        phase=Phase.BASELINE,
        step_id="baseline",
        attempt=1,
        key="final_decision.latest_actor_type",
        presence=Presence.ABSENT,
        source_type=Source.DB,
        source_ref="fixture",
    )
    unavailable = absent.model_copy(
        update={"presence": Presence.UNAVAILABLE, "error_code": "ACCESS_DENIED"}
    )
    assert absent.presence is Presence.ABSENT
    assert unavailable.presence is Presence.UNAVAILABLE


def test_only_same_complete_dimension_conflicts(run_factory):
    run = run_factory()
    first = make(run, 1, source=Source.HTTP)
    same_dimension = make(run, 2, source=Source.DB)
    other_step = make(run, 2, step="later", source=Source.DB)
    assert conflicting_dimensions([first, same_dimension])
    assert not conflicting_dimensions([first, other_step])


def test_exact_is_type_strict_and_timestamp_metadata_is_irrelevant():
    assert not values_equal("1", 1)
    assert values_equal(1, 1)


def test_absolute_tolerance_is_explicit_and_nonnegative():
    policy = ComparatorPolicy(
        kind=ComparatorKind.ABSOLUTE_TOLERANCE,
        value_type="decimal",
        tolerance=0.1,
    )
    assert values_equal(1.0, 1.05, policy)
    assert not values_equal(1.0, "1.0", policy)
    with pytest.raises(ValidationError):
        ComparatorPolicy(
            kind=ComparatorKind.ABSOLUTE_TOLERANCE,
            value_type="decimal",
            tolerance=-1,
        )


def test_stability_requires_consecutive_duration(run_factory):
    run = run_factory()
    timeline = [
        make(run, 1, attempt=index + 1, at=T0 + timedelta(seconds=index * 2)) for index in range(3)
    ]
    assert stable_observation(timeline) == timeline[-1]
