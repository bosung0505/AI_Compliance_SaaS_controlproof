# Feature Specification: E-01·E-02 점수 근거·평가 기준 보존 검증

**Feature Branch**: `004-e01-e02-score-evidence`

**Created**: 2026-10-07

**Status**: Draft — Clarify 진행 중. 3·5번은 코드로 닫혔고 1·2·4·6번은 보성 확인 대기다. 전부 닫히기 전에는
Plan으로 넘어가지 않는다.

**Input**: V4 §10.10 E-01, §10.11 E-02, Decision Log D-013(Spec 004 범위), Spec 003 완료 상태,
[Spec 004 소스 기준선](../../docs/research/Spec004_E01_E02_WhyYou_Source_Baseline.md)

## Clarifications

근거 파일·줄은 [소스 기준선](../../docs/research/Spec004_E01_E02_WhyYou_Source_Baseline.md) §1에 있다
(WhyYou `be81ebc`, ControlProof `455f5fc`).

### Session 2026-10-07 (코드로 닫힘)

- Q3. **E-02 "기준 변경"의 수단** → A: 새 버전 생성·발행 뒤, 발행 **이후에 초대한** 두 번째 지원자를 처리한다.
  발행 버전의 제자리 수정은 제품 경로에 없다(버전 쓰기 HTTP는 생성·발행뿐, 발행 버전은 frozen이며
  `PublishedVersionImmutableError`). 초대는 발급 시점의 최신 발행 버전에 묶이므로 두 번째 지원자는 새 버전 발행
  뒤에 초대해야 한다. 저장소 직접 UPDATE로 발행 버전을 바꾸는 것은 제품 흐름이 아니므로 주 시험에 넣지 않는다.
  영향: US3, Edge Case 4, FR-031·032, E02-A2.
- Q5. **판정 단위** → A: 시나리오 ID 두 개(E-01, E-02), 실행 프로필 두 개, YAML 두 개, Run 두 개로 분리한다.
  실행기 구조상 Run 하나는 `scenario_id`·`execution_profile`·스냅샷을 하나씩만 가지고, `lanes`는 N-02 전용
  타입이며, 범위표도 E-01·E-02를 별도 행으로 관리한다. 한 Run의 lane으로 묶으려면 Run 모델·CLI·범위표 대응을
  바꿔야 한다. E-03(BEFORE/AFTER)의 "두 프로필, 두 Run" 선례를 따른다. seed·fixture·관찰·봉인 코드는 공유하되
  판정·bundle·retest 계보는 시나리오별로 따로 둔다. 영향: FR-040·043, Assertion Contract, SC-001·003·006.

### 보성 확인 대기

코드 사실은 선택지를 좁혔지만 제품 의미 결정이라 보성의 답이 필요하다. 각 항목에 추천안을 적었다.

1. **E-01 "저장 경로"의 경계.** 코드 사실: 점수·Evidence를 쓰는 HTTP 경로는 없고 쓰기는 작업자의 `save_report`
   하나다. AI 응답 검증(`verified_against`)이 네 종류의 잘못된 인용을 모두 비우지만, 고정 모델은 항상 첫 유효
   Evidence를 인용하고 fixture 선택지도 없어서 그 분기를 실제 대상에서 일으키려면 WhyYou local/test 코드에 새
   fixture가 필요하다. 저장소는 인용 ID를 Evidence와 대조하지 않으며, 직접 쓴 "점수+빈 인용" 축은 읽을 때 조용히
   사라진다. 선택지: (a) 저장소 직접 쓰기 deep probe(제품 보호조치가 아닌 저장소 무결성 시험), (b) 새 고정 모델
   fixture로 작업자 경로(WhyYou 변경 필요, 승인 대상), (c) 둘 다. 추천: (b)를 주 시험으로, (a)는 "저장 뒤 노출"
   관찰로 보조. (b)는 WhyYou 제품 코드가 아닌 local/test 대체물 변경이지만 승인을 받는다.
2. **E-01 "근거 제거"의 수단.** 코드 사실: 삭제 요청은 초대·지원자 단위로 보고서까지 함께 지우고 복원이 없다.
   재전사(`TranscriptService.correct`)는 호출하는 라우트가 없고 원래 행을 남긴다. "보고서는 남기고 근거만 제거"하는
   제품 경로는 없다. 선택지: (a) Run 소유 fixture 자막 구간의 직접 제거·재삽입(변경 주입), (b) 삭제 요청(보고서도
   사라져 E-01 노출 시험이 되지 않음), (c) 재전사(제품 경로 없음). 추천: (a)를 변경 주입으로 정의하고 Evidence 행
   제거는 쓰지 않는다(조회 오류 예측 P2). 코드상 예측 P1(조회 응답이 변하지 않음)이 맞으면 E01-A3 FAIL 후보이고,
   첫 사실을 봉인하기 전에 WhyYou를 고치지 않는다.
