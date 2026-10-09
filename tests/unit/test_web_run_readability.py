"""T057a~T057d — run screen readability before the usability review (ID-005-09). Display only; values stay sealed."""

from __future__ import annotations

import json
import re

import pytest

from engine.evidence import verify_bundle
from engine.web import readmodel
from engine.web.preflight import ReadinessStore
from tests.fixtures import web_bundles as wb

STEP_ID = re.compile(r"\b[a-z]+(?:-[a-z0-9]+){1,}\b")


@pytest.fixture(scope="module")
def catalog():
    return readmodel.load_catalog()


def _reader(catalog, root, tmp_path):
    return readmodel.WorkbenchReader(catalog, root, readiness=ReadinessStore(tmp_path / "preflight"))


# -- T057a ---------------------------------------------------------------------------------------------------------
def test_aborted_integrity_label_never_says_verified(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    built = wb.h03_aborted(root)
    view = _reader(catalog, root, tmp_path).run(built.run_id)
    integrity = view["integrity_display"]
    assert view["integrity"]["status"] == "VERIFIED"  # the ID-005-01 decision and JSON value stay
    assert integrity["cli_verify_status"] == verify_bundle(built.bundle)["bundle_status"] == "INVALID"
    assert "VERIFIED" not in integrity["label"]
    assert "봉인 무결성 확인됨" in integrity["label"] and "명령줄 verify: INVALID" in integrity["label"]
    assert "EV-06, EV-07" in integrity["label"]


def test_normal_integrity_label(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    view = _reader(catalog, root, tmp_path).run(wb.h03_case(root, "pass").run_id)
    assert view["integrity_display"]["cli_verify_status"] == "VERIFIED"
    assert view["integrity_display"]["label"] == "봉인 무결성 확인됨 (VERIFIED)"


# -- T057b ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("scenario", ["H-03", "E-01"])
def test_phase_summary_is_plain(catalog, tmp_path, scenario) -> None:
    root = tmp_path / "runs"
    built = wb.h03_case(root, "pass") if scenario == "H-03" else wb.spec004_run(root, "E-01")
    view = _reader(catalog, root, tmp_path).run(built.run_id)
    summary = view["phase_summary"]
    assert [item["phase"] for item in summary] == ["BASELINE", "INJECTED", "RECOVERED"]
    assert [item["label"] for item in summary] == ["기준선", "주입", "복구"]
    assert sum(item["step_count"] for item in summary) == len(view["developer"]["steps"])
    text = json.dumps(summary, ensure_ascii=False)
    for step in view["developer"]["steps"]:
        assert step["step_id"] not in text
    assert not re.search(r"[A-Z]{3,}_[A-Z_]{3,}", " ".join(" ".join(item["sentences"]) for item in summary))
    recovery = summary[-1]
    assert any("복구 결과" in sentence for sentence in recovery["sentences"])


def test_change_injection_kinds_are_korean(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    view = _reader(catalog, root, tmp_path).run(wb.spec004_run(root, "E-01").run_id)
    applied = " ".join(view["phase_summary"][1]["sentences"])
    assert "근거 답변 구간 제거" in applied
    assert "EVIDENCE_SEGMENT_REMOVAL" not in applied and "E01_" not in applied


# -- T057c ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("case", ["h03", "e01"])
def test_evidence_names_are_distinguishable(catalog, tmp_path, case) -> None:
    root = tmp_path / "runs"
    built = wb.h03_case(root, "pass") if case == "h03" else wb.spec004_run(root, "E-01")
    view = _reader(catalog, root, tmp_path).run(built.run_id)
    names = [item["evidence_name"] for item in view["evidence"]]
    assert len(names) == len(set(names))
    for item in view["evidence"]:
        if item["evidence_requirement_ids"]:
            assert item["evidence_name"].startswith(item["evidence_requirement_ids"][0]), item["evidence_name"]
            assert "수집한 원본 기록" not in item["evidence_name"]
    for assertion in view["assertions"]:
        groups = assertion["evidence_groups"]
        group_names = [group["label"] for group in groups]
        assert len(group_names) == len(set(group_names))
        assert sum(group["count"] for group in groups) == len(assertion["evidence_refs"])
        assert all(group["refs"] for group in groups)


def test_every_evidence_label_comes_from_the_catalog(catalog) -> None:
    labels = catalog["evidence_labels"]
    for evidence_id in [f"EV-0{i}" for i in range(1, 10)] + [f"EV2-{i:02d}" for i in range(1, 13)] + [
        f"EV3-{i:02d}" for i in range(1, 11)
    ] + [f"EV4-{i:02d}" for i in range(1, 11)]:
        assert labels.get(evidence_id), evidence_id
    for text in labels.values():
        assert not re.search(r"[A-Za-z]{4,}", text.replace("SHA", "")), text


# -- T057d ---------------------------------------------------------------------------------------------------------
def test_unverified_scope_in_korean_with_raw_in_developer(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    view = _reader(catalog, root, tmp_path).run(wb.h03_case(root, "pass").run_id)
    plain = " ".join(view["unverified_scope"])
    assert "reporting retry exhaustion" not in plain and "재시도" in plain
    assert "reporting retry exhaustion and DLQ" in view["developer"]["unverified_scope_raw"]


def test_target_commit_short_and_hash_in_developer(catalog, tmp_path) -> None:
    root = tmp_path / "runs"
    built = wb.spec004_run(root, "E-01")
    view = _reader(catalog, root, tmp_path).run(built.run_id)
    assert view["run"]["target_commit"] == "aaaaaaa"
    assert view["developer"]["target_version"].startswith("target-snapshot:sha256:")


def test_workbench_target_commit_from_readiness(catalog, tmp_path) -> None:
    store = ReadinessStore(tmp_path / "preflight")
    store.write(
        {
            "scenario_id": "E-01", "execution_profile": "E01_CITATION_EVIDENCE_V1", "result_kind": "READINESS",
            "readiness": "READY", "error_kind": None, "checked_at": "2026-10-09T01:00:00+00:00", "exit_code": 0,
            "stored_payload": {"target_version": "target-snapshot:sha256:" + "c" * 64,
                               "target_snapshot": {"git_commit_sha": "374b122e1296c0159ccd88ed4763d358973c59cb"}},
        }
    )
    view = readmodel.WorkbenchReader(catalog, tmp_path / "runs", readiness=store).workbench()
    assert view["target"]["target_commit"] == "374b122"
