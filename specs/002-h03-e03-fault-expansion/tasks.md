---

description: "Spec 002 H-03·E-03 장애·재시도·DLQ 확장의 구현 작업 목록"
---

# Tasks: H-03·E-03 장애·재시도·DLQ 확장

**Input**: `specs/002-h03-e03-fault-expansion/`의 spec, plan, research, data model, contracts, quickstart  
**Tests**: Spec이 assertion별 단위·계약·통합 시험과 최초 실제 Run을 요구하므로 테스트 작업을 구현보다 먼저 포함한다.  
**Organization**: 공통 기반 뒤에 6개 사용자 스토리를 독립 검증 가능한 증분으로 구성한다. `[FR-*]`, `[H03-A*]`, `[E03-A*]`, `[EV2-*]`는 추적 ID다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 선행조건이 충족되면 다른 파일의 작업과 병렬 실행 가능
- **[Story]**: 기능 Spec의 사용자 스토리
- 모든 작업은 수정하거나 생성할 정확한 파일 경로를 포함한다.
- `../gbsa_aws/` 경로의 작업은 WhyYou 개인 브랜치에서만 수행하며 `main`에 직접 commit·push하지 않는다.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Spec 002의 LocalStack 관찰, 고정 local profile과 테스트 fixture 기반을 준비한다.

- [X] T001 Add `boto3>=1.35,<2` to runtime dependencies in `pyproject.toml`
- [X] T002 [P] Add secret-free variable names and loopback examples for target/environment identity, LocalStack endpoint, reporting queue/DLQ, WhyYou repository, and model fixture in `.env.example` [FR-081~087]
- [X] T003 [P] Create `engine/executors/__init__.py` and `engine/judges/__init__.py`, and create reusable Spec 002 fixture builders for environment snapshots, queue topology, delivery attempts, boundary receipts, terminal failures, reporting effects, decision effects, and redrive receipts in `tests/fixtures/spec002.py`
- [X] T004 [P] In the WhyYou personal branch, document `SQS_REPORTING_MAX_RECEIVE_COUNT=3`, `SQS_REPORTING_VISIBILITY_TIMEOUT_SECONDS=5`, disabled-by-default test controls, and local-only fixture settings in `../gbsa_aws/.env.example` [FR-022, FR-085, FR-088]

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 스토리가 공유하는 v2 profile, 실행 세션, adapter protocol과 증적 저장 계약을 먼저 고정한다.

**⚠️ CRITICAL**: 이 Phase가 완료되기 전에는 사용자 스토리 구현을 시작하지 않는다.

### Foundation tests — write first and confirm failure

- [X] T005 [P] Add model tests requiring `execution_profile ∈ {H03_MINIMAL_V1,H03_DLQ_V2,E03_BEFORE_V2,E03_AFTER_V2}`, one matching `fault_variant`, `delivery_attempt >= 1`, canonical SHA-256 digests, `LOCAL_EMULATED`, AWS `NOT_RUN`, and exact unverified scope `{AWS_SQS,AWS_ECS,AWS_IAM,AWS_CLOUDWATCH,AWS_NETWORK}` in `tests/unit/test_models_spec002.py` [FR-001~010, FR-081~087]
- [X] T006 [P] Add v2 scenario contract tests for unique `(scenario_id,version,execution_profile)`, canonical profile/assertion/evidence ownership, one fault variant per Run, mandatory restore, timing snapshot, and unchanged v1 H-03 loading in `tests/contract/test_scenario_profile_v2.py` [FR-001~003, FR-018~020]
- [X] T007 [P] Add lifecycle tests proving every faulted profile passes through restore, checkpoints are append-only, executor exceptions cannot skip sealing rules, and restore failure blocks later fault Runs in `tests/unit/test_execution_session.py` [FR-066~076, E03-A8]
- [X] T008 [P] Add additive bundle contract tests for `profile_contract=controlproof.bundle-profile.spec002.v1`, new canonical files, typed `file:|artifact:|intrinsic:` evidence refs, cross-Run origin digest, v1 compatibility, and read-only tamper detection in `tests/contract/test_bundle_profile_spec002.py` [FR-056~065, EV2-01~EV2-12]
- [X] T009 [P] Add local environment guard tests for clean ControlProof/WhyYou commits, loopback URLs, LocalStack-only SQS, fixed model/embedder, external-AI denial, AWS `NOT_RUN`, exact queue attributes, and zero Run creation on mismatch in `tests/contract/test_local_environment_guard.py` [FR-081~088]
- [X] T010 [P] Add an installed-package import test for `engine.executors` and `engine.judges` in `tests/contract/test_package_layout.py`, and add a regression test that executes and verifies the unchanged `H03_MINIMAL_V1` scenario and its v1 bundle after all v2 registrations are loaded in `tests/integration/test_spec001_v1_regression.py` [FR-001, FR-010]

### Foundation implementation

