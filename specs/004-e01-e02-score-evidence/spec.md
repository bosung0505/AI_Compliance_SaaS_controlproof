# Feature Specification: E-01·E-02 점수 근거·평가 기준 보존 검증

**Feature Branch**: `yeonwoo/004-e01-e02-score-evidence`

**Created**: 2026-10-07

**Status**: Complete (2026-10-08) — Clarify·Plan·Tasks·Analyze·T001~T097·actual validation·converge 완료.
최초 E-01 FAIL 보존 후 승인된 수정 child PASS, 두 번째 clean checkout E-01/E-02 PASS/SUCCEEDED/VERIFIED.
FR-040/SC-001·006은 owner 승인 ID-004-36을 따른다. 다른 PC/AWS/main 통합은 별도이며 전체 MVP는 미완료다.

**Input**: V4 §10.10 E-01, §10.11 E-02, Decision Log D-013(Spec 004 범위), Spec 003 구현·actual 검증 기반,
[Spec 004 소스 기준선](../../docs/research/Spec004_E01_E02_WhyYou_Source_Baseline.md)

## Clarifications

근거 파일·줄은 [소스 기준선](../../docs/research/Spec004_E01_E02_WhyYou_Source_Baseline.md) §1에 있다.
기준선은 WhyYou `be81ebc`에서 만들었고, 현재 기준 브랜치 `bosung/controlproof-n02-integration`의 `eec8f70`은
`be81ebc`와 트리가 같다(병합 커밋, 파일 차이 0).

### Session 2026-10-07 — 코드로 닫힘

- Q3. **E-02 "기준 변경"의 수단** → 새 버전 생성·발행 뒤 두 번째 지원자를 초대·처리한다. 발행 버전의 제자리 수정은
  제품 경로에 없다(버전 쓰기 HTTP는 생성·발행뿐, 발행 버전은 frozen이고 `PublishedVersionImmutableError`). 버전
  상태는 `draft`·`published`·`retired`다. 초대는 발급 시점의 최신 발행 버전에 묶이므로 두 번째 지원자는 새 버전
  발행 뒤의 최신 발행 버전에 묶여야 한다. 저장소 직접 UPDATE로 발행 버전을 바꾸는 것은 주 시험에 넣지 않는다.
  영향: US3, Edge Cases, FR-031·032, E02-A2. (보성 승인으로 재확인)
- Q5. **판정 단위** → E-01과 E-02는 시나리오 ID·실행 프로필·YAML·Run을 각각 분리한다. Run 하나는
  `scenario_id`·`execution_profile`·스냅샷을 하나씩만 가지며 E-03 BEFORE/AFTER 선례를 따른다. seed·fixture·관찰·
  봉인 구현은 공유하되 판정·bundle·retest 계보는 시나리오별이다. 영향: FR-040·043, Assertion Contract,
  SC-001·003·006. (보성 승인으로 재확인)

### Session 2026-10-07 — 보성 승인

- Q1. **E-01 저장 경계** → 주 시험은 잘못된 인용을 내보내는 **새 고정 모델 fixture로 작업자 경로**를 돌리는 것이다.
  작업자의 실제 `verified_against`→`save_report` 경로가 네 종류의 잘못된 인용을 어떻게 저장하는지 판정한다.
  **저장소 직접 쓰기 deep probe는 보조**이며 "저장소에 들어간 잘못된 인용이 조회에서 어떻게 노출되는가"를 관찰한다.
  새 fixture는 WhyYou local/test 코드(`runtime/controlproof_model_substitute.py`) 변경이므로 Tasks에서 별도 WhyYou
  작업과 PR로 분리한다. WhyYou 제품 코드는 건드리지 않는다. 영향: US1, FR-010~013, E01-A1·A2, Dependencies.
- Q2. **근거 제거** → Run 소유 fixture **자막 구간 행을 직접 지웠다가 같은 값으로 다시 넣는다**. Evidence 행은 지우지
  않는다. 제품 삭제 요청(`/privacy/deletion-requests`)은 보고서까지 지우고 복원이 없으므로 범위 밖으로 기록한다.
  영향: US2, FR-020~022, Scope.
