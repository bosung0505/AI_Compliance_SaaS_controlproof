# Spec 004 E-01·E-02 — WhyYou 소스 기준선

- 조사일: 2026-10-07 (Specify 초안), 2026-10-07 Clarify 보강
- 조사 대상: WhyYou `be81ebccc6d4921ce7bc6610be9b0e7d0277c8a2` (포크 `Happy623623/gbsa_aws_yw`
  `yeonwoo/controlproof-n02-t083` = `bosung/controlproof-n02-integration` `c8e9970` + T083 + T082),
  ControlProof `455f5fc`(실행기 구조 확인용)
- 방법: 소스 읽기와 마이그레이션 읽기만 수행했다. 실제 실행·DB 조회·변경 주입은 하지 않았다.
- 읽는 법: "확인된 사실"은 파일과 줄 범위로 재확인할 수 있다. WhyYou 경로는 `backend/src/interview_evidence/`
  기준이다(마이그레이션과 시험은 `backend/` 기준). "코드상 예측"은 코드에서 도출한 동작이지만 실제 대상에서
  관찰하기 전까지 판정 근거로 쓰지 않는다. "미확인"은 격리 환경에서 확인하기 전까지 가정으로 두지 않는다.

## 1. 확인된 사실

### 점수와 인용 (E-01)

- 축 점수 모델 `AxisAssessment(axis, label, score: int|None 0~100, rationale, quoted_evidence_ids)`는
  점수가 있으면 반드시 인용 Evidence ID가 있어야 생성된다
  (`reporting/domain/report.py` 111~137, `__post_init__`의 ValueError). 인용 ID가 실제 Evidence인지는
  이 불변식이 확인하지 않는다.
- AI 응답 검증 `AssessmentVerdict.verified_against(available_evidence_ids)`는 점수가 있는데 인용이 비었거나,
  모델이 받은 Evidence 집합에 없는 ID를 인용한 축을 `score=None`, `quoted_evidence_ids=()`, 고정 사유
  "인용한 답변을 확인할 수 없어 점수를 보류했습니다."로 비운다(`reporting/application/assessment_prompt.py`
  273~299, 308). 집합은 그 기준의 검증된 Evidence뿐이다(`reporting/application/assessment_service.py` 129,
  `workers/reporting/report.py` 341~363). 따라서 빈 인용·미존재 ID·다른 지원자 ID·다른 기준 ID는 모두 같은
  경로로 비워진다. WhyYou 단위 시험이 이 경로를 다룬다(`tests/unit/reporting/test_criterion_assessment.py`).
- Evidence는 작업자가 그 기준에 매핑된 최종 답변 turn·자막 구간·녹화 구간으로 만들고 타임라인 검증을 통과한
  것만 남긴다(`workers/reporting/report.py` 137~166, `reporting/application/evidence_service.py` 19~49).
  `ReportItem`은 Evidence의 회사·항목·기준·버전 ID가 항목과 같아야 생성되고, `CONFIRMED`·
  `PARTIALLY_CONFIRMED` 항목은 Evidence가 하나 이상이어야 한다(`reporting/domain/report.py` 280~297).
- **점수 저장 경로(미확인 3 해소)**: 보고서 쓰기는 `ReportingRepository.save_report` 하나이고 호출자는 작업자의
  `ReportGenerator.generate`와 `EvidenceService.save_validated_report`뿐이다(`workers/reporting/report.py` 242,
  `reporting/application/evidence_service.py` 51~74). 보고서·항목·Evidence를 쓰는 HTTP 경로는 없다
  (회사용 reporting 라우터는 조회, 타임라인, 사람 검토, review artifact, 최종 결정, 삭제 요청만 있다:
  `reporting/api/company_routes.py` 401~710). `save_report`는 같은 `report_id`가 있으면 거부한다
  (`reporting/repositories/postgres.py` 727~735). 축 점수는 `report_items.axis_assessments` JSON에 저장되고
  저장소는 인용 ID를 Evidence 행과 대조하지 않는다(같은 파일 136~146, 776~792).
- 읽기 시 `_restored_axes`는 파싱되지 않는 축을 조용히 버린다(같은 파일 149~180). 저장소에 직접 "점수는
  있고 인용이 빈" 축을 쓰면 조회에서 그 축이 사라지고, 존재하지 않는 ID를 인용한 축은 그대로 조회된다.
