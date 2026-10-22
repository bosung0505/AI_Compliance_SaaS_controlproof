"""Build a NEW local display-context candidate from the exact frozen 28 reviewed records."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from engine.shared_records import build_snapshot, load_snapshot

REPO = Path(__file__).resolve().parents[3]
FEATURE = REPO / "specs/010-platform-ui-integration"


def frozen_source(source: Path, baseline: dict) -> Path:
    """Keep the captured baseline usable after a reviewed default promotion; never repin it."""
    archived = source.with_name(f"snapshot.{baseline['snapshot_id']}.json")
    for path in (source, archived):
        if (
            path.is_file() and not path.is_symlink() and not path.is_junction()
            and hashlib.sha256(path.read_bytes()).hexdigest() == baseline["file_sha256"]
        ):
            return path
    raise ValueError("Frozen source snapshot missing or changed; review the baseline before building")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--snapshot-id", required=True)
    args = parser.parse_args()
    destination = args.out.resolve()
    if not destination.is_relative_to((REPO / ".controlproof").resolve()) or destination.exists():
        parser.error("Use a new local directory strictly under .controlproof; existing paths are preserved")
    baseline = json.loads((FEATURE / "baseline.json").read_text(encoding="utf-8"))
    source = frozen_source(REPO / baseline["snapshot"]["path"], baseline["snapshot"])
    original = json.loads(source.read_text(encoding="utf-8"))
    sources = [source.parent / "bundles" / record["run_id"] for record in original["records"]]
    pngs = {item["sha256"] for item in baseline["reviewed_png_files"]}
    invalid = {r["run_id"] for r in original["records"] if r["verification"]["bundle_status"] == "INVALID"}
    candidate = build_snapshot(
        sources, destination, reviewed_pngs=pngs, expected_invalid=invalid, snapshot_id=args.snapshot_id,
    )
    assert candidate["records"] == original["records"]
    assert candidate["missing_records"] == original["missing_records"]
    assert candidate["target"] == original["target"]
    assert sum(len(r["files"]) for r in candidate["records"]) == 652
    load_snapshot(destination / "snapshot.json")
    print(f"{candidate['snapshot_id']} records=28 files=652 original-records-unchanged=true")
    print(f"snapshot={args.out.as_posix()}/snapshot.json")


if __name__ == "__main__":
    main()
