import json
import shutil
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest

from engine.evidence import REDACTED, EvidenceBundleWriter, assert_redacted, redact, verify_bundle
from engine.models import (
    SPEC004_UNVERIFIED_SCOPE,
    ExecutionProfile,
    Run,
    TargetEnvironmentSnapshot,
    canonical_json_bytes,
    sha256_bytes,
)


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
# `redact` (T018 done).
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


# T090: independently list the v4 contract, including the manifest, YAML-named snapshot and
# child-only lineage files. Coverage must not silently inherit the verifier's own file allowlist.
_SPEC004_COMMON = {
    "run.json", "scenario.snapshot.yaml", "target.snapshot.json", "environment.snapshot.json",
    "subjects.json", "observations.jsonl", "assertions.json", "judgement.json", "manifest.json",
    "spec004-capabilities.json", "spec004-lanes.json", "report-records.jsonl", "report-reads.jsonl",
    "change-injections.jsonl", "recovery.json", "retest-link.json", "retest-diff.json",
}
_SPEC004_FILES = {
    "E-01": _SPEC004_COMMON | {"citation-cases.jsonl", "model-emissions.jsonl", "storage-probe.json"},
    "E-02": _SPEC004_COMMON | {"criteria-versions.json", "frozen-inputs.json", "recompute.json"},
}
_SPEC004_FILE_CASES = [
    (scenario, name) for scenario, names in _SPEC004_FILES.items() for name in sorted(names)
]
_SECURITY_SENTINEL = "t090-synthetic-credential"
_SAFE_PROJECTION = {
    "subject_ref": "synthetic-subject",
    "evidence_id": "ddac1816-1234-4abc-965e-3573ec751f5d",
    "rationale_sha256": "8" * 64,
    "rationale_length": 32,
    "score": 72,
    "criterion_weight": 50,
    "source_locator": "backend/src/interview_evidence/domain/report.py",
}


def _security_spec004_runner(root, scenario, **options):
    from engine.runner import build_profile_runner
    from engine.scenario import load
    from tests.fixtures.fake_adapters import FakeClock, make_adapters
    from tests.fixtures.fake_spec004 import FakeSpec004Adapters, use_spec004_fixture

    adapters, _ = make_adapters(spec004=FakeSpec004Adapters(**options))
    use_spec004_fixture(adapters)
    return build_profile_runner(load(f"scenarios/{scenario}.yaml"), adapters, root, clock=FakeClock())


@pytest.fixture(scope="module")
def spec004_security_bundles(tmp_path_factory):
    from engine.retest import assert_parent_unchanged, prepare_retest

    root = tmp_path_factory.mktemp("spec004-security-source")
    children = {}
    for scenario in _SPEC004_FILES:
        options = {} if scenario == "E-01" else {"report_mutates_after_change": True}
        parent = _security_spec004_runner(root, scenario, **options)
        _, judgement, parent_bundle = parent.execute(parent.preflight("whyyou-local"))
        assert judgement.verdict.value == "FAIL"
        child = _security_spec004_runner(
            root, scenario, **({"removal_indicator": "score_null"} if scenario == "E-01" else {})
        )
        readiness = child.preflight("whyyou-local")
        child_id = uuid4()
        raw_environment = child.adapters.environment.capture_environment()
        environment = TargetEnvironmentSnapshot.model_validate(
            raw_environment.model_dump(mode="json", exclude={"snapshot_digest"})
            | {"unverified_scope": sorted(SPEC004_UNVERIFIED_SCOPE)}
        )
        parent_run, digest, records = prepare_retest(
            parent_bundle, child_run_id=child_id, child_target=readiness.target_snapshot,
            child_scenario_version=child.scenario.version,
            child_scenario_digest=child.scenario.snapshot().digest,
            child_profile=child.scenario.execution_profile, child_environment=environment,
        )
        _, judgement, bundle = child.execute(
            readiness, parent_run_id=parent_run.run_id, retest_records=records, run_id=child_id
        )
        assert judgement.verdict.value == "PASS"
        assert_parent_unchanged(parent_bundle, digest)
        assert verify_bundle(bundle)["bundle_status"] == "VERIFIED"
        children[scenario] = bundle
    return children


