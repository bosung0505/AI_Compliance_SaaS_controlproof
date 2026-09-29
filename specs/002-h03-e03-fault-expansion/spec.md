# Feature Specification: H-03·E-03 장애·재시도·DLQ 확장

**Feature Branch**: `002-h03-e03-fault-expansion`

**Created**: 2026-09-28

**Status**: Complete — Implemented and validated on `LOCAL_EMULATED`; AWS remains `NOT_RUN`

**Input**: Spec 001에서 검증한 H-03 최소 수직 흐름을 재시도 소진·DLQ·우회 경로까지 확장하고,
같은 장애 계열에서 E-03의 Outbox·상태·사람 결정 이력 완전성과 정확히 한 번의 업무 효과를
독립적으로 검증한다.

**Sources**:

- [2주 MVP 기능 범위 V4](../../docs/product/ControlProof_WhyYou_2주_MVP_기능범위_v4.md)
- [Product Brief](../../docs/product/ControlProof_MVP_Product_Brief.md)
- [MVP 결정 기록](../../docs/product/ControlProof_MVP_Decision_Log.md)
- [ControlProof Constitution](../../.specify/memory/constitution.md)
- [Spec 001](../001-execution-evidence-h03/spec.md)
- [Spec 001 실제 검증 기록](../001-execution-evidence-h03/validation.md)

## Clarifications

### Session 2026-09-28

- Q: 2주 MVP가 공식적으로 검증하는 실행환경은 어디인가? → A: WhyYou 로컬 Docker/LocalStack
  환경만 검증하며 실제 AWS 배포환경은 `NOT_RUN`·미검증 범위로 표시한다.
- Q: `whyyou-local`의 reporting 재시도 소진 후 어떤 최종 실패 경로를 검증하는가? → A: LocalStack의
  `iep-reporting-dlq`를 `INFRASTRUCTURE_DLQ`로 검증한다. reporting에는 애플리케이션
  `JobStatus.DLQ`가 없으므로 그 경로는 `NOT_APPLICABLE`이며 누락이나 FAIL로 판정하지 않는다.
- Q: `AFTER_RESULT_DURABLE_BEFORE_COMPLETION`의 정확한 장애 경계는 어디인가? → A: report,
  assistant retrieval projection, `processed_messages` 표식이 한 DB transaction으로 commit된 뒤이면서
  SQS message acknowledge 전이다. 재전달은 기존 표식을 확인하는 duplicate-ack 경로로 끝나야 한다.
- Q: `whyyou-local`에서 리포트 없는 채용 확정을 만들 수 있어 H-03이 반드시 시험할 쓰기 경로는
  무엇인가? → A: `recordHumanFinalDecision`과, 목표 단계명이 `최종합격` 또는 `불합격`인
  `moveApplicantsToRecruitingStage`다. 그 밖의 일반 단계 이동은 최종 확정 경로로 세지 않는다.
- Q: E-03에서 누락·중복을 판정할 정확한 업무 효과는 무엇인가? → A: reporting은 논리 report 1건,
  그 report와 일관된 assistant retrieval projection 집합, `processed_messages` 표식 1건과 기존
  `report.generation_requested` Outbox 원 사건 보존이다. 사람 결정은 단계 배정 1건, invitation
  `reviewed`, HumanReview 1건, `final_decision.create` 감사 1건이다. 현재 WhyYou가 만들지 않는 별도
  report-completed·final-decision Outbox 이벤트는 필수 효과로 가정하지 않는다.

## User Scenarios & Testing *(mandatory)*

### Feature Goal

검증 실행 담당자는 WhyYou의 리포트 생성 메시지가 반복 실패해 최종 실패 경로로 이동하는 상황을
안전하게 만들고 다음 두 질문에 서로 다른 판정으로 답할 수 있어야 한다.

1. **H-03 결정 안전성**: 실패가 담당자와 운영자에게 드러나고, 정상 최종결정 경로뿐 아니라
   최종 단계 대상 `moveApplicantsToRecruitingStage` 우회 경로로도 리포트 없는 채용 확정을 할 수
   없으며, 실패 건이 조용히 사라지지 않는가?
2. **E-03 이력 완전성**: 저장 전·후 장애와 재전달이 반복되어도 원 업무 사건, 처리 시도,
   리포트, 상태 전이, Outbox 이벤트와 사람 결정 이력을 하나의 계보로 설명할 수 있고,
   최종 업무 효과가 누락되거나 중복되지 않는가?

H-03과 E-03은 같은 종류의 장애와 일부 증적을 사용할 수 있지만 판정 목적은 합치지 않는다.
H-03 PASS가 E-03 PASS를 의미하지 않으며 그 반대도 마찬가지다. AI 점수는 사람의 판단을 돕는
참고 정보일 뿐이며, 이 기능은 점수 임계값에 따른 자동 합격·탈락을 만들거나 시험하지 않는다.

이 기능의 성공은 WhyYou가 반드시 PASS하는 것을 뜻하지 않는다. 실제 누락·중복·우회가 있으면
원본 증적을 가진 FAIL을 내는 것이 올바른 제품 동작이다. 수정 후 재시험은 새 Run으로 만들고
최초 결과를 보존한다.

2주 MVP의 공식 검증 대상은 배포된 AWS 서비스가 아니라 개발자 장비에서 실행하는 `whyyou-local`이다.
PostgreSQL·LocalStack·Mailpit은 컨테이너에서, WhyYou API·worker·회사 화면은 로컬 호스트에서 실행한다.
SQS·DLQ 결과는 LocalStack에 대한 결과이며 실제 AWS SQS, ECS, IAM, CloudWatch, 운영 네트워크와
가용성을 검증했다고 표현해서는 안 된다. 이후 staging이나 AWS 환경을 다시 만들면 같은 시나리오를
새 Run으로 실행해야 하며 로컬 PASS를 클라우드 PASS로 승격하거나 복사해서는 안 된다.

### Spec 001과의 관계

Spec 001의 실행·증적·판정·복구·재시험 계약과 H03-A1~H03-A6은 이 기능의 기준선이다.
Spec 002는 이를 다시 정의하거나 약화하지 않고 다음 공백을 채운다.

- 제한된 횟수의 실패가 아니라 재시도 한도를 실제로 소진한다.
- WhyYou가 현재 구성한 최종 실패 경로를 식별하고, 원 메시지와 실패 건이 연결되는지 확인한다.
- 담당자용 실패 표시와 운영자가 추적할 수 있는 실패 기록을 구분해 확인한다.
- 정상 최종결정 경로 외에 채용 확정 효과를 낼 수 있는 모든 문서화된 경로를 시험한다.
- 리포트의 내구 저장 전과 저장 후·처리 완료 확인 전의 두 장애 경계를 각각 시험한다.
- 복구 후 동일한 논리 요청을 재처리해 업무 효과의 누락과 중복을 확인한다.
- Outbox·처리·상태·사람 결정 이력에 대해 E-03만의 별도 assertion과 verdict를 만든다.

### User Story 1 - 재시도 소진 뒤 실패 건이 사라지지 않는지 확인한다 (Priority: P1)

검증 실행 담당자는 합성 지원자의 리포트 생성 작업에 반복 가능한 장애를 적용한다. ControlProof는
재시도가 설정된 한도까지 수행되는지, 그 뒤 메시지 또는 작업이 WhyYou가 선언한 최종 실패 경로에
남는지, 원 업무 사건과 각 처리 시도를 다시 연결할 수 있는지 확인한다.

**Why this priority**: 장애가 한 번 발생했다는 사실만으로는 실패 건이 최종적으로 보존되는지 알 수
없다. 재시도 소진과 실패 건 추적은 H-03 완성과 E-03 계보 검증의 공통 출발점이다.

**Independent Test**: 격리된 시험환경에서 리포트 생성 대기 상태의 합성 지원자 한 명을 만들고,
해당 건에만 반복 장애를 적용한다. 재시도 한도를 소진시킨 뒤 원 업무 사건, 원 메시지, 모든 처리
시도와 최종 실패 기록을 연결할 수 있는지 확인한다.

**Acceptance Scenarios**:

1. **Given** reporting 대상과 재시도·최종 실패 경로가 식별되고 장애 적용·해제·관찰 수단이 준비됐을 때,
   **When** 실행 담당자가 사전 점검을 수행하면, **Then** ControlProof는 재시도 한도, 관찰 가능한
   실패 경로, 원 사건 연결 키와 복구 가능 여부를 실행 전에 표시한다.
2. **Given** 정상 기준선과 원 리포트 생성 사건이 기록됐을 때, **When** 대상 건에 반복 장애를 적용하면,
   **Then** 각 전달 시도의 순서·시각·시도 번호·오류 결과가 같은 원 사건에 연결된다.
3. **Given** 재시도 한도가 소진됐을 때, **When** 최종 실패 상태를 관찰하면, **Then** 메시지 또는 작업은
   WhyYou가 해당 흐름에 선언한 실패 경로에 남고 원 사건 및 마지막 실패 원인과 연결된다.
4. **Given** `whyyou-local` reporting에 인프라 DLQ만 적용될 때, **When** 결과를 설명하면,
   **Then** `iep-reporting-dlq`를 실제 경로로 표시하고 reporting 애플리케이션 `JobStatus.DLQ`는
   `NOT_APPLICABLE`로 표시한다.
5. **Given** snapshot된 queue 설정을 읽었을 때, **When** `iep-reporting`과
   `iep-reporting-dlq`의 redrive 연결이 없거나 예상 설정과 다르면, **Then** Run 생성을 막고 실제
   설정과 기대값의 차이를 표시한다.