- [X] T011 Implement immutable ScenarioProfile, Run additions, FaultVariant, TargetEnvironmentSnapshot, QueueTopologySnapshot, DeliveryAttemptRecord, TerminalFailureRecord, FaultBoundaryReceipt, DecisionPathCapability, BusinessEffectSnapshot, and RedriveReceipt models in `engine/models.py`; enforce the exact enum, digest, cardinality, `ABSENT` vs `UNAVAILABLE`, and identity constraints from `data-model.md` [FR-001~010, FR-041~065, FR-081~095]
- [X] T012 Implement additive v2 loading and canonical profile validation while preserving v1 behavior in `engine/scenario.py`; reject profile/fault/assertion/evidence mismatches and CLI-supplied semantic overrides [FR-001~003, FR-018~020]
- [X] T013 [P] Add service-neutral environment, queue, decision, effect, boundary-receipt, duplicate-ack, and safe-redrive protocols with sanitized result envelopes in `engine/adapters/base.py` after T011 [FR-011~020, FR-056~065]
- [X] T014 Implement shared lock → checkpoint → artifact → mandatory restore → judgement → seal behavior as `ExecutionSession` in `engine/execution.py`, preserving Spec 001 lifecycle and restore-block semantics [FR-066~080, E03-A8]
- [X] T015 Refactor `engine/runner.py` into a Spec 001-compatible facade plus execution-profile registry, dispatching v1 unchanged and refusing unregistered v2 profiles before Run creation [FR-001~006, FR-020]
- [X] T016 [P] Extend `engine/evidence.py` to write and verify environment, queue, attempts, effects, terminal failure and redrive canonical files, profile-scoped EV2 mappings and origin-Run references without weakening v1 sealing [FR-056~065, EV2-01~EV2-12]
- [X] T017 [P] Extend `engine/config.py` with typed WhyYou/local SQS settings and fail-closed validation for loopback endpoints, fixed fixtures, external-AI denial, queue timing and non-main clean target checkout [FR-014~020, FR-081~088]
- [X] T018 Extend deterministic fake adapters with independent queue, decision, effect, BEFORE/AFTER fault and restore outcomes in `tests/fixtures/fake_adapters.py` after T011 and T013
- [X] T019 Run `pytest -q tests/unit/test_models_spec002.py tests/contract/test_scenario_profile_v2.py tests/unit/test_execution_session.py tests/contract/test_bundle_profile_spec002.py tests/contract/test_local_environment_guard.py tests/contract/test_package_layout.py tests/integration/test_spec001_v1_regression.py` and record the exact command and result in `specs/002-h03-e03-fault-expansion/validation.md`

**Checkpoint**: v1 회귀를 깨뜨리지 않는 v2 공통 모델·실행·증적 기반이 준비된다.

---

## Phase 3: User Story 1 — 재시도 소진 뒤 실패 건이 사라지지 않는지 확인한다 (Priority: P1) 🎯 First Slice

**Goal**: 같은 원 사건의 실제 전달 시도를 끝까지 관찰하고 LocalStack DLQ의 최종 실패 건과 담당자·운영자 상태를 연결한다.

**Independent Test**: 합성 원 사건 하나에 BEFORE 장애를 유지해 receive count 3과 `iep-reporting-dlq` 도달을 관찰하고, 연결된 terminal failure와 담당자/운영자 표시를 assertion fixture로 판정한다.

### Tests for User Story 1 — write first

- [X] T020 [P] [US1] Add queue adapter contract tests for LocalStack attributes, redrive target, max receive count 3, visibility 5 seconds, matching/foreign DLQ messages, successful-empty vs unavailable reads, and credential redaction in `tests/contract/test_whyyou_queue_adapter.py` [FR-011~030, FR-088, EV2-01, EV2-04, EV2-05]
- [X] T021 [P] [US1] In the WhyYou personal branch, extend queue topology tests for reporting overrides, source/DLQ retention and exact redrive policy in `../gbsa_aws/backend/tests/unit/shared/test_local_queue_topology.py` [FR-025, FR-088]
- [X] T022 [P] [US1] In the WhyYou personal branch, add failing tests requiring each BEFORE trigger receipt to include run, session, Outbox event, delivery attempt, fault variant and boundary without PII in `../gbsa_aws/backend/tests/unit/runtime/test_controlproof_reporting_fault.py` [FR-022~024, EV2-03, EV2-04]
- [X] T023 [P] [US1] Add integration tests for ordered attempts → receive-limit exhaustion → matching DLQ, missing/unlinked DLQ FAIL, access-loss INCONCLUSIVE, and wrong queue settings preflight refusal in `tests/integration/test_h03_dlq_lineage.py` [H03-A8, E03-A1, E03-A2]
- [X] T024 [P] [US1] Add H03-A8/A9 judge tests for preserved failure, unlinked/missing failure, queued-forever UI, visible final failure, operator locator absence, and evidence conflict in `tests/unit/test_judge_h03_dlq.py` [FR-026~032, H03-A8, H03-A9]

### Implementation for User Story 1

