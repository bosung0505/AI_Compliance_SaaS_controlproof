# Feature Specification: N-02 동의·AI 처리 순서 검증

**Feature Branch**: `003-n02-consent-order`

**Created**: 2026-10-01

**Status**: Implemented and actually validated — parent Run `15cef078…` (INCONCLUSIVE, RESTORE_FAILED) and evidence-backed child `7b59237e…` (INCONCLUSIVE: A1~A4, A6 PASS; A5/A7 INCONCLUSIVE); PR review fixes implemented (ID-003-19), no new actual Run for those fixes; final converge pending

**Input**: WhyYou 지원자의 유효한 동의가 서버에 확정되기 전에 자료 분석, 면접 녹화 또는 AI 평가가
시작되지 않는지를 정상·우회·동의 저장 실패 조건에서 실행하고 증적으로 판정한다.

**Sources**:

- [2주 MVP 기능 범위 V4](../../docs/product/ControlProof_WhyYou_2주_MVP_기능범위_v4.md)
- [MVP Product Brief](../../docs/product/ControlProof_MVP_Product_Brief.md)
- [MVP 결정 기록 D-013·D-014](../../docs/product/ControlProof_MVP_Decision_Log.md)
- [MVP 시나리오 범위표](../../docs/product/ControlProof_MVP_Scenario_Coverage_Matrix.md)
- [Spec 003 N-02 WhyYou 소스 기준선](../../docs/research/Spec003_N02_WhyYou_Source_Baseline.md)
- [ControlProof Constitution](../../.specify/memory/constitution.md)

## Clarifications

### Session 2026-10-01

- Q: 동의 전에 실제 파일이 저장되지 않았더라도 자료 전송·저장을 가능하게 하는 권한이나 준비 상태가
  생성되면 N-02 보호 대상 효과로 보는가? → A: 그렇다. 지원자 자료를 받을 수 있는 권한·의도·준비
  상태의 생성부터 자료 분석 경로의 보호 대상 효과로 본다.
- Q: 자료 분석·녹화·AI 평가 우회, 정상 순서, 동의 저장 실패를 같은 합성 지원자에게 연속 수행하는가?
  → A: 각 우회 종류와 정상 흐름은 독립 subject lane을 사용하고, 저장 실패와 그 복구만 같은 subject를
  유지한다. 한 lane의 효과를 다른 lane의 기준선으로 재사용하지 않는다.
- Q: 특정 처리 단계에 독립적으로 직접 호출할 수 있는 진입 경로가 없으면 N-02 PASS가 불가능한가?
  → A: 독립 경로 부재를 capability 증적으로 고정하고 해당 처리 종류의 가장 이른 실재 경계를 시험하면
  PASS가 가능하다. 실재 경계는 있지만 실행·관찰하지 못하면 `RUNNER_NOT_READY`다.
- Q: N-02 PASS에 PC·모바일 화면에서 고지 문구가 실제로 보인다는 시각 증적도 필요한가? → A: 아니다.
  N-02는 정상 동의에 사용된 정책 식별값과 서버 확정 순서를 검증한다. viewport별 가시성은 N-01의
  `NOT_RUN` 범위로 유지한다.

## User Scenarios & Testing *(mandatory)*

### Feature Goal

검증 실행 담당자가 동의하지 않은 합성 지원자를 준비하고 WhyYou의 보호 대상 처리 경로를 정상 화면
순서와 직접 우회 순서로 시도한다. ControlProof는 서버에서 유효한 동의가 확정되기 전에 자료 분석,
녹화 또는 AI 평가와 관련된 요청·작업·결과가 만들어졌는지 관찰하고, 동의 저장 실패 때 부분 동의나
후속 처리가 남는지도 확인한다. 이후 장애를 해제하고 정상 동의와 처리를 수행해 순서가 복구되는지
검증한다.

이 기능의 성공은 WhyYou가 반드시 PASS하는 것을 뜻하지 않는다. 동의 전에 보호 대상 처리가 실제로
시작되면 근거 있는 FAIL을 생성하는 것이 ControlProof의 올바른 동작이다. 처음 확인한 FAIL은 봉인하고,
보완 후 결과는 새 child Run으로 연결한다.

### N-02에서 사용하는 동의 완료의 의미

N-02의 기준점은 지원자가 체크박스를 누르거나 화면이 다음 단계로 이동한 시점이 아니다. 다음 사실이
하나의 성공한 서버 처리로 확정된 시점을 **동의 완료**로 본다.

1. 합성 지원자와 해당 지원 건에 연결된 동의 사실이 내구성 있게 기록되었다.
2. 기록에는 지원자가 수락한 정책 버전, 정책 내용 식별값, 필수 처리 목적과 수락 시각이 있다.
3. 지원 건은 동의 완료를 나타내는 상태로 전이되었다.
4. 동의 저장 요청 전체가 성공했으며 실패한 요청의 일부 효과가 섞여 있지 않다.

동의 완료 알림의 비동기 전달 시각은 별도로 관찰한다. 그 전달이 늦었다는 사실만으로 N-02 FAIL을
만들지 않는다. 보호 대상 처리의 권한 판단이 내구성 있는 동의 사실을 직접 사용하고 처리 시작이 동의
완료보다 뒤라면, 비동기 알림 전달 전 처리가 시작됐더라도 N-02 순서 위반으로 보지 않는다.

### 보호 대상 처리의 의미

이 Spec은 WhyYou에 실제로 존재하는 다음 처리 종류를 구분해 검증한다.

- **자료 분석 경로**: AI 분석에 사용할 지원 자료의 전송·저장을 가능하게 하는 권한이나 준비 상태,
  자료를 받아들이는 행위, 분석 요청, 실제 분석 시작과 분석 결과 생성
- **녹화 경로**: 면접 또는 녹화 세션 시작, 녹화 자료 수신·확정과 녹화 결과 생성
- **AI 평가 경로**: 지원자 답변을 평가 대상으로 만드는 요청, 실제 평가 시작과 평가 결과 생성

각 경로에서 단순히 요청이 거부됐는지만 보지 않는다. 저장 객체, 작업 요청, 처리 시작 기록, 결과 또는
파생 데이터가 생기지 않았는지까지 확인한다. 실제 대상에 독립적인 직접 진입점이 없는 단계는 임의의
가짜 기능을 추가하지 않는다. 독립 경로가 없다는 capability 증적을 남기고 해당 처리 종류의 가장 이른
실재 경계를 시험한다. 실재 경계는 있지만 ControlProof가 실행·관찰하지 못하면 준비 완료로 보지 않는다.

### 시험 lane과 subject 격리

