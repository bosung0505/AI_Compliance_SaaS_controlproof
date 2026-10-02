from __future__ import annotations

import json
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

from engine.adapters.base import AdapterResult
from engine.adapters.whyyou.consent_fault import WhyYouConsentFaultAdapter
from engine.models import ConsentStateSnapshot, N02LaneId, Presence, utcnow


def _subject():
    return {
        "run_id": str(uuid4()),
        "lane_id": N02LaneId.CONSENT_FAULT_RECOVERY.value,
        "subject_ref": "synthetic-fault-subject",
        "invitation_id": str(uuid4()),
        "applicant_id": str(uuid4()),
    }


class _AbsentConsent:
    def read_state(self, *, subject, phase, step_id):
        return ConsentStateSnapshot(
            run_id=subject["run_id"],
            lane_id=subject["lane_id"],
            subject_ref=subject["subject_ref"],
            phase=phase,
            step_id=step_id,
            attempt=1,
            invitation_status="identity_verified",
            invitation_row_version=1,
            captured_at=utcnow(),
            source_status=Presence.ABSENT,
            state_digest="a" * 64,
        )


def test_marker_schema_subject_ttl_and_digest_are_canonical(settings) -> None:
    subject = _subject()
    adapter = WhyYouConsentFaultAdapter(settings)
    result = adapter.apply_consent_fault(
        run_id=subject["run_id"],
        subject=subject,
        expires_at=utcnow() + timedelta(minutes=5),
    )
    marker_path = settings.fault_root / "consent" / f"{subject['invitation_id']}.json"
    marker = json.loads(marker_path.read_text())
    assert result.ok and len(result.data["marker_digest"]) == 64
    assert marker["schema_version"] == "controlproof.whyyou-consent-fault.v1"
    assert marker["run_id"] == subject["run_id"]
    assert marker["subject_ref"] == subject["subject_ref"]
    assert marker["one_shot"] is True


def test_invalid_ttl_lane_run_and_path_like_identity_are_rejected(settings) -> None:
    subject = _subject()
    adapter = WhyYouConsentFaultAdapter(settings)
    too_long = adapter.apply_consent_fault(
        run_id=subject["run_id"],
        subject=subject,
        expires_at=utcnow() + timedelta(minutes=11),
    )
    wrong_lane = adapter.apply_consent_fault(
        run_id=subject["run_id"],
        subject=subject | {"lane_id": N02LaneId.NORMAL_ORDER.value},
        expires_at=utcnow() + timedelta(minutes=5),
    )
    wrong_run = adapter.apply_consent_fault(
        run_id=str(uuid4()),
        subject=subject,
        expires_at=utcnow() + timedelta(minutes=5),
    )
    traversal = adapter.apply_consent_fault(
        run_id=subject["run_id"],
        subject=subject | {"invitation_id": "../../outside"},
        expires_at=utcnow() + timedelta(minutes=5),
    )
    assert {too_long.code, wrong_lane.code, wrong_run.code, traversal.code} == {
        "CONSENT_FAULT_TTL_INVALID",
        "CONSENT_FAULT_LANE_MISMATCH",
        "CONSENT_FAULT_RUN_MISMATCH",
        "CONSENT_FAULT_SUBJECT_INVALID",
    }


def test_receipt_reader_selects_exact_current_run_subject_and_rejects_duplicates(settings) -> None:
    subject = _subject()
    adapter = WhyYouConsentFaultAdapter(settings)
    path = settings.fault_root / "receipts" / f"{subject['run_id']}.jsonl"
    path.parent.mkdir(parents=True)
    current = {
        "schema_version": "controlproof.whyyou-consent-fault-receipt.v1",
        "receipt_id": str(uuid4()),
        "run_id": subject["run_id"],
        "lane_id": subject["lane_id"],
        "subject_ref": subject["subject_ref"],
        "invitation_id": subject["invitation_id"],
        "applicant_id": subject["applicant_id"],
        "request_id": str(uuid4()),
        "fault_type": "consent_after_record_before_state_v1",
        "fault_variant": "AFTER_CONSENT_RECORD_BEFORE_STATE",
        "boundary": "AFTER_CONSENT_RECORD_BEFORE_INVITATION_STATE",
        "triggered_at": utcnow().isoformat(),
        "one_shot_consumed": True,
    }
    foreign = current | {"receipt_id": str(uuid4()), "subject_ref": "foreign"}
    path.write_text("\n".join((json.dumps(foreign), json.dumps(current))), encoding="utf-8")
    receipt = adapter.read_consent_fault_receipt(
        run_id=subject["run_id"], subject=subject
    )
    assert receipt.subject_ref == subject["subject_ref"]
    path.write_text("\n".join((json.dumps(current), json.dumps(current))), encoding="utf-8")
    duplicate = adapter.read_consent_fault_receipt(
        run_id=subject["run_id"], subject=subject
    )
    assert isinstance(duplicate, AdapterResult)
    assert duplicate.code == "CONSENT_FAULT_RECEIPT_CARDINALITY_INVALID"


