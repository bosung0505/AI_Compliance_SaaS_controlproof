"""Observation normalization, comparison, stability, and conflict detection."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any

from engine.models import ComparatorKind, ComparatorPolicy, Observation, Presence

H03_COMPARATOR_TYPES: dict[str, str] = {
    "fault.marker.applied": "boolean",
    "fault.effect.receipt_match": "boolean",
    "report.api.presence": "string",
    "report.api.status": "string",
    "report.ui.ready_content_visible": "boolean",
    "report.ui.status_class": "string",
    "decision.attempt.accepted": "boolean",
    "decision.attempt.reason_present": "boolean",
    "decision.attempt.reason_code": "string",
    "invitation.status": "string",
    "recruiting.stage_id": "string",
    "pipeline.row_version": "integer",
    "final_decision.count": "integer",
    "final_decision.latest_actor_type": "string",
    "fault.environment_restore": "string",
    "report.processing_recovery": "string",
}

H03_EXACT_COMPARATORS = {
    key: ComparatorPolicy(kind=ComparatorKind.EXACT, value_type=value_type)
    for key, value_type in H03_COMPARATOR_TYPES.items()
}


def validate(keys: list[str]) -> list[str]:
    """Return observation keys unknown to the H-03 registry."""
    return [key for key in keys if key not in H03_EXACT_COMPARATORS]


def normalize_presence(
    *,
    queried: bool,
    exists: bool | None,
    value: Any = None,
    error_code: str | None = None,
) -> tuple[Presence, Any, str | None]:
    if not queried:
        if not error_code:
            raise ValueError("unavailable observation requires an error code")
        return Presence.UNAVAILABLE, None, error_code
    if exists is False:
        return Presence.ABSENT, None, None
    if exists is not True or value is None:
        raise ValueError("successful present observation requires a value")
    return Presence.PRESENT, value, None


def values_equal(left: Any, right: Any, policy: ComparatorPolicy | None = None) -> bool:
    """Compare without implicit coercion; observed timestamps are never passed here."""
    active = policy or ComparatorPolicy(kind=ComparatorKind.EXACT, value_type=_type_name(left))
    if active.kind is ComparatorKind.EXACT:
        return type(left) is type(right) and left == right
    if type(left) is not type(right):
        return False
    if isinstance(left, bool) or not isinstance(left, (int, float, Decimal, datetime)):
        return False
    if isinstance(left, datetime):
        if left.tzinfo is None or right.tzinfo is None:
            return False
        distance = abs((left - right).total_seconds())
    else:
        distance = abs(Decimal(str(left)) - Decimal(str(right)))
    return distance <= Decimal(str(active.tolerance))


def _type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, (float, Decimal)):
        return "decimal"
    if isinstance(value, datetime):
        return "datetime"
    return "string"


def conflicting_dimensions(
    observations: Iterable[Observation],
    comparators: dict[str, ComparatorPolicy] | None = None,
) -> dict[tuple, tuple[Observation, ...]]:
    """Return only contradictions inside the complete logical identity dimension."""
    policies = comparators or {}
    grouped: dict[tuple, list[Observation]] = defaultdict(list)
    for observation in observations:
        grouped[observation.dimension].append(observation)

    conflicts: dict[tuple, tuple[Observation, ...]] = {}
    for dimension, rows in grouped.items():
        non_unavailable = [row for row in rows if row.presence is not Presence.UNAVAILABLE]
        if len(non_unavailable) < 2:
            continue
        first = non_unavailable[0]
        policy = policies.get(first.key)
        if any(not _observations_equal(first, other, policy) for other in non_unavailable[1:]):
            conflicts[dimension] = tuple(rows)
    return conflicts


def _observations_equal(
    left: Observation,
    right: Observation,
    policy: ComparatorPolicy | None,
) -> bool:
    if left.presence is not right.presence:
        return False
    if left.presence is Presence.ABSENT:
        return True
    return values_equal(left.value, right.value, policy)


def stable_observation(
    timeline: Sequence[Observation],
    *,
    consecutive: int = 3,
    minimum_seconds: float = 4.0,
    comparator: ComparatorPolicy | None = None,
) -> Observation | None:
    """Return the last value when it remains equivalent for the configured stable window."""
    if consecutive < 1:
        raise ValueError("consecutive must be positive")
    if len(timeline) < consecutive:
        return None
    ordered = list(timeline)
    tail = ordered[-consecutive:]
    last = tail[-1]
    if any(not _observations_equal(tail[0], row, comparator) for row in tail[1:]):
        return None
    elapsed = (last.observed_at - tail[0].observed_at).total_seconds()
    return last if elapsed >= minimum_seconds else None


def last_stable_observation(
    timeline: Sequence[Observation],
    *,
    consecutive: int = 3,
    minimum_seconds: float = 4.0,
    comparator: ComparatorPolicy | None = None,
) -> Observation | None:
    """Return the most recent completed stable window, ignoring a later transient tail."""
    if consecutive < 1:
        raise ValueError("consecutive must be positive")
    candidate: Observation | None = None
    for end in range(consecutive, len(timeline) + 1):
        window = timeline[end - consecutive : end]
        if any(not _observations_equal(window[0], row, comparator) for row in window[1:]):
            continue
        elapsed = (window[-1].observed_at - window[0].observed_at).total_seconds()
        if elapsed >= minimum_seconds:
            candidate = window[-1]
    return candidate


class ObservationTimeline:
    """Append-only in-memory view; durable append is owned by EvidenceBundleWriter."""

    def __init__(self) -> None:
        self._rows: list[Observation] = []

    def append(self, observation: Observation) -> None:
        self._rows.append(observation)

    @property
    def rows(self) -> tuple[Observation, ...]:
        return tuple(self._rows)

    def by_key(self, key: str) -> tuple[Observation, ...]:
        return tuple(row for row in self._rows if row.key == key)