- 저장 레코드: `reports`(model/prompt/config_version, status, summary, `overall_score`, `scoring_inputs`),
  `report_items`(criterion_id, competency_model_version_id, assessment_state, observation, rationale,
  sufficiency, uncertainty, follow_up_question, `criterion_weight`, `axis_weights`, 축 점수 JSON),
  `evidence`(report_item_id, criterion_id, competency_model_version_id, answer_turn_id,
  `transcript_segment_id`, video_start_ms/end_ms, generation_version)
  (`alembic/versions/reporting/d_001_reporting.py`, `integration/i_010_report_item_axis_scores.py`,
  `integration/i_014_report_scoring_inputs.py`).
- `evidence.transcript_segment_id`에는 `transcript_segments`로의 외래키가 없다. 외래키는 `report_items`로만
  있다(`d_001_reporting.py` 120~145). 따라서 자막 구간이 삭제·교체돼도 DB 수준에서는 Evidence 행이 남는다.
- **보고서 조회 응답(미확인 1의 코드 부분)**: `GET /v1/interview-sessions/{session_id}/report`는
  세션의 최신 보고서를 읽어 `_report_view`로 내보낸다(`reporting/api/company_routes.py` 401~435, 211~305).
  읽기 경로 `_report_from_row`는 `reports`·`report_items`·`evidence`만 읽고 `transcript_segments`를 읽지 않는다
  (`reporting/repositories/postgres.py` 818~898). 응답의 Evidence 항목은 `transcript_segment_id`를 그대로
  보여 주고 재생 가능 여부 필드가 없다. 점수 `average_score`·`overall_score`는 항목에 동결된 축 점수와
  가중치로 다시 계산한다. 자막 구간과 재생 정보를 읽는 곳은 `GET .../timeline`이다(`company_routes.py` 437~504).
- **근거 제거 수단(미확인 2의 코드 부분)**:
  - 재전사: `TranscriptService.correct`가 새 `transcript_segment_id`·`version+1` 행을 추가한다
    (`reporting/application/transcript_service.py` 58~78). 이 함수를 호출하는 라우트·작업자는 없다(호출자 0건).
    원래 행을 지우지 않으므로 Evidence가 가리키는 구간은 그대로 남는다.
  - 삭제 요청: `POST /v1/company/privacy/deletion-requests`의 범위는 `invitation`·`applicant`뿐이다
    (`reporting/domain/deletion.py` 40~41). 대상 목록에 보고서·Evidence·자막 구간이 함께 들어가므로
    (`reporting/application/public.py` 140~155, `reporting/application/deletion_service.py` 35~62) 보고서 자체가
    삭제된다. 제품 흐름에 복원은 없다.
  - 따라서 "보고서는 남기고 인용 근거만 제거"를 만드는 제품 경로는 없다. 남는 수단은 Run 소유 fixture 행
    (자막 구간)의 직접 제거와 재삽입이다.
- 보고서 생성 작업자는 `report.generation_requested` outbox 사건을 받아 세션 스냅샷, 역량 모델 버전,
  최종 turn, 전사 조각을 읽고 모델(ControlProof 고정 모델 대체 가능)로 기준별 평가를 만든 뒤 저장한다
  (`runtime/worker.py` 404~512, `workers/reporting/report.py`). T083 이후 `ai_assessment` 동의 확인이 시작 전에
  걸린다(`runtime/worker.py` 411~420).
- **고정 모델의 인용(미확인 8 해소)**: `ControlProofFixedModel`은 `assess_interview_criterion`에서 받은
  답변 중 첫 Evidence ID 하나를 모든 축에 인용하고 점수 72를 준다. 답변이 없으면 `None`
  (`runtime/controlproof_model_substitute.py` 108~127). 지원하는 fixture는 `h03-report-v1` 하나이고 다른
  ID는 기동 시 거부된다(같은 파일 16~18, 165~175). 잘못된 인용을 내보내게 하는 설정은 없다. 그렇게 하려면
  WhyYou local/test 코드에 새 fixture를 추가해야 한다(WhyYou 변경).

### 점수 입력·가중치 동결 (E-02)

- `report_items.criterion_weight`(기본 1.0)와 `axis_weights`(기본 `{}`)는 보고서 생성 시점에 버전에서
  복사한 스냅샷이다(`reporting/domain/report.py` 203~211, `workers/reporting/report.py` 210~214,
  `runtime/worker.py` 476, 498). 작업자는 세션 스냅샷이 가리키는 `competency_model_version_id`의 버전을
  읽는다(`runtime/worker.py` 422~425).
