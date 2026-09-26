# Feature Specification: 실행·증적 기본 모델과 H-03 최소 수직 흐름

**Feature Branch**: `001-execution-evidence-h03` (계획 이름, 아직 브랜치 미생성)

**Created**: 2026-09-23

**Status**: Ready for Planning

**Input**: V4와 Product Brief를 기준으로, H-03 최소형을 통해 ControlProof의 실행·관찰·증적·판정·복구·재시험 기본 계약을 검증한다.

**Sources**:

- [2주 MVP 기능 범위 V4](../../docs/product/ControlProof_WhyYou_2주_MVP_기능범위_v4.md)
- [Product Brief](../../docs/product/ControlProof_MVP_Product_Brief.md)
- [MVP 결정 기록](../../docs/product/ControlProof_MVP_Decision_Log.md)
- [ControlProof Constitution](../../.specify/memory/constitution.md)

## User Scenarios & Testing *(mandatory)*

### Feature Goal

검증 실행 담당자가 합성 지원자 한 명을 대상으로 WhyYou의 reporting 처리 실패를 안전하게 주입하고, 담당자에게 리포트 부재 또는 실패가 드러나는지와 리포트 없이 최종 채용 결정을 확정할 수 없는지를 실제로 확인한다. ControlProof는 이 실행의 전후 상태, 장애 조건, 결정 시도, 복구 결과를 원본 증적과 연결해 `PASS`, `FAIL`, `INCONCLUSIVE` 중 하나로 설명해야 한다.

이 기능의 성공은 WhyYou가 반드시 PASS하는 것을 뜻하지 않는다. 실제 동작이 기대와 다르면 근거 있는 FAIL을 내는 것이 올바른 성공 결과다. 현재 상태의 FAIL은 보존하며, WhyYou 수정 후 재시험은 별도 Run으로 연결한다.

#### 이번 기능이 검증하는 통제 의도

사람의 최종 검토에 필요한 리포트가 만들어지지 않은 상태에서는 다음이 보장되어야 한다.

1. 리포트가 준비되지 않았다는 사실이 담당자에게 숨겨지지 않는다.
2. 권한 있는 사람이라도 리포트 없이 최종 채용 결정을 확정할 수 없다.
3. 거부된 결정 시도로 채용 상태나 결정 기록이 일부만 변경되지 않는다.
4. 시험 장애를 해제하고 시험 환경을 안전하게 복구할 수 있다.
5. ControlProof가 위 사실을 실행 당시의 증적으로 설명할 수 있다.

#### 성공과 대상 서비스 판정의 구분

- 기능 구현 성공: ControlProof가 실제 관찰 결과에 맞는 판정과 증적을 생성한다.
- H-03 `PASS`: WhyYou의 보호조치가 모든 필수 assertion을 만족한다.
- H-03 `FAIL`: 하나 이상의 보호조치 위반이 직접 관찰된다.
- H-03 `INCONCLUSIVE`: 직접 관찰된 위반은 없지만 필수 사실을 확인할 수 없다.
- `NOT_RUN`: 실제 Run이 만들어지지 않았다.

### User Story 1 - reporting 장애에서 결정 안전성을 실제 시험한다 (Priority: P1)

검증 실행 담당자는 실행 가능한 H-03 시나리오를 선택하고, 시험 목적·대상·장애 조건·복구 방법을 확인한 뒤 시험을 시작한다. ControlProof는 합성 지원자를 준비하고 정상 기준선을 기록한 다음 reporting 경로에 장애를 적용한다. 리포트가 준비되지 않은 상태에서 담당자 표시와 사람의 최종결정 시도를 관찰하고, 장애를 해제해 복구 결과까지 남긴다.

**Why this priority**: 장애 주입, 관찰, 판정, 증적, 복구를 한 번에 관통하는 최소 제품 가치다. 이 흐름 없이 데이터 모델이나 화면만 구현하면 ControlProof가 능동 검증 제품이라는 주장을 증명할 수 없다.

**Independent Test**: 실제 개인정보가 없는 격리 환경에서 합성 지원자 한 명과 회사 사용자 한 명을 준비한다. 한 종류의 reporting 장애를 적용한 뒤 리포트 상태와 최종결정 시도의 결과, 상태 부작용, 복구 기록이 하나의 Run으로 남는지 확인하면 독립적으로 시험할 수 있다.

**Acceptance Scenarios**:

1. **Given** H-03 대상 기능과 실행·관찰·복구 수단이 준비되어 있고 합성 지원자가 리포트 생성 대기 상태일 때, **When** 실행 담당자가 시험을 시작하면, **Then** ControlProof는 고유 Run을 만들고 당시 시나리오 버전·WhyYou 버전·시험 대상과 정상 기준선을 고정한다.
2. **Given** 정상 기준선이 확인된 Run이 진행 중일 때, **When** reporting 장애가 성공적으로 적용되면, **Then** 적용 대상·시각·조건을 기록하고 이후 관찰을 `INJECTED` 구간에 연결한다.
3. **Given** reporting 장애 때문에 리포트가 준비되지 않았을 때, **When** 담당자가 해당 지원자를 조회하면, **Then** 준비 완료 리포트로 오인할 수 없으며 부재·처리 지연·실패 중 실제 상태가 식별 가능해야 한다.
4. **Given** 리포트가 준비되지 않은 지원자와 권한 있는 회사 사용자가 있을 때, **When** 사용자가 정상 최종결정 경로로 채용 결정을 시도하면, **Then** 요청은 리포트 부재를 설명하는 이유와 함께 거부되고 최종결정·채용 단계·지원 건 상태에 부분 변경이 없어야 한다.
5. **Given** 보호조치 assertion H03-A2~A5 중 하나가 실제 관찰값과 다를 때, **When** ControlProof가 판정하면, **Then** 해당 assertion과 전체 H-03 결과를 `FAIL`로 표시하고 기대값·관찰값·사용 증적을 연결한다.
6. **Given** 직접 관찰된 보호조치 위반은 없지만 필수 관찰이나 증적을 얻지 못했을 때, **When** ControlProof가 판정하면, **Then** `PASS`가 아니라 적절한 reason code를 가진 `INCONCLUSIVE`를 표시한다.
7. **Given** 장애 조건이 적용된 Run일 때, **When** 정상 실행이 끝나거나 중단되면, **Then** ControlProof는 장애 해제와 환경 복구 확인을 반드시 시도하고, 이후 리포트 처리 결과를 환경 복구 결과와 구분해 증적으로 남긴다.
8. **Given** fault marker가 제거되고 worker가 정상 동작하여 환경 복구가 확인되었을 때, **When** Run이 종료되면, **Then** 리포트 처리 결과가 `ready`, `partial`, `failed`, `timeout` 중 무엇이든 환경 복구와 별도 필드로 기록되고 실행 상태는 `COMPLETED`가 된다.
9. **Given** 복구가 실패했을 때, **When** Run이 종료되면, **Then** 실행 상태는 `RESTORE_FAILED`, 표시 결과는 `INCONCLUSIVE`가 되고 수동 정리 확인 전 같은 대상의 후속 장애 실행은 차단된다.

---

### User Story 2 - 판정의 근거와 한계를 검토한다 (Priority: P2)

검증 책임자는 완료된 Run에서 단계별 실행 상태, 대상별 관찰값, assertion별 기대값과 실제값, 사용한 원본 증적, 누락·충돌 증적과 복구 결과를 확인한다. 개발 지식이 없어도 왜 PASS·FAIL·INCONCLUSIVE가 나왔는지와 무엇을 확인하지 못했는지 구분할 수 있어야 한다.

**Why this priority**: 장애를 실행했다는 사실만으로는 검증 결과가 되지 않는다. 결과와 원본 증적이 연결되어야 내부 검토와 향후 증적 문서 작성에 사용할 수 있다.

**Independent Test**: 사전에 준비한 PASS, FAIL, 증적 누락, 증적 충돌 fixture를 각각 판정해 기대한 결과·사유·증적 연결이 표시되는지 확인한다.

**Acceptance Scenarios**:

1. **Given** Run에 모든 필수 관찰과 증적이 있고 모든 assertion이 만족되었을 때, **When** 검증 책임자가 결과를 열면, **Then** 전체 결과는 `PASS`이고 각 assertion에서 기대값·관찰값·증적을 확인할 수 있다.
2. **Given** 최종결정이 수락되었거나 거부 뒤 상태 부작용이 관찰되었을 때, **When** 결과가 생성되면, **Then** 전체 결과는 `FAIL`이고 보호받지 못한 위험을 비개발자용 설명으로 보여준다.
3. **Given** 필수 조회를 수행했지만 기록이 존재하지 않았을 때, **When** 관찰을 검토하면, **Then** `조회 결과 없음`으로 표시하고 유효한 관찰값으로 취급한다.
4. **Given** 접근 실패나 수집기 오류로 조회하지 못했을 때, **When** 관찰을 검토하면, **Then** `조회하지 못함`으로 표시하고 기록 부재로 오인하지 않는다.
5. **Given** 같은 Run·대상·구간·단계·시도의 같은 사실을 표현해야 하는 두 출처가 모순될 때, **When** 판정하면, **Then** 관련 assertion은 평가 불가이며 직접 관찰된 다른 실패가 없는 경우 전체 결과는 `INCONCLUSIVE: EVIDENCE_CONFLICT`가 된다.
6. **Given** 저장 증적이 생성 후 변경되었을 때, **When** 검증 책임자가 증적을 열거나 무결성을 확인하면, **Then** 변경 사실이 탐지되고 그 증적으로 PASS를 만들 수 없다.
7. **Given** 일부 assertion에서 직접적인 FAIL이 확인되고 다른 assertion의 증적이 부족할 때, **When** 결과를 검토하면, **Then** 전체 결과는 관찰된 실패를 숨기지 않는 `FAIL`이며 확인하지 못한 assertion과 증적 공백도 함께 표시한다.

---

### User Story 3 - 수정 후 별도 Run으로 재시험한다 (Priority: P3)

팀이 최초 FAIL 원인을 수정한 뒤 실행 담당자는 이전 Run을 기준으로 재시험을 시작한다. ControlProof는 새 Run을 만들고 이전 결과를 수정하거나 삭제하지 않으며, 두 Run의 시나리오·입력 조건·대상 버전 차이를 확인할 수 있게 연결한다.

**Why this priority**: ControlProof의 차별점은 실패 발견에서 끝나지 않고 같은 조건의 재시험으로 개선을 입증하는 데 있다. 다만 정교한 비교 화면은 후속 UI Spec에서 다룬다.

**Independent Test**: 하나의 완료된 Run에서 재시험을 시작해 새 Run ID와 이전 Run 참조가 생성되고, 최초 결과와 증적이 그대로 남는지 확인한다.

**Acceptance Scenarios**:

1. **Given** 완료된 H-03 Run이 있을 때, **When** 실행 담당자가 재시험을 시작하면, **Then** 새 Run이 생성되고 최초 Run을 부모로 참조한다.
2. **Given** 재시험이 생성되었을 때, **When** 두 Run을 조회하면, **Then** 최초 Run의 판정·증적은 변경되지 않고 각 Run의 대상 버전과 조건 차이를 구분할 수 있다.
3. **Given** 최초 Run이 이미 PASS였을 때, **When** 결과를 검토하면, **Then** 데모를 위해 인위적인 결함 버전을 만들도록 요구하지 않으며 실제 PASS를 그대로 보존한다.
4. **Given** 최초 Run이 FAIL이고 수정 후 Run이 PASS일 때, **When** 두 Run을 조회하면, **Then** FAIL→PASS 변화와 각 판정의 독립 증적을 확인할 수 있다.