def test_restore_removes_owned_marker_and_token_then_proves_safe_state(settings) -> None:
    subject = _subject()
    adapter = WhyYouConsentFaultAdapter(settings, consent_adapter=_AbsentConsent())
    applied = adapter.apply_consent_fault(
        run_id=subject["run_id"],
        subject=subject,
        expires_at=utcnow() + timedelta(minutes=5),
    )
    assert applied.ok
    token = (
        settings.fault_root
        / "consumed"
        / f"{subject['run_id']}-{subject['invitation_id']}.consent"
    )
    token.parent.mkdir(parents=True)
    token.write_text("consumed", encoding="utf-8")
    restored = adapter.restore_consent_fault(
        run_id=subject["run_id"], subject=subject
    )
    assert restored.ok
    assert restored.data == {
        "marker_removed": True,
        "consumed_token_removed": True,
        "hook_inactive": True,
        "failed_request_effects_zero": True,
        "manual_cleanup_required": False,
    }


def test_foreign_marker_is_never_deleted_and_requires_manual_cleanup(settings) -> None:
    subject = _subject()
    adapter = WhyYouConsentFaultAdapter(settings, consent_adapter=_AbsentConsent())
    adapter.apply_consent_fault(
        run_id=subject["run_id"],
        subject=subject,
        expires_at=utcnow() + timedelta(minutes=5),
    )
    marker_path = settings.fault_root / "consent" / f"{subject['invitation_id']}.json"
    marker = json.loads(marker_path.read_text())
    marker["run_id"] = str(uuid4())
    marker_path.write_text(json.dumps(marker), encoding="utf-8")
    result = adapter.restore_consent_fault(
        run_id=subject["run_id"], subject=subject
    )
    assert not result.ok
    assert result.code == "CONSENT_FAULT_FOREIGN_MARKER"
    assert result.data["manual_cleanup_required"] is True
    assert marker_path.exists()


def test_n02_cleanup_safe_probe_requires_zero_consent_document_effects_and_no_fault_files(settings) -> None:
    subject = _subject()
    effects = SimpleNamespace(source_status=Presence.ABSENT, current_effect_ids=())
    processing = SimpleNamespace(read_effects=lambda **_kwargs: effects)
    adapter = WhyYouConsentFaultAdapter(
        settings,
        consent_adapter=_AbsentConsent(),
        processing_adapter=processing,
        cleanup_counts_reader=lambda _subject: {"consent_records": 0, "invitation_events": 0},
    )
    assert adapter.target_safe(subject=subject) is True
    marker = settings.fault_root / "consent" / f"{subject['invitation_id']}.json"
    marker.parent.mkdir(parents=True)
    marker.write_text("{}", encoding="utf-8")
    assert adapter.target_safe(subject=subject) is False
    marker.unlink()
    token = settings.fault_root / "consumed" / f"{subject['run_id']}-{subject['invitation_id']}.consent"
    token.parent.mkdir(parents=True)
    token.write_text("consumed", encoding="utf-8")
    assert adapter.target_safe(subject=subject) is False
    token.unlink()
    effects.current_effect_ids = ("upload:unexpected",)
    assert adapter.target_safe(subject=subject) is False
    effects.current_effect_ids = ()
    adapter.cleanup_counts_reader = lambda _subject: {"consent_records": 1, "invitation_events": 0}
    assert adapter.target_safe(subject=subject) is False
    adapter.cleanup_counts_reader = lambda _subject: (_ for _ in ()).throw(ValueError("unavailable"))
    assert adapter.target_safe(subject=subject) is False
