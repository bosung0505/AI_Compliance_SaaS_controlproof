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
    assert "다른 지원자" in row.inner_text() and "점수·인용 비움" in row.inner_text()
    row.locator("button").click()
    proof = screen.locator("#proof-other-applicant")
    assert proof.is_visible() and proof.locator("a.condition-source").count() >= 2
    proof.locator("a.condition-source").first.click()
    assert "condition=other-applicant" in screen.url
    context = screen.locator("[data-testid=evidence-context]")
    assert "다른 지원자" in context.inner_text() and "점수·인용 비움" in context.inner_text()
    screen.locator("a.btn", has_text="선택한 조건").click()
    assert screen.url.endswith("#condition-other-applicant")
    assert screen.locator("#proof-other-applicant").is_visible()


def test_scenario_recent_result_is_reachable_at_the_top(screen, demo_site):
    screen.goto(f"{demo_site.url}/demo/scenarios/E-01")
    recent = screen.locator("[data-testid=latest-result]")
    assert recent.is_visible()
    assert "다른 지원자" in screen.locator(".condition-chips").inner_text()
    assert no_overflow(screen)
    assert recent.locator("a").bounding_box()["y"] < 600
    recent.locator("a").click()
    assert "/demo/runs/" in screen.url