---

### User Story 4 - 실행할 수 없는 이유를 정확히 구분한다 (Priority: P3)

실행 담당자는 H-03을 실행하기 전에 대상 기능과 ControlProof 실행 준비 상태를 확인한다. reporting 기능은 존재하지만 장애 주입 수단이 없는 경우 이를 대상 부재로 오인하지 않고 준비 중으로 이해할 수 있어야 한다.

**Why this priority**: 실행기 미구현을 `NO_TEST_TARGET`로 기록하면 제품의 검증 공백과 대상 서비스의 기능 부재가 뒤섞여 잘못된 보고서가 만들어진다.

**Independent Test**: 대상 존재 여부, 실행기 준비 여부와 접근 권한을 조합한 준비 상태 fixture로 실행 가능 여부와 사용자 안내를 확인한다.

**Acceptance Scenarios**:

1. **Given** WhyYou의 reporting 기능은 존재하지만 장애 주입 수단이 준비되지 않았을 때, **When** H-03 준비 상태를 확인하면, **Then** `RUNNER_NOT_READY`로 표시되고 실행을 시작할 수 없다.
2. **Given** 대상과 실행 수단은 존재하지만 필요한 읽기 권한이 없을 때, **When** 준비 상태를 확인하면, **Then** `ACCESS_BLOCKED`로 표시되고 필요한 접근 범위를 설명한다.
3. **Given** 대상 기능과 모든 실행·관찰·복구 수단이 준비되었을 때, **When** 준비 상태를 확인하면, **Then** `READY`로 표시되고 실행을 시작할 수 있다.
4. **Given** H-03의 통제 대상 자체가 WhyYou에 없다고 확인되었을 때, **When** 준비 상태를 확인하면, **Then** `NO_TEST_TARGET`로 표시하고 부재 근거를 연결한다.

### Edge Cases

- 합성 지원자의 리포트가 장애 주입 전에 이미 생성되면 기준선 전제조건 실패로 실행을 중단하고, H-03 FAIL이 아닌 `INCONCLUSIVE: INSUFFICIENT_EVIDENCE`로 기록한다.
- 장애 적용 명령은 성공했지만 실제 대상 경로에 영향이 없으면 장애 주입 실패로 기록하고 보호조치 PASS를 만들지 않는다.
- 장애 적용 여부 자체를 관찰할 수 없으면 `INCONCLUSIVE: INSUFFICIENT_EVIDENCE`다.
- worker 로그를 찾지 못했다는 사실만으로 장애 미발동을 확정하지 않는다. Run·session·event와 연결된 공유 trigger receipt를 읽을 수 없으면 H03-A1을 평가 불가로 처리한다.
- 장애 구간 중 reporting 경로가 예기치 않게 복구되면 그 시각을 남기고, 필요한 관찰 창을 충족하지 못한 경우 판정 불가로 처리한다.
- 담당자 표시가 계속 `처리 중`으로만 남고 시나리오가 정한 관찰 기한까지 실패·지연을 구분하지 못하면 `reporting 실패 노출` assertion은 FAIL이다.
- 최종결정 요청은 거부됐지만 결정 기록, 채용 단계 또는 지원 건 상태 중 하나라도 바뀌면 `결정 원자성` assertion은 FAIL이다.
- 최종결정 요청이 거부됐더라도 대상 응답이 리포트 부재를 명시적으로 설명하지 않으면 H03-A3은 FAIL이다. adapter가 일반 404나 빈 detail에서 이유를 추론해 만들어서는 안 된다.
- 최종결정 요청 결과는 성공처럼 보이지만 이후 상태 조회가 불가능하면 직접 확인된 성공 응답은 FAIL 근거로 보존하고 상태 부작용 확인 불가는 별도 증적 공백으로 표시한다.
- 서로 다른 phase, step 또는 attempt의 값 변화는 증적 충돌이 아니다.
- 같은 사실을 관찰한 출처가 잠시 다르다가 관찰 기한 안에 같은 안정 상태가 되면 원시 관찰은 모두 보존하고 안정화된 값을 판정에 사용한다.
- 증적 저장이나 SHA-256 생성에 실패하면 해당 증적은 완전한 필수 증적으로 인정하지 않는다.
- 실행 담당자가 취소하거나 ControlProof가 비정상 종료되어도 장애 해제와 복구 시도는 생략할 수 없다.
- marker 제거와 worker 정상 상태가 확인되면 환경 복구는 성공이다. 그 뒤 리포트가 `failed` 또는 `timeout`이 된 사실은 별도 제품 처리 결과와 finding으로 남기며 환경 복구 실패로 합치지 않는다.
- 복구 실패 뒤 수동 정리 완료를 확인하지 않은 상태에서 새 장애 실행 요청이 오면 거부한다.
- 동시에 실행한 다른 Run의 관찰값이나 증적이 현재 Run에 연결되면 증적 충돌이 아니라 상관관계 오류로 취급하고 해당 Run을 PASS로 만들지 않는다.
- 재시험의 합성 데이터 식별자는 새로 만들 수 있지만 역할·초기 상태·시험 조건 차이는 비교 가능하게 기록해야 한다.

---

## Requirements *(mandatory)*

### Functional Requirements

#### 시나리오와 준비 상태

