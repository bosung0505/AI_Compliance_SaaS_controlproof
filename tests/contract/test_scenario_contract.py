from pathlib import Path

import pytest
import yaml

from engine.models import ComparatorKind
from engine.observations import H03_EXACT_COMPARATORS
from engine.scenario import H03_ASSERTIONS, H03_EVIDENCE, ScenarioError, load

SCENARIO = Path("scenarios/H-03.yaml")


def test_h03_contract_is_complete_and_stable():
    scenario = load(SCENARIO)
    assert tuple(item.assertion_id for item in scenario.assertions) == H03_ASSERTIONS
    assert tuple(item.evidence_id for item in scenario.required_evidence) == H03_EVIDENCE
    assert len({step.step_id for step in scenario.steps}) == len(scenario.steps)
    assert set(scenario.observation_comparators) == set(H03_EXACT_COMPARATORS)
    assert all(
        policy.kind is ComparatorKind.EXACT for policy in scenario.observation_comparators.values()
    )
    assert set(scenario.required_capabilities.values()) == {"v1"}
    assert scenario.snapshot().digest == load(SCENARIO).snapshot().digest


def test_invalid_tolerance_and_duplicate_step_are_rejected(tmp_path):
    data = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
    data["steps"].append(dict(data["steps"][0]))
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ScenarioError, match="unique"):
        load(path)


def test_model_fixture_is_allowlisted():
    scenario = load(SCENARIO)
    assert scenario.allowed_model_fixtures == {
        "h03-report-v1": "ce09b95403b34e1390502c90f5c5edc518ddf65d38c8ce881617a37cac6d16b1"
    }
