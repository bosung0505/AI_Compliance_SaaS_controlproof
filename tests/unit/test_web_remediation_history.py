import hashlib
import json

import pytest

from engine.web import remediation


@pytest.fixture
def history(tmp_path, monkeypatch):
    records = []
    for index, source in enumerate(remediation.H02_RECORDS):
        record = dict(source)
        bundle = tmp_path / record["run_id"]
        bundle.mkdir()
        documents = {
            "manifest.json": {"bundle_digest": f"digest-{index}"},
            "run.json": {
                "run_id": record["run_id"], "scenario_id": "H-02",
                "execution_profile": "H02_CAPABILITY_SURFACE_V1", "state": "COMPLETED",
                "parent_run_id": remediation.H02_RECORDS[0]["run_id"] if index else None,
            },
            "judgement.json": {"verdict": record["verdict"]},
            "target.snapshot.json": {"git_commit_sha": record["whyyou_commit"]},
            "h02-reader-cases.json": [{
                "h02_contract_label": "answer_legacy", "response_status": 200,
                "before": {"stage_name": None, "reviews": 0},
                "after": {"stage_name": "최종합격" if index == 0 else None, "reviews": 0},
            }],
        }
        if index:
            documents["retest-link.json"] = {
                "parent_run_id": records[0]["run_id"], "parent_bundle_digest": "digest-0",
            }
        for name, value in documents.items():
            (bundle / name).write_text(json.dumps(value), encoding="utf-8")
        record["manifest_sha256"] = hashlib.sha256((bundle / "manifest.json").read_bytes()).hexdigest()
        records.append(record)
    monkeypatch.setattr(remediation, "H02_RECORDS", records)
    return tmp_path, lambda _: {"bundle_status": "VERIFIED"}


def test_explains_target_development_separately_from_test_results(history):
    root, verify = history
    result = remediation.h02_history(root, remediation.H02_RECORDS[1]["run_id"], verify)
    assert result["selected_stage"] == "retest"
    assert result["before_rows"][0] == {"label": "채용 단계", "before": "미지정", "after": "최종합격"}
    assert result["after_rows"][0]["after"] == "미지정"
    assert "WhyYou" in result["remedy"] and "조회 전용" in result["remedy"]
    assert "별도의 개발 작업" in result["role_note"]
    assert "로컬 개발 코드" in result["deployment_scope"]
    parent = remediation.h02_history(root, remediation.H02_RECORDS[0]["run_id"], verify)
    assert parent["selected_stage"] == "finding"


@pytest.mark.parametrize("damage", ["missing", "invalid", "manifest", "source", "lineage", "digest"])
def test_does_not_claim_completed_remediation_for_untrusted_history(history, damage):
    root, verify = history
    parent, child = [root / r["run_id"] for r in remediation.H02_RECORDS]
    if damage == "missing":
        (parent / "run.json").unlink()
    elif damage == "invalid":
        verify = lambda _: {"bundle_status": "INVALID"}
    else:
        name = {"manifest": "manifest.json", "source": "target.snapshot.json",
                "lineage": "retest-link.json", "digest": "retest-link.json"}[damage]
        path = child / name
        value = json.loads(path.read_text(encoding="utf-8"))
        key = {"manifest": "extra", "source": "git_commit_sha",
               "lineage": "parent_run_id", "digest": "parent_bundle_digest"}[damage]
        value[key] = "unreviewed"
        path.write_text(json.dumps(value), encoding="utf-8")
    assert remediation.h02_history(root, child.name, verify) is None


def test_does_not_apply_known_remedy_to_another_run(history):
    root, verify = history
    assert remediation.h02_history(root, "9532d923-7209-4af8-8bf8-c2a6d6f3a404", verify) is None
