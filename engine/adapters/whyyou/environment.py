"""Canonical local execution-environment snapshot for WhyYou Spec 002 runs."""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from engine.adapters.whyyou.client import WhyYouClient
from engine.config import Settings
from engine.models import (
    SPEC002_UNVERIFIED_SCOPE,
    AwsDeploymentStatus,
    EnvironmentKind,
    GitIdentity,
    TargetEnvironmentSnapshot,
    sha256_bytes,
)


class WhyYouEnvironmentAdapter:
    def __init__(self, settings: Settings, client: WhyYouClient) -> None:
        self.settings = settings
        self.client = client

    def capture_environment(self) -> TargetEnvironmentSnapshot:
        target = self.client.capture_target_snapshot()
        health = self._health()
        controlproof_root = Path(__file__).resolve().parents[3]
        controlproof = _git_identity(controlproof_root)
        whyyou = GitIdentity(
            commit_sha=str(target.git_commit_sha),
            dirty=bool(target.git_dirty),
            diff_digest=target.git_diff_digest,
        )
        components = {
            "api": str(health.get("app_environment", "local")),
            "reporting-worker": str(health.get("worker_mode", "local")),
            "company-console": "local",
            "postgresql": "local",
            "localstack": "local",
            "mailpit": "local",
            "embedding_fixture": self.settings.embedding_fixture_id,
        }
        endpoints = {
            "api": _sanitized_endpoint(self.settings.whyyou_base_url),
            "console": _sanitized_endpoint(self.settings.whyyou_console_url),
            "database": _sanitized_endpoint(self.settings.whyyou_database_url),
            "sqs": _sanitized_endpoint(self.settings.whyyou_aws_endpoint_url),
        }
        return TargetEnvironmentSnapshot(
            target_id=self.settings.target_id,
            environment_kind=EnvironmentKind(self.settings.environment_kind),
            host_os=f"{platform.system()}-{platform.release()}",
            controlproof_commit=controlproof,
            whyyou_commit=whyyou,
            components=components,
            endpoints=endpoints,
            model_fixture_id=self.settings.model_fixture_id,
            model_fixture_digest=self.settings.model_fixture_digest,
            external_ai_allowed=self.settings.external_ai_allowed,
            aws_deployment_status=AwsDeploymentStatus(
                self.settings.aws_deployment_status
            ),
            unverified_scope=tuple(sorted(SPEC002_UNVERIFIED_SCOPE)),
        )

    def _health(self) -> dict[str, object]:
        response = self.client.http.get("/internal/controlproof/health")
        if response.status_code in {401, 403}:
            raise PermissionError("environment health access denied")
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise TypeError("environment health response is not an object")
        if body.get("model_substitute_enabled") is not True:
            raise RuntimeError("deterministic model substitute is not active")
        if body.get("fixture_id") != self.settings.model_fixture_id:
            raise RuntimeError("model fixture identity does not match")
        return body


def _git_identity(repo: Path) -> GitIdentity:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip().casefold()
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout
    return GitIdentity(
        commit_sha=commit,
        dirty=bool(status),
        diff_digest=sha256_bytes(status) if status else None,
    )


def _sanitized_endpoint(value: str) -> str:
    parsed = urlparse(value.replace("postgresql+psycopg", "postgresql", 1))
    if not parsed.scheme or not parsed.hostname:
        raise ValueError("local endpoint is malformed")
    port = f":{parsed.port}" if parsed.port is not None else ""
    return f"{parsed.scheme}://{parsed.hostname}{port}"