하나의 N-02 Run은 여러 합성 subject를 포함할 수 있다. 자료 분석 우회, 녹화 우회, AI 평가 우회와
정상 순서는 서로 독립된 subject lane을 사용한다. 동의 저장 실패 lane만 실패 조건 제거 뒤 같은
subject로 정상 동의를 다시 수행해 복구를 증명한다. 모든 관찰과 증적에는 lane과 subject가 연결되며,
한 lane에서 생긴 상태나 결과를 다른 lane의 기준선 또는 PASS 근거로 재사용하지 않는다.

실제 깊은 경계가 앞 단계 산출물을 요구하면 별도의 **심층 경계 probe lane**에 allowlist된 합성 전제
fixture를 둘 수 있다. 예를 들어 면접 세션 생성 경계에는 장비 점검과 전략, 평가 worker 경계에는 완료된
합성 면접 입력이 필요할 수 있다. 이 fixture는 실제 사용자 흐름이 만들었다고 주장하지 않고 capability
snapshot에 종류와 digest를 고정한다. fixture가 이미 가진 효과는 N02-A1의 무효 기준선이나 N02-A3·A4의
신규 효과로 세지 않으며, probe 호출 전후의 **증분 효과**만 해당 경계를 판정한다. 별도의 pristine
lane은 동의와 보호 대상 효과가 모두 없는 상태로 N02-A1을 계속 검증한다. 심층 fixture를 정상 순서나
다른 lane의 PASS 근거로 재사용할 수 없다.

동의 저장 실패 lane은 실패 직후 부분 효과 0건을 먼저 봉인한 뒤, 같은 subject에 recording/assessment
경계의 전제조건만 가진 임시 probe overlay를 각각 적용해 실제 경계를 시도할 수 있다. overlay의
기존 효과와 시도 뒤 증분 효과를 분리하고 각 시도 뒤 완전히 제거해야 한다. 정상 동의 복구는 overlay가
없고 미동의 안전 상태가 다시 확인된 뒤에만 시작한다.

### 성공과 대상 서비스 판정의 구분

- 기능 구현 성공: ControlProof가 실행 당시의 실제 동작과 증적에 맞는 판정을 만든다.
- N-02 `PASS`: 등록된 모든 필수 처리 경로에서 동의 전 보호와 정상 순서, 저장 실패 원자성 및 복구가
  확인된다.
- N-02 `FAIL`: 동의 완료 전 보호 대상 처리의 요청·시작·결과 또는 실패한 동의의 부분 효과가 하나라도
  직접 확인된다.
- N-02 `INCONCLUSIVE`: 직접 확인된 위반은 없지만 필수 경로나 순서·부작용을 증명할 수 없다.
- `NOT_RUN`: 실제 Run이 만들어지지 않았다.
- `RUNNER_NOT_READY`: 대상은 있으나 필수 경로를 실행·관찰·복구할 수 없어 Run을 시작할 수 없다.

### User Story 1 - 동의 전 보호 대상 처리를 우회 시도한다 (Priority: P1)

검증 실행 담당자는 본인 확인만 끝났고 동의는 완료하지 않은 합성 지원자를 준비한다. 정상 화면을
거치지 않고 등록된 자료 분석, 녹화, AI 평가 진입 경로를 각각 시도한다. ControlProof는 모든 시도가
거부되는지와 처리 부작용이 전혀 남지 않는지를 경로별로 판정한다.

**Why this priority**: 화면 버튼이 비활성화되어 있어도 서버나 비동기 처리 경로를 직접 호출할 수 있다면
동의 전 처리 방지 통제는 성립하지 않는다. N-02의 가장 직접적인 위험을 검증하는 흐름이다.

**Independent Test**: 격리된 환경에서 pristine 확인용 subject와 자료 분석·녹화·AI 평가 우회용
subject를 각각 독립 lane으로 만들고, 세 보호 대상 처리 경로를 해당 lane에서 한 번씩 시도한 뒤 처리
요청·시작·결과와 파생 데이터가 모두 0건인지 확인한다. 한 subject의 상태를 다른 경로의 기준선이나
PASS 근거로 재사용하지 않는다.

**Acceptance Scenarios**:

1. **Given** 본인 확인은 끝났지만 유효한 동의 사실이 없는 합성 지원자가 있을 때, **When** 자료 분석에
   사용할 자료의 전송·저장 권한 또는 수락 경로를 직접 시도하면, **Then** 요청은 동의가 필요하다는
   의미로 거부되고 전송·저장 준비 상태, 저장 객체·분석 요청·분석 시작·분석 결과는 생성되지 않는다.
2. **Given** 유효한 동의 사실이 없는 지원자가 있을 때, **When** 분석 요청 또는 실제 분석 시작 경로를
   직접 시도하면, **Then** 처리는 시작되지 않고 분석 작업·처리 receipt·결과가 생성되지 않는다.
3. **Given** 유효한 동의 사실이 없는 지원자가 있을 때, **When** 면접·녹화 시작 또는 녹화 자료 수신
   경로를 직접 시도하면, **Then** 녹화 처리는 시작되지 않고 확정된 녹화 자료나 파생 결과가 생성되지
   않는다.
4. **Given** 유효한 동의 사실이 없는 지원자가 있을 때, **When** AI 평가 요청 또는 평가 시작 경로를
   직접 시도하면, **Then** 평가는 시작되지 않고 평가 작업·결과·점수가 생성되지 않는다.
5. **Given** 어떤 직접 시도가 겉으로는 거부되었을 때, **When** ControlProof가 사후 상태를 비교하면,
   **Then** 지원 건 상태, 동의 사실, 처리 작업과 결과에 부분 변경이 없어야 한다.
6. **Given** 동의 완료 전에 보호 대상 처리의 요청·시작·결과 중 하나가 직접 관찰되었을 때, **When**
   N-02를 판정하면, **Then** 해당 경로 assertion과 전체 결과는 `FAIL`이며 기대·관찰·증적이 연결된다.

---

### User Story 2 - 정상 동의 뒤 처리 순서를 증명한다 (Priority: P1)

검증 실행 담당자는 정상 흐름의 합성 지원자가 서버 제공 정책을 수신해 확인하고 모든 필수 목적에
동의하게 한다. 동의가 확정된 뒤 자료 분석, 녹화와 AI 평가를 수행하고, 각 요청과 실제 시작이 동의 완료
이후였음을 하나의 사건 계보로 확인한다.

**Why this priority**: 동의 전 거부만 확인하면 보호조치가 정상 사용자를 영구히 막는 구현도 통과할 수
있다. 동의 이후 정상 한 바퀴가 열리고 그 순서를 설명할 수 있어야 한다.

**Independent Test**: 새 합성 지원자에게 정상 동의를 완료한 뒤 보호 대상 처리 흐름을 실행한다. 정책
식별값, 동의 확정과 처리 요청·시작 사건의 선후 관계 및 정상 결과를 연결하면 독립적으로 시험할 수 있다.

