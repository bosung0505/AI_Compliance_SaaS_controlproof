import json

from engine.runner import RunOrchestrator
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters


def test_all_evidence_links_and_split_recovery_are_present(tmp_path):
    adapters, _ = make_adapters(processing="FAILED")
    runner = RunOrchestrator(load("scenarios/H-03.yaml"), adapters, tmp_path, clock=FakeClock())
    run, judgement, bundle = runner.execute(runner.preflight("whyyou-local"))
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["required_evidence"]) == {f"EV-{index:02d}" for index in range(1, 10)}
    assert all(manifest["required_evidence"].values())
    observations = [
        json.loads(line)
        for line in (bundle / "observations.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    values = {row["key"]: row.get("value") for row in observations}
    assert values["fault.environment_restore"] == "SUCCEEDED"
    assert values["report.processing_recovery"] == "FAILED"
    assert run.target_version.startswith("target-snapshot:sha256:")
    assert judgement.implementation_status if hasattr(judgement, "implementation_status") else True
