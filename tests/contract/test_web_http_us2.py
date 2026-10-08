"""US2/US3 HTTP routes (contracts/web-http.md): run, evidence (422 on integrity failure), memos, report. Part of T036/T040."""

from __future__ import annotations

import hashlib
import http.client
import json
import threading
import urllib.parse
from types import SimpleNamespace

import pytest

from engine.evidence import USER_PATH_RE_V2, verify_bundle
from engine.web import server
from tests.fixtures import web_bundles as wb


def _tree(root):
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@pytest.fixture
def web(tmp_path):
    run_root = tmp_path / "runs"
    good = wb.spec004_run(run_root, "E-01")
    bad = wb.h03_case(run_root, "pass")
    wb.tampered(bad)
    instance = server.make_server(0, run_root=run_root, demo_root=tmp_path / "demo", state_dir=tmp_path / "web")
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield SimpleNamespace(server=instance, port=instance.server_address[1], good=good, bad=bad, tmp=tmp_path)
    instance.shutdown()
    instance.server_close()
    thread.join(5)


def _request(web, method, path, body=None):
    connection = http.client.HTTPConnection("127.0.0.1", web.port, timeout=20)
    headers = {"Host": f"127.0.0.1:{web.port}"}
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        body = urllib.parse.urlencode(body)
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    data = response.read()
    connection.close()
    return response, data


def test_run_json_and_html(web) -> None:
    response, data = _request(web, "GET", f"/api/runs/{web.good.run_id}")
    view = json.loads(data)
    assert response.status == 200 and view["view"] == "run" and view["integrity"]["status"] == "VERIFIED"
    assert not USER_PATH_RE_V2.search(data.decode("utf-8")) and str(web.tmp) not in data.decode("utf-8")
    response, data = _request(web, "GET", f"/runs/{web.good.run_id}")
    assert response.status == 200 and "규칙별 결과" in data.decode("utf-8")


def test_integrity_failed_run_is_200_with_failure_screen(web) -> None:
    response, data = _request(web, "GET", f"/runs/{web.bad.run_id}")
    assert response.status == 200
    assert "무결성 실패" in data.decode("utf-8")


def test_evidence_routes(web) -> None:
    ref = urllib.parse.quote("file:report-reads.jsonl")
    response, data = _request(web, "GET", f"/runs/{web.good.run_id}/evidence?ref={ref}")
    assert response.status == 200 and "원문" in data.decode("utf-8")
    response, _ = _request(web, "GET", f"/runs/{web.good.run_id}/evidence?ref=file%3Anope")
    assert response.status == 404
    response, _ = _request(web, "GET", f"/runs/{web.bad.run_id}/evidence?ref={ref}")
    assert response.status == 422
    response, _ = _request(web, "GET", "/runs/00000000-0000-4000-8000-000000000000")
    assert response.status == 404


def test_memo_post_writes_only_under_web_memos(web) -> None:
    before = _tree(web.tmp / "runs")
    verify_before = {k: v for k, v in verify_bundle(web.good.bundle).items() if k != "verified_at"}
    body = {"author": "연우", "text": "수정 요청", "csrf_token": web.server.csrf_token}
    response, _ = _request(web, "POST", f"/runs/{web.good.run_id}/memos", body)
    assert response.status == 303 and response.getheader("Location") == f"/runs/{web.good.run_id}#memos"
    memo_file = web.tmp / "web" / "memos" / f"{web.good.run_id}.jsonl"
    assert json.loads(memo_file.read_text(encoding="utf-8").splitlines()[0])["text"] == "수정 요청"
    assert _tree(web.tmp / "runs") == before
    assert {k: v for k, v in verify_bundle(web.good.bundle).items() if k != "verified_at"} == verify_before
    _, data = _request(web, "GET", f"/api/runs/{web.good.run_id}")
    assert [memo["text"] for memo in json.loads(data)["memos"]] == ["수정 요청"]


def test_memo_post_rejections(web) -> None:
    path = f"/runs/{web.good.run_id}/memos"
    response, _ = _request(web, "POST", path, {"author": "a", "text": "x"})
    assert response.status == 403
    response, data = _request(web, "POST", path, {"author": "a", "text": "x" * 2001, "csrf_token": web.server.csrf_token})
    assert response.status == 400 and json.loads(data)["error_kind"] == "USAGE"
    response, _ = _request(
        web, "POST", "/runs/00000000-0000-4000-8000-000000000000/memos",
        {"author": "a", "text": "x", "csrf_token": web.server.csrf_token},
    )
    assert response.status == 404
    assert not (web.tmp / "web" / "memos").exists() or not any((web.tmp / "web" / "memos").iterdir())


def test_report_routes(web) -> None:
    response, data = _request(web, "GET", "/api/report")
    report = json.loads(data)
    assert response.status == 200 and report["view"] == "report" and all(report["items_present"].values())
    response, data = _request(web, "GET", "/report")
    text = data.decode("utf-8")
    assert response.status == 200 and "12개 검증 완료" not in text
    assert not USER_PATH_RE_V2.search(text)


def test_evidence_names_survive_the_output_boundary(web) -> None:
    """ID-005-08: `display_name` is a redacted personal-data key, so the web names evidence `evidence_name`."""
    _, data = _request(web, "GET", f"/api/runs/{web.good.run_id}")
    names = [item["evidence_name"] for item in json.loads(data)["evidence"]]
    assert names and "[REDACTED]" not in names


def test_no_view_field_is_masked_by_the_boundary(web) -> None:
    """ID-005-08: web field names must not collide with redaction keys (`display_name`, `name`, ...)."""
    for path in ("/api/workbench", "/api/report", f"/api/runs/{web.good.run_id}"):
        _, data = _request(web, "GET", path)
        assert "[REDACTED]" not in data.decode("utf-8"), path
