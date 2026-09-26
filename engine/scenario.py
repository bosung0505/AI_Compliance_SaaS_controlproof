"""Versioned scenario definition loader and cross-reference validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from engine.models import (
    ComparatorPolicy,
    Phase,
    ScenarioSnapshot,
    canonical_json_bytes,
    sha256_bytes,
)
from engine.observations import H03_EXACT_COMPARATORS

H03_ASSERTIONS = tuple(f"H03-A{index}" for index in range(1, 7))
H03_EVIDENCE = tuple(f"EV-{index:02d}" for index in range(1, 10))


class ScenarioError(ValueError):
    pass


class ScenarioModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Precondition(ScenarioModel):
    precondition_id: str
    kind: str
    description: str
    required: bool = True


class ScenarioStep(ScenarioModel):
    step_id: str
    phase: Phase
    action: str
    attempt_policy: dict[str, Any] = Field(default_factory=lambda: {"max_attempts": 1})
    outputs: tuple[str, ...] = ()
    evidence_requirements: tuple[str, ...] = ()
    always_run: bool = False


class AssertionDefinition(ScenarioModel):
    assertion_id: str
    description: str
    expectation: dict[str, Any]
    fail_condition: dict[str, Any] | None = None
    required_observation_keys: tuple[str, ...]
    required_evidence_ids: tuple[str, ...]
    source_requirements: tuple[str, ...]


class EvidenceRequirement(ScenarioModel):
    evidence_id: str
    description: str
    artifact_types: tuple[str, ...]


class TimingPolicy(ScenarioModel):
    poll_seconds: float = Field(gt=0)
    injected_deadline_seconds: float = Field(gt=0)
    automatic_decision_window_seconds: float = Field(gt=0)
    environment_restore_deadline_seconds: float = Field(gt=0)
    stability_consecutive: int = Field(ge=1)
    stability_seconds: float = Field(ge=0)


class RestorePolicy(ScenarioModel):
    mandatory: bool
    action: str
    report_processing_result_field: str


class ScenarioDefinition(ScenarioModel):
    scenario_id: str
    version: str
    title: str
    control_intent: str
    required_capabilities: dict[str, str]
    preconditions: tuple[Precondition, ...]
    steps: tuple[ScenarioStep, ...]
    assertions: tuple[AssertionDefinition, ...]
    required_evidence: tuple[EvidenceRequirement, ...]
    timing_policy: TimingPolicy
    restore_policy: RestorePolicy
    observation_comparators: dict[str, ComparatorPolicy]
    source_requirements: tuple[str, ...]
    allowed_model_fixtures: dict[str, str]
    excluded_scope: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_definition(self) -> ScenarioDefinition:
        if len({step.step_id for step in self.steps}) != len(self.steps):
            raise ValueError("scenario step_id values must be unique")
        if any(version != "v1" for version in self.required_capabilities.values()):
            raise ValueError("H-03 capability contract versions must all be v1")
        assertion_ids = tuple(item.assertion_id for item in self.assertions)
        evidence_ids = tuple(item.evidence_id for item in self.required_evidence)
        if self.scenario_id == "H-03":
            if set(assertion_ids) != set(H03_ASSERTIONS) or len(assertion_ids) != 6:
                raise ValueError("H-03 requires exactly H03-A1 through H03-A6")
            if set(evidence_ids) != set(H03_EVIDENCE) or len(evidence_ids) != 9:
                raise ValueError("H-03 requires exactly EV-01 through EV-09")
            required_keys = {
                key for assertion in self.assertions for key in assertion.required_observation_keys
            }
            missing = required_keys - set(self.observation_comparators)
            if missing:
                raise ValueError(f"H-03 comparator registry is incomplete: {sorted(missing)}")
            for key in required_keys:
                if self.observation_comparators[key].kind.value != "EXACT":
                    raise ValueError("H-03 assertion inputs must use EXACT")
            if set(self.observation_comparators) != set(H03_EXACT_COMPARATORS):
                raise ValueError("H-03 comparator registry must match the canonical key set")
        known_evidence = set(evidence_ids)
        for step in self.steps:
            unknown = set(step.evidence_requirements) - known_evidence
            if unknown:
                raise ValueError(
                    f"step {step.step_id} references unknown evidence {sorted(unknown)}"
                )
            if step.always_run and step.phase is not Phase.RECOVERED:
                raise ValueError("only RECOVERED steps may be always_run")
        for assertion in self.assertions:
            unknown = set(assertion.required_evidence_ids) - known_evidence
            if unknown:
                raise ValueError(
                    f"assertion {assertion.assertion_id} references unknown evidence {sorted(unknown)}"
                )
        if not self.restore_policy.mandatory:
            raise ValueError("fault scenario requires mandatory restore")
        if not self.allowed_model_fixtures:
            raise ValueError("H-03 requires at least one deterministic model fixture")
        if any(len(digest) != 64 for digest in self.allowed_model_fixtures.values()):
            raise ValueError("model fixture digest must be SHA-256 lowercase hex")
        return self

    def snapshot(self) -> ScenarioSnapshot:
        definition = self.model_dump(mode="json")
        digest = sha256_bytes(canonical_json_bytes(definition))
        return ScenarioSnapshot(
            scenario_id=self.scenario_id,
            version=self.version,
            digest=digest,
            definition=definition,
        )


def load(path: str | Path) -> ScenarioDefinition:
    source = Path(path)
    try:
        raw = yaml.safe_load(source.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ScenarioError(f"{source}: top level must be a mapping")
        return ScenarioDefinition.model_validate(raw)
    except (OSError, yaml.YAMLError, ValueError) as exc:
        if isinstance(exc, ScenarioError):
            raise
        raise ScenarioError(f"{source}: {exc}") from exc


def load_all(directory: str | Path = "scenarios") -> list[ScenarioDefinition]:
    paths = sorted(path for path in Path(directory).glob("*.yaml") if not path.name.startswith("_"))
    return [load(path) for path in paths]
