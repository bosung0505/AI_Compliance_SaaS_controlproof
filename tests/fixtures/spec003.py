"""Deterministic, PII-free builders for Spec 003 tests.

The builders intentionally return JSON-compatible dictionaries. Contract tests can
feed them into the Pydantic models under test without coupling fixture import to the
order in which the new model classes are implemented.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid5

FIXED_AT = datetime(2026, 10, 1, tzinfo=UTC)
RUN_ID = UUID("00000000-0000-7000-8000-000000003001")
POLICY_REQUEST_ID = UUID("00000000-0000-7000-8000-000000003002")
POLICY_DIGEST = "3" * 64
FIXTURE_DIGEST = "4" * 64
STATE_DIGEST = "5" * 64
TRACE_DIGEST = "6" * 64
ARTIFACT_REF = "artifacts/spec003/fact.json"

LANES = (
    "PRISTINE_BASELINE",
    "DOCUMENT_BYPASS",
    "RECORDING_BOUNDARY_PROBE",
    "ASSESSMENT_BOUNDARY_PROBE",
    "NORMAL_ORDER",
    "CONSENT_FAULT_RECOVERY",
)
PATHS = ("DOCUMENT_ANALYSIS", "RECORDING", "AI_ASSESSMENT")
PURPOSES = ("ai_assessment", "document_analysis", "recording")


def _id(namespace: str, value: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"controlproof:spec003:{namespace}:{value}")


def _merge(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    value = deepcopy(base)
    value.update(updates)
    return value


def subject_lane(lane_id: str = "PRISTINE_BASELINE", **updates: Any) -> dict[str, Any]:
    if lane_id not in LANES:
        raise ValueError(f"unknown Spec 003 lane: {lane_id}")
    fixture_kind: str | None = None
    allowed: dict[str, list[str]] = {}
    baseline_kind = "PRISTINE"
    if lane_id == "RECORDING_BOUNDARY_PROBE":
        baseline_kind = "PREREQUISITE_FIXTURE"
        fixture_kind = "recording-strategy-v1"
        allowed = {"strategy_ids": [str(_id(lane_id, "strategy"))]}
    elif lane_id == "ASSESSMENT_BOUNDARY_PROBE":
        baseline_kind = "PREREQUISITE_FIXTURE"
        fixture_kind = "completed-interview-v1"
        allowed = {
            "session_ids": [str(_id(lane_id, "session"))],
            "final_video_ids": [str(_id(lane_id, "video"))],
        }
    return _merge(
        {
            "lane_id": lane_id,
            "subject_ref": f"synthetic-{lane_id.casefold().replace('_', '-')}",
            "invitation_id": str(_id(lane_id, "invitation")),
            "applicant_id": str(_id(lane_id, "applicant")),
            "baseline_kind": baseline_kind,
            "fixture_kind": fixture_kind,
            "fixture_digest": FIXTURE_DIGEST if fixture_kind else None,
            "allowed_preexisting_effects": allowed,
            "probe_overlays": [],
            "target_effect_groups": list(PATHS),
            "trace_namespace": f"controlproof:{RUN_ID}:{lane_id}",
            "seed_correlation_id": str(_id(lane_id, "seed")),
        },
        updates,
    )


def six_subject_lanes() -> list[dict[str, Any]]:
    return [subject_lane(lane_id) for lane_id in LANES]


def policy_snapshot(**updates: Any) -> dict[str, Any]:
    return _merge(
        {
            "policy_version": "2026-08-v1",
            "content_digest": POLICY_DIGEST,
            "required_purposes": list(PURPOSES),
            "retention_days": 365,
            "received_at": FIXED_AT.isoformat(),
            "request_id": str(POLICY_REQUEST_ID),
            "source_ref": "artifacts/spec003/policy-response.json",
        },
        updates,
    )


def consent_state(
    lane_id: str = "NORMAL_ORDER",
    *,
    present: bool = True,
    **updates: Any,
) -> dict[str, Any]:
    lane = subject_lane(lane_id)
    consent_id = str(_id(lane_id, "consent"))
    return _merge(
        {
            "run_id": str(RUN_ID),
            "lane_id": lane_id,
            "subject_ref": lane["subject_ref"],
            "phase": "RECOVERED" if present else "BASELINE",
            "step_id": "consent.state.read",
            "attempt": 1,
            "invitation_status": "consented" if present else "identity_verified",
            "invitation_row_version": 2 if present else 1,
            "consent_record_ids": [consent_id] if present else [],
            "active_consent_count": 1 if present else 0,
            "consent_policy_versions": ["2026-08-v1"] if present else [],
            "consent_content_digests": [POLICY_DIGEST] if present else [],
            "accepted_purpose_sets": [list(PURPOSES)] if present else [],
            "consented_state_change_ids": (
                [str(_id(lane_id, "state-change"))] if present else []
            ),
            "consent_completed_event_ids": (
                [str(_id(lane_id, "consent-event"))] if present else []
            ),
            "trace_ids": [TRACE_DIGEST] if present else [],
            "captured_at": FIXED_AT.isoformat(),
            "source_status": "PRESENT" if present else "ABSENT",
            "source_error_code": None,
            "state_digest": STATE_DIGEST,
        },
        updates,
    )


def processing_attempt(
    path_id: str = "DOCUMENT_ANALYSIS",
    *,
    lane_id: str = "DOCUMENT_BYPASS",
    response_class: str = "DENIED",
    **updates: Any,
) -> dict[str, Any]:
    if path_id not in PATHS:
        raise ValueError(f"unknown Spec 003 path: {path_id}")
    lane = subject_lane(lane_id)
    operation = {
        "DOCUMENT_ANALYSIS": "createSubmissionUploadIntent",
        "RECORDING": "createInterviewSession",
        "AI_ASSESSMENT": "report.generation_requested",
    }[path_id]
    return _merge(
        {
            "attempt_id": str(_id(lane_id, f"{path_id}-attempt")),
            "run_id": str(RUN_ID),
            "lane_id": lane_id,
            "subject_ref": lane["subject_ref"],
            "path_id": path_id,
            "entry_kind": "DOMAIN_EVENT" if path_id == "AI_ASSESSMENT" else "HTTP",
            "operation_id": operation,
            "request_id": str(_id(lane_id, f"{path_id}-request")),
            "trace_id_digest": TRACE_DIGEST,
            "sent_at": FIXED_AT.isoformat(),
            "response_at": FIXED_AT.isoformat(),
            "response_class": response_class,
            "status_code": 403 if response_class == "DENIED" else 202,
            "sanitized_reason_code": (
                "CONSENT_REQUIRED" if response_class == "DENIED" else None
            ),
            "source_ref": ARTIFACT_REF,
        },
        updates,
    )


def protected_effect(
    path_id: str = "DOCUMENT_ANALYSIS",
    *,
    lane_id: str = "DOCUMENT_BYPASS",
    new_effect_ids: list[str] | None = None,
    source_status: str = "ABSENT",
    **updates: Any,
) -> dict[str, Any]:
    lane = subject_lane(lane_id)
    return _merge(
        {
            "run_id": str(RUN_ID),
            "lane_id": lane_id,
            "subject_ref": lane["subject_ref"],
            "phase": "INJECTED",
            "step_id": f"effects.{path_id.casefold()}.read",
            "attempt": 1,
            "effect_group": path_id,
            "request_ids": [],
            "start_receipt_ids": [],
            "result_ids": [],
            "status_projection": {},
            "fixture_effect_ids": [],
            "new_effect_ids": new_effect_ids or [],
            "source_status": source_status,
            "source_error_code": None,
            "state_digest": STATE_DIGEST,
            "captured_at": FIXED_AT.isoformat(),
        },
        updates,
    )


def causal_event(
    kind: str = "CONSENT_COMMITTED",
    *,
    lane_id: str = "NORMAL_ORDER",
    path_id: str | None = None,
    **updates: Any,
) -> dict[str, Any]:
    lane = subject_lane(lane_id)
    return _merge(
        {
            "causal_event_id": str(_id(lane_id, f"{kind}:{path_id or 'consent'}")),
            "kind": kind,
            "run_id": str(RUN_ID),
            "lane_id": lane_id,
            "subject_ref": lane["subject_ref"],
            "path_id": path_id,
            "domain_identity": {"request_id": str(POLICY_REQUEST_ID)},
            "occurred_at": FIXED_AT.isoformat(),
            "observed_at": FIXED_AT.isoformat(),
            "source_type": "database",
            "source_ref": ARTIFACT_REF,
        },
        updates,
    )


def causal_edge(
    from_event_id: str,
    to_event_id: str,
    *,
    status: str = "PROVEN",
    **updates: Any,
) -> dict[str, Any]:
    return _merge(
        {
            "from_event_id": from_event_id,
            "to_event_id": to_event_id,
            "relation": "PROGRAM_ORDER",
            "proof_refs": [ARTIFACT_REF],
            "status": status,
        },
        updates,
    )


def fault_receipt(**updates: Any) -> dict[str, Any]:
    lane = subject_lane("CONSENT_FAULT_RECOVERY")
    return _merge(
        {
            "schema_version": "controlproof.whyyou-consent-fault-receipt.v1",
            "receipt_id": str(_id("fault", "receipt")),
            "run_id": str(RUN_ID),
            "lane_id": lane["lane_id"],
            "subject_ref": lane["subject_ref"],
            "invitation_id": lane["invitation_id"],
            "applicant_id": lane["applicant_id"],
            "fault_variant": "AFTER_CONSENT_RECORD_BEFORE_STATE",
            "boundary": "AFTER_CONSENT_RECORD_BEFORE_INVITATION_STATE",
            "request_id": str(_id("fault", "request")),
            "triggered_at": FIXED_AT.isoformat(),
            "one_shot_consumed": True,
        },
        updates,
    )


def recovery_record(
    *,
    restore_status: str = "SUCCEEDED",
    **updates: Any,
) -> dict[str, Any]:
    lane = subject_lane("CONSENT_FAULT_RECOVERY")
    succeeded = restore_status == "SUCCEEDED"
    return _merge(
        {
            "run_id": str(RUN_ID),
            "lane_id": lane["lane_id"],
            "subject_ref": lane["subject_ref"],
            "marker_removed": succeeded,
            "consumed_token_removed": succeeded,
            "hook_inactive": succeeded,
            "failed_request_effects_zero": succeeded,
            "normal_retry_succeeded": succeeded,
            "logical_consent_count": 1 if succeeded else None,
            "consent_completed_event_count": 1 if succeeded else None,
            "processing_order_proven": succeeded,
            "restore_status": restore_status,
            "manual_cleanup_required": not succeeded,
        },
        updates,
    )


def n02_fact_set(
    verdict: Literal["PASS", "FAIL", "INCONCLUSIVE"] = "PASS",
) -> dict[str, Any]:
    lane_by_path = {
        "DOCUMENT_ANALYSIS": "DOCUMENT_BYPASS",
        "RECORDING": "RECORDING_BOUNDARY_PROBE",
        "AI_ASSESSMENT": "ASSESSMENT_BOUNDARY_PROBE",
    }
    attempts = {
        path: processing_attempt(path, lane_id=lane_by_path[path]) for path in PATHS
    }
    effects = {
        path: protected_effect(path, lane_id=lane_by_path[path]) for path in PATHS
    }
    if verdict == "FAIL":
        effects["RECORDING"] = protected_effect(
            "RECORDING",
            lane_id="RECORDING_BOUNDARY_PROBE",
            new_effect_ids=[str(_id("RECORDING", "session"))],
            source_status="PRESENT",
        )
    elif verdict == "INCONCLUSIVE":
        effects["AI_ASSESSMENT"] = protected_effect(
            "AI_ASSESSMENT",
            lane_id="ASSESSMENT_BOUNDARY_PROBE",
            source_status="UNAVAILABLE",
            source_error_code="OBSERVER_UNAVAILABLE",
        )
    return {
        "verdict": verdict,
        "lanes": six_subject_lanes(),
        "policy": policy_snapshot(),
        "consent": consent_state(),
        "attempts": attempts,
        "effects": effects,
        "fault_receipt": fault_receipt(),
        "recovery": recovery_record(),
    }


def pass_facts() -> dict[str, Any]:
    return n02_fact_set("PASS")


def fail_facts() -> dict[str, Any]:
    return n02_fact_set("FAIL")


def inconclusive_facts() -> dict[str, Any]:
    return n02_fact_set("INCONCLUSIVE")
