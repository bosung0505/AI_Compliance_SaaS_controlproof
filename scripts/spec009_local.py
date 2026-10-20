"""Spec 009 (N-01·N-03) entry point for the existing isolated local harness (explicit CLI commands only).

Same overrides as n02_local.py plus CONTROLPROOF_WHYYOU_PYTHON and, for ControlProof commands, the applicant app URL.
The API defaults to port 8080 because the applicant app's dev proxy targets 127.0.0.1:8080 (research R1).
`up --with-applicant-app` starts the applicant app after the base stack is ready, as one node process running
vite directly (no npm wrapper), recorded in state["processes"] so the existing `stop` ends it with the rest.
Nothing is installed: a missing node or vite fails the start.
"""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import time
from pathlib import Path

from scripts import spec004_local as local

FIXTURE_ID = "n02-analysis-v1"
FIXTURE_DIGEST = "092de5950a39ba3a7255c8696ffb073cddc65cda4615237044e3d910e32f9828"
API_PORT = 8080
APP_PORT = 5174
APP_URL = f"http://127.0.0.1:{APP_PORT}"
APP_READY_SECONDS = 60
_base_environment = local.environment


def environment(state: dict, *, for_cp: bool) -> dict[str, str]:
    values = _base_environment(state, for_cp=for_cp)
    values.update(
        {
            "CONTROLPROOF_MODEL_FIXTURE_ID": FIXTURE_ID,
            "CONTROLPROOF_MODEL_FIXTURE_DIGEST": FIXTURE_DIGEST,
            "CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED": "true",
            "CONTROLPROOF_EXTERNAL_AI_ALLOWED": "false",
            "CONTROLPROOF_WHYYOU_PYTHON": state["whyyou_python"],
        }
    )
    if for_cp:
        values["CONTROLPROOF_APPLICANT_APP_URL"] = APP_URL
    return values


def _ports_free(*ports: int) -> None:
    for port in ports:
        with socket.socket() as check:
            try:
                check.bind(("127.0.0.1", port))
            except OSError as exc:
                raise RuntimeError(f"SPEC009_PORT_IN_USE:{port}") from exc


def _app_status(url: str) -> int | None:
    import httpx

    try:
        return httpx.get(f"{url}/", timeout=3, trust_env=False).status_code
    except httpx.HTTPError:
        return None


def _save(state: dict) -> None:
    (Path(state["root"]) / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")


def start_applicant_app(state: dict, *, timeout_seconds: int = APP_READY_SECONDS) -> None:
    why = Path(state["whyyou_repo"])
    node = shutil.which("node")
    vite = why / "node_modules" / "vite" / "bin" / "vite.js"
    app_dir = why / "apps" / "applicant-interview"
    if not node or not vite.is_file() or not app_dir.is_dir():
        raise RuntimeError("SPEC009_APPLICANT_APP_DEPENDENCY_MISSING")
    _ports_free(APP_PORT)
    boot = Path(state["root"]) / state["boot"]
    with (boot / "applicant_app.log").open("xb") as stream:
        process = subprocess.Popen(
            [node, str(vite), "--strictPort"],
            cwd=app_dir,
            env=environment(state, for_cp=False),
            stdout=stream,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    # Same ownership record as the base harness, so `stop` re-checks creation time and ends it.
    state["pending_process"] = {"name": "applicant_app", "pid": process.pid}
    _save(state)
    info = next(row for row in local.process_snapshot() if row["ProcessId"] == process.pid)
    state.setdefault("processes", {})["applicant_app"] = info
    state.pop("pending_process")
    _save(state)
    for _ in range(timeout_seconds):
        if _app_status(APP_URL) == 200:
            state["applicant_app_url"] = APP_URL
            _save(state)
            print(json.dumps({"status": "APPLICANT_APP_STARTED", "url": APP_URL}))
            return
        time.sleep(1)
    raise RuntimeError("SPEC009_APPLICANT_APP_NOT_READY; inspect applicant_app.log, use stop for owned processes")


def main(argv=None):
    argv = list(argv or [])
    with_app = "--with-applicant-app" in argv
    argv = [item for item in argv if item != "--with-applicant-app"]
    mode = argv[0] if argv else None
    if with_app and mode != "up":
        raise SystemExit("--with-applicant-app is only valid with up")
    # Only harness arguments (before `--`) are inspected; the default goes there too, never into the engine command.
    separator = argv.index("--") if "--" in argv else len(argv)
    harness = argv[:separator]
    if not any(item == "--api-port" or item.startswith("--api-port=") for item in harness):
        argv[separator:separator] = ["--api-port", str(API_PORT)]
    if mode == "up":
        index = next(i for i, item in enumerate(argv) if item == "--api-port" or item.startswith("--api-port="))
        port = int(argv[index].split("=", 1)[1] if "=" in argv[index] else argv[index + 1])
        _ports_free(port, APP_PORT)
    previous_environment, previous_start = local.environment, local.start

    def start(state):
        previous_start(state)
        if with_app:
            start_applicant_app(state)

    try:
        local.environment = environment
        local.start = start
        return local.main(argv)
    finally:
        local.environment = previous_environment
        local.start = previous_start


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
