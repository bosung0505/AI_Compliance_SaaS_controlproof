"""T005 — N-01 pure judge (contracts/assertions-v9.md; FR-011, FR-012, FR-050, SC-003)."""

from __future__ import annotations

import copy
import hashlib
from uuid import UUID

import pytest

from engine.models import AssertionResult
from engine.n01 import (
    NOTICE_ITEMS,
    REQUIRED_RESIDUE_TABLES,
    N01Fragment,
    assertions_for,
    cleanup_verified,
    verdict_for,
)

RUN_ID = "11111111-1111-4111-8111-111111111111"
VIEWPORTS = {"pc": {"width": 1440, "height": 900}, "mobile": {"width": 390, "height": 844}}
FRAGMENTS = {
    "ai_assist": [("ai_assessment.title", "AI 평가 보조")],
    "human_final": [("ai_role", "최종 채용 결정은 기업의 사람이 수행합니다.")],
    "recording_purpose": [("recording_notice", "면접 녹화는 평가 근거 확인에만 사용합니다."), ("recording.title", "면접 녹화")],
    "retention": [("retention.label", "보관기간"), ("retention.days", "180일")],
    "deletion": [("deletion.label", "삭제 방법"), ("deletion_method", "요청 시 30일 안에 삭제합니다.")],
}
POLICY = {"version": "2026-08-v1", "digest": "a" * 64}


def _fragment(fragment_id: str, text: str, **overrides) -> dict:
    value = {
        "fragment_id": fragment_id,
        "expected_text": text,
        "expected_text_digest": hashlib.sha256(text.encode()).hexdigest(),
        "text_present": True,
        "bbox": {"x": 10.0, "y": 20.0, "width": 200.0, "height": 18.0},
        "in_viewport": True,
        "center_hit": True,
        "not_occluded": True,
        "doc_scroll_width": 1440,
        "doc_client_width": 1440,
        "el_scroll_width": 200,
        "el_client_width": 200,
        "no_horizontal_overflow": True,
    }
    value.update(overrides)
    return value


def _lane(lane: str) -> dict:
    return {
        "lane": lane,
        "viewport": dict(VIEWPORTS[lane]),
        "subject": {
            "run_id": RUN_ID,
            "lane_id": lane,
            "subject_ref": f"n01-{lane}",
            "invitation_id": str(UUID(int=1 if lane == "pc" else 2)),
            "applicant_id": str(UUID(int=3 if lane == "pc" else 4)),
        },
        "step_reached": "ready",
        "capture": {"file": f"n01-{lane}-capture.png", "sha256": "b" * 64, "bytes": 2048},
        "token_absent_in_dom": True,
        "operations": [{"kind": "scroll", "fragment_id": "deletion_method", "scroll_y": 120}],
        "items": [
            {"item_id": item, "fragments": [_fragment(fid, text) for fid, text in FRAGMENTS[item]]}
            for item in NOTICE_ITEMS
        ],
        "measurement_error": None,
    }


def _identifier(lane: str, **overrides) -> dict:
    value = {
        "lane": lane,
        "subject_ref": f"n01-{lane}",
        "screen": dict(POLICY),
        "server": dict(POLICY),
        "stored": {"policy_version": POLICY["version"], "evidence_digest": POLICY["digest"]},
        "consented_at": "2026-10-19T01:02:03+00:00",
        "commit_status": 201,
    }
    value.update(overrides)
    return value


def _recovery(**counts) -> dict:
    return {"status": "SUCCEEDED", "owned_residue_counts": {name: 0 for name in REQUIRED_RESIDUE_TABLES} | counts}


@pytest.fixture
def evidence():
    return [_lane("pc"), _lane("mobile")], [_identifier("pc"), _identifier("mobile")]


def _statuses(results: tuple[AssertionResult, ...]) -> dict[str, str]:
    return {item.assertion_id: item.status.value for item in results}


def _set_flag(lane: dict, item_id: str, fragment_id: str, **flags) -> None:
    item = next(item for item in lane["items"] if item["item_id"] == item_id)
    fragment = next(f for f in item["fragments"] if f["fragment_id"] == fragment_id)
    fragment.update(flags)


def test_all_pass(evidence) -> None:
    lanes, identifiers = evidence
    results = assertions_for(lanes, identifiers, _recovery())
    assert _statuses(results) == {"N01-A1": "PASS", "N01-A2": "PASS", "N01-A3": "PASS"}
    assert [item.subject_ref for item in results] == ["pc", "mobile", "policy-identifiers"]
    assert all(item.source_requirements == ("V4-N01",) and item.reason_code is None for item in results)
    assert verdict_for(results, _recovery()) == "PASS"


