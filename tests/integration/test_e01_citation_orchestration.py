"""T034 — E-01 citation journey on the deterministic fake (US1).

Only E01-A1/A2 are asserted here; removal and storage-probe steps belong to US2.
"""

from __future__ import annotations

from engine.models import AssertionStatus
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters
from tests.fixtures.fake_spec004 import FakeSpec004Adapters, use_spec004_fixture


def _run(tmp_path, fake):
    adapters, _ = make_adapters(spec004=fake)
    use_spec004_fixture(adapters)
    runner = build_profile_runner(
        load("scenarios/E-01.yaml"), adapters, tmp_path, clock=FakeClock()
    )
    readiness = runner.preflight("whyyou-local")
    assert readiness.status.value == "READY", readiness
    return runner.execute(readiness)


def _results(judgement):
    return {item.assertion_id: item for item in judgement.assertion_results}


def test_citation_journey_passes_a1_a2_and_orders_the_reference_first(tmp_path) -> None:
    fake = FakeSpec004Adapters()
    _, judgement, _ = _run(tmp_path, fake)
    results = _results(judgement)
    assert results["E01-A1"].status is AssertionStatus.PASS, results["E01-A1"].detail
    assert results["E01-A2"].status is AssertionStatus.PASS, results["E01-A2"].detail
    calls = fake.calls
    assert calls.index("request:E01_REFERENCE") < calls.index("seed:E01_CITATION_MATRIX")
    assert calls.index("seed:E01_CITATION_MATRIX") < calls.index("request:E01_CITATION_MATRIX")
    assert fake.committed >= {lane.subject_ref for lane in fake.lanes.values()}


def test_worker_storing_invalid_citations_fails_a1(tmp_path) -> None:
    _, judgement, _ = _run(tmp_path, FakeSpec004Adapters(citation_storage="STORE_AS_EMITTED"))
    assert _results(judgement)["E01-A1"].status is AssertionStatus.FAIL


def test_refused_report_is_a_precondition_not_a_verdict(tmp_path) -> None:
    _, judgement, _ = _run(
        tmp_path, FakeSpec004Adapters(refuse_lanes=frozenset({"E01_CITATION_MATRIX"}))
    )
    results = _results(judgement)
    assert results["E01-A1"].status is AssertionStatus.INCONCLUSIVE
    assert results["E01-A1"].detail.startswith("PRECONDITION_NOT_MET")
