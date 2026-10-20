"""Build or verify reviewed actual records; no target execution or source mutation."""

from __future__ import annotations

import argparse
from pathlib import Path

from engine.shared_records import DEFAULT_SNAPSHOT, REPO_ROOT, build_snapshot, load_snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path, nargs="?", const=DEFAULT_SNAPSHOT)
    parser.add_argument("--run-root", type=Path, action="append", default=[])
    parser.add_argument("--bundle", type=Path, action="append", default=[])
    parser.add_argument("--out", type=Path)
    parser.add_argument("--reviewed-png", action="append", default=[])
    parser.add_argument("--preserve-invalid", action="append", default=[])
    parser.add_argument("--snapshot-id", default="shared-actual-20261019")
    args = parser.parse_args(argv)
    if args.verify:
        snapshot = load_snapshot(args.verify)
    else:
        if args.out is None or not (args.run_root or args.bundle):
            parser.error("building requires --out and explicit source directories")
        import yaml

        catalog = yaml.safe_load(
            (REPO_ROOT / "catalog/mvp-scenarios.yaml").read_text(encoding="utf-8")
        )
        expected = {
            r["run_id"]
            for e in catalog["scenarios"]
            for r in e["official_status"].get("records", [])
        }
        sources = list(args.bundle)
        for root in args.run_root:
            sources.extend(
                d
                for d in sorted(root.iterdir())
                if d.name in expected and (d / "manifest.json").is_file()
            )
        snapshot = build_snapshot(
            sources,
            args.out,
            reviewed_pngs=set(args.reviewed_png),
            expected_invalid=set(args.preserve_invalid),
            snapshot_id=args.snapshot_id,
        )
    print(
        f"{snapshot['snapshot_id']} records={len(snapshot['records'])} missing={len(snapshot['missing_records'])} sha256={snapshot['snapshot_digest']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
