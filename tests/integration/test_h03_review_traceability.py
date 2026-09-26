from engine.presentation import load_bundle_summary
from engine.runner import RunOrchestrator
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters


def test_every_assertion_projects_artifact_and_source_links(tmp_path):
    adapters, _ = make_adapters()
    runner = RunOrchestrator(load("scenarios/H-03.yaml"), adapters, tmp_path, clock=FakeClock())
    bundle = runner.execute(runner.preflight("whyyou-local"))[2]
    summary = load_bundle_summary(bundle)
    assert {item["assertion_id"] for item in summary["assertions"]} == {
        f"H03-A{index}" for index in range(1, 7)
    }
    for assertion in summary["assertions"]:
        assert assertion["source_requirements"] == [assertion["assertion_id"]]
        assert assertion["evidence"]
        assert all(item["path"] and item["sha256"] for item in assertion["evidence"])
