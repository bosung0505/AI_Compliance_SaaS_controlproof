"""Clickable elements look and react differently from plain text (D-022 internal review #3).

Links get a pointer cursor, a hover background and a short transition; buttons lift on hover; status badges stay
non-interactive. Users who ask for reduced motion get no transition. The report links scenarios to their detail (#2).
"""

from __future__ import annotations

from tests.web.conftest import no_overflow


def _style(locator, prop):
    return locator.evaluate(f"el => getComputedStyle(el).getPropertyValue('{prop}')")


def test_links_show_pointer_hover_and_transition(screen, demo_site) -> None:
    screen.goto(f"{demo_site.url}/demo/")
    link = screen.locator("a.detail-link").first
    assert _style(link, "cursor") == "pointer"
    assert _style(link, "transition-duration") not in ("", "0s")
    screen.mouse.move(0, 0)
    before = _style(link, "background-color")
    link.hover()
    screen.wait_for_timeout(300)
    assert _style(link, "background-color") != before


def test_buttons_react_and_badges_do_not(screen, demo_site) -> None:
    screen.goto(f"{demo_site.url}/demo/")
    button = screen.locator("a[data-testid=open-report]")
    screen.mouse.move(0, 0)
    before = _style(button, "box-shadow")
    button.hover()
    screen.wait_for_timeout(300)
    assert _style(button, "box-shadow") != before
    badge = screen.locator("[data-badge]").first
    assert _style(badge, "cursor") != "pointer"


def test_keyboard_focus_is_visible(screen, demo_site) -> None:
    screen.goto(f"{demo_site.url}/demo/")
    link = screen.locator("a.detail-link").first
    link.focus()
    screen.keyboard.press("Shift+Tab")
    screen.keyboard.press("Tab")
    assert _style(link, "outline-style") not in ("", "none")


def test_reduced_motion_turns_transitions_off(screen, demo_site) -> None:
    screen.emulate_media(reduced_motion="reduce")
    try:
        screen.goto(f"{demo_site.url}/demo/")
        assert _style(screen.locator("a.detail-link").first, "transition-duration") in ("0s", "")
    finally:
        screen.emulate_media(reduced_motion="no-preference")


def test_report_scenario_link_opens_detail(screen, demo_site) -> None:
    screen.goto(f"{demo_site.url}/demo/report")
    screen.locator("[data-testid=report-catalog] a.scenario-link", has_text="E-01").click()
    assert screen.url.endswith("/demo/scenarios/E-01")
    assert no_overflow(screen)