@pytest.mark.parametrize("scenario,relative_path", _SPEC004_FILE_CASES)
def test_every_spec004_file_rejects_writer_bypass_and_preserves_safe_facts(
    tmp_path, spec004_security_bundles, scenario, relative_path
):
    source = spec004_security_bundles[scenario]
    run = Run.model_validate_json((source / "run.json").read_text(encoding="utf-8"))
    writer = EvidenceBundleWriter(tmp_path, run)
    unsafe = _SAFE_PROJECTION | {"security_probe": {"credential": _SECURITY_SENTINEL}}
    path = writer.directory / relative_path
    with pytest.raises(ValueError, match="prohibited secret or PII"):
        if relative_path.endswith(".jsonl"):
            writer.write_bytes(relative_path, canonical_json_bytes(unsafe) + b"\n",
                               "application/x-ndjson")
        else:
            writer.write_json(relative_path, unsafe, redact_first=False)
    assert not path.exists()

    if relative_path.endswith(".jsonl"):
        writer.append_jsonl(relative_path, unsafe)
    else:
        writer.write_json(relative_path, unsafe)
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["security_probe"]["credential"] == REDACTED
    assert {key: persisted[key] for key in _SAFE_PROJECTION} == _SAFE_PROJECTION
    assert _SECURITY_SENTINEL not in path.read_text(encoding="utf-8")
    assert_redacted(path.read_bytes())


@pytest.mark.parametrize("scenario", _SPEC004_FILES)
def test_sealed_spec004_child_covers_every_contract_file_and_emission_allowlist(
    spec004_security_bundles, scenario
):
    bundle = spec004_security_bundles[scenario]
    files = {path.name for path in bundle.iterdir() if path.is_file()}
    assert files == _SPEC004_FILES[scenario]
    for name in sorted(files):
        assert_redacted((bundle / name).read_bytes())
    if scenario == "E-01":
        expected_keys = {
            "schema_version", "receipt_id", "fixture_id", "criterion_id", "mode",
            "provided_evidence_ids", "emitted_quoted_ids", "emitted_score", "mode_status", "emitted_at",
        }
        rows = [json.loads(line) for line in (bundle / "model-emissions.jsonl")
                .read_text(encoding="utf-8").splitlines()]
        assert rows
        assert all(set(row) == expected_keys for row in rows)


def _inject_security_probe(bundle, name):
    """Mutate only disposable fixture copies, updating hashes to isolate redaction from integrity."""
    path = bundle / name
    probe = {"security_probe": {"credential": _SECURITY_SENTINEL}}
    if name.endswith(".jsonl"):
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        if rows:
            rows[0].update(probe)
        else:
            rows.append(probe)
        payload = b"".join(canonical_json_bytes(row) + b"\n" for row in rows)
    else:
        document = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(document, list):
            if document:
                document[0].update(probe)
            else:
                document.append(probe)
        else:
            document.update(probe)
        payload = canonical_json_bytes(document)
    path.write_bytes(payload)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for record in manifest["files"]:
        if record["path"] == name:
            record.update(sha256=sha256_bytes(payload), size_bytes=len(payload))
    manifest.pop("bundle_digest")
    manifest["bundle_digest"] = sha256_bytes(canonical_json_bytes(manifest))
    manifest_path.write_bytes(canonical_json_bytes(manifest))


@pytest.mark.parametrize("scenario,relative_path", _SPEC004_FILE_CASES)
def test_every_spec004_file_is_scanned_even_when_manifest_hashes_match(
    tmp_path, spec004_security_bundles, scenario, relative_path
):
    source_root = spec004_security_bundles[scenario].parent
    root = tmp_path / "copied-runs"
    shutil.copytree(source_root, root)
    bundle = root / spec004_security_bundles[scenario].name
    _inject_security_probe(bundle, relative_path)
    result = verify_bundle(bundle)
    assert relative_path in result["redaction_violations"], result
    assert result["bundle_status"] == "INVALID"
    # A file-byte hash mismatch must not be the reason the injected secret was caught.
    assert relative_path not in result["mismatched_files"]


@pytest.mark.parametrize("field", [
    "authorization", "cookie", "model_prompt", "question_text", "transcript_text",
    "criterion_description", "report_summary", "source_path",
])
def test_emission_reader_rejects_raw_payload_fields_without_echoing_them(settings, tmp_path, field):
    from engine.adapters.base import AdapterResult
    from engine.adapters.whyyou.model_emission import WhyYouModelEmissionAdapter
    from tests.fixtures.spec004 import emission_receipt, sid

    criterion = str(sid("criterion", "security"))
    receipt = emission_receipt(criterion, **{field: _SECURITY_SENTINEL})
    directory = tmp_path / "model"
    directory.mkdir()
    (directory / f"{receipt['receipt_id']}.json").write_text(json.dumps(receipt), encoding="utf-8")
    adapter = WhyYouModelEmissionAdapter(replace(settings, observer_root=tmp_path))
    result = adapter.read_emissions(criterion_ids=(criterion,))
    assert isinstance(result, AdapterResult) and not result.ok
    assert result.code == "EMISSION_RECEIPTS_UNAVAILABLE"
    assert _SECURITY_SENTINEL not in repr(result)


