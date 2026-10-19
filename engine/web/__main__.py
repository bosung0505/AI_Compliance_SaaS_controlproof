"""`python -m engine.web` — the local workbench on 127.0.0.1 only (contracts/web-http.md).

Default: verified review-data/snapshot.json, read-only shared actual records (Spec008).
Explicit --run-root or CONTROLPROOF_RUN_ROOT selects the existing local execution-review mode.
Synthetic records stay separate under /demo/. Only local mode reads/writes .controlproof/web state.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from engine.shared_records import DEFAULT_SNAPSHOT, SnapshotError, load_snapshot
from engine.web.server import BIND_ADDRESS, make_server

DEFAULT_DEMO_ROOT = Path(".controlproof/web-demo/runs")
STATE_DIR = Path(".controlproof/web")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m engine.web", description="ControlProof local workbench")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--shared-snapshot", type=Path)
    parser.add_argument("--demo-root", type=Path, default=DEFAULT_DEMO_ROOT)
    parser.add_argument("--target", default="whyyou-local")
    args = parser.parse_args(argv)
    local_root = args.run_root or os.environ.get("CONTROLPROOF_RUN_ROOT")
    if args.shared_snapshot and local_root:
        parser.error("--shared-snapshot cannot be combined with a local run root or CONTROLPROOF_RUN_ROOT")
    snapshot_path = args.shared_snapshot or (DEFAULT_SNAPSHOT if not local_root else None)
    snapshot = None
    if snapshot_path:
        try:
            snapshot = load_snapshot(snapshot_path)
        except (SnapshotError, OSError) as exc:
            parser.error(str(exc))
        run_root = snapshot_path.parent / "bundles"
    else:
        run_root = Path(local_root)
    if run_root.resolve() == args.demo_root.resolve():
        parser.error("the DEMO root must differ from the run root")
    server = make_server(args.port, run_root=run_root, demo_root=args.demo_root, state_dir=STATE_DIR, target=args.target, shared_snapshot=snapshot)
    port = server.server_address[1]
    print(f"ControlProof 워크벤치: http://{BIND_ADDRESS}:{port}/  (DEMO DATA: http://{BIND_ADDRESS}:{port}/demo/)")
    print("종료: Ctrl+C", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