- Q4. **총점 재계산** → ControlProof가 WhyYou 계산 규칙(`scoring.aggregate`, `weights_for`, 의사소통 축 분리 설정)의
  **사본으로 독립 재계산**한다. 비교 대상은 (1) 저장된 `reports.overall_score`, (2) `scoring_inputs`의 분자·분모,
  (3) 조회 응답의 `overall_score`·`scoring_breakdown` 세 가지다. Python `round`의 짝수 반올림(0.5 → 짝수)까지
  사본에 맞춘다. WhyYou 함수를 호출해 판정하지 않는다. 영향: US3, FR-033·034, E02-A3.
- Q6. **격리 환경** → fixture turn 위에서 고정 모델이 만든 보고서를 E-01·E-02의 **실제 처리로 인정**한다. 입력
  turn·자산·자막 구간이 fixture라는 점과 외부 AI 차단을 한계로 증적과 결과에 표시한다. 영향: FR-003, US4, SC-007.
- **코드상 예측 P1의 처리** → 조회 경로가 자막 구간을 읽지 않아 근거를 지워도 조회 결과가 그대로라면 E01-A3는
  **대상 결함 FAIL**이다. 이 경우 Spec 003 T080~T084와 같은 순서(최초 Run 봉인 → 증거 → 원인 분류 → WhyYou 최소 수정
  결정 → child)로 처리하고, 최초 사실을 봉인하기 전에 WhyYou를 고치지 않는다. 영향: US5, FR-050~052.

## User Scenarios & Testing *(mandatory)*

### Feature Goal

AI가 산출한 점수가 (1) 유효한 답변 근거 없이는 저장·노출되지 않고, (2) 근거가 사라지면 정상 점수처럼
보이지 않으며, (3) 생성 당시의 점수 입력·가중치·버전을 자체 기록해 이후 기준 변경이 과거 리포트를
조용히 바꾸지 못함을, 실제 WhyYou 시험환경에서 원본 증적과 함께 판정한다. 판정은 ControlProof의 계약
완료와 WhyYou의 대상 동작을 분리해 기록한다(Spec 003의 구분 유지).

### 용어

- **점수 근거(Evidence)**: 보고서 항목의 축 점수가 인용하는 답변 turn·자막 구간·영상 구간 기록.
- **유효한 인용**: 같은 지원자, 같은 보고서 항목(기준)에 속하고 모델이 실제로 받은 Evidence ID.
- **근거 부족 상태**: 점수가 없거나 비워졌고 그 사유가 보존된 상태, 또는 조회 응답이 그 점수의 근거를 재생·확인할
  수 없다고 명시한 상태. 점수 숫자만 남은 상태가 아니다.
- **점수 입력 동결**: 리포트가 `scoring_inputs`, 기준별 `criterion_weight`, 축별 `axis_weights`,
  `competency_model_version_id`, 모델·프롬프트·설정 버전을 스스로 보존하는 것.
- **인용 모드 fixture**: 기준(criterion) 설명의 표식에 따라 고정 모델이 유효·빈·미존재·타 지원자·타 기준 인용을
  결정론적으로 내보내는 WhyYou local/test 대체 모델.

### User Story 1 - 유효하지 않은 인용으로 점수 저장을 시도한다 (Priority: P1)

E-01 우회. 인용 모드 fixture로 작업자가 실제 보고서를 만들게 해, 비어 있는 인용·존재하지 않는 Evidence ID·
다른 지원자의 Evidence ID·다른 기준의 Evidence ID를 담은 모델 출력이 작업자의 검증과 저장을 거쳐 어떻게 저장되는지
본다. 유효한 동일 지원자·동일 기준 인용의 기준 사례는 정상 저장돼야 한다. 보조로, 같은 네 종류의 잘못된 인용을
Run 소유 보고서 항목에 저장소 직접 쓰기로 넣고 조회에서 어떻게 노출되는지 관찰한다.

**Independent Test**: 다섯 종류의 모델 출력 각각에 대해 정규화 결과(작업자 저장 레코드)를 비교하고, 보조 probe의
조회 노출을 따로 기록한다.

**Acceptance Scenarios**:

