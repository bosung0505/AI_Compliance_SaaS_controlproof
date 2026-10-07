"""T009 — the ControlProof copy of WhyYou's scoring rule (plan §6, research R-008).

RED until T017 creates `engine/judges/e02_scoring.py`; the module is imported per test so its absence fails
as `ModuleNotFoundError` instead of breaking collection. The expected values come from WhyYou's own tests
(`tests/fixtures/whyyou_scoring_vectors.json`, T003) plus the H-2 round-half-even boundary cases.

API pinned here for T017:
- `Entry(key, score, weight)`, `aggregate(entries) -> Aggregate(score, numerator, denominator,
  contributions, exclusions)`, `weights_for(keys, weights)`
- `criterion_aggregate(axes, axis_weights, config_version)` where `axes` is ordered `(axis, score)` pairs
- `report_aggregate(items, config_version)` and `communication_aggregate(items)` where each item is a mapping
  with `criterion_id`, `criterion_weight`, `axes` and `axis_weights`
- `PINNED_SOURCES`: the WhyYou source paths and blob SHAs the copy was taken from
"""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path

import pytest

VECTORS = json.loads(Path("tests/fixtures/whyyou_scoring_vectors.json").read_text(encoding="utf-8"))
SEPARATED = VECTORS["communication_separated_config_version"]


def scoring():
    return import_module("engine.judges.e02_scoring")


def _items(raw: list[dict]) -> list[dict]:
    return [
        {
            "criterion_id": f"criterion-{index}",
            "criterion_weight": item["criterion_weight"],
            "axes": [tuple(axis) for axis in item["axes"]],
            "axis_weights": item["axis_weights"],
        }
        for index, item in enumerate(raw, start=1)
    ]


@pytest.mark.parametrize("case", VECTORS["aggregate"], ids=lambda case: case["name"])
def test_aggregate_matches_whyyou_vectors(case) -> None:
    module = scoring()
    result = module.aggregate(
        [module.Entry(key, score, weight) for key, score, weight in case["entries"]]
    )
    expected = case["expected"]
    assert result.score == expected["score"]
    if "numerator" in expected:
        assert result.numerator == pytest.approx(expected["numerator"], abs=1e-9)
    if "denominator" in expected:
        assert result.denominator == pytest.approx(expected["denominator"], abs=1e-9)
    if "excluded_keys" in expected:
        assert [item.key for item in result.exclusions] == expected["excluded_keys"]


@pytest.mark.parametrize("case", VECTORS["weights_for"], ids=lambda case: case["name"])
def test_weights_for_defaults_missing_keys_to_one(case) -> None:
    assert scoring().weights_for(case["keys"], case["weights"]) == tuple(case["expected"])


@pytest.mark.parametrize("case", VECTORS["criterion"], ids=lambda case: case["name"])
def test_criterion_score_applies_axis_weights_and_separation(case) -> None:
    module = scoring()
    axes = [tuple(axis) for axis in case["axes"]]
    plain = module.criterion_aggregate(axes, case["axis_weights"], "legacy")
    assert plain.score == case["expected"]["average_score"]
    if "competency_score" in case["expected"]:
        separated = module.criterion_aggregate(axes, case["axis_weights"], SEPARATED)
        assert separated.score == case["expected"]["competency_score"]


@pytest.mark.parametrize("case", VECTORS["report"], ids=lambda case: case["name"])
def test_report_score_matches_whyyou_vectors(case) -> None:
    module = scoring()
    items = _items(case["items"])
    result = module.report_aggregate(items, case["config_version"])
    expected = case["expected"]
    assert result.score == expected["overall_score"]
    if "denominator" in expected:
        assert result.denominator == pytest.approx(expected["denominator"], abs=1e-9)
    if "excluded_normalized_weights" in expected:
        assert [item.normalized_weight for item in result.exclusions] == pytest.approx(
            expected["excluded_normalized_weights"]
        )
    if "communication_score" in expected:
        assert module.communication_aggregate(items).score == expected["communication_score"]


@pytest.mark.parametrize(
    "entries,expected",
    [
        ([("A", 72, 50.0), ("B", 73, 50.0)], 72),  # E-02 v1: 72.5 -> 72 (half-up would be 73)
        ([("A", 72, 25.0), ("B", 74, 75.0)], 74),  # E-02 v2: 73.5 -> 74
    ],
    ids=["v1-72.5-rounds-down-to-even", "v2-73.5-rounds-up-to-even"],
)
def test_h2_boundaries_round_half_to_even(entries, expected) -> None:
    module = scoring()
    result = module.aggregate([module.Entry(*entry) for entry in entries])
    assert result.score == expected
    assert result.denominator == 1.0


def test_zero_denominator_is_none_and_unscored_axes_are_excluded() -> None:
    module = scoring()
    assert module.aggregate([]).score is None
    assert module.aggregate([module.Entry("A", 90, 0.0)]).score == 90
    result = module.criterion_aggregate([("depth", None), ("correctness", 80)], {}, "legacy")
    assert result.score == 80
    assert [item.key for item in result.exclusions] == ["depth"]


def test_copy_pins_its_whyyou_sources() -> None:
    assert scoring().PINNED_SOURCES == (
        {
            "path": "backend/src/interview_evidence/reporting/domain/scoring.py",
            "blob_sha": "61d1e615f90ff63a353f7d2062707700b94744a1",
        },
        {
            "path": "backend/src/interview_evidence/reporting/domain/report.py",
            "blob_sha": "814289681114479aeac7ea778fae78da4d35ac48",
        },
    )