6. **Given** 조회 수단이 정상인데 원 메시지나 최종 실패 기록을 찾을 수 없을 때, **When** 판정하면,
   **Then** 실패 건 유실로 FAIL을 내고 확인한 범위와 원본 조회 결과를 연결한다.
7. **Given** 실패 경로에 접근할 권한이나 관찰 수단이 없을 때, **When** 판정하면, **Then** 유실로 추정하지
   않고 적절한 사유의 INCONCLUSIVE를 내며 미검증 범위를 표시한다.

---

### User Story 2 - 리포트 없는 채용 확정을 모든 경로에서 막는지 확인한다 (Priority: P1)

검증 실행 담당자는 최종 실패 상태의 합성 지원자에 대해 `recordHumanFinalDecision`과 목표가
`최종합격` 또는 `불합격`인 `moveApplicantsToRecruitingStage`를 각각 시도한다. ControlProof는
경로별 응답과 결정·지원 건·채용 단계 상태를 함께 비교해 우회 가능 여부를 판정한다.

**Why this priority**: 한 API만 안전해도 다른 쓰기 경로가 같은 최종 상태를 만들 수 있다면 인간 검토
보호조치는 우회된다. H-03은 화면 버튼이 아니라 최종 채용 효과 전체를 보호해야 한다.

**Independent Test**: 리포트가 없고 reporting 작업이 최종 실패 상태인 합성 지원자를 준비한다.
capability map에 등록된 각 채용 확정 가능 경로를 회사 사용자로 호출한 뒤, 모든 요청이 거부되고
부분 변경이 0건인지 확인한다.

**Acceptance Scenarios**:

1. **Given** reporting 작업이 최종 실패했고 리포트가 없는 지원자일 때, **When** 회사 사용자가 정상
   최종결정 경로로 채용 결정을 시도하면, **Then** 리포트 부재를 설명하는 이유와 함께 거부되고
   결정·지원 건·채용 단계 상태가 바뀌지 않는다.
2. **Given** 동일한 지원자와 초기 상태일 때, **When** `moveApplicantsToRecruitingStage`의 목표를
   `최종합격` 또는 `불합격`으로 지정하면, **Then** 동일한 보호 원칙으로 거부되고 부분 변경이
   없어야 한다.
3. **Given** 대상 버전에 채용 확정 효과를 낼 수 있는 문서화된 경로가 둘 이상일 때, **When** 하나라도
   실행기 등록에서 빠져 있으면, **Then** H-03 Run을 PASS로 만들지 않고 준비 미완료로 표시한다.
4. **Given** 우회 요청이 수락되거나 최종 결정·단계·지원 건 중 하나라도 변경됐을 때, **When** 판정하면,
   **Then** 해당 경로와 변경 전후 증적을 가진 H-03 FAIL을 낸다.
5. **Given** 모든 경로가 거부됐을 때, **When** 장애 구간의 결정 이력을 확인하면, **Then** 사람의 요청
   없이 시스템이 만든 최종 결정도 없어야 한다.

---

### User Story 3 - 리포트 저장 전 장애에서 누락 없는 복구를 확인한다 (Priority: P1)

검증 실행 담당자는 worker가 리포트 생성 요청을 받았지만 리포트가 내구 저장되기 전에 실패하도록
조건을 만든다. 재시도 소진과 최종 실패 기록을 확인한 뒤 장애를 해제하고 같은 논리 요청을 재처리한다.
ControlProof는 최종 report, 그와 일관된 assistant retrieval projection 집합과
`processed_messages` 표식이 누락·중복 없이 남는지 판정한다.

**Why this priority**: 저장 전 장애는 결과가 아예 사라지는 누락 위험을 대표한다. 장애 기록만 남고
복구 후 결과가 만들어지지 않으면 증적 보존과 서비스 복구 모두 실패한 것이다.

**Independent Test**: `BEFORE_RESULT_DURABLE` 의미의 장애 조건을 가진 E-03 Run 하나를 실행한다.
장애 중 리포트가 없고, 복구·재처리 후 리포트와 완료 효과가 정확히 하나이며 전체 처리 계보가
연결되는지 확인한다.

**Acceptance Scenarios**:

1. **Given** 원 업무 사건과 리포트가 없는 기준선일 때, **When** 결과 내구 저장 전에 장애가 발생하면,
   **Then** 실패한 시도는 기록되지만 report·assistant retrieval projection·`processed_messages`
   표식은 만들어지지 않는다.
2. **Given** 저장 전 장애로 재시도 한도를 소진했을 때, **When** 장애를 해제하고 원 사건을 재처리하면,
   **Then** 논리 report 1건, 그와 일관된 assistant retrieval projection 집합과
   `processed_messages` 표식 1건이 생성되고 기존 `report.generation_requested` 원 사건과 연결된다.
3. **Given** 원 사건이 여러 번 전달됐을 때, **When** 복구 결과를 판정하면, **Then** 전달 시도는 여러
   건일 수 있지만 report는 1건이고 projection 집합은 그 report와 일관되며 처리 표식은 1건이다.
4. **Given** report·projection 집합·처리 표식 중 하나가 끝내 생성되지 않았을 때, **When** 관찰
   수단이 정상이라면, **Then** 누락된 효과와 원 사건을 연결한 E-03 FAIL을 낸다.

---

### User Story 4 - 리포트 저장 후 재전달에서 중복 효과를 막는지 확인한다 (Priority: P1)

검증 실행 담당자는 리포트가 내구 저장됐지만 해당 메시지의 처리 완료가 확정되기 전 장애가 발생한
조건을 만든다. 동일 메시지가 다시 전달되더라도 이미 저장된 report·assistant retrieval projection·
처리 표식을 중복 또는 불일치 상태로 만들지 않는지 확인한다.

**Why this priority**: 저장 후 장애는 “처리는 됐지만 완료 신호가 없다”는 분산 처리의 대표적인 중복
위험이다. 정상 흐름과 저장 전 장애만 시험하면 이 결함을 발견할 수 없다.

**Independent Test**: `AFTER_RESULT_DURABLE_BEFORE_COMPLETION` 의미의 장애 조건을 가진 E-03 Run을
별도로 실행한다. 재전달 전후 report·assistant retrieval projection·`processed_messages`와 원
Outbox event의 논리 식별자와 건수를 비교한다.

**Acceptance Scenarios**:

1. **Given** report·assistant retrieval projection·`processed_messages` 표식의 DB transaction은
   commit됐지만 SQS message가 acknowledge되지 않은 상태일 때, **When** 동일한 원 사건이 재전달되면,
   **Then** 기존 표식을 확인하는 duplicate-ack 경로로 끝나고 같은 논리 리포트가 추가 생성되지 않는다.
2. **Given** 재전달이 한 번 이상 발생했을 때, **When** 처리 이력을 재구성하면, **Then** 각 전달 시도와
   중복 억제 결과를 원 사건에 연결할 수 있다.
3. **Given** 재전달 뒤 성공 처리가 끝났을 때, **When** 업무 효과를 비교하면, **Then** report는 1건이고
   projection 집합은 그 report와 일관되며 처리 표식과 원 Outbox event는 각각 1건만 존재한다.
4. **Given** 중복 리포트·중복 완료 효과·서로 모순되는 최종 상태 중 하나가 확인됐을 때, **When**
   판정하면, **Then** 해당 중복 또는 모순과 원본을 연결한 E-03 FAIL을 낸다.

---

### User Story 5 - 복구 후 사람 결정 이력을 정확히 한 번 보존한다 (Priority: P2)

리포트가 정상 복구된 뒤 권한 있는 회사 사용자는 지원자의 실제 답변과 AI 참고 정보를 함께 보고
최종 채용 단계를 선택한다. 검증 실행 담당자는 같은 `Idempotency-Key`로 동일한 논리 결정 요청을
재전송해 단계 배정, invitation `reviewed`, HumanReview와 `final_decision.create` 감사 기록이
누락되거나 중복되지 않는지 확인한다.

**Why this priority**: E-03은 리포트 생성 이력만이 아니라 그 결과를 사용한 사람 결정의 보존까지
다룬다. 다만 리포트 복구가 선행되어야 하므로 P2다.

**Independent Test**: 복구 완료된 합성 지원자에 대해 같은 `Idempotency-Key`를 가진
`recordHumanFinalDecision` 요청을 두 번 전송한다. 두 응답과 무관하게 단계 배정 1건, invitation
`reviewed`, HumanReview 1건과 `final_decision.create` 감사 1건인지 확인한다.

**Acceptance Scenarios**:

1. **Given** 리포트가 준비됐고 회사 사용자가 검토를 완료했을 때, **When** 사람의 최종결정을 기록하면,
   **Then** 선택한 단계 배정, invitation `reviewed`, HumanReview와 `final_decision.create` 감사가 하나의
   결정 계보로 연결된다.
2. **Given** 같은 논리 결정 요청이 다시 전달됐을 때, **When** 결과를 비교하면, **Then** 동일한 업무
   효과를 가리키며 단계 배정·HumanReview·감사가 추가 생성되지 않고 invitation 상태가 모순되지 않는다.
3. **Given** 더 낮은 AI 점수의 지원자를 사람이 채용하거나 더 높은 점수의 지원자를 채용하지 않는
   결정을 했을 때, **When** 이력을 검토하면, **Then** 사람의 실제 선택과 주체가 그대로 보존되며
   ControlProof가 점수를 근거로 결정을 수정하거나 재판정하지 않는다.
