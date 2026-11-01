"""2026-11-01: the workspace screens wear the homepage header/footer (explore-workspace.css repeats the public values).

The computed styles and boxes of the shared header/footer are compared between /product and a workspace screen at
several widths, closed and opened, so a later change to platform.css/explore.css that is not mirrored fails here.
"""

from __future__ import annotations

import pytest

from tests.web.conftest import no_overflow

PROPS = [
    "display", "font-family", "font-size", "font-weight", "letter-spacing", "line-height", "color", "border-top",
    "border-bottom", "border-radius", "padding-top", "padding-right", "padding-bottom", "padding-left", "margin-top",
    "margin-right", "margin-bottom", "margin-left", "gap", "width", "height", "box-shadow", "visibility", "opacity",
    "justify-content", "align-items", "flex-direction", "flex-wrap", "white-space", "text-decoration-line",
]
CLOSED = {
    "header": ".explore-header", "nav-wrap": ".explore-header .nav-wrap", "logo": ".explore-header .cp-logo",
    "nav": ".explore-header .nav", "trigger1": "#nav-trigger-1", "trigger5": "#nav-trigger-5",
    "cta": ".explore-header .desktop-demo", "toggle": ".explore-header .menu-toggle",
    "footer": "footer.footer", "footer-logo": ".footer .cp-logo", "footer-p": ".footer-main p",
    "footer-nav-a": ".footer-main nav a", "footer-bottom": ".footer-bottom", "leadership": ".company-leadership",
}
OPEN_WIDE = {
    "panel": "#nav-panel-2", "panel-inner": "#nav-panel-2 .nav-panel-inner", "panel-label": "#nav-panel-2 .nav-panel-primary p",
    "panel-primary": "#nav-panel-2 .nav-panel-primary a", "panel-secondary": "#nav-panel-2 .nav-panel-secondary a",
    "trigger-open": "#nav-trigger-2",
}
OPEN_NARROW = {
    "menu": ".explore-header .nav", "disclosure": ".nav-disclosure", "trigger": "#nav-trigger-3",
    "panel": "#nav-panel-3", "panel-primary": "#nav-panel-3 .nav-panel-primary a",
}
COLLECT = """([items, props]) => {
  const header = document.querySelector('.explore-header').getBoundingClientRect();
  const footer = document.querySelector('footer.footer').getBoundingClientRect();
  const out = {};
  for (const [key, selector] of Object.entries(items)) {
    const el = document.querySelector(selector);
    const style = getComputedStyle(el), box = el.getBoundingClientRect();
    const base = el.closest('footer') ? footer : header;
    if (style.display === 'none' || !el.getClientRects().length) { out[key] = {rendered: false}; continue; }
    const row = {x: Math.round(box.x - base.x), y: Math.round(box.y - base.y), w: Math.round(box.width), h: Math.round(box.height)};
    for (const prop of props) row[prop] = style.getPropertyValue(prop);
    out[key] = row;
  }
  return out;
}"""


def _chrome(browser, url, width):
    context = browser.new_context(viewport={"width": width, "height": 900})
    page = context.new_page()
    page.goto(url)
    closed = page.evaluate(COLLECT, [CLOSED, PROPS])
    if width > 980:
        page.hover("#nav-trigger-2")
        page.wait_for_timeout(450)
        opened = page.evaluate(COLLECT, [OPEN_WIDE, PROPS])
    else:
        page.click(".explore-header .menu-toggle")
        page.click("#nav-trigger-3")
        page.wait_for_timeout(450)
        opened = page.evaluate(COLLECT, [OPEN_NARROW, PROPS])
    context.close()
    return closed, opened


@pytest.mark.parametrize("width", [1440, 1024, 760, 390])
def test_workspace_header_and_footer_match_the_homepage(web_browser, demo_site, width) -> None:
    product = _chrome(web_browser, f"{demo_site.url}/product", width)
    workspace = _chrome(web_browser, f"{demo_site.url}/demo/results", width)
    assert product == workspace


def test_workspace_top_keeps_demo_banner_and_header_visible_while_scrolling(screen, demo_site) -> None:
    screen.goto(f"{demo_site.url}/demo/")
    assert screen.locator(".explore-header .cp-logo img").evaluate("i => [i.complete, i.naturalWidth]") == [True, 2172]
    screen.mouse.wheel(0, 1600)
    screen.wait_for_timeout(200)
    banner = screen.locator(".workspace-top .demo-banner").bounding_box()
    header = screen.locator(".explore-header").bounding_box()
    assert round(banner["y"]) == 0 and abs(header["y"] - banner["height"]) < 1
    assert screen.evaluate("window.scrollY") > 0 and no_overflow(screen)


def test_workspace_has_separate_site_and_screen_menus_on_narrow_screens(web_browser, demo_site) -> None:
    context = web_browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    errors = []
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(f"{demo_site.url}/demo/")
    is_open = "id => document.getElementById(id).classList.contains('open')"
    page.click(".workspace-menu-toggle")
    assert page.get_attribute(".workspace-menu-toggle", "aria-label") == "화면 메뉴 닫기"
    assert page.evaluate(is_open, "primary-navigation") and not page.evaluate(is_open, "site-navigation")
    assert page.locator("#primary-navigation a").count() == 5
    page.click(".explore-header .menu-toggle")
    assert page.evaluate(is_open, "site-navigation") and not page.evaluate(is_open, "primary-navigation")
    page.keyboard.press("Escape")
    assert not page.evaluate(is_open, "site-navigation")
    assert no_overflow(page) and errors == []
    context.close()


@pytest.mark.parametrize("path", ["/demo/", "/demo/results", "/demo/report", "/demo/prepare", "/guide"])
def test_pages_fit_narrow_screens_with_the_new_frame(web_browser, demo_site, path) -> None:
    context = web_browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    page.goto(f"{demo_site.url}{path}")
    assert page.locator(".explore-header").count() == 1 and page.locator("footer.footer").count() == 1
    assert no_overflow(page)
    context.close()
