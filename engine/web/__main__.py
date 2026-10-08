"""`python -m engine.web` — the local workbench on 127.0.0.1 only (contracts/web-http.md).

Run root: --run-root > CONTROLPROOF_RUN_ROOT > .controlproof/runs (R-004). Synthetic records live in a separate DEMO root
(default .controlproof/web-demo/runs) and are shown only under /demo/. Web state (readiness checks) goes to
.controlproof/web/.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from engine.web.server import BIND_ADDRESS, make_server

DEFAULT_RUN_ROOT = Path(".controlproof/runs")
DEFAULT_DEMO_ROOT = Path(".controlproof/web-demo/runs")
STATE_DIR = Path(".controlproof/web")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m engine.web", description="ControlProof local workbench")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--demo-root", type=Path, default=DEFAULT_DEMO_ROOT)
    parser.add_argument("--target", default="whyyou-local")
    args = parser.parse_args(argv)
    run_root = args.run_root or Path(os.environ.get("CONTROLPROOF_RUN_ROOT") or DEFAULT_RUN_ROOT)
    if run_root.resolve() == args.demo_root.resolve():
        parser.error("the DEMO root must differ from the run root")
    server = make_server(args.port, run_root=run_root, demo_root=args.demo_root, state_dir=STATE_DIR, target=args.target)
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
