"""Portable, synthetic-only Spec 004 setup and CLI wrapper; never starts an actual Run itself.

Use clean source checkouts without .env. Runtime dependencies may be supplied via --whyyou-python.
All resources belong to a distinct Docker project and bind only loopback. Raw journals stay outside Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

CP = Path(__file__).resolve().parents[1]
FIXTURE_DIGEST = hashlib.sha256(b"controlproof:spec004-report-v1").hexdigest()
EMBEDDING_DIGEST = hashlib.sha256(b"controlproof:h03-report-v1").hexdigest()
TOKEN = "controlproof-spec004-synthetic-token"


def example_values(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("\"'")
    return values


def checked_git(repo: Path) -> dict:
    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

    source = {"branch": git("branch", "--show-current"), "head": git("rev-parse", "HEAD")}
    if source["branch"] in {"main", "master"} or git("status", "--porcelain"):
        raise RuntimeError("Use a clean feature checkout, never main")
    if (repo / ".env").exists():
        raise RuntimeError("Use a separate checkout without .env for isolated reproduction")
    return source


def base_environment(why: Path) -> dict[str, str]:
    excluded = (
        "AWS_",
        "GCP_",
        "GOOGLE_",
        "OTEL_",
        "CONTROLPROOF_",
        "WHYYOU_",
        "OPENAI_",
        "ANTHROPIC_",
    )
    values = {key: value for key, value in os.environ.items() if not key.startswith(excluded)}
    values.update(example_values(why / ".env.example"))
    return values


def environment(state: dict, *, for_cp: bool) -> dict[str, str]:
    why = Path(state["whyyou_repo"])
    root = Path(state["root"])
    aws = f"http://127.0.0.1:{state['aws_port']}"
    database = (
        "postgresql+psycopg://controlproof:synthetic-local-only@127.0.0.1:"
        f"{state['pg_port']}/controlproof_spec004"
    )
    values = base_environment(why)
    values.update(
        {
            "PYTHONPATH": str(why / "backend/src"),
            "PYTHONUNBUFFERED": "1",
            "PYTHONIOENCODING": "utf-8",
            "APP_ENVIRONMENT": "local",
            "DATABASE_URL": database,
            "MIGRATION_DATABASE_URL": database,
            "AWS_ACCESS_KEY_ID": "synthetic",
            "AWS_SECRET_ACCESS_KEY": "synthetic",
            "AWS_EC2_METADATA_DISABLED": "true",
            "AWS_REGION": "ap-northeast-2",
            "AWS_DEFAULT_REGION": "ap-northeast-2",
            "AWS_ENDPOINT_URL": aws,
            "S3_PUBLIC_ENDPOINT_URL": aws,
            "SOURCE_BUCKET": "controlproof-spec004-source",
            "MEDIA_BUCKET": "controlproof-spec004-media",
            "LOCAL_COMPANY_ACCESS_TOKEN": TOKEN,
            "LOCAL_COMPANY_EMAIL": "controlproof-spec004@example.invalid",
            "LOCAL_COMPANY_IDENTITY_SUBJECT": "controlproof-spec004-synthetic",
            "AI_PROVIDER": "aws",
            "EMBEDDING_PROVIDER": "aws",
            "STT_PROVIDER": "disabled",
            "TTS_PROVIDER": "text_only",
            "GCP_DOCUMENT_AI_API_ENDPOINT": f"127.0.0.1:{state['aws_port']}",
            "GCP_DOCUMENT_AI_PROJECT_ID": "synthetic-local",
            "GCP_DOCUMENT_AI_PROCESSOR_ID": "synthetic",
            "CONTROLPROOF_FAULT_ROOT": str(root / state["boot"] / "faults"),
            "CONTROLPROOF_OBSERVER_ROOT": str(root / state["boot"] / "observers"),
            "CONTROLPROOF_TEST_HOOKS_ENABLED": "true",
            "CONTROLPROOF_OBSERVER_ENABLED": "true",
            "CONTROLPROOF_EXTERNAL_AI_ALLOWED": "false",
            "CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED": "true",
            "CONTROLPROOF_MODEL_FIXTURE_ID": "spec004-report-v1",
            "CONTROLPROOF_MODEL_FIXTURE_DIGEST": FIXTURE_DIGEST,
            "CONTROLPROOF_EMBEDDING_FIXTURE_ID": "h03-embedding-v1",
            "CONTROLPROOF_EMBEDDING_FIXTURE_DIGEST": EMBEDDING_DIGEST,
            "WORKER_CONCURRENCY": "4",
            "SQS_WAIT_TIME_SECONDS": "1",
            "SMTP_PORT": "14969",
        }
    )
    for service in (
        "BEDROCK_RUNTIME",
        "TRANSCRIBE",
        "POLLY",
        "COGNITO_IDP",
        "MEDIACONVERT",
        "APPLICATION_AUTOSCALING",
        "ECS",
        "KMS",
    ):
        values[f"{service}_ENDPOINT_URL"] = aws
    prefix = f"cp-spec004-{state['instance']}"
    for service in ("analysis", "media", "reporting", "deletion", "capacity"):
        queue = f"{prefix}-{service}"
        values[f"LOCAL_{service.upper()}_QUEUE_NAME"] = queue
        values[f"SQS_{service.upper()}_QUEUE_URL"] = f"{aws}/123456789012/{queue}"
    if for_cp:
        values.update(example_values(CP / ".env.example"))
        values.update(
            {
                "PYTHONPATH": str(CP),
                "CONTROLPROOF_TARGET_ID": "whyyou-local",
                "CONTROLPROOF_RUN_ROOT": str(root / "runs"),
                "CONTROLPROOF_FAULT_ROOT": str(root / state["boot"] / "faults"),
                "CONTROLPROOF_OBSERVER_ROOT": str(root / state["boot"] / "observers"),
                "CONTROLPROOF_EXTERNAL_AI_ALLOWED": "false",
                "CONTROLPROOF_MODEL_FIXTURE_ID": "spec004-report-v1",
                "CONTROLPROOF_MODEL_FIXTURE_DIGEST": FIXTURE_DIGEST,
                "WHYYOU_BASE_URL": f"http://127.0.0.1:{state['api_port']}",
                "WHYYOU_CONSOLE_URL": "http://127.0.0.1:15173",
                "WHYYOU_DATABASE_URL": database,
                "WHYYOU_COMPANY_TOKEN": TOKEN,
                "WHYYOU_REPO_PATH": str(why),
                "WHYYOU_AWS_ENDPOINT_URL": aws,
                "WHYYOU_REPORTING_QUEUE_NAME": f"{prefix}-reporting",
                "WHYYOU_REPORTING_DLQ_NAME": f"{prefix}-reporting-dlq",
            }
        )
    return values


def journal_command(state: dict, argv: list[str], *, cwd: Path, env: dict, name: str, timeout=650):
    root = Path(state["root"]) / "commands" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    root.mkdir(parents=True)
    started = time.monotonic()
    result = subprocess.run(
        argv, cwd=cwd, env=env, capture_output=True, timeout=timeout, check=False
    )
    (root / f"{name}.stdout").write_bytes(result.stdout)
    (root / f"{name}.stderr").write_bytes(result.stderr)
    (root / f"{name}.json").write_text(
        json.dumps(
            {
                "argv": argv,
                "exit_code": result.returncode,
                "seconds": time.monotonic() - started,
                "recorded_at": datetime.now(UTC).isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return result


def process_snapshot() -> list[dict]:
    command = (
        "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,"
        "@{Name='Created';Expression={$_.CreationDate.ToUniversalTime().ToString('o')}} "
        "| ConvertTo-Json -Compress"
    )
    output = subprocess.check_output(["powershell", "-NoProfile", "-Command", command], text=True)
    # Windows native diagnostics can be appended to an otherwise valid JSON line.
    for line in output.splitlines():
        if line.lstrip().startswith(("[", "{")):
            rows = json.loads(line)
            return rows if isinstance(rows, list) else [rows]
    raise RuntimeError("Process inventory did not contain JSON")


def start(state: dict):
    import httpx

    checked_git(CP)
    state["sources"] = {
        "controlproof": checked_git(CP),
        "whyyou": checked_git(Path(state["whyyou_repo"])),
    }
    for port in (state["pg_port"], state["aws_port"], state["api_port"]):
        with socket.socket() as check:
            check.bind(("127.0.0.1", port))
    root = Path(state["root"])
    compose_env = dict(os.environ) | {
        "CP_SPEC004_PG_PORT": str(state["pg_port"]),
        "CP_SPEC004_AWS_PORT": str(state["aws_port"]),
    }
    result = journal_command(
        state,
        [
            "docker",
            "compose",
            "-p",
            state["project"],
            "-f",
            str(CP / "scripts/spec004-local.compose.yaml"),
            "up",
            "-d",
            "--wait",
        ],
        cwd=CP,
        env=compose_env,
        name="compose-up",
        timeout=120,
    )
    if result.returncode:
        raise RuntimeError("Isolated Docker startup failed; inspect local commands journal")
    # Generate valid synthetic GCP signing material using WhyYou's installed dependency, in memory only.
    signing = subprocess.check_output(
        [
            state["whyyou_python"],
            "-c",
            (
                "from cryptography.hazmat.primitives import serialization; "
                "from cryptography.hazmat.primitives.asymmetric import rsa; "
                "print(rsa.generate_private_key(public_exponent=65537,key_size=2048).private_bytes("
                "serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,"
                "serialization.NoEncryption()).decode())"
            ),
        ],
        text=True,
    )
    why_env = environment(state, for_cp=False)
    why_env["GCP_SERVICE_ACCOUNT_JSON"] = json.dumps(
        {
            "type": "service_account",
            "project_id": "synthetic-local",
            "private_key_id": "synthetic",
            "private_key": signing,
            "client_email": "local@synthetic-local.iam.gserviceaccount.com",
            "token_uri": f"http://127.0.0.1:{state['aws_port']}/synthetic-token",
        }
    )
    why = Path(state["whyyou_repo"])
    for name, argv in (
        (
            "migration",
            [
                state["whyyou_python"],
                "-m",
                "alembic",
                "-c",
                "backend/alembic.ini",
                "upgrade",
                "heads",
            ],
        ),
        ("infra", [state["whyyou_python"], "-m", "interview_evidence.runtime.local_infra"]),
    ):
        if journal_command(state, argv, cwd=why, env=why_env, name=name, timeout=120).returncode:
            raise RuntimeError(f"{name} failed; inspect local commands journal")
    boot = root / state["boot"]
    boot.mkdir(parents=True)
    state["processes"] = {}
    for name, argv in (
        (
            "api",
            [
                state["whyyou_python"],
                "-m",
                "uvicorn",
                "interview_evidence.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(state["api_port"]),
            ],
        ),
        ("workers", [state["whyyou_python"], "scripts/run_workers.py"]),
    ):
        with (boot / f"{name}.log").open("xb") as stream:
            process = subprocess.Popen(
                argv,
                cwd=why,
                env=why_env,
                stdout=stream,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        # Preserve the directly owned PID even if process inventory fails during startup.
        state["pending_process"] = {"name": name, "pid": process.pid}
        (root / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
        info = next(row for row in process_snapshot() if row["ProcessId"] == process.pid)
        state["processes"][name] = info
        state.pop("pending_process")
        (root / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    for _ in range(45):
        try:
            response = httpx.get(
                f"http://127.0.0.1:{state['api_port']}/v1/me",
                headers={"Authorization": f"Bearer {TOKEN}"},
                timeout=3,
            )
            if response.status_code == 200:
                state["ready"] = True
                (root / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
                print(json.dumps({"status": "STARTED", "actual_runs": 0, "aws": "NOT_RUN"}))
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise RuntimeError("API startup failed; retain logs, use stop for owned processes")


def stop(state: dict):
    if state.get("pending_process"):
        raise RuntimeError(
            "Startup process inventory incomplete; inspect pending PID before stopping"
        )
    snapshot = process_snapshot()
    selected = {}
    roots = {row["ProcessId"]: row for row in state.get("processes", {}).values()}
    for row in snapshot:
        owned = roots.get(row["ProcessId"])
        if owned and row["Created"] == owned["Created"]:
            selected[row["ProcessId"]] = row
    while True:
        children = {
            row["ProcessId"]: row
            for row in snapshot
            if row["ParentProcessId"] in selected and row["ProcessId"] not in selected
        }
        if not children:
            break
        selected.update(children)
    # Every PID's creation time is rechecked inside one native PowerShell process before termination.
    inventory = Path(state["root"]) / "stop-owned.json"
    inventory.write_text(json.dumps(list(reversed(list(selected.values())))), encoding="utf-8")
    command = (
        "param([string]$InventoryPath)\n"
        "$owned = Get-Content -Raw -LiteralPath $InventoryPath | ConvertFrom-Json; "
        "foreach ($item in $owned) { "
        "$current = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $item.ProcessId); "
        "if ($current -and $current.CreationDate.ToUniversalTime().ToString('o') -eq $item.Created) { "
        "Stop-Process -Id $item.ProcessId -Force -ErrorAction Stop } }"
    )
    # Pass JSON as a script parameter, never interpolate it into shell code.
    script = Path(state["root"]) / "stop-owned.ps1"
    script.write_text(command, encoding="utf-8")
    subprocess.run(["powershell", "-NoProfile", "-File", str(script), str(inventory)], check=True)
    compose_env = dict(os.environ) | {
        "CP_SPEC004_PG_PORT": str(state["pg_port"]),
        "CP_SPEC004_AWS_PORT": str(state["aws_port"]),
    }
    argv = [
        "docker",
        "compose",
        "-p",
        state["project"],
        "-f",
        str(CP / "scripts/spec004-local.compose.yaml"),
        "stop",
    ]
    if journal_command(
        state, argv, cwd=CP, env=compose_env, name="compose-stop", timeout=90
    ).returncode:
        raise RuntimeError("Owned Docker stop failed; retain resources and inspect journal")
    state["stopped"] = True
    (Path(state["root"]) / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(json.dumps({"status": "STOPPED", "evidence_and_volumes_retained": True}))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("up", "cli", "status", "stop"))
    parser.add_argument("--instance", default="repro")
    parser.add_argument("--whyyou-repo", type=Path, default=CP.parent / "gbsa_aws")
    parser.add_argument("--whyyou-python", type=Path)
    parser.add_argument("--state-root", type=Path, default=CP.parent / "cp-local/spec004-local")
    parser.add_argument("--pg-port", type=int, default=15734)
    parser.add_argument("--aws-port", type=int, default=14767)
    parser.add_argument("--api-port", type=int, default=18085)
    args, command = parser.parse_known_args(argv)
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", args.instance):
        parser.error("instance must be lowercase letters/digits/hyphens, starting with a letter")
    if any(not 1024 <= port <= 65535 for port in (args.pg_port, args.aws_port, args.api_port)):
        parser.error("use unprivileged local ports 1024..65535")
    root = (args.state_root.resolve() / args.instance).resolve()
    if root.is_relative_to(CP) or root.is_relative_to(args.whyyou_repo.resolve()):
        parser.error("state root must be outside both source repositories")
    root.mkdir(parents=True, exist_ok=True)
    state_path = root / "state.json"
    if args.mode == "up":
        if state_path.exists() and not json.loads(state_path.read_text())["stopped"]:
            raise RuntimeError(
                "Instance already recorded; inspect status and stop before restarting"
            )
        why = args.whyyou_repo.resolve()
        why_python = (args.whyyou_python or why / ".venv/Scripts/python.exe").resolve()
        if not why_python.is_file():
            raise RuntimeError("Install WhyYou dependencies or supply --whyyou-python")
        state = {
            "instance": args.instance,
            "project": f"controlproof-spec004-{args.instance}",
            "root": str(root),
            "boot": datetime.now(UTC).strftime("boot-%Y%m%dT%H%M%S%fZ"),
            "whyyou_repo": str(why),
            "whyyou_python": str(why_python),
            "pg_port": args.pg_port,
            "aws_port": args.aws_port,
            "api_port": args.api_port,
            "stopped": False,
        }
        start(state)
        return 0
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if args.mode == "stop":
        stop(state)
    elif args.mode == "status":
        print(
            json.dumps(
                {
                    "sources": state.get("sources"),
                    "ready": state.get("ready", False),
                    "stopped": state["stopped"],
                    "project": state["project"],
                }
            )
        )
    else:
        if state["stopped"] or not state.get("ready"):
            raise RuntimeError("Start and inspect the isolated instance first")
        checked_git(CP)
        checked_git(Path(state["whyyou_repo"]))
        if command[:1] == ["--"]:
            command = command[1:]
        if not command:
            parser.error("cli requires engine arguments after --")
        result = journal_command(
            state,
            [sys.executable, "-m", "engine.cli", *command],
            cwd=CP,
            env=environment(state, for_cp=True),
            name=command[0],
        )
        sys.stdout.buffer.write(result.stdout)
        sys.stderr.buffer.write(result.stderr)
        return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
