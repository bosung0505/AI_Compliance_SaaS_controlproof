"""Stage3 coverage and GET navigation contracts; synthetic cases are not actual Runs."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from engine.web.overview import FilterInvalid, coverage, filter_groups, parse_filters, projection
from engine.web.readmodel import WorkbenchReader, load_catalog
from engine.web.preflight import ReadinessStore
from tests.contract.test_platform_public_pages import Markup, page, site  # noqa: F401

CASES = json.loads((Path(__file__).parents[2] / "specs/010-platform-ui-integration/contracts/coverage-cases.json").read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", [c for c in CASES if c["case_type"] == "aggregate"], ids=lambda c: c["case_id"])
def test_prepared_aggregate_cases(case):
    rows = copy.deepcopy(case["input"]["scenarios"])
    for row in rows:
        row["ui"] = {"current_scope": {"partial": row.pop("partial")}}
    result = coverage(rows)
    expected = case["expected"]
    assert result["total"] == expected["total"]
    assert result["counts"] == expected["coverage_counts"]
    assert result["partial_count"] == expected["partial_count"]
    assert result["segments"] == expected["segments"]
    groups = [{"control": c, "scenarios": [r for r in rows if r["control"] == c]} for c in "NHAE" if any(r["control"] == c for r in rows)]
    for group in projection(groups)["groups"]:
        actual = group["ui"]["coverage"]
        assert actual["targeted_progress"] == expected["groups"][group["control"]]["targeted_progress"]
        assert actual["partial_count"] == expected["groups"][group["control"]]["partial_count"]


def test_coverage_uses_treatment_not_verdict_and_never_counts_partial_twice():
    rows = copy.deepcopy(CASES[0]["input"]["scenarios"])
    for row in rows:
        row["ui"] = {"current_scope": {"partial": row.pop("partial")}}
    actual = coverage(rows)
    assert actual["total"] == 12 and actual["partial_count"] == 1
    assert actual["counts"] == {"EXECUTED": 9, "NOT_RUN": 0, "NO_TEST_TARGET": 3}
    assert [s["draw"] for s in actual["segments"]] == [True, False, True]
    rows[0]["official"]["result"] = "FAIL"
    rows[1]["official"]["result"] = "INCONCLUSIVE"
    assert coverage(rows) == actual
    assert coverage([])["counts"] == {"EXECUTED": 0, "NOT_RUN": 0, "NO_TEST_TARGET": 0}
    assert not any(s["draw"] for s in coverage([])["segments"])
    with pytest.raises(ValueError, match="TARGET_TREATMENT_CONFLICT"):
        coverage([{**rows[0], "target_exists": False}])


def test_additive_projection_preserves_catalog_order_and_real_scope(tmp_path):
    catalog = load_catalog()
    data = WorkbenchReader(catalog, tmp_path / "runs", readiness=ReadinessStore(tmp_path / "state")).workbench()
    assert [g["control"] for g in data["groups"]] == [c["control"] for c in catalog["controls"]]
    assert data["ui"]["coverage"]["partial_count"] == 1
    groups = data["ui"]["groups"]
    assert [g["control"] for g in groups] == list("NHAE")
    assert [row["id"] for g in groups for row in g["scenarios"]] == [f"{c}-0{i}" for c in "NHAE" for i in range(1, 4)]
    assert groups[2]["ui"]["coverage"]["targeted_progress"] is None
    scope = groups[0]["scenarios"][2]["ui"]["current_scope"]
    assert scope["source"] == "scenario_file" and scope["source_ref"] == "scenarios/N-03.yaml"
    assert scope["applicable_assertion_ids"] == ["N03-A1", "N03-A2", "N03-A3"]
    assert [i["id"] for i in scope["unverified_items"]] == ["N03-U1", "N03-U2", "N03-U3"]
    assert scope["limitations"][0]["id"] == "N03-L1"


@pytest.mark.parametrize("query", [
    "q=%GG", "q=%FF", "q=%", "q=x&q=x", "q=x&Q=x", "control=ALL", "control=n", "status=INVALID",
    "treatment=PASS", "run_root=x", "q=%00", "q=%0A", "q=%7F", "q=" + "가" * 201,
])
def test_invalid_queries_fail_closed(query):
    with pytest.raises(FilterInvalid):
        parse_filters(query)


def test_filter_decode_once_unicode_and_canonical_query():
    filters = parse_filters("treatment=EXECUTED&status=ALL&control=N&q=++%ED%95%9C%EA%B8%80++")
    assert filters["q"] == "한글"
    assert filters["query"] == "q=%ED%95%9C%EA%B8%80&control=N&treatment=EXECUTED"
    assert parse_filters("q=%252F")["q"] == "%2F"
    assert parse_filters("q=" + "가" * 200)["q"] == "가" * 200
    assert parse_filters("q=&control=&status=&treatment=")["query"] == ""


def test_filter_and_empty_groups(tmp_path):
    data = WorkbenchReader(load_catalog(), tmp_path / "runs", readiness=ReadinessStore(tmp_path / "state")).workbench()
    groups = data["ui"]["groups"]
    result = filter_groups(groups, parse_filters("control=A&status=PASS"))
    assert len(result) == 1 and result[0]["scenarios"] == []
    result = filter_groups(groups, parse_filters("q=n-03&control=N&treatment=EXECUTED&status=PASS"))
    assert [r["id"] for g in result for r in g["scenarios"]] == ["N-03"]


def test_overview_and_results_are_separate_and_all_links_reset(site):  # noqa: F811
    body = page(site, "/")
    assert "VERIFICATION OVERVIEW" in body and "확인한 것과, 아직 남은 것" not in body
    assert all(label in body for label in ("고지와 동의", "사람의 통제", "이의제기와 구제", "평가의 근거"))
    assert "[REDACTED]" not in body
    assert 'data-coverage="EXECUTED">9<' in body and 'data-coverage="NOT_RUN">0<' in body
    links = [a["href"] for tag, a in Markup(body).tags if tag == "a"]
    assert links.count("/results") >= 3
    assert all(f"/results?control={c}" in links for c in "NHAE")
    assert 'id="catalog"' in body and '<table id="catalog"' not in body
    results = page(site, "/results?control=N&q=n-03")
    ids = [a["data-id"] for tag, a in Markup(results).tags if a.get("class") == "scenario-result"]
    assert ids == ["N-03"]
    assert "일부 범위" in results and "N03-U1" in results
    assert 'href="/results"' in results
    assert 'class="scenario-result"' not in page(site, "/results?control=A&status=PASS")
    assert "RESULT_FILTER_INVALID" in page(site, "/results?q=%FF", expected=400)
    xss = page(site, "/results?q=%3Cscript%3Ealert(1)%3C%2Fscript%3E")
    assert '<script>alert(1)</script>' not in xss and "&lt;script&gt;" in xss
    assert "DEMO DATA" in page(site, "/demo/results")
    assert 'href="/demo/results?control=N"' in page(site, "/demo/")


def test_results_get_does_not_run_preflight_and_api_ignores_ui_query(site, monkeypatch):  # noqa: F811
    monkeypatch.setattr(site.runner, "check", lambda *a, **kw: pytest.fail("GET must not execute preflight"))
    page(site, "/results")
    data = json.loads(page(site, "/api/workbench?control=A"))
    assert len([r for g in data["groups"] for r in g["scenarios"]]) == 12
    for path in ("/results", "/demo/results"):
        assert "HOST_NOT_ALLOWED" in page(site, path, expected=421, host="invalid.example")
        tags = Markup(page(site, path)).tags
        assert not any(tag == "style" or "style" in a or any(k.startswith("on") for k in a) for tag, a in tags)
