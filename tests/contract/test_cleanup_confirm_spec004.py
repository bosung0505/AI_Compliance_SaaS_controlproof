"""T050 — `cleanup-confirm` for a blocked Spec 004 subject (FR-022, FR-041, SC-002).

The block comes from a real E-01 `RESTORE_FAILED` Run on fakes. Cleanup is accepted only when the sealed parent
is that Run and a read-only re-probe of every recorded change injection shows its pre-change digest.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from engine import cli
from engine.lifecycle import RestoreBlockStore
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters
from tests.fixtures.fake_spec004 import FakeSpec004Adapters, use_spec004_fixture

SUBJECT = "e01-citation-evidence"


def _blocked_run(tmp_path, monkeypatch, *, safe):
    run_root = tmp_path / "runs"
    adapters, _ = make_adapters(
        spec004=FakeSpec004Adapters(removal_indicator="score_null", restore_mismatch=True)
    )
    use_spec004_fixture(adapters)
    runner = build_profile_runner(load("scenarios/E-01.yaml"), adapters, run_root, clock=FakeClock())
    run, _, _ = runner.execute(runner.preflight("whyyou-local"))
    calls = []
    runtime = SimpleNamespace(
        adapters=SimpleNamespace(
            fault=SimpleNamespace(target_safe=lambda **_kwargs: calls.append("wrong-h03") or True),
            spec004_mutation=SimpleNamespace(
                target_safe=lambda **kwargs: calls.append(kwargs) or safe
            ),
        )
    )
    monkeypatch.setattr(cli, "_settings", lambda _args: SimpleNamespace(run_root=run_root))
    monkeypatch.setattr(cli, "create_runtime", lambda _settings, _path: runtime)
    evidence = tmp_path / "e01-cleanup.json"
    evidence.write_text(json.dumps({"operator_note": "read-only re-probe"}), encoding="utf-8")
    args = [
        "cleanup-confirm", "--target", "whyyou-local", "--subject", SUBJECT,
        "--evidence", str(evidence), "--json",
    ]
    return RestoreBlockStore(run_root), run, calls, args


def test_spec004_cleanup_reprobes_the_recorded_injections(tmp_path, monkeypatch, capsys) -> None:
    blocks, run, calls, args = _blocked_run(tmp_path, monkeypatch, safe=True)
    assert blocks.blocked("whyyou-local", SUBJECT)
    assert cli.main(args) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["blocked_run_id"] == str(run.run_id)
    assert "wrong-h03" not in calls
    injections = calls[0]["injections"]
    assert {row["kind"] for row in injections} >= {"EVIDENCE_SEGMENT_REMOVAL"}
    assert not blocks.blocked("whyyou-local", SUBJECT)


def test_spec004_cleanup_keeps_the_block_when_unsafe(tmp_path, monkeypatch) -> None:
    blocks, _, calls, args = _blocked_run(tmp_path, monkeypatch, safe=False)
    assert cli.main(args) != 0
    assert blocks.blocked("whyyou-local", SUBJECT)
    assert "wrong-h03" not in calls