1. 인용이 빈 점수 → 저장 레코드의 그 축은 점수 `null`·인용 없음이고 사유(비어 있지 않은 `rationale`)가 남는다.
2. 존재하지 않는 ID, 다른 지원자 ID, 다른 기준 ID → 각각 1과 같은 결과이며 잘못된 ID가 **그 기준의 보고서 항목**(축
   인용, 그 항목의 Evidence 행)에 남지 않는다. 다른 기준 ID는 같은 보고서의 다른 항목에, 다른 지원자 ID는 참조
   보고서에 원래 있는 행이므로 그 행의 존재는 위반이 아니다.
3. 유효한 인용 → 점수·인용·사유가 저장되고 인용 ID가 같은 항목의 Evidence 행이며 그 Evidence의 기준·버전 ID가
   항목과 일치한다.
4. 어느 경우에도 다른 지원자(참조 지원자)의 보고서·Evidence 행은 변하지 않는다.
5. 보조 probe의 조회 노출은 사실로 기록하되 E01-A1·A2 판정을 바꾸지 않는다(저장소 직접 쓰기는 제품 경로가 아님).

### User Story 2 - 저장 뒤 근거를 제거하고 노출을 확인한다 (Priority: P1)

E-01 변경 주입. 정상 저장된 점수가 인용한 Evidence의 자막 구간 행(Run 소유 fixture)을 직접 제거하고 보고서를
조회한다. 같은 행을 같은 값으로 다시 넣으면 조회 결과가 원래대로 돌아와야 한다. Evidence 행은 지우지 않는다.

**Acceptance Scenarios**:

1. 제거 뒤 조회: 해당 점수가 근거 부족 상태로 드러나고, 재생 불가능한 인용이 정상 인용처럼 표시되지 않는다.
2. 제거 전·후 조회 결과의 차이가 제거한 근거를 인용한 항목에만 한정된다.
3. 복원 뒤 조회가 제거 전과 같다(점수·인용·사유 동일).
4. Run 종료 시 제거·복원이 원상태로 끝났음이 안전 상태 확인(행 digest 일치)으로 증명된다.

### User Story 3 - 기준 변경 뒤 과거 리포트가 보존되는지 확인한다 (Priority: P1)

E-02. 첫 지원자를 현재 발행 버전으로 처리해 리포트와 동결 입력을 수집하고, 기준·가중치를 바꾼 새 버전을 제품 API로
생성·발행한 뒤 최신 발행 버전에 묶인 두 번째 지원자를 처리한다. 첫 지원자의 리포트를 다시 조회해 최초 결과·입력·
가중치·버전이 그대로인지, 저장된 입력으로 총점을 독립 재계산한 값이 저장값·조회값과 같은지 확인한다.

**Acceptance Scenarios**:

1. 첫 리포트는 `scoring_inputs`, 항목별 `criterion_weight`·`axis_weights`, `competency_model_version_id`,
   모델·프롬프트·설정 버전을 모두 가진다. `scoring_inputs`만 있고 실제 계산 가중치가 없으면 동결 미완.
2. 새 버전 발행 뒤 두 번째 리포트는 새 버전 ID와 새 가중치로 만들어지고, 첫 리포트는 옛 버전 ID를 계속 가리키며
   재조회 결과가 변경 전과 정규화 projection 단위로 같다(점수·입력·가중치·버전).
3. 저장된 입력만으로 독립 재계산한 총점·분자·분모가 저장 `overall_score`, `scoring_inputs`의 분자·분모, 조회 응답의
   `overall_score`·`scoring_breakdown`과 모두 같다.
4. 기준 변경 전·후 설정, 두 리포트, 재계산 규칙·입력·결과가 봉인된다.

### User Story 4 - 결과와 증적 한계를 검토한다 (Priority: P2)

Spec 003 US4와 같다. 인용 모드별 모델 출력·정규화·저장·조회 결과, 제거 전후 비교, 재계산 입력과 결과를 사람이 읽을
수 있게 제시하고, 격리 환경의 한계(fixture turn·자산·자막 구간 위의 보고서, 외부 AI 차단, 인용 모드 fixture가 실제
모델이 아님)를 함께 표시한다.

### User Story 5 - 최초 결과를 보존하고 수정 후 재시험한다 (Priority: P3)

