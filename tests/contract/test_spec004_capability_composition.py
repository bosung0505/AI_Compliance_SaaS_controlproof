"""T042 — E-01 citation-path capability composition and readiness (FR-001).

T047 composes the mutation capabilities; criteria-version ones stay RUNNER_NOT_READY with an operator action
until T055 composes them.
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
    ):
        assert getattr(adapters, name) is not None, name
    # Spec 004 lanes never share the N-02 credential store.
    assert adapters.spec004_consent is not adapters.n02_consent


def test_uncomposed_criteria_capability_names_an_operator_action(settings) -> None:
    adapters, _ = create_whyyou_adapter(settings)
    result = adapters.capability.probe("criteria.version.create")
    assert result.status is ReadinessStatus.RUNNER_NOT_READY
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