**Acceptance Scenarios**:

1. **Given** 서버가 제공한 현재 동의 정책을 지원자 흐름이 수신했을 때, **When** 지원자가 모든 필수
   목적에 동의하면, **Then** 확정된 동의 사실의 정책 버전·내용 식별값·목적은 수신하고 수락한 정책과
   일치한다. PC·모바일에서의 시각적 가시성은 이 assertion의 조건이 아니다.
2. **Given** 동의가 성공적으로 확정되었을 때, **When** 자료 분석을 요청하고 실제 처리를 시작하면,
   **Then** `동의 완료 < 분석 요청 ≤ 분석 시작`의 인과 순서를 증명할 수 있다.
3. **Given** 동의가 성공적으로 확정되었을 때, **When** 녹화를 시작하고 녹화 자료를 확정하면,
   **Then** 동의 완료가 녹화 시작과 자료 생성보다 앞선다는 것을 증명할 수 있다.
4. **Given** 동의가 성공적으로 확정되었을 때, **When** AI 평가를 요청하고 실제 평가를 시작하면,
   **Then** 동의 완료가 평가 요청·시작·결과보다 앞선다는 것을 증명할 수 있다.
5. **Given** 서로 다른 관찰 출처의 시각 정밀도가 낮아 두 사건 시각이 같아 보일 때, **When** 별도의
   순서 또는 인과 식별 정보로 선후를 증명할 수 없으면, **Then** ControlProof는 PASS가 아니라
   `INCONCLUSIVE: INSUFFICIENT_EVIDENCE`를 표시한다.
6. **Given** 동의 완료 알림 전달이 지연되었지만 내구성 있는 동의 사실이 먼저 확정되고 보호 대상
   처리가 그 뒤 시작되었을 때, **When** N-02를 판정하면, **Then** 알림 지연만을 이유로 FAIL을 만들지
   않고 실제 선후 관계와 전달 지연을 함께 표시한다.

---

### User Story 3 - 동의 저장 실패의 부분 효과와 복구를 검증한다 (Priority: P1)

검증 실행 담당자는 동의 확정 도중 한 번의 저장 실패를 발생시킨다. ControlProof는 화면 응답뿐 아니라
동의 사실, 지원 건 상태, 동의 완료 사건과 후속 처리 가능 여부를 확인한다. 실패 조건을 해제한 뒤 정상
동의와 보호 대상 처리까지 다시 수행해 환경이 복구되었음을 증명한다.

**Why this priority**: UI가 실패를 보여도 동의 레코드나 상태 중 일부가 남으면 후속 처리가 동의 없이
열릴 수 있다. 장애 상황이 N-02 통제를 우회하는지 확인하는 대표 능동 검증이다.

**Independent Test**: 동의가 확정되기 전의 안전한 한 지점에서 실패 조건을 적용하고, 요청 실패 뒤
동의 관련 효과와 보호 대상 처리 효과가 0건인지 확인한다. 실패 조건을 제거한 뒤 같은 시험 목적의 정상
흐름이 한 번만 완료되는지 확인한다.

**Acceptance Scenarios**:

1. **Given** 동의하지 않은 합성 지원자와 격리된 시험환경이 있을 때, **When** 동의 확정 중 저장 실패가
   발생하면, **Then** 사용자에게 동의 성공으로 표시되지 않고 유효한 동의 사실·동의 완료 상태·완료
   사건 중 어느 것도 부분적으로 남지 않는다.
2. **Given** 동의 저장 요청이 실패했을 때, **When** 자료 분석·녹화·AI 평가 경로를 다시 시도하면,
   **Then** 모두 미동의 상태와 동일하게 차단되고 보호 대상 처리 효과가 생성되지 않는다.
3. **Given** 실패 조건이 적용되었거나 실행이 중단되었을 때, **When** Run이 종료 단계로 진입하면,
   **Then** 실패 조건 제거와 대상 안전 상태 확인을 반드시 시도한다.
4. **Given** 실패 조건이 제거되고 미동의 안전 상태가 확인되었을 때, **When** 정상 동의를 다시
   수행하면, **Then** 유효한 동의 사실과 상태 전이·완료 사건은 논리적으로 각각 한 세트만 생성된다.
5. **Given** 복구 뒤 정상 동의가 완료되었을 때, **When** 보호 대상 처리를 시작하면, **Then** 정상 순서
   assertion을 만족하고 이전 실패 요청의 일부 효과와 섞이지 않는다.
6. **Given** 실패 조건 제거 또는 안전 상태 확인에 실패했을 때, **When** Run을 종료하면, **Then** 실행
   상태는 `RESTORE_FAILED`, 표시 결과는 `INCONCLUSIVE`가 되고 수동 확인 전 같은 대상의 후속 장애
   실행을 차단한다.

---

### User Story 4 - 경로별 결과와 증적 한계를 검토한다 (Priority: P2)

검증 책임자는 완료된 N-02 Run에서 어떤 처리 경로를 어떻게 시도했는지, 무엇이 거부 또는 허용됐는지,
동의 완료와 처리 요청·시작의 순서가 무엇인지, 어떤 부작용과 복구 상태를 관찰했는지 확인한다.

**Why this priority**: 단일 PASS 문구만으로는 실제로 녹화·평가 경로까지 시험했는지, 단지 화면 버튼만
확인했는지 구분할 수 없다. 결과가 제품 보호조치 개선과 향후 증적 문서에 쓰이려면 경로별 근거와
미검증 범위가 필요하다.

**Independent Test**: PASS, 동의 전 처리 FAIL, 필수 경로 증적 누락, 사건 순서 충돌, 복구 실패
fixture를 각각 판정해 예상 결과·사유·증적 연결과 미검증 범위가 표시되는지 확인한다.

**Acceptance Scenarios**:

1. **Given** 모든 필수 경로의 동의 전 차단, 정상 순서, 저장 실패 원자성과 복구가 증명되었을 때,
   **When** 결과를 검토하면, **Then** N-02는 `PASS`이고 각 assertion에 기대·관찰·증적이 연결된다.
2. **Given** 한 경로에서 동의 전 처리 효과가 직접 확인되었을 때, **When** 결과를 검토하면, **Then**
   N-02는 `FAIL`이고 다른 미관찰 경로가 그 실패를 숨기지 않는다.
3. **Given** 직접 확인된 위반은 없지만 필수 경로의 요청 또는 부작용을 관찰하지 못했을 때, **When**
   결과를 검토하면, **Then** N-02는 `INCONCLUSIVE: INSUFFICIENT_EVIDENCE`다.
4. **Given** 같은 사건의 순서를 나타내야 하는 독립 증적이 서로 모순될 때, **When** 결과를 검토하면,
   **Then** 관련 assertion은 평가 불가이고 다른 직접 실패가 없다면 전체 결과는
   `INCONCLUSIVE: EVIDENCE_CONFLICT`다.
