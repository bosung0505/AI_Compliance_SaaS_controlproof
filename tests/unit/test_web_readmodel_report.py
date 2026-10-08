"""T043 — one-screen report view (FR-025~029, SC-004). RED until T045.

V4 §8.7 (R1~R13) and §12.4 (C1~C9) items, the matrix §2 fixed sentence character for character, catalog counts, the
AI-score principle, test-only additions and limits. No "12개 검증 완료"-style wording.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.web import readmodel
from engine.web.preflight import ReadinessStore
from tests.fixtures import web_bundles as wb

MATRIX = Path("docs/product/ControlProof_MVP_Scenario_Coverage_Matrix.md")
ITEMS = [f"R{index}" for index in range(1, 14)] + [f"C{index}" for index in range(1, 10)]
FORBIDDEN = ("12개 검증 완료", "12개 PASS", "12개 시나리오 PASS", "12개 시나리오 검증 완료", "9개 중 8개 실행")
FIXTURE_NAMES = ("h03-report-v1", "spec004-report-v1")


@pytest.fixture(scope="module")
def catalog():
    return readmodel.load_catalog()


def _report(catalog, root, tmp_path, **kwargs):
    reader = readmodel.WorkbenchReader(catalog, root, readiness=ReadinessStore(tmp_path / "preflight"), **kwargs)
    return reader.report()


def _matrix_sentence():
    lines = [line[2:].strip() for line in MATRIX.read_text(encoding="utf-8").splitlines() if line.startswith("> ")]
    return " ".join(lines)


def _plain(report):
    developer = report.pop("developer")
    try:
        return json.dumps(report, ensure_ascii=False)
    finally:
        report["developer"] = developer


def test_all_22_items_present(catalog, tmp_path) -> None:
    report = _report(catalog, tmp_path / "runs", tmp_path)
    assert (report["schema_version"], report["view"]) == ("controlproof.web.v1", "report")
    assert report["items_present"] == {item: True for item in ITEMS}


def test_fixed_sentence_is_the_matrix_quote(catalog, tmp_path) -> None:
    report = _report(catalog, tmp_path / "runs", tmp_path)
    assert report["fixed_scope_sentence"] == _matrix_sentence()


def test_counts_and_status_rows_copy_the_catalog(catalog, tmp_path) -> None:
    report = _report(catalog, tmp_path / "runs", tmp_path)
    assert (report["counts"]["PASS"], report["counts"]["FAIL"], report["counts"]["NOT_RUN"]) == (4, 0, 4)
    assert report["counts"]["INCONCLUSIVE"]["by_reason"]["NO_TEST_TARGET"] == 3
    rows = {row["id"]: row for row in report["catalog_status"]}
    assert len(rows) == 12
    for entry in catalog["scenarios"]:
        assert rows[entry["id"]]["result"] == entry["official_status"]["result"]
    assert [row["id"] for row in report["no_test_target"]] == ["A-01", "A-02", "A-03"]
    assert all(row["badge"] == "reason_no_test_target" for row in report["no_test_target"])


def test_ai_score_principle_and_human_decision_location(catalog, tmp_path) -> None:
    report = _report(catalog, tmp_path / "runs", tmp_path)
    assert "참고 정보" in report["ai_score_principle"]["text"] and "사람" in report["ai_score_principle"]["text"]
    assert "H-03" in report["human_decision_location"]["text"]
    for item in ("ai_score_principle", "human_decision_location", "purpose_and_scope", "synthetic_data_notice"):
        assert report[item]["source"]


def test_test_only_additions_are_marked_as_test_means(catalog, tmp_path) -> None:
    report = _report(catalog, tmp_path / "runs", tmp_path)
    assert report["test_only_additions"]
    assert all(item["is_product_feature"] is False and item["source"] for item in report["test_only_additions"])


def test_limits_and_unverified_scope(catalog, tmp_path) -> None:
    report = _report(catalog, tmp_path / "runs", tmp_path)
    limitations = " ".join(item["text"] for item in report["limitations"])
    for phrase in ("LOCAL_EMULATED", "AWS", "NOT_RUN", "합성", "외부 AI", "고정 모델"):
        assert phrase in limitations, phrase
    assert report["other_pc_reproduction"]["status"] == "NOT_VERIFIED"
    assert "보증하지" in report["legal_notice"]["text"]
    unverified = " ".join(report["unverified_scope"])
    for scenario_id in ("H-01", "H-02", "N-01", "N-03", "A-01", "AWS"):
        assert scenario_id in unverified
    assert report["claim_scope"] == "EXECUTED_SCENARIO_AND_EVIDENCE_ONLY"


def test_fixed_model_names_only_in_developer_details(catalog, tmp_path) -> None:
    report = _report(catalog, tmp_path / "runs", tmp_path)
    plain = _plain(report)
    for name in FIXTURE_NAMES:
        assert name not in plain
        assert name in json.dumps(report["developer"])


def test_failures_lineages_and_expectations(catalog, tmp_path) -> None:
    report = _report(catalog, tmp_path / "runs", tmp_path)
    failures = {item["scenario_id"] for item in report["major_failures"]}
    assert {"E-01", "H-03", "E-03"} <= failures
    assert all(item["impact"] for item in report["major_failures"])
    assert {item["scenario_id"] for item in report["lineages"]} == failures
    expectations = {item["scenario_id"] for item in report["scenario_expectations"]}
    assert expectations == {"H-03", "E-03", "N-02", "E-01", "E-02"}
    assert any(item["scenario_id"] == "N-02" and item["missing"] for item in report["evidence_summary"])


def test_forbidden_phrases_absent(catalog, tmp_path) -> None:
    text = json.dumps(_report(catalog, tmp_path / "runs", tmp_path), ensure_ascii=False)
    for phrase in FORBIDDEN:
        assert phrase not in text


def test_demo_report_never_mixes_into_actual(catalog, tmp_path) -> None:
    actual_root, demo_root = tmp_path / "runs", tmp_path / "demo"
    wb.spec004_run(demo_root, "E-02")
    wb.spec004_run(demo_root, "E-02")
    actual = _report(catalog, actual_root, tmp_path)
    demo = _report(catalog, demo_root, tmp_path, origin="DEMO")
    assert (actual["data_origin"], demo["data_origin"], demo["demo"]) == ("ACTUAL", "DEMO", True)
    assert actual["counts"] == demo["counts"]
    summary = {item["scenario_id"]: item for item in actual["evidence_summary"]}
    demo_summary = {item["scenario_id"]: item for item in demo["evidence_summary"]}
    assert summary["E-02"]["records_on_this_pc"] == 0
    assert demo_summary["E-02"]["records_on_this_pc"] == 2
