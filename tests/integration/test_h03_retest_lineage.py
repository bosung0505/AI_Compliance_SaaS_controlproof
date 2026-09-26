import json
from dataclasses import replace
from uuid import uuid4

from engine.adapters.base import AdapterResult
from engine.evidence import verify_bundle
from engine.retest import assert_parent_unchanged, prepare_retest
from engine.runner import RunOrchestrator
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, FakeSeed, FakeState, make_adapters


class AlternateRoleSeed(FakeSeed):
    def seed(self, *, run_id, subject_ref):
        result = super().seed(run_id=run_id, subject_ref=subject_ref)
        return AdapterResult(
            result.ok,
            result.code,
            {**result.data, "subject_type": "synthetic_rehire_applicant"},
            result.detail,
        )


class AlternateBaselineState(FakeState):
    def _state(self):
        state = super()._state()
        if self.calls == 1:
            state["recruiting_stage_id"] = "stage-retest"
        return state


def test_fail_to_pass_retest_keeps_independent_queryable_bundles(tmp_path):
    scenario = load("scenarios/H-03.yaml")
    failing_adapters, _ = make_adapters(status_class="queued_only")
    parent_runner = RunOrchestrator(scenario, failing_adapters, tmp_path, clock=FakeClock())
    parent, parent_judgement, parent_bundle = parent_runner.execute(
        parent_runner.preflight("whyyou-local")
    )
    child_id = uuid4()
    passing_adapters, _ = make_adapters()
    child_runner = RunOrchestrator(scenario, passing_adapters, tmp_path, clock=FakeClock())
    readiness = child_runner.preflight("whyyou-local")
    _, parent_digest, records = prepare_retest(
        parent_bundle,
        child_run_id=child_id,
        child_target=readiness.target_snapshot,
        child_scenario_version=scenario.version,
        child_scenario_digest=scenario.snapshot().digest,
    )
    child, child_judgement, child_bundle = child_runner.execute(
        readiness,
        parent_run_id=parent.run_id,
        retest_records=records,
        run_id=child_id,
    )
    assert parent_judgement.verdict.value == "FAIL"
    assert child_judgement.verdict.value == "PASS"
    assert child.parent_run_id == parent.run_id
    assert verify_bundle(parent_bundle)["bundle_status"] == "VERIFIED"
    assert verify_bundle(child_bundle)["bundle_status"] == "VERIFIED"
    assert_parent_unchanged(parent_bundle, parent_digest)


def test_retest_diff_compares_actual_subject_role_and_initial_state(tmp_path):
    scenario = load("scenarios/H-03.yaml")
    parent_adapters, _ = make_adapters()
    parent_runner = RunOrchestrator(scenario, parent_adapters, tmp_path, clock=FakeClock())
    parent, _, parent_bundle = parent_runner.execute(parent_runner.preflight("whyyou-local"))
    parent_subject = json.loads((parent_bundle / "subjects.json").read_text(encoding="utf-8"))[0]
    assert parent_subject["subject_type"] == "synthetic_applicant"
    assert len(parent_subject["initial_state_digest"]) == 64
    assert "locators" in parent_subject
    assert "invitation_id" not in parent_subject

    child_adapters, _ = make_adapters()
    child_adapters = replace(
        child_adapters,
        seed=AlternateRoleSeed(),
        state=AlternateBaselineState(),
    )
    child_runner = RunOrchestrator(scenario, child_adapters, tmp_path, clock=FakeClock())
    readiness = child_runner.preflight("whyyou-local")
    child_id = uuid4()
    _, _, records = prepare_retest(
        parent_bundle,
        child_run_id=child_id,
        child_target=readiness.target_snapshot,
        child_scenario_version=scenario.version,
        child_scenario_digest=scenario.snapshot().digest,
    )

    _, _, child_bundle = child_runner.execute(
        readiness,
        parent_run_id=parent.run_id,
        retest_records=records,
        run_id=child_id,
    )
    diff = json.loads((child_bundle / "retest-diff.json").read_text(encoding="utf-8"))
    assert diff["subject"]["role"]["before"] == "synthetic_applicant"
    assert diff["subject"]["role"]["after"] == "synthetic_rehire_applicant"
    assert diff["subject"]["role"]["changed"] is True
    assert diff["subject"]["initial_state_digest"]["changed"] is True
