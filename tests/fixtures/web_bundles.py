"""Synthetic sealed bundles for the Spec 005 web (T002). Synthetic only; no real applicant data.

Every builder runs the real executor and sealing path on the deterministic fakes, so the bundles verify exactly like
recorded Runs. Reason codes the fakes cannot reach (ACCESS_LIMITED, EVIDENCE_CONFLICT) are produced by wrapping the
H-03 judge before sealing; the bundle is still written and sealed by the engine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from unittest import mock
from uuid import uuid4

from engine import runner as runner_module
from engine.models import (
    SPEC004_UNVERIFIED_SCOPE,
    AssertionStatus,
    InconclusiveReason,
    TargetEnvironmentSnapshot,
    TargetSnapshot,
    Verdict,
)
from engine.retest import prepare_retest
from engine.runner import RunOrchestrator, build_profile_runner
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, FakeState, make_adapters
from tests.fixtures.fake_spec004 import FakeSpec004Adapters, use_spec004_fixture

TARGET = "whyyou-local"
CASES = json.loads(
    (Path(__file__).parent / "bundles" / "cases.json").read_text(encoding="utf-8")
)["cases"]


@dataclass(frozen=True)
class Built:
    run_id: str
    verdict: str
    reason_code: str | None
    run_state: str
    bundle: Path


def _built(run, judgement, bundle) -> Built:
    return Built(
        str(run.run_id),
        judgement.verdict.value,
        judgement.reason_code.value if judgement.reason_code else None,
        run.state.value,
        Path(bundle),
    )


# --- Spec 001 H-03 (H03_MINIMAL_V1) ------------------------------------------------------------


def _h03_runner(root: Path, **options) -> RunOrchestrator:
    adapters, _ = make_adapters(**options)
    return RunOrchestrator(load("scenarios/H-03.yaml"), adapters, root, clock=FakeClock())


def h03_case(root: Path, case: str) -> Built:
    """`pass`, `fail`, `missing` (INSUFFICIENT_EVIDENCE) or `restore_failed` from `bundles/cases.json`."""
    if case not in {"pass", "fail", "missing", "restore_failed"}:
        raise ValueError(f"use a dedicated builder for {case}")
    runner = _h03_runner(root, **CASES[case])
    return _built(*runner.execute(runner.preflight(TARGET)))


def _forced_reason(reason: InconclusiveReason):
    original = runner_module.judge_h03

    def judge(*args, **kwargs):
        judgement = original(*args, **kwargs)
        results = list(judgement.assertion_results)
        first = results[0]
        results[0] = first.model_copy(
            update={
                "status": AssertionStatus.INCONCLUSIVE,
                "reason_code": reason,
                "detail": f"synthetic {reason.value} for the web fixture",
            }
        )
        return judgement.model_copy(
            update={
                "verdict": Verdict.INCONCLUSIVE,
                "reason_code": reason,
                "assertion_results": tuple(results),
                "missing_evidence": (first.assertion_id,),
            }
        )

    return judge


def h03_inconclusive(root: Path, reason: InconclusiveReason) -> Built:
    """INCONCLUSIVE with any reason code (the fakes reach only INSUFFICIENT_EVIDENCE naturally)."""
    if reason is InconclusiveReason.INSUFFICIENT_EVIDENCE:
        return h03_case(root, "missing")
    runner = _h03_runner(root)
    with mock.patch.object(runner_module, "judge_h03", _forced_reason(reason)):
        return _built(*runner.execute(runner.preflight(TARGET)))


class _RaiseAfterFault(FakeState):
    """`cases.json` `aborted`: the observer raises once the fault is applied (restore still succeeds)."""

    def snapshot(self, *, subject, phase):
        if phase == "INJECTED":
            raise RuntimeError("synthetic observer failure after fault")
        return super().snapshot(subject=subject, phase=phase)


def h03_aborted(root: Path) -> Built:
    adapters, _ = make_adapters()
    adapters = replace(adapters, state=_RaiseAfterFault())
    runner = RunOrchestrator(load("scenarios/H-03.yaml"), adapters, root, clock=FakeClock())
    return _built(*runner.execute(runner.preflight(TARGET)))


def h03_lineage(root: Path) -> tuple[Built, Built]:
    """Spec 001-format lineage: FAIL parent → PASS child (no parent digest in the retest link)."""
    parent = h03_case(root, "fail")
    child_runner = _h03_runner(root)
    readiness = child_runner.preflight(TARGET)
    child_id = uuid4()
    scenario = child_runner.scenario
    parent_run, _, records = prepare_retest(
        parent.bundle,
        child_run_id=child_id,
        child_target=readiness.target_snapshot,
        child_scenario_version=scenario.version,
        child_scenario_digest=scenario.snapshot().digest,
    )
    child = child_runner.execute(
        readiness, parent_run_id=parent_run.run_id, retest_records=records, run_id=child_id
    )
    return parent, _built(*child)


# --- Spec 002 (E03_AFTER_V2) lineage -----------------------------------------------------------


def _e03_runner(root: Path, **options):
    options.setdefault("injected_reporting_present", True)
    adapters, _ = make_adapters(**options)
    return build_profile_runner(load("scenarios/E-03-AFTER.yaml"), adapters, root, clock=FakeClock())


def e03_lineage(root: Path) -> tuple[Built, Built]:
    """Spec 002-format lineage: parent → child whose manifest carries the parent's origin reference."""
    parent_runner = _e03_runner(root, dlq_presence="ABSENT")
    parent = _built(*parent_runner.execute(parent_runner.preflight(TARGET)))
    child_runner = _e03_runner(root, dlq_presence="ABSENT")
    readiness = child_runner.preflight(TARGET)
    child_id = uuid4()
    parent_run, _, records = prepare_retest(
        parent.bundle,
        child_run_id=child_id,
        child_target=readiness.target_snapshot,
        child_scenario_version=child_runner.scenario.version,
        child_scenario_digest=child_runner.scenario.snapshot().digest,
        child_profile=child_runner.scenario.execution_profile,
        child_fault_variant=child_runner.scenario.fault_variant,
        child_environment=child_runner.adapters.environment.capture_environment(),
        child_queue=child_runner.adapters.queue.capture_topology(),
    )
    child = child_runner.execute(
        readiness, parent_run_id=parent_run.run_id, retest_records=records, run_id=child_id
    )
    return parent, _built(*child)