- **FR-001**: ControlProof는 H-03 시나리오의 의도, 전제조건, 단계, 필수 assertion, 필수 증적과 복구 조건을 버전이 있는 정의로 관리해야 한다.
- **FR-002**: 과거 Run은 실행 당시의 시나리오 정의로 해석할 수 있어야 하며 이후 시나리오 변경으로 의미가 바뀌어서는 안 된다.
- **FR-003**: ControlProof는 대상 기능 존재 여부와 실행기 준비 여부를 독립적으로 평가해야 한다.
- **FR-004**: 준비 상태는 `READY`, `RUNNER_NOT_READY`, `ACCESS_BLOCKED`, `NO_TEST_TARGET` 중 하나여야 한다.
- **FR-005**: H-03 reporting 기능은 존재하지만 장애 주입 수단이 없을 경우 `RUNNER_NOT_READY`여야 하며 `NO_TEST_TARGET`가 되어서는 안 된다.
- **FR-006**: 준비 상태가 `READY`가 아니면 Run 시작을 허용하지 않고, 실행 담당자에게 이유와 필요한 조치를 보여줘야 한다.

#### 실행과 시험 대상

- **FR-007**: 실행 가능한 H-03 시작 요청은 고유한 Run을 만들어야 한다.
- **FR-008**: Run은 시나리오 ID·버전, 대상 서비스, canonical `TargetSnapshot`과 그 digest인 `target_version`, 시작·종료 시각, 실행 상태, seed 종류, 장애 종류와 재시험 관계를 기록해야 한다. `TargetSnapshot`은 실행 형태에 따라 git commit·dirty 상태와 diff digest, container image digest를 포함하고 OpenAPI·DB schema signature·고정 모델 fixture digest를 함께 고정해야 한다. Spec 001의 실제 H-03 Run은 clean git checkout만 허용하며 container를 사용하면 canonical component `backend`, `reporting-worker`, `company-console`의 image digest를 모두 요구한다.
- **FR-009**: Spec 001의 H-03 Run은 리포트 생성 대기 상태인 합성 지원자 한 명과 정상 최종결정 권한을 가진 합성 회사 사용자 한 명을 사용해야 한다.
- **FR-010**: 모든 관찰값과 증적은 Run과 `subject_ref`에 연결되어야 한다.
- **FR-011**: ControlProof는 장애 적용 전에 리포트 상태, 지원 건 상태, 채용 단계와 최종결정 기록 유무의 기준선을 수집해야 한다.
- **FR-012**: 기준선이 H-03의 전제조건과 다르면 장애를 적용하지 않고 Run을 안전하게 종료해야 한다.
- **FR-013**: Run 실행 상태는 `PENDING`, `RUNNING`, `RESTORING`, `COMPLETED`, `ABORTED`, `RESTORE_FAILED` 중 하나여야 한다.
- **FR-014**: `NOT_RUN`은 실제 Run의 실행 상태가 아니라 시나리오에 실행 결과가 없음을 나타내는 표시 상태로만 사용해야 한다.

#### 장애 적용과 복구

- **FR-015**: reporting 장애는 합성 데이터와 명시된 테스트 환경에만 영향을 주어야 한다.
- **FR-016**: ControlProof는 장애 종류, 적용 대상, 적용 시각, 실행 주체와 적용 성공 여부를 기록해야 한다.
- **FR-017**: 장애가 실제 reporting 처리에 영향을 주었다는 사실을 별도 관찰값으로 확인해야 하며, 명령 성공만으로 장애 적용 성공을 추정해서는 안 된다.
- **FR-018**: 장애가 적용된 Run은 정상 종료·실패·취소와 관계없이 장애 해제와 복구 확인 단계로 진입해야 한다.
- **FR-019**: 복구 결과에는 해제 시각, marker 비활성 확인, worker 정상 여부와 기준선 대비 대상 상태를 포함해야 하며, 이 환경 복구 결과와 이후 리포트 처리 결과를 별도 필드로 기록해야 한다.
- **FR-020**: 복구 실패 시 Run을 `RESTORE_FAILED`로 표시하고 같은 대상에 대한 후속 장애 실행을 수동 정리 확인 전까지 차단해야 한다.

#### 관찰과 상태 의미

- **FR-021**: 모든 관찰값은 `subject_ref`, `phase`, `step_id`, `attempt`, 관찰 시각, 출처와 값 존재 상태를 가져야 한다.
- **FR-022**: `phase`는 `BASELINE`, `INJECTED`, `RECOVERED` 중 하나여야 한다.
- **FR-023**: ControlProof는 `조회했고 값 또는 기록이 없음`과 `조회하지 못함`을 서로 다른 상태로 보존하고 표시해야 한다.
- **FR-024**: 같은 key라도 phase, step 또는 attempt가 다르면 시간에 따른 별도 관찰로 취급해야 한다.
- **FR-025**: 같은 Run·대상·phase·step·attempt에서 같은 사실을 표현해야 하는 비결측 관찰들은 시나리오 버전에 고정된 key별 comparator로 비교해야 한다. comparator가 없으면 `EXACT`가 기본이며, 허용 오차는 `ABSOLUTE_TOLERANCE`와 0 이상의 절대값이 명시된 key에만 적용할 수 있다. Spec 001 H-03의 assertion 입력 key는 모두 `EXACT`이고 `observed_at`은 값 충돌 비교 대상이 아닌 관찰 메타데이터다.
- **FR-026**: 비동기 상태 관찰은 시나리오에 정의된 관찰 기한과 안정화 조건을 가져야 하며, 원시 관찰 순서를 보존해야 한다.

#### H-03 최소 assertion

