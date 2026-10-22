"""Spec010 stage2: real server handlers, public pages and shell; no target execution."""

from __future__ import annotations

import copy
import io
import json
from html.parser import HTMLParser

import pytest

from engine.web import server
from engine.web.readmodel import load_catalog


class Capture(server._Handler):
    def __init__(self, site, path, *, method="GET", host=None):
        self.server, self.path, self.command = site, path, method
        self.headers = {"Host": host or f"127.0.0.1:{site.server_address[1]}", "Content-Length": "0"}
        self.rfile = io.BytesIO()

    def _send(self, status, body, content_type):
        self.response = (int(status), body.decode("utf-8"), content_type)


@pytest.fixture
def site(tmp_path):
    instance = server.make_server(
        0, run_root=tmp_path / "runs", demo_root=tmp_path / "demo/runs",
        state_dir=tmp_path / "state", catalog=copy.deepcopy(load_catalog()),
    )
    yield instance
    instance.server_close()


def page(site, path, *, expected=200, **kwargs):
    handler = Capture(site, path, **kwargs)
    handler._dispatch(handler.command)
    status, body, _ = handler.response
    assert status == expected, (path, status, body[:100])
    return body


class Markup(HTMLParser):
    def __init__(self, body):
        super().__init__()
        self.tags = []
        self.feed(body)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


@pytest.mark.parametrize("path", ["/product", "/guide"])
def test_public_routes_do_not_inspect_runs_or_readiness(site, monkeypatch, path):
    def forbidden(*args, **kwargs):
        raise AssertionError("Public pages must not read Run bundles or PC readiness")
    monkeypatch.setattr(site.readers["ACTUAL"], "workbench", forbidden)
    monkeypatch.setattr(site.readers["ACTUAL"], "scenario", forbidden)
    body = page(site, path)
    assert "ControlProof" in body and 'href="/"' in body and 'href="/demo/"' in body
    assert "workspace.html" not in body and "site.css" not in body
    assert 'href="/product"' in body and 'href="/guide"' in body


def test_intro_uses_catalog_coverage_and_keeps_partial_scope(site):
    body = page(site, "/product")
    assert 'data-coverage="EXECUTED">9<' in body
    assert 'data-coverage="NOT_RUN">0<' in body
    assert 'data-coverage="NO_TEST_TARGET">3<' in body
    assert "N-03" in body and "일부" in body and "법적" in body
    assert "실제 원본 증적은 연결되지 않았습니다" not in body
    entry = next(e for e in site.catalog["scenarios"] if e["id"] == "N-01")
    entry["mvp_treatment"] = "NOT_RUN"
    assert 'data-coverage="EXECUTED">8<' in page(site, "/product")


def test_guide_has_nine_local_only_checks_and_no_post_form(site):
    body = page(site, "/guide")
    tags = Markup(body).tags
    assert sum(tag == "input" and attrs.get("type") == "checkbox" for tag, attrs in tags) == 9
    assert not any(tag == "form" for tag, _ in tags)
    assert 'id="download-guide"' in body
    assert "서버에 전송되지" in body and "실행 승인" in body
    assert "원본 자료 연결은 포함하지 않습니다" not in body


@pytest.mark.parametrize("path", ["/product", "/guide", "/"])
def test_pages_use_only_external_self_assets_and_no_inline_handlers(site, path):
    tags = Markup(page(site, path)).tags
    assert not any(tag == "style" or "style" in attrs or any(k.startswith("on") for k in attrs) for tag, attrs in tags)
    scripts = [attrs for tag, attrs in tags if tag == "script"]
    assert scripts and all(attrs.get("src", "").startswith("/static/") for attrs in scripts)
    for tag, attrs in tags:
        asset = attrs.get("src") if tag == "script" else attrs.get("href") if tag == "link" else None
        if asset:
            assert asset.startswith("/static/")
            page(site, asset)
    assert server.SECURITY_HEADERS["Content-Security-Policy"] == "default-src 'self'; script-src 'self'; style-src 'self'"


def test_common_shell_preserves_context_and_existing_navigation(site):
    body = page(site, "/")
    assert 'class="workspace-shell"' in body
    assert 'href="/product"' in body and 'href="/guide"' in body
    assert 'id="primary-navigation"' in body and 'aria-controls="primary-navigation"' in body
    assert "LOCAL_EMULATED" in body and "NOT_RUN" in body
    assert 'data-coverage="NOT_RUN">0<' in body
    assert 'href="/report"' in body and 'href="/#catalog"' in body
    demo = page(site, "/demo/")
    assert "DEMO DATA" in demo and 'href="/demo/report"' in demo


def test_public_routes_keep_host_and_shared_post_boundaries(site):
    assert "HOST_NOT_ALLOWED" in page(site, "/product", host="invalid.example", expected=421)
    site.readers["ACTUAL"].shared_snapshot = {"snapshot_id": "isolated-test-context"}
    error = json.loads(page(site, "/preflight", method="POST", expected=403))
    assert error["code"] == "SHARED_READ_ONLY"