- [X] T025 [US1] In the WhyYou personal branch, extend `../gbsa_aws/backend/src/interview_evidence/runtime/controlproof_faults.py` and `../gbsa_aws/backend/src/interview_evidence/runtime/worker.py` so BEFORE receipts carry the exact source event/version and delivery attempt while retaining run/session allowlist, TTL, append+fsync and production rejection [FR-022~024]
- [X] T026 [US1] Implement topology capture, attempt normalization, matching DLQ lookup and the single-message send → persisted receipt → delete safe-redrive primitive in `engine/adapters/whyyou/queue.py`; this adapter owns queue mutation and must never delete foreign or unsuccessfully republished messages [FR-024~030, EV2-01, EV2-04, EV2-05, EV2-09]
- [X] T027 [US1] Extend `engine/adapters/whyyou/capability.py` and `engine/adapters/whyyou/adapter.py` with environment/queue/DLQ/receipt capabilities and exact READY/RUNNER_NOT_READY/ACCESS_BLOCKED precedence [FR-011~020, FR-081~088]
- [X] T028 [P] [US1] Extend final-failure visible-state normalization and sanitized screenshot/text capture in `engine/adapters/whyyou/browser.py`, distinguishing final failure from queued, retrying and ready [FR-031~032, H03-A9, EV2-06]
- [X] T029 [P] [US1] Create canonical `H03_DLQ_V2` steps, timing, assertions H03-A1~A9, Spec 001 EV-01~09 plus EV2-01~09/12, decision cases and mandatory restore in `scenarios/H-03-DLQ.yaml` [FR-001~040]
- [X] T030 [US1] Implement H-03 environment/topology/baseline/fault/trigger/attempt/DLQ/UI/restore/redrive action flow in `engine/executors/h03_dlq.py` by calling the T026 queue primitive rather than implementing queue mutation, and register it in `engine/runner.py` after T026~T029 [FR-021~032, FR-040]
- [X] T031 [US1] Implement H03-A8/A9 evidence-only evaluators and preserve existing H03-A1~A6 semantics in `engine/judges/h03_dlq.py` and `engine/judge.py` [FR-026~032, H03-A1~A9]
- [X] T032 [US1] Run `pytest -q tests/contract/test_whyyou_queue_adapter.py tests/integration/test_h03_dlq_lineage.py tests/unit/test_judge_h03_dlq.py` plus the two WhyYou tests from T021~T022, and record the independently passing US1 gate in `specs/002-h03-e03-fault-expansion/validation.md`

**Checkpoint**: 재시도 소진과 최종 실패 보존·노출을 다른 스토리와 독립적으로 검증할 수 있다.

---

## Phase 4: User Story 2 — 리포트 없는 채용 확정을 모든 경로에서 막는지 확인한다 (Priority: P1)

**Goal**: 정상 최종결정과 batch 최종 단계 이동의 세 test case를 모두 호출하고 응답뿐 아니라 부분 변경 0건을 판정한다.

**Independent Test**: report가 없는 합성 지원자에 대해 `FINAL_DECISION`, `BATCH_MOVE_FINAL_ACCEPT`, `BATCH_MOVE_FINAL_REJECT`를 각각 실행해 거부·무변경을 확인하고 한 경로라도 빠지면 READY/PASS를 금지한다.

### Tests for User Story 2 — write first

- [X] T033 [P] [US2] Add decision adapter contract tests for all three canonical path IDs, company actor, final-stage snapshot, explicit refusal, accepted bypass, partial writes and sanitized `Idempotency-Key` digest in `tests/contract/test_whyyou_decision_adapter.py` [FR-017, FR-033~039, FR-091, EV2-07, EV2-08]
- [X] T034 [P] [US2] Add H03-A7 judge tests for all-path refusal, missing path registration, accepted batch bypass, changed stage/invitation/HumanReview/audit and automatic system decision in `tests/unit/test_judge_h03_decisions.py` [H03-A7]
- [X] T035 [P] [US2] Add an integration fixture proving two operation capabilities produce three isolated decision cases and each pre/post effect snapshot is tied to its path and logical operation in `tests/integration/test_h03_decision_paths.py` [FR-033~039]

### Implementation for User Story 2

- [X] T036 [US2] Implement final-decision and final-stage batch calls, stable target error mapping, path isolation and same-state reset in `engine/adapters/whyyou/decisions.py` [FR-033~039, FR-091]
- [X] T037 [P] [US2] Implement minimal decision-effect projection for stage assignment/version, invitation status, HumanReview and `final_decision.create` audit in `engine/adapters/whyyou/effects.py`, returning `ABSENT` only after a successful scoped query and `UNAVAILABLE` on access failure [FR-037~038, FR-094]
- [X] T038 [US2] Extend `engine/adapters/whyyou/capability.py` to enumerate both operations and three canonical cases from the pinned WhyYou OpenAPI/stage snapshot; block PASS when any final-effect path is unregistered [FR-017, FR-035, FR-091]
- [X] T039 [US2] Add the three decision attempts and pre/post decision-effect observations to `engine/executors/h03_dlq.py` without allowing one case to contaminate the next [FR-033~040]
- [X] T040 [US2] Implement H03-A7 aggregation and missing-path readiness enforcement in `engine/judges/h03_dlq.py` [FR-035~039, H03-A7]
- [X] T041 [US2] Run `pytest -q tests/contract/test_whyyou_decision_adapter.py tests/unit/test_judge_h03_decisions.py tests/integration/test_h03_decision_paths.py` and record the independently passing US2 gate in `specs/002-h03-e03-fault-expansion/validation.md`