- **FR-027**: ControlProof는 장애 구간에서 리포트가 준비되지 않았음을 확인해야 한다.
- **FR-028**: ControlProof는 담당자에게 표시되는 상태가 준비 완료 리포트로 오인되지 않는지 확인해야 한다.
- **FR-029**: 담당자 상태가 관찰 기한까지 계속 처리 중으로만 표시되어 실제 최종 실패나 장기 지연을 구분할 수 없으면 실패 노출 assertion을 FAIL로 판정해야 한다.
- **FR-030**: ControlProof는 권한 있는 회사 사용자의 정상 최종결정 시도를 수행하고 수락 또는 거부 결과, 대상 응답이 제공한 이유와 그 출처를 관찰해야 하며, adapter가 일반 오류로부터 이유를 만들어서는 안 된다.
- **FR-031**: 리포트가 준비되지 않은 상태의 최종결정 시도는 리포트 부재를 명시적으로 설명하는 대상 응답과 함께 거부되어야 한다.
- **FR-032**: 거부된 최종결정 시도 뒤 최종결정 기록, 채용 단계와 지원 건 상태가 기준선에서 바뀌지 않아야 한다.
- **FR-033**: ControlProof는 장애 구간에 시스템이 사람의 요청 없이 최종결정을 만들지 않았음을 확인해야 한다.
- **FR-034**: Spec 001의 H-03 판정은 일반 칸반·일괄 단계 이동 우회, 재시도 소진, DLQ, 복구 후 멱등성을 필수 assertion으로 삼아서는 안 된다.

#### 증적과 무결성

- **FR-035**: 각 필수 assertion은 기대값, 실제 관찰값과 판정에 사용한 증적을 연결해야 한다.
- **FR-036**: 필수 증적은 최소한 기준선, 장애 적용·효과 확인, 담당자 표시 상태, 최종결정 요청·결과, 결정 시도 후 상태, 자동결정 부재 확인과 복구 결과를 포함해야 한다.
- **FR-037**: 판정에 사용한 최소 원본은 Run의 증적 묶음에 보존하고 원본 locator도 함께 기록해야 한다.
- **FR-038**: 전체 로그나 전체 데이터 저장소 사본을 증적으로 수집해서는 안 된다.
- **FR-039**: 저장 증적은 수집 시각, 출처, MIME 유형, 크기와 SHA-256 해시를 가져야 한다.
- **FR-040**: 비밀값과 개인정보는 증적 저장 전에 제거하거나 마스킹해야 한다.
- **FR-041**: 증적 무결성 확인에 실패한 자료는 PASS의 필수 근거로 사용할 수 없어야 한다.

#### 판정과 설명

- **FR-042**: assertion 결과는 `PASS`, `FAIL`, `INCONCLUSIVE` 중 하나와 설명을 가져야 한다.
- **FR-043**: Run의 H-03 결과는 `PASS`, `FAIL`, `INCONCLUSIVE` 중 하나여야 하며, 실행 전 시나리오 표시는 `NOT_RUN`일 수 있다.
- **FR-044**: 모든 필수 assertion이 PASS이고 필수 증적이 완전하며 Run 복구가 성공했을 때만 H-03 전체 결과를 PASS로 판정해야 한다.
- **FR-045**: 필수 보호조치 위반이 하나라도 직접 관찰되면 전체 결과를 FAIL로 판정하고, 다른 assertion의 증적 공백도 함께 표시해야 한다.
- **FR-046**: 직접 관찰된 FAIL은 없지만 하나 이상의 필수 assertion을 평가할 수 없으면 전체 결과는 INCONCLUSIVE여야 한다.
- **FR-047**: Run이 `ABORTED` 또는 `RESTORE_FAILED`이면 H-03 전체 결과는 INCONCLUSIVE여야 하며, 중단 전 관찰된 위험은 별도 finding으로 숨김없이 표시해야 한다.
- **FR-048**: 판정 불가 reason code는 `NO_TEST_TARGET`, `ACCESS_LIMITED`, `INSUFFICIENT_EVIDENCE`, `EVIDENCE_CONFLICT`만 사용해야 한다.
- **FR-049**: 결과는 비개발자가 이해할 수 있는 한 문장 설명과 검증하지 못한 범위를 포함해야 한다.
- **FR-050**: ControlProof 구현 완료 여부는 `NOT_IMPLEMENTED`, `PARTIAL`, `IMPLEMENTED` 중 하나로 표시하고 WhyYou의 H-03 판정 결과와 분리해야 한다. 필수 capability handler가 0개면 `NOT_IMPLEMENTED`, 일부만 등록됐거나 계약 버전이 맞지 않으면 `PARTIAL`, 전부 등록되고 계약 버전이 일치하면 `IMPLEMENTED`다. 대상 기능이 존재할 때 `PARTIAL|NOT_IMPLEMENTED`는 `RUNNER_NOT_READY`로 Run 생성을 막고, 대상 기능 자체가 없으면 구현 상태와 별개로 `NO_TEST_TARGET`다. 대상의 `PASS|FAIL|INCONCLUSIVE`나 실행 중 오류는 구현 상태를 바꾸지 않는다.

#### 재시험과 불변성

- **FR-051**: 완료된 Run에서 재시험을 시작하면 새 Run을 만들고 최초 Run을 부모로 연결해야 한다.
- **FR-052**: 재시험은 이전 Run의 판정, 관찰값과 증적을 수정하거나 삭제해서는 안 된다.
- **FR-053**: 최초 Run과 재시험 Run은 시나리오 버전, canonical `TargetSnapshot` digest와 변경된 component path, 시험 대상 역할, 초기 상태와 장애 조건의 차이를 확인할 수 있어야 한다.
- **FR-054**: 최초 Run이 실제로 PASS하면 FAIL 데모를 위해 WhyYou의 결함 버전을 새로 만들도록 강제해서는 안 된다.

#### 결정론적 시험 환경