Spec 003 US5와 같다. 최초 FAIL은 보존하고 원인 분류 뒤 parent-linked child로 재시험한다. 코드상 예측 P1이 실제로
관찰되면(E01-A3 FAIL) 다음 순서를 따른다: 최초 E-01 Run 봉인·verify → 제거가 실제로 일어났는지와 조회 결과를
증거로 원인 분류 → `TARGET_CONTROL_DEFECT`이면 WhyYou 최소 수정 범위를 결정 기록(PROPOSED → 승인) → WhyYou 개인
브랜치에서 실패 시험 먼저 → 수정 → child retest.

### Edge Cases

- 점수는 있으나 축이 "평가 불가"(`score=None`)인 항목은 인용 없음이 정상이다. 이를 근거 없는 점수로 오판하지 않는다.
- 같은 세션의 보고서는 하나다(작업자가 기존 보고서를 돌려주고 생성기는 `version=1`만 쓴다). 그래도 "첫 리포트"는
  Run이 만든 보고서 ID로 고정하고, 같은 세션에 두 번째 보고서 행이 생기면 그 자체를 관찰 사실로 기록한다.
- 근거 제거 대상 자막 구간은 Run 소유 lane의 행만 쓴다. 다른 lane·Run과 공유하는 행이 있으면 제거하지 않고 전제
  실패로 끝낸다.
- 기준 변경은 새 버전 발행으로만 가능하다. 첫 지원자의 보고서가 옛 버전 ID를 가리키는지로 판정한다. 발행 전 버전에
  묶인 지원자는 두 번째 지원자로 쓰지 않는다.
- 기준마다 같은 점수면 가중치를 바꿔도 총점이 같다. 그래서 E-02는 기준별 점수 표식(plan H-2)을 쓰고, 동결 여부는 총점만이
  아니라 가중치·정규화 가중치·분자·분모로도 판정한다.
- 다른 기준 Evidence ID 모드에서 앞 기준의 Evidence가 없으면 그 입력은 만들어지지 않은 것으로 보고 해당 사례를
  `INCONCLUSIVE`로 둔다.

## Requirements *(mandatory)*

### Functional Requirements

#### 시나리오·대상·준비 상태

- **FR-001**: E-01·E-02는 `LOCAL_EMULATED` 격리 WhyYou 대상에서만 실행하고, 외부 AI 차단·작업자 증명·소스 clean을
  Spec 003 preflight 계약 그대로 요구한다.
- **FR-002**: 모든 지원자·보고서·Evidence·역량 모델 버전은 Run 소유 합성 데이터이며, Run 종료 시 Run 소유 행만
  제거한다(ID-003-12 규칙 유지).
- **FR-003**: 보고서는 Run 소유 fixture(완료 세션·최종 turn·녹화 자산·자막 구간·질문 근거) 위에서 실제 WhyYou 작업자와
  고정 모델이 생성하며, 이것을 실제 처리로 인정한다. 입력이 fixture라는 점, 외부 AI 차단, 사용한 fixture ID·digest를
  증적과 결과에 표시한다.
- **FR-004**: 보고서 생성 전 subject는 제품 API로 `ai_assessment`를 포함한 동의를 커밋한다(T083 이후 동의 없는 보고서
  요청은 거부된다).

#### E-01 인용 검증

- **FR-010**: 실행기는 인용 모드 fixture를 사용하는 작업자 경로로 빈 인용, 미존재 ID, 다른 지원자 ID, 다른 기준 ID,
  유효 인용의 다섯 입력을 만든다. 모드는 Run 소유 기준의 표식으로 고르고, 고정 모델이 낸 원래 출력(인용 ID·점수)과
  작업자 저장 레코드를 모두 수집한다.
- **FR-011**: 판정은 작업자 저장 레코드로 한다. 잘못된 인용 모드의 축이 점수 `null`·인용 없음·비어 있지 않은
  `rationale`이면 PASS(그 사유가 WhyYou 고정 보류 문구와 같은지는 기록만 한다). 잘못된 ID가 그 기준 항목의 축 인용이나
  그 항목의 Evidence 행으로 남거나 점수가 남으면 FAIL. 모델 원래 출력이 의도한 모드와 다르면 실행기 결함으로
  `INCONCLUSIVE`.
