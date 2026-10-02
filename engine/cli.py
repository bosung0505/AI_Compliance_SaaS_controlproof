"""ControlProof command-line contract for Spec 001."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import ValidationError

from engine.adapters.whyyou.adapter import create_whyyou_adapter
from engine.config import ConfigError, Settings
from engine.evidence import redact, verify_bundle
from engine.lifecycle import RestoreBlockStore
from engine.models import (
    SPEC002_UNVERIFIED_SCOPE,
    SPEC003_UNVERIFIED_SCOPE,
    AwsDeploymentStatus,
    EnvironmentKind,
    ExecutionProfile,
    ProtectedPathId,
    ReadinessStatus,
    RunState,
    TargetEnvironmentSnapshot,
    Verdict,
)
from engine.presentation import load_bundle_summary, render_human
from engine.retest import RetestError, assert_parent_unchanged, prepare_retest
from engine.runner import RunOrchestrator, build_profile_runner
from engine.scenario import load

SCHEMA_VERSION = "controlproof.cli.v1"
EXIT_USAGE = 1
EXIT_NOT_READY = 2
EXIT_FAIL = 3
EXIT_INCONCLUSIVE = 4
EXIT_INTEGRITY = 5
EXIT_RESTORE = 6


class CliContractError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code


def create_runtime(settings: Settings, scenario_path: Path) -> RunOrchestrator:
    adapters, _client = create_whyyou_adapter(settings)
    return build_profile_runner(load(scenario_path), adapters, settings.run_root)


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (
        ConfigError,
        ValueError,
        ValidationError,
        FileNotFoundError,
        RetestError,
    ) as exc:
        _emit(
            {
                "schema_version": SCHEMA_VERSION,
                "command": getattr(args, "command", None),
                "error": exc.code if isinstance(exc, CliContractError) else type(exc).__name__,
                "detail": str(exc),
            },
            as_json=getattr(args, "json", False),
            error=True,
        )
        return EXIT_USAGE
    except KeyboardInterrupt:
        _emit(
            {
                "schema_version": SCHEMA_VERSION,
                "command": getattr(args, "command", None),
                "error": "INTERRUPTED",
                "detail": "사용자가 작업을 중단했습니다.",
            },
            as_json=getattr(args, "json", False),
            error=True,
        )
        return EXIT_INCONCLUSIVE


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="controlproof")
    sub = parser.add_subparsers(dest="command", required=True)

    preflight = sub.add_parser("preflight")
    _scenario_args(preflight)
    preflight.set_defaults(handler=_preflight)

    run = sub.add_parser("run")
    _scenario_args(run)
    run.add_argument("--label")
    run.add_argument("--operator", default="local-operator")
    run.set_defaults(handler=_run)

    show = sub.add_parser("show")
    _bundle_args(show)
    show.set_defaults(handler=_show)

    verify = sub.add_parser("verify")
    _bundle_args(verify)
    verify.set_defaults(handler=_verify)

    retest = sub.add_parser("retest")
    retest.add_argument("parent")
    retest.add_argument("--target", required=True)
    retest.add_argument("--label")
    retest.add_argument("--operator", default="local-operator")
    retest.add_argument("--run-root", type=Path)
    retest.add_argument("--scenario-file", type=Path)
    retest.add_argument("--json", action="store_true")
    retest.set_defaults(handler=_retest)

    cleanup = sub.add_parser("cleanup-confirm")
    cleanup.add_argument("--target", required=True)
    cleanup.add_argument("--subject", required=True)
    cleanup.add_argument("--evidence", required=True, type=Path)
    cleanup.add_argument("--run-root", type=Path)
    cleanup.add_argument("--scenario-file", type=Path, default=_default_scenario())
    cleanup.add_argument("--json", action="store_true")
    cleanup.set_defaults(handler=_cleanup_confirm)
    return parser


def _scenario_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("scenario_id")
    parser.add_argument("--target", required=True)
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--profile", choices=[item.value for item in ExecutionProfile])
    parser.add_argument("--scenario-file", type=Path)
    parser.add_argument("--json", action="store_true")


def _bundle_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("run")
    parser.add_argument("--run-root", type=Path, default=Path(".controlproof/runs"))
    parser.add_argument("--json", action="store_true")


def _default_scenario() -> Path:
    return Path(__file__).resolve().parents[1] / "scenarios" / "H-03.yaml"


def _settings(args: argparse.Namespace) -> Settings:
    settings = Settings.from_env()
    updates: dict[str, Any] = {}
    if getattr(args, "run_root", None) is not None:
        updates["run_root"] = args.run_root.resolve()
    if getattr(args, "target", None) is not None:
        updates["target_id"] = args.target
    if updates:
        from dataclasses import replace

        settings = replace(settings, **updates)
    return settings


def _preflight(args: argparse.Namespace) -> int:
    scenario_path, selected_profile = _scenario_selection(args)
    settings = _settings(args)
    runtime = create_runtime(settings, scenario_path)
    _validate_runtime_selection(runtime, args.scenario_id, selected_profile)
    readiness = runtime.preflight(args.target)
    payload = _readiness_payload(readiness, runtime.scenario)
    if selected_profile is ExecutionProfile.N02_CONSENT_ORDER_V1:
        _add_n02_paths(payload, runtime)
    _emit(payload, as_json=args.json)
    return 0 if payload["readiness"] == ReadinessStatus.READY.value else EXIT_NOT_READY


def _run(args: argparse.Namespace) -> int:
    scenario_path, selected_profile = _scenario_selection(args)
    settings = _settings(args)
    runtime = create_runtime(settings, scenario_path)
    _validate_runtime_selection(runtime, args.scenario_id, selected_profile)
    readiness = runtime.preflight(args.target)
    payload = _readiness_payload(readiness, runtime.scenario)
    if selected_profile is ExecutionProfile.N02_CONSENT_ORDER_V1:
        _add_n02_paths(payload, runtime)
    if payload["readiness"] != ReadinessStatus.READY.value:
        _emit(payload, as_json=args.json)
        return EXIT_NOT_READY
    run, judgement, bundle = runtime.execute(
        readiness,
        operator_id=args.operator,
        label=args.label,
    )
    payload = _run_payload(run, judgement, bundle)
    _emit(payload, as_json=args.json)
    return _run_exit(run.state, judgement.verdict)


def _show(args: argparse.Namespace) -> int:
    bundle = _resolve_bundle(args.run, args.run_root)
    summary = load_bundle_summary(bundle)
    payload = _projection_payload("show", summary)
    _emit(payload, as_json=args.json, human=render_human(summary))
    return 0


def _verify(args: argparse.Namespace) -> int:
    bundle = _resolve_bundle(args.run, args.run_root)
    result = verify_bundle(bundle)
    run_id = _run_id_from_bundle(bundle)
    run_payload = json.loads((bundle / "run.json").read_text(encoding="utf-8"))
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "command": "verify",
        "run_id": run_id,
        "execution_profile": run_payload.get("execution_profile") or "H03_MINIMAL_V1",
        "profile_contract": manifest.get("profile_contract"),
        "checked_evidence_requirements": sorted(
            manifest.get("required_evidence", {}).keys()
        ),
        **result,
    }
    _emit(payload, as_json=args.json)
    return 0 if result["bundle_status"] == "VERIFIED" else EXIT_INTEGRITY


def _retest(args: argparse.Namespace) -> int:
    settings = _settings(args)
    parent_bundle = _resolve_bundle(args.parent, settings.run_root)
    parent_payload = json.loads((parent_bundle / "run.json").read_text(encoding="utf-8"))
    parent_profile = ExecutionProfile(
        parent_payload.get("execution_profile") or ExecutionProfile.H03_MINIMAL_V1.value
    )
    scenario_path = args.scenario_file or _profile_scenario_path(parent_profile)
    runtime = create_runtime(settings, scenario_path)
    _validate_runtime_selection(runtime, parent_payload["scenario_id"], parent_profile)
    readiness = runtime.preflight(args.target)
    readiness_payload = _readiness_payload(readiness, runtime.scenario)
    if parent_profile is ExecutionProfile.N02_CONSENT_ORDER_V1:
        _add_n02_paths(readiness_payload, runtime)
    if readiness_payload["readiness"] != ReadinessStatus.READY.value:
        _emit(readiness_payload, as_json=args.json)
        return EXIT_NOT_READY
    child_id = uuid4()
    child_environment = None
    if parent_profile is not ExecutionProfile.H03_MINIMAL_V1:
        child_environment = runtime.adapters.environment.capture_environment()
        if parent_profile is ExecutionProfile.N02_CONSENT_ORDER_V1:
            child_environment = TargetEnvironmentSnapshot.model_validate(
                child_environment.model_dump(mode="json", exclude={"snapshot_digest"})
                | {"unverified_scope": sorted(SPEC003_UNVERIFIED_SCOPE)}
            )
    child_queue = (
        runtime.adapters.queue.capture_topology()
        if parent_profile not in {
            ExecutionProfile.H03_MINIMAL_V1,
            ExecutionProfile.N02_CONSENT_ORDER_V1,
        }
        else None
    )
    parent_run, parent_digest, records = prepare_retest(
        parent_bundle,
        child_run_id=child_id,
        child_target=readiness.target_snapshot,
        child_scenario_version=runtime.scenario.version,
        child_scenario_digest=runtime.scenario.snapshot().digest,
        child_profile=runtime.scenario.execution_profile,
        child_fault_variant=runtime.scenario.fault_variant,
        child_environment=child_environment,
        child_queue=child_queue,
    )
    run, judgement, bundle = runtime.execute(
        readiness,
        operator_id=args.operator,
        parent_run_id=parent_run.run_id,
        label=args.label,
        retest_records=records,
        run_id=child_id,
    )
    assert_parent_unchanged(parent_bundle, parent_digest)
    payload = _run_payload(run, judgement, bundle)
    payload["command"] = "retest"
    payload["parent_run_id"] = str(parent_run.run_id)
    _emit(payload, as_json=args.json)
    return _run_exit(run.state, judgement.verdict)


def _cleanup_confirm(args: argparse.Namespace) -> int:
    if not args.evidence.is_file():
        raise FileNotFoundError("cleanup evidence file is required")
    settings = _settings(args)
    runtime = create_runtime(settings, args.scenario_file)
    safe = runtime.adapters.fault.target_safe(subject_ref=args.subject)
    evidence = args.evidence.read_bytes()
    record = RestoreBlockStore(settings.run_root).confirm_cleanup(
        args.target,
        args.subject,
        evidence_sha256=hashlib.sha256(evidence).hexdigest(),
        target_safe=safe,
    )
    _emit(
        {"schema_version": SCHEMA_VERSION, "command": "cleanup-confirm", **record},
        as_json=args.json,
    )
    return 0


def _readiness_payload(readiness, scenario=None) -> dict[str, Any]:
    profile = getattr(scenario, "execution_profile", None)
    is_versioned = profile is not None and profile is not ExecutionProfile.H03_MINIMAL_V1
    return {
        "schema_version": SCHEMA_VERSION,
        "command": "preflight",
        "scenario_id": readiness.scenario_id,
        "scenario_version": readiness.scenario_version,
        "execution_profile": profile.value if profile else ExecutionProfile.H03_MINIMAL_V1.value,
        "fault_variant": (
            scenario.fault_variant.value if getattr(scenario, "fault_variant", None) else None
        ),
        "claim_scope": "EXECUTED_SCENARIO_AND_EVIDENCE_ONLY",
        "target_id": readiness.target_id,
        "environment_kind": EnvironmentKind.LOCAL_EMULATED.value if is_versioned else None,
        "aws_deployment_status": AwsDeploymentStatus.NOT_RUN.value if is_versioned else None,
        "unverified_scope": (
            ["AWS", "N-01", "N-03"]
            if profile is ExecutionProfile.N02_CONSENT_ORDER_V1
            else sorted(SPEC002_UNVERIFIED_SCOPE) if is_versioned else []
        ),
        "target_version": readiness.target_version,
        "target_snapshot": (
            readiness.target_snapshot.model_dump(mode="json") if readiness.target_snapshot else None
        ),
        "model_fixture_id": readiness.model_fixture_id,
        "model_fixture_digest": readiness.model_fixture_digest,
        "implementation_status": readiness.implementation_status.value,
        "readiness": readiness.status.value,
        "checks": [check.model_dump(mode="json") for check in readiness.checks],
        "operator_action": readiness.operator_action,
        "checked_at": readiness.checked_at.isoformat(),
    }


def _add_n02_paths(payload: dict[str, Any], runtime: Any) -> None:
    """Project only read-only path identity; Run-owned digests come later."""
    try:
        processing = runtime.adapters.n02_processing
        paths = processing.paths() if processing is not None else ()
        names = [item.path_id.value for item in paths]
        if set(names) != {path.value for path in ProtectedPathId} or len(names) != len(ProtectedPathId):
            raise ValueError("incomplete protected paths")
        payload["protected_paths"] = names
    except Exception:  # noqa: BLE001 - never project adapter details into CLI output
        payload["protected_paths"] = []
        payload["readiness"] = ReadinessStatus.RUNNER_NOT_READY.value
        payload["operator_action"] = (
            "N-02 보호 대상 경로 capability를 읽을 수 없습니다. "
            "로컬 adapter 설정과 경로 등록을 확인한 뒤 preflight를 다시 실행하세요."
        )


def _run_payload(run, judgement, bundle: Path) -> dict[str, Any]:
    summary = load_bundle_summary(bundle)
    return {**_projection_payload("run", summary), "bundle_path": str(bundle)}


def _scenario_selection(
    args: argparse.Namespace,
) -> tuple[Path, ExecutionProfile]:
    raw_profile = getattr(args, "profile", None)
    if args.scenario_id in {"E-03", "N-02"} and raw_profile is None:
        raise CliContractError(
            "PROFILE_REQUIRED",
            f"{args.scenario_id} requires an explicit compatible --profile",
        )
    profile = (
        ExecutionProfile(raw_profile)
        if raw_profile is not None
        else ExecutionProfile.H03_MINIMAL_V1
    )
    allowed = {
        "H-03": {ExecutionProfile.H03_MINIMAL_V1, ExecutionProfile.H03_DLQ_V2},
        "E-03": {ExecutionProfile.E03_BEFORE_V2, ExecutionProfile.E03_AFTER_V2},
        "N-02": {ExecutionProfile.N02_CONSENT_ORDER_V1},
    }
    if profile not in allowed.get(args.scenario_id, set()):
        raise CliContractError(
            "PROFILE_MISMATCH",
            f"{profile.value} does not belong to {args.scenario_id}",
        )
    return args.scenario_file or _profile_scenario_path(profile), profile


def _profile_scenario_path(profile: ExecutionProfile) -> Path:
    root = Path(__file__).resolve().parents[1] / "scenarios"
    return {
        ExecutionProfile.H03_MINIMAL_V1: root / "H-03.yaml",
        ExecutionProfile.H03_DLQ_V2: root / "H-03-DLQ.yaml",
        ExecutionProfile.E03_BEFORE_V2: root / "E-03-BEFORE.yaml",
        ExecutionProfile.E03_AFTER_V2: root / "E-03-AFTER.yaml",
        ExecutionProfile.N02_CONSENT_ORDER_V1: root / "N-02.yaml",
    }[profile]


def _validate_runtime_selection(
    runtime: Any, scenario_id: str, profile: ExecutionProfile
) -> None:
    active = runtime.scenario.execution_profile or ExecutionProfile.H03_MINIMAL_V1
    if runtime.scenario.scenario_id != scenario_id or active is not profile:
        raise CliContractError(
            "PROFILE_MISMATCH", "scenario ID, profile, and scenario file do not match"
        )


def _projection_payload(command: str, summary: dict[str, Any]) -> dict[str, Any]:
    projection = dict(summary)
    projection_schema = projection.pop("schema_version", None)
    return {
        **projection,
        "projection_schema_version": projection_schema,
        "schema_version": SCHEMA_VERSION,
        "command": command,
    }


def _run_exit(state: RunState, verdict: Verdict) -> int:
    if state is RunState.RESTORE_FAILED:
        return EXIT_RESTORE
    if verdict is Verdict.PASS:
        return 0
    if verdict is Verdict.FAIL:
        return EXIT_FAIL
    return EXIT_INCONCLUSIVE


def _resolve_bundle(value: str, run_root: Path) -> Path:
    direct = Path(value)
    if direct.is_dir():
        return direct.resolve()
    try:
        run_id = UUID(value)
    except ValueError as exc:
        raise FileNotFoundError(f"Run bundle not found: {value}") from exc
    candidate = run_root.resolve() / str(run_id)
    if not candidate.is_dir():
        raise FileNotFoundError(f"Run bundle not found: {value}")
    return candidate


def _run_id_from_bundle(bundle: Path) -> str | None:
    try:
        value = json.loads((bundle / "run.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value.get("run_id")


def _emit(
    payload: dict[str, Any],
    *,
    as_json: bool,
    error: bool = False,
    human: str | None = None,
) -> None:
    safe = redact(payload)
    stream = sys.stderr if error and not as_json else sys.stdout
    if as_json:
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True), file=stream)
    else:
        print(human or safe.get("detail") or json.dumps(safe, ensure_ascii=False), file=stream)


if __name__ == "__main__":
    raise SystemExit(main())
