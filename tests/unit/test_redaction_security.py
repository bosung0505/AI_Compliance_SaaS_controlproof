import json

import pytest

from engine.evidence import REDACTED, EvidenceBundleWriter, redact
from engine.models import canonical_json_bytes


@pytest.mark.parametrize(
    "payload,forbidden",
    [
        ({"Authorization": "Bearer abc.def"}, "abc.def"),
        ({"cookie": "session=secret"}, "session=secret"),
        ({"access_token": "access-secret"}, "access-secret"),
        ({"refresh_token": "refresh-secret"}, "refresh-secret"),
        ({"url": "https://x.test/a?X-Amz-Signature=secret"}, "secret"),
        ({"email": "real.person@example.com"}, "real.person@example.com"),
        ({"applicant_display_name": "홍길동"}, "홍길동"),
        ({"phone": "010-1234-5678"}, "010-1234-5678"),
        ({"database_url": "postgresql://user:secret@localhost/db"}, "user:secret"),
        ({"invitation_token_hash": "raw-token-hash"}, "raw-token-hash"),
        (
            {"source_queue_url": "http://localhost:4566/000000000000/iep-reporting"},
            "000000000000/iep-reporting",
        ),
        ({"receipt_handle": "AQEB-raw-receipt-handle"}, "AQEB-raw-receipt-handle"),
        ({"message_body": '{"candidate_email":"raw@example.com"}'}, "raw@example.com"),
        ({"Idempotency-Key": "raw-idempotency-key"}, "raw-idempotency-key"),
        (
            {
                "raw_db_projection": {
                    "applicant_name": "실지원자",
                    "email": "real.db@example.com",
                    "resume_text": "full database row",
                }
            },
            "full database row",
        ),
        ({"policy_text": "full policy notice"}, "full policy notice"),
        ({"answer_text": "private applicant answer"}, "private applicant answer"),
        ({"document_text": "raw resume body"}, "raw resume body"),
        ({"report_text": "model narrative"}, "model narrative"),
        ({"model_prompt": "secret scoring prompt"}, "secret scoring prompt"),
        ({"credential": "local-password-value"}, "local-password-value"),
        (
            {"source_path": "C:/Users/real-person/private/worktree/file.py"},
            "real-person",
        ),
    ],
)
def test_secret_and_pii_corpus_is_redacted(payload, forbidden):
    serialized = json.dumps(redact(payload), ensure_ascii=False)
    assert forbidden not in serialized


@pytest.mark.parametrize(
    "value",
    [
        "ddac1816-1234-4abc-965e-3573ec751f5d",
        "fb7bd6ee-c010-1234-5678-c1c7e30f022b",
    ],
)
def test_uuid_is_not_corrupted_by_phone_redaction(value):
    assert redact(value) == value


def test_full_database_projection_is_not_persisted_as_an_allowlisted_effect():
    projected = redact(
        {
            "raw_db_projection": {
                "invitation_id": "00000000-0000-7000-8000-000000000001",
                "resume_text": "raw resume",
            },
            "effects": {"logical_report_ids": ["report-01"]},
        }
    )

    assert projected["raw_db_projection"] == REDACTED
    assert projected["effects"] == {"logical_report_ids": ["report-01"]}


@pytest.mark.parametrize(
    "relative_path",
    [
        "environment.snapshot.json",
        "queue-topology.snapshot.json",
        "delivery-attempts.jsonl",
        "effects.jsonl",
        "terminal-failure.json",
        "redrive-receipts.jsonl",
        "artifacts/spec002-sensitive.json",
        "policy-and-consent.json",
        "bypass-attempts.jsonl",
        "protected-effects.jsonl",
        "causal-events.jsonl",
        "fault-receipts.jsonl",
    ],
)
def test_every_spec002_artifact_gate_rejects_redaction_bypass(
    tmp_path, run_factory, relative_path
):
    writer = EvidenceBundleWriter(tmp_path, run_factory())
    unsafe = canonical_json_bytes(
        {
            "receipt_handle": "AQEB-unredacted-handle",
            "message_body": "unredacted-message-body",
        }
    )

    if relative_path.endswith(".jsonl"):
        with pytest.raises(ValueError, match="prohibited secret or PII"):
            writer.write_bytes(relative_path, unsafe + b"\n", "application/x-ndjson")
    else:
        with pytest.raises(ValueError, match="prohibited secret or PII"):
            writer.write_json(
                relative_path,
                {
                    "receipt_handle": "AQEB-unredacted-handle",
                    "message_body": "unredacted-message-body",
                },
                redact_first=False,
            )
