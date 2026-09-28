from __future__ import annotations

from engine.adapters.whyyou.adapter import create_whyyou_adapter
from engine.adapters.whyyou.capability import CAPABILITY_VERSIONS
from engine.config import Settings


def test_spec002_composition_owns_every_before_after_and_decision_replay_boundary(tmp_path):
    settings = Settings.from_env(
        {
            "WHYYOU_BASE_URL": "http://localhost:8000",
            "WHYYOU_CONSOLE_URL": "http://localhost:5173",
            "WHYYOU_DATABASE_URL": "postgresql+psycopg://local:local@localhost/test",
            "WHYYOU_COMPANY_TOKEN": "local-test-token",
            "WHYYOU_COMPANY_USER_ID": "00000000-0000-7000-8000-000000000505",
            "WHYYOU_REPO_PATH": str(tmp_path),
            "CONTROLPROOF_FAULT_ROOT": str(tmp_path / "faults"),
            "CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED": "true",
            "CONTROLPROOF_MODEL_FIXTURE_ID": "h03-report-v1",
            "CONTROLPROOF_MODEL_FIXTURE_DIGEST": "a" * 64,
        }
    )

    adapters, _client = create_whyyou_adapter(settings)

    assert adapters.queue is not None
    assert adapters.decision is not None
    assert adapters.effects is not None
    assert adapters.boundary_receipts is adapters.fault
    assert adapters.duplicate_acks is adapters.fault
    assert adapters.safe_redrive is adapters.queue
    assert callable(adapters.fault.apply)
    assert callable(adapters.fault.apply_after)
    assert callable(adapters.decision.attempt)
    assert callable(adapters.effects.read_decision_effects)
    assert {
        "reporting.fault.before.inject": "v1",
        "reporting.fault.after.inject": "v1",
        "reporting.fault.boundary.read": "v1",
        "reporting.duplicate_ack.read": "v1",
        "hiring.final_decision.replay": "v1",
        "hiring.decision_effects.read": "v1",
    }.items() <= CAPABILITY_VERSIONS.items()