5. **Given** 실제 Run을 시작하기 전에 필수 경로 하나를 실행·관찰·복구할 수 없음이 확인되었을 때,
   **When** 준비 상태를 검토하면, **Then** `RUNNER_NOT_READY`로 표시하고 Run을 만들지 않는다.
6. **Given** 결과가 생성되었을 때, **When** 검증 책임자가 설명을 확인하면, **Then** 로컬에서 실행한
   N-02 한 건의 범위와 실제 AWS·운영환경·법적 준수 전체를 검증하지 않았다는 한계를 구분할 수 있다.
7. **Given** 한 처리 단계에 독립 직접 경로가 없지만 그 부재와 가장 이른 실재 경계가 확인되었을 때,
   **When** 결과를 검토하면, **Then** 독립 경로를 실행한 것처럼 표시하지 않고 부재 근거·대체한 실재
   경계·검증 한계를 함께 보여준다.

---

### User Story 5 - 최초 결과를 보존하고 수정 후 재시험한다 (Priority: P3)

첫 actual Run이 N-02 보호조치 결함을 찾으면 팀은 원본 Run을 봉인한 뒤 확인된 결함만 보완한다. 검증
실행 담당자는 새 Run으로 같은 의도를 재시험하고 수정 전·후 대상 버전과 결과 차이를 확인한다.

**Why this priority**: ControlProof의 가치는 실패를 숨기지 않고 개선을 증명하는 데 있다. 다만 첫 Run이
이미 PASS이면 데모를 위해 결함을 만들 필요는 없다.

**Independent Test**: 완료된 부모 Run으로 재시험을 만들고, 부모 bundle이 변하지 않으며 새 Run이
부모·대상 버전·결과 차이를 기록하는지 확인한다.

**Acceptance Scenarios**:

1. **Given** 완료된 N-02 Run이 있을 때, **When** 재시험을 시작하면, **Then** 새 Run이 생성되고 부모
   Run을 참조한다.
2. **Given** 최초 Run이 FAIL이고 제품을 보완했을 때, **When** child Run을 실행하면, **Then** 부모의
   판정·증적·무결성 식별값은 바뀌지 않고 두 대상 버전과 assertion 차이를 확인할 수 있다.
3. **Given** 최초 Run이 이미 PASS였을 때, **When** 완료 여부를 검토하면, **Then** 인위적인 결함을
   추가하지 않고 실제 PASS와 한계를 그대로 보존한다.

### Edge Cases

- 합성 지원자가 과거 동의 사실이나 동의 완료 상태를 이미 가지고 있으면 미동의 기준선이 아니므로
  장애나 우회 시도 전에 실행을 중단한다.
- 화면에는 동의 성공이 표시됐지만 서버에 유효한 동의 사실이 없으면 정상 동의가 아니며, 후속 처리가
  열리면 FAIL이다.
- 서버에는 동의 사실이 있지만 지원 건 상태가 동의 완료가 아니거나 그 반대인 부분 상태는 동의 완료로
  인정하지 않는다.
- 실패한 동의 요청 뒤 비동기 완료 사건만 남아도 부분 효과이며 FAIL이다.
- 동의 요청이 시간 초과됐지만 서버 처리 결과를 확인할 수 없으면 성공이나 실패로 추정하지 않고
  `INCONCLUSIVE`로 처리한다.
- 동의 전 요청이 거부됐지만 작업이 비동기로 이미 시작되거나 결과가 나중에 생기면 FAIL이다.
- 자료 업로드는 거부됐지만 자료 전송·저장을 가능하게 하는 권한, 의도 또는 준비 상태가 먼저
  만들어졌다면 보호 대상 효과로 보존하고 FAIL로 판정한다.
- 면접 세션만 생성되고 녹화가 시작되지 않은 경우, 세션 생성이 녹화 처리의 필수 시작 경계인지 대상
  capability 정의에 따라 판정하고 결과에 경계를 명시한다.
- AI 평가가 분석 또는 reporting과 결합되어 독립 직접 경로가 없으면 실재하는 최초 요청·시작 경계를
  사용하고 독립 직접 경로가 없다는 한계를 표시한다.
- 동의 완료와 처리 시작 시각이 같아 보이면 인과 순서 증적이 없는 한 PASS로 추정하지 않는다.
- 시스템 시계가 서로 어긋난 경우 timestamp만으로 선후를 판정하지 않고 사건 순서·상관관계 증적을
  요구한다.
- 비동기 동의 완료 알림이 늦거나 재전달돼도 동의 사실과 완료 사건이 논리적으로 중복 저장되지 않으면
  N-02 순서 위반으로 보지 않는다. 중복·누락은 발견사항으로 보존한다.
- 보호 대상 처리 경로 하나가 대상 버전에 존재하지만 실행기만 준비되지 않았으면 `NO_TEST_TARGET`가
  아니라 `RUNNER_NOT_READY`다.
- 증적 수집이나 무결성 식별값 생성이 실패하면 해당 필수 assertion을 PASS로 만들지 않는다.
- 중단 또는 취소 뒤에도 적용한 실패 조건을 제거하고 안전 상태를 확인해야 한다.
- 동시에 실행된 다른 Run의 consent나 처리 사건이 현재 subject에 연결되면 상관관계 오류로 처리하고
  PASS를 만들지 않는다.

## Requirements *(mandatory)*

### Functional Requirements

#### 시나리오·대상·준비 상태

- **FR-001**: ControlProof는 N-02의 목적, 전제조건, 보호 대상 처리 종류, 단계, assertion, 필수 증적,
  복구 조건을 버전이 있는 시나리오 정의로 관리해야 한다.
- **FR-002**: 과거 Run은 실행 당시의 N-02 정의와 대상 버전으로 해석할 수 있어야 하며 이후 정의 변경이
  과거 의미를 바꾸어서는 안 된다.
- **FR-003**: 실제 Run 전에 WhyYou 대상 버전에서 자료 분석·녹화·AI 평가의 실재 진입 경계, 독립 직접
  경로의 존재·부재와 관찰 가능한 효과를 capability로 고정해야 한다. 독립 경로가 없으면 해당 처리
  종류의 가장 이른 실재 경계를 식별해야 한다.
- **FR-004**: 필수 경로가 대상에 존재하지만 실행·관찰·복구 수단 중 하나가 준비되지 않으면 준비 상태는
  `RUNNER_NOT_READY`여야 하며 Run을 시작해서는 안 된다.
- **FR-005**: 접근 권한 때문에 필수 경로 또는 증적을 사용할 수 없으면 준비 상태는 `ACCESS_BLOCKED`여야
  하며 필요한 조치를 설명해야 한다.