@pytest.mark.parametrize("scenario", _SPEC004_FILES)
@pytest.mark.parametrize("as_json", [True, False], ids=["json", "human"])
def test_spec004_cli_preflight_run_show_verify_and_retest_outputs_are_redacted(
    tmp_path, monkeypatch, capsys, scenario, as_json
):
    from engine import cli

    root = tmp_path / "runs"
    options = {} if scenario == "E-01" else {"report_mutates_after_change": True}

    def create(_settings, _path):
        return _security_spec004_runner(root, scenario, **options)

    monkeypatch.setattr(cli, "create_runtime", create)
    monkeypatch.setattr(cli, "_settings", lambda _args: SimpleNamespace(run_root=root))
    profile = (ExecutionProfile.E01_CITATION_EVIDENCE_V1 if scenario == "E-01"
               else ExecutionProfile.E02_SCORING_FREEZE_V1).value

    def call(*argv):
        code = cli.main(list(argv) + (["--json"] if as_json else []))
        captured = capsys.readouterr()
        for output in (captured.out, captured.err):
            assert_redacted(output.encode())
            assert str(root) not in output
        assert captured.out
        return code

    assert call("preflight", scenario, "--profile", profile, "--target", "whyyou-local") == 0
    assert call("run", scenario, "--profile", profile, "--target", "whyyou-local") == 3
    parent = next(path for path in root.iterdir() if (path / "manifest.json").exists())
    assert call("show", parent.name, "--run-root", str(root)) == 0
    assert call("verify", parent.name, "--run-root", str(root)) == 0
    options = {"removal_indicator": "score_null"} if scenario == "E-01" else {}
    assert call("retest", parent.name, "--target", "whyyou-local") == 0


@pytest.mark.parametrize("as_json", [True, False], ids=["json", "human"])
def test_spec004_cli_error_redacts_synthetic_bearer_pii_signed_query_and_user_path(
    monkeypatch, capsys, as_json
):
    from engine import cli

    raw = ("Bearer t090-secret.jwt security.subject@example.com 010-1234-5678 "
           "https://local.test/media?X-Amz-Signature=t090-signature C:/Users/t090-user/receipt.json")

    def fail(_args):
        raise ValueError(raw)

    monkeypatch.setattr(cli, "_settings", fail)
    argv = ["preflight", "E-01", "--profile", "E01_CITATION_EVIDENCE_V1", "--target", "whyyou-local"]
    assert cli.main(argv + (["--json"] if as_json else [])) == cli.EXIT_USAGE
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert output
    assert_redacted(output.encode())
    for forbidden in ("t090-secret.jwt", "security.subject@example.com", "010-1234-5678",
                      "t090-signature", "t090-user"):
        assert forbidden not in output


@pytest.mark.parametrize("scenario", _SPEC004_FILES)
def test_spec004_registered_extra_receipt_is_also_scanned(tmp_path, spec004_security_bundles, scenario):
    source_root = spec004_security_bundles[scenario].parent
    root = tmp_path / "copied-runs"
    shutil.copytree(source_root, root)
    bundle = root / spec004_security_bundles[scenario].name
    name = "artifacts/extra-receipt.json"
    (bundle / "artifacts").mkdir()
    payload = canonical_json_bytes({"credential": _SECURITY_SENTINEL})
    (bundle / name).write_bytes(payload)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"].append({"path": name, "sha256": sha256_bytes(payload),
                              "size_bytes": len(payload), "mime_type": "application/json"})
    manifest.pop("bundle_digest")
    manifest["bundle_digest"] = sha256_bytes(canonical_json_bytes(manifest))
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    result = verify_bundle(bundle)
    assert result["bundle_status"] == "INVALID"
    assert name in result["redaction_violations"]


def test_spec004_redaction_does_not_follow_manifest_paths_outside_bundle(tmp_path):
    from engine.evidence import _spec004_redaction

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (tmp_path / "outside.json").write_text(json.dumps({"credential": _SECURITY_SENTINEL}))
    (bundle / "manifest.json").write_text(json.dumps({"files": [{"path": "../outside.json"}]}))
    result = {"redaction_violations": []}
    _spec004_redaction(bundle, ExecutionProfile.E01_CITATION_EVIDENCE_V1, result)
    assert result["redaction_violations"] == []