- **FR-055**: H-03 Run은 외부 AI 서비스의 변동에 의존하지 않는 결정론적 대역이 활성화되고 그 fixture 식별자와 digest를 확인할 수 있을 때만 `READY`여야 한다.

### Required Assertions

| Assertion ID | 확인할 사실 | PASS 조건 | FAIL 조건 | 필수 증적 |
|---|---|---|---|---|
| H03-A1 | reporting 장애가 실제 적용됨 | 명령 기록과 실제 처리 영향이 모두 관찰됨 | 해당 없음. 적용 실패는 보호조치 평가 전 판정 불가 | 장애 적용 기록, 영향 관찰 |
| H03-A2 | 리포트 미준비 상태가 담당자에게 드러남 | 준비 완료와 구분되는 실제 상태가 관찰 기한 안에 표시됨 | 준비 완료로 표시되거나, 최종 실패·장기 지연을 계속 단순 처리 중으로 숨김 | 담당자 표시 캡처, 상태 조회 결과 |
| H03-A3 | 리포트 없이 최종결정 불가 | 정상 최종결정 시도가 대상이 제공한 리포트 부재 이유와 함께 거부됨 | 결정 요청이 수락되거나, 거부됐지만 대상 응답에 명시적 리포트 부재 이유가 없음 | 결정 요청·응답 |
| H03-A4 | 거부 시 부분 변경 없음 | 결정 기록·채용 단계·지원 건 상태가 모두 기준선과 같음 | 하나라도 변경됨 | 기준선과 시도 후 상태 비교 |
| H03-A5 | 자동 최종결정 없음 | 장애 구간에 사람 요청 없는 최종결정이 없음 | 시스템 주체의 최종결정 또는 확정 상태 변화가 있음 | 결정 이력과 상태 변화 조회 |
| H03-A6 | 장애 해제와 환경 복구 | marker 비활성 및 worker 정상 상태로 대상이 안전함을 확인 | 해당 없음. 환경 복구 확인 실패는 Run 상태와 전체 결과를 판정 불가로 전환 | 해제 기록, worker health, 복구 후 상태, 별도 리포트 처리 결과 |

H03-A1과 H03-A6은 시험 유효성과 안전을 확인하는 assertion이다. A1을 평가할 수 없거나 A6 복구가 실패하면 WhyYou 보호조치의 PASS/FAIL을 확정하지 않고 전체 결과를 INCONCLUSIVE로 표시한다. 단, 그 전에 직접 관찰된 위험은 finding으로 유지한다.

H03-A6의 `환경 복구`는 ControlProof가 주입한 장애가 제거되고 worker가 정상 실행 가능한 상태로 돌아왔는지를 뜻한다. 복구 뒤 리포트가 `ready|partial`이 되는지, 명시적 `failed`로 끝나는지, 120초 안에 끝나지 않는지는 `report_processing_recovery`로 별도 기록한다. `failed|timeout`은 숨기지 않고 finding으로 남기지만 marker 부재와 worker 정상성이 확인된 환경 복구 성공을 실패로 바꾸지는 않는다.

### Key Entities

- **Scenario Definition**: 통제 의도, 버전, 전제조건, 단계, assertion, 필수 증적, 관찰 기한과 복구 조건을 담는 실행 명세다.
- **Scenario Readiness**: 대상 기능 존재 여부와 실행·관찰·복구 수단 준비 상태를 표현한다. 결과 판정과 독립적이다.
- **Run**: 시나리오 한 번의 실행 단위다. 고유 ID, 시나리오와 대상 버전, 생명주기 상태, 시작·종료 시각과 재시험 관계를 가진다.
- **Test Subject**: 한 Run에서 시험하는 합성 지원자 또는 처리 건이다. 모든 관찰과 증적은 `subject_ref`로 이를 가리킨다.
- **Fault Condition**: 테스트 환경에 적용한 장애의 종류, 대상, 적용·해제 시각, 성공 여부와 복구 방법이다.
- **Observation**: 특정 대상·구간·단계·시도에서 수집한 구조화된 사실이다. 값 존재, 조회 결과 없음, 조회 실패를 구분한다.
- **Evidence Artifact**: 관찰과 판정을 뒷받침하는 최소 원본 또는 추출물이다. 원본 locator와 무결성 메타데이터를 가진다.
- **Assertion Result**: 하나의 기대 결과와 실제 관찰을 비교한 결과다. 사용한 관찰·증적과 평가 불가 이유를 연결한다.
- **Judgement**: Run의 assertion 결과를 종합한 H-03 결과와 비개발자용 설명이다.
- **Retest Link**: 수정 후 새 Run과 최초 Run을 연결하고 입력·조건·대상 버전 차이를 설명한다.

### State Semantics

#### Readiness

| 상태 | 의미 | 실행 가능 여부 |
|---|---|---|
| `READY` | 대상과 실행·관찰·복구 수단이 준비됨 | 가능 |
| `RUNNER_NOT_READY` | 대상은 있으나 필요한 실행 수단이 없음 | 불가 |
| `ACCESS_BLOCKED` | 대상은 있으나 허용된 접근으로 관찰 불가 | 불가 |
| `NO_TEST_TARGET` | 대상 기능 자체가 없음 | 불가 |

#### Run Lifecycle

| 상태 | 의미 | 허용되는 다음 상태 |
|---|---|---|
| `PENDING` | 실행 요청이 생성됐으나 시험 동작 전 | `RUNNING`, `ABORTED` |
| `RUNNING` | 기준선·장애·관찰·판정 단계 수행 중 | `RESTORING`, 장애 미적용 시 `ABORTED` |
| `RESTORING` | 장애 해제와 기준선 복구 확인 중 | 정상 완주 시 `COMPLETED`, 복구 후 실행 미완료 시 `ABORTED`, 복구 실패 시 `RESTORE_FAILED` |
| `COMPLETED` | 실행과 복구가 종료됨 | 종료 상태 |
| `ABORTED` | 실행은 완주하지 못했지만 장애를 적용하지 않았거나 적용한 장애를 안전하게 해제함 | 종료 상태 |
| `RESTORE_FAILED` | 장애 해제 또는 안전 상태 확인 실패 | 종료 상태, 수동 정리 필요 |