- **FR-006**: 대상 버전, 실행환경 종류, 시나리오 버전, 정책 식별값, 사용한 capability와 미검증 환경을
  Run 시작 전에 고정해야 한다.

#### 동의 기준선과 완료 사실

- **FR-007**: 각 우회 종류와 정상 순서는 서로 독립된 합성 subject lane을 사용해야 한다. pristine
  기준선 lane은 본인 확인까지만 완료되고 유효한 동의 사실·동의 완료 상태·보호 대상 처리 효과가 없어야
  한다. 실제 깊은 경계가 앞 단계 산출물을 요구하는 probe lane은 capability에 고정된 allowlist fixture를
  가질 수 있으나, fixture 효과와 probe 뒤 증분 효과를 분리하고 다른 lane의 PASS 근거로 재사용해서는
  안 된다. 저장 실패 lane의 같은 subject에 임시 심층 probe overlay를 사용할 때도 실패 직후 0건 확인
  뒤에 적용하고 복구 동의 전에 제거·안전 상태를 확인해야 한다. 저장 실패와 복구 단계만 같은 subject를
  유지한다.
- **FR-008**: 기준선이 미동의 전제와 다르면 보호 대상 처리를 시도하지 않고 Run을 안전하게 종료해야 한다.
- **FR-009**: 정상 동의에는 지원자·지원 건, 정책 버전, 정책 내용 식별값, 수락한 필수 목적과 수락 시각이
  연결되어야 한다.
- **FR-010**: 동의 완료는 동의 사실과 지원 건의 동의 완료 상태가 성공한 하나의 서버 처리로 내구성
  있게 확정된 시점이어야 한다.
- **FR-011**: 화면 체크, 클라이언트 상태 전환 또는 성공 문구만으로 동의 완료를 추정해서는 안 된다.
- **FR-012**: 비동기 동의 완료 알림의 생성·전달은 별도 사건으로 관찰해야 하며 전달 지연만으로 N-02
  FAIL을 만들어서는 안 된다.

#### 동의 전 우회와 부작용

- **FR-013**: ControlProof는 정상 화면 순서를 사용하지 않고 등록된 각 보호 대상 처리 경로를 해당
  독립 미동의 subject로 시도할 수 있어야 한다. 독립 직접 경로가 존재하지 않으면 부재를 증명하고 가장
  이른 실재 경계를 시도해야 한다.
- **FR-014**: 각 우회 시도는 호출 결과뿐 아니라 시도 전·후의 지원 건 상태, 동의 사실, 저장 효과,
  작업 요청, 처리 시작, 결과와 파생 데이터 차이를 관찰해야 한다.
- **FR-015**: 자료 분석 경로는 최소한 자료 전송·저장을 가능하게 하는 권한 또는 준비 상태, 자료 수락·
  저장 효과, 분석 요청, 실제 분석 시작과 결과 생성 여부를 구분해 관찰해야 한다.
- **FR-016**: 녹화 경로는 최소한 면접·녹화 시작, 녹화 자료 수신·확정과 녹화 파생 결과 생성 여부를
  구분해 관찰해야 한다.
- **FR-017**: AI 평가 경로는 최소한 평가 요청, 실제 평가 시작과 결과 또는 점수 생성 여부를 구분해
  관찰해야 한다.
- **FR-018**: 동의 완료 전 보호 대상 처리의 요청·시작·결과 또는 시나리오가 금지한 저장 효과가 하나라도
  직접 확인되면 해당 assertion은 `FAIL`이어야 한다.
- **FR-019**: 요청 거부가 관찰되더라도 사후 부작용을 확인할 수 없으면 그 경로를 PASS로 판정해서는 안 된다.

#### 정상 순서

- **FR-020**: 정상 흐름은 지원자 흐름이 수신하고 수락한 정책과 실제 확정된 동의의 정책 버전·내용
  식별값·필수 목적이 일치함을 확인해야 한다. PC·모바일 viewport 가시성은 N-02 PASS 조건이 아니다.
- **FR-021**: 자료 분석에 대해 `동의 완료 < 처리 요청 ≤ 실제 처리 시작 ≤ 결과 생성`의 적용 가능한
  부분 순서를 증명해야 한다.
- **FR-022**: 녹화에 대해 동의 완료가 면접·녹화 시작과 녹화 자료 확정보다 앞섰음을 증명해야 한다.
- **FR-023**: AI 평가에 대해 동의 완료가 평가 요청·실제 시작·결과 생성보다 앞섰음을 증명해야 한다.
- **FR-024**: timestamp만으로 순서를 판별할 수 없으면 상관관계가 있는 사건 순서 또는 인과 식별 정보를
  사용해야 하며 둘 다 없으면 `INCONCLUSIVE: INSUFFICIENT_EVIDENCE`여야 한다.
- **FR-025**: 정상 동의 뒤 필수 처리 경로가 모두 영구 차단되는 구현은 N-02 PASS로 판정해서는 안 된다.

#### 저장 실패·복구·재시험

- **FR-026**: 동의 확정 중 저장 실패 조건은 격리된 시험환경과 현재 Run·subject에만 적용되어야 한다.
- **FR-027**: 실패 조건이 실제 동의 확정 경계에 도달했다는 사실을 독립 증적으로 확인해야 하며 주입
  명령 성공만으로 장애가 발동했다고 추정해서는 안 된다.
- **FR-028**: 실패한 동의 요청 뒤 유효한 동의 사실, 동의 완료 상태와 완료 사건은 모두 없어야 한다.
- **FR-029**: 실패한 동의 요청 뒤 각 보호 대상 처리 경로는 미동의 기준선과 동일하게 차단되어야 한다.
- **FR-030**: 실패 조건을 적용한 Run은 정상 종료·실패·취소와 관계없이 조건 제거와 안전 상태 확인을
  반드시 시도해야 한다.
- **FR-031**: 복구 성공 뒤 정상 동의의 논리적 효과와 완료 사건은 각각 한 세트만 있어야 하며 실패
  요청의 부분 효과와 연결되어서는 안 된다.
- **FR-032**: 복구 실패 시 Run을 `RESTORE_FAILED`와 `INCONCLUSIVE`로 표시하고 수동 정리 확인 전 같은
  대상의 후속 장애 실행을 차단해야 한다.
- **FR-033**: 재시험은 새 Run으로 생성하고 부모 Run을 참조해야 하며 부모 판정·증적·무결성 식별값을
  수정해서는 안 된다.

#### 판정·증적·설명

- **FR-034**: N-02는 경로별 필수 assertion을 독립 평가하고 그 결과로 전체 verdict를 계산해야 한다.
- **FR-035**: 하나 이상의 직접 위반이 있으면 다른 증적 누락이 있어도 전체 FAIL을 숨겨서는 안 되며,
  미평가 assertion도 함께 표시해야 한다.
