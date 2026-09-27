from __future__ import annotations

import json

from scripts.prepare_sc008_review import prepare


def test_sc008_package_blinds_three_verdicts_and_keeps_answer_key_separate(tmp_path):
    output = tmp_path / "review"

    prepare(output)

    reviewer = json.loads((output / "reviewer-runs.json").read_text(encoding="utf-8"))
    answer_key = json.loads((output / "answer-key.json").read_text(encoding="utf-8"))
    assert [case["case_ref"] for case in reviewer["cases"]] == [
        "CASE-1",
        "CASE-2",
        "CASE-3",
    ]
    assert all(set(case) == {"case_ref", "run_id"} for case in reviewer["cases"])
    assert {case["expected_verdict"] for case in answer_key["cases"]} == {
        "PASS",
        "FAIL",
        "INCONCLUSIVE",
    }
    assert {case["run_id"] for case in reviewer["cases"]} == {
        case["run_id"] for case in answer_key["cases"]
    }
    assert all(
        (output / "runs" / case["run_id"] / "manifest.json").is_file() for case in reviewer["cases"]
    )
    instructions = (output / "README.md").read_text(encoding="utf-8")
    assert "controlproof show <RUN_ID> --run-root" in instructions
