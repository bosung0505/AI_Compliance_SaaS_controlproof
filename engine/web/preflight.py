"""Web readiness check: the CLI `preflight --json` as a subprocess, stored as is (R-007).

The record is interpreted by `result_kind`/`error_kind`/`readiness` (R-010); the exit code is stored but never read.
Only one check runs at a time. Stored payloads pass the output boundary (paths and redaction) before writing.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from engine.evidence import display_paths, redact

SCHEMA_VERSION = "controlproof.web-preflight.v1"
TIMEOUT_SECONDS = 120
TIMEOUT_ACTION = "준비 상태 확인 시간이 초과됐습니다"
UNREADABLE_ACTION = "준비 상태 확인 결과를 읽을 수 없습니다. 명령줄에서 같은 확인을 실행해 보세요"


class UnknownProfile(ValueError):
    """The scenario/profile pair is not an executable profile of the catalog."""


class PreflightBusy(RuntimeError):
    """Another readiness check is still running."""


class ReadinessStore:
    """Latest record per scenario/profile plus an append-only history, under one directory."""

    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)

    def path_for(self, scenario_id: str, profile: str) -> Path:
        return self.directory / f"{scenario_id}--{profile}.json"

    def write(self, record: dict[str, Any]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        text = json.dumps(record, ensure_ascii=False, sort_keys=True)
        self.path_for(record["scenario_id"], record["execution_profile"]).write_text(text + "\n", encoding="utf-8")
        with (self.directory / "history.jsonl").open("a", encoding="utf-8") as history:
            history.write(text + "\n")

    def latest(self, scenario_id: str, profile: str) -> dict[str, Any] | None:
        path = self.path_for(scenario_id, profile)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None


class PreflightRunner:
    def __init__(
        self,
        catalog: dict[str, Any],
        store: ReadinessStore,
        *,
        target: str = "whyyou-local",
        python: str = sys.executable,
        run: Callable[..., Any] = subprocess.run,
        timeout: int = TIMEOUT_SECONDS,
        cwd: Path | None = None,
    ) -> None:
        self.store = store
        self.target = target
        self._python = python
        self._run = run
        self._timeout = timeout
        self._cwd = cwd
        self._lock = threading.Lock()
        self._profiles = {
            (entry["id"], profile["execution_profile"])
            for entry in catalog["scenarios"]
            for profile in entry["profiles"]
        }

    def command(self, scenario_id: str, profile: str) -> list[str]:
        if (scenario_id, profile) not in self._profiles:
            raise UnknownProfile(f"{scenario_id} has no executable profile {profile}")
        return [
            self._python, "-m", "engine.cli", "preflight", scenario_id, "--profile", profile,
            "--target", self.target, "--json",
        ]

    def check(self, scenario_id: str, profile: str) -> dict[str, Any]:
        command = self.command(scenario_id, profile)
        if not self._lock.acquire(blocking=False):
            raise PreflightBusy("a readiness check is already running")
        try:
            record = self._execute(command, scenario_id, profile)
            self.store.write(record)
            return record
        finally:
            self._lock.release()

    def _execute(self, command: list[str], scenario_id: str, profile: str) -> dict[str, Any]:
        base = {"schema_version": SCHEMA_VERSION, "scenario_id": scenario_id, "execution_profile": profile}
        try:
            completed = self._run(
                command, capture_output=True, text=True, encoding="utf-8", timeout=self._timeout, cwd=self._cwd
            )
        except subprocess.TimeoutExpired:
            return _error(base, "UNEXPECTED", TIMEOUT_ACTION, exit_code=None)
        try:
            payload = json.loads(completed.stdout)
            if not isinstance(payload, dict) or payload.get("result_kind") not in {"READINESS", "ERROR"}:
                raise ValueError("not a CLI readiness payload")
        except (TypeError, ValueError):
            return _error(base, "UNEXPECTED", UNREADABLE_ACTION, exit_code=completed.returncode)
        stored = redact(display_paths(payload))
        is_readiness = stored["result_kind"] == "READINESS"
        return {
            **base,
            "result_kind": stored["result_kind"],
            "readiness": stored.get("readiness") if is_readiness else None,
            "error_kind": None if is_readiness else stored.get("error_kind") or "UNEXPECTED",
            "checked_at": stored.get("checked_at") or _now(),
            "operator_action": stored.get("operator_action") if is_readiness else stored.get("detail"),
            "capabilities": stored.get("capabilities"),
            "exit_code": completed.returncode,
            "stored_payload": stored,
        }


def _error(base: dict[str, Any], error_kind: str, action: str, *, exit_code: int | None) -> dict[str, Any]:
    return {
        **base,
        "result_kind": "ERROR",
        "readiness": None,
        "error_kind": error_kind,
        "checked_at": _now(),
        "operator_action": action,
        "capabilities": None,
        "exit_code": exit_code,
        "stored_payload": None,
    }


def _now() -> str:
    return datetime.now(UTC).isoformat()