장애가 한 번이라도 적용된 뒤에는 `ABORTED`로 바로 종료하지 않고 `RESTORING`을 거쳐야 한다.

#### Verdict

| 결과 | 의미 |
|---|---|
| `PASS` | 모든 필수 assertion과 증적이 확인되고 복구도 성공함 |
| `FAIL` | 필수 보호조치 위반이 직접 관찰됨 |
| `INCONCLUSIVE` | 직접 확인된 FAIL 없이 결론에 필요한 조건·관찰·증적이 부족하거나 실행이 안전하게 완료되지 않음 |
| `NOT_RUN` | 시나리오는 있으나 Run이 없음 |

### Required Evidence Set

| Evidence ID | 내용 | 최소 연결 정보 | 판정 사용 |
|---|---|---|---|
| EV-01 | 실행 전 지원 건·채용 단계·리포트·결정 기준선 | Run, subject, `BASELINE`, step, captured time | 필수 |
| EV-02 | 장애 적용 요청과 결과 | Run, subject, `INJECTED`, step, fault condition | 필수 |
| EV-03 | 현재 Run·session·trigger와 일치하는 worker trigger receipt 및 장애 구간 report 상태 | Run, subject, `INJECTED`, step, attempt, outbox event | 필수 |
| EV-04 | 담당자에게 표시된 리포트 상태 | Run, subject, `INJECTED`, step, capture context | 필수 |
| EV-05 | 최종결정 시도의 요청·응답 | Run, subject, `INJECTED`, step, actor | 필수 |
| EV-06 | 결정 시도 후 결정 기록·채용 단계·지원 건 상태 | Run, subject, `INJECTED`, step | 필수 |
| EV-07 | 장애 구간의 자동 최종결정 부재 확인 | Run, subject, `INJECTED`, observation window | 필수 |
| EV-08 | marker 비활성·worker health 기반 환경 복구와 별도 리포트 처리 결과 | Run, subject, `RECOVERED`, step | 필수 |
| EV-09 | 시나리오 snapshot과 canonical `TargetSnapshot` | Run, scenario version/digest, target snapshot/digest, fixture ID/digest | 필수 |

각 증적은 판정에 필요한 최소 범위만 저장하며 비밀값과 개인정보가 제거된 상태여야 한다.

---

### Scope Boundaries

#### Included

- H-03 준비 상태 확인
- 합성 지원자 한 명의 상태 seed
- 정상 기준선 수집
- 테스트 환경의 reporting 장애 한 종류
- 장애 적용 효과 확인
- 담당자에게 보이는 리포트 상태 확인
- 정상 최종결정 경로 한 종류의 거부와 부작용 확인
- 자동 최종결정 부재 확인
- 장애 해제와 복구 확인
- 관찰·증적·assertion·전체 판정
- 원본 증적 보관과 SHA-256 무결성 확인
- 별도 Run 기반 재시험 연결

#### Excluded and Deferred

- reporting 재시도 한도 소진과 DLQ 전환
- 애플리케이션 실패 상태와 인프라 DLQ의 교차 확인
- 칸반·일괄 이동 등 일반 단계 이동 우회
- 복구 후 동일 요청 재전송과 멱등성
- Outbox 이벤트와 결정 이력의 누락·중복 판정
- 복수 지원자와 대조군
- N·E 계열 다른 시나리오 실행
- 네 화면 전체의 완성된 시각 디자인과 종합 보고서
- 운영 환경 장애 주입

위 항목 중 DLQ·재시도·멱등성은 기능 Spec 002에서 다루며 2주 최종 MVP 범위에서는 제외되지 않는다.

2주 MVP 전체의 FAIL→수정→PASS 데모는 실제로 통제 실패가 관찰된 시나리오에서 수행한다. H-03 최초 Run이 이미 PASS라면 H-03에 인위적인 결함을 만들지 않으며, 다른 시나리오에서 관찰된 실제 FAIL이 전체 MVP의 개선 데모를 담당할 수 있다.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 준비된 로컬 시험환경에서 실행 담당자는 수동 데이터 수정 없이 H-03 최소 Run을 시작해 5분 안에 결과와 복구 상태를 확인할 수 있다.
- **SC-002**: 정상, 보호조치 위반, 증적 누락, 증적 충돌, 실행 중단과 복구 실패 fixture 각각에서 기대한 verdict와 reason code가 100% 일치한다.
- **SC-003**: PASS로 표시된 모든 Run은 6개 필수 assertion과 9종 필수 증적을 빠짐없이 연결하며, 필수 증적이 하나라도 불완전하면 PASS가 0건이어야 한다.
- **SC-004**: 최종결정이 거부된 시험에서 결정 기록·채용 단계·지원 건 상태의 부분 변경이 0건이어야 하며, 변경이 발생한 fixture는 모두 FAIL로 탐지된다.
- **SC-005**: 장애가 적용된 Run의 100%에서 복구가 시도되고, 복구 실패 fixture의 100%가 `RESTORE_FAILED`와 후속 실행 차단으로 나타난다.
- **SC-006**: 저장 후 변경한 증적 fixture의 100%에서 무결성 오류를 탐지하며 해당 자료로 PASS를 만들지 않는다.
- **SC-007**: 재시험 후 최초 Run의 판정·관찰·증적 변경 건수가 0건이고, 새 Run의 부모 관계와 버전 차이를 모두 확인할 수 있다.
- **SC-008**: 결과 bundle을 만들지 않은 검토자 1명이 canonical PASS·FAIL·INCONCLUSIVE bundle 3건을 대상으로 각 Run ID를 전달받은 시점부터 120초 안에 문서화된 `show` 명령만 사용해 최종 verdict, 핵심 이유, 실패 또는 판정 불가 assertion, 사용 증적 링크와 환경 복구 성공 여부를 모두 정확히 기록한다. 3건 모두 항목 누락·오답 없이 120초 이하여야 통과하며 검토자 ref, 시작·종료 시각, 소요 시간과 답안을 `validation.md`에 남겨야 한다.
- **SC-009**: 전체 시연과 자동 시험에서 실제 지원자 개인정보 사용 건수는 0건이다.
- **SC-010**: reporting 기능 존재·장애 주입기 미준비 조합의 100%가 `RUNNER_NOT_READY`로 표시되고 `NO_TEST_TARGET`로 표시되는 경우는 0건이다.

