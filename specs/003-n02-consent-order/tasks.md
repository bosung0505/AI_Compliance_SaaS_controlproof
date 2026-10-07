---

description: "Spec 003 N-02 동의·AI 처리 순서 검증의 구현 작업 목록"
---

# Tasks: N-02 동의·AI 처리 순서 검증

**Input**: `specs/003-n02-consent-order/`의 spec, plan, research, data model, contracts, quickstart
**Tests**: Spec이 assertion별 단위·계약·통합 시험, 최초 actual Run과 불변 retest를 요구하므로 테스트 작업을 구현보다 먼저 포함한다.
**Organization**: 공통 기반 뒤에 5개 사용자 스토리를 독립 검증 가능한 증분으로 구성한다. `[FR-*]`, `[N02-A*]`, `[EV3-*]`는 추적 ID다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 선행조건이 충족되면 다른 파일의 작업과 병렬 실행 가능
- **[Story]**: 기능 Spec의 사용자 스토리
- 모든 작업은 수정하거나 생성할 정확한 파일 경로를 포함한다.
- `../gbsa_aws/` 작업은 WhyYou 개인 브랜치에서만 수행하며 `main` 또는 `master`에 직접 commit·push하지 않는다.
- 조건부 보완 작업은 최초 actual Run을 봉인하기 전에 수행하지 않는다. 조건이 성립하지 않으면 증적 참조와 함께 `NOT_REQUIRED`로 기록한다.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: N-02 local/test 설정, 고정 fixture와 구현 기록의 뼈대를 준비한다.

- [X] T001 Add secret-free N-02 variable names and loopback examples for WhyYou API, PostgreSQL, LocalStack, fixed AI fixture, fault root, observer and target repository to `.env.example` [FR-004~006, FR-026, FR-039]
- [X] T002 [P] In the WhyYou personal branch, add disabled-by-default `CONTROLPROOF_TEST_HOOKS_ENABLED`, `CONTROLPROOF_OBSERVER_ENABLED`, local fault-root and fixed-fixture examples to `../gbsa_aws/.env.example`, with an explicit local/test-only warning [FR-026, FR-039, SC-011]
- [X] T003 [P] Create deterministic builders for six subject lanes, policy/consent snapshots, three path attempts/effects, causal events/edges, consent-fault receipts, recovery records and PASS/FAIL/INCONCLUSIVE facts in `tests/fixtures/spec003.py` [FR-007, FR-034~038, EV3-01~EV3-10]
- [X] T004 [P] Create implementation-time record templates with source-SHA, commands, Run IDs, bundle digests, conditional remediation and requirement mappings in `specs/003-n02-consent-order/validation.md`, `specs/003-n02-consent-order/traceability.md` and `specs/003-n02-consent-order/implementation-decisions.md`; do not claim an unexecuted result [FR-002, FR-033, FR-037~041]

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 스토리가 공유하는 scenario v3, profile registry, N-02 모델, 안전 guard와 bundle profile을 먼저 고정한다.

**⚠️ CRITICAL**: 이 Phase가 완료되기 전에는 사용자 스토리 구현을 시작하지 않는다.

### Foundation tests — write first and confirm failure

- [X] T005 [P] Add model tests for canonical six lanes, three protected paths, policy/consent facts, `ABSENT` versus `UNAVAILABLE`, effect deltas, causal edges, fault receipts and recovery cardinality in `tests/unit/test_models_spec003.py` [FR-006~012, FR-014~017, FR-026~032]
- [X] T006 [P] Add scenario v3 contract tests for exact profile `N02_CONSENT_ORDER_V1`, A1~A7, EV3-01~10, six lanes, ordered steps, fixed timing, always-run restore/teardown and forbidden N-01/N-03 steps in `tests/contract/test_scenario_profile_v3.py` [FR-001~004, N02-A1~A7]
- [X] T007 [P] Add additive bundle tests for `controlproof.bundle-profile.spec003.v1`, all ten N-02 canonical files, EV3 cross-references, v1/v2 compatibility and read-only tamper detection in `tests/contract/test_bundle_profile_spec003.py` [FR-002, FR-033, FR-037~039, EV3-01~EV3-10]
- [X] T008 [P] Add CLI/profile registry tests for mandatory N-02 profile selection, stable exit codes, unchanged Spec 001/002 dispatch and non-READY preflight leaving Run directory, subject row, marker and event all absent in `tests/contract/test_cli_n02_profile.py` and `tests/contract/test_profile_registry_v3.py` [FR-001~006]
- [X] T009 [P] Add composed-adapter protocol tests for consent, seed, protected processing, effect, causality, fault and observer capabilities with exact readiness precedence and non-empty sanitized `operator_action` for every non-READY result in `tests/contract/test_whyyou_n02_adapter.py` [FR-003~006, FR-013~017, FR-026~032]
- [X] T010 [P] In the WhyYou personal branch, add startup/no-op tests for local/test-only fault and observer controls, production/staging rejection, invalid paths and disabled defaults in `../gbsa_aws/backend/tests/unit/runtime/test_controlproof_consent.py` [FR-026, FR-039, SC-011]
- [X] T011 [P] Extend security tests to reject applicant PII, policy text, answer/document/report text, credentials, presigned query data and absolute user-specific paths from N-02 artifacts in `tests/unit/test_redaction_security.py` [FR-038~039, SC-011]
- [X] T012 [P] Extend the installed-package and Spec 001 regression tests in `tests/contract/test_package_layout.py` and `tests/integration/test_spec001_v1_regression.py`, and create `tests/integration/test_spec002_v2_regression.py`, to load `engine.executors.n02` and `engine.judges.n02` while executing and verifying unchanged v1/v2 profiles and sealed fixtures [FR-001~002]