**Checkpoint**: 화면 버튼이 아니라 WhyYou의 모든 확인된 최종 채용 효과 경로를 검증한다.

---

## Phase 5: User Story 3 — 리포트 저장 전 장애에서 누락 없는 복구를 확인한다 (Priority: P1)

**Goal**: BEFORE 장애 중 완료 효과 0건과 안전한 DLQ redrive 후 reporting 필수 효과의 정확한 복구를 판정한다.

**Independent Test**: BEFORE 장애 Run에서 report/projection/processed marker 부재를 확인하고, marker 해제와 safe redrive 뒤 report 1건·일관된 projection 집합·processed key 1건·원 Outbox 보존을 확인한다.

### Tests for User Story 3 — write first

- [X] T042 [P] [US3] Add reporting effect projection tests for scoped report IDs, deterministic projection set, processed key `(consumer_name,event_id,event_version)`, original Outbox status, empty-success and unavailable sources in `tests/contract/test_whyyou_effect_adapter.py` [FR-041~050, FR-092~093, EV2-02, EV2-10]
- [X] T043 [P] [US3] Add safe-redrive tests for identical body/attributes, send-before-delete, send failure preserving DLQ, send-success/delete-failure restore uncertainty, foreign-message isolation and recovered polling in `tests/unit/test_whyyou_queue_redrive.py` [FR-041~044, E03-A4, E03-A8]
- [X] T044 [P] [US3] Add E03-A1~A4/A8 judge tests covering complete lineage, attempt mismatch, partial effects during fault, missing/duplicate/inconsistent recovered effects, access loss and restore failure in `tests/unit/test_judge_e03_before.py` [E03-A1~A4, E03-A8]
- [X] T045 [P] [US3] Add a BEFORE integration journey from seed through DLQ, injected-effect absence, marker restore, redrive and recovered reporting effects in `tests/integration/test_e03_before.py` [FR-041~050]

### Implementation for User Story 3

- [X] T046 [US3] Implement scoped reporting-effect reads and canonical identity/digest projection in `engine/adapters/whyyou/effects.py`, excluding report-completed Outbox events that WhyYou does not create [FR-041~050, FR-092~093]
- [X] T047 [US3] After T026 and T043, integrate the existing queue redrive primitive into the common recovery sequence in `engine/execution.py`: require marker removal and worker health before calling it, persist every returned send/delete receipt in `redrive-receipts.jsonl`, map delete uncertainty to `RESTORE_FAILED`, coordinate recovered-result polling through the effect adapter, and migrate the T030 H-03 caller to this shared sequence without reimplementing queue mutation [FR-041~044, FR-066~074, EV2-09]
- [X] T048 [P] [US3] Extend `engine/adapters/whyyou/fault.py` to parse and validate BEFORE boundary receipts against run/session/event/attempt and to prove marker removal independently from reporting recovery [FR-023, FR-043, E03-A3, E03-A8]
- [X] T049 [P] [US3] Create `E03_BEFORE_V2` with assertions E03-A1~A4/A7/A8, required EV2 mapping and canonical timing/restore policy in `scenarios/E-03-BEFORE.yaml` [FR-019, FR-041~055]
- [X] T050 [US3] Implement the BEFORE action pipeline through recovered reporting effects in `engine/executors/e03_before.py` so integration tests can call the pipeline and E03-A1~A4/A8 judges directly; do not add a subset runtime profile, CLI mode, runner registration or partial scenario verdict before US5 adds A7 [FR-041~050]
- [X] T051 [US3] Implement shared E-03 lineage/effect comparison plus E03-A1~A4/A8 evaluators in `engine/judges/common.py` and `engine/judges/e03.py` [FR-041~050, E03-A1~A4, E03-A8]
- [X] T052 [US3] Run `pytest -q tests/contract/test_whyyou_effect_adapter.py tests/unit/test_whyyou_queue_redrive.py tests/unit/test_judge_e03_before.py tests/integration/test_e03_before.py` and record the independently passing US3 subset gate, explicitly marking E03-A7 as pending US5 rather than PASS, in `specs/002-h03-e03-fault-expansion/validation.md`

**Checkpoint**: 저장 전 장애의 계보와 누락 없는 reporting 복구를 독립 판정할 수 있다.

---

## Phase 6: User Story 4 — 리포트 저장 후 재전달에서 중복 효과를 막는지 확인한다 (Priority: P1)

**Goal**: DB commit 후 SQS ack 전의 일회성 장애와 재전달 duplicate-ack를 실제 경계 증적으로 검증한다.

