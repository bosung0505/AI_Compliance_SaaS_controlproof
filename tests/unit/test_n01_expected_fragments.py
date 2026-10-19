"""T009b — expected notice fragments built from the server policy (contracts/assertions-v9.md N-01 table)."""

from __future__ import annotations

import hashlib
import json

import pytest

from engine.n01 import NOTICE_ITEMS, expected_fragments

POLICY = {
    "policy_version": "2026-08-v1",
    "ai_role": "AI는 질문과 평가 초안을 만들지만 최종 채용 결정은 기업의 사람이 수행합니다.",
    "recording_notice": "면접 중 음성과 영상을 녹화하며 Evidence 재생 구간에 사용합니다.",
    "processing_purposes": [
        {"purpose": "document_analysis", "title": "문서 분석", "description": "제출 자료를 질문 준비에 사용합니다."},
        {"purpose": "recording", "title": "면접 녹화", "description": "영상과 음성을 저장합니다."},
        {"purpose": "ai_assessment", "title": "AI 평가 보조", "description": "최종 답변 근거로 평가 초안을 만듭니다."},
    ],
    "retention_days": 180,
    "deletion_method": "삭제 요청 또는 보관기간 만료 시 원본과 파생 데이터를 삭제합니다.",
    "required_purposes": ["document_analysis", "recording", "ai_assessment"],
    "content_digest": "a" * 64,
}


def test_five_items_with_fragments_from_policy_values() -> None:
    fragments = expected_fragments(POLICY)
    assert tuple(fragments) == NOTICE_ITEMS
    assert fragments == {
        "ai_assist": [
            ("ai_assist.title", "AI 평가 보조"),
            ("ai_assist.description", "최종 답변 근거로 평가 초안을 만듭니다."),
        ],
        "human_final": [("human_final.ai_role", POLICY["ai_role"])],
        "recording_purpose": [
            ("recording_purpose.notice", POLICY["recording_notice"]),
            ("recording_purpose.document_analysis.title", "문서 분석"),
            ("recording_purpose.recording.title", "면접 녹화"),
            ("recording_purpose.ai_assessment.title", "AI 평가 보조"),
        ],
        "retention": [("retention.label", "보관기간"), ("retention.days", "180일")],
        "deletion": [("deletion.label", "삭제 방법"), ("deletion.method", POLICY["deletion_method"])],
    }
    assert sum(len(items) for items in fragments.values()) == 11
    digest = hashlib.sha256(json.dumps(fragments, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    assert digest == hashlib.sha256(
        json.dumps(expected_fragments(json.loads(json.dumps(POLICY))), ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


@pytest.mark.parametrize(
    "broken",
    [
        {key: value for key, value in POLICY.items() if key != "ai_role"},
        POLICY | {"processing_purposes": POLICY["processing_purposes"][:2]},
        POLICY | {"deletion_method": "  "},
        POLICY | {"retention_days": "180"},
    ],
)
def test_incomplete_policy_is_rejected(broken: dict) -> None:
    with pytest.raises(ValueError):
        expected_fragments(broken)