def test_sc003_one_screen_one_item_occluded_fails_only_that_screen(evidence) -> None:
    lanes, identifiers = evidence
    _set_flag(lanes[0], "retention", "retention.days", not_occluded=False, center_hit=False)
    results = assertions_for(lanes, identifiers, _recovery())
    assert _statuses(results) == {"N01-A1": "FAIL", "N01-A2": "PASS", "N01-A3": "PASS"}
    assert "retention" in results[0].detail and "not_occluded" in results[0].detail
    assert verdict_for(results, _recovery()) == "FAIL"


def test_mobile_horizontal_overflow_fails_only_mobile(evidence) -> None:
    lanes, identifiers = evidence
    _set_flag(lanes[1], "deletion", "deletion_method", no_horizontal_overflow=False, doc_scroll_width=420)
    assert _statuses(assertions_for(lanes, identifiers, _recovery())) == {
        "N01-A1": "PASS", "N01-A2": "FAIL", "N01-A3": "PASS",
    }


def test_text_present_alone_is_not_pass(evidence) -> None:
    lanes, identifiers = evidence
    _set_flag(lanes[0], "ai_assist", "ai_assessment.title", in_viewport=False)
    assert _statuses(assertions_for(lanes, identifiers, _recovery()))["N01-A1"] == "FAIL"


@pytest.mark.parametrize(
    ("mutate", "assertion_id"),
    [
        (lambda lanes: lanes[0].update(step_reached="identity"), "N01-A1"),
        (lambda lanes: lanes[1].update(token_absent_in_dom=False), "N01-A2"),
        (lambda lanes: lanes[1].update(token_absent_in_dom=None), "N01-A2"),
        (lambda lanes: lanes[0].update(viewport={"width": 1280, "height": 800}), "N01-A1"),
        (lambda lanes: lanes[1].update(viewport={"width": 1440, "height": 900}), "N01-A2"),
        (lambda lanes: lanes[0].update(items=lanes[0]["items"][:4]), "N01-A1"),
        (lambda lanes: lanes[1].update(capture=None), "N01-A2"),
        (lambda lanes: lanes[0].update(measurement_error="BROWSER_MEASURE_FAILED"), "N01-A1"),
        (lambda lanes: lanes.pop(1), "N01-A2"),
    ],
)
def test_lane_without_judgeable_evidence_is_inconclusive(evidence, mutate, assertion_id) -> None:
    lanes, identifiers = evidence
    mutate(lanes)
    results = {item.assertion_id: item for item in assertions_for(lanes, identifiers, _recovery())}
    assert results[assertion_id].status.value == "INCONCLUSIVE"
    assert results[assertion_id].reason_code.value == "INSUFFICIENT_EVIDENCE"
    other = "N01-A2" if assertion_id == "N01-A1" else "N01-A1"
    assert results[other].status.value == "PASS"


def test_commit_failure_after_measurement_does_not_hide_screen_result(evidence) -> None:
    lanes, identifiers = evidence
    lanes[0].update(step_reached="consent", measurement_error="BROWSER_COMMIT_FAILED")
    identifiers[0].update(stored=None, commit_status=None)
    assert _statuses(assertions_for(lanes, identifiers, _recovery())) == {
        "N01-A1": "PASS", "N01-A2": "PASS", "N01-A3": "INCONCLUSIVE",
    }


def test_identifiers_stored_digest_differs_fails(evidence) -> None:
    lanes, identifiers = evidence
    identifiers[1]["stored"]["evidence_digest"] = "c" * 64
    results = assertions_for(lanes, identifiers, _recovery())
    assert _statuses(results)["N01-A3"] == "FAIL"
    assert _statuses(results)["N01-A1"] == "PASS"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda identifiers: identifiers[0].update(screen=None),
        lambda identifiers: identifiers[1].update(server=None),
        lambda identifiers: identifiers.pop(),
        lambda identifiers: identifiers.append(copy.deepcopy(identifiers[0])),
    ],
)
def test_identifiers_unreadable_is_inconclusive(evidence, mutate) -> None:
    lanes, identifiers = evidence
    mutate(identifiers)
    result = assertions_for(lanes, identifiers, _recovery())[2]
    assert (result.status.value, result.reason_code.value) == ("INCONCLUSIVE", "INSUFFICIENT_EVIDENCE")