**Independent Test**: AFTER marker가 commit 뒤 ack만 한 번 생략하고, 재전달은 handler 재실행 없이 processed marker 분기에서 ack하며 reporting 효과가 한 세트인지 확인한다.

### Tests for User Story 4 — write first

- [X] T053 [P] [US4] In the WhyYou personal branch, add failing tests for exact `handler → processed record → transaction commit → after-commit hook → SQS acknowledge` order, one-shot ack drop, fsynced boundary receipt and production rejection in `../gbsa_aws/backend/tests/integration/test_worker_delivery.py` and `../gbsa_aws/backend/tests/unit/runtime/test_controlproof_reporting_fault.py` [FR-045, FR-089]
- [X] T054 [US4] After T053, add duplicate-redelivery tests proving the processed-message branch skips the handler, acknowledges the message and emits a sanitized duplicate-ack receipt in `../gbsa_aws/backend/tests/integration/test_worker_delivery.py` [FR-046~047, FR-090]
- [X] T055 [P] [US4] Add AFTER marker/boundary/duplicate-ack adapter contract tests including wrong event, wrong boundary, repeated one-shot trigger and missing independent effects in `tests/contract/test_whyyou_after_commit_fault.py` [FR-045~048]
- [X] T056 [P] [US4] Add E03-A1/A5/A6/A8 judge and full profile integration cases for correct duplicate-ack, handler rerun, duplicate report/projection/marker, boundary not reached and unexpected DLQ in `tests/unit/test_judge_e03_after.py` and `tests/integration/test_e03_after.py` [E03-A1, E03-A5, E03-A6, E03-A8]

### Implementation for User Story 4

- [X] T057 [US4] In the WhyYou personal branch, add the local/test-only one-shot AFTER marker and boundary receipt behavior in `../gbsa_aws/backend/src/interview_evidence/runtime/controlproof_faults.py` [FR-045, FR-089]
- [X] T058 [US4] In the WhyYou personal branch, invoke the optional AFTER hook only after transaction commit and before SQS acknowledge, and emit duplicate-ack observation from the existing processed-message short circuit in `../gbsa_aws/backend/src/interview_evidence/shared/messaging/worker.py` and `../gbsa_aws/backend/src/interview_evidence/runtime/worker.py` [FR-045~047, FR-089~090]
- [X] T059 [US4] Extend `engine/adapters/whyyou/fault.py` with AFTER marker creation, one-shot boundary receipt validation and duplicate-ack reading without treating a marker-write receipt as boundary proof [FR-045~048]
- [X] T060 [P] [US4] Create `E03_AFTER_V2` with only E03-A1/A5/A6/A8, no terminal-DLQ expectation, EV2-01~04/09/10/12 and 60-second boundary/duplicate deadline in `scenarios/E-03-AFTER.yaml` [FR-019, FR-045~050]
- [X] T061 [US4] Implement AFTER flow and effect snapshots in `engine/executors/e03_after.py` and register it without sharing mutable state with the BEFORE executor [FR-045~050]
- [X] T062 [US4] Implement E03-A5/A6 evaluators, unexpected-DLQ handling and exact reporting effect comparison in `engine/judges/e03.py` [E03-A5, E03-A6]
- [X] T063 [US4] Run the T053~T056 WhyYou and ControlProof tests, then record the independently passing US4 gate in `specs/002-h03-e03-fault-expansion/validation.md`

**Checkpoint**: 저장 후 재전달의 중복 억제가 저장 전 장애와 섞이지 않은 별도 Run으로 검증된다.

---

## Phase 7: User Story 5 — 복구 후 사람 결정 이력을 정확히 한 번 보존한다 (Priority: P2)

**Goal**: 같은 `Idempotency-Key`의 사람 결정을 두 번 보내도 단계·invitation·HumanReview·감사가 정확히 한 세트인지 판정한다.

**Independent Test**: 리포트가 복구된 합성 지원자에게 동일한 결정 요청을 두 번 보내고 네 가지 결정 효과의 identity와 logical count를 비교한다.

### Tests for User Story 5 — write first

- [X] T064 [P] [US5] Add final-decision replay contract tests for identical hashed key/body/stage, first-response loss, equivalent replay result, target ignoring the key, changed-key non-equivalence and raw-key redaction in `tests/contract/test_whyyou_decision_replay.py`; add a failing composition contract that requires queue, decision, effect, BEFORE/AFTER fault and restore capabilities with exact versions in `tests/contract/test_whyyou_adapter_v2_composition.py`; add a failing registry contract proving `E03_BEFORE_V2` dispatches to `E03BeforeExecutor` only after the full composition is available in `tests/contract/test_profile_registry_v2.py` [FR-011~020, FR-051~055, FR-094~095, EV2-11]
- [X] T065 [P] [US5] Add E03-A7 judge tests for exactly one complete decision effect set, missing/duplicate stage/HumanReview/audit, contradictory invitation, wrong actor and AI-score-independent human choice in `tests/unit/test_judge_e03_decision.py` [E03-A7]
- [X] T066 [P] [US5] Add an integration journey that continues a recovered BEFORE Run into two same-key decision calls while preserving the reporting lineage in `tests/integration/test_e03_decision_replay.py` [FR-051~055]

