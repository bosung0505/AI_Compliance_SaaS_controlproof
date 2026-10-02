from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from types import SimpleNamespace

from engine import cli
from engine.lifecycle import RestoreBlockStore


def _n02_case(tmp_path, monkeypatch, *, safe=True):
    run_root = tmp_path / "runs"
    run_root.mkdir(exist_ok=True)
    run_id = "15cef078-ee24-4f0e-91ef-381e0f7a1cc2"
    target = "whyyou-local"
    subject_ref = "n02-consent-order"
    lane = {
        "run_id": run_id,
        "lane_id": "CONSENT_FAULT_RECOVERY",
        "subject_ref": "n02-15cef078-consent-fault-recovery",
        "invitation_id": "3a69ee4e-5970-5ced-83d9-26a70714127d",
        "applicant_id": "a0451c2e-3e36-5de1-8494-2956a9779d05",
    }
    bundle = run_root / run_id
    bundle.mkdir()
    (bundle / "run.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "scenario_id": "N-02",
                "execution_profile": "N02_CONSENT_ORDER_V1",
                "target_id": target,
                "state": "RESTORE_FAILED",
            }
        ),
        encoding="utf-8",
    )
    (bundle / "subjects.json").write_text(json.dumps([lane]), encoding="utf-8")
    blocks = RestoreBlockStore(run_root)
    blocks.block(target, subject_ref, SimpleNamespace(run_id=run_id))
    evidence = tmp_path / "n02-cleanup.json"
    evidence.write_text(
        json.dumps(
            {
                "schema_version": "controlproof.n02-cleanup-evidence.v1",
                "captured_at": datetime.now(UTC).isoformat(),
                "parent_run_id": run_id,
                "target_id": target,
                "subject_ref": subject_ref,
                "lane_subject_ref": lane["subject_ref"],
                "invitation_id": lane["invitation_id"],
                "applicant_id": lane["applicant_id"],
                "safe_state_read_only": True,
                "findings": {
                    "invitation": [["identity_verified", 1]],
                    **{name: 0 for name in (
                        "consent_records", "active_consents", "consented_transitions",
                        "consent_completed_events", "all_invitation_events", "upload_intents",
                        "submissions", "analyses", "interview_strategies",
                    )},
                },
                "fault_files_exist": {"marker": False, "consumed_token": False, "fault_receipt": False},
            }
        ),
        encoding="utf-8",
    )
    calls = []
    runtime = SimpleNamespace(
        adapters=SimpleNamespace(
            fault=SimpleNamespace(target_safe=lambda **_kwargs: calls.append("wrong-h03") or True),
            n02_fault=SimpleNamespace(target_safe=lambda **kwargs: calls.append(kwargs) or safe),
        )
    )
    monkeypatch.setattr(cli, "_settings", lambda _args: SimpleNamespace(run_root=run_root))
    monkeypatch.setattr(cli, "create_runtime", lambda _settings, _path: runtime)
    monkeypatch.setattr(cli, "verify_bundle", lambda _path: {"bundle_status": "VERIFIED"})
    args = ["cleanup-confirm", "--target", target, "--subject", subject_ref, "--evidence", str(evidence), "--json"]
    return blocks, evidence, lane, calls, args


def test_n02_cleanup_uses_bound_parent_and_n02_safe_reprobe(tmp_path, monkeypatch, capsys):
    blocks, evidence, lane, calls, args = _n02_case(tmp_path, monkeypatch)
    assert cli.main(args) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["blocked_run_id"] == lane["run_id"]
    assert output["evidence_sha256"] == hashlib.sha256(evidence.read_bytes()).hexdigest()
    assert calls == [{"subject": lane}]
    assert not blocks.blocked("whyyou-local", "n02-consent-order")


def test_n02_cleanup_rejects_wrong_parent_and_unsafe_reprobe(tmp_path, monkeypatch, capsys):
    blocks, evidence, _, calls, args = _n02_case(tmp_path, monkeypatch, safe=False)
    assert cli.main(args) != 0
    assert blocks.blocked("whyyou-local", "n02-consent-order")
    assert "wrong-h03" not in calls
    evidence_record = json.loads(evidence.read_text(encoding="utf-8"))
    evidence_record["parent_run_id"] = "00000000-0000-0000-0000-000000000001"
    evidence.write_text(json.dumps(evidence_record), encoding="utf-8")
    assert cli.main(args) != 0
    assert blocks.blocked("whyyou-local", "n02-consent-order")


def test_n02_cleanup_rejects_invalid_bundle_and_stale_evidence(tmp_path, monkeypatch):
    blocks, evidence, _, _, args = _n02_case(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "verify_bundle", lambda _path: {"bundle_status": "INVALID"})
    assert cli.main(args) != 0
    assert blocks.blocked("whyyou-local", "n02-consent-order")
    monkeypatch.setattr(cli, "verify_bundle", lambda _path: {"bundle_status": "VERIFIED"})
    record = json.loads(evidence.read_text(encoding="utf-8"))
    record["captured_at"] = "2026-01-01T00:00:00+00:00"
    evidence.write_text(json.dumps(record), encoding="utf-8")
    assert cli.main(args) != 0
    assert blocks.blocked("whyyou-local", "n02-consent-order")


def test_cleanup_confirm_requires_evidence_and_safe_reprobe(tmp_path, monkeypatch, capsys):
    run_root = tmp_path / "runs"
    run_root.mkdir(exist_ok=True)
    blocks = RestoreBlockStore(run_root)
    blocks.block(
        "whyyou-local",
        "candidate-01",
        SimpleNamespace(run_id="00000000-0000-0000-0000-000000000001"),
    )
    evidence = tmp_path / "cleanup-note.json"
    evidence.write_text('{"marker_absent":true,"worker_healthy":true}', encoding="utf-8")
    runtime = SimpleNamespace(
        adapters=SimpleNamespace(
            fault=SimpleNamespace(target_safe=lambda **_kwargs: True),
        )
    )
    monkeypatch.setattr(cli, "_settings", lambda _args: SimpleNamespace(run_root=run_root))
    monkeypatch.setattr(cli, "create_runtime", lambda _settings, _path: runtime)
    exit_code = cli.main(
        [
            "cleanup-confirm",
            "--target",
            "whyyou-local",
            "--subject",
            "candidate-01",
            "--evidence",
            str(evidence),
            "--json",
        ]
    )
    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["evidence_sha256"] == hashlib.sha256(evidence.read_bytes()).hexdigest()
    assert not blocks.blocked("whyyou-local", "candidate-01")


def test_cleanup_confirm_has_no_force_option():
    parser = cli._parser()
    actions = parser._subparsers._group_actions[0].choices["cleanup-confirm"]._actions
    assert "--force" not in {option for action in actions for option in action.option_strings}
