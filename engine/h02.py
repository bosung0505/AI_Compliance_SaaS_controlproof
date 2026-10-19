"""H-02 source inventory contracts. Preparation never produces a product verdict."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class PreparationError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def load_preparation(path: Path | None = None) -> dict:
    path = path or Path(__file__).resolve().parents[1] / "scenarios/_H-02-preparation.yaml"
    expected = {
        "schema": "controlproof.h02-preparation.v1",
        "scenario_id": "H-02",
        "version": "0.1.0",
        "stage": 1,
        "actual_status": "NOT_RUN",
        "planned_assertions": [f"H02-A{i}" for i in range(1, 7)],
        "planned_effects": ["READ_ONLY", "AUXILIARY_WRITE", "HIRING_DECISION_WRITE", "UNKNOWN"],
    }
    try:
        raw = path.read_text(encoding="utf-8")
        node = yaml.compose(raw)
        if not isinstance(node, yaml.MappingNode):
            raise TypeError
        keys = [key.value for key, _ in node.value]
        if any(not isinstance(k, str) for k in keys) or len(set(keys)) != len(keys):
            raise ValueError
        data = yaml.safe_load(raw)
        if data != expected or type(data["stage"]) is not int:
            raise ValueError
    except (OSError, UnicodeError, yaml.YAMLError, ValueError, TypeError, KeyError) as error:
        raise PreparationError("PREPARATION_MANIFEST_INVALID") from error
    return data


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceFile(FrozenModel):
    path: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def relative_python_path(self) -> SourceFile:
        if (
            not self.path.startswith("backend/src/interview_evidence/")
            or not self.path.endswith(".py")
            or any(p in {"", ".", ".."} for p in self.path.split("/"))
            or "\\" in self.path
        ):
            raise ValueError("invalid source path")
        return self


class SourceRef(SourceFile):
    line: int = Field(ge=1)
    end_line: int = Field(ge=1)

    @model_validator(mode="after")
    def ordered_range(self) -> SourceRef:
        if self.end_line < self.line:
            raise ValueError("invalid source range")
        return self


class Surface(FrozenModel):
    id: str
    kind: Literal[
        "ASSISTANT_ROUTE",
        "ASSISTANT_BINDING",
        "MODEL_REQUEST_KEY",
        "MODEL_RESPONSE_FIELD",
        "WORKER_HANDLER",
        "ROUTING_ONLY",
        "API_WORKER_HELPER",
        "DISPATCH_ANCHOR",
    ]
    name: str
    target: str
    queue: str | None = None
    refs: tuple[SourceRef, ...] = Field(min_length=1)
    calls: tuple[str, ...] = ()
    bindings: tuple[tuple[str, str], ...] = ()
    review_status: Literal["UNREVIEWED"] = "UNREVIEWED"


class Issue(FrozenModel):
    code: str
    ref: SourceRef | None = None


def source_digest(sources: tuple[SourceFile, ...]) -> str:
    records = [(s.path, s.sha256) for s in sorted(sources, key=lambda s: s.path)]
    return hashlib.sha256(json.dumps(records, separators=(",", ":")).encode()).hexdigest()


class Inventory(FrozenModel):
    schema_version: Literal["controlproof.h02-source-preparation.v1"] = (
        "controlproof.h02-source-preparation.v1"
    )
    scenario_id: Literal["H-02"] = "H-02"
    stage: Literal[1] = 1
    actual_status: Literal["NOT_RUN"] = "NOT_RUN"
    product_verdict: None = None
    source_head: str | None = None
    source_branch: str | None = None
    source_dirty: bool | None = None
    sources: tuple[SourceFile, ...] = Field(min_length=1)
    source_tree_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    surfaces: tuple[Surface, ...]
    import_closure: tuple[str, ...]
    issues: tuple[Issue, ...]

    @property
    def preparation_status(self) -> str:
        return "BLOCKED" if self.issues else "READY_FOR_REVIEW"

    @model_validator(mode="after")
    def linked_sources(self) -> Inventory:
        manifest = {s.path: s.sha256 for s in self.sources}
        if (
            len(manifest) != len(self.sources)
            or source_digest(self.sources) != self.source_tree_digest
        ):
            raise ValueError("source manifest mismatch")
        if len({s.id for s in self.surfaces}) != len(self.surfaces):
            raise ValueError("duplicate surface identity")
        if not self.issues and any(s.id != f"{s.kind}:{s.name}" for s in self.surfaces):
            raise ValueError("surface identity does not match its contract")
        refs = [r for s in self.surfaces for r in s.refs]
        refs.extend(i.ref for i in self.issues if i.ref is not None)
        if any(manifest.get(r.path) != r.sha256 for r in refs):
            raise ValueError("unbound source reference")
        if not set(self.import_closure) <= manifest.keys():
            raise ValueError("unbound import closure")
        return self


def encode_contract_labels(value):
    """Keep technical contract labels distinct from the shared scanner's personal-name field."""
    if isinstance(value, dict):
        if "name" in value and "h02_contract_label" in value:
            raise ValueError("ambiguous contract label")
        return {
            "h02_contract_label" if k == "name" else k: encode_contract_labels(v)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [encode_contract_labels(v) for v in value]
    return value


def decode_contract_labels(value):
    if isinstance(value, dict):
        if "name" in value and "h02_contract_label" in value:
            raise ValueError("ambiguous contract label")
        return {
            "name" if k == "h02_contract_label" else k: decode_contract_labels(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [decode_contract_labels(v) for v in value]
    return value
