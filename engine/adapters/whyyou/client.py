"""Authenticated WhyYou HTTP client and canonical TargetSnapshot capture."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

import httpx

from engine.config import Settings
from engine.evidence import redact
from engine.models import (
    TargetSnapshot,
    TargetSourceKind,
    canonical_json_bytes,
    sha256_bytes,
)


class TargetSnapshotCaptureError(RuntimeError):
    def __init__(self, message: str, diagnostic: TargetSnapshot | None = None) -> None:
        super().__init__(message)
        self.diagnostic = diagnostic


class WhyYouClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = settings
        self.http = httpx.Client(
            base_url=settings.whyyou_base_url,
            headers={"Authorization": f"Bearer {settings.whyyou_company_token}"},
            timeout=10.0,
            transport=transport,
        )

    def close(self) -> None:
        self.http.close()

    def capture_target_snapshot(self) -> TargetSnapshot:
        repo = self.settings.whyyou_repo_path
        commit = _git(repo, "rev-parse", "HEAD").strip().casefold()
        status = _git_bytes(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all")
        dirty = bool(status)
        diff_digest = _dirty_manifest_digest(repo, status) if dirty else None
        try:
            response = self.http.get("/openapi.json")
            response.raise_for_status()
            openapi = response.json()
            openapi_digest = sha256_bytes(canonical_json_bytes(openapi))
        except (httpx.HTTPError, ValueError) as exc:
            raise TargetSnapshotCaptureError(
                "unable to capture canonical OpenAPI document"
            ) from exc
        migration_head = _migration_head(repo)
        schema_signature = {
            "tables": {
                "invitations": [
                    "invitation_id",
                    "status",
                    "recruiting_stage_id",
                    "pipeline_row_version",
                ],
                "interview_sessions": ["interview_session_id", "invitation_id", "state"],
                "reports": ["report_id", "interview_session_id", "status"],
                "human_reviews": ["invitation_id", "actor_type", "decision_kind"],
                "outbox_events": ["outbox_event_id", "event_type", "idempotency_key"],
            }
        }
        snapshot = TargetSnapshot(
            target_id=self.settings.target_id,
            source_kind=TargetSourceKind.GIT_WORKTREE,
            git_commit_sha=commit,
            git_dirty=dirty,
            git_diff_digest=diff_digest,
            openapi_digest=openapi_digest,
            schema_migration_head=migration_head,
            schema_signature_digest=sha256_bytes(canonical_json_bytes(schema_signature)),
            model_fixture_id=self.settings.model_fixture_id,
            model_fixture_digest=self.settings.model_fixture_digest,
        )
        if dirty:
            raise TargetSnapshotCaptureError(
                "WhyYou checkout is dirty; actual H-03 Run requires a clean target",
                diagnostic=snapshot,
            )
        return snapshot

    def report_status(self, session_id: str) -> dict[str, Any]:
        response = self.http.get(f"/v1/interview-sessions/{session_id}/report")
        body = _json_body(response)
        exchange = _exchange("GET", "/v1/interview-sessions/{session_id}/report", response, body)
        if response.status_code == 200:
            return {
                "presence": "PRESENT",
                "status": body.get("status", "ready"),
                "exchange": exchange,
            }
        if response.status_code == 202:
            return {
                "presence": "ABSENT",
                "status": body.get("status", "queued"),
                "exchange": exchange,
            }
        if response.status_code == 404:
            return {"presence": "ABSENT", "status": body.get("status"), "exchange": exchange}
        if response.status_code in {401, 403}:
            return {"presence": "UNAVAILABLE", "error_code": "ACCESS_DENIED", "exchange": exchange}
        return {
            "presence": "UNAVAILABLE",
            "error_code": f"HTTP_{response.status_code}",
            "exchange": exchange,
        }

    def attempt_final_decision(
        self,
        invitation_id: str,
        *,
        recruiting_stage_id: str,
        expected_pipeline_version: int,
        idempotency_key: str,
    ) -> dict[str, Any]:
        response = self.http.post(
            f"/v1/invitations/{invitation_id}/final-decisions",
            headers={"Idempotency-Key": idempotency_key},
            json={
                "decision_kind": "advance",
                "recruiting_stage_id": recruiting_stage_id,
                "reason": "[SYNTHETIC] ControlProof H-03 safety attempt",
                "expected_pipeline_version": expected_pipeline_version,
            },
        )
        body = _json_body(response)
        stable_code = body.get("code") or body.get("error_code")
        detail = body.get("detail") if isinstance(body.get("detail"), str) else ""
        explicit = stable_code in {"REPORT_NOT_AVAILABLE", "REPORT_REQUIRED"} or (
            "report" in detail.casefold()
            and any(
                word in detail.casefold() for word in ("not available", "not ready", "required")
            )
        )
        return {
            "accepted": 200 <= response.status_code < 300,
            "http_status": response.status_code,
            "reason_present": explicit,
            "reason_code": "REPORT_NOT_AVAILABLE" if explicit else None,
            "reason_source": (
                "target_error_code"
                if stable_code in {"REPORT_NOT_AVAILABLE", "REPORT_REQUIRED"}
                else "target_body"
                if explicit
                else None
            ),
            "idempotency_key_digest": hashlib.sha256(idempotency_key.encode()).hexdigest(),
            "exchange": _exchange(
                "POST",
                "/v1/invitations/{invitation_id}/final-decisions",
                response,
                body,
            ),
        }


def _json_body(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
        return body if isinstance(body, dict) else {"value": body}
    except ValueError:
        return {}


def _exchange(
    method: str, route_template: str, response: httpx.Response, body: Any
) -> dict[str, Any]:
    return redact(
        {
            "request": {"method": method, "route_template": route_template},
            "response": {"status": response.status_code, "body": body},
        }
    )


def _git(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout


def _git_bytes(repo: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return completed.stdout


def _dirty_manifest_digest(repo: Path, porcelain: bytes) -> str:
    entries: list[dict[str, str]] = []
    records = [record for record in porcelain.split(b"\0") if record]
    for record in records:
        decoded = record.decode("utf-8", errors="surrogateescape")
        if len(decoded) < 4:
            continue
        status, relative = decoded[:2], decoded[3:].replace("\\", "/")
        if " -> " in relative:
            relative = relative.split(" -> ", 1)[1]
        path = (repo / relative).resolve()
        digest = sha256_bytes(path.read_bytes()) if path.is_file() else "DELETED"
        entries.append({"status": status, "path": relative, "sha256": digest})
    entries.sort(key=lambda item: item["path"].encode("utf-8", errors="surrogateescape"))
    return sha256_bytes(canonical_json_bytes(entries))


def _migration_head(repo: Path) -> str:
    versions = repo / "backend" / "alembic" / "versions"
    candidates = sorted(path.stem for path in versions.rglob("*.py") if path.name != "__init__.py")
    if not candidates:
        raise TargetSnapshotCaptureError("WhyYou migration head cannot be determined")
    return candidates[-1]
