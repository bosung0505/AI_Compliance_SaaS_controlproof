"""T058 — every web route, HTML and JSON, ACTUAL and DEMO, scanned with the strict scanner (FR-031, SC-007).

The ACTUAL root holds every synthetic bundle kind plus a re-sealed copy whose extra file carries an escaped Windows user
path; the DEMO root is built by `scripts/prepare_web_demo.py`. Both roots live under the test's temporary directory
(itself under the user's home on Windows), so any leaked absolute path is caught. 0 violations.
"""

from __future__ import annotations

import http.client
import json
import shutil
import threading
import urllib.parse

import pytest

from engine.evidence import USER_PATH_RE_V2, canonical_json_bytes, scan_bytes_strict, sha256_bytes
from engine.models import InconclusiveReason
from engine.web import server
from engine.web.readmodel import load_catalog
from scripts import prepare_web_demo
from tests.fixtures import web_bundles as wb


def _leaky_copy(built, root):
    target = root / built.run_id
    shutil.copytree(built.bundle, target, dirs_exist_ok=True)
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    manifest.pop("bundle_digest")
    payload = json.dumps({"p": "C:\\Users\\alice\\runs\\abc", "q": "/home/bob/x"}).encode()
    (target / "notes.json").write_bytes(payload)
    manifest["files"].append({"path": "notes.json", "mime_type": "application/json", "size_bytes": len(payload),
                              "sha256": sha256_bytes(payload)})
    manifest["files"].sort(key=lambda record: record["path"])
    manifest["bundle_digest"] = sha256_bytes(canonical_json_bytes(manifest))
    (target / "manifest.json").write_bytes(canonical_json_bytes(manifest))


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    base = tmp_path_factory.mktemp("redaction")
    actual = base / "runs"
    for case in ("pass", "fail", "missing"):
        wb.h03_case(actual, case)
    wb.h03_inconclusive(actual, InconclusiveReason.ACCESS_LIMITED)
    wb.h03_inconclusive(actual, InconclusiveReason.EVIDENCE_CONFLICT)
    wb.h03_aborted(actual)
    wb.h03_lineage(actual)
    wb.e03_lineage(actual)
    wb.e01_lineage(actual)
    wb.spec004_run(actual, "E-02")
    wb.tampered(wb.h03_case(actual, "pass"))
    wb.unreadable(wb.h03_case(actual, "pass"))
    wb.h03_case(actual, "restore_failed")
    side = base / "side"
    _leaky_copy(wb.h03_case(side, "pass"), actual)
    demo = base / "web-demo" / "runs"
    assert prepare_web_demo.main(["--demo-root", str(demo)]) == 0
    instance = server.make_server(0, run_root=actual, demo_root=demo, state_dir=base / "web")
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield {"port": instance.server_address[1], "actual": actual, "demo": demo, "base": base}
    instance.shutdown()
    instance.server_close()
    thread.join(5)


def _get(site, path):
    connection = http.client.HTTPConnection("127.0.0.1", site["port"], timeout=60)
    connection.request("GET", path, headers={"Host": f"127.0.0.1:{site['port']}"})
    response = connection.getresponse()
    data = response.read()
    connection.close()
    return response.status, data


def _paths(site):
    paths = ["/", "/api/workbench", "/report", "/api/report", "/static/workbench.css", "/static/workbench.js", "/nope",
             "/api/nope", "/runs/00000000-0000-4000-8000-000000000000"]
    for entry in load_catalog()["scenarios"]:
        paths += [f"/scenarios/{entry['id']}", f"/api/scenarios/{entry['id']}"]
    runs = []
    for root, prefix in ((site["actual"], ""), (site["demo"], "/demo")):
        if prefix:
            paths += [f"{prefix}/", f"{prefix}/api/workbench", f"{prefix}/report", f"{prefix}/api/report"]
            paths += [f"{prefix}/scenarios/{entry['id']}" for entry in load_catalog()["scenarios"]]
        for directory in sorted(root.iterdir()):
            if (directory / "run.json").is_file():
                runs.append((prefix, directory.name))
    for prefix, run_id in runs:
        paths += [f"{prefix}/runs/{run_id}", f"{prefix}/api/runs/{run_id}", f"{prefix}/compare/{run_id}",
                  f"{prefix}/api/compare/{run_id}"]
    return paths, runs


def test_every_response_passes_the_strict_scan(site) -> None:
    paths, runs = _paths(site)
    violations, statuses = [], {}
    for path in paths:
        status, data = _get(site, path)
        statuses[status] = statuses.get(status, 0) + 1
        findings = scan_bytes_strict(data)
        if findings or USER_PATH_RE_V2.search(data.decode("utf-8", errors="ignore")):
            violations.append((path, findings))
        if path.startswith(("/api/runs/", "/demo/api/runs/")) and status == 200:
            view = json.loads(data)
            for item in view.get("evidence") or []:
                evidence_path = path.replace("/api", "", 1) + "/evidence?ref=" + urllib.parse.quote(item["ref"])
                ev_status, ev_data = _get(site, evidence_path)
                statuses[ev_status] = statuses.get(ev_status, 0) + 1
                if scan_bytes_strict(ev_data) or USER_PATH_RE_V2.search(ev_data.decode("utf-8", errors="ignore")):
                    violations.append((evidence_path, scan_bytes_strict(ev_data)))
    base = str(site["base"])
    assert violations == []
    assert statuses.get(200, 0) > 200 and len(runs) > 20
    print(f"responses scanned: {sum(statuses.values())} {statuses}")
    status, data = _get(site, "/api/workbench")
    assert base not in data.decode("utf-8") and base.replace("\\", "\\\\") not in data.decode("utf-8")


def test_leaky_evidence_is_not_shown(site) -> None:
    run_id = next(
        directory.name for directory in site["actual"].iterdir() if (directory / "notes.json").is_file()
    )
    status, data = _get(site, f"/runs/{run_id}/evidence?ref=file%3Anotes.json")
    text = data.decode("utf-8")
    assert status == 200 and "alice" not in text and "bob" not in text and "원문을 보이지 않습니다" in text
