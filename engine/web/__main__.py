"""`python -m engine.web` entry point. The server is added in Spec 005 US1 (T031)."""

from __future__ import annotations

import sys

USAGE = (
    "usage: python -m engine.web [--port 8765] [--run-root PATH] [--demo-root PATH] [--target whyyou-local]\n"
    "The local web server is not implemented yet (Spec 005 T031)."
)


def main(argv: list[str] | None = None) -> int:
    print(USAGE, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