3. (코드로 닫힘, 위 Q3)
4. **총점 재계산의 위치.** 코드 사실: `scoring_inputs`를 읽는 코드가 없고, 조회 응답의 점수는 항목의 동결 가중치로
   도메인이 다시 계산한다. 계산 규칙은 `scoring.aggregate`(None 제외, 가중치 합 0이면 동일 가중치, Python
   `round`의 짝수 반올림, 의사소통 축 분리 설정). 추천: ControlProof가 이 규칙의 사본으로 독립 재계산하고
   (1) 저장 `overall_score`, (2) `scoring_inputs`의 numerator/denominator, (3) 조회 응답 `overall_score`·
   `scoring_breakdown` 세 값을 모두 비교한다. WhyYou 함수 호출은 대상 코드를 판정자로 쓰게 되므로 하지 않는다.
5. (코드로 닫힘, 위 Q5)
6. **격리 환경의 한계 선언.** 코드 사실: 고정 모델은 보고서 평가 작업만 지원하고 보고서는 Spec 003 fixture
   turn·자산·전사 조각 위에서 만들어진다. 추천: E-01·E-02의 판정 대상은 "보고서 생성 이후의 저장·노출·동결"이므로
   fixture 위 보고서를 실제 처리로 인정하되, 입력 turn이 fixture라는 사실과 외부 AI 차단을 한계로 증적에 표시한다
   (FR-003 유지).

## User Scenarios & Testing *(mandatory)*

### Feature Goal

AI가 산출한 점수가 (1) 유효한 답변 근거 없이는 저장·노출되지 않고, (2) 근거가 사라지면 정상 점수처럼
보이지 않으며, (3) 생성 당시의 점수 입력·가중치·버전을 자체 기록해 이후 기준 변경이 과거 리포트를
조용히 바꾸지 못함을, 실제 WhyYou 시험환경에서 원본 증적과 함께 판정한다. 판정은 ControlProof의 계약
완료와 WhyYou의 대상 동작을 분리해 기록한다(Spec 003의 구분 유지).

### 용어

- **점수 근거(Evidence)**: 보고서 항목의 축 점수가 인용하는 답변 turn·자막 구간·영상 구간 기록.
- **유효한 인용**: 같은 지원자, 같은 보고서 항목(기준)에 속하고 모델이 실제로 받은 Evidence ID.
- **근거 부족 상태**: 점수가 없거나 비워졌고 그 사유가 보존된 상태. 점수 숫자만 남은 상태가 아니다.
- **점수 입력 동결**: 리포트가 `scoring_inputs`, 기준별 `criterion_weight`, 축별 `axis_weights`,
  `competency_model_version_id`, 모델·프롬프트·설정 버전을 스스로 보존하는 것.

### User Story 1 - 유효하지 않은 인용으로 점수 저장을 시도한다 (Priority: P1)

E-01 우회. 비어 있는 인용, 존재하지 않는 Evidence ID, 다른 지원자의 Evidence ID, 다른 기준의 Evidence ID로
점수 저장을 시도하고, AI 응답 검증 경로에도 같은 잘못된 인용을 넣는다. 유효한 동일 지원자·동일 기준 인용의
기준 사례는 정상 저장돼야 한다.

**Independent Test**: 다섯 종류의 입력 각각에 대해 저장 결과(거부·`null`화·정상)와 저장 레코드를 비교한다.

**Acceptance Scenarios**:

1. 인용이 빈 점수 → 저장 거부 또는 점수 `null`·인용 제거, 사유 보존.
2. 존재하지 않는 ID, 다른 지원자 ID, 다른 기준 ID → 각각 1과 같은 결과이며 잘못된 ID가 저장 레코드에 남지 않는다.
3. 유효한 인용 → 점수·인용·사유가 저장되고 Evidence의 지원자·기준 ID가 요청과 일치한다.
4. 어느 경우에도 다른 지원자의 보고서·Evidence 행은 변하지 않는다.