---

## Assumptions

- WhyYou의 reporting 처리와 사람 전용 최종결정 기능은 현재 검증 대상에 존재한다.
- 팀은 실제 채용 운영과 분리된 로컬 또는 명시적 테스트 환경을 사용할 수 있다.
- 테스트 환경에서만 활성화되는 최소 reporting 장애 연결점을 추가할 수 있다.
- 회사 사용자 권한을 가진 합성 테스트 계정과 합성 지원자 상태를 준비할 수 있다.
- 외부 AI 호출은 고정 결과 대역으로 바꿀 수 있어 반복 실행 결과가 외부 모델 변동에 좌우되지 않는다.
- H-03의 정확한 관찰 기한과 안정화 간격은 기술 Plan에서 WhyYou의 실제 처리 특성을 확인해 정하되, 담당자가 실패를 무기한 `처리 중`으로 보게 하는 결과는 허용하지 않는다.
- 증적 보존 기간과 외부 반출 정책은 MVP 이후 운영 정책에서 정한다. MVP에서는 최소한 데모와 재시험 검토 기간 동안 원본을 사용할 수 있어야 한다.
- 현재 첨부 골격은 구현 시작점이지만 기존 Observation 구조, readiness 판정과 H-03 YAML은 이 Spec에 맞게 변경할 수 있다.

## Dependencies

- WhyYou 테스트 환경과 대상 버전 식별 정보
- 합성 지원자 상태를 만드는 허용된 seed 경로
- 사람 전용 정상 최종결정 경로
- 담당자에게 노출되는 리포트 상태 조회 경로
- reporting 장애 적용과 해제를 수행할 테스트 전용 수단
- 결정 시도 전후 상태와 결정 이력을 읽을 수 있는 허용된 증적 경로
- ControlProof의 Run·관찰·증적 저장 위치

## Risks and Product Responses

| 위험 | 제품 차원의 대응 |
|---|---|
| 장애가 실제 적용되지 않았는데 보호조치가 통과한 것으로 보임 | 장애 명령과 실제 영향 확인을 분리하고 둘 다 없으면 판정 불가 |
| 결정 거부 응답만 보고 부분 저장을 놓침 | 응답과 결정 기록·단계·지원 건 상태를 함께 비교 |
| 테스트 실행기가 없어 대상 기능 부재로 잘못 보고 | readiness에서 `RUNNER_NOT_READY`와 `NO_TEST_TARGET` 분리 |
| 비동기 상태 변화가 증적 충돌로 오인됨 | phase·step·attempt와 안정화 조건으로 시간 변화를 구분 |
| 복구 실패가 다음 시험에 영향을 줌 | `RESTORE_FAILED`와 후속 장애 실행 차단 |
| 원본 로그를 과수집해 개인정보가 포함됨 | 판정에 사용한 최소 추출물만 저장하고 사전 마스킹 |
| WhyYou가 이미 안전해 FAIL→PASS 데모가 나오지 않음 | 실제 PASS를 보존하고 결함을 인위적으로 만들지 않음 |
| ControlProof의 성공과 WhyYou의 PASS가 혼동됨 | 구현 상태와 대상 verdict를 별도로 표시 |

## Traceability

| Product source | 이 Spec의 반영 위치 |
|---|---|
| Product Brief 6.3~6.10 | FR-001~FR-026, FR-042~FR-054, Key Entities, State Semantics |
| Product Brief 8.1 | User Story 1, H-03 최소 assertion, Included 범위 |
| Decision D-001~D-003 | FR-010, FR-021~FR-026 |
| Decision D-004~D-005 | FR-035~FR-041, Required Evidence Set |
| Decision D-006 | FR-013~FR-020, FR-047 |
| Decision D-008~D-009 | FR-027~FR-034, Excluded and Deferred |
| Decision D-010~D-011 | Assumptions, FR-003~FR-006, FR-048 |
| Constitution I·II·V·VI·VII | 판정, readiness, 격리·복구, 불변 재시험, 전체 추적성 |

## Planning Gate

기술 Plan은 다음 사항을 확인한 뒤 작성해야 한다.

- H-03 최소형과 Spec 002의 DLQ·멱등성 확장이 섞이지 않았는가
- reporting 장애 연결점이 테스트 환경에만 한정되는가
- 기존 골격에서 readiness, Observation 식별 차원과 충돌 판정을 어떻게 이전할 것인가
- 장애 적용 뒤 어떤 종료 경로에서도 복구를 보장할 수 있는가
- 판정에 필요한 9종 증적을 최소 수집으로 확보할 수 있는가
- 최초 Run과 재시험 Run을 불변으로 보존할 수 있는가
- 모든 구현 task가 FR 또는 assertion ID에 연결될 수 있는가
