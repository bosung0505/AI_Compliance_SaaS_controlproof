"""시나리오 로더.

YAML 을 읽어 검증한다. 여기서 막아야 하는 것:
  - 관찰값 키 오타 (사전에 없는 키를 규칙이 가리킴)
  - 알 수 없는 규칙 타입
  - 전제조건이 비어 있는 시나리오

전제조건에 required 이면서 absent 인 단계가 있으면 대상 부재로 표시한다.
이 판단을 로드 시점에 하는 이유는, 대상이 없는 시나리오를 실행 큐에
올리지 않기 위해서다. 없는 것을 실행한 척하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from engine.judge import RULES
from engine.observations import validate as validate_keys

_RULE_KEY_FIELDS = {
    "state_equals": ("subject",),
    "event_order": ("before", "after"),
    "time_limit": ("from", "to"),
}


@dataclass
class Scenario:
    id: str
    control: str
    name: str
    intent: str
    beneficiary: str
    initiator: str
    seed: str
    adapters: tuple[str, ...]
    injection: tuple[str, ...]
    preconditions: tuple[dict[str, Any], ...]
    steps: tuple[dict[str, Any], ...]
    expected: str
    rules: tuple[dict[str, Any], ...]
    evidence_required: tuple[str, ...]
    implementation: dict[str, Any] = field(default_factory=dict)
    legal_basis: tuple[str, ...] = ()
    fault: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def no_test_target(self) -> bool:
        return any(
            p.get("required") and p.get("status") == "absent"
            for p in self.preconditions
        )

    @property
    def missing_preconditions(self) -> tuple[str, ...]:
        return tuple(
            p["step"] for p in self.preconditions
            if p.get("required") and p.get("status") == "absent"
        )

    def rule_keys(self) -> list[str]:
        keys: list[str] = []
        for rule in self.rules:
            for f in _RULE_KEY_FIELDS.get(rule["type"], ()):
                keys.append(rule[f])
            if rule["type"] == "fields_present":
                keys += list(rule.get("present", []))
                keys += list(rule.get("absent", []))
        return keys


class ScenarioError(ValueError):
    pass


_REQUIRED = (
    "id", "control", "name", "intent", "beneficiary", "initiator",
    "seed", "preconditions", "steps", "expected", "rules",
)


def load(path: str | Path) -> Scenario:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ScenarioError(f"{path}: 최상위가 매핑이 아님")

    missing = [f for f in _REQUIRED if f not in data]
    if missing:
        raise ScenarioError(f"{path}: 필수 항목 누락 {missing}")

    if data["seed"] not in ("state", "path"):
        raise ScenarioError(f"{path}: seed 는 state 또는 path (3.3절)")

    for rule in data["rules"]:
        if rule["type"] not in RULES:
            raise ScenarioError(f"{path}: 알 수 없는 규칙 타입 {rule['type']!r}")

    scenario = Scenario(
        id=data["id"],
        control=data["control"],
        name=data["name"],
        intent=data["intent"],
        beneficiary=data["beneficiary"],
        initiator=data["initiator"],
        seed=data["seed"],
        adapters=tuple(data.get("adapters", ())),
        injection=tuple(data.get("injection", ())),
        preconditions=tuple(data["preconditions"]),
        steps=tuple(data["steps"]),
        expected=data["expected"],
        rules=tuple(data["rules"]),
        evidence_required=tuple(data.get("evidence_required", ())),
        implementation=data.get("implementation", {}),
        legal_basis=tuple(data.get("legal_basis", ())),
        fault=data.get("fault", {}),
        raw=data,
    )

    unknown = validate_keys(scenario.rule_keys())
    if unknown:
        raise ScenarioError(
            f"{path}: 관찰값 키 사전에 없는 키 {unknown}. "
            f"오타이거나 engine/observations.py 에 등록이 필요함"
        )
    return scenario


def load_all(directory: str | Path = "scenarios") -> list[Scenario]:
    paths = sorted(p for p in Path(directory).glob("*.yaml") if not p.name.startswith("_"))
    return [load(p) for p in paths]