4. **Given** 결정 효과나 필수 이력이 누락 또는 중복됐을 때, **When** 관찰 수단이 정상이라면,
   **Then** 해당 E-03 assertion을 FAIL로 판정한다.

---

### User Story 6 - H-03과 E-03을 독립적으로 설명하고 재시험한다 (Priority: P2)

검증 결과 검토자는 같은 장애 계열에서 나온 H-03과 E-03 결과를 각각 확인하고, 어느 보호조치가
실패했는지와 무엇을 검증하지 못했는지를 혼동 없이 이해한다. 수정 후 결과는 최초 Run을 덮어쓰지
않고 별도 Run으로 연결한다.

**Why this priority**: 결정 안전성과 이력 완전성을 하나의 녹색 결과로 합치면 한쪽의 실패가 가려진다.
또한 최초 실패를 보존해야 개선 사실을 증명할 수 있다.

**Independent Test**: H-03만 실패하는 fixture, E-03만 실패하는 fixture, 증적 접근이 막힌 fixture와
모두 통과하는 fixture를 각각 판정해 두 결과가 독립적으로 기대값과 일치하는지 확인한다.

**Acceptance Scenarios**:

1. **Given** 우회 결정은 차단됐지만 복구 후 report 또는 assistant retrieval projection이
   중복·불일치할 때, **When** 판정하면,
   **Then** H-03과 E-03 결과를 합치지 않고 H-03 보호조치 결과와 E-03 FAIL을 각각 표시한다.
2. **Given** 이력은 완전하지만 최종 단계 대상 `moveApplicantsToRecruitingStage`로 리포트 없는 확정이
   가능할 때, **When** 판정하면,
   **Then** E-03 이력 결과와 H-03 FAIL을 각각 표시한다.
3. **Given** 필수 증적 접근이 막혀 한 시나리오를 평가할 수 없을 때, **When** 다른 시나리오의 직접
   위반 또는 충족 사실은 충분히 관찰됐으면, **Then** 각 시나리오가 서로 다른 verdict를 가질 수 있다.
4. **Given** 최초 Run 이후 WhyYou가 수정됐을 때, **When** 재시험하면, **Then** 새 Run은 부모와 대상
   버전 차이를 연결하고 최초 Run의 판정·증적·digest를 변경하지 않는다.

### Edge Cases

- 재시도 한도 설정값과 실제 전달 횟수가 다르면 설정 snapshot과 실제 시계열을 모두 보존하고
  재시도 소진 assertion을 FAIL로 판정한다.
- reporting에 애플리케이션 `JobStatus.DLQ`가 없고 인프라 DLQ만 있으면 실제 구성을 표시한다.
  존재하지 않는 애플리케이션 상태를 새로 만들거나 누락으로 판정하지 않는다.
- DLQ 메시지는 존재하지만 원 업무 사건·지원자·Outbox 이벤트와 연결되지 않으면 “보존됨”으로
  보지 않고 FAIL로 판정한다.
- 메시지가 재시도 중인데 관찰 기한이 먼저 끝나면 최종 실패에 도달했다고 추정하지 않고
  INCONCLUSIVE로 판정한다.
- 실패 건이 DLQ로 이동했지만 담당자 화면이 계속 단순 `처리 중`으로만 표시되면 H-03 FAIL이다.
- 운영자용 실패 기록은 보이지만 담당자 화면의 상태가 오해를 만들면 H-03을 PASS로 만들지 않는다.
- 일반 단계 이동은 되지만 그 단계가 최종 채용 효과를 뜻하지 않으면 최종결정 우회로 간주하지 않는다.
  대상 버전의 단계 의미 snapshot을 기준으로 판정한다.
- 같은 메시지의 여러 전달 시도는 그 자체로 중복 실패가 아니다. report·projection·처리 표식 또는
  사람 결정 필수 효과가 정의된 기대 건수와 다를 때 중복·누락이다.
- 서로 다른 논리 요청이 같은 지원자에게 연속 수행된 것은 중복이 아니다. 동일 논리 요청 식별자와
  대상·행위가 같은 경우만 재전송으로 비교한다.
- 결과 저장 뒤 완료 확인 전 장애에서 트랜잭션이 실제로 롤백됐다면 저장 전 장애와 같은 결과가
  나타날 수 있다. 선언한 장애 경계가 관찰되지 않으면 대상 결함으로 추정하지 않고 Run을
  INCONCLUSIVE로 처리한다.
- 복구 도중 환경 안전성 확인이 실패하면 이미 관찰한 직접 위반은 finding으로 유지하되 전체 결과는
  INCONCLUSIVE로 종료하고 같은 대상의 후속 장애 Run을 차단한다.
- 메시지 재처리 후 리포트는 하나지만 검색 projection 같은 파생 효과가 중복됐으면 E-03 FAIL이다.
- 결정 요청의 첫 응답이 유실돼 클라이언트가 재전송한 경우에도 결정 업무 효과는 하나여야 한다.
- 증적 출처들이 같은 사건의 동일 시점 상태를 다르게 말하면 EVIDENCE_CONFLICT이며, 서로 다른
  시도나 구간의 정상적인 상태 변화는 충돌이 아니다.

## Requirements *(mandatory)*

### Functional Requirements

#### 검증 환경과 주장 경계

- **FR-081**: Spec 002의 공식 2주 MVP target ID는 `whyyou-local`이어야 하며 실행환경 종류는
  `LOCAL_EMULATED`로 기록해야 한다.
- **FR-082**: 각 Run은 WhyYou commit, ControlProof commit, 운영체제, 컨테이너 구성, 로컬 서비스 URL,
  PostgreSQL 버전, LocalStack 버전과 queue·DLQ 설정을 포함한 환경 snapshot을 가져야 한다.
- **FR-083**: `LOCAL_EMULATED` Run의 AWS 배포환경 검증 상태는 항상 `NOT_RUN`이어야 하며 실제 AWS
  SQS·ECS·IAM·CloudWatch·운영 네트워크를 검증한 것으로 표시해서는 안 된다.
- **FR-084**: 로컬 SQS·DLQ에 대한 PASS는 LocalStack 메시징 계약에만 적용되고 실제 AWS의 운영
  안정성·권한·경보·복구를 보증해서는 안 된다.
- **FR-085**: 로컬 실행은 외부 클라우드 AI 호출을 허용해서는 안 되며 ControlProof 고정 모델 대역이
  활성화되고 fixture ID와 digest가 확인돼야 `READY`가 될 수 있다.
- **FR-086**: 로컬 Run 결과는 환경 종류와 미검증 클라우드 범위를 결과 요약과 구조화된 결과에 모두
  표시해야 한다.
- **FR-087**: 향후 staging 또는 AWS 환경 검증은 새 target ID와 새 Run으로 실행해야 하며 로컬 Run의
  verdict·증적을 해당 환경 결과로 복사하거나 승격해서는 안 된다.

#### Spec 001 계약의 연속성

- **FR-001**: Spec 002의 모든 실행은 Spec 001의 Run, subject, phase, step, attempt, Observation,
  Evidence Artifact, Assertion Result, Judgement와 Retest Link 의미를 유지해야 한다.
- **FR-002**: 하나의 Run은 H-03 또는 E-03 중 정확히 한 시나리오를 실행해야 하며 두 시나리오의
  verdict를 하나로 합쳐서는 안 된다.
- **FR-003**: H-03과 E-03 Run이 같은 장애 조건을 사용하더라도 각각 고유한 Run ID와 시나리오
  snapshot을 가져야 한다.
- **FR-004**: 모든 관찰과 증적은 `subject_ref`, `phase`, `step_id`, `attempt`로 어떤 지원자·구간·단계·
  처리 시도인지 구분할 수 있어야 한다.
- **FR-005**: 조회 성공 후 결과 없음과 조회 자체 실패를 구분해야 한다.
- **FR-006**: 같은 시나리오·초기 상태·장애 의미로 재시험할 수 있어야 하며 합성 대상 식별자가 다른
  Run과 충돌해서는 안 된다.
- **FR-007**: AI 점수는 자동 채용 판정 규칙이나 H-03·E-03 verdict 입력으로 사용해서는 안 된다.
- **FR-008**: 실제 지원자 정보와 운영 채용 데이터는 어떤 Run에도 사용해서는 안 된다.
- **FR-009**: 외부 AI 결과의 변동이 재시도·중복 판정에 영향을 주지 않도록 고정된 합성 결과가
  준비된 경우에만 실행 가능해야 한다.
- **FR-010**: 완료된 Spec 001 Run과 Spec 002 Run은 서로를 수정하거나 덮어써서는 안 된다.

#### 준비 상태와 실행 조건

- **FR-011**: 실행 전 대상 버전에서 reporting 원 사건, 재시도 한도, 최종 실패 경로, 관찰 경로,
  장애 적용·해제 방법과 복구 방법의 capability를 확인해야 한다.
- **FR-012**: 최종 실패 경로는 `APPLICATION_DLQ`, `INFRASTRUCTURE_DLQ`, `TRACEABLE_FAILED_STATE` 중
  대상에 실제 존재하는 종류와 식별자를 선언해야 하며, 존재하지 않는 종류를 필수로 가정해서는 안 된다.
- **FR-013**: 대상이 둘 이상의 최종 실패 경로를 함께 사용한다고 선언하면 모든 선언된 경로를
  관찰할 준비가 되어야 `READY`가 될 수 있다.
