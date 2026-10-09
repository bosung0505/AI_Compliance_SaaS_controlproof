"""T049 — scenario detail ② at 1280px and 1024px (FR-008~012, SC-010). RED until T051.

The readiness check runs through the real web runner with a fake subprocess (no target service): E-01 answers READY,
E-02 answers a usage error, which must show as "확인 도구 오류" and never as a readiness badge.
"""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from engine.web import server
from engine.web.preflight import PreflightRunner, ReadinessStore
from engine.web.readmodel import load_catalog
from tests.web.conftest import no_overflow


def _fake_cli(command, **kwargs):
    scenario_id = command[4]
    if scenario_id == "E-02":
        payload = {"schema_version": "controlproof.cli.v1", "command": "preflight", "result_kind": "ERROR",
                   "error_kind": "USAGE", "error": "USAGE", "detail": "the following arguments are required"}
        return SimpleNamespace(returncode=2, stdout=json.dumps(payload), stderr="")
    payload = {"schema_version": "controlproof.cli.v1", "command": "preflight", "result_kind": "READINESS",
               "readiness": "READY", "checked_at": datetime.now(UTC).isoformat(), "operator_action": None}
    return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")


@pytest.fixture(scope="module")
def actual_site(tmp_path_factory):
    base = tmp_path_factory.mktemp("web-us4")
    catalog = load_catalog()
    runner = PreflightRunner(catalog, ReadinessStore(base / "web" / "preflight"), run=_fake_cli)
    instance = server.make_server(
        0, run_root=base / "runs", demo_root=base / "demo" / "runs", state_dir=base / "web", preflight_runner=runner
    )
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield SimpleNamespace(url=f"http://127.0.0.1:{instance.server_address[1]}")
    instance.shutdown()
    instance.server_close()
    thread.join(5)


def test_e01_shows_preconditions_and_copyable_command_without_run_button(screen, actual_site) -> None:
    screen.goto(f"{actual_site.url}/scenarios/E-01")
    assert no_overflow(screen)
    guide = screen.locator("[data-testid=run-guide]")
    for text in ("준비 상태 READY", "잠금", "차단", "사람의 실행 승인"):
        assert text in guide.inner_text()
    command = screen.locator("[data-testid=run-command]").first
    assert "python -m engine.cli run E-01" in command.inner_text()
    assert guide.locator("button[data-copy]").count() >= 1
    labels = [button.inner_text() for button in screen.locator("main button").all()]
    assert all(label in {"복사", "준비 상태 확인"} for label in labels), labels
    assert screen.locator("progress, [role=progressbar]").count() == 0
    assert "법 조문 대응은 표시하지 않음(법적 준수 비보증)" in screen.locator("main").inner_text()


@pytest.mark.parametrize("scenario_id", ["H-01", "A-01"])
def test_not_run_and_no_target_have_no_run_elements(screen, actual_site, scenario_id) -> None:
    screen.goto(f"{actual_site.url}/scenarios/{scenario_id}")
    assert no_overflow(screen)
    assert screen.locator("main button, main form, progress, [role=progressbar]").count() == 0
    assert screen.locator("[data-testid=run-command], [data-badge=pass]").count() == 0
    text = screen.locator("main").inner_text()
    assert ("미실행" in text) if scenario_id == "H-01" else ("부재" in text)


def test_preflight_from_detail_stores_a_new_checked_at(screen, actual_site) -> None:
    screen.goto(f"{actual_site.url}/scenarios/E-01")
    form = screen.locator("form[data-testid=preflight-form]").first
    form.locator("button[type=submit]").click()
    screen.wait_for_url(f"{actual_site.url}/scenarios/E-01")
    readiness = screen.locator("[data-testid=profile-readiness]").first
    assert readiness.locator("[data-badge=ready]").count() == 1
    assert readiness.locator("[data-testid=checked-at]").inner_text().strip()


def test_usage_error_is_a_tool_error_not_readiness(screen, actual_site) -> None:
    screen.goto(f"{actual_site.url}/scenarios/E-02")
    screen.locator("form[data-testid=preflight-form] button[type=submit]").first.click()
    screen.wait_for_url(f"{actual_site.url}/scenarios/E-02")
    readiness = screen.locator("[data-testid=profile-readiness]").first
    assert readiness.locator("[data-badge=tool_error]").count() == 1
    assert readiness.locator("[data-badge=ready], [data-badge=runner_not_ready]").count() == 0
    assert "확인 도구 오류" in readiness.inner_text()


def test_workbench_detail_link_opens_the_scenario(screen, actual_site) -> None:
    screen.goto(f"{actual_site.url}/")
    screen.locator("tr.scenario-row[data-id=E-01] a.detail-link").click()
    assert screen.url.endswith("/scenarios/E-01")
