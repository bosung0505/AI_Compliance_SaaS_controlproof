"""T005 — N-03 pure judge (contracts/assertions-v9.md; FR-030, FR-031, FR-050, SC-004)."""

from __future__ import annotations

from uuid import UUID

import pytest

from engine.models import ConsentStateSnapshot, N02LaneId, N03LaneId, utcnow
from engine.n03 import REQUIRED_RESIDUE_TABLES, assertions_for, cleanup_verified, verdict_for

RUN_ID = "22222222-2222-4222-8222-222222222222"
CURRENT = {"version": "2026-08-v1", "digest": "a" * 64}
STALE = {"version": "2026-08-v1-stale", "digest": "a" * 63 + "b"}
RECORD_ID = str(UUID(int=10))


def _subject(lane: str) -> dict:
    return {
        "run_id": RUN_ID,
        "lane_id": lane,
        "subject_ref": f"n03-{lane}",
        "invitation_id": str(UUID(int=1 if lane == "stale" else 2)),
        "applicant_id": str(UUID(int=3 if lane == "stale" else 4)),
    }


def _state(lane: str, *, step: str, records: tuple[str, ...] = (), digest: str = "d" * 64, status="PRESENT") -> dict:
    base = {
        "run_id": RUN_ID,
        "lane_id": lane,
        "subject_ref": f"n03-{lane}",
        "phase": "INJECTED",
        "step_id": step,
        "attempt": 1,
        "invitation_status": "consented" if records else "identity_verified",
        "invitation_row_version": 2 if records else 1,
        "captured_at": utcnow(),
        "state_digest": digest,
    }
    if status == "UNAVAILABLE":
        snapshot = ConsentStateSnapshot(**base, source_status="UNAVAILABLE", source_error_code="OPERATIONALERROR")
    elif records:
        snapshot = ConsentStateSnapshot(
            **base,
            consent_record_ids=tuple(UUID(value) for value in records),
            active_consent_count=len(records),
            consent_policy_versions=(CURRENT["version"],),
            consent_content_digests=(CURRENT["digest"],),
            source_status="PRESENT",
        )
    else:
        snapshot = ConsentStateSnapshot(**base, source_status="ABSENT")
    return snapshot.model_dump(mode="json")


def _attempt(**overrides) -> dict:
    value = {
        "subject": _subject("stale"),
        "current": dict(CURRENT),
        "submitted": dict(STALE),
        "response_status": 422,
        "adapter_code": "CONSENT_POLICY_MISMATCH",
        "durable_state": "NOT_COMMITTED",
    }
    value.update(overrides)
    return value


def _latest(**overrides) -> dict:
    value = {
        "subject": _subject("stale"),
        "reread": dict(CURRENT),
        "response_status": 201,
        "adapter_code": "CONSENT_COMMIT_RESPONSE_RECEIVED",
        "stored": {"policy_version": CURRENT["version"], "evidence_digest": CURRENT["digest"]},
        "consent_record_id": RECORD_ID,
    }
    value.update(overrides)
    return value


def _recovery(**counts) -> dict:
    return {"status": "SUCCEEDED", "owned_residue_counts": {name: 0 for name in REQUIRED_RESIDUE_TABLES} | counts}


@pytest.fixture
def evidence() -> dict:
    past_record = (str(UUID(int=20)),)
    return {
        "stale_attempt": _attempt(),
        "stale_before": _state("stale", step="submit-stale-consent", digest="1" * 64),
        "stale_after": _state("stale", step="submit-stale-consent", digest="1" * 64),
        "latest_commit": _latest(),
        "past_before": _state("past", step="seed-lanes", records=past_record, digest="2" * 64),
        "past_after": _state("past", step="reread-and-commit", records=past_record, digest="2" * 64),
    }


def _run(evidence: dict, recovery: dict | None = None):
    return assertions_for(**evidence, recovery=recovery or _recovery())


def _statuses(results) -> dict[str, str]:
    return {item.assertion_id: item.status.value for item in results}


def test_all_pass(evidence) -> None:
    results = _run(evidence)
    assert _statuses(results) == {"N03-A1": "PASS", "N03-A2": "PASS", "N03-A3": "PASS"}
    assert [item.subject_ref for item in results] == ["stale", "stale", "past"]
    assert all(item.source_requirements == ("V4-N03",) for item in results)
    assert verdict_for(results, _recovery()) == "PASS"


def test_stale_accepted_with_2xx_fails(evidence) -> None:
    evidence["stale_attempt"] = _attempt(response_status=201, adapter_code="CONSENT_COMMIT_RESPONSE_RECEIVED")
    assert _statuses(_run(evidence))["N03-A1"] == "FAIL"


def test_stale_rejected_but_state_changed_fails(evidence) -> None:
    evidence["stale_after"] = _state("stale", step="submit-stale-consent", digest="9" * 64)
    assert _statuses(_run(evidence))["N03-A1"] == "FAIL"