- **FR-014**: 대상 기능은 있으나 재시도 소진·최종 실패 이동·복구 중 하나를 실행할 수 없으면
  `RUNNER_NOT_READY`로 표시하고 Run 생성을 막아야 한다.
- **FR-015**: 대상 기능과 실행기는 있으나 허용된 접근으로 필수 상태를 읽을 수 없으면
  `ACCESS_BLOCKED`로 표시하고 Run 생성을 막아야 한다.
- **FR-016**: reporting 기능 자체가 없을 때만 `NO_TEST_TARGET`을 사용해야 한다.
- **FR-017**: H-03 준비 상태는 정상 최종결정 경로와 대상 버전에서 채용 확정 효과를 낼 수 있는
  모든 문서화된 대체 경로를 포함해야 한다.
- **FR-018**: E-03 준비 상태는 결과 내구 저장 전과 결과 내구 저장 후·처리 완료 확인 전의 두 장애
  의미를 서로 구분해 만들고 관찰할 수 있어야 한다.
- **FR-019**: 한 E-03 Run에는 두 장애 의미 중 하나만 적용해야 하며 두 조건은 각각 격리된 Run으로
  실행해야 한다.
- **FR-020**: preflight 결과는 구현 상태와 WhyYou verdict를 분리하고, 준비되지 않은 실행을
  `NO_TEST_TARGET`이나 PASS로 표시해서는 안 된다.
- **FR-088**: `whyyou-local`의 reporting 최종 실패 경로는 `INFRASTRUCTURE_DLQ`인
  `iep-reporting-dlq`로 고정하고, 원 queue `iep-reporting`의 redrive 설정과 연결해 관찰해야 한다.
  reporting 애플리케이션 `JobStatus.DLQ`는 `NOT_APPLICABLE`로 기록해야 한다.

#### 재시도 소진과 최종 실패 보존

- **FR-021**: H-03과 E-03의 재시도 소진 Run은 장애 적용 전 원 업무 사건과 원 메시지 식별자를
  기준선으로 기록해야 한다.
- **FR-022**: 장애는 선택한 Run과 subject의 reporting 처리에만 적용되고 다른 처리 건에는 영향을
  주지 않아야 한다.
- **FR-023**: 장애 적용 명령과 worker에서 장애가 실제 발동한 사실을 독립적으로 확인해야 한다.
- **FR-024**: 각 전달 시도에 시도 번호, 관찰 시각, 오류 종류, 재시도 여부와 다음 상태를 기록해야 한다.
- **FR-025**: 선언된 재시도 한도와 실제 처리 시도 시계열을 비교해야 한다.
- **FR-026**: 재시도 한도 소진 후 대상이 선언한 최종 실패 경로에서 원 사건과 연결되는 실패 기록을
  찾을 수 있어야 한다.
- **FR-027**: 최종 실패 기록은 원 사건, 원 메시지 또는 Outbox 이벤트, subject, 마지막 처리 시도와
  실패 원인을 하나의 계보로 재구성할 수 있어야 한다.
- **FR-028**: 조회가 정상 완료됐는데 선언된 실패 기록이 없거나 원 사건과 연결되지 않으면
  실패 건 유실로 판정해야 한다.
- **FR-029**: 최종 실패 경로 조회가 실패하거나 권한 때문에 제한되면 유실로 추정하지 않고
  INCONCLUSIVE로 판정해야 한다.
- **FR-030**: 애플리케이션 실패 상태와 인프라 DLQ가 모두 존재하면 두 상태를 서로 다른 출처로
  보존하고 동일 사건에 대한 모순을 검사해야 한다.

#### H-03 결정 안전성 확장

- **FR-031**: 담당자에게 보이는 상태는 `리포트 없음`, `생성 중`, `재시도 중`, `최종 실패`, `준비 완료`
  가운데 대상이 제공하는 실제 의미를 구분해 기록해야 한다.
- **FR-032**: 작업이 최종 실패했는데 담당자 화면 또는 조회 결과가 관찰 기한까지 단순 생성 중으로만
  보이면 H-03 실패 노출 assertion을 FAIL로 판정해야 한다.
- **FR-033**: 최종 실패 상태에서 권한 있는 회사 사용자의 정상 최종결정 시도를 수행하고 대상이
  제공한 응답 이유와 처리 전후 상태를 관찰해야 한다.
- **FR-034**: `moveApplicantsToRecruitingStage`의 목표를 `최종합격`과 `불합격`으로 각각 지정해
  리포트 없는 채용 확정 우회가 가능한지 시도해야 한다.
- **FR-035**: 채용 확정 효과를 낼 수 있는 경로 하나라도 실행기에서 누락되면 H-03 Run은 PASS가
  될 수 없어야 한다.
- **FR-036**: 리포트 없는 상태의 모든 채용 확정 시도는 명시적 거부 결과를 가져야 한다.
- **FR-037**: 거부된 각 시도 뒤 최종결정 기록, HumanReview, 채용 단계와 지원 건 상태가 기준선에서
  바뀌지 않아야 한다.
- **FR-038**: 장애 구간에 사람 요청 없이 시스템 주체가 만든 최종결정 또는 확정 상태 변화가
  없어야 한다.
- **FR-039**: 우회 경로가 요청을 수락하거나 채용 확정 효과 또는 부분 변경을 만들면 H-03을 FAIL로
  판정해야 한다.
- **FR-040**: H-03의 재처리 성공 여부는 복구 가능성으로 표시하되, 리포트·이벤트·결정의 중복·누락은
  E-03 assertion의 책임으로 유지해야 한다.

#### E-03 이력 완전성과 정확히 한 번의 업무 효과

- **FR-041**: E-03은 원 업무 사건부터 Outbox, 전달 시도, 최종 실패, 복구·재처리와 최종 업무 효과까지
  순서대로 재구성 가능한 처리 계보를 만들어야 한다.
- **FR-042**: 여러 번의 메시지 전달을 중복 업무 효과로 간주해서는 안 되며, 동일 논리 결과의 식별자와
  대상·행위가 같은 효과가 둘 이상 생겼는지를 판정해야 한다.
- **FR-043**: 결과 내구 저장 전 장애 Run은 장애 구간에 report·assistant retrieval projection·
  `processed_messages` 표식이 생성되지 않았음을 확인해야 한다.
- **FR-044**: 결과 내구 저장 전 장애를 복구해 재처리한 뒤 논리 report 1건, 그 report와 일관된
  assistant retrieval projection 집합과 `processed_messages` 표식 1건이 존재해야 한다.
- **FR-045**: 결과 내구 저장 후·처리 완료 확인 전 장애 Run은 장애가 선언한 경계에 실제로 도달했음을
  report·assistant retrieval projection·`processed_messages`의 같은 DB transaction commit과 SQS
  acknowledge 미수행의 독립 관찰로 확인해야 한다.
- **FR-046**: 결과 저장 후 동일 원 사건이 재전달돼도 같은 논리 리포트를 추가 생성해서는 안 된다.
- **FR-047**: 결과 저장 후 재전달 과정에서 assistant retrieval projection을 중복·불일치 상태로
  만들거나 `processed_messages` 표식을 중복 생성해서는 안 된다.
- **FR-048**: 장애 의미가 실제로 관찰되지 않으면 대상 서비스의 PASS나 FAIL로 추정하지 않고
  해당 Run을 INCONCLUSIVE로 판정해야 한다.
- **FR-049**: 복구 후 report·assistant retrieval projection·`processed_messages` 중 하나가 끝내 없고
  해당 출처 조회는 정상이면 E-03을 FAIL로 판정해야 한다.
- **FR-050**: 같은 논리 report나 `processed_messages` 표식이 둘 이상 존재하거나 projection 집합이
  해당 report와 불일치하면 E-03을 FAIL로 판정해야 한다.
- **FR-051**: 복구 후 회사 사용자가 리포트를 검토한 다음에만 사람의 최종결정 이력 시험을 시작해야 한다.
- **FR-052**: 사람의 최초 `recordHumanFinalDecision` 요청은 단계 배정, invitation `reviewed`,
  HumanReview와 `final_decision.create` 감사를 하나의 결정 계보로 연결해야 한다.
- **FR-053**: 같은 논리 결정 요청의 재전송은 최초 요청과 같은 업무 효과를 가리켜야 하며 단계 배정,
  HumanReview 또는 감사를 추가 생성하거나 invitation 상태를 모순되게 바꿔서는 안 된다.
- **FR-054**: 사람의 결정 내용과 주체를 그대로 보존해야 하며 AI 점수의 높고 낮음에 따라 결정
  내용을 변경하거나 결정 정당성을 자동 평가해서는 안 된다.
- **FR-055**: E-03은 리포트 처리 계보와 사람 결정 계보의 누락·중복 결과를 각각 표시해야 한다.
- **FR-089**: `AFTER_RESULT_DURABLE_BEFORE_COMPLETION` 장애는 report·assistant retrieval projection·
  `processed_messages` 표식의 DB transaction commit 이후, SQS message acknowledge 이전에만
  발동해야 한다.
- **FR-090**: FR-089 이후 같은 event가 재전달되면 worker는 기존 `processed_messages` 표식을 근거로
  handler를 다시 실행하지 않는 duplicate-ack 경로를 사용해야 하며 그 사실을 증적으로 남겨야 한다.
