"""Write synthetic (DEMO DATA) bundles and readiness records for the web workbench (Spec 005 T033, FR-030, SC-011).

Usage: python -m scripts.prepare_web_demo [--demo-root .controlproof/web-demo/runs]

Bundles come from tests/fixtures/web_bundles.py (fake adapters, no target service). Readiness records go to
<demo root>/../preflight. The DEMO root must not be the real run root; the web shows it only under /demo/.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.models import InconclusiveReason
from engine.web.preflight import ReadinessStore
from engine.web.readmodel import load_catalog
from tests.fixtures import web_bundles as wb

DEFAULT_DEMO_ROOT = Path(".controlproof/web-demo/runs")
MARKER = ".controlproof-demo-root"
DEMO_TARGET_VERSION = "demo-target-version"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="prepare_web_demo")
    parser.add_argument("--demo-root", type=Path, default=DEFAULT_DEMO_ROOT)
    args = parser.parse_args(argv)
    demo_root = args.demo_root
    real_roots = {Path(".controlproof/runs").resolve()}
    if os.environ.get("CONTROLPROOF_RUN_ROOT"):
        real_roots.add(Path(os.environ["CONTROLPROOF_RUN_ROOT"]).resolve())
    if demo_root.resolve() in real_roots:
        parser.error("the DEMO root must not be the real run root")
    if demo_root.exists() and any(demo_root.iterdir()) and not (demo_root / MARKER).is_file():
        parser.error("the DEMO root is not empty and was not created by this script")
    demo_root.mkdir(parents=True, exist_ok=True)
    (demo_root / MARKER).write_text("synthetic DEMO DATA bundles for the ControlProof web workbench\n", encoding="utf-8")

    built = [wb.h03_case(demo_root, case) for case in ("pass", "fail", "missing")]
    built += [
        wb.h03_inconclusive(demo_root, InconclusiveReason.ACCESS_LIMITED),
        wb.h03_inconclusive(demo_root, InconclusiveReason.EVIDENCE_CONFLICT),
        wb.h03_aborted(demo_root),
    ]
    built += list(wb.h03_lineage(demo_root)) + list(wb.e03_lineage(demo_root)) + list(wb.e01_lineage(demo_root))
    built.append(wb.spec004_run(demo_root, "E-02"))
    tampered = wb.h03_case(demo_root, "pass")
    wb.tampered(tampered)
    built.append(tampered)
    # Last: a restore failure leaves a restore block that stops later H-03 Runs in this root (as the engine intends).
    built.append(wb.h03_case(demo_root, "restore_failed"))

    _write_readiness(ReadinessStore(demo_root.parent / "preflight"))
    print(f"DEMO bundles: {len(built)} (1 deliberately tampered) · readiness records: 7 profiles")
    return 0


def _write_readiness(store: ReadinessStore) -> None:
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    for entry in load_catalog()["scenarios"]:
        for profile in entry["profiles"]:
            # N-02 is checked at another time so the screen shows a row-level time (approved mockup).
            checked = (now - timedelta(minutes=67)) if entry["id"] == "N-02" else now
            payload = {
                "schema_version": "controlproof.cli.v1", "command": "preflight", "result_kind": "READINESS",
                "scenario_id": entry["id"], "execution_profile": profile["execution_profile"], "readiness": "READY",
                "checked_at": checked.isoformat(), "target_version": DEMO_TARGET_VERSION, "operator_action": None,
                "demo": True,
            }
            store.write(
                {
                    "schema_version": "controlproof.web-preflight.v1", "scenario_id": entry["id"],
                    "execution_profile": profile["execution_profile"], "result_kind": "READINESS",
                    "readiness": "READY", "error_kind": None, "checked_at": payload["checked_at"],
                    "operator_action": None, "capabilities": None, "exit_code": 0,
                    "stored_payload": json.loads(json.dumps(payload)),
                }
            )


if __name__ == "__main__":
    raise SystemExit(main())
