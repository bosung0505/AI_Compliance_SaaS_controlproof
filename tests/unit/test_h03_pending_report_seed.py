from seeds.h03_pending_report import (
    build_pending_report_fixture,
    check_pending_invariants,
    trigger_event,
)


def test_external_tenant_is_reused_without_tenant_upsert():
    from uuid import uuid4

    seed = build_pending_report_fixture(
        "run-external",
        company_id=uuid4(),
        reviewer_id=uuid4(),
    )

    assert seed.fixture.of("company") == []
    assert seed.fixture.of("company_user") == []


def test_pending_fixture_has_final_media_but_no_report_or_decision_event():
    seed = build_pending_report_fixture("run-1")
    assert check_pending_invariants(seed) == []
    assert seed.fixture.of("report") == []
    assert seed.fixture.of("report_item") == []
    assert seed.fixture.of("evidence") == []
    assert all(asset["asset_type"] == "final_video" for asset in seed.fixture.of("recording_asset"))
    assert "report_generation_event_id" not in seed.correlation
    stages = {row["name"]: row for row in seed.fixture.of("recruiting_stage")}
    assert {"검토", "최종합격", "불합격"}.issubset(stages)
    assert seed.correlation["final_accept_stage_id"] == str(
        stages["최종합격"]["recruiting_stage_id"]
    )
    assert seed.correlation["final_reject_stage_id"] == str(stages["불합격"]["recruiting_stage_id"])


def test_trigger_is_explicit_and_idempotent():
    seed = build_pending_report_fixture("run-1")
    first = trigger_event(seed, run_id="run-1")
    second = trigger_event(seed, run_id="run-1")
    assert first == second
    assert first["event_type"] == "report.generation_requested"


def test_pending_report_has_active_consent_for_the_new_target_guard():
    from seeds.state_seed import ORDER, upsert_sql

    first = build_pending_report_fixture("consent-precondition")
    second = build_pending_report_fixture("consent-precondition")
    consent = first.fixture.of("consent")
    assert len(consent) == 1
    assert consent == second.fixture.of("consent")
    assert consent[0]["invitation_id"] == first.fixture.of("invitation")[0]["invitation_id"]
    assert consent[0]["company_id"] == first.fixture.of("invitation")[0]["company_id"]
    assert "ai_assessment" in consent[0]["purposes"]
    assert consent[0]["withdrawn_at"] is None
    assert len(consent[0]["evidence_digest"]) == 64
    assert ORDER.index("invitation") < ORDER.index("consent")
    statement, params = upsert_sql("consent", consent[0])
    assert "INSERT INTO consent_records" in statement
    assert "ai_assessment" in params["purposes"]


def test_pending_report_without_consent_is_rejected_before_apply():
    import pytest

    from seeds.h03_pending_report import apply_pending

    seed = build_pending_report_fixture("missing-consent")
    seed.fixture.rows["consent"] = []
    with pytest.raises(ValueError, match="one active assessment consent"):
        apply_pending(None, seed)
