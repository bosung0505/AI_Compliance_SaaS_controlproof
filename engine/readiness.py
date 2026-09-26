"""Separate target presence, runner implementation, access, and runtime readiness."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from engine.adapters.base import CapabilityProbeResult
from engine.models import (
    ImplementationStatus,
    ReadinessCheck,
    ReadinessStatus,
    ScenarioReadiness,
    TargetSnapshot,
)
from engine.scenario import ScenarioDefinition


def calculate_implementation_status(
    required: Mapping[str, str],
    registered: Mapping[str, str],
) -> ImplementationStatus:
    matching = sum(
        registered.get(capability) == version for capability, version in required.items()
    )
    if not registered or matching == 0:
        return ImplementationStatus.NOT_IMPLEMENTED
    if matching != len(required):
        return ImplementationStatus.PARTIAL
    return ImplementationStatus.IMPLEMENTED


def evaluate_readiness(
    scenario: ScenarioDefinition,
    *,
    target_id: str,
    registrations: Mapping[str, str],
    probe_results: Sequence[CapabilityProbeResult],
    target_feature_exists: bool,
    target_snapshot: TargetSnapshot | None,
) -> ScenarioReadiness:
    implementation = calculate_implementation_status(
        scenario.required_capabilities,
        registrations,
    )
    by_capability = {result.capability: result for result in probe_results}
    checks: list[ReadinessCheck] = []
    for capability, required_version in scenario.required_capabilities.items():
        registered_version = registrations.get(capability)
        if registered_version != required_version:
            checks.append(
                ReadinessCheck(
                    capability=capability,
                    status=ReadinessStatus.RUNNER_NOT_READY,
                    detail=(
                        f"required contract {required_version}; registered "
                        f"{registered_version or 'none'}"
                    ),
                    operator_action="install or update the matching capability handler",
                )
            )
            continue
        result = by_capability.get(capability)
        if result is None:
            checks.append(
                ReadinessCheck(
                    capability=capability,
                    status=ReadinessStatus.RUNNER_NOT_READY,
                    detail="capability probe did not return a result",
                    operator_action="repair the capability probe",
                )
            )
            continue
        checks.append(
            ReadinessCheck(
                capability=result.capability,
                status=result.status,
                detail=result.detail,
                operator_action=result.operator_action,
            )
        )

    if not target_feature_exists:
        status = ReadinessStatus.NO_TEST_TARGET
        action = "select a target that exposes the H-03 reporting and final-decision controls"
    elif any(check.status is ReadinessStatus.ACCESS_BLOCKED for check in checks):
        status = ReadinessStatus.ACCESS_BLOCKED
        action = _actions(checks, status)
    elif implementation is not ImplementationStatus.IMPLEMENTED:
        status = ReadinessStatus.RUNNER_NOT_READY
        action = "complete every required capability handler at contract v1"
    elif target_snapshot is None:
        status = ReadinessStatus.RUNNER_NOT_READY
        action = "repair canonical target snapshot capture before running"
    elif target_snapshot.git_dirty:
        status = ReadinessStatus.RUNNER_NOT_READY
        action = "use a clean WhyYou checkout; the dirty digest is diagnostic only"
    elif any(check.status is not ReadinessStatus.READY for check in checks):
        status = ReadinessStatus.RUNNER_NOT_READY
        action = _actions(checks, status)
    else:
        status = ReadinessStatus.READY
        action = None

    return ScenarioReadiness(
        scenario_id=scenario.scenario_id,
        scenario_version=scenario.version,
        target_id=target_id,
        implementation_status=implementation,
        status=status,
        checks=tuple(checks),
        target_version=target_snapshot.target_version if target_snapshot else None,
        target_snapshot=target_snapshot,
        model_fixture_id=target_snapshot.model_fixture_id if target_snapshot else None,
        model_fixture_digest=target_snapshot.model_fixture_digest if target_snapshot else None,
        operator_action=action,
    )


def _actions(checks: Sequence[ReadinessCheck], status: ReadinessStatus) -> str:
    actions = [
        check.operator_action
        for check in checks
        if check.status is status and check.operator_action
    ]
    if not actions:
        actions = [
            check.operator_action
            for check in checks
            if check.status is not ReadinessStatus.READY and check.operator_action
        ]
    return "; ".join(dict.fromkeys(actions)) or "inspect readiness checks and repair the target"
