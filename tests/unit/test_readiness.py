from __future__ import annotations

import pytest

from engine.adapters.base import CapabilityProbeResult
from engine.adapters.whyyou.capability import CAPABILITY_VERSIONS
from engine.models import ImplementationStatus, ReadinessStatus
from engine.readiness import evaluate_readiness
from engine.scenario import load


def _results(status=ReadinessStatus.READY):
    return [
        CapabilityProbeResult(capability, status, "fixture") for capability in CAPABILITY_VERSIONS
    ]


@pytest.mark.parametrize(
    "registrations,expected_implementation",
    [
        ({}, ImplementationStatus.NOT_IMPLEMENTED),
        ({"target.version.read": "v1"}, ImplementationStatus.PARTIAL),
    ],
)
def test_incomplete_runner_is_not_ready(
    target_snapshot,
    registrations,
    expected_implementation,
):
    result = evaluate_readiness(
        load("scenarios/H-03.yaml"),
        target_id="whyyou-local",
        registrations=registrations,
        probe_results=_results(),
        target_feature_exists=True,
        target_snapshot=target_snapshot,
    )
    assert result.status is ReadinessStatus.RUNNER_NOT_READY
    assert result.implementation_status is expected_implementation


def test_target_absence_wins_over_runner_gaps():
    result = evaluate_readiness(
        load("scenarios/H-03.yaml"),
        target_id="whyyou-local",
        registrations={},
        probe_results=[],
        target_feature_exists=False,
        target_snapshot=None,
    )
    assert result.status is ReadinessStatus.NO_TEST_TARGET


def test_access_blocked_precedes_other_probe_gaps(target_snapshot):
    rows = _results()
    rows[0] = CapabilityProbeResult(
        rows[0].capability,
        ReadinessStatus.ACCESS_BLOCKED,
        "credential denied",
        "provide local credential",
    )
    rows[1] = CapabilityProbeResult(
        rows[1].capability,
        ReadinessStatus.RUNNER_NOT_READY,
        "hook absent",
        "enable local hook",
    )
    result = evaluate_readiness(
        load("scenarios/H-03.yaml"),
        target_id="whyyou-local",
        registrations=CAPABILITY_VERSIONS,
        probe_results=rows,
        target_feature_exists=True,
        target_snapshot=target_snapshot,
    )
    assert result.status is ReadinessStatus.ACCESS_BLOCKED


def test_every_capability_ready_allows_run(target_snapshot):
    result = evaluate_readiness(
        load("scenarios/H-03.yaml"),
        target_id="whyyou-local",
        registrations=CAPABILITY_VERSIONS,
        probe_results=_results(),
        target_feature_exists=True,
        target_snapshot=target_snapshot,
    )
    assert result.status is ReadinessStatus.READY
    assert result.target_version == target_snapshot.target_version
