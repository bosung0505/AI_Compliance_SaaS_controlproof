"""T021 — catalog parity with the scope matrix (contracts/catalog.md rules 1~6; FR-003, FR-009, FR-019, SC-001).

RED until T027 (`catalog/mvp-scenarios.yaml`).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from engine.models import ExecutionProfile
from engine.scenario import load

CATALOG = Path("catalog/mvp-scenarios.yaml")
MATRIX = Path("docs/product/ControlProof_MVP_Scenario_Coverage_Matrix.md")
TREATMENT = {"실제 실행": "EXECUTED", "`NOT_RUN`": "NOT_RUN", "`NO_TEST_TARGET`": "NO_TEST_TARGET"}
# FR-019: plain text must not carry WhyYou internals, fixture names or sealed file names.
FORBIDDEN_PLAIN = (
    "iep-", "HumanReview", "JobStatus", "COMPANY_USER", "Alembic", "m_021", "h03-report-v1",
    "spec004-report-v1", "fixture", "manifest", "bundle", ".json", ".jsonl", ".yaml", "LocalStack",
)
LEGAL_ARTICLE = re.compile(r"제\s*\d+\s*조|Art(icle)?\.?\s*\d+|§\s*\d+\s*\(", re.IGNORECASE)


@pytest.fixture(scope="module")
def catalog():
    return yaml.safe_load(CATALOG.read_text(encoding="utf-8"))


def _matrix_rows():
    rows = {}
    for line in MATRIX.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 6 and re.fullmatch(r"[NHEA]-0\d", cells[0]):
            rows[cells[0]] = {"question": cells[1], "treatment": TREATMENT[cells[2]], "owner_spec": cells[3]}
    return rows


def _matrix_sentence():
    lines = [line[2:].strip() for line in MATRIX.read_text(encoding="utf-8").splitlines() if line.startswith("> ")]
    return " ".join(lines)


def _plain_texts(entry):
    explanation = entry["explanation"]
    for value in explanation.values():
        for item in value if isinstance(value, list) else [value]:
            yield item["text"]
    yield entry["official_status"]["summary"]


def test_rule1_matrix_rows_match_12_of_12(catalog) -> None:
    matrix = _matrix_rows()
    entries = {entry["id"]: entry for entry in catalog["scenarios"]}
    assert len(catalog["scenarios"]) == 12 and len(entries) == 12
    assert set(entries) == set(matrix)
    for scenario_id, row in matrix.items():
        entry = entries[scenario_id]
        assert entry["question"] == row["question"], scenario_id
        assert entry["mvp_treatment"] == row["treatment"], scenario_id
        assert entry["owner_spec"] == row["owner_spec"], scenario_id


def test_rule2_counts_and_fixed_sentence(catalog) -> None:
    treatments = [entry["mvp_treatment"] for entry in catalog["scenarios"]]
    assert (treatments.count("EXECUTED"), treatments.count("NOT_RUN"), treatments.count("NO_TEST_TARGET")) == (5, 4, 3)
    assert " ".join(catalog["fixed_scope_sentence"].split()) == " ".join(_matrix_sentence().split())


def test_rule2_status_shapes(catalog) -> None:
    for entry in catalog["scenarios"]:
        status = entry["official_status"]
        if entry["mvp_treatment"] == "NOT_RUN":
            assert entry["profiles"] == [] and status["result"] == "NOT_RUN"
            assert {"not_run_reason", "follow_up_condition"} <= set(entry["explanation"])
        elif entry["mvp_treatment"] == "NO_TEST_TARGET":
            assert entry["profiles"] == [] and entry["target_exists"] is False
            assert (status["result"], status["reason_code"]) == ("INCONCLUSIVE", "NO_TEST_TARGET")
            assert "absence_evidence" in entry["explanation"]
        else:
            assert entry["profiles"] and entry["target_exists"] is True
        if status["result"] == "INCONCLUSIVE":
            assert status["reason_code"]


def test_rule3_seven_profiles_map_to_existing_scenario_files(catalog) -> None:
    seen = []
    for entry in catalog["scenarios"]:
        for profile in entry["profiles"]:
            path = Path(profile["scenario_file"])
            assert path.is_file(), path
            scenario = load(path)
            assert scenario.scenario_id == entry["id"]
            active = scenario.execution_profile or ExecutionProfile.H03_MINIMAL_V1
            assert active.value == profile["execution_profile"]
            assert "{target}" in profile["run_command"] and "--json" in profile["run_command"]
            seen.append(profile["execution_profile"])
    assert len(seen) == 7 and len(set(seen)) == 7


def test_rule4_sources_present_and_no_legal_articles(catalog) -> None:
    for entry in catalog["scenarios"]:
        for name, value in entry["explanation"].items():
            for item in value if isinstance(value, list) else [value]:
                assert item.get("text") and item.get("source"), (entry["id"], name)
        assert not LEGAL_ARTICLE.search(entry["explanation"]["policy_basis"]["text"]), entry["id"]


def test_rule5_official_run_ids_appear_in_their_validation_document(catalog) -> None:
    checked = 0
    for entry in catalog["scenarios"]:
        status = entry["official_status"]
        for record in status.get("records", []):
            document = Path(record.get("validation_ref") or status["validation_ref"])
            assert record["run_id"] in document.read_text(encoding="utf-8"), (entry["id"], record["run_id"])
            if record.get("manifest_sha256"):
                assert record["manifest_sha256"] in document.read_text(encoding="utf-8")
            checked += 1
    assert checked >= 10


def test_rule6_plain_text_has_no_internal_fixture_or_file_names(catalog) -> None:
    for entry in catalog["scenarios"]:
        for text in _plain_texts(entry):
            for word in FORBIDDEN_PLAIN:
                assert word not in text, (entry["id"], word)


def test_explanation_texts_are_whole_values(catalog) -> None:
    """ID-005-08: an unquoted comma in a YAML flow mapping silently cut texts into extra keys."""

    def walk(value):
        if isinstance(value, dict):
            if "text" in value:
                assert set(value) <= {"text", "source", "status"}, value
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(catalog)
