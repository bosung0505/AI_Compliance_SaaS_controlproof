"""Deterministic, PII-free builders for Spec 004 (E-01/E-02) tests.

The builders return JSON-compatible dictionaries shaped like `data-model.md`, so contract and
unit tests can feed them into the Pydantic models under test without coupling fixture import to
the order in which those models are implemented (same approach as `tests/fixtures/spec003.py`).
Free text never appears: only its SHA-256 and length, as FR-042 requires of sealed evidence.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

FIXED_AT = datetime(2026, 10, 7, tzinfo=UTC)
RUN_ID = UUID("00000000-0000-7000-8000-000000004001")
COMPANY_ID = UUID("00000000-0000-7000-8000-000000000001")
STATE_DIGEST = "4" * 64
TEXT_DIGEST = "7" * 64
FIXTURE_ID = "spec004-report-v1"
FIXTURE_DIGEST = "e15ec3790b64b2fba10e0caa9372f08c917edbbaa99ce308076952b838668b3f"
UNVERIFIED_NOTICE_DIGEST = "8" * 64

E01_LANES = ("E01_REFERENCE", "E01_CITATION_MATRIX", "E01_EVIDENCE_REMOVAL", "E01_STORAGE_PROBE")
E02_LANES = ("E02_FIRST_APPLICANT", "E02_SECOND_APPLICANT")
CITATION_MODES = ("VALID", "EMPTY", "NONEXISTENT", "OTHER_APPLICANT", "OTHER_CRITERION")
INVALID_MODES = ("EMPTY", "NONEXISTENT", "OTHER_APPLICANT", "OTHER_CRITERION")
MATRIX_CODES = {
    "VALID": "E01-1-VALID",
    "EMPTY": "E01-2-EMPTY",
    "NONEXISTENT": "E01-3-NONEXISTENT",
    "OTHER_APPLICANT": "E01-4-OTHER-APPLICANT",
    "OTHER_CRITERION": "E01-5-OTHER-CRITERION",
}
AXES = ("correctness", "depth", "fundamentals", "ownership", "communication")
COMMUNICATION_SEPARATED = "report-config-v2-communication-separated"
#: plan.md "E-02 점수 표식 값": v1 72.5 -> 72, v2 73.5 -> 74 (round half to even, both directions).
E02_V1 = (
    {"code": "E02-A", "score": 72, "weight": 50.0},
    {"code": "E02-B", "score": 73, "weight": 50.0},
)
E02_V2 = (
    {"code": "E02-A", "score": 72, "weight": 25.0},
    {"code": "E02-B", "score": 74, "weight": 75.0},
)
E02_V1_AXIS_WEIGHTS = {axis: 20.0 for axis in AXES}
E02_V2_AXIS_WEIGHTS = {
    "correctness": 30.0,
    "depth": 25.0,
    "fundamentals": 20.0,
    "ownership": 15.0,
    "communication": 10.0,
}


def sid(namespace: str, value: str) -> UUID:
    """Stable synthetic identity, the Spec 004 analogue of the Spec 003 builder."""
    return uuid5(NAMESPACE_URL, f"controlproof:spec004:{namespace}:{value}")


def uuid7_at(at: datetime, sequence: int) -> UUID:
    """A UUIDv7 with the given millisecond, like WhyYou's `new_uuid7(occurred_at)`."""
    millis = int(at.timestamp() * 1000)
    value = (millis << 80) | (7 << 76) | (sequence & 0xFFF) << 64 | (0b10 << 62) | sequence
    return UUID(int=value)


