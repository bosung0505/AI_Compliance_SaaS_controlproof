# Research: E-01·E-02 점수 근거·평가 기준 보존 검증

## 조사 범위

- ControlProof branch: `004-e01-e02-score-evidence` (base `003-n02-consent-order`, PR #1 병합 `d0c0e5b`)
- WhyYou 기준 branch: `bosung/controlproof-n02-integration`
- WhyYou 기준 commit: `eec8f706a6b8b3fb8d7c5193c7f349e9f9f93014` (`be81ebc`와 트리 동일)
- 조사일: 2026-10-07
- 원천: [Spec 004 소스 기준선](../../docs/research/Spec004_E01_E02_WhyYou_Source_Baseline.md)과 Plan 단계 추가 읽기
- 목적: Plan의 기술 결정 근거. 실제 E-01·E-02 Run 결과나 WhyYou PASS를 대신하지 않는다.

WhyYou 경로는 `backend/src/interview_evidence/` 기준이다. 기준선에서 확인한 줄 번호는 기준선 문서에 있고 여기서는
결정에 쓴 사실만 요약한다.

## R-001. E-01 주 시험 경계: 작업자 경로와 인용 모드 fixture

**Decision**: 잘못된 인용 시험은 실제 보고서 작업자(`ReportRequestedEventHandler` → `ReportGenerator` →
`CriterionAssessor.assess` → `verified_against` → `save_report`)를 통과시킨다. 모델 출력만 WhyYou local/test 고정 모델의
새 fixture `spec004-report-v1`로 바꾼다. 모드는 Run 소유 기준 설명(`criterion.text`)의 표식으로 고른다.

**Rationale**:

- 점수·Evidence를 쓰는 HTTP 경로는 없고 쓰기는 작업자의 `save_report` 하나다.
- 모델 payload에는 `criterion.criterion_id`, `criterion.name`, `criterion.text`, `provided_answers[].evidence_id`가 있다
  (`reporting/application/assessment_prompt.py` `build_assessment_prompt`). 기준 설명은 Run이 seed하므로 표식을 넣을
  수 있다.
- 현 고정 모델 `h03-report-v1`은 항상 첫 유효 Evidence를 인용하고 다른 fixture ID는 거부한다. 기존 fixture 동작을
  바꾸면 H-03·N-02 scenario의 fixture digest가 의미를 잃으므로 새 ID를 추가한다.
- fixture는 프로세스 시작 시 하나로 정해지므로(`resolve_controlproof_model`) 한 Run 안의 다섯 모드는 표식으로 갈라야
  한다.

**Alternatives rejected**:

- 저장소 직접 쓰기만 사용: 작업자의 검증을 전혀 통과하지 않아 도메인·저장소 무결성만 본다(보조 관찰로 유지).
- 모드마다 다른 fixture ID와 재기동: 한 Run에서 다섯 모드를 비교할 수 없고 작업자 재기동이 Run 시간 예산을 넘는다.
- 제품 `AssessmentVerdict` 코드에 시험 분기 추가: 제품 코드 변경이며 승인 범위 밖이다.

## R-002. 다섯 인용 모드의 입력 출처

**Decision**:

| 모드 | 모델이 내는 인용 | 출처 |
|---|---|---|
| `VALID` | 그 기준에 제공된 첫 Evidence ID | payload |
| `EMPTY` | `[]` (점수는 있음) | 고정 |
| `NONEXISTENT` | 표식에 적힌 UUID(실행기가 uuid5로 만든, 어디에도 없는 값) | 기준 설명 |
| `OTHER_APPLICANT` | 표식에 적힌 참조 지원자 보고서의 실제 Evidence ID | 기준 설명(참조 보고서 생성 뒤 seed) |
| `OTHER_CRITERION` | 표식이 가리키는 앞 기준에 같은 처리 호출에서 제공된 Evidence ID | fixture의 처리 호출 범위 기억 |

**Rationale**: Evidence ID는 생성 시점의 uuid7이라 미리 알 수 없다. 참조 지원자의 ID는 그 보고서가 저장된 뒤에만
알 수 있으므로 인용 시험 lane의 기준은 참조 보고서 생성 뒤 seed한다. 같은 보고서의 다른 기준 Evidence는 한 번의
`generate` 호출 안에서 기준 순서대로 만들어지므로 fixture가 그 호출 안에서 앞 기준에 받은 ID를 기억해야만 결정론적으로
낼 수 있다. 기억 범위는 같은 프로세스·같은 세션 payload로 제한하고, 앞 기준이 없으면 모드 실패를 receipt로 남긴다.

**Alternatives rejected**: 다른 기준 모드를 참조 지원자 Evidence로 대체(타 지원자와 타 기준이 섞여 원인 구분 불가),
다른 기준 모드 생략(Clarify의 네 종류 요구 미충족).

## R-003. fixture 원래 출력의 증거

**Decision**: `spec004-report-v1`은 local/test observer root가 설정돼 있으면 응답마다 비민감 emission receipt
(`controlproof.spec004-model-emission.v1`: criterion_id, mode, emitted quoted ids, emitted score, emitted_at)를 쓴다.
ControlProof는 이를 저장 레코드와 비교해 "모델이 의도한 잘못된 인용을 실제로 냈는가"를 독립 확인한다.

**Rationale**: 정규화된 저장 레코드만 보면 "작업자가 비웠다"와 "모델이 애초에 유효 인용을 냈다"를 구분할 수 없다.
Spec 003 ID-003-17이 제출·거부·시작을 별도 증거로 나눈 것과 같은 이유다.

**Alternatives rejected**: 모델 입력에서 기대 출력을 계산만 하기(대체물 결함을 탐지하지 못함), 작업자 로그 수집(과수집).

## R-004. 보조 deep probe

**Decision**: 별도 lane의 정상 보고서 항목 `report_items.axis_assessments` JSON에 네 종류의 잘못된 인용을 직접 쓰고
`GET .../report`를 읽은 뒤 원래 JSON으로 되돌린다. 결과는 진단 관찰 `E01-D1`로만 봉인한다.

**Rationale**: 저장소는 인용 ID를 Evidence와 대조하지 않고, 읽기 경로 `_restored_axes`는 "점수+빈 인용" 축을 조용히
버린다(기준선 §1). 이 노출 방식은 운영자에게 의미 있는 사실이지만 제품 쓰기 경로를 거치지 않으므로 대상 통제의
PASS/FAIL로 쓰지 않는다(Clarify Q1).

## R-005. 근거 제거 수단

**Decision**: 유효 인용 항목의 Evidence가 가리키는 `transcript_segments` 행(Run 소유 fixture)을 DELETE하고, 같은
컬럼 값으로 INSERT해 복원한다. Evidence 행은 건드리지 않는다.

**Rationale**:

- `evidence.transcript_segment_id`에는 외래키가 없어 자막 구간만 지울 수 있다.
- 제품 삭제 요청은 초대·지원자 단위로 보고서까지 지우고 복원이 없다. 재전사 `correct`는 호출 경로가 없고 원래 행을
  남긴다(기준선 §1).
- Evidence 행 삭제는 `CONFIRMED` 항목의 읽기를 실패시킬 것으로 예측된다(P2).

**Alternatives rejected**: 제품 삭제 요청(E-01 노출 시험 불가), 재전사(제품 경로 없음), Evidence 행 삭제(P2).

## R-006. 근거 제거 뒤 예측과 처리

**Decision**: `GET .../report` 읽기 경로는 `transcript_segments`를 읽지 않으므로(P1) 제거 뒤 응답이 그대로일 것으로
예측한다. 이것이 실제로 관찰되면 E01-A3 FAIL 후보이며 Spec 003 T080~T084 순서로 처리한다(plan §8). 타임라인은
자막 구간을 읽으므로 제거가 실제로 일어났다는 보조 증거로 함께 수집한다.

**Rationale**: 첫 사실을 봉인하기 전에 WhyYou를 고치면 탐지 증거가 사라진다(Constitution VI, Spec 003 R-013).

## R-007. 기준 변경 수단과 두 번째 지원자

**Decision**: E-02 lane의 Run 소유 직무에서 v1을 제품 API로 생성·발행하고, 첫 지원자 보고서를 만든 뒤 v2를 제품 API로
생성·발행한다. 두 번째 지원자는 발행 뒤 제품 API로 읽은 최신 발행 버전에 묶어 seed한다(plan 판단 보류 H-1).

**Rationale**:

- 버전 쓰기 HTTP는 `POST /positions/{position_id}/competency-model-versions`와
  `POST /competency-model-versions/{version_id}/publish`(If-Match 필요)뿐이다. 생성 body는 job requirement 1개 이상,
  `interview_duration_minutes=30`, 기준 가중치 합 100, 축 가중치는 비우거나 다섯 축 모두 합 100을 요구한다.
- 초대 API는 발급 시점의 최신 발행 버전에 묶는다(`hiring_service.py`). 실행기가 같은 규칙(최신 발행 버전)을 제품
  API 조회로 따르면 초대 발급·본인 확인 흐름 없이 같은 묶임을 재현한다.
- 보고서는 세션 스냅샷의 `competency_model_version_id`로 버전을 읽으므로 fixture 세션에도 같은 버전 ID를 넣는다.

**Alternatives rejected**: 발행 버전 직접 UPDATE(제품 경로 아님), Spec 003처럼 버전 행 직접 seed(제품의 생성·발행
검증을 거치지 않아 "기준 변경"이 제품 동작이 아님).

## R-008. 재계산 사본

**Decision**: `engine/judges/e02_scoring.py`에 WhyYou `reporting/domain/scoring.py`의 `aggregate`·`weights_for`와
`Report.score_for`·`criterion_aggregate`·의사소통 축 분리 규칙의 사본을 둔다. 사본은 원본 경로와 git blob SHA를 상수로
가지며 preflight가 대상 checkout의 blob SHA와 비교한다.

**Rationale**:

- `scoring_inputs`를 읽는 코드가 WhyYou에 없고 조회 응답은 도메인이 동결 가중치로 다시 계산한다. 대상 함수를 호출하면
  대상 코드를 판정자로 쓰게 된다(Clarify Q4).
- 규칙의 미세 차이(0 가중치 합 → 동일 가중치, 없는 축 키 → 1.0, `round` 짝수 반올림, `report-config-v2-communication-
  separated`에서 의사소통 축 제외)가 결과를 바꾼다.

**Comparison targets**: 저장 `reports.overall_score`, `scoring_inputs.numerator`·`denominator`·`criteria[]`,
조회 응답 `overall_score`·`scoring_breakdown`·항목 `average_score`.

## R-009. 고정 점수와 가중치 효과

**Decision**: `spec004-report-v1`은 기준 설명 표식 `score=NN`이 있으면 그 기준의 모든 축에 NN을 준다(없으면 72).
E-02 v1·v2의 기준 점수를 다르게 두어 가중치 변경이 총점을 바꾸고 짝수 반올림 사례(예: 71.5 → 72)를 실측한다
(plan 판단 보류 H-2).

**Rationale**: 72 고정이면 가중치를 바꿔도 총점이 같아 동결 여부를 가중치·분자·분모로만 볼 수 있다. 판정은 가능하지만
"재계산이 저장값과 같다"는 주장이 사소하게 참이 된다.

## R-010. 보고서 생성 입력 fixture

**Decision**: Spec 003 `build_probe_overlay_rows`·`apply_processing_prerequisites` 패턴을 확장해 lane마다 완료 세션,
기준별 면접관 질문 turn·지원자 최종 turn, 질문 근거(`target_criterion_id`), 자막 구간, 최종 녹화 자산을 seed한다.
보고서 요청은 Spec 003 평가 경로처럼 `report.generation_requested` outbox 사건을 넣는다.

**Rationale**: 작업자는 질문 근거로 답변을 기준에 묶고, 자막 구간이 없는 turn은 건너뛰며, `final_video` 자산과 지원자
turn이 없으면 재시도한다(`runtime/worker.py`). Spec 003 child가 같은 방식으로 보고서를 실제로 만들었다.

## R-011. 동의 전제

**Decision**: 모든 E-01·E-02 subject는 보고서 요청 전에 Spec 003 `ConsentAdapter`로 정책 조회·동의 커밋을 한다.

**Rationale**: T083 이후 `ai_assessment` 동의가 없으면 보고서 작업자가 거부한다. H-03 seed가 겪은 문제(ID-003-19)를
반복하지 않는다. 동의 행을 직접 seed하지 않고 제품 API를 쓰는 이유는 V4 §3 "E-02는 경로 시드(동의 정책 버전)를
함께 사용"을 따르기 위해서다.

## R-012. profile/schema 확장

**Decision**: 새 profile `E01_CITATION_EVIDENCE_V1`, `E02_SCORING_FREEZE_V1`, schema `controlproof.scenario.v4`, bundle
profile `controlproof.bundle-profile.spec004.v1`을 추가한다. `ScenarioDefinition.lanes`는 profile별 lane enum을
허용하도록 넓힌다.

**Rationale**: Run 하나는 scenario_id·profile을 하나씩 가진다(Clarify Q5). 현 `lanes` 타입은 `N02LaneId`뿐이고 v3
검증은 N-02 전용이다. v1·v2·v3 시나리오와 기존 bundle 검증은 바꾸지 않는다.

## R-013. 시간 정책

**Decision**: N-02 값을 재사용한다: poll 2초, 연속 3회·4초 안정화, restore 120초, Run 540초, verify 60초. fault marker가
없으므로 `fault_ttl_seconds`는 두지 않는다.

**Rationale**: 보고서 작업자 처리와 안정화 읽기가 주 시간이다. Spec 003 child가 같은 작업자 경로를 예산 안에서 돌렸다.

## R-014. DB migration과 웹 UI

**Decision**: WhyYou migration·제품 코드·ControlProof 웹 UI를 추가하지 않는다. WhyYou 변경은 local/test 고정 모델 파일과
그 시험뿐이다(최초 FAIL 뒤 승인된 보완은 별도).

## 남은 확인 (Implement 중 샌드박스 진단)

진단 Run은 공식 Run이 아니며 결과는 판정이 아니라 설계 입력이다. Spec 003 ID-003-18의 격리 대상(PostgreSQL+pgvector,
moto, WhyYou API·작업자, AI 엔드포인트 loopback)을 쓴다.

| ID | 확인 내용 | 방법 | 결과가 바꾸는 것 |
|---|---|---|---|
| SD-1 | P1: 자막 구간 제거 뒤 보고서 조회가 그대로인가 | Run 소유 행 제거 → report·timeline 조회 → 재삽입 → 재조회 | E01-A3 예상, 보완 경로 준비 |
| SD-2 | 실제 `scoring_inputs`·`overall_score`·응답 `scoring_breakdown` 값 | 진단 보고서에 읽기 전용 SELECT와 GET | 재계산 비교 허용 오차 |
| SD-3 | v2 발행 뒤 최신 발행 버전에 묶인 두 번째 지원자가 v2 가중치로 보고서를 받는가 | 제품 API 생성·발행 → seed → 보고서 | E02-A2 전제 |
| SD-4 | 다섯 인용 모드의 emission receipt와 저장 레코드 | 새 fixture로 진단 보고서 | E01-A1·A2 판정 입력 |
| SD-5 | deep probe 쓰기 뒤 조회 노출(빈 인용 축 소실 예측) | JSON 직접 쓰기 → GET → 원복 | E01-D1 기록 형식 |

## Resolved Planning Questions

| 질문 | 결론 |
|---|---|
| 잘못된 인용 주 시험 경계 | 작업자 경로 + `spec004-report-v1` 인용 모드 |
| 보조 시험 | report item JSON 직접 쓰기, 진단 관찰 `E01-D1` |
| 근거 제거·복원 | Run 소유 자막 구간 행 DELETE/INSERT, Evidence 행 불변 |
| 기준 변경 | 제품 API 생성·발행, 두 번째 지원자는 최신 발행 버전에 묶음 |
| 재계산 | ControlProof 사본, 원본 blob SHA 고정, 세 비교 대상 |
| 판정 단위 | E-01·E-02 별도 profile·Run |
| 격리 한계 | fixture 입력·외부 AI 차단·fixture ID를 결과에 표시 |
| P1 관찰 시 | 봉인 → 분류 → 승인된 최소 수정 → child |

Plan 단계의 `NEEDS CLARIFICATION`은 0개다. 보성 결정이 필요한 판단 보류 H-1~H-4는 plan.md에 있다.