### Foundation implementation

- [X] T013 Implement the data-model entities and exact invariants from `data-model.md` in `engine/models.py`, including profile, lane, path, policy, consent, effect, attempt, causal, fault and recovery records [FR-006~012, FR-014~017, FR-026~038]
- [X] T014 Implement additive scenario v3 loading and canonical N-02 validation in `engine/scenario.py`; preserve v1/v2 behavior and reject semantic CLI overrides [FR-001~004]
- [X] T015 [P] Add service-neutral N-02 consent, seed, processing, effect, causality, observer and fault protocols with sanitized result envelopes in `engine/adapters/base.py` after T013 [FR-003~006, FR-013~017, FR-026~032]
- [X] T016 [P] Extend `engine/config.py` with typed N-02 local/test settings and fail-closed validation for loopback services, fixed AI fixtures, non-main clean target checkout, bounded fault root and external-AI denial [FR-004~006, FR-026, FR-039, SC-011]
- [X] T017 Refactor profile-specific validation and dispatch in `engine/runner.py` so N-02 does not inherit Spec 002 queue requirements, while preserving all registered v1/v2 profiles [FR-001~006]
- [X] T018 [P] Extend `engine/evidence.py` with the Spec 003 profile registry, canonical N-02 writers/verifiers, EV3 mapping and cross-reference checks without rewriting existing sealed bundles [FR-002, FR-033, FR-037~039, EV3-01~EV3-10]
- [X] T019 Extend deterministic fake adapters with independent path response/effect, causal-order, source-unavailable, fault-trigger, restore and recovery outcomes in `tests/fixtures/fake_adapters.py` after T013 and T015 [FR-014~019, FR-024, FR-027~032]
- [X] T020 In the WhyYou personal branch, create the disabled-by-default marker, receipt, observer and environment-guard primitives in `../gbsa_aws/backend/src/interview_evidence/runtime/controlproof_consent.py`; enforce Run/lane/subject allowlists, TTL ≤600 seconds, one-shot ownership, fsync-before-fault-trigger and sanitized payloads, while observer write/flush failure remains non-fatal to the product transaction [FR-026~027, FR-037~039]
- [X] T021 In the WhyYou personal branch, wire the T020 guard objects only for local/test runtime composition in `../gbsa_aws/backend/src/interview_evidence/runtime/production.py` and `../gbsa_aws/backend/src/interview_evidence/runtime/worker.py`; production/staging enablement must fail startup [FR-026, FR-039, SC-011]
- [X] T022 [P] In the WhyYou personal branch, add only the bounded N-02 marker/receipt directory mounts and local environment variables required by T020 to `../gbsa_aws/compose.yaml`; do not expose a public fault endpoint [FR-026, FR-039]
- [X] T023 Run the T005~T012 foundation tests plus the scoped WhyYou T010 tests, and record exact commands and results in `specs/003-n02-consent-order/validation.md` [FR-001~006, FR-026, FR-037~039, SC-011]

**Checkpoint**: Spec 001·002 회귀를 깨뜨리지 않는 N-02 공통 모델·계약·안전 기반이 준비된다.

---

## Phase 3: User Story 1 — 동의 전 보호 대상 처리를 우회 시도한다 (Priority: P1) 🎯 First Slice

**Goal**: 서로 격리된 미동의 subject에서 자료 분석·녹화·AI 평가의 실제 경계를 시도하고 요청과 사후 효과를 함께 판정한다.

**Independent Test**: fake adapter의 여섯 lane 중 pristine 및 세 bypass/probe lane만 실행해 A1~A4를 평가하고, 거부+0 delta는 PASS, 직접 효과는 FAIL, 사후 조회 불가는 INCONCLUSIVE인지 확인한다.

### Tests for User Story 1 — write first

- [X] T024 [P] [US1] Add seed/teardown contract tests for six deterministic subjects, pristine invariants, recording/assessment fixture allowlists, digest stability, lane isolation, current-Run-only cleanup and whole-transaction rollback when any lane seed fails in `tests/contract/test_n02_seed_adapter.py` [FR-007~008, EV3-01, EV3-03]
- [X] T025 [P] [US1] Add protected-processing adapter tests for the actual upload-intent, interview-session and report-event boundaries, directness metadata, sanitized responses, effect projection and `ABSENT`/`UNAVAILABLE` distinction in `tests/contract/test_n02_processing_adapter.py` [FR-003, FR-013~019, EV3-04~EV3-05]
- [X] T026 [P] [US1] In the WhyYou personal branch, add receipt validation, foreign Run/lane rejection, PII exclusion and non-fatal writer I/O failure tests in `../gbsa_aws/backend/tests/unit/runtime/test_controlproof_n02_observer.py`, plus actual analysis/session create/session start/recording confirm/report boundary integration tests in `../gbsa_aws/backend/tests/integration/interview_engine/test_controlproof_n02_observer.py` [FR-014~017, FR-037~039]
- [X] T027 [P] [US1] Add A1~A4 judge tests for valid pristine baseline, denied+zero delta PASS, each prohibited effect FAIL, missing post-effect INCONCLUSIVE and baseline precondition abort in `tests/unit/test_judge_n02_bypass.py` [FR-008, FR-018~019, N02-A1~A4]
- [X] T028 [P] [US1] Add isolated document, recording and assessment bypass journeys with deterministic fake adapters in `tests/integration/test_n02_bypass_orchestration.py` [FR-007, FR-013~019, N02-A1~A4]
- [X] T029 [P] [US1] Add fixture/delta isolation tests proving deep-probe prerequisite effects are excluded from new effects and no lane or subject can satisfy another lane's assertion in `tests/integration/test_n02_lane_isolation.py` [FR-007, FR-014, EV3-03~EV3-05]

