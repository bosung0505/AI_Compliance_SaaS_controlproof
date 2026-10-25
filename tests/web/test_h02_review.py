import json

import pytest

from engine.h02 import encode_contract_labels
from engine.web.h02_review import READERS, conditions, result_sentences
from engine.web.review import test_plan as make_plan


def test_h02_explains_reader_change_and_human_score_independence(tmp_path):
    readers = []
    normalized = []
    for index, name in enumerate(READERS):
        before = {
            "recruiting_stage_id": None,
            "stage_name": None,
            "pipeline_row_version": 1,
            "reviews": 0,
        }
        after = (
            {
                **before,
                "recruiting_stage_id": "accepted",
                "stage_name": "최종합격",
                "pipeline_row_version": 2,
            }
            if index == 1
            else before
        )
        readers.append({"name": name, "before": before, "after": after, "response_status": 200})
        normalized.append(
            {"name": name, "before": before, "after": after, "state_changed": index == 1}
        )
    humans = [
        {
            "name": name,
            "before": {"overall_score": score},
            "after": {"stage_name": stage, "reviews": 1},
        }
        for name, score, stage in [("human_low", 35, "최종합격"), ("human_high", 90, "불합격")]
    ]
    docs = {
        "h02-facts.json": {
            "reader_cases": normalized,
            "human_control": {
                "low_accepted": True,
                "high_rejected": True,
                "same_position": True,
                "same_version": True,
                "model_receipts_verified": True,
            },
        },
        "h02-reader-cases.json": readers,
        "h02-human-controls.json": humans,
    }
    for name, value in docs.items():
        (tmp_path / name).write_text(
            json.dumps(encode_contract_labels(value), ensure_ascii=False), encoding="utf-8"
        )
    rules = [
        {"assertion_id": f"H02-A{i}", "status": "FAIL" if i == 2 else "PASS", "evidence_refs": []}
        for i in range(1, 7)
    ]
    rows = conditions(tmp_path, rules, lambda _: [])
    assert len(rows) == 10
    changed = next(r for r in rows if r["id"] == "reader-answer_legacy")
    assert "미지정에서 최종합격" in changed["observed"]
    assert any(p["value"] == "1 → 2" for p in changed["proof_rows"])
    assert "35점" in next(r for r in rows if r["id"] == "human_low")["observed"]
    assert "90점" in next(r for r in rows if r["id"] == "human_high")["observed"]
    assert "1개에서" in result_sentences(rows)[0]
    assert len(make_plan("H-02", None)["stages"]) == 3


def test_missing_h02_records_do_not_look_successful(tmp_path):
    rows = conditions(tmp_path, [], lambda _: [])
    assert not any(r["recorded"] for r in rows)
    assert "0개에 전후 상태 기록" in result_sentences(rows)[0]


@pytest.mark.parametrize(
    "effect,verified,expected",
    [
        ("AUXILIARY_WRITE", True, "명령 경로는 발견되지 않았습니다"),
        ("HIRING_DECISION_WRITE", True, "명령 경로가 1개 발견됐습니다"),
        ("UNKNOWN", True, "부재를 확인하지 못했습니다"),
        ("AUXILIARY_WRITE", False, "부재를 확인하지 못했습니다"),
    ],
)
def test_worker_observation_answers_command_presence_without_inventing_execution(
    tmp_path, effect, verified, expected
):
    review = [{"id": "worker", "kind": "WORKER_HANDLER", "effect": effect,
               "source_verified": True}]
    for name, value in {
        "h02-review.json": review,
        "h02-facts.json": {"worker_effects_verified": verified, "inventory_ids": ["worker"]},
    }.items():
        (tmp_path / name).write_text(json.dumps(value), encoding="utf-8")
    row = next(r for r in conditions(tmp_path, [], lambda _: []) if r["id"] == "H02-A3")
    assert expected in row["observed"]
    assert "정상 처리했습니다" not in row["observed"]
    assert "전수 실행은 아님" in str(row["proof_rows"])


def test_classification_and_cleanup_report_missing_parts_separately(tmp_path):
    (tmp_path / "h02-review.json").write_text(json.dumps([
        {"id": "one", "effect": "AUXILIARY_WRITE", "source_verified": False}
    ]), encoding="utf-8")
    (tmp_path / "h02-facts.json").write_text(json.dumps({
        "inventory_ids": ["one", "missing"], "cleanup_verified": True,
        "source_identity_verified": False,
    }), encoding="utf-8")
    rows = {r["id"]: r for r in conditions(tmp_path, [], lambda _: [])}
    assert "소스 근거 미확인 1개" in rows["H02-A4"]["observed"]
    assert "검토 완료 여부는 확인하지 못" in rows["H02-A4"]["observed"]
    assert "잔여행은 0건" in rows["H02-A6"]["observed"]
    assert "소스가 실행 중 유지됐는지는 확인하지 못" in rows["H02-A6"]["observed"]
