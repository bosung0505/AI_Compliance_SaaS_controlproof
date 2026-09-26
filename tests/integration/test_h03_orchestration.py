import json

from engine.evidence import verify_bundle
from engine.models import Verdict
from engine.runner import RunOrchestrator
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters


def test_full_h03_order_produces_sealed_bundle(tmp_path):
    adapters, browser = make_adapters()
    runner = RunOrchestrator(load("scenarios/H-03.yaml"), adapters, tmp_path, clock=FakeClock())
    readiness = runner.preflight("whyyou-local")
    run, judgement, bundle = runner.execute(readiness)
    assert judgement.verdict is Verdict.PASS
    assert browser.closed
    assert verify_bundle(bundle)["bundle_status"] == "VERIFIED"
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert all(manifest["required_evidence"][f"EV-{index:02d}"] for index in range(1, 10))
    assert len((bundle / "observations.jsonl").read_text(encoding="utf-8").splitlines()) >= 20
    assert str(run.run_id) == manifest["run_id"]
