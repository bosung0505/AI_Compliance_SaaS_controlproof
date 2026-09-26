from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

from engine import cli
from engine.lifecycle import RestoreBlockStore


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