# --- Spec 004 E-01 / E-02 ----------------------------------------------------------------------


def _spec004_runner(root: Path, scenario: str, *, commit: str | None = None, **options):
    adapters, _ = make_adapters(spec004=FakeSpec004Adapters(**options))
    use_spec004_fixture(adapters)
    if commit:
        original = adapters.target.snapshot
        adapters.target.snapshot = TargetSnapshot.model_validate(
            original.model_dump(mode="json", exclude={"target_version"}) | {"git_commit_sha": commit}
        )
    return build_profile_runner(load(f"scenarios/{scenario}.yaml"), adapters, root, clock=FakeClock())


def spec004_run(root: Path, scenario: str, **options) -> Built:
    """E-01/E-02 Run. E-01 defaults to the P1 FAIL; `removal_indicator="score_null"` gives PASS."""
    runner = _spec004_runner(root, scenario, **options)
    return _built(*runner.execute(runner.preflight(TARGET)))


def _spec004_child(root: Path, parent: Built, scenario: str, **options) -> Built:
    child_runner = _spec004_runner(root, scenario, commit="b" * 40, **options)
    readiness = child_runner.preflight(TARGET)
    raw = child_runner.adapters.environment.capture_environment()
    environment = TargetEnvironmentSnapshot.model_validate(
        raw.model_dump(mode="json", exclude={"snapshot_digest"})
        | {"unverified_scope": sorted(SPEC004_UNVERIFIED_SCOPE)}
    )
    child_id = uuid4()
    parent_run, _, records = prepare_retest(
        parent.bundle,
        child_run_id=child_id,
        child_target=readiness.target_snapshot,
        child_scenario_version=child_runner.scenario.version,
        child_scenario_digest=child_runner.scenario.snapshot().digest,
        child_profile=child_runner.scenario.execution_profile,
        child_environment=environment,
    )
    return _built(
        *child_runner.execute(
            readiness, parent_run_id=parent_run.run_id, retest_records=records, run_id=child_id
        )
    )


def e01_lineage(root: Path) -> tuple[Built, Built, Built]:
    """Spec 004-format lineage: P1 FAIL parent → PASS child → PASS grandchild (parent digest in the link)."""
    parent = spec004_run(root, "E-01")
    child = _spec004_child(root, parent, "E-01", removal_indicator="score_null")
    grandchild = _spec004_child(root, child, "E-01", removal_indicator="score_null")
    return parent, child, grandchild


# --- integrity variants ------------------------------------------------------------------------


def tampered(built: Built) -> Path:
    """Change one sealed file after sealing (the bundle must then verify INVALID)."""
    target = built.bundle / "judgement.json"
    target.write_bytes(target.read_bytes().replace(b'"summary"', b'"summary" ', 1))
    return built.bundle


def unreadable(built: Built) -> Path:
    """Remove the manifest so the bundle cannot be read as sealed."""
    (built.bundle / "manifest.json").unlink()
    return built.bundle