- **FR-036**: 직접 위반이 없고 필수 증적이 부족하면 `INCONCLUSIVE: INSUFFICIENT_EVIDENCE`, 같은 사실의
  증적이 모순되면 `INCONCLUSIVE: EVIDENCE_CONFLICT`를 사용해야 한다.
- **FR-037**: 모든 관찰과 증적은 Run, subject, 실행 구간, 단계, 시도, 수집 시각과 출처에 연결되어야 한다.
- **FR-038**: 판정에 사용한 최소 원본은 비밀값과 개인정보를 제거한 뒤 저장하고 원본 위치·조회 조건,
  내용 유형, 크기와 SHA-256을 기록해야 한다.
- **FR-039**: 전체 로그 또는 전체 데이터 저장소 덤프를 수집해서는 안 되며 실제 지원자·운영 credential을
  시험이나 증적에 사용해서는 안 된다.
- **FR-040**: 결과는 경로별 기대·관찰·사용 증적, 실제 순서, 실패 조건·복구 상태, 미검증 경로와 환경을
  비개발자가 구분할 수 있는 설명으로 제공해야 한다.
- **FR-041**: `LOCAL_EMULATED` 결과를 실제 AWS 또는 운영환경 결과로 표현하거나 법적 준수 전체를
  보증해서는 안 된다.

### N-02 Assertion Contract

#### Post-T078 evidence provenance clarification (2026-10-02)

The sealed initial Run `15cef078-ee24-4f0e-91ef-381e0f7a1cc2` is immutable. A
ControlProof-inserted `report.generation_requested` outbox row is the assessment
probe input, not by itself a WhyYou acceptance, processing start or result. A4/A6
direct effects require a separately observed target boundary/start/result or a
target-created durable effect. Mere worker handler entry before an authorization
decision does not establish assessment start. If the target outcome is unavailable,
the corrected evidence contract yields `INCONCLUSIVE`, preserving the parent
verdict as a historical result with its documented runner provenance defect.

For A5/A6, preserve a bounded, allowlisted reason code for a rejected consent
HTTP response; do not seal raw response bodies, credentials or personal data.
For A7, record condition removal, safe-state check and normal retry separately
while retaining the existing `RESTORE_FAILED` precedence and persistent block
until independently confirmed safe. Any later Run uses a new Run ID and links
the original parent; a changed evidence interpretation must be visible in that
lineage rather than applied retrospectively to the parent.

| Assertion ID | 반드시 확인할 질문 | PASS 조건 | 직접 FAIL 조건 |
|---|---|---|---|
| N02-A1 | pristine 미동의 기준선이 맞는가 | 동의 사실·완료 상태·보호 대상 효과가 모두 없음 | pristine lane에 이미 동의 또는 처리 효과가 있으면 Run 전제 실패로 종료 |
| N02-A2 | 동의 전 자료 분석 경로가 닫혀 있는가 | 요청 거부와 전송·저장 권한·준비·저장·요청·시작·결과 효과 0건 | 금지된 효과 하나 이상 생성 |
| N02-A3 | 동의 전 녹화 경로가 닫혀 있는가 | 시작·수신 거부와 녹화·파생 효과 0건 | 녹화 시작·자료·파생 효과 하나 이상 생성 |
| N02-A4 | 동의 전 AI 평가 경로가 닫혀 있는가 | 요청 거부와 평가 작업·결과·점수 0건 | 평가 요청·시작·결과 하나 이상 생성 |
| N02-A5 | 정상 동의와 처리의 순서가 맞는가 | 정책 식별 일치와 모든 적용 경로에서 동의 완료가 요청·시작보다 앞섬 | 처리 요청·시작·결과가 동의 완료보다 먼저 발생 |
| N02-A6 | 동의 저장 실패가 원자적인가 | 실패 뒤 동의 사실·상태·완료 사건과 처리 효과 0건 | 부분 동의 또는 보호 대상 처리 효과 생성 |
| N02-A7 | 실패 조건이 제거되고 정상 복구되는가 | 안전 상태 확인 뒤 정상 효과 한 세트와 올바른 처리 순서 | 조건 잔존, 부분 효과 혼입, 중복 효과 또는 복구 후 순서 위반 |

N02-A1의 기준선 불일치는 대상 보호조치의 FAIL이 아니라 유효한 시험을 만들지 못한 것이다. 장애 또는
우회 시도 전에 발견되면 Run은 보호조치 PASS/FAIL을 주장하지 않는다. N02-A2~A7의 직접 위반은 N-02
FAIL 근거다.

### Required Evidence Set

| Evidence ID | 내용 | 최소 연결 정보 | 주요 assertion |
|---|---|---|---|
| EV3-01 | 대상 버전·실행환경·정책·보호 대상 경로와 독립 직접 경로 존재·부재 capability snapshot | Run, target, source version, scenario version, environment, capture time | readiness, 전체 |
| EV3-02 | 지원자 흐름의 정책 수신값과 정상 동의 확정 사실 | subject, policy version, content identifier, purposes, accepted time, consent completion | N02-A5 |
| EV3-03 | 미동의 기준선과 각 경로 시도 전 상태 | subject, `BASELINE`, consent/state/effect counts | N02-A1~A4 |
| EV3-04 | 경로별 우회 요청과 직접 응답 | subject, path, step, attempt, request correlation, sanitized response | N02-A2~A4 |
| EV3-05 | 각 우회 뒤 저장·작업·시작·결과·파생 효과 snapshot | subject, path, `INJECTED`, correlation, effect counts | N02-A2~A4 |
| EV3-06 | 정상 동의 완료부터 처리 요청·시작·결과까지 사건 계보 | subject, event identity, causal order and times | N02-A5 |
| EV3-07 | 동의 저장 실패 적용과 실제 경계 발동 사실 | Run, subject, failure condition, trigger receipt | N02-A6 |
| EV3-08 | 실패 직후 동의·상태·완료 사건·처리 효과 snapshot | subject, failed request correlation, effect counts | N02-A6 |
| EV3-09 | 조건 제거, 안전 상태, 정상 재시도와 중복 여부 | subject, `RECOVERED`, logical effect identity/counts | N02-A7 |
| EV3-10 | assertion 결과, 증적 참조와 봉인 manifest | Run, assertion IDs, artifact hashes, parent Run | 전체, 재시험 |

한 artifact가 여러 Evidence ID의 최소 사실을 함께 담을 수 있지만, 각 assertion에서 어떤 사실을
사용했는지 역추적할 수 있어야 한다.

### Key Entities

- **N-02 Scenario Version**: 실행 당시의 보호 대상 경로, 단계, assertion, 필수 증적과 복구 조건을
  고정한 정의다.
- **Consent Policy Snapshot**: 지원자 흐름이 수신한 정책 버전, 내용 식별값, 필수 목적과 보존 관련 정보를
  나타낸다.
