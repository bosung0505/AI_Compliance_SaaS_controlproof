"""Spec 009 plan Compatibility — existing scenario snapshot digests stay byte-identical (analysis A3).

Pins were computed at `5b894dd` (before T004). New v9 fields must not leak into earlier profiles' digests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.scenario import ScenarioError, load

SCENARIOS = Path("scenarios")
FROZEN_DIGESTS = {
    "E-01.yaml": "b510becedd0d2b05f262c60af3faa0acb7e23c085154ebf5309031da0641e7cb",
    "E-02.yaml": "e6e0c56e33ad2a693640ed9cb54d8ea56777b882f30b67c9fa4374c09ede01eb",
    "E-03-AFTER.yaml": "739350adc53307c848861e11b6a895c13fbe4261cf993c7938edea26920c9ff3",
    "E-03-BEFORE.yaml": "70ac59317cdb0317103a01b9e87f2535838b1df8af609fa3eec4926f1977b8a4",
    "H-01.yaml": "df162b64894318b215f7e8567c71d6f8835dc5996ab85e7e904903774d6bb231",
    "H-02.yaml": "37bcdd4ed497596580726ca720cf49fddc549fced9c38da01f30f191dc744215",
    "H-03-DLQ.yaml": "e7aa68fd59f3458c0b65a2d5bf474effd2954fd6b45d0fab33e52a0a04e7543b",
    "H-03.yaml": "7d989c2e60c3e05dc8e5c7eec15b29f1c8341dd183328f670f224e81485bbacf",
    "N-02.yaml": "6ee0731c943fe869fb2fe096e240796e2aaa381d268f6bca623dfd9bcf34063d",
    "_N-02-analysis.yaml": "ded295ad4a7f8a38f552a65a27f7a7b081f1357e6399fadc9d4407d37105f7ac",
}
# Not ScenarioDefinition documents (preparation records and the catalog template use their own schema),
# so `load` rejects them before and after T004; they have no snapshot digest to pin.
NOT_SCENARIO_DEFINITIONS = ("_H-01-preparation.yaml", "_H-02-preparation.yaml", "_TEMPLATE.yaml")


@pytest.mark.parametrize("name", sorted(FROZEN_DIGESTS))
def test_existing_scenario_snapshot_digest_is_frozen(name: str) -> None:
    assert load(SCENARIOS / name).snapshot().digest == FROZEN_DIGESTS[name]


@pytest.mark.parametrize("name", NOT_SCENARIO_DEFINITIONS)
def test_non_definition_yaml_is_still_rejected(name: str) -> None:
    with pytest.raises(ScenarioError):
        load(SCENARIOS / name)


def test_pinned_set_covers_the_thirteen_pre_spec009_files() -> None:
    assert len(FROZEN_DIGESTS) + len(NOT_SCENARIO_DEFINITIONS) == 13
    present = {path.name for path in SCENARIOS.glob("*.yaml")}
    assert set(FROZEN_DIGESTS) | set(NOT_SCENARIO_DEFINITIONS) <= present
