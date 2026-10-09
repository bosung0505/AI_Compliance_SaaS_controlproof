"""T057a~T057d — readability checks on the run screen at 1280px and 1024px (ID-005-09)."""

from __future__ import annotations

from tests.web.conftest import find_run, no_overflow


def _plain_text(page) -> str:
    """Visible main text without collapsed developer details."""
    return page.evaluate(
        """() => { const main = document.querySelector('main').cloneNode(true);
                   main.querySelectorAll('details').forEach(d => d.remove());
                   return main.innerText; }"""
    )


def _header_text(page) -> str:
    return page.evaluate(
        """() => { const h = document.querySelector('header').cloneNode(true);
                   h.querySelectorAll('details').forEach(d => d.remove());
                   return h.innerText; }"""
    )


def test_aborted_run_never_shows_verified(screen, demo_site) -> None:
    screen.goto(f"{demo_site.url}/demo/runs/{find_run(demo_site.demo_root, 'H-03', state='ABORTED')}")
    assert no_overflow(screen)
    text = _plain_text(screen)
    assert "VERIFIED" not in text
    assert "명령줄 verify: INVALID" in text and "EV-06, EV-07" in text


def test_steps_in_plain_words_ids_only_in_developer(screen, demo_site) -> None:
    screen.goto(f"{demo_site.url}/demo/runs/{find_run(demo_site.demo_root, 'H-03', verdict='FAIL', state='COMPLETED')}")
    summary = screen.locator("[data-testid=phase-summary]").inner_text()
    assert "기준선" in summary and "주입" in summary and "복구" in summary
    for step_id in ("seed-pending-report", "apply-reporting-fault", "capture-baseline"):
        assert step_id not in _plain_text(screen)
        assert screen.locator("details[data-testid=developer]", has_text=step_id).count() >= 1


def test_evidence_names_grouped_without_repeats(screen, demo_site) -> None:
    screen.goto(f"{demo_site.url}/demo/runs/{find_run(demo_site.demo_root, 'H-03', verdict='FAIL', state='COMPLETED')}")
    for cell in screen.locator("td.evidence-cell").all():
        names = [group.get_attribute("data-name") for group in cell.locator(".evidence-group").all()]
        assert len(names) == len(set(names))
    table_names = [cell.inner_text() for cell in screen.locator("[data-testid=evidence-table] td.evidence-name").all()]
    assert table_names and len(table_names) == len(set(table_names))
    assert "수집한 원본 기록" not in _plain_text(screen)


def test_english_scope_and_snapshot_hash_hidden_by_default(screen, demo_site) -> None:
    screen.goto(f"{demo_site.url}/demo/runs/{find_run(demo_site.demo_root, 'H-03', verdict='FAIL', state='COMPLETED')}")
    text = _plain_text(screen)
    assert "reporting retry exhaustion" not in text and "generic stage-move" not in text
    assert "target-snapshot:sha256" not in text and "target-snapshot:sha256" not in _header_text(screen)
