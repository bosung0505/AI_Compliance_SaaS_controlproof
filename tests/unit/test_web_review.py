"""Approved UX: concrete observations, sealed facts and rule/case separation."""

import hashlib

from engine.web.preflight import ReadinessStore
from engine.web.readmodel import WorkbenchReader, load_catalog
from engine.web.review import build_review
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
    assert review["title"] == "AI 점수의 인용 근거가 유효한가?"
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