- **`scoring_inputs` 형태(미확인 5 해소)**: `_scoring_inputs`가 저장 시점에 다음 JSON을 만든다
  (`reporting/repositories/postgres.py` 78~133):
  `criteria[]{criterion_id, score, weight, normalized_weight, contribution}`,
  `excluded[]{criterion_id, weight, normalized_weight}`, `numerator`, `denominator`,
  `axis_weights{criterion_id: {axis: weight}}`(비어 있지 않은 항목만),
  `communication{score, numerator, denominator, scored_criteria[], unscored_criteria[]}`.
  축별 점수는 `scoring_inputs`에 없고 `report_items.axis_assessments`에 있다.
- `scoring_inputs`를 읽는 코드는 없다(저장소 밖 참조 0건; 주석 "No reader yet", `postgres.py` 91, 758).
  조회 응답의 `overall_score`·`scoring_breakdown`은 도메인 `Report.overall_score`·`criterion_aggregate`가 항목의
  동결 가중치로 다시 계산한 값이다(`reporting/domain/report.py` 321~380, `company_routes.py` 223~232).
  저장 열 `reports.overall_score`는 정렬용이다.
- 재계산 규칙: `scoring.aggregate`(`reporting/domain/scoring.py` 98~160). 점수 `None`은 분자·분모 모두에서
  빠지고, 가중치 합이 0이면 같은 가중치로 읽고, 결과는 `round(numerator / denominator)`(Python `round`,
  0.5는 짝수 쪽: 72.5→72, 73.5→74). 축 가중치에 없는 키는 1.0(`weights_for`, 163~171). 보고서 설정이
  `report-config-v2-communication-separated`이면 기준 점수에서 의사소통 축을 뺀다(`report.py` 17, 321~327).
  작업자는 이 설정으로 만든다(`workers/reporting/report.py` 233).
- **발행 버전 수정 가능성(미확인 4 해소, 열린 질문 3)**: 버전 관련 쓰기 HTTP는
  `POST /positions/{position_id}/competency-model-versions`(새 draft 생성)와
  `POST /competency-model-versions/{version_id}/publish`뿐이고 PUT·PATCH는 없다
  (`company_management/api/company_routes.py` 700, 764). `save_criterion_version` 호출자는
  `CriteriaService.create_version`(새 ID, `version_number = 기존 수 + 1`)과 `publish_version`(상태 전이)뿐이다
  (`company_management/application/criteria_service.py` 31~108). 도메인은 frozen이고 draft가 아니면
  `publish`·`replace_persona`가 `PublishedVersionImmutableError`를 낸다
  (`company_management/domain/criteria.py` 104~105, 295~325; 설명 183~187). 따라서 제품 경로로는 발행 버전의
  가중치를 제자리에서 바꿀 수 없고, 기준 변경은 새 버전 생성·발행뿐이다. 마이그레이션에 해당 테이블의 트리거는
  없으므로 저장소 직접 UPDATE는 막히지 않는다.
- 버전 상태 enum은 `draft`·`published`·`retired`다(`criteria.py` 28~31). 초안에 적은 `closed`는 오기였다.
  `RETIRED`로 전이하는 코드는 없다.
- 초대는 발급 시점의 최신 발행 버전(`version_number` 최대)에 묶인다(`company_management/application/
  hiring_service.py` 91~95). 새 버전으로 평가받으려면 두 번째 지원자는 새 버전 발행 뒤에 초대돼야 한다.
- **보고서 개수·재생성(미확인 6 해소)**: 작업자는 그 세션에 보고서가 있으면 새로 만들지 않고 기존 보고서를
  돌려준다(`runtime/worker.py` 430~441). 생성기는 항상 `version=1`로 만들고(`workers/reporting/report.py` 229),
  `(company_id, interview_session_id, version)`은 유일하다(`reporting/repositories/postgres.py` 320~324).
  조회는 최신 version을 읽는다(같은 파일 911~930). 따라서 한 세션에 보고서는 하나이고 재생성이 과거 보고서를
  덮어쓰지 않는다.
- **사람 검토(미확인 7 해소)**: 검토 기록은 별도 `HumanReview` 행으로 저장되고(`reporting/application/
  review_service.py` 133~158, `reporting/domain/review.py` 27~36) 보고서·항목·점수·가중치를 바꾸지 않는다.
  조회 응답에 `human_reviews`로 따로 붙는다(`company_routes.py` 303). E-02 범위 밖이다.
- Spec 003 seed는 역량 모델 버전 하나와 기준 하나를 만들며 WhyYou 모델이 읽을 수 있는 값으로 고정됐다
  (ID-003-15). Spec 003 fixture turn·자산·전사 조각 위에서 고정 모델이 `partial` 보고서를 실제로 만들었다
  (T084 child, 샌드박스 Run 7~9).

### ControlProof 실행기 구조 (열린 질문 5)

