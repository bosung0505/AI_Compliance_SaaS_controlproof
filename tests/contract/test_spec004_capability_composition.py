"""T042 — E-01 citation-path capability composition and readiness (FR-001).

T047 composes the mutation capabilities and T059 the criteria-version and scoring-source ones; the scoring-source
probe is RUNNER_NOT_READY with `SCORING_RULE_SOURCE_DRIFT` when WhyYou's blobs differ from the pinned copy.
"""

from __future__ import annotations

from dataclasses import replace

from engine.adapters.whyyou.adapter import create_whyyou_adapter
from engine.adapters.whyyou.capability import CAPABILITY_VERSIONS
from engine.models import ReadinessStatus
from engine.scenario import E01_REQUIRED_CAPABILITIES, E02_REQUIRED_CAPABILITIES


def test_every_spec004_capability_is_registered_at_v1() -> None:
    required = dict(E01_REQUIRED_CAPABILITIES) | dict(E02_REQUIRED_CAPABILITIES)
    assert required.items() <= CAPABILITY_VERSIONS.items()


def test_citation_path_adapters_are_composed(settings) -> None:
    adapters, _ = create_whyyou_adapter(settings)
    for name in (
        "spec004_seed",
        "spec004_consent",
        "spec004_requests",
        "spec004_records",
        "spec004_emissions",
        "spec004_mutation",
        "spec004_versions",
        "spec004_scoring_source",
    ):
        assert getattr(adapters, name) is not None, name
    # Spec 004 lanes never share the N-02 credential store.
    assert adapters.spec004_consent is not adapters.n02_consent


def test_scoring_source_drift_is_not_ready_with_an_operator_action(settings) -> None:
    adapters, _ = create_whyyou_adapter(settings)
    adapters.spec004_scoring_source._git = lambda _args: "0" * 40
    result = adapters.capability.probe("scoring.rule.source.read")
    assert result.status is ReadinessStatus.RUNNER_NOT_READY
    assert "SCORING_RULE_SOURCE_DRIFT" in result.detail
    assert result.operator_action


def test_emission_capability_requires_the_observer_root(settings, tmp_path) -> None:
    missing = replace(settings, observer_root=tmp_path / "absent")
    adapters, _ = create_whyyou_adapter(missing)
    result = adapters.capability.probe("model.emission.read")
    assert result.status is ReadinessStatus.RUNNER_NOT_READY
    assert result.operator_action
    present = replace(settings, observer_root=tmp_path)
    adapters, _ = create_whyyou_adapter(present)
    assert adapters.capability.probe("model.emission.read").status is ReadinessStatus.READY
