"""One N-02 Run owns all six lanes, judgement and a reviewable sealed bundle."""

from __future__ import annotations

import json
from dataclasses import replace
from uuid import UUID

import pytest

from engine.adapters.base import AdapterResult
from engine.evidence import verify_bundle
from engine.models import (
    N02LaneId,
    Presence,
    ProcessingResponseClass,
    ProtectedPathId,
    RunState,
    Verdict,
    sha256_bytes,
)
from engine.presentation import load_bundle_summary
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, FakeN02Adapters, make_adapters


class CountingN02(FakeN02Adapters):
    def __init__(self, **options):
        super().__init__(**options)
        self.seed_count = 0
        self.teardown_count = 0

    def seed_lanes(self, *, run_id: str):
        self.seed_count += 1
        return super().seed_lanes(run_id=run_id)

    def teardown_lanes(self, *, run_id: str, lanes):
        self.teardown_count += 1
        return super().teardown_lanes(run_id=run_id, lanes=lanes)


def _runner(tmp_path, fake):
    adapters, _ = make_adapters()
    adapters = replace(
        adapters,
        n02_seed=fake,
        n02_consent=fake,
        n02_processing=fake,
        n02_causality=fake,
        n02_fault=fake,
        n02_observer=fake,
    )
    return build_profile_runner(load("scenarios/N-02.yaml"), adapters, tmp_path, clock=FakeClock())


def test_complete_six_lane_run_seals_verified_bundle_and_review(tmp_path) -> None:
    fake = CountingN02()
    runner = _runner(tmp_path, fake)
    readiness = runner.preflight("whyyou-local")
    assert readiness.status.value == "READY"

    run, judgement, bundle = runner.execute(readiness)
    summary = load_bundle_summary(bundle)
    verified = verify_bundle(bundle)

    assert fake.seed_count == 1
    assert fake.teardown_count == 1
    assert run.state is RunState.COMPLETED
    assert judgement.verdict is Verdict.PASS
    assert [item.assertion_id for item in judgement.assertion_results] == [
        f"N02-A{index}" for index in range(1, 8)
    ]
    assert verified["bundle_status"] == "VERIFIED"
    assert verified["checked_evidence_requirements"] == [
        f"EV3-{index:02d}" for index in range(1, 11)
    ]
    assert len(json.loads((bundle / "n02-lanes.json").read_text(encoding="utf-8"))["lanes"]) == 6
    assert run.policy_snapshot_digest == sha256_bytes((bundle / "policy-and-consent.json").read_bytes())
    policy_evidence = json.loads((bundle / "policy-and-consent.json").read_text(encoding="utf-8"))
    assert policy_evidence["normal_commit"]["code"] == "CONSENT_COMMITTED"
    assert policy_evidence["failed_commit"]["status_code"] == 500
    assert run.lane_manifest_digest == sha256_bytes((bundle / "n02-lanes.json").read_bytes())
    assert summary["verdict"] == "PASS"
    assert set(summary["path_results"].values()) == {"PASS"}
    assert summary["environment_kind"] == "LOCAL_EMULATED"
    assert summary["aws_deployment_status"] == "NOT_RUN"
    assert set(summary["unverified_scope"]) == {"AWS", "N-01", "N-03"}


def test_direct_recording_effect_remains_fail_in_combined_run(tmp_path) -> None:
    class RecordingViolation(CountingN02):
        def read_effects(self, *, path_id, subject, phase, step_id):
            observed = super().read_effects(
                path_id=path_id, subject=subject, phase=phase, step_id=step_id
            )
            if (
                path_id == ProtectedPathId.RECORDING.value
                and subject["lane_id"] == N02LaneId.RECORDING_BOUNDARY_PROBE.value
            ):
                return observed.model_copy(update={
                    "current_effect_ids": ("synthetic-new-recording",),
                    "new_effect_ids": ("synthetic-new-recording",),
                    "source_status": Presence.PRESENT,
                })
            return observed

    fake = RecordingViolation()
    runner = _runner(tmp_path, fake)
    run, judgement, bundle = runner.execute(runner.preflight("whyyou-local"))

    assert run.state is RunState.COMPLETED
    assert judgement.verdict is Verdict.FAIL
    assert "N02-A3" in {item.assertion_id for item in judgement.assertion_results if item.status.value == "FAIL"}
    assert verify_bundle(bundle)["bundle_status"] == "VERIFIED"