### Implementation for User Story 5

- [X] T067 [US5] Implement same-key final-decision replay and stable logical decision identity in `engine/adapters/whyyou/decisions.py`, retaining raw keys only in memory and persisting only their SHA-256 [FR-051~055, FR-095]
- [X] T068 [P] [US5] Extend decision effect comparison in `engine/adapters/whyyou/effects.py` to require one stage assignment, invitation `reviewed`, one COMPANY_USER HumanReview and one `final_decision.create` audit, with no completion Outbox requirement [FR-052~055, FR-094]
- [X] T069 [US5] Implement E03-A7 in `engine/judges/e03.py`, treating a successfully observed duplicate/missing effect as FAIL and inaccessible evidence as INCONCLUSIVE [E03-A7]
- [X] T070 [US5] Complete the post-recovery decision replay steps in `engine/executors/e03_before.py` so the canonical E03_BEFORE_V2 profile can receive a full verdict only after A7/A8 are evaluated, compose queue, decision, effect and both fault-boundary adapters with their capability versions in `engine/adapters/whyyou/adapter.py`, and then register `E03_BEFORE_V2 → E03BeforeExecutor` in `engine/runner.py` only after the complete composition is available [FR-011~020, FR-051~055]
- [X] T071 [US5] Run `pytest -q tests/contract/test_whyyou_decision_replay.py tests/contract/test_whyyou_adapter_v2_composition.py tests/contract/test_profile_registry_v2.py tests/unit/test_judge_e03_decision.py tests/integration/test_e03_decision_replay.py tests/integration/test_e03_before.py` and record the independently passing US5 gate in `specs/002-h03-e03-fault-expansion/validation.md`

**Checkpoint**: reporting 복구 뒤 사람 결정의 정확히 한 번 효과를 AI 점수와 무관하게 판정한다.

---

## Phase 8: User Story 6 — H-03과 E-03을 독립적으로 설명하고 재시험한다 (Priority: P2)

**Goal**: 세 profile의 독립 verdict, 환경 한계, 증적 무결성, 최초 FAIL과 수정 후 retest 계보를 CLI에서 설명한다.

**Independent Test**: H-03만 FAIL, E-03만 FAIL, 한쪽 INCONCLUSIVE, 모두 PASS fixture와 parent→child retest를 실행해 서로 verdict를 덮지 않고 sealed bundle을 보존하는지 확인한다.

### Tests for User Story 6 — write first

- [X] T072 [P] [US6] Add CLI contracts for mandatory profile selection on E-03, H03 v1 default compatibility, additive output fields, exit codes, applied/remaining assertions, AWS `NOT_RUN` and no semantic override flags in `tests/contract/test_cli_profiles_v2.py` [FR-066~080, FR-081~087]
- [X] T073 [P] [US6] Add presentation tests for separate H-03/E-03 verdicts, failure route, path coverage, missing/duplicate effects, remaining variant coverage, implementation status, cloud-unverified scope, `claim_scope=EXECUTED_SCENARIO_AND_EVIDENCE_ONLY`, and the explicit statement that results do not certify or guarantee overall legal compliance in `tests/contract/test_presentation_spec002.py` [FR-077~079, SC-012, SC-014]
- [X] T074 [P] [US6] Add retest tests proving profile/fault inheritance, new Run ID, environment/queue/target diff, parent read-only digest and cross-Run evidence origin verification in `tests/integration/test_spec002_retest_lineage.py` [FR-075~080]
- [X] T075 [P] [US6] Add the four-way independent verdict matrix and required-evidence integrity cases in `tests/integration/test_spec002_verdict_matrix.py` [SC-002~010]

### Implementation for User Story 6

- [X] T076 [US6] Implement `--profile` dispatch, preflight/run/show/verify/retest v2 projections and stable exit semantics in `engine/cli.py`, keeping the outer schema `controlproof.cli.v1` [FR-066~080]
- [X] T077 [P] [US6] Extend `engine/presentation.py` with independent scenario/profile verdicts, remaining variant coverage, actual failure route, effect differences, restore status, AWS `NOT_RUN`, unverified scope, structured `claim_scope=EXECUTED_SCENARIO_AND_EVIDENCE_ONLY`, and a human-readable no-certification/no-guarantee statement for overall legal compliance [FR-077~079, FR-086, SC-012, SC-014]
- [X] T078 [US6] Extend `engine/retest.py` to inherit scenario/profile/fault, compare target/environment/queue digests, reject unsafe cleanup state and preserve parent/cross-Run origin digests [FR-075~080, FR-087]
- [X] T079 [US6] Run the T072~T075 contracts plus the full deterministic three-profile suite and record results in `specs/002-h03-e03-fault-expansion/validation.md`

### Actual-stack FAIL → remediation → retest gate

