from engine.h01_actual import CASE_LABELS, PATH_LABELS
from engine.web.h01_review import conditions
from engine.web.review import test_plan as make_plan


def test_h01_shared_review_explains_who_response_and_actual_state():
    rows = conditions(
        [
            {
                "assertion_id": "H01-A4",
                "status": "FAIL",
                "evidence_refs": [],
                "actual": {
                    "paths": [
                        {
                            "path": "BATCH_ACCEPT",
                            "status": "FAIL",
                            "observation": "실제 채용 단계가 변경됨",
                            "response": "ACCEPTED",
                            "http_status": None,
                            "before": {
                                "pipeline_row_version": 1,
                                "recruiting_stage_id": "old",
                                "reviews": [],
                                "report_status": "ready",
                            },
                            "after": {
                                "pipeline_row_version": 2,
                                "recruiting_stage_id": "new",
                                "reviews": [],
                                "audits": [],
                            },
                        }
                    ]
                },
            }
        ],
        lambda refs: [],
    )
    assert len(rows) == 1 and rows[0]["title"] == CASE_LABELS["SYSTEM_BOUNDARY"]
    assert (
        rows[0]["group"] == "2. " + PATH_LABELS["BATCH_ACCEPT"] and rows[0]["rule_status"] == "FAIL"
    )
    facts = {r["label"]: r["value"] for r in rows[0]["proof_rows"]}
    assert facts["채용 단계"] == "변경됨" and facts["채용 상태 변경 버전"] == "1 → 2"
    assert "제품 감사 기록 없음" in facts["실제 감사 기록"]
    plan = make_plan("H-01", None)
    assert len(plan["conditions"]) == 6 and len(plan["stages"]) == 3
