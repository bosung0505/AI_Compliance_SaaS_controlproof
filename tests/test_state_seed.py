from seeds.state_seed import (
    AXES,
    ApplicantSpec,
    build_fixture,
    check_invariants,
    upsert_sql,
)


def three_applicants():
    return [
        ApplicantSpec(ref="A1", scored_axes=AXES[:3], axis_score=81),
        ApplicantSpec(ref="A2", scored_axes=AXES[:4], axis_score=64),
        ApplicantSpec(ref="A3", scored_axes=AXES[:2], axis_score=55),
    ]


def test_fixture_shape():
    fx = build_fixture("run-1", three_applicants())
    assert fx.count("company") == 1
    assert fx.count("invitation") == 3
    assert fx.count("interview_turn") == 18          # 지원자당 6턴
    assert fx.count("transcript_segment") == 18
    assert fx.count("report") == 3
    assert fx.count("evidence") == 9                 # 지원자당 3개


def test_idempotent_ids():
    """같은 라벨이면 같은 UUID. 로컬 스택이 부팅마다 시드를 다시 돌려도 안전해야 한다."""
    a = build_fixture("run-1", three_applicants())
    b = build_fixture("run-1", three_applicants())
    assert a.correlation == b.correlation
    assert [r["invitation_id"] for r in a.of("invitation")] == \
           [r["invitation_id"] for r in b.of("invitation")]


def test_different_label_isolates():
    a = build_fixture("run-1", three_applicants())
    b = build_fixture("run-2", three_applicants())
    assert a.correlation["company_id"] != b.correlation["company_id"]


def test_invariants_hold():
    fx = build_fixture("run-1", three_applicants())
    assert check_invariants(fx) == []


def test_null_axis_has_no_citation():
    """점수 null 인 축은 인용이 비어야 한다. E-01 의 정상 기준선."""
    fx = build_fixture("run-1", [ApplicantSpec(ref="A1", scored_axes=("correctness",))])
    item = fx.of("report_item")[0]
    assert item["axis_assessments"]["correctness"]["quoted_evidence_ids"]
    for axis in AXES[1:]:
        entry = item["axis_assessments"][axis]
        assert entry["score"] is None
        assert entry["quoted_evidence_ids"] == []


def test_scored_axis_cites_existing_evidence():
    fx = build_fixture("run-1", three_applicants())
    existing = {str(e["evidence_id"]) for e in fx.of("evidence")}
    for item in fx.of("report_item"):
        for data in item["axis_assessments"].values():
            for ev in data["quoted_evidence_ids"]:
                assert ev in existing


def test_dangling_citation_is_detected():
    """E-01 의 결함 조건을 만들면 불변식 점검이 잡아야 한다."""
    fx = build_fixture("run-1", three_applicants())
    item = fx.of("report_item")[0]
    item["axis_assessments"]["correctness"]["quoted_evidence_ids"] = ["00000000-0000-0000-0000-000000000000"]
    problems = check_invariants(fx)
    assert any("존재하지 않는 Evidence" in p for p in problems)


def test_evidence_within_recording_duration():
    fx = build_fixture("run-1", three_applicants())
    limit = fx.of("recording_asset")[0]["duration_ms"]
    for ev in fx.of("evidence"):
        assert ev["video_end_ms"] <= limit


def test_report_freezes_scoring_inputs():
    """E-02 가 시험할 대상. 리포트에 기준이 동결돼 있어야 한다."""
    fx = build_fixture("run-1", three_applicants())
    inputs = fx.of("report")[0]["scoring_inputs"]
    assert inputs["competency_model_version_id"] == fx.correlation["competency_model_version_id"]
    assert set(inputs["axis_weights"]) == set(AXES)


def test_invitation_ready_for_review():
    """H 계열 전제: 지원 건은 completed, 단계는 검토, 리포트는 ready."""
    fx = build_fixture("run-1", three_applicants())
    assert all(r["status"] == "completed" for r in fx.of("invitation"))
    assert fx.of("recruiting_stage")[0]["name"] == "검토"
    assert all(r["status"] == "ready" for r in fx.of("report"))
    assert all(s["state"] == "reviewable" for s in fx.of("interview_session"))


def test_correlation_anchors_present():
    """실행 ID 상관관계 연결(6.2 1단계)에 쓸 앵커."""
    fx = build_fixture("run-1", three_applicants())
    assert "invitation_id:A1" in fx.correlation
    assert "report_id:A3" in fx.correlation
    assert "run-1" in fx.of("invitation")[0]["applicant_email_normalized"]


def test_upsert_sql_uses_conflict_target():
    fx = build_fixture("run-1", three_applicants())
    sql, params = upsert_sql("invitation", fx.of("invitation")[0])
    assert "INSERT INTO invitations" in sql
    assert "ON CONFLICT (company_id, invitation_id) DO UPDATE" in sql
    assert params["status"] == "completed"
