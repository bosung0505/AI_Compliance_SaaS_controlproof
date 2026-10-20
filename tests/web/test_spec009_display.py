"""T011 — workbench one-liners: target access on result and scenario screens, N-03 unverified scope and limits.

Sealed N-01/N-03 Runs come from the executors over fakes; the server runs on a temporary run root (local mode).
"""

from __future__ import annotations

import html
import http.client
import threading
from types import SimpleNamespace

import pytest

from engine.executors.n01 import N01Executor
from engine.executors.n03 import N03Executor
from engine.scenario import load
from engine.web import server
from engine.web.readmodel import scope_item_lines, target_access_line
from tests.fixtures import web_bundles as wb
from tests.fixtures.fake_spec009 import make_spec009_adapters, ready, spec009_target

N01 = load("scenarios/N-01.yaml")
N03 = load("scenarios/N-03.yaml")


def _sealed(tmp_path, target, executor_type, scenario):
    workspace = tmp_path / scenario.scenario_id
    workspace.mkdir()
    adapters, _backend, _store = make_spec009_adapters(workspace, target)
    run, _judgement, _directory = executor_type(scenario, adapters, tmp_path / "runs").execute(ready(scenario, target))
    return str(run.run_id)


@pytest.fixture
def site(tmp_path, target_snapshot):
    target = spec009_target(target_snapshot)
    runs = SimpleNamespace(
        n01=_sealed(tmp_path, target, N01Executor, N01),
        n03=_sealed(tmp_path, target, N03Executor, N03),
        e01=wb.spec004_run(tmp_path / "runs", "E-01").run_id,
    )
    instance = server.make_server(0, run_root=tmp_path / "runs", demo_root=tmp_path / "demo", state_dir=tmp_path / "web")
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield SimpleNamespace(port=instance.server_address[1], runs=runs)
    instance.shutdown()
    instance.server_close()
    thread.join(5)


def _page(site, path) -> str:
    connection = http.client.HTTPConnection("127.0.0.1", site.port, timeout=30)
    connection.request("GET", path, headers={"Host": f"127.0.0.1:{site.port}"})
    response = connection.getresponse()
    body = response.read().decode("utf-8")
    connection.close()
    assert response.status == 200, path
    return body


def test_labels_join_in_declaration_order() -> None:
    assert target_access_line(["SCREEN", "API"]) == "화면 + API"
    assert target_access_line(["API"]) == "API"
    assert target_access_line(["SOURCE"]) == "소스 열람"
    assert target_access_line([]) is None and target_access_line(None) is None


def test_n01_result_screen_shows_target_access_above_the_limits(site) -> None:
    body = _page(site, f"/runs/{site.runs.n01}")
    line = '<p class="target-access">대상 접근: 화면 + API</p>'
    assert line in body
    assert body.index(line) < body.index("<b>실행 한계</b>")
    assert "후속 조건" not in body


def test_n03_result_screen_lists_unverified_items_and_limitation(site) -> None:
    body = _page(site, f"/runs/{site.runs.n03}")
    assert '<p class="target-access">대상 접근: API</p>' in body
    for item in N03.unverified_scope_items:
        assert html.escape(f"미검증: {item.text} — 후속 조건: {item.follow_up}", quote=False) in body
    assert "한계: 이전 정책 식별값은 실제 교체 없이 만든 값" in body
    assert body.count('<li class="scope-item">') == 4


@pytest.mark.parametrize(("scenario_id", "line"), [("N-01", "화면 + API"), ("N-03", "API")])
def test_scenario_screens_show_target_access(site, scenario_id, line) -> None:
    body = _page(site, f"/scenarios/{scenario_id}")
    assert f'<p class="target-access">대상 접근: {line}</p>' in body


@pytest.mark.parametrize("path", ["/scenarios/H-01", "/scenarios/E-01"])
def test_existing_scenarios_have_no_target_access_line(site, path) -> None:
    assert 'class="target-access"' not in _page(site, path)


def test_existing_result_screen_has_no_target_access_line(site) -> None:
    body = _page(site, f"/runs/{site.runs.e01}")
    assert 'class="target-access"' not in body and 'class="scope-item"' not in body


def test_scope_lines_are_escaped_when_rendered(site) -> None:
    lines = scope_item_lines(
        {"unverified_scope_items": [{"id": "X", "text": "<script>x</script>", "follow_up": "a & b"}], "limitations": []}
    )
    assert lines == ["미검증: <script>x</script> — 후속 조건: a & b"]
    # The server's template environment autoescapes .html (engine/web/server.py); the string template mirrors it.
    from jinja2 import Environment, select_autoescape

    environment = Environment(autoescape=select_autoescape(["html"], default_for_string=True))
    rendered = environment.from_string('{% for line in lines %}<li class="scope-item">{{ line }}</li>{% endfor %}').render(
        lines=lines
    )
    assert "<script>" not in rendered and "&lt;script&gt;" in rendered and "a &amp; b" in rendered