def test_submitted_equal_to_current_is_runner_defect(evidence) -> None:
    evidence["stale_attempt"] = _attempt(submitted={"version": STALE["version"], "digest": CURRENT["digest"]})
    result = _run(evidence)[0]
    assert (result.status.value, result.reason_code.value) == ("INCONCLUSIVE", "INSUFFICIENT_EVIDENCE")
    assert "실행기 결함" in result.detail


@pytest.mark.parametrize("code", ["CONSENT_COMMIT_TRANSPORT_UNAVAILABLE", "CONSENT_COMMIT_RESPONSE_UNKNOWN"])
def test_stale_transport_error_is_inconclusive(evidence, code) -> None:
    evidence["stale_attempt"] = _attempt(response_status=None, adapter_code=code, durable_state="UNKNOWN")
    assert _statuses(_run(evidence))["N03-A1"] == "INCONCLUSIVE"


@pytest.mark.parametrize("field", ["stale_before", "stale_after"])
def test_stale_projection_missing_or_unavailable_is_inconclusive(evidence, field) -> None:
    evidence[field] = None
    assert _statuses(_run(evidence))["N03-A1"] == "INCONCLUSIVE"
    evidence[field] = _state("stale", step="submit-stale-consent", status="UNAVAILABLE")
    assert _statuses(_run(evidence))["N03-A1"] == "INCONCLUSIVE"


def test_latest_stored_differs_fails(evidence) -> None:
    evidence["latest_commit"] = _latest(stored={"policy_version": CURRENT["version"], "evidence_digest": "c" * 64})
    assert _statuses(_run(evidence)) == {"N03-A1": "PASS", "N03-A2": "FAIL", "N03-A3": "PASS"}


def test_latest_rejected_fails_and_unread_is_inconclusive(evidence) -> None:
    evidence["latest_commit"] = _latest(response_status=422, adapter_code="CONSENT_COMMIT_REJECTED")
    assert _statuses(_run(evidence))["N03-A2"] == "FAIL"
    evidence["latest_commit"] = _latest(stored=None)
    assert _statuses(_run(evidence))["N03-A2"] == "INCONCLUSIVE"
    evidence["latest_commit"] = _latest(response_status=None)
    assert _statuses(_run(evidence))["N03-A2"] == "INCONCLUSIVE"


def test_past_changed_fails(evidence) -> None:
    evidence["past_after"] = _state("past", step="reread-and-commit", records=(str(UUID(int=21)),), digest="3" * 64)
    assert _statuses(_run(evidence))["N03-A3"] == "FAIL"


def test_past_unavailable_is_inconclusive(evidence) -> None:
    evidence["past_after"] = _state("past", step="reread-and-commit", status="UNAVAILABLE")
    result = _run(evidence)[2]
    assert (result.status.value, result.reason_code.value) == ("INCONCLUSIVE", "INSUFFICIENT_EVIDENCE")


def test_recovery_failure_makes_verdict_inconclusive(evidence) -> None:
    failed = _recovery(outbox_events=2)
    results = _run(evidence, failed)
    assert set(_statuses(results).values()) == {"PASS"}
    assert verdict_for(results, failed) == "INCONCLUSIVE"
    tables = _recovery()["owned_residue_counts"]
    assert "applicant_access_tokens" not in tables and cleanup_verified(_recovery())


def test_unread_current_or_reread_policy_is_inconclusive(evidence) -> None:
    """T009: an executor that could not read the policy seals the attempt without identifiers."""
    evidence["stale_attempt"] = _attempt(
        current=None, submitted=None, response_status=None, adapter_code="NOT_ATTEMPTED", durable_state="NOT_ATTEMPTED"
    )
    evidence["latest_commit"] = _latest(reread=None, response_status=None, stored=None, adapter_code="NOT_ATTEMPTED")
    results = _run(evidence)
    assert _statuses(results) == {"N03-A1": "INCONCLUSIVE", "N03-A2": "INCONCLUSIVE", "N03-A3": "PASS"}
    assert results[0].actual["current"] is None and results[1].actual["reread"] is None


def test_success_class_without_exact_status_counts_as_2xx(evidence) -> None:
    """The consent adapter's success envelope carries no status code; ok=True is recorded as class 2xx."""
    evidence["stale_attempt"] = _attempt(
        response_status=None, response_class="2xx", adapter_code="CONSENT_COMMIT_RESPONSE_RECEIVED", durable_state="COMMITTED"
    )
    evidence["latest_commit"] = _latest(response_status=None, response_class="2xx")
    results = _run(evidence)
    assert _statuses(results)["N03-A1"] == "FAIL" and _statuses(results)["N03-A2"] == "PASS"
    assert results[0].actual["response_class"] == "2xx"


def test_consent_state_lane_id_accepts_spec009_lanes_and_keeps_n02_values() -> None:
    assert _state("stale", step="x")["lane_id"] == "stale"
    snapshot = ConsentStateSnapshot.model_validate(_state("past", step="x"))
    assert snapshot.lane_id is N03LaneId.PAST
    n02 = ConsentStateSnapshot.model_validate(_state("past", step="x") | {"lane_id": "NORMAL_ORDER"})
    assert n02.lane_id is N02LaneId.NORMAL_ORDER
    assert n02.model_dump(mode="json")["lane_id"] == "NORMAL_ORDER"
