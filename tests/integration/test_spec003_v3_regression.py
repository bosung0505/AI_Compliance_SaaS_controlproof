"""T011 — Spec 003 (N-02, scenario v3) must keep executing and verifying while Spec 004 is added.

Guard tests: these pass now and must stay green through every Spec 004 task (FR-043).
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

from engine.evidence import verify_bundle
from engine.models import ExecutionProfile, RunState, Verdict
from engine.runner import build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, FakeN02Adapters, make_adapters

PARENT_BUNDLE = Path(".controlproof/runs/15cef078-ee24-4f0e-91ef-381e0f7a1cc2")
PARENT_MANIFEST_SHA256 = "d2306f3cd6e2b15ce87d94e4844a2278c7ea3c0b3c052a2aac45e1bff8f2bc9b"


def test_n02_v3_profile_still_executes_and_verifies(tmp_path) -> None:
    fake = FakeN02Adapters()
    adapters, _ = make_adapters()
    adapters = replace(
        adapters,
        n02_seed=fake,
        n02_consent=fake,
        n02_processing=fake,
        n02_causality=fake,
        n02_fault=fake,
        n02_observer=fake,
    )
    runner = build_profile_runner(
        load("scenarios/N-02.yaml"), adapters, tmp_path, clock=FakeClock()
    )
    run, judgement, bundle = runner.execute(runner.preflight("whyyou-local"))
    assert run.execution_profile is ExecutionProfile.N02_CONSENT_ORDER_V1
    assert run.state is RunState.COMPLETED
    assert judgement.verdict is Verdict.PASS
    result = verify_bundle(bundle)
    assert result["bundle_status"] == "VERIFIED"
    assert result["checked_evidence_requirements"] == [f"EV3-{index:02d}" for index in range(1, 11)]


def test_sealed_spec003_parent_bundle_is_unchanged_and_verifies() -> None:
    """The one published N-02 parent (AGENTS.md exception) is read-only evidence for every later Spec."""
    manifest = PARENT_BUNDLE / "manifest.json"
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == PARENT_MANIFEST_SHA256
    assert verify_bundle(PARENT_BUNDLE)["bundle_status"] == "VERIFIED"
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == PARENT_MANIFEST_SHA256
