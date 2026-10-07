"""PR review regressions: restore timing and independently readable recovered evidence."""

import json

import pytest

from engine.evidence import EvidenceBundleWriter, verify_bundle
from engine.executors.n02 import N02ExecutionError
from engine.lifecycle import RestoreBlockStore
from engine.models import N02LaneId
from tests.fixtures.fake_adapters import FakeClock, FakeN02Adapters
from tests.integration.test_spec003_timing import _n02_runner


class SlowRetry(FakeN02Adapters):
    def __init__(self, clock):
        super().__init__()
        self.clock = clock

    def commit(self, *, subject, policy, request_id, trace_id):
        if (
            N02LaneId(subject["lane_id"]) is N02LaneId.CONSENT_FAULT_RECOVERY
            and not self._fault_active
        ):
            self.clock.sleep(130)
        return super().commit(
            subject=subject, policy=policy, request_id=request_id, trace_id=trace_id
        )


def _rows(bundle, name):
    return [json.loads(line) for line in (bundle / name).read_text().splitlines() if line]


def test_slow_normal_retry_does_not_consume_the_restore_budget(tmp_path):
    clock = FakeClock()
    runner = _n02_runner(tmp_path, SlowRetry(clock), clock)
    run, judgement, bundle = runner.execute(runner.preflight("whyyou-local"))

    assert run.state.value == "COMPLETED"
    assert judgement.verdict.value == "PASS"
    assert not RestoreBlockStore(tmp_path).blocked("whyyou-local", "n02-consent-order")
    assert runner.timing_report()["environment_restore_seconds"] < 120
    assert verify_bundle(bundle)["bundle_status"] == "VERIFIED"


def test_a7_pass_seals_retry_consent_effects_and_causal_proof(tmp_path):
    runner = _n02_runner(tmp_path, FakeN02Adapters(), FakeClock())
    _run, judgement, bundle = runner.execute(runner.preflight("whyyou-local"))
    assert (
        next(a for a in judgement.assertion_results if a.assertion_id == "N02-A7").status.value
        == "PASS"
    )
    policy = json.loads((bundle / "policy-and-consent.json").read_text())
    assert policy["recovered_state"]["active_consent_count"] == 1
    assert policy["recovered_commit"]["request_id"]
    assert policy["safe_state"]["active_consent_count"] == 0
    for name in ("bypass-attempts.jsonl", "protected-effects.jsonl"):
        recovered = [
            row for row in _rows(bundle, name) if row.get("recovery_stage") == "AFTER_RETRY"
        ]
        assert {row["path_id"] for row in recovered} == {
            "DOCUMENT_ANALYSIS",
            "RECORDING",
            "AI_ASSESSMENT",
        }
    events = [
        row
        for row in _rows(bundle, "causal-events.jsonl")
        if row["lane_id"] == "CONSENT_FAULT_RECOVERY"
    ]
    assert any(row["kind"] == "CONSENT_COMMITTED" for row in events)
    assert {row["path_id"] for row in events if row["kind"] == "RESULT_CREATED"} == {
        "DOCUMENT_ANALYSIS",
        "RECORDING",
        "AI_ASSESSMENT",
    }
    assert verify_bundle(bundle)["bundle_status"] == "VERIFIED"


@pytest.mark.parametrize("missing", ["consent", "causal", "effects"])
def test_a7_pass_cannot_be_sealed_from_summary_flags_alone(tmp_path, monkeypatch, missing):
    append = EvidenceBundleWriter.append_jsonl
    write = EvidenceBundleWriter.write_json

    def omit_row(self, name, row, *args, **kwargs):
        if (
            missing == "causal"
            and name == "causal-events.jsonl"
            and row.get("lane_id") == "CONSENT_FAULT_RECOVERY"
        ):
            return None
        if (
            missing == "effects"
            and name == "protected-effects.jsonl"
            and row.get("recovery_stage") == "AFTER_RETRY"
        ):
            return None
        return append(self, name, row, *args, **kwargs)

    def omit_state(self, name, value, *args, **kwargs):
        if missing == "consent" and name == "policy-and-consent.json":
            value = {key: item for key, item in value.items() if key != "recovered_state"}
        return write(self, name, value, *args, **kwargs)

    monkeypatch.setattr(EvidenceBundleWriter, "append_jsonl", omit_row)
    monkeypatch.setattr(EvidenceBundleWriter, "write_json", omit_state)
    runner = _n02_runner(tmp_path, FakeN02Adapters(), FakeClock())
    with pytest.raises(N02ExecutionError, match="sealed bundle failed verification"):
        runner.execute(runner.preflight("whyyou-local"))
