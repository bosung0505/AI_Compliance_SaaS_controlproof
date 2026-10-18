"""Approved UX: concrete observations, sealed facts and rule/case separation."""

import hashlib
import re
from pathlib import Path

from engine.web.preflight import ReadinessStore
from engine.web.readmodel import WorkbenchReader, load_catalog
from engine.web.review import TITLES, build_review
from tests.fixtures import web_bundles as wb


def reader(root, tmp_path):
    return WorkbenchReader(load_catalog(), root, readiness=ReadinessStore(tmp_path / "ready"))


def digest(path):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob("*") if p.is_file()}


def test_e01_exposes_seven_observations_with_four_original_rules(tmp_path):
    root = tmp_path / "runs"
    built = wb.spec004_run(root, "E-01", removal_indicator="score_null")
    before = digest(built.bundle)
    view = reader(root, tmp_path).run(built.run_id)
    review = view["review"]
    assert review["title"] == "유효한 인용 근거 없는 점수 저장·노출 차단"
    assert len(review["conditions"]) == 7
    assert review["rule_count"] == 4
    assert len({r["assertion_id"] for r in review["conditions"]}) == 4
    assert all(r["recorded"] and r["observed"] and r["sources"] for r in review["conditions"])
    assert {r["facts"].get("outcome") for r in review["conditions"][:5]} == {"EMPTIED", "STORED_VALID"}
    assert before == digest(built.bundle)


def test_invalid_bundle_never_produces_a_review(tmp_path):
    root = tmp_path / "runs"
    built = wb.spec004_run(root, "E-01")
    wb.tampered(built)
    view = reader(root, tmp_path).run(built.run_id)
    assert view["review"] is None and view["verdict"] is None


def test_failed_condition_is_not_replaced_by_expected_behavior(tmp_path):
    root = tmp_path / "runs"
    built = wb.spec004_run(root, "E-01")
    view = reader(root, tmp_path).run(built.run_id)
    removed = next(r for r in view["review"]["conditions"] if r["id"] == "removed")
    assert removed["rule_status"] == "FAIL"
    assert "드러나지" in removed["observed"]


def test_scenario_has_recent_result_and_human_test_conditions(tmp_path):
    root = tmp_path / "runs"
    built = wb.spec004_run(root, "E-01")
    view = reader(root, tmp_path).scenario("E-01")
    assert view["latest_run"]["run_id"] == built.run_id
    assert len(view["test_plan"]["conditions"]) == 7
    assert "다른 지원자" in " ".join(view["test_plan"]["conditions"])


def test_evidence_keeps_selected_condition_context(tmp_path):
    root = tmp_path / "runs"
    built = wb.spec004_run(root, "E-01")
    r = reader(root, tmp_path)
    row = r.run(built.run_id)["review"]["conditions"][0]
    view = r.evidence(built.run_id, row["sources"][0]["ref"], condition_id=row["id"])
    assert view["context"]["condition"]["id"] == row["id"]
    assert view["scenario_id"] == "E-01"
    assert '"mode": "EMPTY"' in view["excerpt"]
    assert "OTHER_APPLICANT" not in view["excerpt"]


def test_pass_status_without_case_records_does_not_invent_observations(tmp_path):
    assertions = [{"assertion_id": f"E01-A{i}", "status": "PASS", "actual": None} for i in range(1, 5)]
    review = build_review("E-01", {"version": "1.0.0"}, assertions, tmp_path, [])
    assert review["passed_rule_count"] == 4
    assert all(not row["recorded"] for row in review["conditions"])
    assert all("기록 없음" in row["observed"] for row in review["conditions"])
    assert "기록" in review["summary"] and "확인하세요" not in review["summary"]
    assert "모두 보류됐습니다" not in review["summary"]


def test_all_twelve_titles_match_the_original_v4_design():
    original = Path("docs/product/ControlProof_WhyYou_2주_MVP_기능범위_v4.md").read_text(encoding="utf-8")
    headings = re.findall(r"^### 10\.\d+ ([NHEA]-0[123])\. (.+)$", original, re.MULTILINE)
    expected = {key: title.replace("`", "").removesuffix(" — 판정 불가") for key, title in headings}
    assert len(expected) == 12
    assert TITLES == expected


def test_e01_summary_and_comparison_describe_the_recorded_validation_path(tmp_path):
    built = wb.spec004_run(tmp_path / "runs", "E-01", removal_indicator="score_null")
    view = reader(tmp_path / "runs", tmp_path).run(built.run_id)
    review = view["review"]
    assert "확인하세요" not in review["summary"]
    assert "보류" in review["summary"] and "복원" in review["summary"]
    assert "고정" in review["process"] and "응답 검증" in review["process"]
    assert "DB" not in review["summary"] and "직접" not in review["summary"]
    assert not any(source["ref"] == "file:storage-probe.json" for condition in review["conditions"] for source in condition["sources"])
    assert any(item["ref"] == "file:storage-probe.json" for item in view["evidence"])
    row = next(row for row in review["conditions"] if row["id"] == "other-applicant")
    assert "지원자" in row["setup"] and "WhyYou" in row["observed"]
    assert row["comparison"] and any(item["label"] == "점수" for item in row["comparison"])
    assert "점수·인용 비움" not in row["observed"]


def test_failed_removal_is_reported_in_the_summary(tmp_path):
    built = wb.spec004_run(tmp_path / "runs", "E-01")
    review = reader(tmp_path / "runs", tmp_path).run(built.run_id)["review"]
    assert "드러나지" in review["summary"] or "알리지" in review["summary"]
