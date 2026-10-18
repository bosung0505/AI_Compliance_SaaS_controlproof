"""Conditions, observations and source context remain connected in the approved UX."""

from tests.web.conftest import find_run, no_overflow


def test_e01_conditions_open_all_sources_without_losing_the_run(screen, demo_site):
    run_id = find_run(demo_site.demo_root, "E-01", verdict="PASS")
    screen.goto(f"{demo_site.url}/demo/runs/{run_id}")
    review = screen.locator("[data-testid=condition-review]")
    assert review.locator("tr.observation-row").count() == 7
    assert "규칙 4개" in screen.locator("[data-testid=plain-explanation]").inner_text()
    assert no_overflow(screen)
    row = screen.locator("#condition-other-applicant")
    assert "다른 지원자" in row.inner_text() and "WhyYou" in row.inner_text() and "보류" in row.inner_text()
    summary = screen.locator("[data-testid=plain-explanation]").inner_text()
    assert "확인하세요" not in summary and "보류" in summary
    assert "DB" not in summary and "직접" not in summary
    assert "고정 테스트용 모델" in screen.locator("[data-testid=test-process]").inner_text()
    row.locator("button").click()
    proof = screen.locator("#proof-other-applicant")
    assert proof.is_visible() and proof.locator("a.condition-source").count() >= 2
    assert proof.locator("[data-testid=record-comparison]").is_visible()
    assert "테스트에 넣은 AI 평가" in proof.inner_text() and "서비스가 실제 저장한 결과" in proof.inner_text()
    proof.locator("a.condition-source").first.click()
    assert "condition=other-applicant" in screen.url
    context = screen.locator("[data-testid=evidence-context]")
    assert "지원자" in context.inner_text() and "보류" in context.inner_text()
    assert context.locator("[data-testid=record-comparison]").is_visible()
    assert screen.locator("[data-testid=original-record]").get_attribute("open") is None
    screen.locator("a.btn", has_text="선택한 조건").click()
    assert screen.url.endswith("#condition-other-applicant")
    assert screen.locator("#proof-other-applicant").is_visible()


def test_scenario_recent_result_is_reachable_at_the_top(screen, demo_site):
    screen.goto(f"{demo_site.url}/demo/scenarios/E-01")
    recent = screen.locator("[data-testid=latest-result]")
    assert recent.is_visible()
    assert "다른 지원자" in screen.locator(".condition-chips").inner_text()
    assert no_overflow(screen)
    assert recent.bounding_box()["y"] < 600
    assert screen.locator("#runs").bounding_box()["y"] < screen.locator("[data-testid=run-guide]").bounding_box()["y"]
    recent.locator("a").click()
    assert "/demo/runs/" in screen.url
