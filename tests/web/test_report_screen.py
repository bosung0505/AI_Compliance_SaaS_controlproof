"""T044 — report screen ④ (report part) at 1280px and 1024px (FR-025~029, SC-004, SC-011). RED until T046."""

from __future__ import annotations

import json
import urllib.request

from tests.web.conftest import no_overflow

ITEMS = [f"R{index}" for index in range(1, 14)] + [f"C{index}" for index in range(1, 10)]


def test_22_item_markers_visible(screen, demo_site) -> None:
    screen.goto(f"{demo_site.url}/demo/report")
    assert screen.locator(".demo-banner").count() == 1
    assert no_overflow(screen)
    for item in ITEMS:
        marker = screen.locator(f"[data-item={item}]")
        assert marker.count() >= 1, item
        assert marker.first.is_visible(), item
    sentence = screen.locator("[data-testid=fixed-scope-sentence]").inner_text()
    assert "12개 시나리오를 한 화면에서 관리한다" in sentence
    text = screen.locator("main").inner_text()
    assert "12개 검증 완료" not in text and "12개 PASS" not in text
    assert "h03-report-v1" not in text.replace(screen.locator("details[data-testid=developer]").first.inner_text(), "")


def test_report_reached_from_the_workbench(screen, demo_site) -> None:
    screen.goto(f"{demo_site.url}/demo/")
    screen.locator("a[data-testid=open-report]").click()
    assert screen.url.endswith("/demo/report")
    screen.locator("nav [role=tab]").nth(3).click()
    assert screen.url.endswith("/demo/report")


def test_demo_report_never_mixes_into_actual_counts(screen, demo_site) -> None:
    with urllib.request.urlopen(f"{demo_site.url}/api/report") as response:
        actual = json.loads(response.read())
    with urllib.request.urlopen(f"{demo_site.url}/demo/api/report") as response:
        demo = json.loads(response.read())
    assert (actual["data_origin"], demo["data_origin"]) == ("ACTUAL", "DEMO")
    assert actual["counts"] == demo["counts"]
    assert all(item["records_on_this_pc"] == 0 for item in actual["evidence_summary"])
    assert any(item["records_on_this_pc"] > 0 for item in demo["evidence_summary"])
    screen.goto(f"{demo_site.url}/report")
    assert screen.locator(".demo-banner").count() == 0