- [X] T080 [US6] On clean ControlProof and WhyYou personal branches, execute all three quickstart preflights and record only non-sensitive commit/digest/topology/readiness data in `specs/002-h03-e03-fault-expansion/validation.md`; do not create a Run unless every profile is READY [FR-081~088]
- [X] T081 [US6] Execute and seal one initial `H03_DLQ_V2`, `E03_BEFORE_V2`, and `E03_AFTER_V2` Run before any WhyYou protection fix; verify every bundle and record Run ID, verdict, failed/inconclusive assertions, bundle digest and restore status in `specs/002-h03-e03-fault-expansion/validation.md` [FR-079~080, FR-096, SC-001, SC-003~006, SC-008~009, SC-011, SC-013]
- [ ] T082 [US2] Only if the sealed H03-A7 result proves a batch-final-stage bypass, add failing coverage in `../gbsa_aws/backend/tests/integration/reporting/test_recruiting_stage_decision.py` and route the `최종합격|불합격` batch path through the report-required protection in `../gbsa_aws/backend/src/interview_evidence/company_management/application/hiring_service.py`; otherwise record `NOT_REQUIRED` with the artifact reference in `specs/002-h03-e03-fault-expansion/validation.md` [H03-A7]
- [ ] T083 [US1] Only if the sealed H03-A9 result proves final failure is hidden, record the evidence, persistence/API/UI alternatives, selected additive design and exact target files in `specs/002-h03-e03-fault-expansion/implementation-decisions.md`; if H03-A9 is the only direct FAIL, keep Spec 002 completion blocked until the selected follow-up implementation and parent-linked PASS retest are complete rather than closing it as `DEFERRED` [FR-096, H03-A9]
- [ ] T084 [US5] Only if the sealed E03-A7 result proves duplicate decision effects, add failing coverage in `../gbsa_aws/backend/tests/integration/reporting/test_final_decision_idempotency.py`, implement idempotent command ownership in `../gbsa_aws/backend/src/interview_evidence/reporting/application/final_decision_service.py`, and make `../gbsa_aws/backend/src/interview_evidence/reporting/api/company_routes.py` delegate to that application service; otherwise record `NOT_REQUIRED` with the artifact reference in `specs/002-h03-e03-fault-expansion/validation.md` [E03-A7]
- [ ] T085 [US6] If any initial Run directly FAILed, create at least one evidence-driven target fix and parent-linked PASS retest for an affected profile, verify every parent and child bundle, and record the change without rewriting history; if all three initial Runs PASSed, re-verify and link the approved Spec 001 representative FAIL→PASS bundle pair instead of manufacturing a defect in `specs/002-h03-e03-fault-expansion/validation.md` [FR-075~080, FR-096, SC-010, SC-015]

**Checkpoint**: 세 profile의 최초 결과와 수정 후 결과가 독립적이고 불변인 증적 계보로 남는다.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 보안, 시간 제한, 추적성, 재현성과 팀 인계를 전체 스토리에 걸쳐 마감한다.

- [ ] T086 [P] Extend the secret/PII regression corpus to queue URLs, receipt handles, message bodies, Idempotency-Key, DB projections and all new v2 artifacts in `tests/unit/test_redaction_security.py` [FR-061~063, SC-011]
- [ ] T087 [P] Add deterministic clock tests proving 360-second DLQ, 60-second duplicate-ack, 180-second recovery and 600-second whole-Run deadlines come only from the scenario snapshot in `tests/integration/test_spec002_timing.py` [SC-001]
- [ ] T088 Add an FR/SC/H03-A/E03-A/EV2 → task → test → implementation traceability matrix in `specs/002-h03-e03-fault-expansion/traceability.md` [Constitution VII]
- [ ] T089 [P] Update team-facing setup, branch safety, profile meanings, AWS `NOT_RUN`, first FAIL preservation and result interpretation in `README.md`, including the exact boundary that ControlProof reports only executed scenarios and captured evidence and does not certify or guarantee overall legal compliance [SC-012, SC-014]
- [ ] T090 Execute every command in `specs/002-h03-e03-fault-expansion/quickstart.md` from a clean environment and correct only inaccurate command/path/document assumptions found during execution
- [ ] T091 Run `ruff check .` and the complete ControlProof `pytest -q` suite plus the scoped WhyYou tests, then record commands, counts, durations, known target FAILs, restore status and final source SHAs in `specs/002-h03-e03-fault-expansion/validation.md`

---

## Dependencies & Execution Order

### Phase dependencies

```text
Phase 1 Setup
    ↓
Phase 2 Foundation
    ↓
Phase 3 US1 — retry/DLQ/failure visibility
    ├──────────────→ Phase 4 US2 — all decision paths
    ├──────────────→ Phase 5 US3 — BEFORE recovery
    └──────────────→ Phase 6 US4 — AFTER duplicate-ack
                         ↓
                 Phase 7 US5 — human decision replay
                         ↓
                 Phase 8 US6 — independent results/retest
                         ↓
                 Phase 9 Polish/validation
```

