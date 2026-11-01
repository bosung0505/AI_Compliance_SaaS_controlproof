"""2026-11-01 homepage (Spec010 T038/T039): the supplied standalone export, served by the real handlers.

The export embedded its CSS/JS/logo and linked to a local server on port 8767. In the repository the same markup uses
`/static/` assets (CSP default-src 'self') and relative links. Counts and per-control labels come from the catalog;
the remaining narrative copy is static, so the facts it states are pinned against the catalog below.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from engine.web import server
from engine.web.public import public_view
from engine.web.readmodel import load_catalog
from tests.contract.test_platform_detail_pages import request
from tests.contract.test_platform_public_pages import Markup

ROOT = Path(__file__).parents[2]
LOGO = ROOT / "engine/web/static/controlproof-logo.png"
# Bytes of the logo embedded in `ControlProof_홈페이지.html` (2172x724 RGBA), stored unchanged.
LOGO_SHA256 = "546482e47812089def9c5e6798d83ee856774af18e2a075b2546948bb40dcaf4"
N02_FINAL = "16dbd987-23a5-4030-bb62-77787488969b"


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    snapshot = json.loads((ROOT / "review-data/snapshot.json").read_text(encoding="utf-8"))
    state = tmp_path_factory.mktemp("homepage")
    instance = server.make_server(
        0, run_root=ROOT / "review-data/bundles", demo_root=state / "demo/runs",
        state_dir=state / "state", shared_snapshot=snapshot,
    )
    yield instance
    instance.server_close()


def html(site, path):
    body, _ = request(site, path)
    return body.decode("utf-8")


def test_logo_is_the_supplied_png_served_only_through_the_static_allowlist(site):
    body, headers = request(site, "/static/controlproof-logo.png")
    assert headers["Content-Type"] == "image/png"
    assert body == LOGO.read_bytes() and body.startswith(b"\x89PNG\r\n\x1a\n")
    assert hashlib.sha256(body).hexdigest() == LOGO_SHA256
    assert headers["Content-Security-Policy"] == "default-src 'self'; script-src 'self'; style-src 'self'"
    for name in ("CONTROLPROOF-logo.png", "controlproof-logo.PNG", "controlproof-logo.svg", "missing.png", "..%2Fserver.py"):
        request(site, f"/static/{name}", expected=404)
    # The static folder holds no other image; reviewed evidence PNGs keep their strict content endpoint.
    assert sorted(path.name for path in LOGO.parent.glob("*.png")) == ["controlproof-logo.png"]


@pytest.mark.parametrize("path", ["/product", "/guide"])
def test_public_header_has_five_closed_disclosures_and_no_export_leftovers(site, path):
    body = html(site, path)
    header = re.search(r'<header class="header explore-header">.*?</header>', body, re.DOTALL).group()
    tags = Markup(header).tags
    triggers = [attrs for tag, attrs in tags if tag == "button" and attrs.get("class") == "nav-trigger"]
    panels = {attrs["id"]: attrs for tag, attrs in tags if tag == "div" and attrs.get("class") == "nav-panel"}
    assert [t["aria-controls"] for t in triggers] == [f"nav-panel-{i}" for i in range(1, 6)]
    assert all(t["aria-expanded"] == "false" for t in triggers)
    for trigger in triggers:
        panel = panels[trigger["aria-controls"]]
        assert "inert" in panel and panel["aria-labelledby"] == trigger["id"]
    assert 'aria-controls="primary-navigation"' in header
    images = [attrs for tag, attrs in Markup(body).tags if tag == "img"]
    assert len(images) == 2
    assert all(a["src"] == "/static/controlproof-logo.png" and a["alt"] == "ControlProof" for a in images)
    for leftover in ("127.0.0.1", ":8767", "data:image", "codex-browser", "<style"):
        assert leftover not in body
    assert ('aria-current="page"' in header) == (path == "/guide")


def test_every_public_link_is_relative_and_resolves_to_a_get_route(site):
    targets = set()
    for page in ("/product", "/guide"):
        for tag, attrs in Markup(html(site, page)).tags:
            href = attrs.get("href") if tag == "a" else None
            if not href or href.startswith("#"):
                continue
            parts = urlsplit(href)
            assert not parts.scheme and not parts.netloc and href.startswith("/"), href
            targets.add(parts.path + (f"?{parts.query}" if parts.query else ""))
    assert {"/results?control=N", "/results?control=A", f"/runs/{N02_FINAL}", "/demo/", "/report", "/prepare"} <= targets
    for target in sorted(targets):
        request(site, target)


def test_counts_and_control_labels_come_from_the_catalog(site):
    body = html(site, "/product")
    labels = re.findall(
        r'<span class="domain-code">([NHAE])</span>.*?<small( class="unavailable-label")?>([^<]+)</small>',
        body, re.DOTALL,
    )
    assert labels == [
        ("N", "", "3개 실행 · N-03 일부 범위"),
        ("H", "", "3개 실행"),
        ("A", ' class="unavailable-label"', "3개 대상 기능 없음"),
        ("E", "", "3개 실행"),
    ]
    assert body.count('data-coverage="EXECUTED">9<') == 2
    assert body.count('data-coverage="NO_TEST_TARGET">3<') == 2
    assert "관리 시나리오 12개 중 9개에 실행 기록이 있습니다." in body


def test_static_homepage_copy_still_matches_the_catalog_facts():
    """Fails when a fact the static copy states changes in the catalog, so the copy is reviewed with it."""
    catalog = load_catalog()
    by_id = {entry["id"]: entry for entry in catalog["scenarios"]}
    view = public_view(catalog, {})
    assert [scenario for domain in view["domains"].values() for scenario in domain["partial"]] == ["N-03"]
    assert sorted(key for key, e in by_id.items() if e["mvp_treatment"] == "NO_TEST_TARGET") == ["A-01", "A-02", "A-03"]
    for scenario_id in ("N-02", "H-01", "E-01"):
        assert by_id[scenario_id]["official_status"]["result"] == "PASS"
    finals = [r["run_id"] for r in by_id["N-02"]["official_status"]["records"] if r["role"] == "final"]
    assert finals == [N02_FINAL]


def test_feature_preview_tabs_start_on_the_first_panel(site):
    tags = Markup(html(site, "/product")).tags
    tabs = [attrs for _, attrs in tags if attrs.get("role") == "tab"]
    panels = {attrs["id"]: attrs for _, attrs in tags if attrs.get("role") == "tabpanel"}
    assert [t["aria-controls"] for t in tabs] == ["feature-screen-0", "feature-screen-1", "feature-screen-2"]
    assert [t["aria-selected"] for t in tabs] == ["true", "false", "false"]
    assert [t["tabindex"] for t in tabs] == ["0", "-1", "-1"]
    assert ["hidden" in panels[t["aria-controls"]] for t in tabs] == [False, True, True]


HEADER = re.compile(r'<header class="header explore-header">.*?</header>', re.DOTALL)
FOOTER = re.compile(r'<footer class="footer wrap">.*?</footer>', re.DOTALL)
WORKSPACE_PAGES = [
    ("/", 200), ("/results", 200), ("/prepare", 200), ("/report", 200), ("/scenarios/N-03", 200),
    (f"/runs/{N02_FINAL}", 200), (f"/runs/{N02_FINAL}/evidence", 404), ("/compare/d3aac7d9-0a52-4f9a-9c8f-f6e1f7b6de18", 200),
    ("/demo/", 200), ("/demo/results", 200), ("/scenarios/N-99", 404),
]


@pytest.mark.parametrize("path,status", WORKSPACE_PAGES)
def test_workspace_pages_share_the_homepage_header_and_footer(site, path, status):
    """Same partials as /product: only the menu id differs (the sidebar keeps primary-navigation) and the logo is the h1."""
    body = request(site, path, expected=status)[0].decode("utf-8")
    product = html(site, "/product")
    headers = HEADER.findall(body)
    assert len(headers) == 1 and "workspace-mark" not in body and "workspace-brand" not in body
    header = headers[0]
    assert '<h1 class="brand-heading"><a class="brand" href="/product"><span class="cp-logo">' in header
    assert 'id="site-navigation"' in header and 'aria-controls="site-navigation"' in header
    normalized = header.replace("site-navigation", "primary-navigation")
    normalized = normalized.replace('<h1 class="brand-heading">', "").replace("</a></h1>", "</a>")
    assert normalized == HEADER.search(product).group()
    assert FOOTER.findall(body) == FOOTER.findall(product)
    assert body.index('<div class="workspace-top">') < body.index(header) < body.index('<div class="workspace-frame">')
    assert ('class="demo-banner"' in body) == path.startswith("/demo/")
    if path.startswith("/demo/"):
        assert body.index('<div class="workspace-top">') < body.index('class="demo-banner"') < body.index(header)
    sidebar = re.search(r'<nav class="workspace-nav" id="primary-navigation".*?</nav>', body, re.DOTALL).group()
    assert sidebar.count("<a ") == 5 and 'aria-controls="primary-navigation"' in body
    for asset in ("/static/explore-workspace.css", "/static/navigation.js", "/static/platform.js"):
        assert asset in body
