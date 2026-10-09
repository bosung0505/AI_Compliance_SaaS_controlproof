"""T059 — workbench and run screens render within 2 seconds with 30 synthetic bundles, verify cache warm (A-8)."""

from __future__ import annotations

import copy
import http.client
import threading
import time

import pytest

from engine.web import server
from engine.web.readmodel import load_catalog
from tests.fixtures import web_bundles as wb

LIMIT_SECONDS = 2.0


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    base = tmp_path_factory.mktemp("perf")
    root = base / "runs"
    groups = {
        "H-03": [wb.h03_case(root, "pass").run_id for _ in range(10)],
        "E-01": [wb.spec004_run(root, "E-01").run_id for _ in range(10)],
        "E-02": [wb.spec004_run(root, "E-02").run_id for _ in range(10)],
    }
    catalog = copy.deepcopy(load_catalog())
    for entry in catalog["scenarios"]:
        if entry["id"] in groups:  # every bundle is an "official" record, so the workbench verifies all 30
            entry["official_status"]["records"] = [
                {"role": "final", "run_id": run_id, "result": "PASS"} for run_id in groups[entry["id"]]
            ]
    instance = server.make_server(0, run_root=root, demo_root=base / "demo" / "runs", state_dir=base / "web",
                                  catalog=catalog)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield {"port": instance.server_address[1], "runs": [run_id for ids in groups.values() for run_id in ids]}
    instance.shutdown()
    instance.server_close()
    thread.join(5)


def _timed_get(site, path):
    connection = http.client.HTTPConnection("127.0.0.1", site["port"], timeout=60)
    started = time.perf_counter()
    connection.request("GET", path, headers={"Host": f"127.0.0.1:{site['port']}"})
    response = connection.getresponse()
    response.read()
    elapsed = time.perf_counter() - started
    connection.close()
    assert response.status == 200, path
    return elapsed


def test_workbench_and_run_screens_within_two_seconds(site) -> None:
    assert len(site["runs"]) == 30
    _timed_get(site, "/")  # warm the verify cache for all 30 bundles
    workbench = max(_timed_get(site, "/") for _ in range(3))
    runs = [_timed_get(site, f"/runs/{run_id}") for run_id in (site["runs"][0], site["runs"][10], site["runs"][20])]
    _timed_get(site, f"/runs/{site['runs'][10]}")
    warm_run = _timed_get(site, f"/runs/{site['runs'][10]}")
    print(f"workbench warm max {workbench:.3f}s · run first {[round(value, 3) for value in runs]} · run warm {warm_run:.3f}s")
    assert workbench < LIMIT_SECONDS
    assert max(runs) < LIMIT_SECONDS and warm_run < LIMIT_SECONDS
