"""Criteria versions through the product API, scoring-rule source blobs (T055, ID-004-20).

Versions are created and published with the company token (`/v1/positions/{id}/competency-model-versions`,
`/v1/competency-model-versions/{id}/publish` with `If-Match-Version`). The version view omits criterion IDs, so
they and the other-positions digest are read from the DB read-only. No token or response text leaves the adapter
except sanitized codes.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Iterable
from contextlib import AbstractContextManager
from typing import Any

import httpx
from sqlalchemy import create_engine, text

from engine.adapters.base import AdapterResult
from engine.config import Settings
from engine.judges.e02_scoring import PINNED_SOURCES
from engine.models import CriteriaVersionSnapshot, canonical_json_bytes, sha256_bytes

_CRITERIA = (
    "SELECT criterion_id, code, weight FROM evaluation_criteria "
    "WHERE competency_model_version_id = :version_id ORDER BY code"
)
_VERSIONS = (
    "SELECT position_id, competency_model_version_id, version_number, status, row_version "
    "FROM competency_model_versions ORDER BY position_id, version_number"
)


def _detail_code(response: httpx.Response) -> str:
    try:
        detail = response.json().get("detail")
    except ValueError:
        return "UNPARSEABLE"
    if isinstance(detail, dict):
        return str(detail.get("code") or "UNSPECIFIED")[:80]
    if isinstance(detail, list) and detail and isinstance(detail[0], dict):
        return str(detail[0].get("type") or "VALIDATION_ERROR")[:80]
    return "UNSPECIFIED"


class WhyYouCriteriaVersionAdapter:
    def __init__(
        self,
        settings: Settings,
        *,
        http_client: httpx.Client | None = None,
        read_factory: Callable[[], AbstractContextManager] | None = None,
    ) -> None:
        self.settings = settings
        self.http = http_client or httpx.Client(base_url=settings.whyyou_base_url, timeout=15)
        if read_factory is None:
            read_factory = create_engine(settings.whyyou_database_url).connect
        self._read = read_factory

    def _headers(self, **extra: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.settings.whyyou_company_token}", **extra}

    def create_version(
        self, *, position_id: str, body: dict[str, Any], idempotency_key: str
    ) -> AdapterResult:
        try:
            response = self.http.post(
                f"/v1/positions/{position_id}/competency-model-versions",
                json=body,
                headers=self._headers(**{"Idempotency-Key": idempotency_key}),
            )
        except httpx.HTTPError as exc:
            return AdapterResult(False, "CRITERIA_API_UNAVAILABLE", detail=type(exc).__name__)
        if response.status_code == 201:
            view = response.json()
            return AdapterResult(
                True,
                "VERSION_CREATED",
                {
                    "version_id": str(view["competency_model_version_id"]),
                    "row_version": int(view["row_version"]),
                    "version_number": int(view["version_number"]),
                },
            )
        code = "VERSION_CREATE_REJECTED" if response.status_code == 422 else "VERSION_CREATE_FAILED"
        return AdapterResult(
            False,
            code,
            {"status_code": response.status_code, "detail_code": _detail_code(response)},
        )

    def publish_version(
        self, *, version_id: str, row_version: int, idempotency_key: str
    ) -> AdapterResult:
        try:
            response = self.http.post(
                f"/v1/competency-model-versions/{version_id}/publish",
                headers=self._headers(
                    **{"Idempotency-Key": idempotency_key, "If-Match-Version": str(row_version)}
                ),
            )
        except httpx.HTTPError as exc:
            return AdapterResult(False, "CRITERIA_API_UNAVAILABLE", detail=type(exc).__name__)
        if response.status_code == 200:
            view = response.json()
            return AdapterResult(
                True,
                "VERSION_PUBLISHED",
                {
                    "version_id": str(view["competency_model_version_id"]),
                    "row_version": int(view["row_version"]),
                    "published_at": view.get("published_at"),
                },
            )
        code = (
            "VERSION_PUBLISH_CONFLICT" if response.status_code == 409 else "VERSION_PUBLISH_FAILED"
        )
        return AdapterResult(False, code, {"status_code": response.status_code})

    def latest_published(
        self, *, position_id: str, snapshot_phase: str
    ) -> CriteriaVersionSnapshot | AdapterResult:
        try:
            response = self.http.get(
                f"/v1/positions/{position_id}/competency-model-versions",
                headers=self._headers(),
            )
        except httpx.HTTPError as exc:
            return AdapterResult(False, "CRITERIA_API_UNAVAILABLE", detail=type(exc).__name__)
        if response.status_code != 200:
            return AdapterResult(
                False, "VERSION_LIST_FAILED", {"status_code": response.status_code}
            )
        published = [
            item for item in response.json().get("items") or () if item.get("status") == "published"
        ]
        if not published:
            return AdapterResult(False, "NO_PUBLISHED_VERSION")
        # WhyYou binds an invitation to the published version with the highest number.
        view = max(published, key=lambda item: int(item["version_number"]))
        version_id = str(view["competency_model_version_id"])
        other = self.other_positions_digest(excluded_position_ids=(position_id,))
        if not other.ok:
            return other
        try:
            with self._read() as connection:
                rows = connection.execute(
                    text(_CRITERIA), {"version_id": version_id}
                ).mappings().all()
        except Exception as exc:  # noqa: BLE001 - sanitized source failure
            return AdapterResult(False, "CRITERIA_DB_UNAVAILABLE", detail=type(exc).__name__)
        return CriteriaVersionSnapshot(
            position_id=position_id,
            competency_model_version_id=version_id,
            version_number=int(view["version_number"]),
            row_version=int(view["row_version"]),
            status=view["status"],
            published_at=view.get("published_at"),
            criteria=tuple(
                {
                    "criterion_id": str(row["criterion_id"]),
                    "code": row["code"],
                    "weight": float(row["weight"]),
                }
                for row in rows
            ),
            axis_weights={key: float(value) for key, value in (view.get("axis_weights") or {}).items()},
            request_ids=(),
            snapshot_phase=snapshot_phase,
            other_positions_digest=other.data["digest"],
        )

    def other_positions_digest(self, *, excluded_position_ids: Iterable[str]) -> AdapterResult:
        excluded = {str(value) for value in excluded_position_ids}
        try:
            with self._read() as connection:
                rows = connection.execute(text(_VERSIONS)).mappings().all()
        except Exception as exc:  # noqa: BLE001 - sanitized source failure
            return AdapterResult(False, "CRITERIA_DB_UNAVAILABLE", detail=type(exc).__name__)
        projection = [
            {key: str(value) for key, value in dict(row).items()}
            for row in rows
            if str(row["position_id"]) not in excluded
        ]
        return AdapterResult(
            True,
            "OTHER_POSITIONS_READ",
            {"digest": sha256_bytes(canonical_json_bytes(projection)), "rows": len(projection)},
        )


class WhyYouScoringSourceAdapter:
    """`git rev-parse --verify HEAD:<path>` in the WhyYou checkout for each pinned scoring source."""

    def __init__(self, settings: Settings, *, git: Callable[[list[str]], str] | None = None) -> None:
        self.settings = settings
        self._git = git or self._run_git

    def _run_git(self, args: list[str]) -> str:
        completed = subprocess.run(
            ["git", "-C", str(self.settings.whyyou_repo_path), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return completed.stdout.strip()

    def read_blob_shas(self) -> AdapterResult:
        shas: dict[str, str] = {}
        try:
            for source in PINNED_SOURCES:
                shas[source["path"]] = self._git(["rev-parse", "--verify", f"HEAD:{source['path']}"])
        except (OSError, subprocess.SubprocessError) as exc:
            return AdapterResult(False, "SCORING_SOURCE_UNAVAILABLE", detail=type(exc).__name__)
        return AdapterResult(True, "BLOB_SHAS_READ", {"blob_shas": shas})
