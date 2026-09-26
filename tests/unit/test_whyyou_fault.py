from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx

from engine.adapters.whyyou.client import WhyYouClient
from engine.adapters.whyyou.fault import WhyYouFaultAdapter
from engine.config import Settings


def _adapter(tmp_path, *, report_status=202, health_status=200):
    def handler(request):
        if request.url.path == "/health":
            return httpx.Response(health_status)
        return httpx.Response(report_status, json={"status": "queued"})

    settings = Settings.from_env(
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
    client = WhyYouClient(settings, transport=httpx.MockTransport(handler))
    return WhyYouFaultAdapter(settings, client)


def test_apply_probe_and_idempotent_restore(tmp_path):
    adapter = _adapter(tmp_path)
    run_id = str(uuid4())
    session_id = str(uuid4())
    subject = {"interview_session_id": session_id}
    applied = adapter.apply(
        run_id=run_id,
        subject=subject,
        expires_at=datetime.now(UTC) + timedelta(minutes=2),
    )
    assert applied.ok
    receipt = {
        "run_id": run_id,
        "session_id": session_id,
        "outbox_event_id": "event-1",
        "fault_type": "reporting_handler_timeout_v1",
    }
    path = adapter.receipt_path(run_id)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    effect = adapter.probe_effect(
        run_id=run_id,
        subject=subject,
        trigger={"outbox_event_id": "event-1"},
    )
    assert effect.ok
    first = adapter.restore(run_id=run_id, subject=subject)
    second = adapter.restore(run_id=run_id, subject=subject)
    assert first.ok and second.ok
    assert first.data["environment_restore"] == "SUCCEEDED"
    assert first.data["report_processing_recovery"] == "TIMEOUT"


def test_wrong_session_receipt_and_restore_uncertainty_are_not_success(tmp_path):
    adapter = _adapter(tmp_path, health_status=503)
    run_id = str(uuid4())
    session_id = str(uuid4())
    subject = {"interview_session_id": session_id}
    path = adapter.receipt_path(run_id)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "session_id": str(uuid4()),
                "outbox_event_id": "event-1",
                "fault_type": "reporting_handler_timeout_v1",
            }
        ),
        encoding="utf-8",
    )
    assert not adapter.probe_effect(
        run_id=run_id,
        subject=subject,
        trigger={"outbox_event_id": "event-1"},
    ).ok
    restored = adapter.restore(run_id=run_id, subject=subject)
    assert not restored.ok
    assert restored.data["environment_restore"] == "FAILED"
