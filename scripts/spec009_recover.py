"""Remove the owned rows a Spec 009 RESTORE_FAILED Run left behind and write recovery evidence.

Only for a Run blocked under its own subject ("n01-notice"/"n03-stale-consent"). The sealed bundle is never
changed; afterwards `controlproof cleanup-confirm --subject <subject> --evidence <out>` re-counts read-only and
releases the block, and the next verification is a child Run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from engine import spec009_recovery
from engine.config import Settings
from engine.lifecycle import atomic_write
from engine.models import ExecutionProfile, canonical_json_bytes

PROFILES = (ExecutionProfile.N01_NOTICE_V1.value, ExecutionProfile.N03_STALE_CONSENT_V1.value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--profile", required=True, choices=PROFILES)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    settings = Settings.from_env()
    evidence = spec009_recovery.recover(settings, run_id=args.run_id, profile=ExecutionProfile(args.profile))
    atomic_write(args.out, canonical_json_bytes(evidence))
    print(json.dumps({key: evidence.get(key) for key in ("run_id", "profile", "status")}))
    return 0 if evidence.get("status") == "SUCCEEDED" else 1


if __name__ == "__main__":
    sys.exit(main())
