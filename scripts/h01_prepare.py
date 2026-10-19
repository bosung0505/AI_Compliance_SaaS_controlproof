"""Print a synthetic H-01 preparation plan; never calls HTTP/DB or creates an actual Run."""

import argparse
import json
from uuid import UUID, uuid4

from engine.h01 import build_subjects, load_preparation


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preparation-id", type=UUID, default=None)
    args = parser.parse_args(argv)
    preparation_id = args.preparation_id or uuid4()
    definition = load_preparation()
    subjects = build_subjects(
        preparation_id,
        company_id=UUID(int=1),
        reviewer_id=UUID(int=2),
        target_stage_id=UUID(int=3),
    )
    print(
        json.dumps(
            {
                **definition,
                "preparation_id": str(preparation_id),
                "synthetic_placeholders_only": True,
                "subjects": [subject.model_dump(mode="json") for subject in subjects],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
