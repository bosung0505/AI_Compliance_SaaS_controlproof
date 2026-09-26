from __future__ import annotations

import httpx
import pytest

import engine.adapters.whyyou.client as client_module
from engine.adapters.whyyou.client import TargetSnapshotCaptureError, WhyYouClient
from engine.config import Settings


def _settings(tmp_path) -> Settings:
    return Settings.from_env(
        {
            "WHYYOU_BASE_URL": "http://localhost:8000",
            "WHYYOU_CONSOLE_URL": "http://localhost:5173",
            "WHYYOU_DATABASE_URL": "postgresql+psycopg://local:local@localhost/test",
            "WHYYOU_COMPANY_TOKEN": "local-test-token",
            "WHYYOU_REPO_PATH": str(tmp_path),
            "CONTROLPROOF_FAULT_ROOT": str(tmp_path / "faults"),
            "CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED": "true",
            "CONTROLPROOF_MODEL_FIXTURE_ID": "h03-report-v1",
            "CONTROLPROOF_MODEL_FIXTURE_DIGEST": (
                "ce09b95403b34e1390502c90f5c5edc518ddf65d38c8ce881617a37cac6d16b1"
            ),
        }
    )


def _client(tmp_path, handler) -> WhyYouClient:
    return WhyYouClient(_settings(tmp_path), transport=httpx.MockTransport(handler))


@pytest.mark.parametrize(
    "status,body,presence,normalized",
    [
        (200, {"status": "ready"}, "PRESENT", "ready"),
        (202, {"status": "queued"}, "ABSENT", "queued"),
        (404, {}, "ABSENT", None),
        (403, {"detail": "no"}, "UNAVAILABLE", None),
        (503, {}, "UNAVAILABLE", None),
    ],
)
def test_report_status_normalization(tmp_path, status, body, presence, normalized):
    client = _client(tmp_path, lambda request: httpx.Response(status, json=body))
    result = client.report_status("session")
    assert result["presence"] == presence
    assert result.get("status") == normalized
    assert "authorization" not in str(result).casefold()


def test_company_bearer_is_sent_but_never_captured(tmp_path):
    def handler(request):
        assert request.headers["authorization"] == "Bearer local-test-token"
        return httpx.Response(202, json={"status": "queued"})

    result = _client(tmp_path, handler).report_status("session")
    assert "local-test-token" not in str(result)


@pytest.mark.parametrize(
    "status,body,accepted,reason",
    [
        (409, {"code": "REPORT_NOT_AVAILABLE"}, False, True),
        (409, {"detail": "report is not ready"}, False, True),
        (404, {"detail": "not found"}, False, False),
        (201, {}, True, False),
    ],
)
def test_final_decision_reason_must_come_from_target(
    tmp_path,
    status,
    body,
    accepted,
    reason,
):
    client = _client(tmp_path, lambda request: httpx.Response(status, json=body))
    result = client.attempt_final_decision(
        "invitation",
        recruiting_stage_id="stage",
        expected_pipeline_version=1,
        idempotency_key="controlproof-test-key",
    )
    assert result["accepted"] is accepted
    assert result["reason_present"] is reason
    assert result["reason_code"] == ("REPORT_NOT_AVAILABLE" if reason else None)


def test_clean_and_dirty_git_snapshots_are_canonical(tmp_path, monkeypatch):
    monkeypatch.setattr(client_module, "_git", lambda *_args: "a" * 40)
    monkeypatch.setattr(client_module, "_migration_head", lambda _repo: "head-v1")
    monkeypatch.setattr(client_module, "_git_bytes", lambda *_args: b"")
    client = _client(tmp_path, lambda request: httpx.Response(200, json={"paths": {}}))
    snapshot = client.capture_target_snapshot()
    assert snapshot.target_version.startswith("target-snapshot:sha256:")
    assert snapshot.git_dirty is False

    dirty_file = tmp_path / "dirty.txt"
    dirty_file.write_text("changed", encoding="utf-8")
    monkeypatch.setattr(
        client_module,
        "_git_bytes",
        lambda *_args: b"?? dirty.txt\0",
    )
    with pytest.raises(TargetSnapshotCaptureError) as caught:
        client.capture_target_snapshot()
    assert caught.value.diagnostic is not None
    assert caught.value.diagnostic.git_dirty is True
    assert caught.value.diagnostic.git_diff_digest
