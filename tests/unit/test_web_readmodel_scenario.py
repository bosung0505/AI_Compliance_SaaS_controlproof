"""T048 — scenario view ② (FR-008~012). RED until T050.

Definition from the sealed snapshot when a Run exists in this root, else from `scenarios/*.yaml`; H-03 and E-03 split by
profile; NOT_RUN/NO_TEST_TARGET carry no profiles and no command fields; commands only from catalog templates.
"""

from __future__ import annotations

import json

import pytest
import yaml

from engine.web import readmodel
from engine.web.preflight import ReadinessStore
from tests.fixtures import web_bundles as wb

LEGAL_NOTICE = "법 조문 대응은 표시하지 않음(법적 준수 비보증)"


@pytest.fixture(scope="module")
def catalog():
    return readmodel.load_catalog()


def _reader(catalog, root, tmp_path, store=None):
    return readmodel.WorkbenchReader(
        catalog, root, readiness=store or ReadinessStore(tmp_path / "preflight"), target="whyyou-local"
    )


def test_definition_from_scenario_file_without_runs(catalog, tmp_path) -> None:
    view = _reader(catalog, tmp_path / "runs", tmp_path).scenario("E-01")
    assert (view["schema_version"], view["view"], view["id"]) == ("controlproof.web.v1", "scenario", "E-01")
    definition = view["profiles"][0]["definition"]
    source = yaml.safe_load(open("scenarios/E-01.yaml", encoding="utf-8"))
    assert definition["source"] == "scenario_file" and definition["run_id"] is None
    assert definition["version"] == source["version"]
    assert [item["assertion_id"] for item in definition["assertions"]] == [a["assertion_id"] for a in source["assertions"]]
    assert view["definition"] == definition


def test_definition_from_sealed_snapshot_when_a_run_exists(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    built = wb.spec004_run(root, "E-01")
    definition = _reader(catalog, root, tmp_path).scenario("E-01")["profiles"][0]["definition"]
    assert (definition["source"], definition["run_id"]) == ("sealed_snapshot", built.run_id)


def test_h03_and_e03_split_by_profile(catalog, tmp_path) -> None:
    reader = _reader(catalog, tmp_path / "runs", tmp_path)
    for scenario_id, profiles in (("H-03", ["H03_MINIMAL_V1", "H03_DLQ_V2"]), ("E-03", ["E03_BEFORE_V2", "E03_AFTER_V2"])):
        view = reader.scenario(scenario_id)
        assert [item["execution_profile"] for item in view["profiles"]] == profiles
        versions = {item["execution_profile"]: item["definition"]["assertions"] for item in view["profiles"]}
        assert versions[profiles[0]] != versions[profiles[1]]


@pytest.mark.parametrize("scenario_id", ["H-01", "H-02", "N-01", "N-03", "A-01", "A-02", "A-03"])
def test_not_run_and_no_target_have_no_profiles_or_commands(catalog, tmp_path, scenario_id) -> None:
    view = _reader(catalog, tmp_path / "runs", tmp_path).scenario(scenario_id)
    assert view["profiles"] == []
    text = json.dumps(view, ensure_ascii=False)
    assert "run_command" not in text and "retest_command" not in text and "python -m engine.cli" not in text
    if view["mvp_treatment"] == "NOT_RUN":
        assert view["explanation"]["not_run_reason"] and view["explanation"]["follow_up_condition"]
    else:
        assert view["explanation"]["absence_evidence"] and view["target_exists"] is False


def test_legal_mapping_notice_and_explanation(catalog, tmp_path) -> None:
    view = _reader(catalog, tmp_path / "runs", tmp_path).scenario("E-01")
    explanation = view["explanation"]
    assert explanation["legal_mapping_notice"] == LEGAL_NOTICE
    for key in ("intent", "protected_object", "policy_basis", "implementation_location", "synthetic_data"):
        assert explanation[key], key
    assert explanation["manual_steps"]
    assert view["explanation_sources"]["policy_basis"]


def test_commands_only_from_catalog_templates(catalog, tmp_path) -> None:
    view = _reader(catalog, tmp_path / "runs", tmp_path).scenario("E-01")
    profile = view["profiles"][0]
    template = next(e for e in catalog["scenarios"] if e["id"] == "E-01")["profiles"][0]
    assert profile["run_command"] == template["run_command"].format(target="whyyou-local", label="<라벨>")
    assert profile["retest_command"] == template["retest_command"].format(
        parent_run_id="<최초 실행 ID>", target="whyyou-local", label="<라벨>"
    )
    assert profile["preconditions_for_run"] == [
        "준비 상태 READY(확인 시각 확인)",
        "같은 대상의 다른 실행이 잠금을 잡고 있지 않음",
        "이전 복구 실패로 남은 차단이 없음",
        "사람의 실행 승인",
    ]


def test_readiness_with_checked_at_and_tool_error(catalog, tmp_path) -> None:
    store = ReadinessStore(tmp_path / "preflight")
    store.write({"scenario_id": "E-01", "execution_profile": "E01_CITATION_EVIDENCE_V1", "result_kind": "READINESS",
                 "readiness": "READY", "error_kind": None, "checked_at": "2026-10-09T01:00:00+00:00", "exit_code": 0,
                 "stored_payload": {}})
    store.write({"scenario_id": "E-02", "execution_profile": "E02_SCORING_FREEZE_V1", "result_kind": "ERROR",
                 "readiness": None, "error_kind": "USAGE", "checked_at": "2026-10-09T01:01:00+00:00", "exit_code": 2,
                 "stored_payload": {}})
    reader = _reader(catalog, tmp_path / "runs", tmp_path, store)
    ready = reader.scenario("E-01")["profiles"][0]["readiness"]
    assert (ready["value"], ready["badge"], ready["checked_at"]) == ("READY", "ready", "2026-10-09T01:00:00+00:00")
    error = reader.scenario("E-02")["profiles"][0]["readiness"]
    assert (error["value"], error["badge"], error["error_kind"]) == (None, "tool_error", "USAGE")


def test_previous_runs_listed_with_integrity(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    parent, child, _ = wb.e01_lineage(root)
    runs = {item["run_id"]: item for item in _reader(catalog, root, tmp_path).scenario("E-01")["previous_runs"]}
    assert runs[parent.run_id]["verdict"] == "FAIL" and runs[parent.run_id]["integrity"] == "VERIFIED"
    assert runs[child.run_id]["parent_run_id"] == parent.run_id
    assert runs[child.run_id]["record_role"] == "WEB_VALIDATION"


def test_unknown_scenario_is_not_found(catalog, tmp_path) -> None:
    with pytest.raises(readmodel.ScenarioNotFound):
        _reader(catalog, tmp_path / "runs", tmp_path).scenario("X-99")