- **FR-091**: `whyyou-local`의 H-03 decision path capability는 `recordHumanFinalDecision`과 목표
  단계명이 `최종합격` 또는 `불합격`인 `moveApplicantsToRecruitingStage`를 반드시 포함해야 한다.
  전자는 `FINAL_DECISION`, 후자는 목표 단계별 `BATCH_MOVE_FINAL_ACCEPT`와
  `BATCH_MOVE_FINAL_REJECT`로 표현해 operation capability 2개와 canonical path ID 3개를 구분해야 한다.
  snapshot된 WhyYou commit에서 다른 최종 확정 경로가 발견되면 PASS 전에 capability와 시험 대상을
  갱신해야 한다.
- **FR-092**: reporting의 필수 업무 효과 집합은 논리 report 1건, 그 report와 일관된 assistant
  retrieval projection 집합, 같은 event의 `processed_messages` 표식 1건과 기존
  `report.generation_requested` Outbox 원 사건 보존으로 고정해야 한다.
- **FR-093**: WhyYou가 현재 생성하지 않는 별도 report-completed Outbox event를 reporting의 필수
  효과로 요구하거나, 그 부재를 FAIL로 판정해서는 안 된다.
- **FR-094**: 사람 결정의 필수 업무 효과 집합은 단계 배정 1건, invitation `reviewed`, HumanReview
  1건과 `final_decision.create` 감사 1건으로 고정해야 한다. 별도 final-decision Outbox event는
  필수 효과로 요구해서는 안 된다.
- **FR-095**: E03-A7의 최초 요청과 재전송은 동일한 `Idempotency-Key`를 사용해야 하며, 현재 대상이
  이를 무시해 중복이나 모순을 만들면 최초 Run을 FAIL로 봉인하고 수정 후 새 Run으로 재시험해야 한다.

#### 증적과 무결성

- **FR-056**: 각 필수 assertion은 기대값, 실제 관찰값과 판정에 사용한 최소 원본 증적을 연결해야 한다.
- **FR-057**: 증적은 최소한 Run, scenario, subject, phase, step, attempt, 출처, 수집 시각, MIME 유형,
  크기와 SHA-256을 포함해야 한다.
- **FR-058**: 처리 계보에는 시험 실행 ID, subject, 원 업무 사건, Outbox 이벤트, 메시지 또는 작업,
  각 처리 시도와 최종 업무 효과의 식별 관계가 포함돼야 한다.
- **FR-059**: 최종 실패 증적은 실제 적용된 실패 경로 종류와 locator를 포함해야 한다.
- **FR-060**: 사람이 보는 상태 증적과 운영자가 추적하는 실패 기록 증적을 서로 다른 출처로 구분해야 한다.
- **FR-061**: 원본 locator는 보존하되 전체 로그나 전체 데이터베이스 사본을 수집해서는 안 된다.
- **FR-062**: 비밀값과 개인정보는 증적 저장 전에 제거하거나 마스킹해야 한다.
- **FR-063**: 증적 무결성 확인에 실패한 자료는 PASS의 필수 근거로 사용할 수 없어야 한다.
- **FR-064**: 동일 사건에 대한 독립 출처가 같은 phase·step·attempt에서 모순되면
  `EVIDENCE_CONFLICT`로 판정해야 한다.
- **FR-065**: 한 시나리오 Run의 증적을 다른 시나리오 verdict에 사용할 때는 원본 Run·artifact와
  digest를 참조해야 하며 복사본을 새 원본처럼 표시해서는 안 된다.

#### 판정, 복구와 재시험

- **FR-066**: H-03과 E-03의 assertion 결과는 각각 `PASS`, `FAIL`, `INCONCLUSIVE` 중 하나와 설명을
  가져야 한다.
- **FR-067**: 각 Run의 시나리오 결과는 `PASS`, `FAIL`, `INCONCLUSIVE` 중 하나여야 하며 실행 전에는
  `NOT_RUN`일 수 있다.
- **FR-068**: 모든 필수 assertion이 PASS이고 필수 증적이 완전하며 환경 복구가 성공했을 때만 해당
  시나리오 결과를 PASS로 판정해야 한다.
- **FR-069**: 필수 보호조치 위반이나 확인 가능한 누락·중복이 하나라도 직접 관찰되면 해당 시나리오를
  FAIL로 판정하고 다른 증적 공백도 함께 표시해야 한다.
- **FR-070**: 직접 관찰된 FAIL 없이 필수 사실을 평가할 수 없으면 해당 시나리오를 INCONCLUSIVE로
  판정해야 한다.
- **FR-071**: 판정 불가 reason code는 Constitution에서 정한 `NO_TEST_TARGET`, `ACCESS_LIMITED`,
  `INSUFFICIENT_EVIDENCE`, `EVIDENCE_CONFLICT`만 사용해야 한다.
- **FR-072**: 장애가 한 번이라도 적용된 Run은 종료·중단 여부와 관계없이 장애 해제와 환경 안전성
  복구를 시도해야 한다.
- **FR-073**: 복구 실패 시 Run은 `RESTORE_FAILED`, 시나리오 결과는 INCONCLUSIVE가 되며 수동 확인 전
  같은 대상의 후속 장애 Run을 차단해야 한다.
- **FR-074**: 복구 실패 전에 직접 관찰된 위험은 finding으로 보존하고 숨겨서는 안 된다.
- **FR-075**: 완료된 Run의 재시험은 새 Run으로 만들고 부모 Run, 시나리오·장애 의미·대상 버전·초기
  상태의 같음과 차이를 표시해야 한다.
- **FR-076**: 재시험은 부모 Run의 판정·관찰·증적 또는 manifest를 수정하거나 삭제해서는 안 된다.
- **FR-077**: H-03 결과 설명에는 실패 노출, 결정 경로별 안전성, 실패 건 보존 위치와 미검증 경로가
  포함돼야 한다.
- **FR-078**: E-03 결과 설명에는 장애 경계, 전달 시도 수, 최종 실패 위치, 누락·중복 업무 효과와
  사람 결정 이력 검증 범위가 포함돼야 한다.
- **FR-079**: ControlProof 구현 완료 상태는 WhyYou의 H-03·E-03 verdict와 분리해야 한다.
- **FR-080**: 최초 실제 실행에서 FAIL이 나오면 수정 전에 Run과 증적을 봉인해야 하며 수정 후 PASS만
  남겨서는 안 된다.
- **FR-096**: 세 최초 실제 Run 중 직접 관찰된 FAIL이 하나라도 있으면 Spec 002 완료 처리 전에 그중
  최소 한 건을 증적에 근거해 대상에서 수정하고 원 FAIL을 부모로 지정한 새 PASS Run으로 재시험해야
  한다. 세 Run이 모두 PASS인 경우에는 결함을 인위적으로 만들지 않고, 프로젝트의 기존 대표
  FAIL→수정→PASS 계보를 검증해 연결해야 한다. 새 제품 상태·API·UI 설계가 필요한 유일한 FAIL을
  단순 `DEFERRED`로 남긴 채 Spec 002를 완료 처리해서는 안 된다.

### Required Assertions

#### H-03 전체 판정

Spec 002의 H-03 전체 판정은 Spec 001의 H03-A1~H03-A6과 아래 확장 assertion을 모두 사용한다.
기존 assertion의 의미와 필수 증적은 Spec 001을 기준으로 한다.

| Assertion ID | 확인할 사실 | PASS 조건 | FAIL 조건 | 필수 증적 |
|---|---|---|---|---|
| H03-A7 | operation 2개에서 파생된 canonical path ID 3개가 리포트 부재를 우회하지 못함 | `FINAL_DECISION`, `BATCH_MOVE_FINAL_ACCEPT`, `BATCH_MOVE_FINAL_REJECT`가 모두 거부되고 부분 변경 0건 | 한 path라도 수락되거나 결정·단계·지원 건에 부분 변경 발생 | operation/path 목록, path별 요청·응답, 전후 상태 |
| H03-A8 | 재시도 소진 뒤 실패 건이 LocalStack DLQ에 보존됨 | 실제 재시도 한도 도달과 `iep-reporting-dlq`의 원 사건 연결 기록 확인 | 조회는 정상이나 DLQ 실패 건이 없거나 원 사건과 연결 불가 | redrive 설정 snapshot, 시도 시계열, DLQ record |
| H03-A9 | 최종 실패가 담당자와 운영자에게 숨겨지지 않음 | 담당자 상태가 최종 실패를 처리 중·준비 완료와 구분하고 운영 기록에서 원인·대상 추적 가능 | 담당자가 오인하거나 운영 기록에서 실패 건을 추적할 수 없음 | 담당자 표시, 상태 조회, 운영 실패 기록 |

H03-A7~A9 가운데 하나라도 실행기에서 빠지면 확장 H-03은 PASS가 될 수 없다. 대상 기능은 있지만
실행 수단이 준비되지 않은 경우 `RUNNER_NOT_READY`, 실행 중 접근이 제한되거나 증적이 부족한 경우
해당 사유의 INCONCLUSIVE로 구분한다.

#### E-03 판정

