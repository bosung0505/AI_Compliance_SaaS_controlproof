"""Shared browser-test fixtures for the US2/US3 screens: one DEMO site and one browser per test module (a sync Playwright instance must close before the next starts).

Playwright's bundled Chromium is used when installed, otherwise the installed Edge or Chrome channel (R-014). The server
runs in a thread of the test process and is shut down at the end.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from engine.web import server
from scripts import prepare_web_demo


def find_run(demo_root: Path, scenario_id: str, *, verdict=None, state=None, valid=True) -> str:
    from engine.evidence import verify_bundle

    for directory in sorted(demo_root.iterdir()):
        if not (directory / "manifest.json").is_file():
            continue
        run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
        judgement = json.loads((directory / "judgement.json").read_text(encoding="utf-8"))
        if run["scenario_id"] != scenario_id:
            continue
        if verdict and judgement["verdict"] != verdict or state and run["state"] != state:
            continue
        if (verify_bundle(directory, require_all_evidence=False)["bundle_status"] == "VERIFIED") != valid:
            continue
        return directory.name
    raise LookupError(f"no DEMO run for {scenario_id} {verdict} {state} valid={valid}")


@pytest.fixture(scope="module")
def demo_site(tmp_path_factory):
    base = tmp_path_factory.mktemp("web-us2")
    demo_root = base / "web-demo" / "runs"
    assert prepare_web_demo.main(["--demo-root", str(demo_root)]) == 0
    instance = server.make_server(0, run_root=base / "runs", demo_root=demo_root, state_dir=base / "web")
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield SimpleNamespace(url=f"http://127.0.0.1:{instance.server_address[1]}", demo_root=demo_root, base=base)
    instance.shutdown()
    instance.server_close()
    thread.join(5)


@pytest.fixture(scope="module")
def web_browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as playwright:
        launched, failures = None, []
        for options in ({}, {"channel": "msedge"}, {"channel": "chrome"}):
            try:
                launched = playwright.chromium.launch(**options)
            except Exception as exc:  # noqa: BLE001 - try the next installed browser
                failures.append(f"{options.get('channel', 'chromium')}: {type(exc).__name__}")
            else:
                print(f"browser: {options.get('channel', 'chromium')} {launched.version}")
                break
        if launched is None:
            pytest.skip(f"no Playwright Chromium, Edge or Chrome browser installed ({'; '.join(failures)})")
        yield launched
        launched.close()


@pytest.fixture(params=(1280, 1024), ids=lambda width: f"{width}px")
def screen(request, web_browser, demo_site):
    """A page at the given width that fails the test on any console error or horizontal overflow."""
    context = web_browser.new_context(viewport={"width": request.param, "height": 900})
    page = context.new_page()
    errors = []
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: errors.append(str(error)))
    yield page
    assert errors == []
    context.close()


def no_overflow(page) -> bool:
    return page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
