from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx

from engine.adapters.whyyou.client import WhyYouClient
from engine.adapters.whyyou.fault import WhyYouFaultAdapter
from engine.config import Settings
from engine.models import FaultBoundary, FaultBoundaryReceipt, FaultVariant


def _adapter(tmp_path) -> WhyYouFaultAdapter:
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
            "CONTROLPROOF_MODEL_FIXTURE_DIGEST": "a" * 64,
        }
    )
    client = WhyYouClient(
        settings,
        transport=httpx.MockTransport(lambda _request: httpx.Response(200)),
    )
    return WhyYouFaultAdapter(settings, client)


def _after_boundary(run_id: str, session_id: str, event_id: str, **updates):
    return {
        "schema_version": "controlproof.whyyou-fault-receipt.v2",
        "run_id": run_id,
        "session_id": session_id,
        "outbox_event_id": event_id,
        "delivery_attempt": 1,
        "fault_variant": "AFTER_RESULT_DURABLE_BEFORE_COMPLETION",
        "boundary": "AFTER_DB_COMMIT_BEFORE_SQS_ACK",
        "triggered_at": datetime.now(UTC).isoformat(),
        "one_shot_consumed": True,
        **updates,
    }


def test_after_marker_is_one_shot_and_marker_write_is_not_boundary_proof(tmp_path):
    adapter = _adapter(tmp_path)
    run_id, session_id, event_id = (str(uuid4()), str(uuid4()), str(uuid4()))
    subject = {"interview_session_id": session_id}

    applied = adapter.apply_after(
        run_id=run_id,
        subject=subject,
        expires_at=datetime.now(UTC) + timedelta(minutes=2),
    )

    assert applied.ok
    assert applied.data["marker"]["one_shot"] is True
    assert applied.data["marker"]["fault_type"] == "reporting_after_commit_drop_ack_v1"
    missing = adapter.read_boundary_receipt(
        run_id=run_id,
        source_event_id=event_id,
        fault_variant="AFTER_RESULT_DURABLE_BEFORE_COMPLETION",
        session_id=session_id,
    )
    assert not missing.ok
    assert not adapter.read_duplicate_ack(
        run_id=run_id,
        source_event_id=event_id,
    ).ok


def test_after_boundary_rejects_wrong_event_boundary_and_unconsumed_marker(tmp_path):
    adapter = _adapter(tmp_path)
    run_id, session_id, event_id = (str(uuid4()), str(uuid4()), str(uuid4()))
    path = adapter.receipt_path(run_id)
    path.parent.mkdir(parents=True)
    records = [
        _after_boundary(run_id, session_id, str(uuid4())),
        _after_boundary(run_id, session_id, event_id, boundary="BEFORE_REPORT_SIDE_EFFECT"),
        _after_boundary(run_id, session_id, event_id, one_shot_consumed=False),
        _after_boundary(run_id, session_id, event_id),
    ]
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )

    receipt = adapter.read_boundary_receipt(
        run_id=run_id,
        source_event_id=event_id,
        fault_variant="AFTER_RESULT_DURABLE_BEFORE_COMPLETION",
        session_id=session_id,
    )

    assert isinstance(receipt, FaultBoundaryReceipt)
    assert receipt.fault_variant is FaultVariant.AFTER_RESULT_DURABLE_BEFORE_COMPLETION
    assert receipt.boundary is FaultBoundary.AFTER_DB_COMMIT_BEFORE_SQS_ACK
    assert receipt.one_shot_consumed is True

    path.write_text(
        json.dumps(records[-1]) + "\n" + json.dumps(records[-1]) + "\n",
        encoding="utf-8",
    )
    repeated = adapter.read_boundary_receipt(
        run_id=run_id,
        source_event_id=event_id,
        fault_variant="AFTER_RESULT_DURABLE_BEFORE_COMPLETION",
        session_id=session_id,
    )
    assert not repeated.ok
    assert repeated.code == "AFTER_BOUNDARY_REPEATED"


def test_duplicate_ack_requires_same_event_and_sanitized_processed_branch_receipt(tmp_path):
    adapter = _adapter(tmp_path)
    run_id, session_id, event_id = (str(uuid4()), str(uuid4()), str(uuid4()))
    path = adapter.receipt_path(run_id)
    path.parent.mkdir(parents=True)
    wrong = {
        "schema_version": "controlproof.whyyou-duplicate-ack.v1",
        "run_id": run_id,
        "session_id": session_id,
        "outbox_event_id": str(uuid4()),
        "event_version": 1,
        "delivery_attempt": 2,
        "consumer_name": "reporting-worker",
        "handler_skipped": True,
        "acknowledged": True,
        "observed_at": datetime.now(UTC).isoformat(),
    }
    matched = {**wrong, "outbox_event_id": event_id}
    path.write_text(
        json.dumps(wrong) + "\n" + json.dumps(matched) + "\n",
        encoding="utf-8",
    )

    result = adapter.read_duplicate_ack(run_id=run_id, source_event_id=event_id)

    assert result.ok
    assert result.data["receipt"]["handler_skipped"] is True
    assert "payload" not in result.data["receipt"]