def test_recovery_failure_keeps_assertions_and_makes_verdict_inconclusive(evidence) -> None:
    lanes, identifiers = evidence
    failed = _recovery(consent_records=1)
    results = assertions_for(lanes, identifiers, failed)
    assert set(_statuses(results).values()) == {"PASS"}
    assert verdict_for(results, failed) == "INCONCLUSIVE"
    assert not cleanup_verified({"status": "FAILED", "owned_residue_counts": _recovery()["owned_residue_counts"]})
    missing = _recovery()
    missing["owned_residue_counts"].pop("applicant_access_tokens")
    assert not cleanup_verified(missing)


def test_assertion_values_exclude_capture_bytes_and_raw_text(evidence) -> None:
    lanes, identifiers = evidence
    actual = assertions_for(lanes, identifiers, _recovery())[0].actual
    assert actual["capture"] == {"file": "n01-pc-capture.png", "sha256": "b" * 64, "bytes": 2048}
    fragment = actual["items"][0]["fragments"][0]
    assert set(fragment) == {
        "fragment_id", "expected_text_digest", "text_present", "in_viewport", "not_occluded", "no_horizontal_overflow",
    }


def test_fragment_digest_must_match_text() -> None:
    value = _fragment("ai_role", "사람이 결정합니다.")
    value["expected_text_digest"] = "0" * 64
    with pytest.raises(ValueError):
        N01Fragment.model_validate(value)


# ---- measurement v2 (2026-10-20): hidden and vertically clipped notices -------------------------------------


def _v2(lane: dict) -> dict:
    lane = copy.deepcopy(lane)
    lane["measurement_version"] = 2
    for item in lane["items"]:
        for fragment in item["fragments"]:
            fragment.update(
                style_visible=True,
                not_clipped=True,
                clip_ancestor=None,
                computed_opacity=1.0,
                computed_visibility="visible",
            )
    return lane


def test_v1_record_keeps_the_v1_rules_and_actual(evidence) -> None:
    lanes, identifiers = evidence
    explicit = [dict(lane, measurement_version=1) for lane in lanes]
    baseline = assertions_for(lanes, identifiers, _recovery())
    assert assertions_for(explicit, identifiers, _recovery()) == baseline
    assert "measurement_version" not in baseline[0].actual
    assert baseline[0].expected["flags"] == ["text_present", "in_viewport", "not_occluded", "no_horizontal_overflow"]


def test_v2_record_passes_with_all_six_flags(evidence) -> None:
    lanes, identifiers = evidence
    results = assertions_for([_v2(lane) for lane in lanes], identifiers, _recovery())
    assert _statuses(results) == {"N01-A1": "PASS", "N01-A2": "PASS", "N01-A3": "PASS"}
    assert results[0].expected["flags"][-2:] == ["style_visible", "not_clipped"]
    assert results[0].actual["measurement_version"] == 2
    fragment = results[0].actual["items"][0]["fragments"][0]
    assert fragment["style_visible"] is True and fragment["not_clipped"] is True


@pytest.mark.parametrize("flag", ["style_visible", "not_clipped"])
def test_v2_new_flag_false_fails_that_lane(evidence, flag) -> None:
    lanes, identifiers = evidence
    mobile = _v2(lanes[1])
    _set_flag(mobile, "recording_purpose", "recording_notice", **{flag: False})
    results = assertions_for([_v2(lanes[0]), mobile], identifiers, _recovery())
    assert _statuses(results) == {"N01-A1": "PASS", "N01-A2": "FAIL", "N01-A3": "PASS"}
    assert flag in results[1].detail


def test_v1_record_ignores_v2_only_flags(evidence) -> None:
    lanes, identifiers = evidence
    _set_flag(lanes[1], "recording_purpose", "recording_notice", style_visible=False, not_clipped=False)
    assert _statuses(assertions_for(lanes, identifiers, _recovery()))["N01-A2"] == "PASS"


@pytest.mark.parametrize("version", [0, 3])
def test_unknown_measurement_version_is_inconclusive(evidence, version) -> None:
    lanes, identifiers = evidence
    lanes[0]["measurement_version"] = version
    result = assertions_for(lanes, identifiers, _recovery())[0]
    assert (result.status.value, result.reason_code.value) == ("INCONCLUSIVE", "INSUFFICIENT_EVIDENCE")


def test_v2_record_without_v2_measurements_is_inconclusive(evidence) -> None:
    lanes, identifiers = evidence
    lanes[0]["measurement_version"] = 2
    result = assertions_for(lanes, identifiers, _recovery())[0]
    assert result.status.value == "INCONCLUSIVE"
