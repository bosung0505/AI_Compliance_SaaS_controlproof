"""T010 — Spec 009 preflight: READY / ACCESS_BLOCKED / RUNNER_NOT_READY and contract capability names.

Every probe is a fake (tests/fixtures/fake_spec009.FakeProbes); nothing touches git, HTTP, a DB or a browser.
"""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from engine.executors.n01 import N01Executor
from engine.executors.n03 import N03Executor
from engine.scenario import load
from tests.fixtures.fake_spec009 import FakeProbes, spec009_settings, spec009_target

N01 = load("scenarios/N-01.yaml")
N03 = load("scenarios/N-03.yaml")
N01_CAPABILITIES = {
    "target.version.read",
    "target.environment.read",
    "applicant.screen.open",
    "browser.chromium.available",
    "n01.invitations.seed",
    "n01.invitations.teardown",
    "consent.policy.read",
    "consent.state.read",
}
N03_CAPABILITIES = {
    "target.version.read",
    "target.environment.read",
    "n02.subjects.seed",
    "n02.subjects.teardown",
    "consent.policy.read",
    "consent.commit.write",
    "consent.state.read",
}


@pytest.fixture
def target(target_snapshot):
    return spec009_target(target_snapshot)


def _preflight(executor_type, scenario, tmp_path, target, *, settings=None, **probe_overrides):
    adapters = SimpleNamespace(
        spec009_seed=SimpleNamespace(settings=settings or spec009_settings(tmp_path)),
        spec009_probes=FakeProbes(target, **probe_overrides),
    )
    before = {path for path in tmp_path.rglob("*")}
    readiness = executor_type(scenario, adapters, tmp_path / "runs").preflight("whyyou-local")
    assert {path for path in tmp_path.rglob("*")} == before  # preflight has no side effects
    return readiness


def _check(readiness, capability):
    return next(check for check in readiness.checks if check.capability == capability)


@pytest.mark.parametrize(
    ("executor_type", "scenario", "capabilities"),
    [(N01Executor, N01, N01_CAPABILITIES), (N03Executor, N03, N03_CAPABILITIES)],
)
def test_ready_with_contract_capability_names(tmp_path, target, executor_type, scenario, capabilities) -> None:
    readiness = _preflight(executor_type, scenario, tmp_path, target)
    assert readiness.status.value == "READY", readiness.checks
    assert {check.capability for check in readiness.checks} == capabilities == set(scenario.required_capabilities)
    assert readiness.target_version == target.target_version
    assert readiness.implementation_status.value == "IMPLEMENTED"


def test_n01_app_without_response_is_access_blocked(tmp_path, target) -> None:
    readiness = _preflight(N01Executor, N01, tmp_path, target, app=httpx.ConnectError("refused"))
    assert readiness.status.value == "ACCESS_BLOCKED"
    assert _check(readiness, "applicant.screen.open").status.value == "ACCESS_BLOCKED"
    assert readiness.operator_action


def test_n01_app_url_missing_is_access_blocked(tmp_path, target) -> None:
    readiness = _preflight(N01Executor, N01, tmp_path, target, settings=spec009_settings(tmp_path, applicant_app_url=None))
    assert _check(readiness, "applicant.screen.open").status.value == "ACCESS_BLOCKED"


@pytest.mark.parametrize(("executor_type", "scenario"), [(N01Executor, N01), (N03Executor, N03)])
def test_api_401_is_access_blocked(tmp_path, target, executor_type, scenario) -> None:
    readiness = _preflight(executor_type, scenario, tmp_path, target, api={"/openapi.json": (401, {})})
    assert readiness.status.value == "ACCESS_BLOCKED"
    assert _check(readiness, "consent.policy.read").status.value == "ACCESS_BLOCKED"


def test_n01_missing_chromium_is_runner_not_ready(tmp_path, target) -> None:
    readiness = _preflight(N01Executor, N01, tmp_path, target, chromium=False)
    assert readiness.status.value == "RUNNER_NOT_READY"
    assert _check(readiness, "browser.chromium.available").status.value == "RUNNER_NOT_READY"
    assert _check(readiness, "applicant.screen.open").status.value == "READY"


@pytest.mark.parametrize(("executor_type", "scenario"), [(N01Executor, N01), (N03Executor, N03)])
def test_dirty_source_is_runner_not_ready(tmp_path, target, executor_type, scenario) -> None:
    readiness = _preflight(executor_type, scenario, tmp_path, target, dirty=True)
    assert readiness.status.value == "RUNNER_NOT_READY"
    assert _check(readiness, "target.version.read").detail == "SPEC009_CLEAN_FEATURE_SOURCES_REQUIRED"


def test_n03_isolation_fixture_or_python_missing_is_runner_not_ready(tmp_path, target) -> None:
    unsafe = spec009_settings(tmp_path, external_ai_allowed=True)
    readiness = _preflight(N03Executor, N03, tmp_path, target, settings=unsafe)
    assert _check(readiness, "target.environment.read").detail == "SPEC009_ISOLATED_FIXTURE_REQUIRED"
    assert readiness.status.value == "RUNNER_NOT_READY"
    readiness = _preflight(N03Executor, N03, tmp_path, target, python=False)
    assert _check(readiness, "target.environment.read").detail == "SPEC009_WHYYOU_PYTHON_REQUIRED"


def test_n03_missing_consent_path_or_table_is_runner_not_ready(tmp_path, target) -> None:
    readiness = _preflight(N03Executor, N03, tmp_path, target, api={"/openapi.json": (200, {"paths": {}})})
    assert _check(readiness, "consent.commit.write").detail == "SPEC009_TARGET_PATH_MISSING"
    assert readiness.status.value == "RUNNER_NOT_READY"
    readiness = _preflight(N03Executor, N03, tmp_path, target, db_missing={"applicant_access_sessions"})
    assert _check(readiness, "n02.subjects.seed").status.value == "RUNNER_NOT_READY"
    assert _check(readiness, "consent.state.read").status.value == "READY"


def test_n01_missing_token_table_blocks_invitation_seed(tmp_path, target) -> None:
    readiness = _preflight(N01Executor, N01, tmp_path, target, db_missing={"applicant_access_tokens"})
    assert _check(readiness, "n01.invitations.seed").status.value == "RUNNER_NOT_READY"
    assert readiness.status.value == "RUNNER_NOT_READY"


def test_unproven_live_fixture_and_unreachable_target(tmp_path, target) -> None:
    health = (200, {"controlproof": {"fixture_id": "other", "fixture_digest": "0" * 64, "external_ai_isolated": True}})
    readiness = _preflight(N03Executor, N03, tmp_path, target, api={"/internal/controlproof/health": health})
    assert _check(readiness, "target.environment.read").detail == "SPEC009_LIVE_FIXTURE_UNPROVEN"
    readiness = _preflight(N03Executor, N03, tmp_path, target, target_error=httpx.ConnectError("refused"))
    assert readiness.status.value == "ACCESS_BLOCKED"
    assert _check(readiness, "target.version.read").status.value == "ACCESS_BLOCKED"
    assert readiness.target_snapshot is None


def test_wrong_target_id_is_runner_not_ready(tmp_path, target) -> None:
    adapters = SimpleNamespace(
        spec009_seed=SimpleNamespace(settings=spec009_settings(tmp_path)), spec009_probes=FakeProbes(target)
    )
    readiness = N03Executor(N03, adapters, tmp_path / "runs").preflight("other-target")
    assert readiness.status.value != "READY"
