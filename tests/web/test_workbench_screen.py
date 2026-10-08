"""T026 — workbench screen in a real browser at 1280px and 1024px (FR-001~007, SC-001, SC-006). RED until T032.

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
    return page.locator("tr.scenario-row:visible")


def test_layout_demo_band_and_no_horizontal_overflow(page) -> None:
    assert page.locator(".demo-banner").inner_text().startswith("DEMO DATA")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    header = page.locator("header").inner_text()
    assert "LOCAL_EMULATED" in header and "NOT_RUN" in header
    assert page.locator("nav [role=tab]").count() == 4
    assert page.locator("tr.scenario-row").count() == 12
    for cell in page.locator("td.scenario-id").all():
        assert cell.evaluate("el => getComputedStyle(el).whiteSpace") == "nowrap"


def test_count_cards_and_neutral_inconclusive_card(page) -> None:
    assert page.locator("[data-count=PASS] .num").inner_text() == "4"
    assert page.locator("[data-count=FAIL] .num").inner_text() == "0"
    assert page.locator("[data-count=NOT_RUN] .num").inner_text() == "4"
    card = page.locator("[data-count=INCONCLUSIVE]")
    assert card.locator(".num").inner_text() == "4"
    assert card.locator(".neutral-title").count() == 1
    for key, icon, count in (("insufficient_evidence", "?", "1"), ("reason_no_test_target", "∅", "3")):
        in_card = card.locator(f"[data-badge={key}]")
        assert in_card.locator(".ic").inner_text() == icon
        assert in_card.get_attribute("data-count-value") == count
        in_table = page.locator(f"tr.scenario-row [data-badge={key}]").first
        assert in_table.get_attribute("class") == in_card.get_attribute("class")
        assert in_table.locator(".ic").inner_text() == icon


def test_one_common_checked_at_and_only_differing_rows_show_time(page) -> None:
    assert page.locator("[data-testid=common-checked-at]").count() == 1
    differing = page.locator("tr.scenario-row .row-checked-at")
    assert differing.count() == 1
    assert page.locator("tr.scenario-row[data-id=N-02] .row-checked-at").count() == 1


@pytest.mark.parametrize("name,expected", [("runnable", 5), ("failed", 0), ("inconclusive", 4)])
def test_filters_5_0_4(page, name, expected) -> None:
    page.locator(f"[data-filter={name}]").check()
    assert _visible_rows(page).count() == expected
    page.locator(f"[data-filter={name}]").uncheck()
    assert _visible_rows(page).count() == 12


def test_a_rows_have_no_run_control_or_progress(page) -> None:
    for scenario_id in ("A-01", "A-02", "A-03"):
        row = page.locator(f"tr.scenario-row[data-id={scenario_id}]")
        assert row.locator("button, form, progress, input, [role=progressbar]").count() == 0
        assert row.locator("[data-badge=pass]").count() == 0


def test_runner_not_ready_and_no_test_target_badges_differ(page) -> None:
    rnr = page.locator("tr.scenario-row[data-id=H-01] [data-badge=runner_not_ready]")
    ntt = page.locator("tr.scenario-row[data-id=A-01] [data-badge=readiness_no_test_target]")
    assert rnr.count() == 1 and ntt.count() == 1
    assert rnr.inner_text() != ntt.inner_text()
    assert rnr.locator(".ic").inner_text() != ntt.locator(".ic").inner_text()
    assert rnr.get_attribute("class") != ntt.get_attribute("class")


def test_no_pass_badge_on_not_run_or_inconclusive_rows(page) -> None:
    for row in page.locator("tr.scenario-row").all():
        if row.get_attribute("data-result") in {"NOT_RUN", "INCONCLUSIVE"}:
            assert row.locator("[data-badge=pass]").count() == 0


def test_preflight_form_is_the_only_action_and_disabled_on_demo(page) -> None:
    form = page.locator("form[data-testid=preflight-form]")
    assert form.count() == 1
    assert form.locator("button[type=submit]").is_disabled()
    assert page.locator("main form").count() == 1
