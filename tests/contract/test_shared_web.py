"""A shared viewer reads the same actual snapshot without PC-specific state or POST mutations."""

import http.client
import json
import threading

import pytest

from engine.web.readmodel import WorkbenchReader, load_catalog
from engine.web.server import _when, make_server
from tests.fixtures import web_bundles as wb


class ForbiddenState:
    def latest(self, *args):
        raise AssertionError("shared viewing read PC-specific readiness")

    def list(self, *args):
        raise AssertionError("shared viewing read PC-specific memos")


def context():
    return {
        "snapshot_id": "actual-shared",
        "snapshot_digest": "a" * 64,
        "reviewed_at": "2026-10-19T00:00:00Z",
        "missing_records": [],
        "target": {"target_version": "frozen", "target_commit": "a" * 7},
    }


def test_shared_time_is_fixed_to_korea_regardless_of_host_timezone():
    assert _when("2026-10-19T00:00:00Z", shared=True) == "2026-10-19 09:00"


def test_reader_ignores_local_state_and_fixes_context(tmp_path):
    built = wb.spec004_run(tmp_path / "actual", "E-02")
    reader = WorkbenchReader(
        load_catalog(),
        built.bundle.parent,
        readiness=ForbiddenState(),
        memos=ForbiddenState(),
        shared_snapshot=context(),
    )
    first, second = reader.workbench(), reader.workbench()
    assert first == second
    assert first["generated_at"] == context()["reviewed_at"]
    assert first["target"]["target_commit"] == "a" * 7
    assert reader.scenario("E-02")["readiness"]["source"] == "NONE"
    view = reader.run(built.run_id)
    assert not view["memo_allowed"] and view["memos"] == []
    assert view["verdict"]["value"] == built.verdict
    assert view["run"]["record_role"] == "SHARED_HISTORY"


@pytest.mark.parametrize("path", ["/preflight", "/runs/00000000-0000-4000-8000-000000000000/memos"])
def test_shared_post_is_forbidden_before_any_local_work(tmp_path, path):
    instance = make_server(
        0,
        run_root=tmp_path / "actual",
        demo_root=tmp_path / "demo",
        state_dir=tmp_path / "state",
        shared_snapshot=context(),
    )
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    try:
        client = http.client.HTTPConnection("127.0.0.1", instance.server_address[1], timeout=10)
        client.request("POST", path, body="")
        response = client.getresponse()
        payload = json.loads(response.read())
        assert response.status == 403 and payload["code"] == "SHARED_READ_ONLY"
        assert not (tmp_path / "state").exists()
        client.close()
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join(5)