- **Consent Fact**: 특정 지원자와 지원 건이 특정 정책·목적에 동의했다는 확정 사실과 수락 시각이다.
- **Protected Processing Path**: 자료 분석, 녹화 또는 AI 평가에서 시험할 실재 진입 경계와 관찰 가능한
  효과의 집합이다.
- **Lifecycle Event**: 동의 완료, 처리 요청, 실제 시작, 결과 생성처럼 순서를 비교할 수 있는 상관관계가
  있는 사건이다.
- **Run Subject**: 실제 사람이 아닌 한 번의 Run에 격리된 합성 지원자와 지원 건이다.
- **Observation**: 특정 subject·구간·단계·시도에서 조회한 값 또는 조회 상태다.
- **Evidence Artifact**: 판정에 사용한 최소 원본과 출처·수집 시각·무결성 정보다.
- **N-02 Assertion Result**: N02-A1~A7별 기대, 실제 관찰, 사용 증적과 결과다.
- **Recovery Record**: 실패 조건 제거, 안전 상태 확인과 정상 재시도의 결과다.

### Scope Boundaries

#### Included

- WhyYou local/test 환경의 합성 지원자와 합성 회사
- N-02에 필요한 본인 확인 완료·미동의 기준선 생성
- 자료 분석, 녹화, AI 평가의 실재 보호 대상 경로 discovery와 readiness
- 우회 종류·정상 순서별 독립 subject lane과 저장 실패·복구용 동일 subject lane
- 정상 화면을 거치지 않은 동의 전 직접 우회 시도
- 요청 결과와 영속·비동기 부작용의 전후 비교
- 정상 동의의 정책 식별값과 처리 사건 순서 검증
- 한 종류의 동의 저장 실패 조건과 transaction 원자성 검증
- 실패 조건 제거, 안전 상태 확인, 정상 동의·처리 복구
- 경로별 assertion, verdict, 최소 증적, 무결성 검증과 봉인 bundle
- 실제 첫 FAIL 보존과 필요 시 child 재시험

#### Excluded and Deferred

- N-01의 PC·모바일 고지 표시 품질과 필수 문구 시각 검증
- N-03의 진행 중 정책 변경, 기존 동의 무효화와 재동의 전체 흐름
- 이의제기 A-01~A-03 기능 신규 구현
- H-01·H-02, E-01·E-02의 실행과 판정
- 실제 AWS staging·production 배포와 운영 트래픽 검증
- 실제 지원자, 운영 채용 결정, 운영 credential 사용
- 동의 철회·보관기간 만료의 전체 제품 정책 검증
- 여러 종류의 무작위 장애, 장시간 부하·성능·동시성 시험
- 외부 AI 모델 정확도·편향·법령 전체 준수 인증
- ControlProof 고객용 웹 워크벤치와 사람 대상 웹 UX 검토

현재 정책과 제출된 정책 식별값이 다른 요청을 서버가 거부하는 사실은 정상 동의 무결성의 보조 관찰로
남길 수 있다. 그러나 진행 도중 정책이 바뀐 기존 동의를 무효화하는 N-03 전체 시나리오는 이 Spec의
PASS 조건에 포함하지 않는다.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 등록된 모든 필수 보호 대상 경로의 동의 전 시도에서 요청 결과와 사후 효과가 100%
  관찰되며, 필수 사후 효과 하나라도 관찰하지 못한 Run이 PASS로 표시되는 경우는 0건이다.
- **SC-002**: 동의 전 자료 분석·녹화·AI 평가 효과가 생성되는 모든 고정 FAIL fixture를 100% N-02
  FAIL로 탐지하며 PASS로 오분류하는 경우는 0건이다.
- **SC-003**: N-02 PASS Run의 100%에서 정책 버전·내용 식별값·필수 목적이 연결되고, 모든 적용 가능한
  처리 경로에서 동의 완료가 처리 요청·시작보다 앞선다는 증적이 있다.
- **SC-004**: 사건 시각이 같거나 출처가 모순되어 선후를 증명할 수 없는 모든 fixture는 100%
  `INCONCLUSIVE`이며 PASS로 표시되는 경우는 0건이다.
- **SC-005**: 동의 저장 실패 Run의 100%에서 동의 사실·동의 완료 상태·완료 사건·보호 대상 처리 효과가
  각각 0건임을 확인하고, 부분 효과 fixture의 100%를 FAIL로 탐지한다.
- **SC-006**: 실패 조건이 적용된 Run의 100%에서 복구를 시도하고, 복구 실패 fixture의 100%가
  `RESTORE_FAILED`와 후속 장애 실행 차단으로 나타난다.
- **SC-007**: 정상 복구 fixture의 100%에서 동의 관련 논리 효과는 각각 한 세트이고, 복구 후 처리 순서는
  N02-A5를 만족한다.
- **SC-008**: 준비된 격리 환경에서 실행 담당자는 미동의 우회, 정상 순서, 동의 저장 실패와 복구를
  포함한 한 N-02 Run의 결과와 bundle 검증을 10분 안에 완료할 수 있다.
- **SC-009**: PASS·FAIL·INCONCLUSIVE 결과의 100%가 경로별 기대·관찰·증적, 복구 상태와 미검증 범위를
  제공하며, 필수 artifact 무결성 실패가 있는 PASS는 0건이다.
- **SC-010**: 재시험 후 부모 Run의 판정·증적·manifest 변경 건수는 0건이고 child Run의 부모 관계와
  대상 버전 차이를 100% 확인할 수 있다.
- **SC-011**: 전체 자동시험과 actual Run에서 실제 지원자 개인정보, 운영 채용 결정, 운영 credential과
  허용되지 않은 외부 AI 호출 사용 건수는 각각 0건이다.
- **SC-012**: 결과 설명의 100%가 실행한 N-02 경로와 로컬 환경의 범위만 주장하며, N-01·N-03·실제
  AWS·법적 준수 전체까지 검증했다고 표현하는 경우는 0건이다.

## Assumptions

- Spec 001·002의 Run, observation, evidence, verdict, restore, immutable retest와 target snapshot 계약을
  재사용한다.
- 공식 대상은 WhyYou의 local/test checkout이며 actual Run은 `LOCAL_EMULATED`, 실제 AWS는 `NOT_RUN`이다.
- WhyYou의 현재 지원자 흐름에는 정책 조회, 본인 확인, 동의 기록과 자료 제출·분석·면접·평가 기능이
  존재한다.
- 내구성 있게 확정된 동의 사실과 동의 완료 상태가 N-02 권한 판단의 기준이며, 비동기 완료 알림은
  유일한 진실 원본이 아니다.
- 한 Run은 자료 분석·녹화·AI 평가 우회와 정상 순서에 각각 독립된 합성 subject를 사용하고, 동의 저장
  실패와 복구만 같은 subject를 유지한다.
