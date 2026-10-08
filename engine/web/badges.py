"""The one badge table (spec "승인된 화면 구조와 상태 이름", R-016).

Templates pick a badge by key only; shape families are 판정 = round, 준비 상태 = square, 실행 안전 = filled. Icons and labels
never vary between screens. This module maps copied status values to keys; it does not judge anything.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Badge:
    key: str
    category: str
    label_ko: str
    label_en: str | None
    icon: str
    shape: str
    tone: str
    description: str

    @property
    def css_class(self) -> str:
        return f"badge shape-{self.shape} tone-{self.tone}"

    @property
    def text(self) -> str:
        if self.label_en and self.label_ko != self.label_en:
            return f"{self.label_en} {self.label_ko}"
        return self.label_en or self.label_ko


_ROWS = (
    ("pass", "판정", "통과", "PASS", "✔", "round", "pass", "기대 결과와 필수 증적이 모두 확인됨"),
    ("fail", "판정", "실패", "FAIL", "✖", "round", "fail",
     "실제 동작이 기대와 다르거나 통제가 작동하지 않음. 사유 코드 대신 기대·관찰·설명"),
    ("inconclusive", "판정", "판정 불가", "INCONCLUSIVE", "", "round", "neutral",
     "결론을 낼 수 없음. 항상 reason code가 함께 보임"),
    ("not_run", "판정", "미실행", "NOT_RUN", "○", "round", "not-run", "정의는 있으나 실행하지 않음. 실패도 통과도 아님"),
    ("insufficient_evidence", "reason code", "INSUFFICIENT_EVIDENCE", "INSUFFICIENT_EVIDENCE", "?", "round",
     "insufficient", "판정에 필요한 증적이 부족함"),
    ("reason_no_test_target", "reason code", "NO_TEST_TARGET", "NO_TEST_TARGET", "∅", "square", "no-target",
     "대상 기능·처리 경로가 없음. ControlProof가 만들지 않음"),
    ("access_limited", "reason code", "ACCESS_LIMITED", "ACCESS_LIMITED", "⊟", "round", "access",
     "필요한 화면·로그·데이터에 접근할 수 없음 (목업 사례 없음, 같은 규칙)"),
    ("evidence_conflict", "reason code", "EVIDENCE_CONFLICT", "EVIDENCE_CONFLICT", "⇄", "round", "conflict",
     "같은 사실을 나타내는 증적이 서로 모순됨 (목업 사례 없음, 같은 규칙)"),
    ("ready", "준비 상태", "READY", "READY", "●", "square", "ready", "준비 상태 확인을 통과함(확인 시각 기준)"),
    ("runner_not_ready", "준비 상태", "RUNNER_NOT_READY", "RUNNER_NOT_READY", "⚙", "square", "runner",
     "대상 기능은 있으나 ControlProof 실행기가 준비되지 않음"),
    ("access_blocked", "준비 상태", "ACCESS_BLOCKED", "ACCESS_BLOCKED", "⊟", "square", "access",
     "권한·접근이 막혀 확인하지 못함"),
    ("readiness_no_test_target", "준비 상태", "NO_TEST_TARGET", "NO_TEST_TARGET", "∅", "square", "no-target",
     "대상 기능이 없음(reason code와 같은 표시)"),
    ("tool_error", "확인 도구", "확인 도구 오류", None, "!", "square", "tool",
     "준비 상태가 아니라 확인 요청 자체가 잘못됨(사용법 오류)"),
    ("restore_failed", "실행 안전", "복구 실패", "RESTORE_FAILED", "⚠", "filled", "restore",
     "대상 서비스 FAIL이 아니라 실행 안전 문제. 수동 정리 확인 필요"),
    ("integrity_failed", "실행 안전", "무결성 실패", None, "⛔", "filled", "integrity",
     "봉인 뒤 기록이 바뀜. 그 기록의 판정을 사실로 보이지 않음"),
)

BADGES: dict[str, Badge] = {row[0]: Badge(*row) for row in _ROWS}

_RESULT = {"PASS": "pass", "FAIL": "fail", "NOT_RUN": "not_run", "INCONCLUSIVE": "inconclusive"}
_REASON = {
    "INSUFFICIENT_EVIDENCE": "insufficient_evidence",
    "NO_TEST_TARGET": "reason_no_test_target",
    "ACCESS_LIMITED": "access_limited",
    "EVIDENCE_CONFLICT": "evidence_conflict",
}
_READINESS = {
    "READY": "ready",
    "RUNNER_NOT_READY": "runner_not_ready",
    "ACCESS_BLOCKED": "access_blocked",
    "NO_TEST_TARGET": "readiness_no_test_target",
}


def result_badge(result: str, reason_code: str | None) -> Badge:
    """`INCONCLUSIVE` is shown by its reason code badge under a neutral title, never by itself."""
    if result == "INCONCLUSIVE" and reason_code in _REASON:
        return BADGES[_REASON[reason_code]]
    return BADGES[_RESULT[result]]


def readiness_badge(value: str) -> Badge:
    return BADGES[_READINESS[value]]
