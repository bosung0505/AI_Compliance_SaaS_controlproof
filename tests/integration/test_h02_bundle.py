import json
from types import SimpleNamespace

import pytest

from engine.adapters.whyyou.h02_live import FIXTURE_DIGEST, FIXTURE_ID, h02_cases
from engine.evidence import verify_bundle
from engine.executors.h02 import H02Executor
from engine.h02 import Inventory, SourceFile, SourceRef, Surface, source_digest
from engine.models import ScenarioReadiness
from engine.scenario import load
from tests.fixtures.n02_review_bundle import reseal_file
from tests.fixtures.spec002 import environment_snapshot
from tests.unit.test_h01_actual import SETTINGS


@pytest.fixture
def bundle(tmp_path, monkeypatch, target_snapshot):
    settings = SimpleNamespace(
        **vars(SETTINGS),
        model_fixture_id=FIXTURE_ID,
        model_fixture_digest=FIXTURE_DIGEST,
        whyyou_repo_path=tmp_path,
    )
    target = target_snapshot.model_copy(
        update={"model_fixture_id": FIXTURE_ID, "model_fixture_digest": FIXTURE_DIGEST}
    )
    target = type(target).model_validate(target.model_dump(exclude={"target_version"}))
    environment = environment_snapshot(
        model_fixture_id=FIXTURE_ID,
        model_fixture_digest=FIXTURE_DIGEST,
        whyyou_commit={"commit_sha": target.git_commit_sha, "dirty": False},
    )
    source = SourceFile(path="backend/src/interview_evidence/a.py", sha256="a" * 64)
    inventory = Inventory(
        source_head=target.git_commit_sha,
        source_branch="validation/test",
        source_dirty=False,
        sources=(source,),
        source_tree_digest=source_digest((source,)),
        issues=(),
        import_closure=(source.path,),
        surfaces=(
            Surface(
                id="DISPATCH_ANCHOR:main",
                kind="DISPATCH_ANCHOR",
                name="main",
                target="a.main",
                refs=(SourceRef(**source.model_dump(), line=1, end_line=2),),
            ),
        ),
    )

    class FakeLive:
        def __init__(self, settings, adapters, run_id):
            self.cases = h02_cases(run_id, settings)
            self.resources = set()
            self.preparations = []

        def runtime(self):
            return {}

        def prepare(self, *args):
            raise RuntimeError("synthetic preparation unavailable")

        def cleanup(self):
            return {"status": "SUCCEEDED", "owned_residue_counts": {"invitations": 0}}

    monkeypatch.setattr("engine.executors.h02.H02Live", FakeLive)
    monkeypatch.setattr("engine.executors.h02.collect_inventory", lambda _: inventory)
    monkeypatch.setattr(
        "engine.adapters.whyyou.h02_review.review_mode", lambda _: "read-only-pipeline-reader"
    )
    monkeypatch.setattr(
        "engine.adapters.whyyou.h02_review.review_record",
        lambda _: {
            "mode": "read-only-pipeline-reader",
            "effects": {"DISPATCH_ANCHOR:main": "AUXILIARY_WRITE"},
        },
    )
    adapters = SimpleNamespace(
        spec004_seed=SimpleNamespace(settings=settings),
        environment=SimpleNamespace(capture_environment=lambda: environment),
    )
    readiness = ScenarioReadiness(
        scenario_id="H-02",
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
    run, judgment, directory = H02Executor(load("scenarios/H-02.yaml"), adapters, tmp_path).execute(
        readiness
    )
    assert judgment.verdict == "INCONCLUSIVE"
    assert (tmp_path / "progress" / f"{run.run_id}.json").is_file()
    return directory


def test_incomplete_actual_is_sealed_without_fabricated_pass(bundle):
    result = verify_bundle(bundle)
    assert result["bundle_status"] == "VERIFIED" and result["checked_files"] == 17


@pytest.mark.parametrize(
    "name",
    ["h02-facts.json", "h02-review.json", "h02-runtime.json", "subjects.json", "recovery.json"],
)
def test_resealed_fabricated_h02_evidence_is_invalid(bundle, name):
    data = json.loads((bundle / name).read_text(encoding="utf-8"))
    if name == "h02-facts.json":
        data["runtime_verified"] = True
    elif name == "h02-review.json":
        data[0]["effect"] = "HIRING_DECISION_WRITE"
    elif name == "h02-runtime.json":
        data["routes"] = ["POST /assistant/finalize"]
    elif name == "subjects.json":
        data[0]["subject"]["invitation_id"] = data[1]["subject"]["invitation_id"]
    else:
        data["owned_residue_counts"]["invitations"] = 1
    reseal_file(bundle, name, data)
    assert verify_bundle(bundle)["bundle_status"] == "INVALID"
