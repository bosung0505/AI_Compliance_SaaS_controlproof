"""관찰값 키 사전.

시나리오의 판정 규칙은 여기 등록된 추상 키만 가리킨다.
키를 실제 엔드포인트·테이블·필드로 바꾸는 일은 연결 설정이 한다.

이 분리가 시나리오 재사용의 핵심이다. 고객이 바뀌면 mapping 만 교체하고
시나리오 YAML 은 그대로 둔다. 키 자체를 바꿔야 한다면 그건 매핑이 아니라
시나리오 교체다.

명명 규칙: <대상>.<속성>  /  사건은 event.<이름>
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class KeyKind(StrEnum):
    STATE = "state"      # 시점의 상태값
    EVENT = "event"      # 발생 시각을 갖는 사건
    RECORD = "record"    # 존재 여부와 필드를 갖는 기록
    COUNT = "count"      # 개수


@dataclass(frozen=True)
class KeyDef:
    key: str
    kind: KeyKind
    desc: str


REGISTRY: tuple[KeyDef, ...] = (
    # --- 동의·고지 (N 계열) ---
    KeyDef("consent.policy_version", KeyKind.STATE, "지원자에게 제시된 동의 정책 버전"),
    KeyDef("consent.content_digest", KeyKind.STATE, "동의 정책 내용 해시"),
    KeyDef("consent.record", KeyKind.RECORD, "동의 기록 (지원자·시각·버전)"),
    KeyDef("notice.items_visible", KeyKind.STATE, "동의 화면에 실제로 보인 고지 항목"),
    KeyDef("notice.viewport", KeyKind.STATE, "확인한 화면 폭"),
    KeyDef("event.consent_completed", KeyKind.EVENT, "동의 완료"),
    KeyDef("event.submission_created", KeyKind.EVENT, "지원 자료 제출"),
    KeyDef("event.analysis_requested", KeyKind.EVENT, "분석 요청"),
    KeyDef("event.analysis_started", KeyKind.EVENT, "실제 분석 시작 / analyzing 전환"),
    KeyDef("submission.response_status", KeyKind.STATE, "자료 제출 요청의 응답 코드"),
    KeyDef("analysis.response_status", KeyKind.STATE, "분석 요청의 응답 코드"),

    # --- 지원 건·채용 단계 (H 계열) ---
    KeyDef("invitation.state", KeyKind.STATE, "지원 건 상태 (completed / reviewed 등)"),
    KeyDef("invitation.stage", KeyKind.STATE, "현재 채용 단계"),
    KeyDef("invitation.row_version", KeyKind.STATE, "낙관적 잠금 버전"),
    KeyDef("decision.response_status", KeyKind.STATE, "최종결정 요청의 응답 코드"),
    KeyDef("decision.actor_type", KeyKind.STATE, "결정을 시도한 주체 유형"),
    KeyDef("human_review.record", KeyKind.RECORD, "HumanReview 기록 (결정자·시각·단계·사유)"),
    KeyDef("human_review.count", KeyKind.COUNT, "해당 지원 건의 최종결정 기록 수"),
    KeyDef("event.stage_moved", KeyKind.EVENT, "채용 단계 이동"),
    KeyDef("event.state_transition", KeyKind.EVENT, "지원 건 상태 전이"),
    KeyDef("stage_move.response_status", KeyKind.STATE, "일반 단계 이동 요청의 응답 코드"),

    # --- 리포트·평가 (H-03, E 계열) ---
    KeyDef("report.status", KeyKind.STATE, "리포트 상태 (ready / 처리중 / 실패)"),
    KeyDef("report.visible_state", KeyKind.STATE, "담당자 화면에 표시된 리포트 상태"),
    KeyDef("report.scoring_inputs", KeyKind.RECORD, "리포트에 동결된 점수 산출 입력"),
    KeyDef("axis.quoted_evidence_ids", KeyKind.RECORD, "축별 점수가 인용한 Evidence ID"),
    KeyDef("evidence.record", KeyKind.RECORD, "Evidence 기록"),
    KeyDef("score.write_response_status", KeyKind.STATE, "점수 저장 시도의 응답 코드"),

    # --- 비동기·장애 (H-03, E-03) ---
    KeyDef("job.status", KeyKind.STATE, "애플리케이션 작업 상태 (DLQ 포함)"),
    KeyDef("sqs.dlq_message", KeyKind.RECORD, "인프라 DLQ 메시지"),
    KeyDef("outbox.event", KeyKind.RECORD, "아웃박스 이벤트"),
    KeyDef("audit.event", KeyKind.RECORD, "감사 이벤트"),
    KeyDef("error.record", KeyKind.RECORD, "오류 기록"),
    KeyDef("retry.count", KeyKind.COUNT, "재시도 횟수"),

    # --- 버전 (E-02) ---
    KeyDef("version.competency_model", KeyKind.STATE, "적용된 평가 기준 버전"),
    KeyDef("version.commit", KeyKind.STATE, "시험 시점 대상 커밋"),
)

BY_KEY = {k.key: k for k in REGISTRY}


def validate(keys: list[str]) -> list[str]:
    """사전에 없는 키를 돌려준다. 시나리오 로드 시 호출해 오타를 잡는다."""
    return [k for k in keys if k not in BY_KEY]