- **FR-012**: 다른 지원자 ID 모드는 같은 Run의 참조 지원자 보고서가 만든 실제 Evidence ID를, 다른 기준 ID 모드는
  같은 보고서의 앞 기준에 제공된 실제 Evidence ID를 쓴다. 참조 지원자의 보고서·Evidence는 시험 전후로 바뀌지 않아야
  한다.
- **FR-013**: 보조 deep probe는 Run 소유 보고서 항목의 축에 네 종류의 잘못된 인용(빈 인용, 미존재·타 지원자·타 기준 ID)을
  저장소 직접 쓰기로 넣고 조회
  응답의 노출을 수집한다. 결과는 진단 관찰로 봉인하고 E01-A1·A2의 판정 근거로 쓰지 않는다. 쓰기 전 값으로 복구한다.

#### E-01 근거 제거·복원

- **FR-020**: 근거 제거는 유효 인용 항목이 인용한 Evidence의 자막 구간 행(Run 소유 fixture)을 직접 삭제하는 것이다.
  삭제 전 행 projection과 digest를 보존하고, 제거 전·후·복원 후 세 번의 회사 보고서 조회와 타임라인 조회를 같은
  경로로 수집한다. Evidence 행과 제품 삭제 요청 경로는 쓰지 않는다.
- **FR-021**: 제거 뒤 조회에서 해당 점수가 근거 부족 상태로 식별되지 않으면 FAIL. 근거를 인용하지 않은 다른 항목이
  변하면 FAIL.
- **FR-022**: 복원은 같은 행을 같은 값으로 다시 넣는 것이다. 복원 뒤 행 digest가 제거 전과 다르거나 복원·확인이 실패하면
  복구 안전 문제이므로 `RESTORE_FAILED`(verdict INCONCLUSIVE)로 처리하고 같은 대상의 후속 변경 주입을 차단한다. 행 digest는
  같은데 보고서 조회가 제거 전과 다르면 E01-A4 FAIL이다(Spec 003 ID-003-14의 복구 안전·assertion 분리).

#### E-02 동결·보존

- **FR-030**: 첫 지원자 리포트에서 동결 입력 집합(점수 입력, 기준별·축별 가중치, 버전 ID, 모델·프롬프트·설정
  버전)을 수집하고 누락 필드는 항목별로 기록한다.
- **FR-031**: 기준 변경은 제품 API로 새 버전을 생성·발행하는 것이다. 변경 전·후 버전 스냅샷(버전 ID, 번호, 상태,
  기준별 가중치, 축 가중치)을 수집하고, 두 번째 지원자는 발행 뒤의 최신 발행 버전에 묶는다. 새 버전은 Run 소유
  데이터로 teardown 대상이다.
- **FR-032**: 두 번째 지원자 처리 뒤 첫 리포트 재조회와 저장 레코드가 변경 전과 다르면 FAIL. 두 번째 리포트가
  새 버전 ID·가중치로 만들어지지 않았으면 해당 assertion은 대상 동작이 아니라 전제 실패이므로 사유 코드와 함께
  `INCONCLUSIVE`로 둔다.
- **FR-033**: ControlProof는 WhyYou 계산 규칙의 사본으로 저장된 항목 축 점수·가중치에서 기준 점수와 총점·분자·분모를
  독립 재계산한다. 저장 `overall_score`, `scoring_inputs`의 분자·분모, 조회 응답 `overall_score`·`scoring_breakdown`
  중 하나라도 재계산과 다르면 FAIL. 실수 비교는 계약에 고정한 허용 오차를 쓰고, 정수 점수는 정확히 같아야 한다.
- **FR-034**: 재계산 규칙 사본은 WhyYou 원본 파일의 경로와 blob SHA를 함께 기록한다. preflight에서 대상의 원본 blob
  SHA가 사본의 기준과 다르면 `RUNNER_NOT_READY`다. 사본·입력·결과를 봉인한다.

#### 판정·증적·복구

- **FR-040**: assertion(§E01/E02 Assertion Contract)별 PASS/FAIL/INCONCLUSIVE를 Spec 003과 같은 판정
  모델로 낸다. PASS·FAIL은 detail/expected/actual로 사유를 제시하고, INCONCLUSIVE에는 reason_code를 요구한다
  (ID-004-36, 제품 책임자 승인). 판정은 시나리오별 Run 단위다. E-01 Run의 전체 PASS는 E01-A1~A4, E-02 Run의 전체 PASS는
  E02-A1~A3이 모두 PASS일 때만.