- **Setup** has no dependency.
- **Foundation** depends on Setup and blocks every story.
- **US1** establishes source event, delivery/DLQ and recovery primitives used by US2/US3.
- **US2** can start after US1 queue lineage is stable; its fake-adapter tests can start after Foundation.
- **US3** reuses US1 safe redrive and completes the BEFORE reporting portion; it does not emit a canonical E-03 PASS until US5 adds A7.
- **US4** reuses effect identity from US3 but uses an isolated Run and can proceed in parallel with US2 after Foundation/adapter contracts stabilize.
- **US5** requires a recovered report path from US3.
- **US6** requires all canonical profile assertions, bundle verification and restore behavior.
- **T080~T081** are the first actual-stack Runs and must occur before **T082~T084** target remediation.
- **Polish** depends on every story selected for the release and any affected retest.

### Key task dependencies

- T011 blocks T012~T018; T012~T018 block user-story implementation.
- T020~T024 precede T025~T031; T026/T027/T029 block T030.
- T033~T035 precede T036~T040; T036~T039 block T040.
- T042~T045 precede T046~T051; T047/T048/T049 block T050.
- T053~T056 must fail before T057~T062 modify the AFTER boundary.
- T064~T066 precede T067~T070; T070 completes canonical E03_BEFORE_V2.
- T072~T075 precede T076~T078.
- T081 must be sealed and verified before any T082, T083 or T084 change.
- T085 requires at least one parent FAIL→child PASS pair whenever T081 contains a direct FAIL; if T081 is all PASS, T085 verifies the approved Spec 001 representative pair and must preserve every digest.

## Parallel Opportunities

### Foundation

```text
T005 models | T006 scenario | T007 execution | T008 bundle | T009 environment | T010 v1 regression
after T011: T013 protocols | T016 evidence | T017 config | T018 fake adapters
```

### User Story 1

```text
Tests: T020 queue contract | T021 WhyYou topology | T022 WhyYou receipts | T023 journey | T024 judge
Implementation: T025 target receipt | T028 browser | T029 scenario; then T026/T027 → T030 → T031
```

### User Story 2

```text
T033 adapter contract | T034 judge | T035 integration
after contracts: T036 decisions | T037 effects; then T038/T039 → T040
```

### User Story 3

```text
T042 effects | T043 redrive | T044 judge | T045 integration
after tests: T046 effects | T048 BEFORE receipt | T049 scenario; T047 blocks final recovery path
```

### User Story 4

```text
T053 target boundary; then T054 duplicate delivery in the same test file
in parallel with that chain: T055 adapter | T056 judge/integration
after all four tests: T057 marker | T060 scenario; then T058/T059 → T061/T062
```

### User Story 5

```text
T064 replay contract | T065 judge | T066 integration
after tests: T067 decision replay | T068 effect comparison; then T069/T070
```

### User Story 6

```text
T072 CLI | T073 presentation | T074 retest | T075 verdict matrix
after tests: T077 presentation can proceed beside T078 retest while T076 owns CLI
```

## Implementation Strategy

### First independently demonstrable slice

1. Complete Setup and Foundation.
2. Complete US1.
3. Stop and verify retry exhaustion, DLQ lineage and final-failure visibility with deterministic fixtures.
4. Do not describe this slice as full Spec 002 or full 2-week MVP completion.

### Two-week P1 core

1. Complete US1 and US2 for H-03 decision safety.
2. Complete US3 and US4 for both E-03 fault boundaries.
3. Run all deterministic profile tests.
4. Add US5 and US6 for human-decision idempotency, independent explanation and immutable retest evidence.

### Actual target closure

1. Preflight all profiles on clean personal branches.
2. Seal and verify the three initial Runs.
3. Treat a truthful WhyYou FAIL as a valid ControlProof result.
4. Apply only evidence-confirmed target fixes from T082~T084.
5. Retest as new child Runs; never replace the original FAIL.

### Team split after Foundation

- Developer A: US1 queue/DLQ and H-03 executor/judge
- Developer B: US2 decision paths and US5 human-decision replay
- Developer C: US3/US4 effect observer and WhyYou fault boundaries
- Shared review: US6 bundle/CLI/retest, first actual Runs and remediation gate

## Notes

- Tests listed before implementation must fail for the intended missing behavior before production code is changed.
- WhyYou tasks run only on `bosung/controlproof-h03-integration` or a descendant personal branch; never on `main`.
- The actual AWS environment remains `NOT_RUN`; LocalStack PASS cannot be promoted to AWS PASS.
- A delivery attempt is not a business-effect duplicate. Judges compare the explicit logical identities in `data-model.md`.
- Do not add application `JobStatus.DLQ`, completion Outbox events, a generic chaos framework, or a web workbench under this Spec.
- Do not store actual applicants, raw credentials, receipt handles, full message bodies, full logs or DB dumps.
- ControlProof implementation completion and WhyYou scenario verdict remain separate.
- Every task is complete only when its linked tests pass and the relevant source path is committed in the correct repository.
