"""Prepare blinded synthetic bundles for the SC-008 non-author review."""

from __future__ import annotations

import argparse
import json
import secrets
from datetime import UTC, datetime
from pathlib import Path

from engine.presentation import load_bundle_summary
from engine.runner import RunOrchestrator
from engine.scenario import load
from tests.fixtures.fake_adapters import FakeClock, make_adapters

CASES = (
    ("PASS", {}),
    ("FAIL", {"status_class": "queued_only"}),
    ("INCONCLUSIVE", {"effect": False}),
)


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def prepare(output: Path) -> None:
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty review directory: {output}")

    run_root = output / "runs"
    run_root.mkdir(parents=True, exist_ok=True)
    scenario = load("scenarios/H-03.yaml")
    generated: list[dict[str, object]] = []

    for expected_verdict, options in CASES:
        adapters, _ = make_adapters(**options)
        runner = RunOrchestrator(scenario, adapters, run_root, clock=FakeClock())
        run, judgement, bundle = runner.execute(runner.preflight("whyyou-local"))
        if judgement.verdict.value != expected_verdict:
            raise SystemExit(
                f"fixture verdict mismatch: expected {expected_verdict}, "
                f"got {judgement.verdict.value}"
            )
        generated.append(
            {
                "run_id": str(run.run_id),
                "expected_verdict": expected_verdict,
                "summary": load_bundle_summary(bundle),
            }
        )

    secrets.SystemRandom().shuffle(generated)
    reviewer_cases = [
        {"case_ref": f"CASE-{index}", "run_id": item["run_id"]}
        for index, item in enumerate(generated, start=1)
    ]
    answer_key = {
        "warning": "Do not show this file to the reviewer until all three cases are complete.",
        "cases": [
            {
                "case_ref": reviewer_cases[index]["case_ref"],
                "run_id": item["run_id"],
                "expected_verdict": item["expected_verdict"],
                "summary": item["summary"],
            }
            for index, item in enumerate(generated)
        ],
    }
    created_at = datetime.now(UTC).isoformat()
    _write_json(
        output / "reviewer-runs.json",
        {
            "created_at": created_at,
            "run_root": str(run_root.resolve()),
            "cases": reviewer_cases,
        },
    )
    _write_json(output / "answer-key.json", answer_key)
    (output / "README.md").write_text(
        "# SC-008 reviewer handoff\n\n"
        "1. `reviewer-runs.json`의 CASE-1~3을 위에서부터 검토합니다.\n"
        "2. 각 case마다 타이머를 새로 시작합니다.\n"
        "3. 아래 명령에서 `<RUN_ID>`만 바꿉니다.\n\n"
        "```powershell\n"
        f"controlproof show <RUN_ID> --run-root '{run_root.resolve()}'\n"
        "```\n\n"
        "검토자는 `answer-key.json`, 코드, 원본 artifact를 열지 않습니다. "
        "각 case의 다섯 답과 시간을 "
        "`specs/001-execution-evidence-h03/review-usability-checklist.md`에 기록합니다.\n",
        encoding="utf-8",
    )
    print(f"Prepared SC-008 review package: {output.resolve()}")
    for case in reviewer_cases:
        print(f"{case['case_ref']}: {case['run_id']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".controlproof/sc008-review"),
        help="empty output directory (default: .controlproof/sc008-review)",
    )
    args = parser.parse_args()
    prepare(args.output)


if __name__ == "__main__":
    main()