- **FR-041**: 변경 주입(근거 제거, deep probe 쓰기, 기준 변경)은 Run 종료 전 원상 복구하거나 Run 소유 teardown으로
  제거하고 안전 상태를 확인한다. 미확인이면 `RESTORE_FAILED`와 차단.
- **FR-042**: 증적은 Spec 003 봉인·검증·redaction 계약을 따른다. 보고서 자유 텍스트(요약·관찰·사유)는 원문 대신
  SHA-256과 길이만 봉인한다.
- **FR-043**: E-01과 E-02는 시나리오 ID·실행 프로필·YAML·Run·bundle·retest 계보를 각각 따로 가진다. seed·fixture·
  관찰·봉인 구현은 공유할 수 있으나 한 Run의 결과가 다른 시나리오의 판정 근거가 되지 않는다.

#### 최초 결과·보완

- **FR-050**: 최초 E-01·E-02 Run의 FAIL·INCONCLUSIVE는 봉인 뒤 덮어쓰지 않는다. 원인은
  `TARGET_CONTROL_DEFECT`, `RUNNER_OR_OBSERVER_DEFECT`, `RESTORE_OPERATOR_DEFECT` 중 하나로 증거와 함께 분류한다.
- **FR-051**: E01-A3 FAIL이 대상 결함으로 분류되면 WhyYou 최소 수정 범위(조회 경로가 근거 부족을 드러내는 방식)를
  결정 기록으로 남기고 승인 뒤 개인 브랜치에서 실패 시험부터 구현한다. 최초 사실 봉인 전에는 수정하지 않는다.
- **FR-052**: 보완 뒤 검증은 같은 프로필의 parent-linked child Run으로만 한다. 부모 manifest는 변하지 않아야 한다.

### E01/E02 Assertion Contract

E01-A* 는 E-01 Run, E02-A* 는 E-02 Run에서만 판정한다.

| ID | 주장 | 판정 근거 |
|---|---|---|
| E01-A1 | 빈·미존재·타 지원자·타 기준 인용은 작업자 검증·저장에서 비워진다 | 네 모드의 모델 원래 출력, 저장 레코드, 참조 지원자 불변 |
| E01-A2 | 유효 인용은 정상 저장된다 | 유효 모드 항목의 저장 레코드와 Evidence 소유 ID |
| E01-A3 | 근거 제거 뒤 점수는 근거 부족으로 노출된다 | 제거 receipt, 제거 전·후 조회 비교 |
| E01-A4 | 근거 복원 뒤 조회가 원상 복구된다 | 복원 receipt·행 digest, 복원 후 조회와 제거 전 조회 비교 |
| E02-A1 | 리포트가 동결 입력 집합을 자체 보존한다 | 첫 리포트 저장 레코드 |
| E02-A2 | 새 버전 발행 뒤 과거 리포트가 변하지 않는다 | 변경 전·후 첫 리포트 비교, 두 리포트의 버전 ID·가중치 |
| E02-A3 | 저장 입력으로 재계산한 총점이 저장값·조회값과 같다 | 독립 재계산 결과와 계약의 다섯 비교 대상(ID-004-23) |

보조 deep probe(FR-013)는 assertion이 아니라 진단 관찰 `E01-D1`로 봉인한다.

### Required Evidence Set

EV4-01 시나리오·대상·고정 모델·재계산 규칙 원본 스냅샷, EV4-02 lane·subject·fixture, EV4-03 인용 모드 입력과
모델 원래 출력, EV4-04 저장 레코드 전후, EV4-05 보고서·타임라인 조회 3회(제거 전·후·복원 후), EV4-06 기준 변경 전·후
설정, EV4-07 두 리포트와 동결 입력, EV4-08 재계산 규칙·입력·결과, EV4-09 변경 주입·복구·안전 상태, EV4-10 판정·
manifest. 시나리오별 적용 집합은 Plan의 계약을 따른다.

### Key Entities

- Report, ReportItem, AxisAssessment, Evidence, TranscriptSegment, CompetencyModelVersion, EvaluationCriterion
  (WhyYou 소유, 기준선 문서 참조). ControlProof: Run, lane/subject, 인용 모드 사례, 변경 주입 기록, 재계산 기록.

