"""증적 스키마.

이 파일이 ControlProof의 계약이다. 어댑터·판정·저장·보고서가 모두 여기에 맞춘다.
스키마 변경은 엔진 전체에 파급되므로, D1에 고정하고 H-03을 수직으로 관통시켜
검증한 뒤에는 바꾸지 않는다.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Verdict(StrEnum):
    """판정값. '못 한 것'과 '안 한 것'을 섞지 않는다."""

    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_RUN = "NOT_RUN"


class InconclusiveReason(StrEnum):
    """판정 불가 사유. 고객이 받는 처방이 전혀 다르므로 반드시 구분한다."""

    NO_TEST_TARGET = "NO_TEST_TARGET"          # 대상 기능 자체가 없음
    ACCESS_LIMITED = "ACCESS_LIMITED"          # 접근 권한·경로가 없어 관찰 불가
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"  # 판정에 필요한 증적 미확보
    EVIDENCE_CONFLICT = "EVIDENCE_CONFLICT"    # 관찰 결과가 서로 충돌


class Source(StrEnum):
    """관찰값을 어디서 얻었는가."""

    API = "api"
    LOG = "log"
    BROWSER = "browser"
    MAIL = "mail"
    FAULT = "fault"
    SEED = "seed"


class TargetVersion(BaseModel):
    """시험 시점의 대상 버전. 증적의 '어떤 버전에서'에 해당한다."""

    model_config = ConfigDict(frozen=True)

    target: str = "WhyYou"
    commit: str | None = None
    policy_version: str | None = None
    policy_digest: str | None = None
    competency_model_version_id: str | None = None
    extra: dict[str, str] = Field(default_factory=dict)


class Observation(BaseModel):
    """관찰값 하나.

    key 는 관찰값 키 사전(engine/observations.py)의 추상 키다.
    시나리오의 판정 규칙은 이 키만 가리키며, 키를 실제 엔드포인트·필드로
    바꾸는 일은 연결 설정(어댑터 매핑)이 한다. 고객이 바뀌면 매핑만 바뀐다.

    absent=True 는 '조회했고 존재하지 않음'을 뜻한다.
    조회 자체를 못 한 경우는 Observation 을 만들지 않고 missing 으로 남긴다.
    이 구분이 FAIL 과 INCONCLUSIVE 를 가른다.
    """

    model_config = ConfigDict(frozen=True)

    key: str
    value: Any = None
    absent: bool = False
    occurred_at: datetime | None = None
    source: Source
    raw_ref: str | None = None          # 원본 위치 (응답 파일, 로그 행, 캡처 경로)
    note: str | None = None


class RuleResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_type: str
    passed: bool | None            # None = 평가 불가
    detail: str
    used_keys: tuple[str, ...] = ()
    missing_keys: tuple[str, ...] = ()


class Run(BaseModel):
    """시험 실행 하나. 모든 기록을 묶는 단위."""

    model_config = ConfigDict(frozen=True)

    run_id: UUID = Field(default_factory=uuid4)
    scenario_id: str
    started_at: datetime
    seed_kind: str                      # state | path
    fault_kind: str = "none"
    version: TargetVersion = Field(default_factory=TargetVersion)
    manual_steps: tuple[int, ...] = ()  # 사람이 수행한 단계. 재현성 판단에 필요
    correlation: dict[str, str] = Field(default_factory=dict)
    # 상관관계 연결(기능범위 6.2 1단계)의 키:
    #   applicant_id, invitation_id, report_id, trace_id, window_from, window_to
    retest_of: UUID | None = None       # 재시험이면 최초 실행 ID. 덮어쓰지 않는다.


class Judgement(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: UUID
    scenario_id: str
    verdict: Verdict
    reason: InconclusiveReason | None = None
    rule_results: tuple[RuleResult, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    decided_at: datetime
    summary: str = ""


class EvidenceBundle(BaseModel):
    """실행 ID로 묶인 증적 묶음. 보고서가 읽는 단위."""

    model_config = ConfigDict(frozen=True)

    run: Run
    observations: tuple[Observation, ...]
    judgement: Judgement
    artifacts: tuple[str, ...] = ()     # 캡처·응답 원본 파일 경로
