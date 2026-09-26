from seeds.h03_pending_report import (
    build_pending_report_fixture,
    check_pending_invariants,
    trigger_event,
)


def test_pending_fixture_has_final_media_but_no_report_or_decision_event():
    seed = build_pending_report_fixture("run-1")
    assert check_pending_invariants(seed) == []
    assert seed.fixture.of("report") == []
    assert seed.fixture.of("report_item") == []
    assert seed.fixture.of("evidence") == []
    assert all(asset["asset_type"] == "final_video" for asset in seed.fixture.of("recording_asset"))
    assert "report_generation_event_id" not in seed.correlation


def test_trigger_is_explicit_and_idempotent():
    seed = build_pending_report_fixture("run-1")
    first = trigger_event(seed, run_id="run-1")
    second = trigger_event(seed, run_id="run-1")
    assert first == second
    assert first["event_type"] == "report.generation_requested"