### Implementation for User Story 1

- [X] T030 [P] [US1] Create deterministic canonical subject definitions and stable synthetic identities in `seeds/n02_subjects.py`; never use deliverable real email addresses or existing demo subjects [FR-007, FR-039]
- [X] T031 [US1] Implement WhyYou lane seed as one atomic transaction with full rollback on any lane failure, plus pristine/deep-fixture snapshots, digest verification and allowlisted teardown in `engine/adapters/whyyou/n02_seed.py` using T030 [FR-007~008, EV3-01, EV3-03]
- [X] T032 [P] [US1] Implement actual document upload-intent, recording create-session and assessment `report.generation_requested` attempts plus path capability/directness capture in `engine/adapters/whyyou/protected_processing.py`; do not add a fake assessment endpoint [FR-003, FR-013~017, EV3-01, EV3-04]
- [X] T033 [US1] Add scoped pre/post effect projections and delta calculation for document, recording and assessment effects to `engine/adapters/whyyou/protected_processing.py`, returning `ABSENT` only after a successful query and `UNAVAILABLE` on source failure [FR-014~019, EV3-03, EV3-05]
- [X] T034 [US1] In the WhyYou personal branch, emit sanitized local/test observer receipts at actual analysis and report handler entry in `../gbsa_aws/backend/src/interview_evidence/workers/analysis/event_handler.py` and `../gbsa_aws/backend/src/interview_evidence/runtime/worker.py` using T020 [FR-014~017, FR-037~039]
- [X] T035 [US1] In the WhyYou personal branch, emit non-fatal session-created/session-started/recording-confirmed observer receipts immediately after `_create_session_once`, `_start_session_once` and `confirm_recording_upload` succeed in `../gbsa_aws/backend/src/interview_evidence/interview_engine/application/session_service.py`; add an optional observer port in `../gbsa_aws/backend/src/interview_evidence/interview_engine/api/__init__.py` and wire it only for local/test in `../gbsa_aws/backend/src/interview_evidence/runtime/production.py`, without changing product authorization [FR-014~016, FR-037~039]
- [X] T036 [P] [US1] Create canonical scenario v3 steps, A1~A7, EV3-01~10, six lanes, fixed timing and always-run cleanup in `scenarios/N-02.yaml` [FR-001, FR-007~008]
- [X] T037 [US1] Implement baseline, three bypass/deep-probe attempts, post-effect capture and guaranteed lane teardown in `engine/executors/n02.py` after T031~T036 [FR-007~019, EV3-01, EV3-03~EV3-05]
- [X] T038 [US1] Implement evidence-only N02-A1~A4 evaluators and direct-FAIL precedence in `engine/judges/n02.py`, and register the judge in `engine/judge.py` [FR-018~019, FR-034~036, N02-A1~A4]
- [X] T039 [US1] Compose the seed, processing/effect and observer capabilities for `whyyou-local-n02-v1` in `engine/adapters/whyyou/adapter.py` and expose exact READY/RUNNER_NOT_READY/ACCESS_BLOCKED reasons with a non-empty sanitized `operator_action` whenever readiness is not READY [FR-003~006]
- [X] T040 [US1] Run T024~T029 and their implementation tests, then record the independently passing A1~A4 gate in `specs/003-n02-consent-order/validation.md` [FR-007~019, N02-A1~A4, EV3-01, EV3-03~EV3-05]

**Checkpoint**: 동의 전 세 처리 경계와 사후 부작용을 독립 판정할 수 있다. 이 단계만으로 N-02 전체 완료를 주장하지 않는다.

---

## Phase 4: User Story 2 — 정상 동의 뒤 처리 순서를 증명한다 (Priority: P1)

**Goal**: 정책 수신, 서버 동의 확정, 세 처리 요청·시작·결과의 인과관계를 정상 한 바퀴로 증명한다.

**Independent Test**: 새 NORMAL_ORDER subject에서 정책을 읽고 동의를 확정한 뒤 세 경로를 실행해 A5를 평가한다. timestamp가 같아도 edge가 있으면 판정하고, edge가 없으면 INCONCLUSIVE로 남긴다.

### Tests for User Story 2 — write first

- [X] T041 [P] [US2] Add consent adapter contracts for policy GET, consent POST, committed consent/state-change/Outbox projection, purpose/digest match, sanitized headers, request timeout and successful-empty versus unavailable reads in `tests/contract/test_n02_consent_adapter.py` [FR-009~012, FR-020, EV3-02]
- [X] T042 [P] [US2] Add causal adapter tests for HTTP command/response, transaction projection, Outbox identity, worker receipt and result edges, including equal timestamps, missing edge and same-fact conflict in `tests/contract/test_n02_causality_adapter.py` [FR-012, FR-021~024, EV3-06]
- [X] T043 [P] [US2] In the WhyYou personal branch, add transaction-level tests proving consent record, invitation transition and consent-completed Outbox commit together or roll back together in `../gbsa_aws/backend/tests/integration/company_management/test_controlproof_n02_consent_transaction.py` [FR-009~012]
- [X] T044 [P] [US2] Add normal-order integration cases for all paths opened after consent, notification-delay tolerance, policy mismatch, consent-response timeout with known and unknown durable state, permanently blocked path and causal evidence loss in `tests/integration/test_n02_normal_order.py` [FR-020~025, N02-A5]
- [X] T045 [P] [US2] Add N02-A5 judge tests for policy identity, three path causal chains, equal-time edges, notification delivery delay, consent-response timeout with unavailable server state, direct order violation and insufficient evidence in `tests/unit/test_judge_n02_order.py` [FR-020~025, N02-A5]

