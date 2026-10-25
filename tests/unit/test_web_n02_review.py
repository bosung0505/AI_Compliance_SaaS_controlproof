from engine.web.review import build_review
from engine.web.review import test_plan as make_plan


def review(tmp_path, number, actual, status="PASS"):
    return build_review(
        "N-02",
        {},
        [
            {
                "assertion_id": f"N02-A{number}",
                "status": status,
                "actual": actual,
                "detail": "원본 기술 문장",
            }
        ],
        tmp_path,
        [],
    )


def test_n02_missing_facts_never_turn_pass_badge_into_observation(tmp_path):
    result = review(tmp_path, 5, None)
    assert "기록" in result["conditions"][0]["observed"]
    assert "세 경로" not in result["summary"]
    assert result["conditions"][0]["title"] == "동의 저장 후 문서 분석·녹화·AI 평가 진행"


def test_n02_bypass_explains_actual_refusal_and_effects(tmp_path):
    result = review(
        tmp_path,
        4,
        {
            "response_class": "SUBMITTED",
            "new_effect_ids": [],
            "refusal_receipt_ids": ["receipt"],
            "start_receipt_ids": [],
            "source_status": "ABSENT",
        },
    )
    row = result["conditions"][0]
    assert "거부" in row["observed"] and "동의하지 않은" in row["setup"]
    assert row["proof_rows"] and row["comparison"] == []
    assert "SUBMITTED" not in row["observed"]


def test_n02_failed_or_unproven_order_is_not_presented_as_completed(tmp_path):
    result = review(
        tmp_path,
        5,
        {"policy_identity_matches": True, "event_count": 10, "edge_count": 9},
        "INCONCLUSIVE",
    )
    assert "확인하지 못" in result["conditions"][0]["observed"]
    assert "모두 정상" not in result["summary"]


def test_n02_recovery_summary_uses_saved_counts_and_order(tmp_path):
    result = review(
        tmp_path,
        7,
        {
            "restore_status": "SUCCEEDED",
            "logical_consent_count": 1,
            "consent_completed_event_count": 1,
            "normal_retry_succeeded": True,
            "processing_order_proven": True,
            "marker_removed": True,
        },
    )
    row = result["conditions"][0]
    assert "한 번" in row["observed"] and "재시도" in row["setup"]
    assert "확인하세요" not in result["summary"]


def test_n02_plan_explains_consent_fault_and_retry():
    plan = make_plan("N-02", {})
    assert len(plan["stages"]) == 4
    assert "동의 저장 장애" in " ".join(plan["conditions"])


def test_n02_observed_leaks_are_explicit_instead_of_generic_uncertainty(tmp_path):
    row = review(tmp_path, 6, {
        "partial_consent": True, "leaked_effect_ids": ["effect"],
    }, "FAIL")["conditions"][0]
    assert "후속 처리 기록이 남았습니다" in row["observed"]
    assert "확인하지 못" not in row["observed"]
    retry = review(tmp_path, 7, {
        "logical_consent_count": 2, "consent_completed_event_count": 2,
    }, "FAIL")["conditions"][0]
    assert "중복됐습니다" in retry["observed"]
