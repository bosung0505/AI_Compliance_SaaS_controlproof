"""T025 — local web HTTP boundary (contracts/web-http.md; FR-012, FR-031, SC-010, R-002). RED until T031."""

from __future__ import annotations

import http.client
import inspect
import json
import re
import threading
import urllib.parse
from types import SimpleNamespace

import pytest

from engine.evidence import USER_PATH_RE_V2
from engine.web import server
from tests.fixtures import web_bundles as wb

HEADERS = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'",
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
}


class _BlockingRunner:
    def __init__(self) -> None:
        self.started, self.release, self.calls = threading.Event(), threading.Event(), []
        self._lock = threading.Lock()

    def check(self, scenario_id, profile):
        from engine.web.preflight import PreflightBusy

        if not self._lock.acquire(blocking=False):
            raise PreflightBusy()
        try:
            self.calls.append((scenario_id, profile))
            self.started.set()
            self.release.wait(5)
            return {"result_kind": "READINESS", "readiness": "READY"}
        finally:
            self._lock.release()


@pytest.fixture
def web(tmp_path):
    run_root = tmp_path / "runs"
    wb.spec004_run(run_root, "E-02")
    runner = _BlockingRunner()
    instance = server.make_server(
        0, run_root=run_root, demo_root=tmp_path / "demo", state_dir=tmp_path / "web", preflight_runner=runner
    )
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield SimpleNamespace(server=instance, port=instance.server_address[1], runner=runner, tmp=tmp_path)
    runner.release.set()
    instance.shutdown()
    instance.server_close()
    thread.join(5)


def _request(web, method, path, *, host=None, body=None):
    connection = http.client.HTTPConnection("127.0.0.1", web.port, timeout=10)
    headers = {"Host": host or f"127.0.0.1:{web.port}"}
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        body = urllib.parse.urlencode(body)
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    data = response.read()
    connection.close()
    return response, data


def test_bind_address_is_fixed_to_loopback(web) -> None:
    assert web.server.server_address[0] == "127.0.0.1"
    parameters = inspect.signature(server.make_server).parameters
    assert not {"host", "bind", "address"} & set(parameters)


@pytest.mark.parametrize("host", ["evil.example", "evil.example:{port}", "0.0.0.0:{port}"])
def test_foreign_host_is_421(web, host) -> None:
    response, data = _request(web, "GET", "/api/workbench", host=host.format(port=web.port))
    assert response.status == 421
    assert json.loads(data)["error_kind"] == "CONTRACT"


def test_localhost_host_is_accepted(web) -> None:
    response, _ = _request(web, "GET", "/api/workbench", host=f"localhost:{web.port}")
    assert response.status == 200


def test_post_without_or_with_wrong_token_is_403(web) -> None:
    form = {"scenario_id": "E-01", "execution_profile": "E01_CITATION_EVIDENCE_V1"}
    for body in (form, dict(form, csrf_token="wrong")):
        response, data = _request(web, "POST", "/preflight", body=body)
        assert response.status == 403
        assert json.loads(data)["error_kind"] == "CONTRACT"
    assert web.runner.calls == []


def test_unknown_profile_is_400_usage(web) -> None:
    body = {"scenario_id": "A-01", "execution_profile": "X", "csrf_token": web.server.csrf_token}
    response, data = _request(web, "POST", "/preflight", body=body)
    assert response.status == 400
    assert json.loads(data)["error_kind"] == "USAGE"


@pytest.mark.parametrize("path", ["/", "/api/workbench", "/demo/", "/demo/api/workbench", "/static/workbench.css", "/nope"])
def test_security_headers_on_every_response(web, path) -> None:
    response, _ = _request(web, "GET", path)
    for name, value in HEADERS.items():
        assert response.getheader(name) == value, (path, name)


def test_workbench_json_schema_and_boundary(web) -> None:
    response, data = _request(web, "GET", "/api/workbench")
    assert response.status == 200
    assert response.getheader("Content-Type").startswith("application/json")
    view = json.loads(data)
    assert {"schema_version", "view", "generated_at", "environment_kind", "aws_deployment_status", "claim_scope",
            "data_origin", "demo", "target", "readiness_checked_at", "counts", "groups", "retest_needed",
            "preserved_first_failures"} <= set(view)
    assert (view["schema_version"], view["view"], view["data_origin"]) == ("controlproof.web.v1", "workbench", "ACTUAL")
    text = data.decode("utf-8")
    assert not USER_PATH_RE_V2.search(text)
    assert str(web.tmp) not in text and str(web.tmp).replace("\\", "\\\\") not in text
    response, data = _request(web, "GET", "/demo/api/workbench")
    assert (json.loads(data)["data_origin"], json.loads(data)["demo"]) == ("DEMO", True)


def test_html_pages_have_no_absolute_paths(web) -> None:
    for path in ("/", "/demo/"):
        response, data = _request(web, "GET", path)
        assert response.status == 200 and response.getheader("Content-Type").startswith("text/html")
        text = data.decode("utf-8")
        assert not USER_PATH_RE_V2.search(text) and str(web.tmp) not in text
    _, demo = _request(web, "GET", "/demo/")
    assert "DEMO DATA" in demo.decode("utf-8")


def test_not_found_is_json_error(web) -> None:
    response, data = _request(web, "GET", "/api/nope")
    assert response.status == 404
    payload = json.loads(data)
    assert (payload["schema_version"], payload["view"], payload["error_kind"]) == ("controlproof.web.v1", "error", "NOT_FOUND")


def test_route_table_has_no_run_retest_or_cleanup_start(web) -> None:
    routes = [(method, pattern) for method, pattern, _ in server.ROUTES]
    # State-changing routes: the readiness check and fix memos (US2, contracts/web-http.md). Memos are not run actions.
    # Changed expectation (2026-10-09, approved): US1 listed only "/preflight".
    assert [pattern for method, pattern in routes if method == "POST"] == ["/preflight", "/runs/{run_id}/memos"]
    for _method, pattern in routes:
        assert not re.search(r"retest|cleanup|/run$|/run/", pattern), pattern
    for path in ("/run", "/retest", "/cleanup-confirm", "/runs/x/retest"):
        response, _ = _request(web, "POST", path, body={"csrf_token": web.server.csrf_token})
        assert response.status in (404, 405), path


def test_concurrent_preflight_post_is_409(web) -> None:
    body = {"scenario_id": "E-01", "execution_profile": "E01_CITATION_EVIDENCE_V1",
            "csrf_token": web.server.csrf_token, "return_to": "/"}
    first = {}
    worker = threading.Thread(target=lambda: first.update(response=_request(web, "POST", "/preflight", body=body)))
    worker.start()
    assert web.runner.started.wait(5)
    response, data = _request(web, "POST", "/preflight", body=body)
    assert response.status == 409
    assert json.loads(data)["error_kind"] == "BUSY"
    web.runner.release.set()
    worker.join(5)
    assert first["response"][0].status == 303
    assert first["response"][0].getheader("Location") == "/"