### Implementation for User Story 2

- [X] T046 [US2] Implement policy read, consent commit and scoped consent/state/Outbox projection in `engine/adapters/whyyou/consent.py`; store policy identifiers and purposes but not raw policy text or credentials [FR-009~012, FR-020, EV3-02]
- [X] T047 [P] [US2] Implement normalized causal events/edges from HTTP, database transaction, Outbox, boundary receipt and result identities in `engine/adapters/whyyou/causality.py`; timestamps alone must not invent an edge [FR-012, FR-021~024, EV3-06]
- [X] T048 [US2] Extend `engine/adapters/whyyou/adapter.py` with T046~T047 capabilities and readiness checks for current policy version/digest/purpose set and required boundary receipts [FR-003~006, FR-020~024]
- [X] T049 [US2] Extend `engine/executors/n02.py` with NORMAL_ORDER policy read, one-transaction consent, post-response durable snapshot, downstream processing and causal capture; processing commands must not be sent before the consent response is committed [FR-009~012, FR-020~025]
- [X] T050 [US2] Implement N02-A5 policy/causal-order evaluation in `engine/judges/n02.py`, treating notification delay as an observation rather than an automatic FAIL [FR-020~025, N02-A5]
- [X] T051 [US2] Run T041~T045 and their implementation tests, then record the independently passing normal-order gate in `specs/003-n02-consent-order/validation.md` [FR-009~012, FR-020~025, N02-A5, EV3-02, EV3-06]

**Checkpoint**: 차단뿐 아니라 동의 후 정상 처리가 열리고 그 순서를 증명할 수 있다.

---

## Phase 5: User Story 3 — 동의 저장 실패의 부분 효과와 복구를 검증한다 (Priority: P1)

**Goal**: 동의 record flush 뒤 상태·Outbox 전의 한 지점에서 실패시키고 전체 rollback, 미동의 차단, marker 제거와 같은 subject의 정상 복구를 증명한다.

**Independent Test**: CONSENT_FAULT_RECOVERY subject에 one-shot marker를 적용해 실제 trigger receipt와 부분 효과 0건을 확인하고, 세 임시 probe 뒤 pristine digest를 복원한 다음 정상 동의 효과가 정확히 한 세트인지 평가한다.

### Tests for User Story 3 — write first

- [X] T052 [P] [US3] Add fault-adapter contracts for canonical marker schema, subject ownership, TTL, one-shot token, fsynced matching receipt, path traversal defense, safe restore and foreign marker isolation in `tests/contract/test_whyyou_consent_fault.py` [FR-026~032, EV3-07]
- [X] T053 [P] [US3] In the WhyYou personal branch, add marker validation/concurrency/fsync-failure tests and verify disabled, expired, wrong-subject, wrong-Run and production cases are safe no-ops in `../gbsa_aws/backend/tests/unit/runtime/test_controlproof_consent.py` [FR-026~027, FR-039]
- [X] T054 [P] [US3] In the WhyYou personal branch, add an integration test that triggers after `save_consent()` but before state/Outbox, returns 5xx and leaves consent/state-change/Outbox zero on a separate connection in `../gbsa_aws/backend/tests/integration/company_management/test_controlproof_n02_consent_rollback.py` [FR-027~028, N02-A6]
- [X] T055 [P] [US3] Add restore tests for marker/token removal, fault-inactive probe, failed-consent zero snapshot, per-path overlay apply/remove, original pristine digest recovery and manual-cleanup blocking in `tests/integration/test_n02_consent_fault_restore.py` [FR-029~032, EV3-08~EV3-09]
- [X] T056 [P] [US3] Add N02-A6/A7 judge tests for missing trigger, partial consent, protected effect leakage, overlay residue, duplicate recovered effects, correct recovery and restore failure precedence in `tests/unit/test_judge_n02_recovery.py` [FR-027~032, N02-A6~A7]
- [X] T057 [P] [US3] Add the complete failure→three blocked paths→restore→same-subject normal retry journey in `tests/integration/test_n02_fault_recovery.py` [FR-026~032, N02-A6~A7]

### Implementation for User Story 3

- [X] T058 [US3] In the WhyYou personal branch, invoke the T020 fault boundary immediately after `save_consent()` and before invitation transition/Outbox in `../gbsa_aws/backend/src/interview_evidence/company_management/application/applicant_access_service.py`; let the request middleware roll back the transaction and return 5xx [FR-026~028]
- [X] T059 [US3] Implement marker apply, receipt read, current-Run restore, fault-inactive probe and safe-state verification in `engine/adapters/whyyou/consent_fault.py` [FR-026~032, EV3-07~EV3-09]
- [X] T060 [US3] Extend `engine/adapters/whyyou/n02_seed.py` with fault-subject recording/assessment overlay apply/remove operations that restore the original pristine digest before retry [FR-007, FR-029~031]
- [X] T061 [US3] Extend `engine/executors/n02.py` with fault apply, failed consent, matching trigger read, zero-partial-effect snapshot, three blocked path probes, mandatory marker/overlay restore and same-subject normal recovery; execute cleanup on error, timeout and cancellation [FR-026~032, EV3-07~EV3-09]
- [X] T062 [US3] Implement N02-A6/A7 and `RESTORE_FAILED → INCONCLUSIVE` precedence in `engine/judges/n02.py`, preserving direct prohibited effects without hiding them [FR-027~036, N02-A6~A7]
- [X] T063 [US3] Extend `engine/execution.py` only where required to persist N-02 restore checkpoints and block later fault Runs until `cleanup-confirm`; do not weaken Spec 001/002 restore behavior [FR-030~032]
- [X] T064 [US3] Run T052~T057 and their implementation tests, then record the independently passing fault/recovery gate in `specs/003-n02-consent-order/validation.md` [FR-026~032, N02-A6~A7, EV3-07~EV3-09, SC-005~007]

