"""Typed local/test-only configuration with secret-safe errors."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from engine.models import SHA256_RE


class ConfigError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TimingConfig:
    poll_seconds: float = 2.0
    injected_deadline_seconds: float = 30.0
    automatic_decision_window_seconds: float = 10.0
    environment_restore_deadline_seconds: float = 120.0
    stability_consecutive: int = 3
    stability_seconds: float = 4.0


@dataclass(frozen=True, slots=True)
class Settings:
    target_id: str
    run_root: Path
    fault_root: Path
    whyyou_base_url: str
    whyyou_console_url: str
    whyyou_database_url: str
    whyyou_company_token: str
    whyyou_company_id: str
    whyyou_company_user_id: str
    whyyou_repo_path: Path
    model_substitute_enabled: bool
    model_fixture_id: str
    model_fixture_digest: str
    embedding_fixture_id: str = "h03-embedding-v1"
    embedding_fixture_digest: str = ""
    environment_kind: str = "LOCAL_EMULATED"
    aws_deployment_status: str = "NOT_RUN"
    external_ai_allowed: bool = False
    observer_root: Path = Path(".controlproof/observers")
    test_hooks_enabled: bool = False
    observer_enabled: bool = False
    whyyou_aws_endpoint_url: str = "http://localhost:4566"
    whyyou_aws_region: str = "ap-northeast-2"
    reporting_queue_name: str = "iep-reporting"
    reporting_dlq_name: str = "iep-reporting-dlq"
    reporting_max_receive_count: int = 3
    reporting_visibility_timeout_seconds: int = 5
    timing: TimingConfig = TimingConfig()

    @classmethod
    def from_env(cls, environment: dict[str, str] | None = None) -> Settings:
        env = dict(os.environ if environment is None else environment)
        required = (
            "WHYYOU_BASE_URL",
            "WHYYOU_CONSOLE_URL",
            "WHYYOU_DATABASE_URL",
            "WHYYOU_COMPANY_TOKEN",
            "WHYYOU_REPO_PATH",
            "CONTROLPROOF_FAULT_ROOT",
            "CONTROLPROOF_MODEL_FIXTURE_ID",
            "CONTROLPROOF_MODEL_FIXTURE_DIGEST",
        )
        missing = [name for name in required if not env.get(name, "").strip()]
        if missing:
            raise ConfigError(f"required local/test settings are missing: {', '.join(missing)}")
        base_url = env["WHYYOU_BASE_URL"].strip()
        console_url = env["WHYYOU_CONSOLE_URL"].strip()
        database_url = env["WHYYOU_DATABASE_URL"].strip()
        for name, value in (
            ("WHYYOU_BASE_URL", base_url),
            ("WHYYOU_CONSOLE_URL", console_url),
        ):
            _require_local_url(name, value)
        _require_local_database(database_url)
        aws_endpoint = env.get("WHYYOU_AWS_ENDPOINT_URL", "http://localhost:4566").strip()
        _require_local_url("WHYYOU_AWS_ENDPOINT_URL", aws_endpoint)
        enabled = env.get("CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED", "false").casefold() == "true"
        external_ai_allowed = (
            env.get("CONTROLPROOF_EXTERNAL_AI_ALLOWED", "false").casefold() == "true"
        )
        if external_ai_allowed:
            raise ConfigError("external AI must remain disabled for Spec 002 local runs")
        try:
            max_receive_count = int(env.get("WHYYOU_REPORTING_MAX_RECEIVE_COUNT", "3"))
            visibility_timeout = int(
                env.get("WHYYOU_REPORTING_VISIBILITY_TIMEOUT_SECONDS", "5")
            )
        except ValueError as exc:
            raise ConfigError("reporting queue timing must be integer values") from exc
        if max_receive_count != 3:
            raise ConfigError("reporting max receive count must be 3")
        if visibility_timeout != 5:
            raise ConfigError("reporting visibility timeout must be 5 seconds")
        digest = env["CONTROLPROOF_MODEL_FIXTURE_DIGEST"].strip()
        if not SHA256_RE.fullmatch(digest):
            raise ConfigError("CONTROLPROOF_MODEL_FIXTURE_DIGEST must be lowercase SHA-256")
        embedding_digest = env.get(
            "CONTROLPROOF_EMBEDDING_FIXTURE_DIGEST", digest
        ).strip()
        if not SHA256_RE.fullmatch(embedding_digest):
            raise ConfigError(
                "CONTROLPROOF_EMBEDDING_FIXTURE_DIGEST must be lowercase SHA-256"
            )
        run_root = Path(env.get("CONTROLPROOF_RUN_ROOT", ".controlproof/runs")).resolve()
        fault_root = Path(env["CONTROLPROOF_FAULT_ROOT"]).resolve()
        observer_root = Path(
            env.get("CONTROLPROOF_OBSERVER_ROOT", ".controlproof/observers")
        ).resolve()
        return cls(
            target_id=env.get("CONTROLPROOF_TARGET_ID", "whyyou-local").strip(),
            run_root=run_root,
            fault_root=fault_root,
            whyyou_base_url=base_url,
            whyyou_console_url=console_url,
            whyyou_database_url=database_url,
            whyyou_company_token=env["WHYYOU_COMPANY_TOKEN"].strip(),
            whyyou_company_id=env.get(
                "WHYYOU_COMPANY_ID", "00000000-0000-7000-8000-000000000001"
            ).strip(),
            whyyou_company_user_id=env.get(
                "WHYYOU_COMPANY_USER_ID", "00000000-0000-7000-8000-000000000002"
            ).strip(),
            whyyou_repo_path=Path(env["WHYYOU_REPO_PATH"]).resolve(),
            model_substitute_enabled=enabled,
            model_fixture_id=env["CONTROLPROOF_MODEL_FIXTURE_ID"].strip(),
            model_fixture_digest=digest,
            embedding_fixture_id=env.get(
                "CONTROLPROOF_EMBEDDING_FIXTURE_ID", "h03-embedding-v1"
            ).strip(),
            embedding_fixture_digest=embedding_digest,
            environment_kind=env.get(
                "CONTROLPROOF_ENVIRONMENT_KIND", "LOCAL_EMULATED"
            ).strip(),
            aws_deployment_status=env.get(
                "CONTROLPROOF_AWS_DEPLOYMENT_STATUS", "NOT_RUN"
            ).strip(),
            external_ai_allowed=external_ai_allowed,
            observer_root=observer_root,
            test_hooks_enabled=(
                env.get("CONTROLPROOF_TEST_HOOKS_ENABLED", "false").casefold()
                == "true"
            ),
            observer_enabled=(
                env.get("CONTROLPROOF_OBSERVER_ENABLED", "false").casefold() == "true"
            ),
            whyyou_aws_endpoint_url=aws_endpoint,
            whyyou_aws_region=env.get("WHYYOU_AWS_REGION", "ap-northeast-2").strip(),
            reporting_queue_name=env.get(
                "WHYYOU_REPORTING_QUEUE_NAME", "iep-reporting"
            ).strip(),
            reporting_dlq_name=env.get(
                "WHYYOU_REPORTING_DLQ_NAME", "iep-reporting-dlq"
            ).strip(),
            reporting_max_receive_count=max_receive_count,
            reporting_visibility_timeout_seconds=visibility_timeout,
        )

    def validate_spec002_safety(
        self,
        *,
        repo_branch: str | None = None,
        repo_dirty: bool | None = None,
        controlproof_branch: str | None = None,
        controlproof_dirty: bool | None = None,
        whyyou_branch: str | None = None,
        whyyou_dirty: bool | None = None,
    ) -> None:
        if self.target_id != "whyyou-local":
            raise ConfigError("Spec 002 target must be whyyou-local")
        if self.environment_kind != "LOCAL_EMULATED":
            raise ConfigError("Spec 002 environment must be LOCAL_EMULATED")
        if self.aws_deployment_status != "NOT_RUN":
            raise ConfigError("local AWS deployment status must be NOT_RUN")
        if not self.model_substitute_enabled or self.external_ai_allowed:
            raise ConfigError("fixed model substitute is required and external AI must be disabled")
        if not self.embedding_fixture_id or not SHA256_RE.fullmatch(
            self.embedding_fixture_digest
        ):
            raise ConfigError("fixed embedding fixture is required")
        if self.reporting_queue_name != "iep-reporting" or self.reporting_dlq_name != "iep-reporting-dlq":
            raise ConfigError("official reporting queue and DLQ names are required")
        active_whyyou_branch = whyyou_branch or repo_branch
        active_whyyou_dirty = whyyou_dirty if whyyou_dirty is not None else repo_dirty
        if active_whyyou_branch is None or active_whyyou_dirty is None:
            raise ConfigError("WhyYou git identity must be supplied")
        normalized = active_whyyou_branch.strip().casefold()
        if normalized in {"main", "master"}:
            raise ConfigError("WhyYou main branch cannot be used for a modifying Spec 002 Run")
        if active_whyyou_dirty:
            raise ConfigError("WhyYou checkout must be clean before a Spec 002 Run")
        if controlproof_branch is not None or controlproof_dirty is not None:
            if controlproof_branch is None or controlproof_dirty is None:
                raise ConfigError("ControlProof git identity must be supplied as one snapshot")
            if controlproof_dirty:
                raise ConfigError("ControlProof checkout must be clean before a Spec 002 Run")

    def safe_projection(self) -> dict[str, str | bool]:
        return {
            "target_id": self.target_id,
            "run_root": str(self.run_root),
            "fault_root": str(self.fault_root),
            "whyyou_base_url": self.whyyou_base_url,
            "whyyou_console_url": self.whyyou_console_url,
            "whyyou_repo_path": str(self.whyyou_repo_path),
            "model_substitute_enabled": self.model_substitute_enabled,
            "model_fixture_id": self.model_fixture_id,
            "model_fixture_digest": self.model_fixture_digest,
            "embedding_fixture_id": self.embedding_fixture_id,
            "embedding_fixture_digest": self.embedding_fixture_digest,
            "environment_kind": self.environment_kind,
            "aws_deployment_status": self.aws_deployment_status,
            "external_ai_allowed": self.external_ai_allowed,
            "whyyou_aws_endpoint_url": self.whyyou_aws_endpoint_url,
            "whyyou_aws_region": self.whyyou_aws_region,
            "reporting_queue_name": self.reporting_queue_name,
            "reporting_dlq_name": self.reporting_dlq_name,
            "reporting_max_receive_count": str(self.reporting_max_receive_count),
            "reporting_visibility_timeout_seconds": str(
                self.reporting_visibility_timeout_seconds
            ),
            "observer_root": str(self.observer_root),
            "test_hooks_enabled": self.test_hooks_enabled,
            "observer_enabled": self.observer_enabled,
        }

    def validate_n02_safety(
        self,
        *,
        controlproof_branch: str,
        controlproof_dirty: bool,
        whyyou_branch: str,
        whyyou_dirty: bool,
    ) -> None:
        """Fail closed before an N-02 Run can create subjects or marker files."""

        if self.target_id != "whyyou-local":
            raise ConfigError("N-02 target must be whyyou-local")
        if self.environment_kind != "LOCAL_EMULATED" or self.aws_deployment_status != "NOT_RUN":
            raise ConfigError("N-02 requires LOCAL_EMULATED with AWS NOT_RUN")
        if not self.model_substitute_enabled or self.external_ai_allowed:
            raise ConfigError("N-02 requires fixed AI fixtures and denies external AI")
        if not self.embedding_fixture_id or not SHA256_RE.fullmatch(
            self.embedding_fixture_digest
        ):
            raise ConfigError("N-02 requires a fixed embedding fixture")
        for name, branch, dirty in (
            ("ControlProof", controlproof_branch, controlproof_dirty),
            ("WhyYou", whyyou_branch, whyyou_dirty),
        ):
            if not branch.strip():
                raise ConfigError(f"{name} git branch must be supplied")
            if dirty:
                raise ConfigError(f"{name} checkout must be clean before an N-02 Run")
        if whyyou_branch.strip().casefold() in {"main", "master"}:
            raise ConfigError("WhyYou main branch cannot be used for an N-02 Run")
        if not self.test_hooks_enabled or not self.observer_enabled:
            raise ConfigError("N-02 local test hook and observer must both be enabled")
        _require_bounded_root("CONTROLPROOF_FAULT_ROOT", self.fault_root)
        _require_bounded_root("CONTROLPROOF_OBSERVER_ROOT", self.observer_root)


def _require_local_url(name: str, value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "host.docker.internal",
    }:
        raise ConfigError(f"{name} must point to an allowlisted local/test host")


def _require_local_database(value: str) -> None:
    parsed = urlparse(value.replace("postgresql+psycopg", "postgresql", 1))
    if parsed.hostname not in {"localhost", "127.0.0.1", "host.docker.internal", "postgres"}:
        raise ConfigError("WHYYOU_DATABASE_URL must point to an allowlisted local/test host")


def _require_bounded_root(name: str, value: Path) -> None:
    resolved = value.resolve()
    if resolved == Path(resolved.anchor) or len(resolved.parts) < 3:
        raise ConfigError(f"{name} must be a bounded non-root directory")
