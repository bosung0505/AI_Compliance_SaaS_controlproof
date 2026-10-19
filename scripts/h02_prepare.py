"""Print source review preparation only; no H-02 Run, product verdict or target execution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.adapters.whyyou.h02_source import collect_inventory
from engine.h02 import PreparationError, load_preparation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--whyyou-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        load_preparation()
        target = args.whyyou_repo.resolve()
        output = args.output.resolve() if args.output is not None else None
        if output is not None and output.is_relative_to(target):
            raise PreparationError("OUTPUT_INSIDE_TARGET")
        inventory = collect_inventory(target)
        payload = inventory.model_dump(mode="json")
        payload["preparation_status"] = inventory.preparation_status
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        if output is not None:
            output.write_text(text + "\n", encoding="utf-8")
        print(text)
        return 2 if inventory.issues else 0
    except (PreparationError, OSError) as error:
        print(
            json.dumps(
                {
                    "scenario_id": "H-02",
                    "stage": 1,
                    "actual_status": "NOT_RUN",
                    "product_verdict": None,
                    "preparation_status": "BLOCKED",
                    "error_code": error.code
                    if isinstance(error, PreparationError)
                    else "SOURCE_IO_ERROR",
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