- 깊은 실제 경계의 필수 전제조건은 별도 probe lane에 allowlist된 합성 fixture로 만들 수 있으며,
  fixture 자체와 probe 호출 뒤 증분 효과를 구분할 수 있다.
- 시각만으로 순서를 판단할 수 없을 때 사용할 상관관계 또는 사건 순서 정보가 대상에 있거나 test-only
  관찰로 안전하게 제공될 수 있다.
- 동의 저장 실패 조건은 Run·subject allowlist를 가진 local/test 전용 조건으로 만들 수 있다.
- 최초 actual Run 전에 확인되지 않은 WhyYou 보호조치 결함을 미리 수정하지 않는다.
- N-01과 N-03은 공식 범위표에 따라 `NOT_RUN`이며 이 Spec 완료로 자동 완료되지 않는다.

## Dependencies

- 완료된 Spec 001·002의 공통 실행·증적·복구·재시험 기반
- WhyYou `bosung/controlproof-h03-integration` 계열의 식별 가능한 source version
- 합성 지원자와 본인 확인 완료·미동의 기준선을 만드는 격리된 seed 경로
- 서버가 제공한 정책과 확정된 동의 사실을 읽을 수 있는 허용된 관찰 경로
- 자료 분석·녹화·AI 평가의 실재 진입 경계와 부작용을 실행·관찰할 수 있는 local/test capability
- 동의 저장 실패를 한 Run·subject에 한정해 적용하고 제거할 수 있는 안전한 시험 조건
- 고정 AI 대역과 외부 AI 호출이 없는 재현 가능한 WhyYou 로컬 환경
- ControlProof Run 저장소와 bundle 무결성 검증 기능

## Risks and Product Responses

| 위험 | 제품 차원의 대응 |
|---|---|
| 화면 체크박스 클릭을 동의 완료로 오인 | 서버에 내구성 있게 확정된 동의 사실과 상태를 기준점으로 사용 |
| HTTP 거부만 보고 비동기 부작용을 놓침 | 각 경로의 저장·작업·시작·결과 효과를 시도 전후로 비교 |
| 자료 업로드 차단 하나로 녹화·평가까지 PASS 처리 | 보호 대상 경로를 분리하고 N02-A2~A4 독립 assertion 유지 |
| 직접 진입점이 없는 단계를 가짜 진입 경로로 만듦 | 실재 경계와 관찰 가능한 최초 효과를 capability로 고정하고 한계를 표시 |
| Outbox 전달 지연을 자동 위반으로 판정 | durable consent와 실제 처리 시작의 순서를 판정하고 전달 지연은 별도 관찰 |
| timestamp 정밀도·시계 오차로 거짓 PASS | 인과 순서 증적을 요구하고 없으면 INCONCLUSIVE |
| 동의 저장 실패 뒤 일부 record나 상태가 남음 | 동의 사실·상태·완료 사건을 독립 비교하고 하나라도 남으면 FAIL |
| 실패 조건이 후속 Run이나 다른 지원자에게 영향 | Run·subject allowlist, 의무 복구, 실패 시 후속 장애 Run 차단 |
| N-03 정책 변경 시나리오가 조용히 포함 | 현재 정책 식별 일치만 포함하고 진행 중 변경·재동의는 명시적으로 제외 |
| source 기준선의 오래된 cross-module 시험을 신뢰 | 현재 코드에 맞는 통합시험을 Plan에서 복구 또는 대체하고 actual Run으로 확인 |
| 최초 FAIL 전에 WhyYou를 편의상 수정 | 첫 actual Run과 bundle을 봉인한 뒤 관찰로 확인된 경계만 개인 브랜치에서 보완 |
| 로컬 PASS가 AWS·법적 인증으로 확대 | 모든 결과에 `LOCAL_EMULATED`, AWS `NOT_RUN`, 시나리오 한정 주장을 표시 |

## Traceability

| Product source | 이 Spec의 반영 위치 |
|---|---|
| V4 N-02 | User Story 1~4, N02-A1~A7, FR-007~FR-040 |
| Product Brief 14.4 | Feature Goal, User Story 1~3, Scope Boundaries, SC-001~SC-012 |
| Scenario Coverage Matrix N-02 | 실제 실행 범위, verdict와 완료 기준 |
| Decision D-001~D-006 | Run·subject·관찰·증적·복구·판정 계약 |
| Decision D-011 | readiness와 판정 불가 reason code |
| Decision D-012 | 웹 UX 검토 제외 |
| Decision D-013 | Spec 003이 N-02 수직 흐름을 소유 |
| Decision D-014 | source baseline, 5개 실제 실행 범위, 독립 재현·AI 작업 원칙 |
| N-02 source baseline | 동의 완료 기준, 확인된 submission 보호, 미확인 분석·녹화·평가 경로 |
| Constitution I·II·V·VI·VII | 증적 기반 판정, 상태 분리, 격리·복구, 불변 재시험, 추적성 |

## Planning Gate — Resolved

아래 질문은 [Plan](./plan.md), [Research](./research.md), [Data Model](./data-model.md)과
[Contracts](./contracts/)에서 실제 WhyYou 코드 기준으로 확정했다.

- 자료 분석·녹화·AI 평가 각각의 공식 요청·실제 시작·결과 경계와 관찰 가능한 부작용은 무엇인가
- 미동의 subject로 각 경계를 안전하게 시도할 수 있는 기존 경로와 필요한 local/test 전용 probe는
  무엇인가
- 동의 완료 transaction의 어느 실패 지점이 부분 저장·rollback을 가장 직접적으로 검증하는가
- 동의 완료, 처리 요청과 실제 시작의 순서를 어떤 공통 상관관계와 사건 식별 정보로 증명할 것인가
- 정책 버전·내용 식별값과 동의 사실을 전체 개인정보 없이 어떤 최소 증적으로 수집할 것인가
- 실패 조건의 allowlist, trigger receipt, 제거와 안전 상태 확인을 어떻게 보장할 것인가
- source baseline에서 발견된 오래된 cross-module 시험을 복구할지 새 통합시험으로 대체할지
- N02-A1~A7과 EV3-01~EV3-10을 구현 task·자동시험·actual Run artifact에 어떻게 연결할 것인가
- Spec 001·002의 기존 실행·증적·복구·재시험 계약을 깨뜨리지 않는가

미해결 `NEEDS CLARIFICATION`은 0개다. Tasks 생성 뒤 `$speckit-analyze`를 재실행해 CRITICAL·HIGH와
팀 해석 차이를 만드는 MEDIUM이 모두 0건임을 확인했다. 다음 단계는 `$speckit-implement`이며 Tasks의
테스트 우선 순서와 최초 actual Run 이전 제품 guard 수정 금지를 지킨다.