### User Story 2 - 저장 뒤 근거를 제거하고 노출을 확인한다 (Priority: P1)

E-01 변경 주입. 정상 저장된 점수가 인용한 Evidence의 자막 구간을 제거하고 보고서를 조회한다. 제거한 근거를
복원하면 조회 결과가 원래대로 돌아와야 한다.

**Acceptance Scenarios**:

1. 제거 뒤 조회: 해당 점수가 근거 부족 상태로 드러나고, 재생 불가능한 인용이 정상 인용처럼 표시되지 않는다.
2. 제거 전·후 조회 결과의 차이가 제거한 Evidence에만 한정된다.
3. 복원 뒤 조회가 제거 전과 같다(점수·인용·사유 동일).
4. Run 종료 시 제거·복원이 원상태로 끝났음이 안전 상태 확인으로 증명된다.

### User Story 3 - 기준 변경 뒤 과거 리포트가 보존되는지 확인한다 (Priority: P1)

E-02. 첫 지원자를 현재 발행 버전으로 처리해 리포트와 동결 입력을 수집하고, 기준·가중치를 바꾼 새 버전을 생성·발행한
뒤 그 이후에 초대한 두 번째 지원자를 처리한다(Clarify Q3: 발행 버전의 제자리 수정은 제품 경로에 없다). 첫 지원자의
리포트를 다시 조회해 최초 결과·입력·가중치·버전이 그대로인지, 저장된 입력으로 총점을 재계산한 값이 저장된 결과와
같은지 확인한다.

**Acceptance Scenarios**:

1. 첫 리포트는 `scoring_inputs`, 항목별 `criterion_weight`·`axis_weights`, `competency_model_version_id`,
   모델·프롬프트·설정 버전을 모두 가진다. `scoring_inputs`만 있고 실제 계산 가중치가 없으면 동결 미완.
2. 새 버전 발행 뒤 두 번째 리포트는 새 버전 ID와 새 가중치로 만들어지고, 첫 리포트는 옛 버전 ID를 계속 가리키며
   재조회 결과가 변경 전과 바이트 단위로 같은 사실(점수·입력·가중치·버전)을 보여 준다.
3. 저장된 입력만으로 독립 재계산한 총점이 저장된 총점과 같다.
4. 기준 변경 전·후 설정, 두 리포트, 재계산 결과가 봉인된다.

### User Story 4 - 결과와 증적 한계를 검토한다 (Priority: P2)

Spec 003 US4와 같다. 경로별 요청·검증·저장·조회 결과, 제거 전후 비교, 재계산 입력과 결과를 사람이 읽을 수
있게 제시하고, 격리 환경의 한계(fixture turn 위의 보고서, 외부 AI 차단)를 함께 표시한다.

### User Story 5 - 최초 결과를 보존하고 수정 후 재시험한다 (Priority: P3)

Spec 003 US5와 같다. 최초 FAIL은 보존하고 원인 분류 뒤 parent-linked child로 재시험한다.

### Edge Cases

- 점수는 있으나 축이 "평가 불가"(`score=None`)인 항목은 인용 없음이 정상이다. 이를 근거 없는 점수로 오판하지 않는다.
- 같은 세션의 보고서는 하나다(작업자가 기존 보고서를 돌려주고 생성기는 `version=1`만 쓴다). 그래도 "첫 리포트"는
  Run이 만든 보고서 ID로 고정하고, 같은 세션에 두 번째 보고서 행이 생기면 그 자체를 관찰 사실로 기록한다.
- 근거 제거 중 다른 지원자의 전사 조각이 같은 turn 버전을 공유하는 경우가 있는지 확인하고, 있으면 대상 외로 둔다.
- 기준 변경은 새 버전 발행으로만 가능하다(Clarify Q3). "변경"은 발행으로 정의하고, 첫 지원자의 보고서가 옛 버전 ID를
  가리키는지로 판정한다. 발행 전에 초대된 지원자는 옛 버전으로 평가되므로 두 번째 지원자로 쓰지 않는다.

## Requirements *(mandatory)*

### Functional Requirements

#### 시나리오·대상·준비 상태

- **FR-001**: E-01·E-02는 `LOCAL_EMULATED` 격리 WhyYou 대상에서만 실행하고, 외부 AI 차단·작업자 증명·소스 clean을
  Spec 003 preflight 계약 그대로 요구한다.