| Assertion ID | 확인할 사실 | PASS 조건 | FAIL 조건 | 필수 증적 |
|---|---|---|---|---|
| E03-A1 | 원 사건부터 최종 결과까지 처리 계보가 완전함 | 원 업무 사건·Outbox·메시지·모든 시도·최종 효과 연결 가능 | 조회는 정상이나 필수 연결이나 처리 시도 기록 누락 | 기준선, lineage map, 시도 시계열 |
| E03-A2 | 재시도 소진과 최종 실패 전이가 설명 가능함 | 설정된 한도, 실제 시도 수, 마지막 오류와 실패 경로가 일치 | 시도 수·상태·실패 원인이 불일치하거나 실패 건 유실 | 설정 snapshot, 시도별 결과, 최종 실패 기록 |
| E03-A3 | 저장 전 장애에서 미완료 효과가 생기지 않음 | 장애 중 report·projection·`processed_messages`가 모두 없음 | 장애 중 하나 이상의 완료 효과가 부분 생성됨 | 장애 경계 receipt, report·projection·처리 표식 조회 |
| E03-A4 | 저장 전 장애 복구 후 reporting 효과가 누락·중복되지 않음 | report 1건, 일관된 projection 집합, 처리 표식 1건과 원 Outbox 연결 | 필수 효과 누락·중복 또는 projection 불일치 | 복구·재처리 기록, 효과별 전후 비교 |
| E03-A5 | DB commit 후·ack 전 재전달이 handler를 재실행하지 않음 | 장애 경계 확인, 논리 report 1건 유지, duplicate-ack 확인 | report 중복 또는 handler 재실행 | transaction commit·ack 경계 증적, 재전달 기록, report 목록 |
| E03-A6 | 저장 후 재전달의 reporting 효과가 정확함 | report 1건, 일관된 projection 집합, 처리 표식 1건, 원 Outbox 보존 | 필수 효과 누락·중복, projection 불일치 또는 원 사건 단절 | report·projection·처리 표식·Outbox 전후 비교 |
| E03-A7 | 사람 결정과 관련 이력이 정확히 한 번임 | 동일 `Idempotency-Key` 재전송 후 단계 배정·HumanReview·감사가 각각 1건이고 invitation은 `reviewed` | 하나라도 누락·중복되거나 invitation 상태 모순 | 결정 요청·응답, 단계·invitation·HumanReview·감사 전후 비교 |
| E03-A8 | 장애 해제와 환경 안전성 복구 | 주입 조건 비활성, worker 정상, 후속 Run에 안전함 | 해당 없음. 확인 실패는 전체 결과를 판정 불가로 전환 | 장애 해제, worker 상태, 잔여 조건 검사 |

E03-A3·A4는 `BEFORE_RESULT_DURABLE` Run, E03-A5·A6은
`AFTER_RESULT_DURABLE_BEFORE_COMPLETION` Run에서 각각 평가한다. 한 Run에서 두 장애 경계를
동시에 만족한 것으로 처리하지 않는다. E03-A7은 리포트 복구가 확인된 뒤 수행한다.

### Key Entities

- **Fault Variant**: 재현하려는 장애의 의미적 경계다. Spec 002는 결과 내구 저장 전과 결과 내구
  저장 후·처리 완료 확인 전을 구분한다.
- **Processing Lineage**: 원 업무 사건에서 Outbox 이벤트, 메시지·작업, 각 전달 시도, 최종 실패,
  복구·재처리와 최종 업무 효과까지의 연결 관계다.
- **Delivery Attempt**: 같은 원 메시지를 worker가 처리하려 한 한 번의 시도다. 시도 번호, 시각,
  결과, 오류와 다음 상태를 가진다.
- **Terminal Failure Route**: 재시도 소진 뒤 실패 건이 보존되는 대상의 실제 경로다. 공식
  `whyyou-local` target에서는 LocalStack `iep-reporting-dlq` 하나이며 종류는
  `INFRASTRUCTURE_DLQ`다. reporting 애플리케이션 DLQ는 존재하지 않는다.
- **Terminal Failure Record**: 원 사건, 메시지·작업, 마지막 시도와 실패 원인을 연결하는 최종 실패
  기록이다.
- **Logical Operation**: 재전송 전후에도 동일한 업무 의도를 가리키는 리포트 생성 또는 사람 결정
  요청이다. 기술적인 키 형식은 Plan에서 정하되 대상·행위·논리 식별자가 같아야 한다.
- **Business Effect**: report, assistant retrieval projection, 처리 표식, 단계 배정, invitation 상태,
  HumanReview, 감사와 원 Outbox처럼 사용자와 업무 흐름에 남는 결과다.
- **Required Effect Set**: 현재 WhyYou source commit을 기준으로 E-03이 정확한 누락·중복을 판정할
  효과 목록이다. reporting과 사람 결정 집합을 분리하며 대상이 만들지 않는 completion Outbox
  이벤트를 임의로 추가하지 않는다.
- **Decision Path Capability**: 대상 버전에서 최종 채용 효과를 직접 또는 간접으로 만들 수 있는
  문서화된 쓰기 경로와 그 효과다. 공식 `whyyou-local` target에서는
  `recordHumanFinalDecision`과 목표가 `최종합격`·`불합격`인 `moveApplicantsToRecruitingStage`다.
- **Scenario Judgement**: 한 Run의 H-03 또는 E-03 assertion을 종합한 독립 verdict와 설명이다.
- **Target Environment Snapshot**: Run이 실제로 실행된 환경의 target ID, 환경 종류, 소스 commit,
  로컬 구성요소 버전과 메시지 설정을 동결한 기록이다. 다른 환경에 verdict를 재사용하지 못하게 한다.

### Fault Variant Semantics

| 값 | 의미 | 유효성 확인 |
|---|---|---|
| `BEFORE_RESULT_DURABLE` | worker가 원 메시지를 받았지만 유효 리포트가 내구 저장되기 전에 실패 | 장애 시점에 유효 리포트·완료 효과가 없음 |
| `AFTER_RESULT_DURABLE_BEFORE_COMPLETION` | report·assistant retrieval projection·`processed_messages` 표식의 DB transaction이 commit됐지만 SQS message acknowledge 전에 실패 | 같은 transaction의 세 효과 존재, acknowledge 미수행, 재전달의 duplicate-ack가 같은 event에서 확인됨 |

장애 주입 명령이 성공했다는 기록만으로 경계 도달을 인정하지 않는다. 위 유효성 사실을 직접
관찰하지 못하면 해당 Run은 INCONCLUSIVE다.

### Required Evidence Set

| Evidence ID | 내용 | 최소 연결 정보 | 주요 판정 |
|---|---|---|---|
| EV2-01 | 대상 버전·실행환경과 reporting 재시도·최종 실패·결정 경로 capability snapshot | Run, `whyyou-local`, `LOCAL_EMULATED`, source commit, 구성요소 버전, target digest, queue·DLQ 설정 출처, 수집 시각 | readiness, 환경 주장 경계, H03-A7~A9, E03-A2 |
| EV2-02 | 원 업무 사건과 장애 전 리포트·상태·결정·이벤트 기준선 | Run, subject, `BASELINE`, 원 사건 ID | 전체 |
| EV2-03 | 장애 적용 요청과 실제 경계 발동 receipt | Run, subject, fault variant, step, attempt | 시험 유효성, E03-A3/A5 |
| EV2-04 | 각 전달 시도의 시각·번호·오류·결과 시계열 | Run, subject, 원 메시지, attempt | H03-A8, E03-A1/A2 |
| EV2-05 | 재시도 소진 뒤 최종 실패 기록 | Run, subject, 원 사건, route 종류·locator, 마지막 attempt | H03-A8/A9, E03-A2 |
| EV2-06 | 최종 실패 시 담당자 표시와 상태 조회 결과 | Run, subject, `INJECTED`, capture context | H03-A9 |
| EV2-07 | 정상·대체 결정 경로별 요청·응답 | Run, subject, actor, path capability, logical operation | H03-A7 |
| EV2-08 | 결정 시도 뒤 HumanReview·채용 단계·지원 건·자동결정 상태 | Run, subject, `INJECTED`, path capability | H03-A7 및 기존 A4/A5 |
| EV2-09 | 장애 해제, worker 안전 상태와 재처리 요청·결과 | Run, subject, `RECOVERED`, logical operation | E03-A4/A6/A8 |
| EV2-10 | 복구 후 report·assistant retrieval projection·`processed_messages`와 원 Outbox 식별자·논리 건수 | Run, subject, 원 event, report ID, projection IDs, processed key | E03-A4~A6 |
| EV2-11 | 동일 `Idempotency-Key`의 사람 결정 최초·재전송과 단계·invitation·HumanReview·감사 비교 | Run, subject, actor, logical decision ID | E03-A7 |
| EV2-12 | scenario·fault variant·target·fixture snapshot과 봉인 manifest | Run, 각 digest, parent Run | 재현·무결성·재시험 |

필수 8종 사실은 V4의 E-03 정의를 유지한다. 위 증적은 그 사실을 판정 가능한 단위로 나눈 것이며,
한 파일이나 한 로그 행에 모두 존재할 필요는 없다. 각 artifact는 판정에 필요한 최소 범위만 저장한다.

### Resolved Specification Decisions

