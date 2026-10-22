"""Report screen links to scenario detail (D-022 internal review #2): every scenario named on the report opens its detail page.

Before this, the report's only link was the retest comparison, so a reader had to go back to the workbench to reach a
scenario, its runs or its evidence. The detail page already links to runs and runs to evidence, so one link per scenario
row is enough to reach evidence from the report.
"""

from __future__ import annotations

import http.client
import re
import threading
from types import SimpleNamespace

import pytest

from engine.web import server
from tests.fixtures import web_bundles as wb

IDS = ["N-01", "N-02", "N-03", "H-01", "H-02", "H-03", "E-01", "E-02", "E-03", "A-01", "A-02", "A-03"]


@pytest.fixture
def web(tmp_path):
    run_root = tmp_path / "runs"
    wb.spec004_run(run_root, "E-01")
    instance = server.make_server(0, run_root=run_root, demo_root=tmp_path / "demo", state_dir=tmp_path / "web")
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield SimpleNamespace(port=instance.server_address[1])
    instance.shutdown()
    instance.server_close()
    thread.join(5)


def _html(web, path):
    connection = http.client.HTTPConnection("127.0.0.1", web.port, timeout=20)
    connection.request("GET", path, headers={"Host": f"127.0.0.1:{web.port}"})
    response = connection.getresponse()
    body = response.read().decode("utf-8")
    connection.close()
    assert response.status == 200
    return body


def _section(html, testid):
    match = re.search(rf'data-testid="{testid}".*?</table>', html, re.DOTALL)
    assert match, testid
    return match.group(0)


def test_catalog_table_links_every_scenario_to_its_detail(web) -> None:
    table = _section(_html(web, "/report"), "report-catalog")
    for scenario_id in IDS:
        assert f'href="/scenarios/{scenario_id}"' in table, scenario_id


def test_expectations_and_evidence_summary_link_to_detail(web) -> None:
    html = _html(web, "/report")
    expectations = re.search(r'data-testid="scenario-expectations".*?</ul>', html, re.DOTALL)
    assert expectations, "scenario-expectations list"
    for scenario_id in ("N-02", "H-03", "E-01", "E-02", "E-03"):
        assert f'href="/scenarios/{scenario_id}"' in expectations.group(0), scenario_id
    summary = _section(html, "evidence-summary")
    for scenario_id in ("N-02", "H-03", "E-01", "E-02", "E-03"):
        assert f'href="/scenarios/{scenario_id}"' in summary, scenario_id


def test_links_are_plain_get_routes_only(web) -> None:
    html = _html(web, "/report")
    assert "<form" not in html
    hrefs = set(re.findall(r'href="([^"]+)"', html))
    # The shared navigation now links to the existing catalog section, still a read-only GET.
    allowed = re.compile(r"^(#(?:main|report-[a-z-]+)|/static/.*|/(?:#catalog)?|/report|/results|/prepare|/product(?:#controls)?|/guide|/demo/?|/scenarios/[A-Z]-\d\d|/compare/[0-9a-f-]+|/runs/[0-9a-f-]+)$")
    assert all(allowed.match(href) for href in hrefs), sorted(h for h in hrefs if not allowed.match(h))
