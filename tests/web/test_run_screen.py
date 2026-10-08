"""T037 — run screen ③ in a real browser at 1280px and 1024px (FR-013~020, SC-002, SC-003). RED until T041."""

from __future__ import annotations

from tests.web.conftest import find_run, no_overflow


def _open(screen, demo_site, run_id):
    screen.goto(f"{demo_site.url}/demo/runs/{run_id}")
    assert screen.locator(".demo-banner").count() == 1
    assert no_overflow(screen)


def test_fail_run_plain_first_developer_collapsed(screen, demo_site) -> None:
    run_id = find_run(demo_site.demo_root, "H-03", verdict="FAIL", state="COMPLETED")
    _open(screen, demo_site, run_id)
    lead = screen.locator("[data-testid=run-lead]")
    assert lead.locator("[data-badge=fail]").count() == 1
    plain = screen.locator("[data-testid=plain-explanation]")
    assert plain.is_visible() and "무엇이" in plain.inner_text()
    developer = screen.locator("details[data-testid=developer]")
    assert developer.count() >= 1
    for item in developer.all():
        assert item.get_attribute("open") is None
    assert "manifest.json" not in plain.inner_text()


def test_failed_only_toggle(screen, demo_site) -> None:
    run_id = find_run(demo_site.demo_root, "H-03", verdict="FAIL", state="COMPLETED")
    _open(screen, demo_site, run_id)
    rows = screen.locator("tr.assertion-row")
    total = rows.count()
    assert total > 0
    screen.locator("[data-testid=fail-only]").check()
    visible = screen.locator("tr.assertion-row:visible")
    assert 0 < visible.count() < total
    for row in visible.all():
        assert row.get_attribute("data-status") in {"FAIL", "INCONCLUSIVE"}
    screen.locator("[data-testid=fail-only]").uncheck()
    assert screen.locator("tr.assertion-row:visible").count() == total


def test_memo_form_is_separate_from_the_sealed_record(screen, demo_site) -> None:
    run_id = find_run(demo_site.demo_root, "E-01", verdict="FAIL")
    _open(screen, demo_site, run_id)
    section = screen.locator("[data-testid=memo-section]")
    assert "봉인 기록과 분리" in section.inner_text()
    assert section.locator("form").count() == 1
    assert section.locator("button[type=submit]").is_disabled()  # DEMO records take no memos


def test_integrity_failure_is_not_a_fail(screen, demo_site) -> None:
    run_id = find_run(demo_site.demo_root, "H-03", valid=False)
    _open(screen, demo_site, run_id)
    lead = screen.locator("[data-testid=run-lead]")
    assert lead.locator("[data-badge=integrity_failed]").count() == 1
    assert screen.locator("[data-badge=fail], [data-badge=pass]").count() == 0
    assert screen.locator("tr.assertion-row").count() == 0


def test_restore_failure_badge_comes_before_the_verdict(screen, demo_site) -> None:
    run_id = find_run(demo_site.demo_root, "H-03", state="RESTORE_FAILED")
    _open(screen, demo_site, run_id)
    badges = screen.locator("[data-testid=run-lead] [data-badge]")
    assert badges.first.get_attribute("data-badge") == "restore_failed"
    restore = screen.locator("[data-testid=run-lead] [data-badge=restore_failed]")
    fail = screen.locator("[data-badge=fail]")
    if fail.count():
        assert restore.get_attribute("class") != fail.first.get_attribute("class")
    assert "수동 정리" in screen.locator("[data-testid=restore]").inner_text()


def test_aborted_run_shows_state_first_and_missing_evidence(screen, demo_site) -> None:
    run_id = find_run(demo_site.demo_root, "H-03", state="ABORTED")
    _open(screen, demo_site, run_id)
    lead = screen.locator("[data-testid=run-lead]")
    assert lead.locator("[data-testid=run-state]").first.inner_text().startswith("중단")
    assert "봉인 무결성 확인됨" in lead.inner_text()
    assert "EV-06" in screen.locator("[data-testid=aborted-missing]").inner_text()


def test_workbench_to_result_to_evidence_in_three_clicks(screen, demo_site) -> None:
    screen.goto(f"{demo_site.url}/demo/")
    clicks = 0
    screen.locator("tr.scenario-row[data-id=E-01] a.result-link").first.click()
    clicks += 1
    assert "/demo/runs/" in screen.url
    screen.locator("a.evidence-link").first.click()
    clicks += 1
    assert "/evidence" in screen.url
    assert len(screen.locator("[data-testid=evidence-sha256]").inner_text().strip()) == 64
    assert clicks <= 3
    assert no_overflow(screen)