**Checkpoint**: 동의 저장 실패의 원자성, 장애 제거와 같은 subject의 정상 복구를 독립 판정할 수 있다.

---

## Phase 6: User Story 4 — 경로별 결과와 증적 한계를 검토한다 (Priority: P2)

**Goal**: A1~A7, 세 경로, causal order, 복구, 미검증 범위와 bundle 무결성을 CLI에서 서로 혼동 없이 설명한다.

**Independent Test**: PASS, 직접 FAIL, 증적 누락, 증적 충돌, baseline 불일치와 restore failure fixture를 show/verify해 예상 verdict·reason·증적 참조와 claim boundary를 확인한다.

### Tests for User Story 4 — write first

- [X] T065 [P] [US4] Add the combined A1~A7 verdict matrix and precedence cases for direct FAIL, insufficient evidence, evidence conflict, baseline abort and restore failure in `tests/integration/test_n02_verdict_matrix.py` [FR-034~036, N02-A1~A7]
- [X] T066 [P] [US4] Add presentation contracts for lane/path directness, request/effect delta, policy/causal order, fault/recovery, unavailable facts, AWS/N-01/N-03 limits and no-certification language in `tests/contract/test_presentation_spec003.py` [FR-040~041, SC-009, SC-012]
- [X] T067 [P] [US4] Add CLI contracts for N-02 preflight/run/show/verify projection, stable exit codes, all assertion lists, non-empty sanitized `operator_action` on non-READY preflight, zero preflight side effects and no automatic remediation/retest in `tests/contract/test_cli_n02.py` [FR-004~006, FR-034~041]
- [X] T068 [P] [US4] Add bundle verification integration tests for all EV3 mappings, lane/subject/attempt/effect/causal/fault references, unregistered files and redaction failures in `tests/integration/test_n02_bundle_links.py` [FR-037~039, EV3-01~EV3-10]

T065~T068 테스트와 T072 여섯 lane 통합 gate는 자동 fixture에서 PASS다. 실제 WhyYou 판정은 T078을 기다린다.

### Implementation for User Story 4

- [X] T069 [P] [US4] Extend `engine/presentation.py` with N-02 path, order, recovery and limitation projections, including `claim_scope=EXECUTED_SCENARIO_AND_EVIDENCE_ONLY` and explicit no-certification wording [FR-040~041]
- [X] T070 [US4] Implement N-02 preflight/run/show/verify dispatch and additive machine output in `engine/cli.py`, preserving `controlproof.cli.v1` and existing exit meanings [FR-004~006, FR-034~041]
- [X] T071 [US4] Complete EV3 cross-reference and readable-fact validation in `engine/evidence.py`; a valid hash with unreadable required facts must not reconstruct PASS [FR-034~039, EV3-01~EV3-10]

T070 preflight는 읽기 전용 보호 경로 목록만 출력한다. 실제 정책·lane·경로 digest는 Run에서 확정해 bundle에 기록한다.
- [X] T072 [US4] Add a deterministic complete six-lane orchestration test with sealed bundle and verified show projection in `tests/integration/test_n02_orchestration.py` [SC-001~SC-009]
- [X] T073 [US4] Run T065~T068 plus T072 and record the independently passing review/bundle gate in `specs/003-n02-consent-order/validation.md` [FR-034~041, N02-A1~A7, EV3-01~EV3-10, SC-001~005, SC-009, SC-012]

**Checkpoint**: 자동 fixture에서 N-02 전체 결과와 근거 한계를 일관되게 검토할 수 있다. 아직 WhyYou 실제 판정은 아니다.

---

## Phase 7: User Story 5 — 최초 결과를 보존하고 수정 후 재시험한다 (Priority: P3)

**Goal**: 최초 WhyYou actual Run을 있는 그대로 봉인하고, 직접 FAIL이 확인된 경계만 보완한 뒤 새 child Run으로 차이를 증명한다.

**Independent Test**: 완료된 parent fixture에서 child를 만들고 parent manifest가 불변이며 scenario/profile은 상속되고 대상 SHA와 결과 차이가 새 bundle에만 기록되는지 확인한다.

### Tests and implementation for immutable retest

- [X] T074 [P] [US5] Add retest tests for inherited scenario/profile, fresh six-subject set, new Run ID, target/policy/capability/fixture diff, parent read-only digest and unresolved-cleanup refusal in `tests/integration/test_n02_retest_lineage.py` [FR-002, FR-032~033, SC-010]
- [X] T075 [P] [US5] Add parent/child bundle verification tests proving the parent manifest and evidence bytes remain unchanged before and after child creation in `tests/contract/test_n02_retest_bundle.py` [FR-002, FR-033, EV3-10]
- [X] T076 [US5] Extend `engine/retest.py` with N-02 profile inheritance, fresh lane seeding, target/policy/capability/fixture diffs and manual-cleanup refusal without modifying parent files [FR-002, FR-032~033]

T076의 실제 child 경로에는 승인된 최소 확장으로 `engine/cli.py`, `engine/executors/n02.py`, `engine/evidence.py`의 N-02 분기와 parent-link 검증을 포함했다. 실제 WhyYou Run은 아직 실행하지 않았다.

### Actual-stack first truth gate

