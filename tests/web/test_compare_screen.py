"""T054 — compare screen ④ (compare part) at 1280px and 1024px (FR-021~023, SC-005). RED until T056."""

from __future__ import annotations

import json

from tests.web.conftest import no_overflow


def _e01_child(demo_root):
    for directory in sorted(demo_root.iterdir()):
        link = directory / "retest-link.json"
        run = directory / "run.json"
        if link.is_file() and json.loads(run.read_text(encoding="utf-8"))["scenario_id"] == "E-01":
            parent = json.loads(link.read_text(encoding="utf-8"))["parent_run_id"]
            parent_run = json.loads((demo_root / parent / "run.json").read_text(encoding="utf-8"))
            if parent_run.get("parent_run_id") is None:
                return directory.name, parent
    raise LookupError("no E-01 child in the DEMO root")


def test_two_runs_side_by_side_parent_unchanged(screen, demo_site) -> None:
    child, parent = _e01_child(demo_site.demo_root)
    screen.goto(f"{demo_site.url}/demo/compare/{child}")
    assert no_overflow(screen)
    left = screen.locator("[data-testid=compare-parent]")
    right = screen.locator("[data-testid=compare-child]")
    assert parent in left.inner_text().replace("…", "") or parent[:8] in left.inner_text()
    assert child[:8] in right.inner_text() and parent[:8] != child[:8]
    assert left.locator("[data-badge=fail]").count() == 1
    assert right.locator("[data-badge=pass]").count() == 1
    assert "부모 기록 불변 확인" in screen.locator("[data-testid=parent-unchanged]").inner_text()
    assert screen.locator("tr.assertion-change").count() >= 4


def test_retest_only_as_a_command(screen, demo_site) -> None:
    child, _ = _e01_child(demo_site.demo_root)
    screen.goto(f"{demo_site.url}/demo/compare/{child}")
    assert "python -m engine.cli retest" in screen.locator("[data-testid=retest-command]").inner_text()
    labels = [button.inner_text() for button in screen.locator("main button").all()]
    assert all(label == "복사" for label in labels), labels
    assert screen.locator("main form").count() == 0


def test_compare_reached_from_run_and_report(screen, demo_site) -> None:
    child, _ = _e01_child(demo_site.demo_root)
    screen.goto(f"{demo_site.url}/demo/runs/{child}")
    screen.locator("a[data-testid=open-compare]").click()
    assert screen.url.endswith(f"/demo/compare/{child}")
