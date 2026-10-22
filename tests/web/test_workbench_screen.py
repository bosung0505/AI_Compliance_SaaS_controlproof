"""T026 / Spec010 T012 — overview and results at 1280px and 1024px.

Playwright's bundled Chromium is used when installed; otherwise the installed Edge channel (research R-014). The screen
uses the DEMO root built by `scripts/prepare_web_demo.py`.
"""

from __future__ import annotations

import threading

import pytest

from engine.web import server
from scripts import prepare_web_demo

sync_api = pytest.importorskip("playwright.sync_api")
WIDTHS = (1280, 1024)


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    base = tmp_path_factory.mktemp("web")
    demo_root = base / "web-demo" / "runs"
    assert prepare_web_demo.main(["--demo-root", str(demo_root)]) == 0
    instance = server.make_server(0, run_root=base / "runs", demo_root=demo_root, state_dir=base / "web")
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{instance.server_address[1]}"
    instance.shutdown()
    instance.server_close()
    thread.join(5)


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as playwright:
        launched, failures = None, []
        for options in ({}, {"channel": "msedge"}, {"channel": "chrome"}):
            try:
                launched = playwright.chromium.launch(**options)
            except Exception as exc:  # noqa: BLE001 - try the next installed browser
                failures.append(f"{options.get('channel', 'chromium')}: {type(exc).__name__}")
            else:
                print(f"browser: {options.get('channel', 'chromium')} {launched.version}")
                break
        if launched is None:
            pytest.skip(f"no Playwright Chromium, Edge or Chrome browser installed ({'; '.join(failures)})")
        yield launched
        launched.close()


@pytest.fixture(params=WIDTHS, ids=lambda width: f"{width}px")
def page(request, browser, site):
    context = browser.new_context(viewport={"width": request.param, "height": 900})
    opened = context.new_page()
    errors = []
    opened.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    opened.on("pageerror", lambda error: errors.append(str(error)))
    opened.goto(f"{site}/demo/")
    yield opened
    assert errors == []
    context.close()


def _visible_rows(page):
    return page.locator("article.scenario-result:visible")


def _results(page):
    page.get_by_role("link", name="결과 검토하기 →", exact=True).click()


def test_layout_demo_band_and_no_horizontal_overflow(page) -> None:
    assert page.locator(".demo-banner").inner_text().startswith("DEMO DATA")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    header = page.locator("header").inner_text()
    assert "LOCAL_EMULATED" in header and "NOT_RUN" in header
    assert page.locator(".workspace-nav a").count() == 5
    assert page.locator(".control-card").count() == 4
    assert page.locator(".scenario-tags a").count() == 12
    _results(page)
    assert _visible_rows(page).count() == 12
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_coverage_graph_and_neutral_target_absence(page) -> None:
    for treatment, count in (("EXECUTED", "9"), ("NOT_RUN", "0"), ("NO_TEST_TARGET", "3")):
        assert page.locator(f'[data-coverage="{treatment}"]').inner_text() == count
    assert page.locator(".chart-segment").count() == 2
    assert "12" in page.locator(".coverage-chart svg").get_attribute("aria-label")
    _results(page)
    assert page.locator(".scenario-result [data-badge=reason_no_test_target]").count() == 3


def test_common_checked_at_and_per_row_preparation_are_available(page) -> None:
    _results(page)
    assert page.locator("[data-testid=common-checked-at]").count() == 1
    row = page.locator('article.scenario-result[data-id="N-02"]')
    assert "새 테스트 준비" in row.locator("details").inner_text()
    assert row.locator("[data-badge=ready]").count() >= 1


@pytest.mark.parametrize("status,expected", [("PASS", 9), ("FAIL", 0), ("INCONCLUSIVE", 3)])
def test_result_filters_and_reset(page, status, expected) -> None:
    _results(page)
    page.get_by_role("combobox", name="공식 결과", exact=True).select_option(status)
    page.get_by_role("button", name="적용", exact=True).click()
    assert _visible_rows(page).count() == expected
    page.get_by_role("link", name="초기화", exact=True).click()
    assert _visible_rows(page).count() == 12


def test_a_rows_have_no_run_control_or_progress(page) -> None:
    card = page.locator(".control-card").filter(has_text="이의제기와 구제")
    assert card.locator("progress, [role=progressbar]").count() == 0
    _results(page)
    for scenario_id in ("A-01", "A-02", "A-03"):
        row = page.locator(f'article.scenario-result[data-id="{scenario_id}"]')
        assert row.locator("button, form, progress, input, [role=progressbar]").count() == 0
        assert row.locator("[data-badge=pass]").count() == 0


def test_runner_not_ready_and_no_test_target_badges_differ(page) -> None:
    # Since Spec 009 closure (12/9/0/3) no catalog row is NOT_RUN, so the runner_not_ready badge has no live row;
    # its distinction from NO_TEST_TARGET is checked on the badge definitions and the A-01 row.
    from engine.web.badges import BADGES

    _results(page)
    assert page.locator(".scenario-result [data-badge=runner_not_ready]").count() == 0
    ntt = page.locator('article.scenario-result[data-id="A-01"] [data-badge=readiness_no_test_target]')
    assert ntt.count() == 1
    rnr = BADGES["runner_not_ready"]
    assert ntt.locator(".ic").inner_text() == BADGES["readiness_no_test_target"].icon != rnr.icon
    assert BADGES["readiness_no_test_target"].label_ko != rnr.label_ko
    assert ntt.get_attribute("class") == BADGES["readiness_no_test_target"].css_class != rnr.css_class


def test_no_pass_badge_on_not_run_or_inconclusive_rows(page) -> None:
    _results(page)
    page.get_by_role("combobox", name="공식 결과", exact=True).select_option("INCONCLUSIVE")
    page.get_by_role("button", name="적용", exact=True).click()
    assert _visible_rows(page).count() == 3
    assert page.locator(".scenario-result [data-badge=pass]").count() == 0


def test_preflight_form_is_the_only_action_and_disabled_on_demo(page) -> None:
    _results(page)
    form = page.locator("form[data-testid=preflight-form]")
    assert form.count() == 1
    assert form.locator("button[type=submit]").is_disabled()
    assert page.locator('main form[method="post"]').count() == 1
    assert page.locator('main form[method="get"]').count() == 1