- [X] T077 [US5] On clean committed ControlProof and WhyYou personal feature branches, execute the `N02_CONSENT_ORDER_V1` preflight from `specs/003-n02-consent-order/quickstart.md`; record non-sensitive source SHAs, readiness, capability/policy/lane digests and AWS `NOT_RUN` in `specs/003-n02-consent-order/validation.md`, and create no Run unless READY [FR-003~006, SC-011~012]
- [X] T078 [US5] Execute exactly one initial N-02 actual Run before any product consent-guard remediation, then run show/verify and record Run ID, A1~A7 results, path results, restore status and manifest SHA-256 in `specs/003-n02-consent-order/validation.md` [FR-033~041, SC-001~SC-009]
- [X] T079 [US5] Freeze the T078 source/result mapping in `specs/003-n02-consent-order/traceability.md` and document every direct FAIL, INCONCLUSIVE fact and unavailable scope without changing the sealed parent bundle [FR-002, FR-033~041]

T077 2026-10-02 first attempt: both branches were clean and committed, but the local Docker/API/DB/LocalStack environment was unavailable. The CLI preflight produced no readiness result and was interrupted; T077 remained open and no actual Run was started at that point. See `validation.md`.
T077~T079 retry after Docker restart: clean-source preflight READY; the one initial actual Run `15cef078-ee24-4f0e-91ef-381e0f7a1cc2` ended `RESTORE_FAILED` / `INCONCLUSIVE` with A4~A7 FAIL. The sealed bundle VERIFIED and its source/result mapping is in `validation.md` and `traceability.md`. No child Run or remediation was started.

### Evidence-gated conditional product remediation

- [X] T080-E1 [US5] Before T080 classification, correct the post-T078 evidence contract with test-first scoped checks in `tests/contract/test_n02_consent_adapter.py`, `tests/contract/test_n02_processing_adapter.py`, `tests/unit/test_judge_n02_bypass.py` and the relevant N-02 orchestration/bundle contracts. Allowed implementation scope is `engine/adapters/whyyou/consent.py`, `engine/adapters/whyyou/protected_processing.py`, `engine/models.py`, `engine/judges/n02.py`, `engine/executors/n02.py`, `engine/evidence.py`, and local/test observer instrumentation only in `../gbsa_aws/backend/src/interview_evidence/runtime/worker.py` and `../gbsa_aws/backend/src/interview_evidence/runtime/controlproof_consent.py` with scoped observer tests. Tag runner-inserted assessment events as inputs; require a separate target boundary/start/result to establish A4/A6 direct effects; seal an allowlisted 422 reason and stage-specific recovery facts without changing the parent bundle. No WhyYou product guard is authorized by this task. Review all external-AI paths and safe-state evidence before any child Run. [FR-017~019, FR-027~033, EV3-04~EV3-10]
- [X] T080-E2 [US5] Before any parent-linked diagnostic or remediation Run, establish a local/test-only external-AI isolation contract for every reachable WhyYou worker AI dependency (model, embedder, AWS/GCP speech and Document AI OCR); prove API and every managed active worker configuration with scoped tests and fail-closed preflight. Independently verify N-02 consent-fault safe state before any evidence-backed `cleanup-confirm`. ID-003-05/06 in `implementation-decisions.md` record the reviewed multi-process scope and implemented automated isolation gate. An isolated live API/four-worker probe returned `processing.paths.read=READY`, and a separate read-only check of the original N-02 fault subject found no consent or document effects and no active marker/token. The parent restore block remains active; no `cleanup-confirm` or child Run occurred. [FR-004~006, FR-030~033, SC-011]
- [X] T080-E3 [US5] Add an N-02-specific `cleanup-confirm` contract in `engine/cli.py`, `engine/adapters/whyyou/consent_fault.py` and adapter composition, preserving H-03 behavior. Require a VERIFIED blocked parent, matching fresh evidence for its `CONSENT_FAULT_RECOVERY` subject, and a live read-only N-02 state/effect re-probe before clearing only the N-02 block. Test wrong parent, invalid bundle, stale evidence, unsafe target and historical consent facts. The original parent's block was cleared with evidence SHA-256 `406a87bc88cf2f0ec0bcff1799f7ad4b8099937e507484d11ad9e3d801649eef`; parent bundle remains VERIFIED and unchanged. No child Run occurred. [FR-028~033]
- [X] T080-E4 [US5] Review and implement the N-02 retest gate before any child Run. A `RESTORE_FAILED` N-02 parent may prepare a child only when its VERIFIED bundle, matching cleanup maintenance record, original evidence bytes/SHA-256, safe-state facts and absence of a new block all verify. The CLI requires `--cleanup-evidence` for this case and seals the confirmation reference into a future child link. H-03/E-03 restore-failed parents remain refused. Scoped test-first RED, 23+1 related PASS and a read-only check against the actual parent/maintenance record are in `validation.md`; no child Run occurred. [FR-032~033]

T080 remains open because A5~A7 root causes cannot be derived from the immutable parent's missing 422 detail. T080-E2 isolation, T080-E3 cleanup confirmation and T080-E4 retest gating are complete, but a fresh full READY preflight and evidence-bearing child diagnostic remain open. No child Run or WhyYou product consent guard was started.

T080-E2 isolation sub-bundle: WhyYou local/test startup rejects external AI provider routes, exposes a sanitized isolation digest, and requires each managed worker PID to write a fresh matching attestation after a successful cycle. The launcher holds an exclusive pool lock and publishes attested interpreter PIDs. N-02 `processing.paths.read` fails closed on missing, stale, mismatched or extra fresh proof. Scoped tests and an isolated live API/four-worker capability probe passed. The original N-02 fault subject passed an independent read-only safe-state check. T080-E3 later cleared the block with new evidence; these snapshots do not change the parent's verdict or replace a future Run-time process inventory. See ID-003-06/07 and `validation.md`.

