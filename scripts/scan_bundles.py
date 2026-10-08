"""Read-only v1/v2 redaction scan over sealed bundles (Spec 005 T012, FR-036, R-012).

Usage: python -m scripts.scan_bundles --run-root <root> [--run-root <root> ...] [--label <name> ...] --out <report.json>

The report holds bundle IDs, bundle-relative file paths, rule names and counts only — never matched values or absolute
paths. Bundles are opened read-only and never changed.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from engine.evidence import SCANNED_SUFFIXES, scan_bytes

SCHEMA_VERSION = "controlproof.scan-report.v1"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scan_bundles")
    parser.add_argument("--run-root", action="append", required=True, type=Path)
    parser.add_argument("--label", action="append", default=[])
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    if len(args.label) > len(args.run_root):
        parser.error("more --label values than --run-root values")
    labels = args.label + [f"root-{index}" for index in range(len(args.label) + 1, len(args.run_root) + 1)]
    roots = [_scan_root(root, label) for root, label in zip(args.run_root, labels, strict=True)]
    report = {"schema_version": SCHEMA_VERSION, "summary": _summary(roots), "roots": roots}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = report["summary"]
    print(
        f"bundles={summary['bundle_count']} newly_flagged={summary['newly_flagged_bundles']} "
        f"v1={summary['v1']} v2={summary['v2']}"
    )
    return 0


def _scan_root(root: Path, label: str) -> dict[str, Any]:
    if not root.is_dir():
        return {"label": label, "status": "MISSING", "bundles": []}
    bundles = [
        _scan_bundle(directory)
        for directory in sorted(root.iterdir())
        if directory.is_dir() and (directory / "manifest.json").is_file()
    ]
    return {"label": label, "status": "SCANNED", "bundles": bundles}


def _scan_bundle(directory: Path) -> dict[str, Any]:
    files = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix.casefold() not in SCANNED_SUFFIXES:
            continue
        payload = path.read_bytes()
        v1 = scan_bytes(payload, profile="v1")
        v2 = scan_bytes(payload, profile="v2")
        if v1 or v2:
            files.append({"path": path.relative_to(directory).as_posix(), "v1": v1, "v2": v2})
    newly_flagged = any(
        count > item["v1"].get(rule, 0) for item in files for rule, count in item["v2"].items()
    )
    return {"run_id": directory.name, "files": files, "newly_flagged": newly_flagged}


def _summary(roots: list[dict[str, Any]]) -> dict[str, Any]:
    v1: Counter[str] = Counter()
    v2: Counter[str] = Counter()
    bundles = [bundle for root in roots for bundle in root["bundles"]]
    for bundle in bundles:
        for item in bundle["files"]:
            v1.update(item["v1"])
            v2.update(item["v2"])
    return {
        "bundle_count": len(bundles),
        "v1": dict(sorted(v1.items())),
        "v2": dict(sorted(v2.items())),
        "newly_flagged_bundles": sum(1 for bundle in bundles if bundle["newly_flagged"]),
    }


if __name__ == "__main__":
    raise SystemExit(main())
