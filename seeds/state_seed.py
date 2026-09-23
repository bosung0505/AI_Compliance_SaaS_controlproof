"""상태 시드 — DB에 행을 직접 생성한다.

리포트까지 준비된 검토 대기 지원자를 만든다. H·E 계열 시나리오가 쓴다.
동의 화면을 거치지 않으므로 N 계열에는 쓰지 않는다 (기능범위 3.3).

설계
  build_fixture()  순수 함수. 행 dict 를 만든다. DB 없이 테스트 가능.
  apply()          만들어진 행을 DB 에 쓴다. 얇게 유지한다.

이 분리로 불변식(인용 정합성, 멱등성)을 DB 없이 검증할 수 있고,
고객사가 바뀌면 TABLES 매핑만 교체하면 된다.

멱등성
  모든 식별자는 (시드 네임스페이스, 실행 라벨, 논리 이름)의 uuid5 다.
  같은 라벨로 두 번 돌리면 같은 UUID 가 나오고 upsert 로 수렴한다.
  로컬 스택이 부팅마다 시드를 다시 돌려도 안전해야 한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

SEED_NS = uuid5(NAMESPACE_URL, "controlproof.seed.state")

# 논리 이름 -> 실제 테이블명. 고객사가 바뀌면 여기만 교체한다.
TABLES = {
    "company": "companies",
    "company_user": "company_users",
    "position": "positions",
    "competency_model_version": "competency_model_versions",
    "evaluation_criterion": "evaluation_criteria",
    "recruiting_stage": "recruiting_stages",
    "invitation": "invitations",
    "applicant_profile": "applicant_profiles",
    "interview_session": "interview_sessions",
    "interview_turn": "interview_turns",
    "transcript_segment": "transcript_segments",
    "recording_asset": "recording_assets",
    "report": "reports",
    "report_item": "report_items",
    "evidence": "evidence",
}

# 각 테이블의 기본키. upsert 충돌 대상.
PKEYS = {
    "company": ("company_id",),
    "company_user": ("company_id", "company_user_id"),
    "position": ("company_id", "position_id"),
    "competency_model_version": ("company_id", "competency_model_version_id"),
    "evaluation_criterion": ("company_id", "criterion_id"),
    "recruiting_stage": ("company_id", "recruiting_stage_id"),
    "invitation": ("company_id", "invitation_id"),
    "applicant_profile": ("company_id", "applicant_id"),
    "interview_session": ("company_id", "interview_session_id"),
    "interview_turn": ("company_id", "turn_id"),
    "transcript_segment": ("company_id", "transcript_segment_id"),
    "recording_asset": ("company_id", "recording_asset_id"),
    "report": ("company_id", "report_id"),
    "report_item": ("company_id", "report_item_id"),
    "evidence": ("company_id", "evidence_id"),
}

# 쓰기 순서. 외래 참조가 뒤를 향하므로 이 순서를 지킨다.
ORDER = tuple(TABLES.keys())

AXES = ("correctness", "depth", "fundamentals", "ownership", "communication")
T0 = datetime(2026, 9, 23, 9, 0, tzinfo=UTC)


def sid(label: str, name: str) -> UUID:
    """결정론적 식별자. 같은 (라벨, 이름)은 항상 같은 UUID."""
    return uuid5(SEED_NS, f"{label}/{name}")


@dataclass
class ApplicantSpec:
    """합성 지원자 하나의 명세.

    scored_axes 에 없는 축은 점수 null 이며 인용도 비어야 한다.
    이 불변식은 WhyYou 의 인용 검증 규칙과 같고, E-01 의 정상 기준선이 된다.
    """

    ref: str
    scored_axes: tuple[str, ...] = AXES[:3]
    axis_score: int = 72
    assessment_state: str = "confirmed"
    evidence_count: int = 3
    note: str = ""


@dataclass
class Fixture:
    label: str
    rows: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    correlation: dict[str, str] = field(default_factory=dict)

    def of(self, logical: str) -> list[dict[str, Any]]:
        return self.rows.get(logical, [])

    def count(self, logical: str) -> int:
        return len(self.of(logical))


def build_fixture(
    label: str,
    applicants: list[ApplicantSpec],
    *,
    now: datetime = T0,
    company_name: str = "ControlProof 합성 회사",
    identity_subject: str | None = None,
) -> Fixture:
    """행을 만든다. DB 를 건드리지 않는다.

    label 은 실행 라벨이다. 시험 실행 ID 를 넣으면 실행마다 격리되고,
    고정 문자열을 넣으면 재실행 시 같은 데이터로 수렴한다.
    """
    if not applicants:
        raise ValueError("합성 지원자가 최소 1명 필요하다")

    company_id = sid(label, "company")
    reviewer_id = sid(label, "user/reviewer")
    position_id = sid(label, "position")
    cmv_id = sid(label, "cmv")
    stage_id = sid(label, "stage/검토")

    rows: dict[str, list[dict]] = {k: [] for k in TABLES}

    rows["company"].append({
        "company_id": company_id,
        "name": company_name,
        "default_retention_days": 180,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    })

    # identity_subject 가 로컬 principal provider 의 조회 키다.
    # 값이 어긋나면 로그인은 되는데 모든 요청이 401 로 떨어진다.
    rows["company_user"].append({
        "company_id": company_id,
        "company_user_id": reviewer_id,
        "identity_subject": identity_subject or f"controlproof-{label}-reviewer",
        "email_normalized": f"reviewer+{label}@controlproof.test",
        "role_code": "owner",
        "status": "active",
        "created_at": now,
    })

    rows["position"].append({
        "company_id": company_id,
        "position_id": position_id,
        "title": "합성 포지션",
        "role_type": "backend",
        "headcount": 1,
        "created_by": reviewer_id,
        "status": "open",
        "row_version": 1,
        "created_at": now,
    })

    rows["competency_model_version"].append({
        "company_id": company_id,
        "competency_model_version_id": cmv_id,
        "position_id": position_id,
        "version_number": 1,
        "interview_duration_minutes": 20,
        "axis_weights": {a: 1.0 / len(AXES) for a in AXES},
        "status": "published",
        "row_version": 1,
        "published_at": now,
    })

    criterion_id = sid(label, "criterion/C1")
    rows["evaluation_criterion"].append({
        "company_id": company_id,
        "competency_model_version_id": cmv_id,
        "criterion_id": criterion_id,
        "code": "C1",
        "name": "문제 해결",
        "weight": 1.0,
        "required": True,
    })

    rows["recruiting_stage"].append({
        "company_id": company_id,
        "recruiting_stage_id": stage_id,
        "position_id": position_id,
        "name": "검토",
        "sort_order": 1,
        "row_version": 1,
    })

    correlation: dict[str, str] = {
        "company_id": str(company_id),
        "position_id": str(position_id),
        "competency_model_version_id": str(cmv_id),
        "reviewer_id": str(reviewer_id),
    }

    for spec in applicants:
        _build_applicant(
            rows, label, spec, now,
            company_id=company_id, position_id=position_id,
            cmv_id=cmv_id, stage_id=stage_id, criterion_id=criterion_id,
            correlation=correlation,
        )

    return Fixture(label=label, rows=rows, correlation=correlation)


def _build_applicant(
    rows: dict[str, list[dict]],
    label: str,
    spec: ApplicantSpec,
    now: datetime,
    *,
    company_id: UUID,
    position_id: UUID,
    cmv_id: UUID,
    stage_id: UUID,
    criterion_id: UUID,
    correlation: dict[str, str],
) -> None:
    ref = spec.ref
    invitation_id = sid(label, f"invitation/{ref}")
    applicant_id = sid(label, f"applicant/{ref}")
    session_id = sid(label, f"session/{ref}")
    asset_id = sid(label, f"asset/{ref}")
    report_id = sid(label, f"report/{ref}")
    item_id = sid(label, f"item/{ref}")

    rows["invitation"].append({
        "company_id": company_id,
        "invitation_id": invitation_id,
        "position_id": position_id,
        "competency_model_version_id": cmv_id,
        "applicant_id": applicant_id,
        # 실행 라벨을 이메일에 넣어 상관관계 연결의 앵커로 쓴다 (기능범위 6.2)
        "applicant_email_normalized": f"{ref}+{label}@controlproof.test",
        "applicant_display_name": f"합성지원자-{ref}",
        "token_hash": f"seeded-{sid(label, f'token/{ref}').hex}",
        "expires_at": now + timedelta(days=7),
        "status": "completed",
        "identity_verified_at": now,
        "last_state_actor_type": "system",
        "row_version": 1,
        "recruiting_stage_id": stage_id,
        "pipeline_row_version": 1,
    })

    rows["applicant_profile"].append({
        "company_id": company_id,
        "applicant_id": applicant_id,
        "invitation_id": invitation_id,
        "display_name": f"합성지원자-{ref}",
        "verification_method": "seeded",
    })

    # state=reviewable 이어야 콘솔이 검토 경로를 만든다
    rows["interview_session"].append({
        "company_id": company_id,
        "interview_session_id": session_id,
        "invitation_id": invitation_id,
        "applicant_id": applicant_id,
        "competency_model_version_id": cmv_id,
        "state": "reviewable",
        "session_sequence": 1,
        "row_version": 1,
        "created_at": now,
        "started_at": now,
        "completed_at": now + timedelta(minutes=18),
    })

    # 턴 6개: 면접관 3, 지원자 3 교대
    segments: list[dict] = []
    answer_turn_ids: list[UUID] = []
    for i in range(6):
        turn_id = sid(label, f"turn/{ref}/{i}")
        speaker = "interviewer" if i % 2 == 0 else "applicant"
        start_ms = i * 60_000
        rows["interview_turn"].append({
            "company_id": company_id,
            "turn_id": turn_id,
            "interview_session_id": session_id,
            "sequence": i,
            "speaker": speaker,
            "status": "final",
            "text": f"[합성] {speaker} 발화 {i}",
            "target_criterion_id": criterion_id if speaker == "interviewer" else None,
            "idempotency_key": f"{label}-{ref}-turn-{i}",
            "model_config_version": "seed-v1",
            "finalized_at": now + timedelta(milliseconds=start_ms),
        })
        seg_id = sid(label, f"segment/{ref}/{i}")
        segments.append({
            "company_id": company_id,
            "transcript_segment_id": seg_id,
            "interview_session_id": session_id,
            "turn_id": turn_id,
            "speaker": speaker,
            "text": f"[합성] {speaker} 발화 {i}",
            "confidence": 0.97,
            "session_start_ms": start_ms,
            "session_end_ms": start_ms + 50_000,
            "version": 1,
            "created_at": now,
        })
        if speaker == "applicant":
            answer_turn_ids.append(turn_id)
    rows["transcript_segment"].extend(segments)

    # duration_ms 는 마지막 구간 끝 이상이어야 한다. Evidence 구간이 이를 넘지 않는다.
    duration_ms = segments[-1]["session_end_ms"]
    rows["recording_asset"].append({
        "company_id": company_id,
        "recording_asset_id": asset_id,
        "interview_session_id": session_id,
        "asset_type": "assembled",
        "object_key": f"seed/{label}/{ref}/assembled.mp4",
        "content_hash": sid(label, f"hash/{ref}").hex,
        "duration_ms": duration_ms,
        "status": "ready",
        "created_at": now,
    })

    # Evidence 는 지원자 발화 구간에만 붙인다
    applicant_segments = [s for s in segments if s["speaker"] == "applicant"]
    evidence_ids: list[UUID] = []
    for k in range(min(spec.evidence_count, len(applicant_segments))):
        seg = applicant_segments[k]
        ev_id = sid(label, f"evidence/{ref}/{k}")
        evidence_ids.append(ev_id)
        rows["evidence"].append({
            "company_id": company_id,
            "evidence_id": ev_id,
            "report_item_id": item_id,
            "criterion_id": criterion_id,
            "competency_model_version_id": cmv_id,
            "answer_turn_id": seg["turn_id"],
            "transcript_segment_id": seg["transcript_segment_id"],
            "video_start_ms": seg["session_start_ms"],
            "video_end_ms": min(seg["session_end_ms"], duration_ms),
            "observation": f"[합성] 근거 {k}",
            "sufficiency": "direct",
            "generation_version": "seed-v1",
            "created_at": now,
        })

    # 불변식: 점수 있는 축만 인용을 갖고, null 축은 인용이 비어 있다
    axis_assessments = {}
    for axis in AXES:
        if axis in spec.scored_axes and evidence_ids:
            axis_assessments[axis] = {
                "score": spec.axis_score,
                "quoted_evidence_ids": [str(e) for e in evidence_ids],
            }
        else:
            axis_assessments[axis] = {"score": None, "quoted_evidence_ids": []}

    scored = [a["score"] for a in axis_assessments.values() if a["score"] is not None]
    average = round(sum(scored) / len(scored)) if scored else None

    rows["report"].append({
        "company_id": company_id,
        "report_id": report_id,
        "interview_session_id": session_id,
        "invitation_id": invitation_id,
        "version": 1,
        "kind": "final",
        "model_version": "seed-model-v1",
        "prompt_version": "seed-prompt-v1",
        "config_version": "seed-config-v1",
        "status": "ready",
        "summary": f"[합성] {ref} 리포트",
        "overall_score": average,
        # 평가 기준을 동결한다. E-02 가 이 값의 불변을 시험한다.
        "scoring_inputs": {
            "competency_model_version_id": str(cmv_id),
            "axis_weights": {a: 1.0 / len(AXES) for a in AXES},
            "criterion_weights": {"C1": 1.0},
        },
        "created_at": now,
    })

    rows["report_item"].append({
        "company_id": company_id,
        "report_item_id": item_id,
        "report_id": report_id,
        "criterion_id": criterion_id,
        "criterion_name": "문제 해결",
        "competency_model_version_id": cmv_id,
        "assessment_state": spec.assessment_state,
        "observation": f"[합성] {ref} 관찰",
        "sufficiency": "direct",
        "axis_assessments": axis_assessments,
        "criterion_weight": 1.0,
        "axis_weights": {a: 1.0 / len(AXES) for a in AXES},
    })

    correlation[f"invitation_id:{ref}"] = str(invitation_id)
    correlation[f"applicant_id:{ref}"] = str(applicant_id)
    correlation[f"report_id:{ref}"] = str(report_id)


# --- 불변식 점검 -------------------------------------------------------------


def check_invariants(fx: Fixture) -> list[str]:
    """시드가 시험 기준선으로 쓸 수 있는 상태인지 확인한다.

    여기서 깨지면 시나리오가 아니라 시드가 틀린 것이다. 그 구분이 중요하다.
    """
    problems: list[str] = []
    evidence_ids = {str(e["evidence_id"]) for e in fx.of("evidence")}
    segment_ids = {str(s["transcript_segment_id"]) for s in fx.of("transcript_segment")}
    durations = {str(a["interview_session_id"]): a["duration_ms"] for a in fx.of("recording_asset")}
    sessions = {str(r["report_id"]): str(r["interview_session_id"]) for r in fx.of("report")}

    for item in fx.of("report_item"):
        for axis, data in item["axis_assessments"].items():
            cited = data.get("quoted_evidence_ids", [])
            if data.get("score") is None:
                if cited:
                    problems.append(f"{axis}: 점수 null 인데 인용 있음")
                continue
            if not cited:
                problems.append(f"{axis}: 점수 있는데 인용 없음")
            for ev in cited:
                if ev not in evidence_ids:
                    problems.append(f"{axis}: 존재하지 않는 Evidence 인용 {ev}")

    for ev in fx.of("evidence"):
        if str(ev["transcript_segment_id"]) not in segment_ids:
            problems.append(f"evidence {ev['evidence_id']}: 자막 구간 없음")

    for item in fx.of("report_item"):
        session = sessions.get(str(item["report_id"]))
        limit = durations.get(session)
        if limit is None:
            continue
        for ev in fx.of("evidence"):
            if str(ev["report_item_id"]) == str(item["report_item_id"]) and ev["video_end_ms"] > limit:
                problems.append(f"evidence {ev['evidence_id']}: 녹화 길이 초과")

    return problems


# --- DB 쓰기 -----------------------------------------------------------------


def upsert_sql(logical: str, row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    table = TABLES[logical]
    cols = list(row)
    conflict = ", ".join(PKEYS[logical])
    updates = [c for c in cols if c not in PKEYS[logical]]
    setter = ", ".join(f"{c} = EXCLUDED.{c}" for c in updates) or f"{cols[0]} = EXCLUDED.{cols[0]}"
    sql = (
        f"INSERT INTO {table} ({', '.join(cols)}) "
        f"VALUES ({', '.join(':' + c for c in cols)}) "
        f"ON CONFLICT ({conflict}) DO UPDATE SET {setter}"
    )
    return sql, row


def apply(connection, fx: Fixture) -> None:
    """행을 DB 에 쓴다. connection 은 SQLAlchemy Connection.

    ORDER 순서를 지켜 외래 참조를 만족시킨다. 멱등 upsert 이므로
    같은 라벨로 다시 돌려도 안전하다.
    """
    from sqlalchemy import text

    problems = check_invariants(fx)
    if problems:
        raise ValueError(f"시드 불변식 위반: {problems}")

    for logical in ORDER:
        for row in fx.of(logical):
            sql, params = upsert_sql(logical, row)
            connection.execute(text(sql), params)


def teardown(connection, fx: Fixture) -> None:
    """시드가 만든 회사를 통째로 지운다. 실행 간 격리용."""
    from sqlalchemy import text

    company_id = fx.correlation["company_id"]
    for logical in reversed(ORDER):
        connection.execute(
            text(f"DELETE FROM {TABLES[logical]} WHERE company_id = :cid"),
            {"cid": company_id},
        )