| ID | 결정 | 이유와 영향 |
|---|---|---|
| SD-002-01 | H-03 Run과 E-03 Run은 별도다. | “한 Run은 한 시나리오”라는 공통 계약을 지키고 한쪽 PASS가 다른 쪽 실패를 가리지 않게 한다. 동일 조건을 쓰더라도 각자 snapshot과 verdict를 가진다. |
| SD-002-02 | reporting의 최종 실패 경로는 capability로 발견한다. | 현재 대상이 애플리케이션 DLQ와 인프라 DLQ를 모두 쓴다고 가정하지 않는다. 실제 구성된 경로는 모두 검증하되 존재하지 않는 경로를 억지로 신규 구현하거나 FAIL 사유로 삼지 않는다. |
| SD-002-03 | “정확히 한 번”은 처리 시도 1회를 뜻하지 않는다. | 메시지는 여러 번 전달될 수 있다. 리포트·상태·이벤트·사람 결정 같은 논리적 업무 효과가 각각 1건인지 판정한다. |
| SD-002-04 | 두 저장 경계는 별도 E-03 Run으로 시험한다. | 두 장애를 한 Run에 섞으면 어느 경계에서 누락·중복이 생겼는지 설명하기 어렵고 복구 조건도 오염된다. |
| SD-002-05 | H-03은 결정 안전성, E-03은 이력·멱등성을 소유한다. | 동일 증적을 참조할 수 있지만 assertion과 verdict는 중복 정의하지 않는다. H-03 PASS로 E-03을 대신할 수 없다. |
| SD-002-06 | 웹 결과 화면 사용성은 이 Spec의 완료 조건이 아니다. | Spec 002는 판정 가능한 데이터와 설명 계약까지 만든다. 사람이 실제 웹 결과를 검토하는 시험은 워크벤치·보고서 Spec에서 수행한다. |
| SD-002-07 | 2주 MVP의 공식 대상은 `whyyou-local` 하나다. | WhyYou AWS 리소스가 내려간 현재 상태에서 재현 가능한 Docker/LocalStack 환경으로 제품 한 사이클을 검증한다. AWS 운영환경은 `NOT_RUN`이며 향후 새 Run 없이는 검증됐다고 주장하지 않는다. |
| SD-002-08 | reporting의 공식 최종 실패 경로는 LocalStack `iep-reporting-dlq`다. | 현재 WhyYou reporting worker에는 애플리케이션 `JobStatus.DLQ`가 없고 queue redrive 정책이 최종 실패를 보존한다. 없는 애플리케이션 상태를 구현하거나 FAIL 조건으로 만들지 않는다. |
| SD-002-09 | 저장 후 장애 경계는 DB commit 후·SQS acknowledge 전이다. | WhyYou worker는 handler 결과와 `processed_messages` 표식을 commit한 뒤 queue message를 acknowledge한다. 이 사이를 시험해야 실제 at-least-once 재전달과 중복 억제를 검증할 수 있다. |
| SD-002-10 | H-03은 API operation 2개에서 파생되는 canonical path ID 3개를 시험한다. | `recordHumanFinalDecision`은 `FINAL_DECISION` 한 case이고, `moveApplicantsToRecruitingStage`는 `최종합격`·`불합격` 목표별 두 case다. 같은 operation의 다른 의미를 합치지 않되 일반 중간 단계 이동까지 무제한 확장하지 않는다. |
| SD-002-11 | E-03의 필수 업무 효과를 현재 WhyYou 코드에 맞춰 열거한다. | reporting은 report·assistant projection·processed marker·원 Outbox, 사람 결정은 단계·invitation·HumanReview·감사다. 존재하지 않는 completion Outbox를 요구하면 정상 구현도 거짓 FAIL이 되므로 제외한다. |

---

### Scope Boundaries

#### Included

- `whyyou-local`의 PostgreSQL·LocalStack·Mailpit 컨테이너와 호스트 API·worker·회사 화면
- ControlProof 고정 모델 대역을 사용한 외부 AI 호출 없는 결정론적 실행
- LocalStack SQS와 reporting DLQ의 재시도·redrive 계약
- 실행환경 snapshot과 AWS 미검증 범위 표시
- Spec 001 실행·증적 계약의 재사용
- reporting 재시도 설정과 실제 전달 시도 관찰
- 재시도 한도 소진
- 대상에 실제 구성된 최종 실패 경로와 원 사건 연결
- 담당자 실패 표시와 운영 추적 가능성
- 정상 최종결정 경로와 채용 확정 효과가 있는 문서화된 대체 경로
- 결과 내구 저장 전 장애
- 결과 내구 저장 후·처리 완료 확인 전 장애
- 장애 복구와 동일 논리 요청 재처리
- report·assistant retrieval projection·`processed_messages`·원 Outbox의 누락·중복·일관성 판정
- 복구 후 단계 배정·invitation·HumanReview·감사의 누락·중복 판정
- H-03과 E-03 독립 verdict
- 증적 최소 수집·마스킹·SHA-256·manifest 봉인
- 최초 Run 보존과 별도 재시험 계보

#### Excluded and Deferred

- 실제 AWS staging·production 배포와 해당 환경의 시나리오 실행
- AWS SQS·ECS·IAM·CloudWatch·운영 네트워크·가용성 검증
- 로컬 결과를 AWS 배포환경 PASS로 승격하는 행위
- reporting 외 분석·미디어·삭제·capacity worker의 DLQ 시험
- 운영 환경 장애 주입
- 실제 지원자 또는 실제 채용 결정 사용
- 무작위 chaos, 장시간 부하, 동시성·성능 한계 시험
- 모든 클라우드와 메시지 제품에 대한 범용 DLQ 구현
- DLQ 운영자가 직접 재처리하는 별도 관리 화면 신규 구현
- ControlProof 웹 워크벤치와 시각 디자인
- 웹 결과 화면의 사람 사용성 시험
- N-01~N-03, H-01~H-02, E-01~E-02 실행
- A-01~A-03 기능 신규 구현
- 법적 준수 전체, 모델 정확도 또는 편향 인증

이 기능은 WhyYou의 현재 reporting 실패 경로를 검증한다. 대상에 없는 애플리케이션 DLQ나 운영
대시보드를 Spec 통과 목적으로 새로 만드는 것은 범위가 아니다. 반대로 대상에 이미 존재하는 경로가
관찰되지 않는다면 이를 숨기지 않고 readiness 또는 verdict에 반영한다.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 준비된 격리 시험환경에서 실행 담당자는 수동 데이터 수정 없이 재시도 소진 → 최종 실패
  확인 → 복구·재처리까지 한 변형을 10분 안에 완료하고 결과와 복구 상태를 확인할 수 있다.
- **SC-002**: 재시도 한도 불일치, 실패 건 유실, 원 사건 연결 단절 fixture의 100%가 해당 H-03 또는
  E-03 FAIL로 탐지되고 PASS로 표시되는 경우는 0건이다.
- **SC-003**: H-03 PASS Run의 100%가 대상 버전에 등록된 모든 채용 확정 가능 경로의 거부와
  결정·HumanReview·단계·지원 건 부분 변경 0건을 증명한다.
- **SC-004**: `BEFORE_RESULT_DURABLE` 정상 복구 fixture의 100%에서 report 1건, 해당 report와 일관된
  assistant retrieval projection 집합, `processed_messages` 표식 1건과 원 Outbox 연결이 확인되며,
  누락·중복·불일치 fixture의 100%가 E-03 FAIL로 탐지된다.
- **SC-005**: `AFTER_RESULT_DURABLE_BEFORE_COMPLETION` 정상 복구 fixture의 100%에서 재전달 횟수와
  관계없이 report 1건, 일관된 projection 집합, 처리 표식 1건과 duplicate-ack가 확인된다.
- **SC-006**: 같은 `Idempotency-Key`의 사람 결정 요청을 두 번 전송한 정상 fixture의 100%에서 단계
  배정·HumanReview·`final_decision.create` 감사 효과가 각각 정확히 1건이고 invitation은 `reviewed`다.
- **SC-007**: H-03만 실패, E-03만 실패, 한쪽 증적 부족, 양쪽 PASS fixture에서 두 시나리오 verdict가
  서로 독립적으로 기대 결과와 100% 일치한다.
- **SC-008**: PASS로 표시된 모든 H-03·E-03 Run은 해당 필수 assertion과 증적을 100% 연결하며,
  필수 증적이 하나라도 없거나 무결성 검증에 실패하면 PASS가 0건이다.
- **SC-009**: 장애가 적용된 Run의 100%에서 복구가 시도되고, 복구 실패 fixture의 100%가
  `RESTORE_FAILED`와 후속 장애 Run 차단으로 나타난다.
- **SC-010**: 재시험 뒤 부모 Run의 판정·관찰·증적·manifest 변경 건수는 0건이며 자식 Run의 부모 관계와
  대상 버전 차이를 100% 확인할 수 있다.
- **SC-011**: 전체 자동 시험과 실제 데모에서 실제 지원자 개인정보와 운영 채용 결정 사용 건수는 0건이다.
- **SC-012**: 결과 설명의 100%가 실제 최종 실패 위치, 검증한 결정 경로, 누락·중복 업무 효과와
  미검증 범위를 구분하고 법적 준수 전체를 보증한다고 표현하지 않는다.
- **SC-013**: Spec 002 Run의 100%가 target을 `whyyou-local`, 환경을 `LOCAL_EMULATED`, AWS 배포환경을
  `NOT_RUN`으로 표시하며 실제 소스 commit과 LocalStack queue·DLQ 설정을 증적으로 연결한다.
- **SC-014**: 로컬 PASS 결과 가운데 실제 AWS SQS·ECS·IAM·CloudWatch·운영환경까지 검증했다고
  표현하거나 클라우드 환경 결과로 재사용되는 건수는 0건이다.
- **SC-015**: Spec 002 완료 기록에는 최소 한 쌍의 검증된 부모 FAIL→자식 PASS bundle과 변경 근거가
  존재한다. 세 최초 실제 Run이 모두 PASS라면 새 결함을 만들지 않고 기존 승인된 대표 FAIL→PASS
  bundle 쌍의 무결성과 적용 가능성을 다시 검증한 참조가 존재한다.

---

## Assumptions

- Spec 001의 실행·증적·복구·재시험 기반과 WhyYou H-03 보호조치 보완 커밋을 기준선으로 사용한다.
- WhyYou의 기존 AWS 리소스는 현재 내려가 있으며 Spec 002 기간에 다시 배포하지 않는다.
- 공식 실행환경은 Docker Desktop에서 PostgreSQL·LocalStack·Mailpit을 실행하고 WhyYou API·worker·
  회사 화면을 호스트에서 실행하는 단일 개발자 장비다.