def _merge(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    value = deepcopy(base)
    value.update(updates)
    return value


def marker(mode: str, *, arg: UUID | None = None, score: int | None = None) -> str:
    parts = [f"mode={mode}"]
    if arg is not None:
        parts.append(f"arg={arg}")
    if score is not None:
        parts.append(f"score={score}")
    return f"[controlproof-spec004 {' '.join(parts)}]"


def lane_criterion(
    lane_id: str,
    code: str,
    *,
    citation_mode: str | None = "VALID",
    mode_argument: str | None = None,
    fixture_score: int | None = None,
    weight: float = 20.0,
    **updates: Any,
) -> dict[str, Any]:
    code = code.upper()
    criterion_id = sid(f"{lane_id}:criterion", code)
    argument = UUID(mode_argument) if mode_argument else None
    value = {
        "criterion_id": str(criterion_id),
        "code": code,
        "weight": weight,
        "citation_mode": citation_mode,
        "mode_argument": mode_argument,
        "fixture_score": fixture_score,
        "marker": marker(citation_mode or "VALID", arg=argument, score=fixture_score),
        "answer_turn_id": str(sid(f"{lane_id}:answer", code)),
        "question_turn_id": str(sid(f"{lane_id}:question", code)),
        "transcript_segment_id": str(sid(f"{lane_id}:segment", code)),
    }
    return _merge(value, updates)


def matrix_criteria(*, reference_evidence_id: UUID) -> list[dict[str, Any]]:
    valid = lane_criterion("E01_CITATION_MATRIX", MATRIX_CODES["VALID"])
    return [
        valid,
        lane_criterion("E01_CITATION_MATRIX", MATRIX_CODES["EMPTY"], citation_mode="EMPTY"),
        lane_criterion(
            "E01_CITATION_MATRIX",
            MATRIX_CODES["NONEXISTENT"],
            citation_mode="NONEXISTENT",
            mode_argument=str(sid(str(RUN_ID), "e01-nonexistent")),
        ),
        lane_criterion(
            "E01_CITATION_MATRIX",
            MATRIX_CODES["OTHER_APPLICANT"],
            citation_mode="OTHER_APPLICANT",
            mode_argument=str(reference_evidence_id),
        ),
        lane_criterion(
            "E01_CITATION_MATRIX",
            MATRIX_CODES["OTHER_CRITERION"],
            citation_mode="OTHER_CRITERION",
            mode_argument=valid["criterion_id"],
        ),
    ]


def report_lane(
    lane_id: str, criteria: list[dict[str, Any]] | None = None, **updates: Any
) -> dict[str, Any]:
    if lane_id not in E01_LANES + E02_LANES:
        raise ValueError(f"unknown Spec 004 lane: {lane_id}")
    e02 = lane_id in E02_LANES
    position_scope = "E02" if e02 else lane_id
    value = {
        "run_id": str(RUN_ID),
        "lane_id": lane_id,
        "subject_ref": f"synthetic-{lane_id.casefold().replace('_', '-')}",
        "position_id": str(sid("position", position_scope)),
        "invitation_id": str(sid("invitation", lane_id)),
        "applicant_id": str(sid("applicant", lane_id)),
        "interview_session_id": str(sid("session", lane_id)),
        "competency_model_version_id": str(sid("version", lane_id)),
        "version_source": "PRODUCT_API_LATEST_PUBLISHED" if e02 else "RUN_SEED",
        "criteria": criteria or [lane_criterion(lane_id, f"{lane_id.casefold()}-1")],
        "fixture_rows": {"transcript_segments": [str(sid(f"{lane_id}:segment", "1"))]},
        "fixture_digest": STATE_DIGEST,
        "consent_required_purposes": ["ai_assessment", "document_analysis", "recording"],
        "trace_namespace": f"controlproof:{RUN_ID}:{lane_id}",
        "seed_correlation_id": f"spec004:{RUN_ID}:{lane_id}",
    }
    return _merge(value, updates)


def emission_receipt(
    criterion_id: str,
    *,
    mode: str = "VALID",
    provided: list[str] | None = None,
    quoted: list[str] | None = None,
    score: int | None = 72,
    mode_status: str = "EMITTED",
    **updates: Any,
) -> dict[str, Any]:
    provided = provided if provided is not None else [str(uuid7_at(FIXED_AT, 1))]
    value = {
        "schema_version": "controlproof.spec004-model-emission.v1",
        "receipt_id": str(sid("receipt", f"{criterion_id}:{mode}")),
        "fixture_id": FIXTURE_ID,
        "criterion_id": criterion_id,
        "mode": mode,
        "provided_evidence_ids": provided,
        "emitted_quoted_ids": quoted if quoted is not None else provided[:1],
        "emitted_score": score,
        "mode_status": mode_status,
        "emitted_at": FIXED_AT.isoformat(),
    }
    return _merge(value, updates)


def stored_axis(
    axis: str = "correctness",
    *,
    score: int | None = 72,
    quoted: list[str] | None = None,
    unverified: bool = False,
) -> dict[str, Any]:
    return {
        "axis": axis,
        "score": score,
        "quoted_evidence_ids": quoted if quoted is not None else [],
        "rationale_sha256": UNVERIFIED_NOTICE_DIGEST if unverified else TEXT_DIGEST,
        "rationale_is_unverified_notice": unverified,
    }


def citation_case(mode: str, *, outcome: str | None = None, **updates: Any) -> dict[str, Any]:
    criterion_id = str(sid("E01_CITATION_MATRIX:criterion", MATRIX_CODES[mode]))
    evidence_id = str(uuid7_at(FIXED_AT, 2))
    valid = mode == "VALID"
    value = {
        "case_id": f"E01_CITATION_MATRIX:{MATRIX_CODES[mode]}",
        "mode": mode,
        "intended_quoted_ids": [evidence_id]
        if valid
        else ([] if mode == "EMPTY" else [str(sid("intended", mode))]),
        "emission_receipt_id": str(sid("receipt", f"{criterion_id}:{mode}")),
        "stored_axes": [
            stored_axis(
                axis,
                score=72 if valid else None,
                quoted=[evidence_id] if valid else [],
                unverified=not valid,
            )
            for axis in AXES
        ],
        "stored_evidence_ids": [evidence_id],
        "invalid_id_present": False,
        "rationale_present": True,
        "outcome": outcome or ("STORED_VALID" if valid else "EMPTIED"),
    }
    return _merge(value, updates)


def report_item(
    criterion_id: str,
    *,
    weight: float,
    score: int | None,
    axis_weights: dict[str, float],
    version_id: str,
    **updates: Any,
) -> dict[str, Any]:
    value = {
        "report_item_id": str(sid("item", criterion_id)),
        "criterion_id": criterion_id,
        "competency_model_version_id": version_id,
        "assessment_state": "confirmed" if score is not None else "insufficient_evidence",
        "criterion_weight": weight,
        "axis_weights": dict(axis_weights),
        "axes": [
            stored_axis(
                axis, score=score, quoted=[str(uuid7_at(FIXED_AT, 3))] if score is not None else []
            )
            for axis in AXES
        ],
        "observation_sha256": TEXT_DIGEST,
        "rationale_sha256": TEXT_DIGEST,
        "uncertainty_sha256": TEXT_DIGEST,
    }
    return _merge(value, updates)


def report_record(
    lane_id: str,
    phase: str,
    items: list[dict[str, Any]],
    *,
    overall_score: int | None,
    scoring_inputs: dict[str, Any],
    **updates: Any,
) -> dict[str, Any]:
    value = {
        "run_id": str(RUN_ID),
        "lane_id": lane_id,
        "subject_ref": f"synthetic-{lane_id.casefold().replace('_', '-')}",
        "phase": phase,
        "report_id": str(sid("report", lane_id)),
        "report_version": 1,
        "model_version": "bedrock-model-v1",
        "prompt_version": "assessment-prompt-v2",
        "config_version": COMMUNICATION_SEPARATED,
        "status": "ready",
        "summary_sha256": TEXT_DIGEST,
        "summary_length": 32,
        "overall_score": overall_score,
        "scoring_inputs": scoring_inputs,
        "items": items,
        "evidence": [],
        "transcript_segments": [],
        "source_status": "PRESENT",
        "state_digest": STATE_DIGEST,
    }
    return _merge(value, updates)


def scoring_inputs(entries: list[tuple[str, int | None, float]]) -> dict[str, Any]:
    """`_scoring_inputs` shape for the given (criterion_id, score, weight) entries."""
    total = sum(max(0.0, weight) for _, _, weight in entries) or float(len(entries))
    criteria, excluded = [], []
    numerator = denominator = 0.0
    for criterion_id, score, weight in entries:
        normalized = weight / total
        if score is None:
            excluded.append(
                {"criterion_id": criterion_id, "weight": weight, "normalized_weight": normalized}
            )
            continue
        contribution = normalized * score
        criteria.append(
            {
                "criterion_id": criterion_id,
                "score": score,
                "weight": weight,
                "normalized_weight": normalized,
                "contribution": contribution,
            }
        )
        numerator += contribution
        denominator += normalized
    return {
        "criteria": criteria,
        "excluded": excluded,
        "numerator": numerator,
        "denominator": denominator,
        "axis_weights": {},
        "communication": {
            "score": None,
            "numerator": 0.0,
            "denominator": 0.0,
            "scored_criteria": [],
            "unscored_criteria": [],
        },
    }


def e02_report_record(version: str, phase: str = "GENERATED", **updates: Any) -> dict[str, Any]:
    lane_id = "E02_FIRST_APPLICANT" if version == "v1" else "E02_SECOND_APPLICANT"
    spec = E02_V1 if version == "v1" else E02_V2
    axis_weights = E02_V1_AXIS_WEIGHTS if version == "v1" else E02_V2_AXIS_WEIGHTS
    version_id = str(sid("version", version))
    items = [
        report_item(
            str(sid(f"{version}:criterion", entry["code"])),
            weight=entry["weight"],
            score=entry["score"],
            axis_weights=axis_weights,
            version_id=version_id,
        )
        for entry in spec
    ]
    inputs = scoring_inputs(
        [
            (item["criterion_id"], entry["score"], entry["weight"])
            for item, entry in zip(items, spec, strict=True)
        ]
    )
    overall = round(inputs["numerator"] / inputs["denominator"])
    return report_record(
        lane_id, phase, items, overall_score=overall, scoring_inputs=inputs, **updates
    )


def report_read(phase: str, **updates: Any) -> dict[str, Any]:
    value = {
        "phase": phase,
        "request_id": str(sid("read", phase)),
        "status_code": 200,
        "report": {"overall_score": 72, "items": []},
        "timeline": {"entries": []},
        "unknown_fields": [],
        "read_digest": STATE_DIGEST,
    }
    return _merge(value, updates)


def change_injection(
    kind: str = "EVIDENCE_SEGMENT_REMOVAL", state: str = "RESTORED", **updates: Any
) -> dict[str, Any]:
    restored = state == "RESTORED"
    value = {
        "injection_id": str(sid("injection", kind)),
        "kind": kind,
        "run_id": str(RUN_ID),
        "lane_id": "E01_EVIDENCE_REMOVAL"
        if kind != "CRITERIA_VERSION_PUBLISH"
        else "E02_FIRST_APPLICANT",
        "subject_ref": "synthetic-e01-evidence-removal",
        "target_table": {
            "EVIDENCE_SEGMENT_REMOVAL": "transcript_segments",
            "STORAGE_PROBE_WRITE": "report_items",
            "CRITERIA_VERSION_PUBLISH": "competency_model_versions",
        }[kind],
        "target_ids": [str(sid("target", kind))],
        "pre_projection_digest": STATE_DIGEST,
        "applied_at": FIXED_AT.isoformat(),
        "apply_receipt": {"affected_rows": 1, "absence_confirmed": True},
        "restore_action": {
            "EVIDENCE_SEGMENT_REMOVAL": "REINSERT",
            "STORAGE_PROBE_WRITE": "REWRITE",
            "CRITERIA_VERSION_PUBLISH": "TEARDOWN",
        }[kind],
        "restored_at": (FIXED_AT + timedelta(seconds=5)).isoformat() if restored else None,
        "post_restore_digest": STATE_DIGEST if restored else None,
        "state": state,
        "failure_code": None if state != "RESTORE_FAILED" else "RESTORE_DIGEST_MISMATCH",
    }
    return _merge(value, updates)


def criteria_version(version: str = "v1", **updates: Any) -> dict[str, Any]:
    spec = E02_V1 if version == "v1" else E02_V2
    value = {
        "position_id": str(sid("position", "E02")),
        "competency_model_version_id": str(sid("version", version)),
        "version_number": 1 if version == "v1" else 2,
        "row_version": 2,
        "status": "published",
        "published_at": FIXED_AT.isoformat(),
        "criteria": [
            {
                "criterion_id": str(sid(f"{version}:criterion", entry["code"])),
                "code": entry["code"],
                "weight": entry["weight"],
            }
            for entry in spec
        ],
        "axis_weights": dict(E02_V1_AXIS_WEIGHTS if version == "v1" else E02_V2_AXIS_WEIGHTS),
        "request_ids": [str(sid("version-request", version))],
        "snapshot_phase": "V1_PUBLISHED" if version == "v1" else "V2_PUBLISHED",
        "other_positions_digest": STATE_DIGEST,
    }
    return _merge(value, updates)


def frozen_inputs(version: str = "v1", **updates: Any) -> dict[str, Any]:
    record = e02_report_record(version)
    value = {
        "report_id": record["report_id"],
        "competency_model_version_id": str(sid("version", version)),
        "model_version": record["model_version"],
        "prompt_version": record["prompt_version"],
        "config_version": record["config_version"],
        "criterion_weights": {
            item["criterion_id"]: item["criterion_weight"] for item in record["items"]
        },
        "axis_weights": {item["criterion_id"]: item["axis_weights"] for item in record["items"]},
        "scoring_inputs_present": True,
        "missing_fields": [],
        "matches_version_snapshot": True,
    }
    return _merge(value, updates)