def test_target_assessment_start_receipt_is_sealed_and_linked(tmp_path) -> None:
    event_id = UUID("00000000-0000-7000-8000-000000000041")
    receipt_id = UUID("00000000-0000-7000-8000-000000000042")

    class AssessmentStart(CountingN02):
        def attempt(self, *, path_id, subject, drive=False):
            result = super().attempt(path_id=path_id, subject=subject, drive=drive)
            if subject["lane_id"] == "ASSESSMENT_BOUNDARY_PROBE" and path_id == "AI_ASSESSMENT":
                return result.model_copy(update={
                    "response_class": ProcessingResponseClass.SUBMITTED,
                    "probe_input_effect_id": f"event:{event_id}",
                })
            return result

        def read_effects(self, *, path_id, subject, phase, step_id):
            result = super().read_effects(
                path_id=path_id, subject=subject, phase=phase, step_id=step_id
            )
            if subject["lane_id"] == "ASSESSMENT_BOUNDARY_PROBE" and path_id == "AI_ASSESSMENT":
                return result.model_copy(update={
                    "source_status": Presence.PRESENT,
                    "current_effect_ids": (f"event:{event_id}",),
                    "probe_input_effect_ids": (f"event:{event_id}",),
                    "start_receipt_ids": (str(receipt_id),),
                })
            return result

        def read_processing_receipts(self, *, run_id, lane_id, subject_ref):
            if lane_id != "ASSESSMENT_BOUNDARY_PROBE":
                return AdapterResult(True, "RECEIPTS_READ", {"receipts": ()})
            return AdapterResult(True, "RECEIPTS_READ", {"receipts": ({
                "schema_version": "controlproof.whyyou-processing-receipt.v1",
                "receipt_id": str(receipt_id),
                "run_id": run_id,
                "lane_id": lane_id,
                "subject_ref": subject_ref,
                "path_id": "AI_ASSESSMENT",
                "boundary": "REPORT_ASSESSMENT_STARTED",
                "request_or_event_id": str(event_id),
                "trace_id_digest": "a" * 64,
                "observed_at": "2026-10-02T00:00:00+00:00",
            },)})

    runner = _runner(tmp_path, AssessmentStart())
    _, judgement, bundle = runner.execute(runner.preflight("whyyou-local"))
    observations = [
        json.loads(line)
        for line in (bundle / "observations.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert judgement.assertion_results[3].status.value == "FAIL"
    assert any(row.get("receipt_id") == str(receipt_id) for row in observations)
    assert verify_bundle(bundle)["bundle_status"] == "VERIFIED"


def test_restore_failure_keeps_direct_facts_and_blocks_next_fault_run(tmp_path) -> None:
    fake = CountingN02(restore_succeeded=False)
    runner = _runner(tmp_path, fake)
    run, judgement, bundle = runner.execute(runner.preflight("whyyou-local"))

    assert run.state is RunState.RESTORE_FAILED
    assert judgement.verdict is Verdict.INCONCLUSIVE
    assert verify_bundle(bundle)["bundle_status"] == "VERIFIED"
    assert fake.teardown_count == 0
    assert any((tmp_path / "blocks").glob("*.json"))
    with pytest.raises(RuntimeError, match="blocked"):
        runner.execute(runner.preflight("whyyou-local"))
    assert fake.seed_count == 1


def test_unproven_recovered_processing_is_an_a7_result_not_a_restore_failure(tmp_path) -> None:
    """ID-003-14: T084 attempt 2 removed the fault and confirmed the safe state, but a path
    stayed closed after the retried consent; the Run became RESTORE_FAILED, held teardown and
    blocked the target. Restore safety and the retry outcome are separate facts."""
    from engine.lifecycle import RestoreBlockStore

    fake = CountingN02(blocked_paths=frozenset({ProtectedPathId.RECORDING}))
    runner = _runner(tmp_path, fake)
    run, judgement, bundle = runner.execute(runner.preflight("whyyou-local"))
    recovery = json.loads((bundle / "recovery.json").read_text(encoding="utf-8"))
    statuses = {item.assertion_id: item.status.value for item in judgement.assertion_results}

    assert recovery["restore_status"] == "SUCCEEDED"
    assert recovery["manual_cleanup_required"] is False
    assert recovery["processing_order_proven"] is False
    assert run.state is RunState.COMPLETED
    assert fake.teardown_count == 1
    assert statuses["N02-A7"] == "FAIL"
    assert judgement.verdict is Verdict.FAIL
    assert not RestoreBlockStore(tmp_path).blocked("whyyou-local", "n02-consent-order")
    assert verify_bundle(bundle)["bundle_status"] == "VERIFIED"


@pytest.mark.parametrize("boundary", ["REPORT_ASSESSMENT_REFUSED", "REPORT_HANDLER_ENTERED"])
def test_target_assessment_refusal_is_sealed_linked_and_passes_a4(tmp_path, boundary) -> None:
    """ID-003-17: refusal receipt + zero effects passes A4; the consumer's processed row for
    the runner input is bookkeeping, and a refusal claim without a linked target refusal
    receipt cannot be sealed."""
    event_id = UUID("00000000-0000-7000-8000-000000000051")
    receipt_id = UUID("00000000-0000-7000-8000-000000000052")

    class AssessmentRefusal(CountingN02):
        def attempt(self, *, path_id, subject, drive=False):
            result = super().attempt(path_id=path_id, subject=subject, drive=drive)
            if subject["lane_id"] == "ASSESSMENT_BOUNDARY_PROBE" and path_id == "AI_ASSESSMENT":
                return result.model_copy(update={
                    "response_class": ProcessingResponseClass.SUBMITTED,
                    "probe_input_effect_id": f"event:{event_id}",
                })
            return result

        def read_effects(self, *, path_id, subject, phase, step_id):
            result = super().read_effects(
                path_id=path_id, subject=subject, phase=phase, step_id=step_id
            )
            if subject["lane_id"] == "ASSESSMENT_BOUNDARY_PROBE" and path_id == "AI_ASSESSMENT":
                return result.model_copy(update={
                    "source_status": Presence.PRESENT,
                    "current_effect_ids": (f"event:{event_id}", f"processed:{event_id}"),
                    "probe_input_effect_ids": (f"event:{event_id}",),
                    "probe_bookkeeping_effect_ids": (f"processed:{event_id}",),
                    "refusal_receipt_ids": (str(receipt_id),),
                })
            return result

        def read_processing_receipts(self, *, run_id, lane_id, subject_ref):
            if lane_id != "ASSESSMENT_BOUNDARY_PROBE":
                return AdapterResult(True, "RECEIPTS_READ", {"receipts": ()})
            return AdapterResult(True, "RECEIPTS_READ", {"receipts": ({
                "schema_version": "controlproof.whyyou-processing-receipt.v1",
                "receipt_id": str(receipt_id),
                "run_id": run_id,
                "lane_id": lane_id,
                "subject_ref": subject_ref,
                "path_id": "AI_ASSESSMENT",
                "boundary": boundary,
                "request_or_event_id": str(event_id),
                "trace_id_digest": "a" * 64,
                "observed_at": "2026-10-02T00:00:00+00:00",
            },)})

    runner = _runner(tmp_path, AssessmentRefusal())
    if boundary != "REPORT_ASSESSMENT_REFUSED":
        from engine.executors.n02 import N02ExecutionError

        with pytest.raises(N02ExecutionError, match="failed verification"):
            runner.execute(runner.preflight("whyyou-local"))
        sealed = next(path for path in tmp_path.iterdir() if (path / "manifest.json").exists())
        assert "protected-effects.jsonl:refusal-receipt-link" in (
            verify_bundle(sealed)["mismatched_files"]
        )
        return
    _, judgement, bundle = runner.execute(runner.preflight("whyyou-local"))
    observations = [
        json.loads(line)
        for line in (bundle / "observations.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert judgement.assertion_results[3].status.value == "PASS"
    assert any(row.get("receipt_id") == str(receipt_id) for row in observations)
    assert verify_bundle(bundle)["bundle_status"] == "VERIFIED"