- **FR-002**: 모든 지원자·보고서·Evidence는 Run 소유 합성 데이터이며, Run 종료 시 Run 소유 행만 제거한다
  (ID-003-12 규칙 유지).
- **FR-003**: 보고서는 Spec 003 fixture(세션·turn·자산·전사 조각) 위에서 고정 모델로 실제 생성한다. 고정 모델이
  만든 보고서임을 증적에 표시한다.

#### E-01 인용 검증

- **FR-010**: 실행기는 빈 인용, 미존재 ID, 다른 지원자 ID, 다른 기준 ID, 유효 인용의 다섯 입력을 Clarify §1에서
  정한 경계로 보낸다. 각 입력의 payload, 대상 응답, 저장 레코드 전후를 수집한다.
- **FR-011**: 판정은 저장 레코드로 한다. 거부와 `null`화는 둘 다 PASS이되 어느 쪽인지 기록한다. 잘못된 ID가
  Evidence 행으로 남으면 FAIL.
- **FR-012**: AI 응답 검증 경로는 모델 출력 대체(고정 모델)로 같은 다섯 입력을 넣어 정규화 결과를 수집한다.

#### E-01 근거 제거·복원

- **FR-020**: 근거 제거는 Clarify §2의 수단으로 하고, 제거 전·후·복원 후 세 번의 보고서 조회를 같은 경로로 수집한다.
- **FR-021**: 제거 뒤 조회에서 해당 점수가 근거 부족 상태로 식별되지 않으면 FAIL. 다른 항목이 변하면 FAIL.
- **FR-022**: 복원 뒤 조회가 제거 전과 다르면 FAIL. 복원 실패는 `RESTORE_FAILED`로 처리하고 같은 대상의 후속
  변경 주입을 차단한다.

#### E-02 동결·보존

- **FR-030**: 첫 지원자 리포트에서 동결 입력 집합(점수 입력, 기준별·축별 가중치, 버전 ID, 모델·프롬프트·설정
  버전)을 수집하고 누락 필드는 항목별로 기록한다.
- **FR-031**: 기준 변경은 제품 API로 새 버전을 생성·발행하는 것이다(Clarify Q3). 변경 전·후 버전 스냅샷(버전 ID,
  번호, 상태, 기준별 가중치, 축 가중치)을 수집하고, 두 번째 지원자는 발행 뒤에 초대한다. 새 버전은 Run 소유 데이터로
  teardown 대상이다.
- **FR-032**: 두 번째 지원자 처리 뒤 첫 리포트 재조회와 저장 레코드가 변경 전과 다르면 FAIL. 두 번째 리포트가
  새 버전 ID·가중치로 만들어지지 않았으면 해당 assertion은 대상 동작이 아니라 전제 실패이므로 사유 코드와 함께
  `INCONCLUSIVE`로 둔다.
- **FR-033**: 독립 재계산 총점과 저장 총점이 다르면 FAIL. 재계산 규칙 사본과 입력을 봉인한다.

#### 판정·증적·복구

- **FR-040**: assertion(§E01/E02 Assertion Contract)별 PASS/FAIL/INCONCLUSIVE와 사유 코드를 Spec 003과 같은 판정
  모델로 낸다. 판정은 시나리오별 Run 단위다(Clarify Q5). E-01 Run의 전체 PASS는 E01-A1~A4, E-02 Run의 전체 PASS는
  E02-A1~A3이 모두 PASS일 때만.
- **FR-043**: E-01과 E-02는 시나리오 ID·실행 프로필·YAML·Run·bundle·retest 계보를 각각 따로 가진다. seed·fixture·
  관찰·봉인 구현은 공유할 수 있으나 한 Run의 결과가 다른 시나리오의 판정 근거가 되지 않는다.
- **FR-041**: 변경 주입(근거 제거, 기준 변경)은 Run 종료 전 원상 복구하고 안전 상태를 확인한다. 미확인이면
  `RESTORE_FAILED`와 차단.
- **FR-042**: 증적은 Spec 003 봉인·검증·redaction 계약을 따르고, 보고서 본문의 자유 텍스트는 합성 데이터만 담는다.

### E01/E02 Assertion Contract (초안)

E01-A* 는 E-01 Run, E02-A* 는 E-02 Run에서만 판정한다(Clarify Q5).