- [X] T080 [US5] For every T078 direct FAIL, record the assertion, exact artifact and root-cause class `TARGET_CONTROL_DEFECT|RUNNER_OR_OBSERVER_DEFECT|RESTORE_OPERATOR_DEFECT` in `specs/003-n02-consent-order/implementation-decisions.md`; for A5~A7 failures not covered by T081~T083, first add the failing regression to `../gbsa_aws/backend/tests/integration/company_management/test_controlproof_n02_consent_transaction.py` or `tests/integration/test_n02_fault_recovery.py`, then apply only the evidence-selected minimal fix in `../gbsa_aws/backend/src/interview_evidence/company_management/application/applicant_access_service.py`, `../gbsa_aws/backend/src/interview_evidence/shared/database.py`, `engine/executors/n02.py` or `engine/adapters/whyyou/consent_fault.py`; if no such FAIL exists, record `NOT_REQUIRED` and do not manufacture a defect [FR-026~033, N02-A5~A7, SC-010]
- [X] T081 [US5] Only if T078 proves a document-analysis boundary bypass, add a failing target regression in `../gbsa_aws/backend/tests/integration/submission_analysis/test_consent_gate.py` and add the minimal active `document_analysis` consent check at the confirmed boundary in `../gbsa_aws/backend/src/interview_evidence/workers/analysis/event_handler.py`; otherwise record `NOT_REQUIRED` with the parent artifact in `specs/003-n02-consent-order/validation.md` [N02-A2, N02-A6]
- [X] T082 [US5] Only if T078 proves a recording boundary bypass, add a failing target regression in `../gbsa_aws/backend/tests/integration/interview_engine/test_controlproof_n02_consent_gate.py` and add the minimal active `recording` consent check through `../gbsa_aws/backend/src/interview_evidence/integration/submission_interview.py`; otherwise record `NOT_REQUIRED` with the parent artifact in `specs/003-n02-consent-order/validation.md` [N02-A3, N02-A6]
- [X] T083 [US5] Only if T078 proves an AI-assessment boundary bypass, add a failing target regression in `../gbsa_aws/backend/tests/unit/reporting/test_report_event_handler.py` and add the minimal active `ai_assessment` consent check to `ReportRequestedEventHandler` in `../gbsa_aws/backend/src/interview_evidence/runtime/worker.py`; otherwise record `NOT_REQUIRED` with the parent artifact in `specs/003-n02-consent-order/validation.md` [N02-A4, N02-A6]
- [X] T084 [US5] If T078 directly FAILed and every evidence-required remediation from T080~T083 is complete, run a parent-linked child retest, verify parent and child bundles and record ControlProof/target SHA and result differences; if T078 had no direct FAIL, re-verify the parent and record that no child was required in `specs/003-n02-consent-order/validation.md` [FR-002, FR-033, SC-010]

**Checkpoint**: 최초 사실은 보존되고, 필요한 경우에만 수정 전→후 계보가 별도 Run으로 남는다.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 보안, 시간 제한, 추적성, 재현성과 팀 인계를 전체 스토리에 걸쳐 마감한다.

- [X] T085 [P] Add deterministic timing tests proving 2-second poll, 3 consecutive stable reads over at least 4 seconds, 600-second fault TTL, 120-second restore, 540-second Run deadline and reserved 60-second bundle-verify budget come only from the scenario snapshot in `tests/integration/test_spec003_timing.py` [SC-006, SC-008]
- [X] T086 [P] Extend the security corpus to all EV3 files, marker/observer receipts, causal identifiers and CLI output in `tests/unit/test_redaction_security.py` [FR-038~039, SC-011]
- [ ] T087 Run `ruff check .` and the complete ControlProof `pytest -q` suite plus every scoped WhyYou N-02 test, and record commands, counts, durations, target FAILs, restore status and source SHAs in `specs/003-n02-consent-order/validation.md` [FR-001~041, SC-001~012]
- [ ] T088 Execute every unconditional command in `specs/003-n02-consent-order/quickstart.md` from a clean local environment, replace `<run-id>` placeholders with T078/T084 actual IDs, execute retest and cleanup commands only when their documented condition applies, record every skipped conditional with its reason, and verify Run+bundle-verify completes within 600 seconds [SC-008]
- [ ] T089 Complete the FR/SC/N02-A/EV3 → task → test → implementation → actual artifact matrix in `specs/003-n02-consent-order/traceability.md` [FR-001~041, SC-001~012, N02-A1~A7, Constitution VII]
- [ ] T090 Verify all conditional branches T080~T084 are either completed or evidence-backed `NOT_REQUIRED`, and summarize the final implementation/target verdict distinction in `specs/003-n02-consent-order/implementation-decisions.md` [FR-033~041]
- [ ] T091 [P] Scan tracked source and generated bundle metadata for `C:\\Users\\`, other absolute user paths, raw credentials and real applicant identifiers; record the clean command/result in `specs/003-n02-consent-order/validation.md` [FR-038~039, SC-011]
- [ ] T092 Update Spec 003 state, source SHAs, reproducibility commands, actual verdict and next workflow step consistently in `README.md`, `docs/TEAM_HANDOFF.md`, `docs/AI_SPEC_KIT_PLAYBOOK.md`, `docs/product/ControlProof_MVP_Product_Brief.md` and `docs/product/ControlProof_MVP_Scenario_Coverage_Matrix.md` [SC-012]
- [ ] T093 Have a second clean checkout or teammate follow only `README.md`, `docs/TEAM_HANDOFF.md` and `specs/003-n02-consent-order/quickstart.md` through preflight and one N-02 Run, then record source SHAs, manifest digest and any portability defect in `specs/003-n02-consent-order/validation.md` [SC-008, Constitution VII]

