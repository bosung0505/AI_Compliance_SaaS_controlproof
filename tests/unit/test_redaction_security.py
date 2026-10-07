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


# T010 (Spec 004): report, interview and criterion free text must never reach a bundle in clear; Spec 004
# projections carry `*_sha256` and `*_length` instead (FR-042). The raw-field names below are the ones a
# Spec 004 projection must never carry. Generic keys such as `summary`/`rationale` are deliberately not
# listed: existing judgement artifacts use them for ControlProof's own wording. RED until T018 extends
# `redact` (strict xfail, ID-004-01).
@pytest.mark.xfail(strict=True, raises=AssertionError, reason="RED until T018 redacts Spec 004 text fields")
@pytest.mark.parametrize(
    "payload,forbidden",
    [
        ({"report_summary": "합성 보고서 요약 원문"}, "합성 보고서 요약 원문"),
        ({"item_observation": "합성 관찰 원문"}, "합성 관찰 원문"),
        ({"axis_rationale": "합성 축 사유 원문"}, "합성 축 사유 원문"),
        ({"item_uncertainty": "합성 불확실성 원문"}, "합성 불확실성 원문"),
        ({"follow_up_question": "합성 후속 질문 원문"}, "합성 후속 질문 원문"),
        ({"question_text": "합성 질문 원문"}, "합성 질문 원문"),
        ({"transcript_text": "합성 자막 원문"}, "합성 자막 원문"),
        ({"criterion_description": "[controlproof-spec004 mode=VALID] 합성 기준 설명"}, "합성 기준 설명"),
        ({"playback_url": "http://localhost:4566/media/final.mp4"}, "final.mp4"),
    ],
)
def test_spec004_free_text_corpus_is_redacted(payload, forbidden):
    serialized = json.dumps(redact(payload), ensure_ascii=False)
    assert forbidden not in serialized


def test_spec004_text_digests_survive_redaction():
    digests = {"summary_sha256": "7" * 64, "summary_length": 32, "rationale_sha256": "8" * 64}
    assert redact(digests) == digests


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
        # T086: every remaining Spec 003 EV3 file, the sealed observer rows and the judgement.
        "target.snapshot.json",
        "n02-capabilities.json",
        "n02-lanes.json",
        "baseline-effects.jsonl",
        "causal-edges.jsonl",
        "observations.jsonl",
        "recovery.json",
        "assertions.json",
        "judgement.json",
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


_IDENTIFIER_ONLY_KEYS = {"trace_id", "cookie", "authorization", "idempotency_key", "session_cookie"}


@pytest.mark.parametrize(
    "row",
    [
        {"receipt_id": "r1", "boundary": "REPORT_HANDLER_ENTERED", "trace_id": "controlproof:x:y:z",
         "cookie": "iep_applicant_session=raw-session-cookie"},
        {"marker": "consent", "Idempotency-Key": "raw-idempotency-key", "invitation_id": "i"},
        {"event_id": "e1", "kind": "PROCESSING_REQUESTED", "request_headers": {"Authorization": "Bearer raw.jwt"}},
    ],
)
def test_receipt_marker_and_causal_rows_cannot_carry_raw_identifiers(tmp_path, run_factory, row):
    """T086: observer receipts, fault markers and causal rows carry digests only."""
    writer = EvidenceBundleWriter(tmp_path, run_factory())
    with pytest.raises(ValueError, match="prohibited secret or PII"):
        writer.write_bytes("observations.jsonl", canonical_json_bytes(row) + b"\n", "application/x-ndjson")


def test_sealed_n02_bundle_and_cli_payloads_are_redacted(tmp_path, monkeypatch):
    """T086/SC-011: a complete N-02 Run leaves no raw identifier, header, cookie, user path or
    PII in any sealed file, and the CLI run payload carries only the redacted bundle path."""
    from dataclasses import replace

    from engine import cli
    from engine.evidence import assert_redacted
    from engine.runner import build_profile_runner
    from engine.scenario import load
    from tests.fixtures.fake_adapters import FakeClock, FakeN02Adapters, make_adapters

    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    fake = FakeN02Adapters()
    adapters, _ = make_adapters()
    adapters = replace(adapters, n02_seed=fake, n02_consent=fake, n02_processing=fake,
                       n02_causality=fake, n02_fault=fake, n02_observer=fake)
    runner = build_profile_runner(load("scenarios/N-02.yaml"), adapters, tmp_path, clock=FakeClock())
    run, judgement, bundle = runner.execute(runner.preflight("whyyou-local"))

    sealed = sorted(path for path in bundle.rglob("*") if path.is_file())
    assert len(sealed) >= 20
    for path in sealed:
        if path.suffix in {".json", ".jsonl"}:
            assert_redacted(path.read_bytes())
            if path.suffix == ".jsonl":
                for line in path.read_text(encoding="utf-8").splitlines():
                    row = json.loads(line)
                    assert not (_IDENTIFIER_ONLY_KEYS & {key.casefold() for key in row}), path.name
                    for digest in (row.get("trace_id_digest"), row.get("fixture_digest")):
                        assert digest is None or (len(digest) == 64 and int(digest, 16) >= 0), path.name

    payload = cli._run_payload(run, judgement, bundle)
    assert_redacted(canonical_json_bytes(payload))
    assert "iep_applicant_session" not in json.dumps(payload)
    # A bundle under a user home is shown with the home replaced, on either platform.
    for home in ("C:/Users/real-person", "/home/real-person"):
        shown = redact({"bundle_path": f"{home}/.controlproof/runs/{run.run_id}"})["bundle_path"]
        assert "[USER_ROOT]" in shown and "real-person" not in shown
