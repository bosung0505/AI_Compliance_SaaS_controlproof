import json
from types import SimpleNamespace

import pytest

from engine.adapters.whyyou.h01_live import FIXTURE_DIGEST, FIXTURE_ID, plan_cases
from engine.evidence import verify_bundle
from engine.executors.h01 import H01Executor
from engine.models import ScenarioReadiness
from engine.scenario import load
from tests.fixtures.n02_review_bundle import reseal_file
from tests.fixtures.spec002 import environment_snapshot
from tests.unit.test_h01_actual import SETTINGS
from tests.unit.test_h01_preparation import state


@pytest.fixture
def bundle(tmp_path, monkeypatch, target_snapshot):
    settings = SimpleNamespace(
        **vars(SETTINGS), model_fixture_id=FIXTURE_ID, model_fixture_digest=FIXTURE_DIGEST
    )
    target = target_snapshot.model_copy(
        update={"model_fixture_id": FIXTURE_ID, "model_fixture_digest": FIXTURE_DIGEST}
    )
    target = type(target).model_validate(target.model_dump(exclude={"target_version"}))
    env = environment_snapshot(
        model_fixture_id=FIXTURE_ID,
        model_fixture_digest=FIXTURE_DIGEST,
        whyyou_commit={"commit_sha": target.git_commit_sha, "dirty": False},
    )
    adapters = SimpleNamespace(
        spec004_seed=SimpleNamespace(settings=settings),
        environment=SimpleNamespace(capture_environment=lambda: env),
    )

    class FakeLive:
        def __init__(self, settings, adapters, run_id):
            self.cases = plan_cases(run_id, settings)
            self.preparations = []
            self.model_receipts = []

        def prepare(self, path, subject, lane):
            return state(subject)

        def identity(self, subject, lane):
            return True

        def observe(self, subject):
            return state(subject)

        def attempt(self, path, subject, lane, before):
            return {
                "response": "DENIED",
                "request_observed": True,
                "http_status": 403,
                "case": subject.case.value,
                "request_id": str(subject.request_id),
                "run_id": str(subject.run_id),
            }

        def cleanup(self):
            return {
                "status": "SUCCEEDED",
                "owned_residue_counts": {
                    k: 0
                    for k in (
                        "invitations",
                        "reports",
                        "human_reviews",
                        "audit_events",
                        "command_idempotency",
                        "outbox_events",
                        "processed_messages",
                        "assistant_retrieval_documents",
                    )
                },
            }

    monkeypatch.setattr("engine.executors.h01.H01Live", FakeLive)
    readiness = ScenarioReadiness(
        scenario_id="H-01",
        scenario_version="1.0.0",
        target_id="whyyou-local",
        implementation_status="IMPLEMENTED",
        status="READY",
        checks=(),
        target_snapshot=target,
        target_version=target.target_version,
        model_fixture_id=FIXTURE_ID,
        model_fixture_digest=FIXTURE_DIGEST,
    )
    run, judgement, directory = H01Executor(
        load("scenarios/H-01.yaml"), adapters, tmp_path
    ).execute(readiness)
    assert judgement.verdict == "FAIL"  # denied company control is a factual control failure
    assert (tmp_path / "progress" / f"{run.run_id}.json").is_file()
    return directory


def test_sealed_failure_is_verifiable_and_not_promoted_to_pass(bundle):
    result = verify_bundle(bundle)
    assert result["bundle_status"] == "VERIFIED" and result["checked_files"] == 15


@pytest.mark.parametrize(
    "mutation", ["assessment", "case_ownership", "request", "cleanup", "model"]
)
def test_resealed_fabricated_facts_fail_semantic_verification(bundle, mutation):
    name = {
        "assessment": "assertions.json",
        "case_ownership": "h01-cases.json",
        "request": "h01-requests.json",
        "cleanup": "recovery.json",
        "model": "h01-model-emissions.json",
    }[mutation]
    data = json.loads((bundle / name).read_text(encoding="utf-8"))
    if mutation == "assessment":
        data[0]["status"] = "PASS"
    elif mutation == "case_ownership":
        data[0]["subject"]["run_id"] = data[1]["subject"]["run_id"]
    elif mutation == "request":
        data[0]["response"] = "ACCEPTED"
    elif mutation == "cleanup":
        data["owned_residue_counts"]["invitations"] = 1
    else:
        data.append({"emitted_command": True})
    reseal_file(bundle, name, data)
    assert verify_bundle(bundle)["bundle_status"] == "INVALID"
