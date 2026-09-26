from __future__ import annotations

from datetime import UTC, datetime, timedelta

from engine.adapters.base import AdapterResult, AdapterSet, CapabilityProbeResult
from engine.adapters.whyyou.capability import CAPABILITY_VERSIONS
from engine.models import ReadinessStatus, TargetSnapshot, TargetSourceKind


class FakeClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 9, 24, tzinfo=UTC)

    def now(self):
        return self.current

    def sleep(self, seconds: float) -> None:
        self.current += timedelta(seconds=seconds)


class FakeTarget:
    def __init__(self, *, target_exists=True, overrides=None):
        self.target_exists = target_exists
        self.overrides = overrides or {}
        self.snapshot = TargetSnapshot(
            target_id="whyyou-local",
            source_kind=TargetSourceKind.GIT_WORKTREE,
            git_commit_sha="a" * 40,
            git_dirty=False,
            openapi_digest="b" * 64,
            schema_migration_head="head-v1",
            schema_signature_digest="c" * 64,
            model_fixture_id="h03-report-v1",
            model_fixture_digest="ce09b95403b34e1390502c90f5c5edc518ddf65d38c8ce881617a37cac6d16b1",
        )

    @property
    def registrations(self):
        return CAPABILITY_VERSIONS

    def capture_target_snapshot(self):
        return self.snapshot

    def target_feature_exists(self):
        return self.target_exists

    def probe(self, capability):
        status = self.overrides.get(capability, ReadinessStatus.READY)
        return CapabilityProbeResult(
            capability,
            status,
            "fixture probe",
            None if status is ReadinessStatus.READY else "repair fixture capability",
        )


class FakeSeed:
    def seed(self, *, run_id, subject_ref):
        return AdapterResult(
            True,
            "SUBJECT_SEEDED",
            {
                "subject_ref": subject_ref,
                "synthetic": True,
                "seed_correlation_id": f"cp-{run_id}",
                "invitation_id": "00000000-0000-0000-0000-000000000001",
                "interview_session_id": "00000000-0000-0000-0000-000000000002",
                "target_stage_id": "00000000-0000-0000-0000-000000000003",
                "pipeline_row_version": 1,
            },
        )

    def trigger(self, *, run_id, subject):
        return AdapterResult(
            True,
            "REPORTING_TRIGGERED",
            {"outbox_event_id": "00000000-0000-0000-0000-000000000004"},
        )

    def teardown(self, *, run_id, subject):
        return AdapterResult(True, "TEARDOWN_COMPLETE")


class FakeState:
    def __init__(self, *, reason_present=True, decision_accepted=False, mutate=False):
        self.reason_present = reason_present
        self.decision_accepted = decision_accepted
        self.mutate = mutate
        self.calls = 0

    def _state(self):
        self.calls += 1
        return {
            "invitation_status": "reviewed" if self.mutate and self.calls > 1 else "completed",
            "recruiting_stage_id": "stage-2" if self.mutate and self.calls > 1 else "stage-1",
            "pipeline_row_version": 2 if self.mutate and self.calls > 1 else 1,
            "final_decision_count": 1 if self.mutate and self.calls > 1 else 0,
            "latest_final_decision_actor_type": "SYSTEM"
            if self.mutate and self.calls > 1
            else None,
            "report_presence": "ABSENT",
            "report_status": None,
        }

    def snapshot(self, *, subject, phase):
        return AdapterResult(True, "STATE_CAPTURED", {"state": self._state(), "phase": phase})

    def report_status(self, *, subject):
        return AdapterResult(
            True,
            "REPORT_STATUS",
            {"presence": "ABSENT", "status": "queued", "exchange": {"status": 202}},
        )

    def attempt_final_decision(self, *, subject):
        return AdapterResult(
            True,
            "DECISION_ATTEMPTED",
            {
                "accepted": self.decision_accepted,
                "reason_present": self.reason_present,
                "reason_code": "REPORT_NOT_AVAILABLE" if self.reason_present else None,
                "exchange": {"status": 409 if self.reason_present else 404},
            },
        )


class FakeFault:
    def __init__(self, *, effect=True, restore=True, processing="READY"):
        self.effect = effect
        self.restore_ok = restore
        self.processing = processing

    def apply(self, *, run_id, subject, expires_at):
        return AdapterResult(True, "FAULT_MARKER_APPLIED", {"run_id": run_id})

    def probe_effect(self, *, run_id, subject, trigger):
        return AdapterResult(
            self.effect,
            "FAULT_EFFECT_CONFIRMED" if self.effect else "TRIGGER_RECEIPT_MISSING",
            {"run_id": run_id, "outbox_event_id": trigger["outbox_event_id"]},
        )

    def restore(self, *, run_id, subject):
        return AdapterResult(
            self.restore_ok,
            "ENVIRONMENT_RESTORED" if self.restore_ok else "ENVIRONMENT_RESTORE_FAILED",
            {
                "environment_restore": "SUCCEEDED" if self.restore_ok else "FAILED",
                "report_processing_recovery": self.processing,
                "marker_inactive": self.restore_ok,
                "worker_healthy": self.restore_ok,
            },
        )

    def target_safe(self, *, subject_ref):
        return self.restore_ok


class FakeBrowser:
    def __init__(self, status_class="failed"):
        self.status_class = status_class
        self.closed = False

    def capture_review(self, *, subject):
        return AdapterResult(
            True,
            "BROWSER_CAPTURED",
            {
                "projection": {
                    "route": "/review/{session_id}",
                    "visible_text": "리포트 생성 실패",
                    "ready_content_visible": False,
                    "decision_control_visible": True,
                    "status_class": self.status_class,
                    "viewport": {"width": 1440, "height": 900},
                },
                "screenshot_bytes": b"synthetic-png",
            },
        )

    def close(self):
        self.closed = True


def make_adapters(
    *,
    status_class="failed",
    reason_present=True,
    decision_accepted=False,
    mutate=False,
    effect=True,
    restore=True,
    processing="READY",
    target_exists=True,
    readiness_overrides=None,
):
    target = FakeTarget(target_exists=target_exists, overrides=readiness_overrides)
    browser = FakeBrowser(status_class=status_class)
    return (
        AdapterSet(
            target=target,
            capability=target,
            seed=FakeSeed(),
            state=FakeState(
                reason_present=reason_present,
                decision_accepted=decision_accepted,
                mutate=mutate,
            ),
            fault=FakeFault(effect=effect, restore=restore, processing=processing),
            browser=browser,
        ),
        browser,
    )