| ID | 주장 | 판정 근거 |
|---|---|---|
| E01-A1 | 빈·미존재·타 지원자·타 기준 인용은 저장 또는 검증에서 비워진다 | 입력 4종의 저장 레코드와 정규화 결과 |
| E01-A2 | 유효 인용은 정상 저장된다 | 기준 사례의 저장 레코드와 Evidence 소유 ID |
| E01-A3 | 근거 제거 뒤 점수는 근거 부족으로 노출된다 | 제거 전·후 조회 비교 |
| E01-A4 | 근거 복원 뒤 조회가 원상 복구된다 | 복원 후 조회와 제거 전 조회 비교 |
| E02-A1 | 리포트가 동결 입력 집합을 자체 보존한다 | 첫 리포트 저장 레코드 |
| E02-A2 | 새 버전 발행 뒤 과거 리포트가 변하지 않는다 | 변경 전·후 첫 리포트 비교, 두 리포트의 버전 ID·가중치 |
| E02-A3 | 저장 입력으로 재계산한 총점이 저장 총점과 같다 | 독립 재계산 결과 |

### Required Evidence Set (초안)

EV4-01 시나리오·대상 스냅샷, EV4-02 lane·subject·fixture, EV4-03 인용 시험 입력과 대상 응답,
EV4-04 저장 레코드 전후, EV4-05 보고서 조회 3회(제거 전·후·복원 후), EV4-06 기준 변경 전·후 설정,
EV4-07 두 리포트와 동결 입력, EV4-08 재계산 규칙·입력·결과, EV4-09 복구·안전 상태, EV4-10 판정·manifest.

### Key Entities

- Report, ReportItem, AxisAssessment, Evidence, TranscriptSegment, CompetencyModelVersion, EvaluationCriterion
  (WhyYou 소유, 기준선 문서 참조). ControlProof: Run, lane/subject, 변경 주입 기록, 재계산 기록.

### Scope Boundaries

#### Included

E-01 우회 4종+기준 사례, E-01 근거 제거·복원, E-02 동결·보존·재계산, Spec 003 기반 봉인·복구·재시험.

#### Excluded and Deferred

사람 검토 기록의 점수 변경, 웹 화면 노출(Spec 005), 실제 AWS, N-01·N-03, 외부 AI 모델 품질,
문서 분석 결과 생성(격리 환경 한계, Spec 003 ID-003-18).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: E-01 Run의 E01-A1~A4와 E-02 Run의 E02-A1~A3이 전부 PASS/FAIL/INCONCLUSIVE 중 하나로 판정되고 사유
  코드가 있다.
- **SC-002**: 근거 제거·기준 변경은 Run 종료 전 복구되고 안전 상태가 확인된다. 미확인 시 차단된다.
- **SC-003**: E-01·E-02 각 Run은 540초, 봉인·검증까지 600초 안에 끝난다(Spec 003 시간 정책 재사용).
- **SC-004**: 봉인 bundle이 VERIFIED이고 모든 파일이 redaction 계약을 통과한다.
- **SC-005**: 최초 Run의 FAIL은 원인 분류(TARGET/RUNNER/RESTORE_OPERATOR) 뒤 child로만 재시험된다.
- **SC-006**: 팀원 PC에서 preflight와 시나리오별 Run 1건(E-01, E-02)이 재현되고 이식성 결함이 기록된다.

## Assumptions

- Spec 003의 실행기·seed·fixture·관찰·봉인 계약을 재사용한다. 고정 모델이 fixture turn 위에서 보고서를 만든다는
  사실은 Spec 003 T084 child로 확인됐다.
- WhyYou의 점수·인용·가중치 저장 구조는 기준선 문서의 소스 SHA 기준이며, 변경되면 기준선을 다시 만든다.

## Dependencies

- Spec 003 PR 병합(또는 그 브랜치 위에서 작업), WhyYou 통합 브랜치(T083·T082 포함) 결정.
- Clarify 1·2·4·6번 보성 답변(3·5번은 2026-10-07 코드로 닫힘).
- 1번에서 고정 모델 새 fixture(작업자 경로)를 택하면 WhyYou local/test 코드 변경 승인.

## Risks and Product Responses

- 점수 저장 HTTP 경로가 없어 "우회"를 deep probe로만 정의하면 제품 보호조치가 아닌 도메인 불변식을 시험하게 된다
  → Clarify §1에서 작업자 경로(고정 모델 출력 조작)를 포함할지 정한다.
- 근거 제거 수단이 삭제 요청이면 복원이 제품 흐름에 없을 수 있다 → fixture 수준 제거·복원과 제품 삭제 경로를
  분리해 기록한다.