- WhyYou reporting은 `iep-reporting` queue와 LocalStack `iep-reporting-dlq`의 redrive 정책을
  사용한다. submission analysis에 있는 `JobStatus.DLQ`는 reporting 흐름의 상태가 아니다.
- 로컬 환경에서 재시도 대기 시간을 데모에 적합하게 단축할 수 있지만,
  시도 수와 상태 의미는 대상 계약과 같아야 한다.
- 결과 내구 저장 전·후 장애는 Run과 합성 subject로 범위가 제한된 test-only 조건으로 만들 수 있다.
- 현재 source commit의 최종 채용 효과 경로는 `recordHumanFinalDecision`과 목표가 `최종합격` 또는
  `불합격`인 `moveApplicantsToRecruitingStage`다.
- 같은 논리 요청 여부를 판별할 안정적인 식별 정보가 존재하거나 test-only 입력으로 제공될 수 있다.
- 사람이 기록하는 최종결정은 권한 있는 합성 회사 사용자만 수행하며 결정 내용은 테스트 fixture가
  지정하되 AI 점수 임계값에서 파생하지 않는다.
- reporting 필수 효과는 report·assistant retrieval projection·`processed_messages`·원 Outbox로,
  사람 결정 필수 효과는 단계 배정·invitation·HumanReview·감사로 확정한다.
- 증적 보존 기간과 외부 반출 정책은 MVP 이후 운영 정책에서 정한다. 이번 기능은 실행·재시험·팀 검토
  기간 동안 원본을 사용할 수 있어야 한다.

## Dependencies

- 완료된 Spec 001과 `001-execution-evidence-h03`의 공통 실행·증적 계약
- WhyYou 전용 검증 브랜치와 정확한 대상 commit 식별 정보
- Docker Desktop에서 실행 가능한 PostgreSQL·LocalStack·Mailpit과 WhyYou 로컬 실행환경
- 합성 지원자·회사 사용자·리포트 생성 대기 상태를 만드는 격리된 상태 seed
- 고정 AI 결과 fixture
- reporting 재시도 설정과 원 메시지·처리 시도를 읽을 수 있는 허용된 경로
- 대상에 실제 구성된 최종 실패 경로를 관찰할 수 있는 권한
- 결과 내구 저장 전·후에 적용 가능한 test-only 장애 조건과 강제 해제 수단
- `recordHumanFinalDecision`과 최종 단계 대상 `moveApplicantsToRecruitingStage` 실행·관찰 경로
- report·assistant retrieval projection·`processed_messages`·원 Outbox와 단계 배정·invitation·
  HumanReview·감사를 읽을 수 있는 증적 경로
- ControlProof Run·증적 저장소와 Spec 001 무결성 검증 기능

## Risks and Product Responses

| 위험 | 제품 차원의 대응 |
|---|---|
| submission analysis의 `JobStatus.DLQ`를 reporting 경로로 오인 | reporting은 LocalStack `iep-reporting-dlq`만 적용하고 애플리케이션 DLQ는 `NOT_APPLICABLE`로 기록 |
| 재시도 명령 성공만 보고 한도 소진을 가정 | 설정 snapshot과 시도별 실제 시계열 및 최종 실패 기록을 함께 요구 |
| DLQ 메시지는 있지만 원 사건과 연결되지 않음 | subject·원 사건·Outbox·메시지·attempt 연결이 없으면 FAIL |
| 정상 결정 API만 막고 단계 이동으로 우회 | 채용 확정 효과를 가진 모든 문서화된 경로를 readiness와 assertion에 포함 |
| 여러 전달 시도를 중복 업무 결과로 오판 | 처리 attempt와 logical business effect를 분리해 건수 비교 |
| 저장 전·후 장애 의미가 실제로 만들어지지 않음 | 장애 명령이 아닌 내구 결과와 처리 완료 상태로 경계 도달을 확인, 미확인 시 INCONCLUSIVE |
| 복구 후 report는 하나지만 projection이나 처리 표식이 중복·불일치 | report ID·projection ID·processed key와 원 Outbox를 독립 비교 |
| 결정 재전송이 별개의 사람 결정으로 기록됨 | 같은 `Idempotency-Key`의 단계·invitation·HumanReview·감사를 함께 비교하고 현재 구현 결함은 최초 FAIL로 보존 |
| 존재하지 않는 completion Outbox를 필수로 가정 | 현재 source commit의 실제 효과 집합만 요구하고 별도 completion event는 비적용으로 명시 |
| H-03 PASS가 E-03 결함을 가림 | 별도 Run·assertion·verdict 유지 |
| 테스트 장애가 다른 지원자나 후속 Run에 남음 | Run·subject allowlist, 의무 복구, 실패 시 후속 장애 Run 차단 |
| 증적 수집이 개인정보·비밀값을 과수집 | 최소 추출물, 저장 전 마스킹, 전체 로그·DB 덤프 금지 |
| Spec 002가 웹 UI 완료로 오해됨 | 구조화된 결과 계약까지만 포함하고 웹 결과 화면·사람 UX 검토는 후속 Spec으로 명시 |
| LocalStack 결과가 실제 AWS 검증으로 오해됨 | 모든 Run과 결과에 `whyyou-local`·`LOCAL_EMULATED`·AWS `NOT_RUN`과 미검증 서비스를 표시 |
| 로컬에서 외부 GCP·AWS AI를 실수로 호출 | 고정 모델 대역의 활성화·fixture digest를 readiness 필수조건으로 두고 외부 AI 호출 0건을 증명 |
| 향후 배포 뒤 로컬 PASS가 그대로 재사용됨 | 배포환경마다 새 target snapshot과 새 Run을 요구하고 환경 간 verdict 승격을 금지 |

## Traceability

| Product source | 이 Spec의 반영 위치 |
|---|---|
| V4 10.6 H-03 | User Story 1~2, FR-021~FR-040, H03-A7~A9 |
| V4 10.12 E-03 | User Story 3~5, FR-041~FR-055, E03-A1~A8 |
| V4 12.1~12.4 | Scope Boundaries, Required Evidence Set, Success Criteria |
| V4 14.2 데모 | User Story 6, FR-075~FR-080, SC-007·SC-010 |
| Product Brief 8.1~8.2 | Feature Goal, Spec 001과의 관계, H-03/E-03 독립 판정 |
| Product Brief 9.1~9.4 | FR-001~FR-020, FR-056~FR-080 |
| Decision D-001~D-003 | FR-001~FR-006, 처리 계보와 충돌 규칙 |
| Decision D-006 | FR-072~FR-074, E03-A8 |
| Decision D-008 | 재시도 소진·DLQ·우회 경로 Included 범위 |
| Decision D-009 | SD-002-01·03·05, H-03/E-03 assertion 분리 |
| Decision D-011 | FR-011~FR-020 readiness와 구현 상태 분리 |
| Decision D-012 | SD-002-06, 웹 결과 화면 사람 검토 후속 이관 |
| Constitution VI 필수 품질 게이트 | FR-096, SC-015, 최초 FAIL→수정→PASS 완료 조건 |
| 2026-09-28 환경 clarification | FR-081~FR-087, SD-002-07, SC-013~SC-014, Target Environment Snapshot |
| 2026-09-28 target contract clarification | FR-088~FR-095, SD-002-08~11, H03-A7~A8, E03-A3~A7 |
| Constitution I·II·V·VI·VII | 증적 기반 판정, readiness, 격리·복구, 불변 재시험, 추적성 |

## Planning Gate

기술 Plan은 다음 사항을 확인한 뒤 작성해야 한다.

- `whyyou-local` 환경 snapshot과 AWS `NOT_RUN`·미검증 범위를 결과 계약에 어떻게 고정할 것인가
- 고정 모델 대역 외 외부 AWS·GCP AI 호출이 0건임을 어떻게 사전 차단하고 증명할 것인가
- LocalStack `iep-reporting`의 redrive 한도 소진과 `iep-reporting-dlq` 이동을 어떤 observer로
  확인하고 원 사건과 연결할 것인가
- 로컬 시험에서 재시도 한도를 안전하게 소진시키고 실제 시도 수를 어떻게 관찰할 수 있는가
- report·assistant retrieval projection·`processed_messages` commit 후 SQS acknowledge 전 장애 hook을
  어떻게 만들고 실제 경계 도달을 독립적으로 관찰할 것인가
- `recordHumanFinalDecision`과 최종 단계 대상 `moveApplicantsToRecruitingStage`를 같은 보호
  원칙으로 어떻게 호출하고 전후 효과를 비교할 것인가
- report·assistant retrieval projection·`processed_messages`·원 Outbox와 단계 배정·invitation·
  HumanReview·감사를 어떤 식별자로 읽고 논리 건수를 비교할 것인가
- E03-A3~A6의 두 변형을 서로 오염되지 않는 별도 Run으로 실행하고 복구할 수 있는가
- 공유 증적을 참조할 때 원본 Run과 digest를 보존할 수 있는가
- 필수 12종 증적을 전체 로그·DB 덤프 없이 최소 수집할 수 있는가
- 모든 구현 task를 FR, H03-A 또는 E03-A ID와 테스트에 연결할 수 있는가
- Spec 001의 기존 PASS/FAIL/INCONCLUSIVE·복구·무결성 계약을 깨뜨리지 않는가