---

## Dependencies & Execution Order

### Phase dependencies

```text
Phase 1 Setup
    ↓
Phase 2 Foundation
    ├──────────────→ Phase 3 US1 — pre-consent bypass/effects
    ├──────────────→ Phase 4 US2 — normal consent/causal order
    └──────────────→ Phase 5 US3 — consent fault/restore
                         ↓
                 Phase 6 US4 — combined judgement/bundle/CLI
                         ↓
                 Phase 7 US5 — initial actual Run/conditional fix/retest
                         ↓
                 Phase 8 Polish/validation/handoff
```

- **Setup** has no dependency.
- **Foundation** depends on Setup and blocks every story.
- **US1, US2 and US3** can start after Foundation with separate files and fixtures; shared `engine/executors/n02.py`, `engine/judges/n02.py` and `engine/adapters/whyyou/adapter.py` changes must be serialized or coordinated.
- **US4** requires the A1~A7 slices from US1~US3.
- **US5** requires the complete deterministic profile, bundle and CLI from US4.
- **T078** is the immutable first actual Run and blocks all conditional remediation T080~T083.
- **Polish** depends on the selected conditional path and any required child retest.

### Key task dependencies

- T013 blocks T014~T019; T020 blocks T021~T022 and all WhyYou observer/fault wiring.
- T024~T029 must fail for the intended missing behavior before T030~T039 implement US1.
- T031/T032/T033/T034/T035/T036 block T037; T037 blocks T038 and the US1 gate T040.
- T041~T045 precede T046~T050; T046/T047/T048 block T049 and T050.
- T052~T057 precede T058~T063; T058/T059/T060 block the complete T061 recovery flow.
- T065~T068 precede T069~T072; T072 must pass before preflight.
- T074~T075 precede T076.
- T077 must be READY before T078; T078 must be sealed and verified before T080~T083.
- T084 is required only after an evidence-confirmed direct FAIL; parent bundle bytes and manifest digest must remain unchanged.

## Parallel Opportunities

### Foundation

```text
T005 models | T006 scenario | T007 bundle | T008 CLI | T009 adapter | T010 WhyYou safety | T011 redaction | T012 regression
after T013: T015 protocols | T016 config | T018 evidence | T019 fake adapters | T020 WhyYou local/test runtime
```

### User Story 1

```text
Tests: T024 seed | T025 processing | T026 target observer | T027 judge | T028 orchestration | T029 isolation
Implementation: T030 subject definitions | T032 attempts | T036 scenario; then T031/T033/T034/T035 → T037 → T038/T039
```

### User Story 2

```text
T041 consent | T042 causality | T043 target transaction | T044 journey | T045 judge
after tests: T046 consent adapter | T047 causal adapter; then T048/T049 → T050
```

### User Story 3

```text
T052 fault contract | T053 target guard | T054 rollback | T055 restore | T056 judge | T057 journey
after tests: T058 target hook | T059 fault adapter | T060 overlays; then T061/T062/T063
```

### User Story 4

```text
T065 verdict | T066 presentation | T067 CLI | T068 bundle
after tests: T069 presentation can proceed beside T070 CLI and T071 bundle verification; then T072
```

## Implementation Strategy

### First independently demonstrable slice

1. Complete Setup and Foundation.
2. Complete US1.
3. Stop and validate A1~A4 with deterministic fixtures.
4. Treat this as an engineering checkpoint, not full N-02 or full MVP completion.

### N-02 P1 core

1. Add US2 normal consent and causal order.
2. Add US3 fault atomicity and restore.
3. Run the combined deterministic A1~A7 gate.
4. Do not change WhyYou product consent guards before the first actual Run.

### Actual target closure

1. Commit both repositories on non-main feature branches and pass preflight.
2. Seal and verify the initial actual Run.
3. A truthful WhyYou FAIL is a valid ControlProof result, not an implementation failure.
4. Apply only evidence-confirmed minimal remediations from T080~T083 after root-cause ownership is fixed.
5. Retest as a new child Run; never replace the original result.

### Suggested team split after Foundation

- Developer A: US1 seed, three path attempts and effect projection
- Developer B: US2 consent and causality
- Developer C: US3 fault, rollback and restore
- Shared review: US4 bundle/CLI, initial actual Run, evidence-gated remediation and retest

## Notes

- Tests listed before implementation must fail for the intended missing behavior before product code is changed.
- WhyYou work stays on `bosung/controlproof-h03-integration` or a descendant personal branch; never on `main`/`master`.
- Observer, fault hook and synthetic fixtures are permitted before the first actual Run because they expose or induce facts; they must not silently add the product guard being tested.
- The actual AWS environment remains `NOT_RUN`; LocalStack/local PASS cannot be promoted to AWS PASS.
- A denied request without a successful post-effect read is not PASS.
- Deep-probe fixture effects are prerequisites, not evidence that a normal user flow succeeded.
- Do not add a fake AI-assessment endpoint, generic chaos framework, DB migration, N-01 viewport test, N-03 policy invalidation flow or web workbench under this Spec.
- Do not store actual applicants, raw policy/document/answer/report text, credentials, full logs or database dumps.
- ControlProof implementation completion and the observed WhyYou N-02 verdict remain separate facts.
- Every task is complete only when linked tests pass and the relevant source path is committed in the correct repository.
