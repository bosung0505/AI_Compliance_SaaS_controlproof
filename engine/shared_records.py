"""Versioned, read-only distribution of sealed actual records (Spec008)."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from engine.evidence import canonical_json_bytes, scan_bytes_strict, sha256_bytes, verify_bundle

SCHEMA = "controlproof.shared-records.v1"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = REPO_ROOT / "review-data/snapshot.json"
TEXT_SUFFIXES = {".json", ".jsonl", ".yaml"}
VERIFICATION_KEYS = ("bundle_status", "missing_files", "mismatched_files", "unregistered_files")


class SnapshotError(ValueError):
    """A shared snapshot cannot be trusted or published."""


def _regular(path: Path) -> None:
    if path.is_symlink() or path.is_junction() or not path.is_file():
        raise SnapshotError("Only regular files are allowed in a shared snapshot")


def safe_path(root: Path, relative: str) -> Path:
    value = PurePosixPath(relative)
    if (
        not relative
        or value.is_absolute()
        or value.as_posix() != relative
        or any(p in {".", ".."} for p in value.parts)
        or "\\" in relative
        or ":" in relative
    ):
        raise SnapshotError("Invalid snapshot relative path")
    current = root
    for part in value.parts:
        current = current / part
        if current.is_symlink() or current.is_junction():
            raise SnapshotError("Links are not allowed in shared records")
    if not current.resolve().is_relative_to(root.resolve()):
        raise SnapshotError("Snapshot path escapes its root")
    return current


def file_hashes(directory: Path) -> dict[str, str]:
    if directory.is_symlink() or directory.is_junction():
        raise SnapshotError("Linked record directories are not allowed")
    result = {}
    for file in sorted(directory.rglob("*")):
        if file.is_symlink() or file.is_junction():
            raise SnapshotError("Links are not allowed in shared records")
        if file.is_dir():
            continue
        _regular(file)
        result[file.relative_to(directory).as_posix()] = sha256_bytes(file.read_bytes())
    return result


def display_hashes(repo: Path) -> dict[str, str]:
    """Pin the catalog, scenario definitions and code/assets that interpret the sealed bytes."""
    paths = [
        *repo.glob("engine/**/*.py"),
        *repo.glob("engine/web/templates/**/*.html"),
        *repo.glob("engine/web/static/*.css"),
        *repo.glob("engine/web/static/*.js"),
        *repo.glob("catalog/*.yaml"),
        *repo.glob("scenarios/*.yaml"),
        *repo.glob("scenarios/*.json"),
    ]
    # Git may check source out as CRLF on Windows. Sealed evidence uses -text and is never normalized.
    return {
        p.relative_to(repo).as_posix(): sha256_bytes(p.read_bytes().replace(b"\r\n", b"\n"))
        for p in sorted(paths)
    }


def verification(path: Path) -> dict[str, Any]:
    result = verify_bundle(path)
    return {key: result[key] for key in VERIFICATION_KEYS}


def check_shareable(path: Path, *, reviewed_pngs: set[str], run_id: str) -> None:
    for name, digest in file_hashes(path).items():
        file = path / name
        if file.suffix in TEXT_SUFFIXES:
            payload = file.read_bytes()
            if scan_bytes_strict(payload) or re.search(
                rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", payload
            ):
                raise SnapshotError(f"Sharing scan failed: {run_id}/{name}")
        elif file.suffix == ".png" and digest in reviewed_pngs:
            if not file.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
                raise SnapshotError("Invalid reviewed PNG")
        else:
            raise SnapshotError(f"File type has not been reviewed: {run_id}/{name}")


def load_snapshot(path: Path = DEFAULT_SNAPSHOT, *, repo: Path = REPO_ROOT) -> dict[str, Any]:
    """Verify every supplied byte before exposing the snapshot as an ACTUAL record root."""
    _regular(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        digest = data["snapshot_digest"]
        unsigned = {k: v for k, v in data.items() if k != "snapshot_digest"}
        if data["schema_version"] != SCHEMA or digest != sha256_bytes(
            canonical_json_bytes(unsigned)
        ):
            raise SnapshotError("Snapshot digest or schema mismatch")
        if data["display_files"] != display_hashes(repo):
            raise SnapshotError(
                "Snapshot display code/catalog differs; select its matching code version"
            )
        directory = safe_path(path.parent, "bundles")
        expected_files = {}
        ids = set()
        for record in data["records"]:
            run_id = record["run_id"]
            if str(uuid.UUID(run_id)) != run_id or run_id in ids:
                raise SnapshotError("Invalid or duplicate Run ID")
            ids.add(run_id)
            bundle = safe_path(directory, run_id)
            for name, value in record["files"].items():
                file = safe_path(bundle, name)
                _regular(file)
                if sha256_bytes(file.read_bytes()) != value:
                    raise SnapshotError(f"Shared file missing or changed: {run_id}/{name}")
                expected_files[f"{run_id}/{name}"] = value
            if verification(bundle) != record["verification"]:
                raise SnapshotError(f"Sealed verification state changed: {run_id}")
        if file_hashes(directory) != expected_files:
            raise SnapshotError("Shared bundle file inventory mismatch")
        return data
    except (KeyError, TypeError, OSError, json.JSONDecodeError, ValueError) as exc:
        if isinstance(exc, SnapshotError):
            raise
        raise SnapshotError("Shared snapshot is missing, malformed or incomplete") from exc


def build_snapshot(
    sources: list[Path],
    destination: Path,
    *,
    repo: Path = REPO_ROOT,
    reviewed_pngs: set[str] | None = None,
    expected_invalid: set[str] | None = None,
    snapshot_id: str = "shared-actual-20261019",
) -> dict[str, Any]:
    """Copy reviewed records to a NEW directory; never repair or modify source records."""
    import shutil

    if destination.exists():
        raise SnapshotError("Snapshot destination must not exist; create a new version")
    catalog = yaml.safe_load((repo / "catalog/mvp-scenarios.yaml").read_text(encoding="utf-8"))
    expected = {
        r["run_id"]: r
        for e in catalog["scenarios"]
        for r in e["official_status"].get("records", [])
    }
    unique: dict[str, tuple[Path, dict[str, Any]]] = {}
    for source in sources:
        run_id = source.name
        if str(uuid.UUID(run_id)) != run_id:
            raise SnapshotError("Source directory must be its Run ID")
        hashes = file_hashes(source)
        check_shareable(source, reviewed_pngs=reviewed_pngs or set(), run_id=run_id)
        state = verification(source)
        if state["unregistered_files"]:
            raise SnapshotError(f"Unregistered files cannot be shared: {run_id}")
        if state["bundle_status"] != "VERIFIED" and run_id not in (expected_invalid or set()):
            raise SnapshotError(f"Unreviewed invalid record: {run_id}")
        run = json.loads((source / "run.json").read_text(encoding="utf-8"))
        manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
        if run["run_id"] != run_id or manifest["run_id"] != run_id:
            raise SnapshotError("Run identity mismatch")
        official = expected.get(run_id, {})
        if (
            official.get("manifest_sha256")
            and official["manifest_sha256"] != hashes["manifest.json"]
        ):
            raise SnapshotError(f"Catalog manifest mismatch: {run_id}")
        if official.get("bundle_digest") and official["bundle_digest"] != manifest["bundle_digest"]:
            raise SnapshotError(f"Catalog bundle digest mismatch: {run_id}")
        record = {
            "run_id": run_id,
            "scenario_id": run["scenario_id"],
            "parent_run_id": run.get("parent_run_id"),
            "execution_profile": run.get("execution_profile"),
            "official": bool(official),
            "files": hashes,
            "verification": state,
        }
        if run_id in unique and unique[run_id][1] != record:
            raise SnapshotError(f"Conflicting copies of Run: {run_id}")
        unique[run_id] = (source, record)
    if not unique:
        raise SnapshotError("No actual records selected")
    for entry in catalog["scenarios"]:
        for final in entry["official_status"].get("records", []):
            if final["role"] == "final" and final["run_id"] not in unique:
                raise SnapshotError("Every official final record must be present")
    latest_source = max(
        (p for p, _ in unique.values()),
        key=lambda p: json.loads((p / "run.json").read_text(encoding="utf-8"))["started_at"],
    )
    target = json.loads((latest_source / "target.snapshot.json").read_text(encoding="utf-8"))
    data = {
        "schema_version": SCHEMA,
        "snapshot_id": snapshot_id,
        "reviewed_at": datetime.now(UTC).isoformat(),
        "records": [r for _, r in sorted(unique.values(), key=lambda pair: pair[1]["run_id"])],
        "missing_records": [
            {"run_id": i, "note": "보관 위치 조사에서 원본을 찾지 못함. 요약 기록만 보존."}
            for i in sorted(expected.keys() - unique.keys())
        ],
        "target": {
            "target_version": target.get("target_version"),
            "target_commit": (target.get("git_commit_sha") or "")[:7] or None,
        },
        "display_files": display_hashes(repo),
    }
    data["snapshot_digest"] = sha256_bytes(canonical_json_bytes(data))
    for run_id, (source, _) in sorted(unique.items()):
        shutil.copytree(source, destination / "bundles" / run_id)
    (destination / "snapshot.json").write_bytes(canonical_json_bytes(data))
    load_snapshot(destination / "snapshot.json", repo=repo)
    return data
