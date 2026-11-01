"""2026-11-01 homepage in a real browser: logo under CSP, header disclosures, preview tabs and mobile menu.

Public pages read only the catalog, so the DEMO site serves the same `/product` and `/guide` markup.
"""

from __future__ import annotations

import pytest

from tests.web.conftest import no_overflow


def test_logo_loads_under_csp_and_header_disclosures_open_and_close(screen, demo_site) -> None:
    screen.goto(f"{demo_site.url}/product")
    sizes = screen.eval_on_selector_all(".cp-logo img", "imgs => imgs.map(i => [i.complete, i.naturalWidth])")
    assert sizes == [[True, 2172], [True, 2172]]
    screen.hover("#nav-trigger-2")
    screen.wait_for_timeout(400)
    assert screen.get_attribute("#nav-trigger-2", "aria-expanded") == "true"
    assert screen.evaluate("document.getElementById('nav-panel-2').inert") is False
    assert screen.locator("#nav-panel-2 a").first.is_visible()
    screen.keyboard.press("Escape")
    screen.wait_for_timeout(400)
    assert screen.locator(".nav-disclosure.is-open").count() == 0
    assert screen.evaluate("document.getElementById('nav-panel-2').inert") is True
    screen.mouse.move(5, 600)
    screen.focus("#nav-trigger-4")
    screen.keyboard.press("ArrowDown")
    screen.wait_for_timeout(400)
    screen.keyboard.press("Tab")
    assert screen.evaluate("document.activeElement.closest('.nav-panel')?.id") == "nav-panel-4"
    assert no_overflow(screen)


def test_feature_preview_tabs_follow_click_and_arrow_keys(screen, demo_site) -> None:
    screen.goto(f"{demo_site.url}/product")
    visible = "() => [0, 1, 2].map(i => !document.getElementById('feature-screen-' + i).hidden)"
    assert screen.evaluate(visible) == [True, False, False]
    screen.click("#feature-tab-1")
    assert screen.evaluate(visible) == [False, True, False]
    screen.keyboard.press("ArrowRight")
    assert screen.evaluate(visible) == [False, False, True]
    assert screen.evaluate("document.activeElement.id") == "feature-tab-2"
    screen.keyboard.press("Home")
    assert screen.evaluate(visible) == [True, False, False]


@pytest.mark.parametrize("path", ["/product", "/guide"])
def test_mobile_menu_opens_disclosures_without_horizontal_overflow(web_browser, demo_site, path) -> None:
    context = web_browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    errors = []
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(f"{demo_site.url}{path}")
    assert no_overflow(page)
    page.click(".menu-toggle")
    assert page.get_attribute(".menu-toggle", "aria-expanded") == "true"
    page.click("#nav-trigger-3")
    page.wait_for_timeout(300)
    assert page.locator("#nav-panel-3 a").first.is_visible()
    page.keyboard.press("Escape")
    assert page.get_attribute(".menu-toggle", "aria-expanded") == "false"
    assert errors == []
    context.close()
