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
    whyyou_repo_path: Path
    model_substitute_enabled: bool
    model_fixture_id: str
    model_fixture_digest: str
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
        enabled = env.get("CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED", "false").casefold() == "true"
        digest = env["CONTROLPROOF_MODEL_FIXTURE_DIGEST"].strip()
        if not SHA256_RE.fullmatch(digest):
            raise ConfigError("CONTROLPROOF_MODEL_FIXTURE_DIGEST must be lowercase SHA-256")
        run_root = Path(env.get("CONTROLPROOF_RUN_ROOT", ".controlproof/runs")).resolve()
        fault_root = Path(env["CONTROLPROOF_FAULT_ROOT"]).resolve()
        return cls(
            target_id=env.get("CONTROLPROOF_TARGET_ID", "whyyou-local").strip(),
            run_root=run_root,
            fault_root=fault_root,
            whyyou_base_url=base_url,
            whyyou_console_url=console_url,
            whyyou_database_url=database_url,
            whyyou_company_token=env["WHYYOU_COMPANY_TOKEN"].strip(),
            whyyou_repo_path=Path(env["WHYYOU_REPO_PATH"]).resolve(),
            model_substitute_enabled=enabled,
            model_fixture_id=env["CONTROLPROOF_MODEL_FIXTURE_ID"].strip(),
            model_fixture_digest=digest,
        )

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
        }


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