- Run 하나는 `scenario_id`·`scenario_version`·`scenario_digest`·`execution_profile`을 각각 하나만 가진다
  (`engine/models.py` 1247~1270).
- 시나리오 YAML 하나는 `scenario_id` 하나와 `execution_profile` 하나를 선언하고, 프로필마다 정해진 assertion·
  evidence·단계 목록과 대조된다(`engine/scenario.py` 153~290). `lanes` 필드의 타입은 `N02LaneId`뿐이다
  (같은 파일 161, `engine/models.py` 135~141).
- 실행기는 `execution_profile`로 등록·선택된다(`engine/runner.py` 880~918). CLI는 `scenario_id`별 허용
  프로필 표로 선택을 검증한다(`engine/cli.py` 465~496). retest는 부모 Run의 프로필을 따른다(같은 파일 240~280).
- 선례: E-03은 `scenario_id` 하나에 프로필 두 개(`E03_BEFORE_V2`, `E03_AFTER_V2`), YAML 두 개, Run 두 개다
  (`scenarios/E-03-BEFORE.yaml`, `scenarios/E-03-AFTER.yaml`). H-03도 같다.
- 범위표는 E-01과 E-02를 별도 행으로 관리한다(`docs/product/ControlProof_MVP_Scenario_Coverage_Matrix.md`
  44~45).

### 코드상 예측 (관찰 전에는 판정 근거로 쓰지 않음)

- P1. 인용한 Evidence의 자막 구간 행만 지우면 `GET .../report` 응답은 변하지 않는다(읽기 경로가 자막 구간을
  읽지 않음). 관찰되면 E01-A3 FAIL 후보다. Spec 003 원칙대로 첫 사실을 봉인하기 전에 WhyYou를 고치지 않는다.
- P2. `CONFIRMED` 항목의 Evidence 행을 모두 지우면 읽기에서도 `ReportItem` 생성이 실패해 보고서 조회가 오류가
  된다(`report.py` 280~289). Evidence 행 제거는 E-01 수단으로 쓰지 않는 편이 안전하다.
- P3. 고정 모델은 항상 유효 인용을 내므로, 고정 모델 경로만으로는 AI 응답 검증의 잘못된 인용 분기를 실제
  대상에서 일으킬 수 없다.

## 2. 미확인 — 남은 것과 확인 방법

코드로 닫히지 않은 것은 실제 대상 관찰이 필요한 항목뿐이다. 모두 읽기 전용 조회만으로는 확인할 수 없고(Spec 003
Run DB는 teardown으로 정리됨) 변경 주입이나 새 보고서 생성이 필요하므로 이번 Clarify 세션에서는 수행하지 않았다.
Plan 이후 샌드박스 진단 Run(Spec 003 ID-003-18의 격리 대상: PostgreSQL+pgvector, moto, WhyYou API·작업자,
AI 엔드포인트 loopback)에서 확인한다. 진단 Run은 공식 Run이 아니며 결과는 판정이 아니라 설계 입력이다.

1. P1 확인: Run 소유 fixture 자막 구간 하나를 지운 뒤 `GET .../report`와 `GET .../timeline` 응답을 지우기 전과
   비교한다. 같은 행을 재삽입한 뒤 두 응답이 원래와 같은지 본다.
2. P2 확인: Evidence 행 제거를 수단으로 채택할 때만 필요하다(채택하지 않으면 생략).
3. 고정 모델 보고서의 실제 저장 레코드: 새 진단 Run의 보고서에서 `reports.scoring_inputs`·`overall_score`와
   `report_items`를 읽기 전용 `SELECT`로 수집하고 조회 응답의 `scoring_breakdown`과 비교한다.
4. 새 버전 발행 뒤 두 번째 초대·처리 흐름이 seed/fixture 위에서 실제로 새 버전 ID와 새 가중치로 보고서를
   만드는지.

## 3. Spec 003에서 그대로 쓰는 것

- 실행기 기반: 시나리오 스냅샷·시간 정책, seed/overlay/전제 fixture, observer receipt, 봉인·검증, retest,
  RESTORE_FAILED·차단 규칙, 고정 모델 격리 증명.
- 상태 시드(E-02 "평가 기준 버전과 scoring_inputs")는 Spec 003의 N-02 seed와 fixture turn·자산·전사 조각을
  확장해 만든다. 경로 시드(동의 정책 버전)는 N-02 lane을 재사용한다(V4 §3 "E-02는 두 시드를 함께 사용").
  T083 이후 보고서 생성에는 `ai_assessment` 동의가 필요하므로 E-01·E-02 subject도 동의를 커밋한 상태여야 한다.
