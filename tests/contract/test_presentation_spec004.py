"""T062 — Spec 004 review projections (contracts/controlproof-cli-v4.md "Run", "Show", "Claim boundary").

RED until T065 extends `engine/presentation.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

from engine.presentation import load_bundle_summary, render_human
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters
from tests.fixtures.fake_spec004 import FakeSpec004Adapters, use_spec004_fixture

LIMITATIONS = ["FIXTURE_INTERVIEW_INPUT", "EXTERNAL_AI_BLOCKED", "FIXED_MODEL_SUBSTITUTE"]


def _bundle(tmp_path: Path, scenario: str, **options) -> Path:
    adapters, _ = make_adapters(spec004=FakeSpec004Adapters(**options))
    use_spec004_fixture(adapters)
    runner = build_profile_runner(load(f"scenarios/{scenario}.yaml"), adapters, tmp_path, clock=FakeClock())
    _, _, bundle = runner.execute(runner.preflight("whyyou-local"))
    return bundle


def test_e01_projection_shows_modes_removal_and_diagnostic(tmp_path) -> None:
    summary = load_bundle_summary(_bundle(tmp_path, "E-01", removal_indicator="score_null"))
    assert summary["citation_modes"] == {
        "VALID": "STORED_VALID",
        "EMPTY": "EMPTIED",
        "NONEXISTENT": "EMPTIED",
        "OTHER_APPLICANT": "EMPTIED",
        "OTHER_CRITERION": "EMPTIED",
    }
    assert summary["evidence_removal"] == {
        "applied": True,
        "restored": True,
        "exposed_as_insufficient": True,
    }
    assert set(summary["diagnostics"]["E01-D1"]) == {"EMPTY", "NONEXISTENT", "OTHER_APPLICANT"}
    assert summary["change_injection_restore_status"] == "SUCCEEDED"
    assert summary["limitations"] == LIMITATIONS
    assert summary["unverified_scope"] == ["AWS", "N-01", "N-03"]
    assert summary["evaluated_assertions"] == ["E01-A1", "E01-A2", "E01-A3", "E01-A4"]
    notice = summary["legal_scope_notice"]
    assert "E-01" in notice and "fixture" in notice and "고정 모델" in notice and "AWS" in notice
    text = render_human(summary)
    assert "인용 모드" in text and "근거 제거" in text and "E01-D1" in text
    assert "applicant said" not in json.dumps(summary, ensure_ascii=False)


def test_e01_restore_failure_is_visible(tmp_path) -> None:
    summary = load_bundle_summary(
        _bundle(tmp_path, "E-01", removal_indicator="score_null", restore_mismatch=True)
    )
    assert summary["change_injection_restore_status"] == "FAILED"
    assert summary["run_state"] == "RESTORE_FAILED"


def test_e02_projection_shows_versions_binding_and_recompute(tmp_path) -> None:
    bundle = _bundle(tmp_path, "E-02")
    summary = load_bundle_summary(bundle)
    versions = json.loads((bundle / "criteria-versions.json").read_text(encoding="utf-8"))
    assert summary["versions"]["v1"]["competency_model_version_id"] == versions["v1"][
        "competency_model_version_id"
    ]
    assert summary["versions"]["v2"]["version_number"] == 2
    assert summary["versions"]["v2"]["status"] == "published"
    assert summary["first_report_unchanged"] is True
    assert summary["second_report_bound_to"] == versions["published_v2_id"]
    assert len(summary["recompute"]) == 2
    assert all(all(targets.values()) for targets in summary["recompute"].values())
    assert summary["limitations"] == LIMITATIONS
    assert "E-02" in summary["legal_scope_notice"]
    text = render_human(summary)
    assert "기준 버전" in text and "재계산" in text
