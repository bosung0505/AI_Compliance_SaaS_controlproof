"""Stage 0/1 baseline and EXISTING handler checks; NOT implementation of future UI contracts.

Dispatch checks call the existing server in process: they do not test a browser or HTTP socket transport.
Future COV/HTTP/IMG cases are prepared data and are not counted as behavior passes here.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
from collections import Counter
from pathlib import Path

import pytest
import yaml

from engine.shared_records import load_snapshot
from engine.web import server

REPO = Path(__file__).resolve().parents[3]
FEATURE = REPO / "specs/010-platform-ui-integration"
BASELINE = json.loads((FEATURE / "baseline.json").read_text(encoding="utf-8"))


def test_sealed_inventory_and_current_catalog_match_frozen_baseline():
    snapshot = json.loads((REPO / BASELINE["snapshot"]["path"]).read_text(encoding="utf-8"))
    inventory = {
        f"{record['run_id']}/{name}": digest
        for record in snapshot["records"] for name, digest in record["files"].items()
    }
    actual = {
        p.relative_to(REPO / "review-data/bundles").as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (REPO / "review-data/bundles").rglob("*") if p.is_file()
    }
    assert actual == inventory
    canonical = json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical).hexdigest() == BASELINE["snapshot"]["inventory_canonical_sha256"]
    assert len(actual) == 652 and len(snapshot["records"]) == 28
    assert Counter(r["verification"]["bundle_status"] for r in snapshot["records"]) == {
        "VERIFIED": 27, "INVALID": 1,
    }
    catalog = yaml.safe_load((REPO / "catalog/mvp-scenarios.yaml").read_text(encoding="utf-8"))
    assert Counter(s["mvp_treatment"] for s in catalog["scenarios"]) == {"EXECUTED": 9, "NO_TEST_TARGET": 3}
    assert sum(len(s["profiles"]) for s in catalog["scenarios"]) == 11


def test_design_archive_matches_frozen_source_hashes():
    directory = REPO / BASELINE["design_archive_local"]
    if not directory.is_dir():
        pytest.skip("Local-only supplied design archive is not present in this checkout")
    for name, entry in BASELINE["design_files"].items():
        payload = (directory / name).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == entry["sha256"]
        assert len(payload) == entry["size_bytes"]


def test_prepared_case_files_have_unique_ids_and_current_case_matches_catalog():
    coverage = json.loads((FEATURE / "contracts/coverage-cases.json").read_text(encoding="utf-8"))
    http = json.loads((FEATURE / "contracts/http-cases.json").read_text(encoding="utf-8"))
    assert len(coverage["cases"]) == 18 and len(http["cases"]) == 65
    ids = [c["case_id"] for c in coverage["cases"]] + [c["id"] for c in http["cases"]]
    assert len(ids) == len(set(ids)) == 83
    for case in http["cases"]:
        assert {"request", "expected", "coverage"} <= case.keys()
    current = next(c for c in coverage["cases"] if c["case_id"] == "COV-01")
    catalog = yaml.safe_load((REPO / "catalog/mvp-scenarios.yaml").read_text(encoding="utf-8"))
    actual = {s["id"]: s for s in catalog["scenarios"]}
    assert len(current["input"]["scenarios"]) == len(actual) == 12
    for row in current["input"]["scenarios"]:
        source = actual[row["id"]]
        assert row["mvp_treatment"] == source["mvp_treatment"]
        assert row["official"]["result"] == source["official_status"]["result"]


class CaptureHandler(server._Handler):
    """Exercise real dispatch/routes/redaction with output captured before socket transport."""

    def __init__(self, site, path, *, method="GET", host=None, body=b""):
        self.server = site
        self.path = path
        self.command = method
        self.headers = {
            "Host": host or f"127.0.0.1:{site.server_address[1]}",
            "Content-Length": str(len(body)),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        self.rfile = io.BytesIO(body)
        self.captured = None

    def _send(self, status, body, content_type):
        self.captured = (int(status), body, content_type)


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    directory = tmp_path_factory.mktemp("ui-contract-baseline")
    snapshot_path = REPO / os.environ.get("CONTROLPROOF_UI_TEST_SNAPSHOT", "review-data/snapshot.json")
    snapshot = load_snapshot(snapshot_path)
    instance = server.make_server(
        0, run_root=snapshot_path.parent / "bundles", demo_root=directory / "demo/runs",
        state_dir=directory / "state", shared_snapshot=snapshot,
    )
    yield instance
    instance.server_close()


def request(site, path, *, expected=200, **kwargs):
    handler = CaptureHandler(site, path, **kwargs)
    handler._dispatch(handler.command)
    status, body, content_type = handler.captured
    assert status == expected, (path, status, body[:150])
    return json.loads(body) if content_type.startswith("application/json") else body


def test_existing_workbench_and_scenario_api_contract(site):
    data = request(site, "/api/workbench")
    assert data["schema_version"] == "controlproof.web.v1"
    assert data["treatment_counts"].get("NOT_RUN", 0) == 0
    assert data["treatment_counts"]["EXECUTED"] == 9
    assert data["counts"]["PASS"] == 9
    assert data["shared_snapshot"]["snapshot_id"] == site.readers["ACTUAL"].shared_snapshot["snapshot_id"]
    n03 = request(site, "/api/scenarios/N-03")
    assert n03["target_access"] == "API" and len(n03["scope_items"]) == 4
    n01 = request(site, "/api/scenarios/N-01")
    assert n01["target_access"] == "화면 + API"


def test_existing_run_compare_report_api_contract(site):
    child = "d3aac7d9-0a52-4f9a-9c8f-f6e1f7b6de18"
    data = request(site, f"/api/runs/{child}")
    assert data["verdict"]["value"] == "PASS"
    assert data["memo_allowed"] is False
    n03 = request(site, "/api/runs/f27b68e8-0df8-46b3-a198-c7917c2f08bb")
    assert len(n03["scope_items"]) == 4
    compare = request(site, f"/api/compare/{child}")
    assert compare["lineage_problem"] is None and compare["parent_unchanged"] is True
    report = request(site, "/api/report")
    assert len(report["items_present"]) == 22 and all(report["items_present"].values())


def test_existing_error_and_readonly_dispatch_boundaries(site):
    assert request(site, "/api/scenarios/N-99", expected=404)["code"] == "SCENARIO_NOT_FOUND"
    assert request(site, "/api/workbench", expected=421, host="invalid.example")["code"] == "HOST_NOT_ALLOWED"
    assert request(site, "/preflight", method="POST", body=b"csrf_token=invalid", expected=403)["code"] == "SHARED_READ_ONLY"


@pytest.mark.parametrize("path", [
    "/prepare",
])
def test_preparation_route_is_read_only_in_shared_mode(site, path):
    html = request(site, path).decode("utf-8")
    assert "service-prepare" in html and "<form" not in html
