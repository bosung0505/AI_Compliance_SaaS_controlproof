# Spec 004 E-01·E-02 — WhyYou 소스 기준선

- 조사일: 2026-10-07
- 조사 대상: WhyYou `be81ebccc6d4921ce7bc6610be9b0e7d0277c8a2` (포크 `Happy623623/gbsa_aws_yw`
  `yeonwoo/controlproof-n02-t083` = `bosung/controlproof-n02-integration` `c8e9970` + T083 + T082)
- 방법: 소스 읽기와 마이그레이션 읽기만 수행했다. 실제 실행·DB 조회는 하지 않았다.
- 읽는 법: "확인된 사실"은 파일과 줄 범위로 재확인할 수 있다. "미확인"은 Spec 004 Source discovery에서
  격리 환경으로 확인하기 전까지 가정으로 두지 않는다.

## 1. 확인된 사실

### 점수와 인용 (E-01)

- 축 점수 모델 `AxisAssessment(axis, label, score: int|None 0~100, rationale, quoted_evidence_ids)`는
  점수가 있으면 반드시 인용 Evidence ID가 있어야 생성된다
  (`reporting/domain/report.py` 112~137, `__post_init__`의 ValueError). 이 불변식은 도메인 객체 생성 시점에만
  걸린다.
- AI 응답 검증 `AssessmentResponse.verified_against(available_evidence_ids)`는 모델이 받은 Evidence 집합에
  없는 ID를 인용한 점수를 `score=None`, `quoted_evidence_ids=()`, 고정 사유 문구로 비운다
  (`reporting/application/assessment_prompt.py` 273~299). 다른 지원자·다른 기준의 Evidence ID는 그 집합에
  없으므로 같은 경로로 비워진다.
- 저장 레코드: `reports`(model/prompt/config_version, status, summary, `overall_score`, `scoring_inputs`),
  `report_items`(criterion_id, competency_model_version_id, assessment_state, observation, rationale,
  sufficiency, uncertainty, follow_up_question, `criterion_weight`, `axis_weights`, 축 점수 JSON),
  `evidence`(report_item_id, criterion_id, competency_model_version_id, answer_turn_id,
  `transcript_segment_id`, video_start_ms/end_ms, generation_version)
  (`alembic/versions/reporting/d_001_reporting.py`, `integration/i_010_report_item_axis_scores.py`,
  `integration/i_014_report_scoring_inputs.py`).
- `evidence.transcript_segment_id`에는 `transcript_segments`로의 외래키가 없다. 외래키는 `report_items`로만
  있다(`d_001_reporting.py` 127~140). 따라서 자막 구간이 삭제·교체돼도 DB 수준에서는 Evidence 행이 남는다.
- 회사용 보고서 조회 경로: `GET /v1/company/interview-sessions/{session_id}/report`,
  `.../review-artifacts`, `.../timeline`; 사람 검토 기록은
  `POST /v1/company/reports/{report_id}/items/{report_item_id}/reviews`
  (`reporting/api/company_routes.py`).
- 보고서 생성 작업자는 `report.generation_requested` outbox 사건을 받아 세션 스냅샷, 역량 모델 버전,
  최종 turn, 전사 조각을 읽고 모델(ControlProof 고정 모델 대체 가능: `assess_interview_criterion`,
  `assess_job_requirement`)로 기준별 평가를 만든 뒤 저장한다(`runtime/worker.py` ReportRequestedEventHandler,
  `workers/reporting/report.py`). T083 이후 동의 확인이 시작 전에 걸린다.

### 점수 입력·가중치 동결 (E-02)

- `report_items.criterion_weight`(기본 1.0)와 `axis_weights`(기본 `{}`)는 발행된 역량 모델 버전에서
  보고서 생성 시점에 복사한 스냅샷이며, 이후 회사가 가중치를 바꿔도 다시 읽지 않도록 설계돼 있다
  (`report.py` 204~212 주석, `i_014` 설명). `reports.scoring_inputs`는 계산에 실제로 쓰인 가중치·분자·분모와
  근거 부족으로 제외된 기준을, `reports.overall_score`는 정렬용으로 비정규화한 가중 점수를 담는다.
- 집계는 항목의 스냅샷에서 계산된다(`ReportItem.axis_aggregate`, `competency_score`,
  `Report` 수준 가중 집계 `report.py` 300~380). 분모는 설정 총합이 아니라 실제로 센 가중치의 합이다.
- 역량 모델 버전은 `create_version`과 `publish_version`으로 관리된다
  (`company_management/application/criteria_service.py` 31~, 96~). 버전마다 `status`(draft/published/
  closed)와 `published_at`이 있고, 보고서 항목은 `competency_model_version_id`로 버전을 가리킨다.
- Spec 003 seed는 역량 모델 버전 하나와 기준 하나를 만들며 WhyYou 모델이 읽을 수 있는 값으로 고정됐다
  (ID-003-15). Spec 003 fixture turn·자산·전사 조각 위에서 고정 모델이 `partial` 보고서를 실제로 만들었다
  (T084 child, 샌드박스 Run 7~9).

## 2. 미확인 — Source discovery에서 확인할 것

1. `GET .../report` 응답이 인용 Evidence의 자막 구간이 없을 때 점수를 그대로 보여 주는지, 근거 부족으로
   표시하는지, 재생 정보만 빠지는지. (E-01 변경 주입의 핵심)
2. 자막 구간 삭제·교체 경로: 운영자 재전사(`transcript_segments.version`)와 삭제 요청
   (`/privacy/deletion-requests`) 중 어느 것이 E-01의 "근거 제거"에 해당하는지, 그리고 복원 가능 여부.
3. 점수 "저장 경로"에 HTTP 노출이 있는지. 현재 확인된 쓰기 경로는 작업자의 보고서 저장과 사람 검토
   기록뿐이다. 실행기가 우회 입력을 넣을 경계가 저장소 직접 쓰기(deep probe)인지 작업자 입력인지 정해야 한다.
4. 발행된 버전의 가중치를 제자리에서 바꿀 수 있는지(`save_criterion_version`이 published에도 쓰이는지),
   아니면 새 버전만 만들 수 있는지. E-02 "기준 변경"의 구현 방식이 여기에 달려 있다.
5. `scoring_inputs`의 정확한 JSON 형태와 재계산 함수의 입력. 총점 재계산 비교를 어느 계층에서 할지.
6. 동일 지원자에 보고서가 두 개 이상 생길 수 있는지(`reports.version`), 재생성이 과거 보고서를 덮어쓰는지.
7. 사람 검토 기록이 점수나 가중치를 바꾸는지(E-02 범위 밖이라면 명시).
8. 고정 모델이 `quoted_evidence_ids`를 어떻게 채우는지, 잘못된 인용을 의도적으로 내보내게 할 수 있는지
   (E-01 AI 응답 검증 경로 시험에 필요).

## 3. Spec 003에서 그대로 쓰는 것

- 실행기 기반: 시나리오 스냅샷·시간 정책, seed/overlay/전제 fixture, observer receipt, 봉인·검증, retest,
  RESTORE_FAILED·차단 규칙, 고정 모델 격리 증명.
- 상태 시드(E-02 "평가 기준 버전과 scoring_inputs")는 Spec 003의 N-02 seed와 fixture turn·자산·전사 조각을
  확장해 만든다. 경로 시드(동의 정책 버전)는 N-02 lane을 재사용한다(V4 §3 "E-02는 두 시드를 함께 사용").
