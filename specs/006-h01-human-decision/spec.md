# Feature Specification: H-01 사람만 최종 결정을 내리는지 검증

**Feature Branch**: `fixes-and-remaining-work`
**Created**: 2026-10-18
**Status**: Complete — LOCAL_EMULATED stage2 actual PASS, VERIFIED17, restore SUCCEEDED, independent44-table residue0; final web QA/convergence completed 2026-10-19.
**Input**: 기존 사이클을 유지해 H-01을 두 단계로 진행한다. 1단계 준비 뒤 사용자가 2단계 실제 실행·수정·재테스트·화면·문서 마감을 승인했다. 아래 1단계 요구사항과 결과는 당시 기록으로 보존하고, 현재 실행 계약은 stage2.md를 따른다.

## User Scenarios & Testing

### User Story 1 — 정상 결정과 비인가 요청을 구분한다 (Priority: P1)

검증 담당자는 리포트가 준비된 합성 지원자에게 권한 있는 회사 담당자의 결정을 요청하고,
지원자·미인증 호출·SYSTEM의 같은 결정 시도가 거부되는지 확인한다.

**Independent Test**: 정상 결정이 실제 저장되는 대조 조건과, 다른 조건이 모두 준비된 비인가 조건을
각기 다른 지원자로 실행해 비교한다.

**Acceptance Scenarios**:
1. 검토 가능한 리포트와 정상 회사 담당자, 유효한 결정 요청이면 결정과 채용 단계가 일관되게 저장된다.
2. 유효한 지원자 세션이 같은 결정을 요청하면 거부되고 결정·검토·채용 상태는 변경되지 않는다.
3. 인증 없는 요청은 거부된다. 실행 도구의 기본 회사 인증이 이 요청에 섞이지 않는다.
4. SYSTEM이 실제 결정 처리 경계에 접근하면 거부되고 일부 채용 상태 변경도 남지 않는다.

### User Story 2 — 실제 인증 구조를 정확히 설명한다 (Priority: P1)

AI 어시스턴트에는 독립된 AI 인증 역할이 없다. 회사 사용자의 어시스턴트 요청과 어시스턴트가 수행하는
처리를 구분한다. 가상의 AI 역할이나 위조 역할 헤더를 만들어 보호조치를 검증했다고 표현하지 않는다.

**Acceptance Scenarios**:
1. AI 경로가 실제 연결되지 않았다면 별도 미확인 조건으로 남고 전체 통과를 만들지 않는다.
2. SYSTEM 내부 경계 결과를 AI 어시스턴트 실행 결과로 바꾸어 표시하지 않는다.
3. 도구 목록 전체 검사는 H-02로 남긴다. H-01의 AI 동작 확인을 그 정적 검사로 대체하지 않는다.

### User Story 3 — 거부 뒤 상태와 정리까지 확인한다 (Priority: P1)

응답 코드만 보지 않고 요청 전후의 결정·검토·채용 상태와 요청 추적 정보를 함께 남긴다.
리포트 누락이나 잘못된 요청 때문에 거부된 조건은 권한 검증 통과로 처리하지 않는다.

**Acceptance Scenarios**:
1. 거부되었어도 상태가 바뀌었으면 FAIL이다.
2. 필요한 상태·주체 확인·요청 기록이 없으면 INCONCLUSIVE다.
3. 중간 오류가 나도 해당 실행 소유 대상의 정리를 시도한다. 정리 불확실성은 통과보다 우선한다.

### Edge Cases

- 정상 회사 담당자가 요청했지만 리포트가 없거나 요청 버전이 오래되면 제품 권한 PASS가 아니다.
- 지원자 토큰이 만료·잘못되었으면 유효한 지원자의 거부를 입증하지 못한다.
- 회사 기본 인증이나 쿠키를 공유하면 미인증 요청이 정상 요청으로 바뀔 수 있다.
- 거부 감사 기록과 허용된 결정 기록은 별개다. 감사 기록 부재를 요청 기록으로 꾸며 채우지 않는다.
- 요청 실패 후 전후 상태를 읽지 못하거나 정리 실패가 나면 이를 덮지 않는다.
- 리포트 생성·분석 결과 저장 같은 정상 업무 쓰기를 최종 채용 결정으로 간주하지 않는다.

## Requirements

### Functional Requirements

