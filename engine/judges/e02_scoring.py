"""Independent copy of WhyYou's report scoring rule (Spec 004 plan §6, research R-008).

ControlProof recomputes a report's scores from the frozen inputs it reads back and compares the result with
the stored `overall_score`, `scoring_inputs` and the company API response. It never calls WhyYou code to
judge WhyYou: this module is a copy, pinned to the exact source blobs it was taken from. A target whose
sources drift from these pins is `RUNNER_NOT_READY` (`SCORING_RULE_SOURCE_DRIFT`), never silently accepted.

Copied semantics (WhyYou `eec8f70`):
- `aggregate`: an entry whose score is `None` is excluded from both numerator and denominator; weights are
  `max(0, w)`; a zero weight total means equal weights; `score = round(numerator / denominator)` with
  Python's round-half-to-even; a zero denominator is `None`, never 0.
- `weights_for`: a key the mapping does not name counts 1.0.
- a criterion's score aggregates its axes with the item's axis weights; under
  `report-config-v2-communication-separated` the `communication` axis is left out of it.
- the report score aggregates criterion scores with `criterion_weight`; the communication score aggregates
  each criterion's `communication` axis with the same weights.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

PINNED_SOURCES = (
    {
        "path": "backend/src/interview_evidence/reporting/domain/scoring.py",
        "blob_sha": "61d1e615f90ff63a353f7d2062707700b94744a1",
    },
    {
        "path": "backend/src/interview_evidence/reporting/domain/report.py",
        "blob_sha": "814289681114479aeac7ea778fae78da4d35ac48",
    },
)
RULE_COPY_ID = "controlproof.whyyou-scoring-copy.v1"
COMMUNICATION_SEPARATED_CONFIG_VERSION = "report-config-v2-communication-separated"
COMMUNICATION_AXIS = "communication"


@dataclass(frozen=True, slots=True)
class Entry:
    key: str
    score: int | None
    weight: float


@dataclass(frozen=True, slots=True)
class Contribution:
    key: str
    score: int
    weight: float
    normalized_weight: float
    contribution: float


@dataclass(frozen=True, slots=True)
class Exclusion:
    key: str
    weight: float
    normalized_weight: float


@dataclass(frozen=True, slots=True)
class Aggregate:
    score: int | None
    numerator: float
    denominator: float
    contributions: tuple[Contribution, ...]
    exclusions: tuple[Exclusion, ...]


def aggregate(entries: Sequence[Entry]) -> Aggregate:
    if not entries:
        return Aggregate(
            score=None, numerator=0.0, denominator=0.0, contributions=(), exclusions=()
        )
    total_weight = sum(max(0.0, entry.weight) for entry in entries)
    if total_weight <= 0:
        weights = [1.0] * len(entries)
        total_weight = float(len(entries))
    else:
        weights = [max(0.0, entry.weight) for entry in entries]
    contributions: list[Contribution] = []
    exclusions: list[Exclusion] = []
    numerator = 0.0
    denominator = 0.0
    for entry, weight in zip(entries, weights, strict=True):
        normalized = weight / total_weight
        if entry.score is None:
            exclusions.append(Exclusion(key=entry.key, weight=weight, normalized_weight=normalized))
            continue
        contribution = normalized * entry.score
        contributions.append(
            Contribution(
                key=entry.key,
                score=entry.score,
                weight=weight,
                normalized_weight=normalized,
                contribution=contribution,
            )
        )
        numerator += contribution
        denominator += normalized
    return Aggregate(
        score=round(numerator / denominator) if denominator > 0 else None,
        numerator=numerator,
        denominator=denominator,
        contributions=tuple(contributions),
        exclusions=tuple(exclusions),
    )


def weights_for(keys: Sequence[str], weights: Mapping[str, float]) -> tuple[float, ...]:
    return tuple(float(weights.get(key, 1.0)) for key in keys)


def criterion_aggregate(
    axes: Iterable[tuple[str, int | None]],
    axis_weights: Mapping[str, float],
    config_version: str,
) -> Aggregate:
    """A criterion's score from its ordered `(axis, score)` pairs (WhyYou `Report.axis_aggregate_for`)."""
    selected = [
        (axis, score)
        for axis, score in axes
        if config_version != COMMUNICATION_SEPARATED_CONFIG_VERSION or axis != COMMUNICATION_AXIS
    ]
    weights = weights_for([axis for axis, _ in selected], axis_weights)
    return aggregate(
        [
            Entry(key=axis, score=score, weight=weight)
            for (axis, score), weight in zip(selected, weights, strict=True)
        ]
    )


def _criterion_weight(item: Mapping[str, Any]) -> float:
    value = item.get("criterion_weight")
    return 1.0 if value is None else float(value)


def _axes(item: Mapping[str, Any]) -> list[tuple[str, int | None]]:
    return [(str(axis), score) for axis, score in item.get("axes", ())]


def report_aggregate(items: Sequence[Mapping[str, Any]], config_version: str) -> Aggregate:
    """The report score (WhyYou `Report.criterion_aggregate` / `overall_score`)."""
    return aggregate(
        [
            Entry(
                key=str(item["criterion_id"]),
                score=criterion_aggregate(
                    _axes(item), item.get("axis_weights") or {}, config_version
                ).score,
                weight=_criterion_weight(item),
            )
            for item in items
        ]
    )


def communication_aggregate(items: Sequence[Mapping[str, Any]]) -> Aggregate:
    """The separate communication score (WhyYou `Report.communication_aggregate`)."""
    entries = []
    for item in items:
        score = next((value for axis, value in _axes(item) if axis == COMMUNICATION_AXIS), None)
        entries.append(
            Entry(key=str(item["criterion_id"]), score=score, weight=_criterion_weight(item))
        )
    return aggregate(entries)