### Scope Boundaries

#### Included

E-01 작업자 경로의 잘못된 인용 4종과 기준 사례, 보조 deep probe 노출 관찰, E-01 근거 제거·복원, E-02 동결·보존·
재계산, Spec 003 기반 봉인·복구·재시험, WhyYou local/test 인용 모드 fixture(별도 WhyYou 작업·PR).

#### Excluded and Deferred

사람 검토 기록의 점수 변경, 웹 화면 노출(Spec 005), 실제 AWS, N-01·N-03, 외부 AI 모델 품질,
문서 분석 결과 생성(격리 환경 한계, Spec 003 ID-003-18), 제품 삭제 요청 경로를 근거 제거 수단으로 쓰는 것(보고서까지
삭제되고 복원이 없음), 재전사(`TranscriptService.correct`)를 근거 교체 수단으로 쓰는 것(호출 경로 없음), 발행 버전의
저장소 직접 수정, 직무 요건 평가(`reports.requirement_assessments`)의 점수·인용(E-01 범위 밖: 0~100 축 점수가 아니라
상태와 파생 신뢰도이며 총점·`scoring_inputs`에 들어가지 않는다. 근거는 research R-015).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: E-01 Run의 E01-A1~A4와 E-02 Run의 E02-A1~A3이 전부 PASS/FAIL/INCONCLUSIVE 중 하나로 판정된다.
  PASS·FAIL은 detail/expected/actual로 사유를 제시하고 INCONCLUSIVE에는 reason_code가 있다(ID-004-36).
- **SC-002**: 근거 제거·deep probe 쓰기·기준 변경은 Run 종료 전 복구 또는 Run 소유 teardown으로 제거되고 안전 상태가
  확인된다. 미확인 시 차단된다.
- **SC-003**: E-01·E-02 각 Run은 540초, 봉인·검증까지 600초 안에 끝난다(Spec 003 시간 정책 재사용).
- **SC-004**: 봉인 bundle이 VERIFIED이고 모든 파일이 redaction 계약을 통과한다.
- **SC-005**: 최초 Run의 FAIL은 원인 분류(TARGET/RUNNER/RESTORE_OPERATOR) 뒤 child로만 재시험된다.
- **SC-006**: 두 번째 깨끗한 checkout 또는 팀원 PC에서 preflight와 시나리오별 Run 1건(E-01, E-02)이 재현되고
  이식성 결함이 기록된다(T097, ID-004-36). 같은 PC의 새 checkout 재현을 다른 PC 검증으로 표기하지 않는다.
- **SC-007**: 모든 E-01·E-02 결과는 fixture 입력·외부 AI 차단·사용한 고정 모델 fixture ID를 한계로 표시한다.

## Assumptions

- Spec 003의 실행기·seed·fixture·관찰·봉인 계약을 재사용한다. 고정 모델이 fixture turn 위에서 보고서를 만든다는
  사실은 Spec 003 T084 child로 확인됐다.
- WhyYou의 점수·인용·가중치 저장 구조는 기준선 문서의 소스 SHA 기준이며, 변경되면 기준선을 다시 만든다.

## Dependencies

- Spec 003 PR #1 병합 완료(ControlProof `003-n02-consent-order`), WhyYou 기준 `bosung/controlproof-n02-integration`
  `eec8f70`.
- 인용 모드 fixture를 담은 WhyYou local/test 변경: `eec8f70`에서 분기한 개인 브랜치와 PR(Tasks에서 별도 작업).

## Risks and Product Responses

- 점수 저장 HTTP 경로가 없어 "우회"를 deep probe로만 정의하면 도메인 불변식만 시험하게 된다 → 주 시험을 인용 모드
  fixture의 작업자 경로로 두고 deep probe는 진단 관찰로 분리했다.
- 인용 모드 fixture가 대상 쪽 시험 대체물이므로 fixture 결함이 대상 결함처럼 보일 수 있다 → 모델 원래 출력을 함께
  봉인하고 의도한 모드와 다르면 실행기 결함으로 분류한다.
- 근거 제거가 제품 흐름이 아닌 fixture 행 직접 삭제다 → 변경 주입으로 명시하고 복원·안전 상태 확인을 필수로 둔다.