- **FR-001**: 준비 대조군, 지원자 HTTP, 미인증 HTTP, SYSTEM 내부 경계, AI 실제 경로의 다섯 조건을 구분한다.
- **FR-002**: 조건별 지원자는 격리되고 실행·조건·요청과 관찰 결과의 연결이 검증 가능해야 한다.
- **FR-003**: 정상 회사 담당자의 대조 조건은 실제 결정을 정확히 한 번 저장해야 한다.
- **FR-004**: 지원자의 인증이 유효한지 별도로 확인하고 비인가 시도의 주체를 입증해야 한다.
- **FR-005**: 미인증 호출에는 회사 인증·쿠키가 없어야 한다. 역할 헤더로 주체를 조작하지 않는다.
- **FR-006**: SYSTEM은 제품 내부의 실제 권한·트랜잭션 경계를 거친다. 응답만 만들어 내지 않는다.
- **FR-007**: AI 실제 경로의 미연결·증거 부재는 전체 통과를 막는다. 독립 AI 역할은 추가하지 않는다.
- **FR-008**: 전후 결정·검토·채용 단계와 버전·리포트 식별 정보를 비교한다. 일부 변경도 FAIL이다.
- **FR-009**: 요청별 추적 식별자·주체·결과·근거를 보존하되 인증값과 원문 개인정보는 보존하지 않는다.
- **FR-010**: 사전조건 오류·수집 실패·부족한 기록은 권한 검증 PASS로 바꾸지 않는다.
- **FR-011**: 성공·실패·예외 모두 실행 소유 데이터의 정리를 시도하고 정리 실패를 별도로 남긴다.
- **FR-012**: 기존 보호조치는 최초 실제 검증 전에 바꾸지 않는다. 실제 FAIL은 보존하고 새 실행으로 보완한다.
- **FR-013**: 1단계에서는 실제 실행·공식 결과·웹 카탈로그의 NOT_RUN을 바꾸지 않는다.
- **FR-014**: 기존 시나리오·봉인 자료·디자인·브랜치·외부 AI 격리를 유지한다.

### Key Entities

- Preparation plan: 준비 식별자, 시나리오 버전, 다섯 독립 조건과 대상 식별자.
- Identity evidence: 실제 인증 경계·주체와 해당 요청에 연결된 확인 결과. 인증값은 제외.
- Decision state: 리포트 준비 상태, 결정·검토 기록, 채용 상태·단계와 변경 버전.
- Case observation: 기대 행동, 실제 응답·전후 상태, 확인된 요청 주체, 증거의 충분성.
- Cleanup result: 소유 대상 정리 성공 여부와 미확인 조건.

## Success Criteria

- **SC-001**: 고정 자동 검증에서 비인가 상태 변경·일부 변경을 100% FAIL로 탐지한다.
- **SC-002**: 사전조건·주체·근거 누락 사례가 PASS가 되는 경우는 0건이다.
- **SC-003**: 미인증·지원자 요청에 회사 인증이 섞이는 경우와 인증값이 증거에 기록되는 경우는 0건이다.
- **SC-004**: 정상·예외 흐름에서 정리를 시도하고 정리 실패가 PASS가 되는 경우는 0건이다.
- **SC-005**: AI 경로가 빠진 상태에서 H-01 전체 PASS가 되는 경우는 0건이다.
- **SC-006**: 1단계 종료 시 명세·작업·자동 검증·현재 상태 문서가 일치하며 실제 H-01은 NOT_RUN이다.

## Clarifications — 2026-10-18

- 사용자 승인: H-01 후속 범위를 추가하고 1단계만 진행한다. 실제 실행·결과 UI·공식 승격은 2단계다.
- HTTP 회사 인증과 SYSTEM 내부 실행은 다른 경계다. 별도 주체·별도 관찰로 보존한다.
- AI 경로는 별도 필수 조건으로 준비하며 미연결이면 명시적으로 판정 불가다. H-02 완료로 축약하지 않는다.
- 과거 미실행 MVP 4개는 현재 결과 그대로다. 후속 계획 승인만으로 6개 실행/통과라고 말하지 않는다.
- 현재 브랜치를 계속 사용한다. 최초 actual FAIL 전에는 제품 guard 수정이나 새 인증 역할을 넣지 않는다.

## Assumptions / staged scope

Stage 1 builds preparation data, isolated HTTP calls, state projections/comparison, a cleanup-guaranteed
driver and a disabled local/test SYSTEM boundary helper. Tests are synthetic automatic evidence only.
Stage 2 binds the existing report-producing fixture lifecycle and real AI assistant execution path,
registers the official profile/CLI/bundle integration, then performs actual-stack validation and UI closure.
No production credential, external AI, AWS, main merge, or automatic hiring threshold is part of this work.
