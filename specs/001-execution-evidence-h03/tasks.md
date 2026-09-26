---

description: "Spec 001 H-03 실행·증적 최소 수직 흐름의 구현 작업 목록"
---

# Tasks: 실행·증적 기본 모델과 H-03 최소 수직 흐름

**Input**: `specs/001-execution-evidence-h03/`의 spec, plan, research, data model, contracts, quickstart  
**Tests**: Spec과 Constitution이 단위·계약·통합·대표 E2E 시험을 필수로 요구하므로 테스트 작업을 구현보다 먼저 포함한다.  
**Organization**: 공통 기반 뒤에 사용자 스토리별 독립 증분으로 구성한다. Task의 `[FR-*]`, `[H03-A*]`, `[EV-*]` 표기는 요구사항 추적 ID다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 선행조건이 충족되면 다른 파일의 작업과 병렬 실행 가능
- **[Story]**: 기능 Spec의 사용자 스토리
- 모든 작업은 수정하거나 생성할 정확한 파일 경로를 포함한다.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Python CLI, 브라우저, WhyYou 연결과 실행 산출물 격리 기반을 준비한다.

- [X] T001 Add `playwright>=1.55`, `sqlalchemy>=2.0`, `psycopg[binary]>=3.2` and the `controlproof = engine.cli:main` console entry point in `pyproject.toml`
- [X] T002 [P] Ignore `.controlproof/` runtime bundles, Playwright artifacts, and temporary fault markers while preserving committed fixtures in `.gitignore`
- [X] T003 [P] Create package initializers for the planned adapter layout in `engine/adapters/whyyou/__init__.py` and create test package initializers under `tests/unit/__init__.py`, `tests/contract/__init__.py`, `tests/integration/__init__.py`, and `tests/fixtures/__init__.py`
- [X] T004 [P] Document only variable names and safe local examples for `CONTROLPROOF_RUN_ROOT`, WhyYou URLs, database, company token, repository path, shared fault/receipt root, `CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED`, and `CONTROLPROOF_MODEL_FIXTURE_ID` in `.env.example`
- [X] T005 Add a deterministic test configuration with temporary Run/fault/receipt roots, a fixed model fixture digest, and no network access by default in `tests/conftest.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 사용자 스토리가 공유하는 상태, 관찰, 증적, scenario, adapter 경계를 먼저 고정한다.

**⚠️ CRITICAL**: 이 Phase가 완료되기 전에는 사용자 스토리 구현을 시작하지 않는다.

### Foundation tests — write first

- [X] T006 [P] Add model validation tests covering all ReadinessStatus, RunState, Verdict, InconclusiveReason, Phase, Presence, AssertionStatus, `NOT_IMPLEMENTED|PARTIAL|IMPLEMENTED` ImplementationStatus, ComparatorKind, and TargetSourceKind values; require created Runs to be `IMPLEMENTED`; and enforce “`NOT_RUN`은 scenario listing projection에만 사용할 수 있고, `run_id`가 있는 Judgement에는 저장할 수 없다” in `tests/unit/test_models.py` [FR-004, FR-013, FR-014, FR-042, FR-043, FR-048, FR-050]
- [X] T007 [P] Add lifecycle and host-lock tests for every permitted transition, terminal-state immutability, and the rule “`fault_ever_applied=true`이면 `RUNNING → ABORTED` 직접 전이를 금지한다” in `tests/unit/test_lifecycle.py` [FR-013, FR-018, FR-020]
- [X] T008 [P] Add Presence and conflict tests proving `ABSENT` differs from `UNAVAILABLE`, only `run_id + subject_ref + phase + step_id + attempt + key` identifies a conflict dimension, undeclared comparators default to type-strict `EXACT`, H-03 assertion keys are `EXACT`, `observed_at` is excluded, and `ABSOLUTE_TOLERANCE` requires an explicit non-negative value without coercion in `tests/unit/test_observations.py` [FR-021~026]
- [X] T009 [P] Add scenario schema tests for unique `step_id`, H-03 assertion/evidence references, capability ID→required contract version mappings with all H-03 entries at `v1`, version digest stability, a complete `EXACT` H-03 comparator registry, rejection of invalid/negative tolerance, allowed deterministic model fixture ID/digest, and invalid readiness/result aliases in `tests/contract/test_scenario_contract.py` [FR-001~005, FR-025, FR-050, FR-055]
- [X] T010 [P] Add bundle contract tests for root-confined relative paths, atomic JSON/JSONL records, canonical TargetSnapshot digest/run linkage including dirty-diff requirements, pre-persist redaction, SHA-256/size/MIME metadata, seal immutability, and manifest completeness in `tests/contract/test_bundle_contract.py` [FR-008, FR-035~041]

### Foundation implementation

- [X] T011 Implement the shared enums plus immutable ScenarioSnapshot, `controlproof.target-snapshot.v1` TargetSnapshot, Run, TestSubject, FaultCondition, Observation, EvidenceArtifact, AssertionResult, Finding, Judgement, and RetestLink models in `engine/models.py`; enforce git/image source-kind fields, dirty→diff digest, canonical `target-snapshot:sha256:<64 lowercase hex>`, `NOT_IMPLEMENTED|PARTIAL|IMPLEMENTED` semantics, created Run=`IMPLEMENTED`, “`NOT_RUN`은 scenario listing projection에만 사용할 수 있고, `run_id`가 있는 Judgement에는 저장할 수 없다”, terminal timestamps, `attempt >= 1`, and `RESTORE_FAILED → manual_cleanup_required=true` [FR-007~014, FR-021~025, FR-035~050]
- [X] T012 [P] Implement Run transition validation, target+subject host locking, restore-failure block markers, and atomic lifecycle persistence in `engine/lifecycle.py` after T011 [FR-013, FR-018~020]
- [X] T013 [P] Implement append-only polling timelines, `PRESENT|ABSENT|UNAVAILABLE` normalization, stability selection, and same-dimension conflict detection using type-strict default `EXACT` or explicitly configured non-negative `ABSOLUTE_TOLERANCE` without implicit coercion in `engine/observations.py` after T011 [FR-021~026]
- [X] T014 [P] Replace the spike dataclass loader with versioned ScenarioDefinition validation, canonical digest snapshots, step/assertion/evidence cross-reference checks, comparator registry validation, and separate target/readiness preconditions in `engine/scenario.py` after T011 [FR-001~006, FR-025]
- [X] T015 [P] Implement `collect → allowlist projection → redaction → serialize → persist → hash`, atomic writes, JSONL append/fsync, manifest sealing, and root-confined paths in `engine/evidence.py` after T011 [FR-035~041]
- [X] T016 [P] Define service-neutral CapabilityProbe, SeedAdapter, StateAdapter, FaultAdapter, BrowserAdapter, Clock, and TargetAdapter protocols with explicit capability ID+contract version registration and sanitized result envelopes in `engine/adapters/base.py` after T011 [FR-003, FR-010, FR-015~019, FR-050]
- [X] T017 [P] Implement typed environment loading, local/test target allowlists, secret-safe validation errors, and defaults for timing policy in `engine/config.py` after T011 [FR-015, FR-026, FR-040]
- [X] T018 Implement the readiness check result aggregator and implementation-status calculation from required capability handler registration plus contract-version matching in `engine/readiness.py` after T014 and T016; when the target feature exists force `PARTIAL|NOT_IMPLEMENTED` to `RUNNER_NOT_READY`, preserve `NO_TEST_TARGET` when the feature itself is absent, and keep readiness, implementation status, and verdict separate [FR-003~006, FR-050]
- [X] T019 Create an argparse CLI shell with stable JSON envelopes, exit-code mapping, secret-safe stderr, and placeholders that refuse unimplemented commands in `engine/cli.py` after T011 and T017
- [X] T020 Migrate the existing spike tests to the new immutable dimensions without weakening their original intent in `tests/test_judge.py` and `tests/test_state_seed.py`, then keep `pytest -q` green before story work

**Checkpoint**: 공통 모델과 저장 계약이 고정되고 기존 테스트가 새 계약에서 통과한다.

---

## Phase 3: User Story 1 — reporting 장애에서 결정 안전성을 실제 시험한다 (Priority: P1) 🎯 MVP

**Goal**: 합성 지원자 한 명의 reporting 처리를 안전하게 실패시키고, 화면 표시·최종결정 거부·무부작용·자동결정 부재·복구를 실제 증적으로 판정한다.

**Independent Test**: 결정론적 fake adapter 통합 환경에서 한 Run을 수행해 H03-A1~A6, EV-01~EV-09, terminal Run state, 환경 복구와 별도 리포트 처리 결과가 하나의 sealed bundle로 생성되는지 확인한다. 실제 WhyYou 로컬 스택 검증은 capability 구현이 끝난 T077에서 수행한다.

### Tests for User Story 1 — write and observe failure first

- [X] T021 [P] [US1] Add a contract test requiring exactly H03-A1~A6, EV-01~EV-09, one synthetic subject, an allowed fixed model fixture ID/digest, an explicit `EXACT` comparator for every H-03 assertion input key, `BASELINE|INJECTED|RECOVERED` steps, 2-second polling, 30-second injected deadline, 10-second automatic-decision window, a 120-second environment-restore deadline, and a separate report-processing recovery field in `tests/contract/test_h03_scenario.py` [FR-001, FR-009, FR-019, FR-022, FR-025~026, FR-055, H03-A1~A6, EV-01~EV-09]
- [X] T022 [P] [US1] Add deterministic fixture tests proving the H-03 seed creates a completed synthetic interview with final media and no report, no final decision, and no report-generation event until trigger time in `tests/unit/test_h03_pending_report_seed.py` [FR-009, FR-011, FR-012]
- [X] T023 [P] [US1] Add WhyYou adapter contract tests for canonical TargetSnapshot across clean git, dirty→RUNNER_NOT_READY with deterministic porcelain/file-hash diagnostic, complete/missing `backend|reporting-worker|company-console` image components, capture failure, company authentication, report `200/202/404`, decision rejection/acceptance, explicit target-provided `REPORT_NOT_AVAILABLE`, generic 404/empty detail remaining `reason_present=false`, state projection, access failure, transient failure, and target absence using HTTPX MockTransport in `tests/contract/test_whyyou_adapter_contract.py` [FR-003~008, FR-027~033]
- [X] T024 [P] [US1] Add fault adapter tests for atomic run/session marker apply, TTL/schema validation, effect probe requiring an append-only matching trigger receipt, idempotent removal, wrong-session isolation, marker+worker environment recovery, separate `READY|PARTIAL|FAILED|TIMEOUT|UNAVAILABLE` report-processing recovery, and restore uncertainty in `tests/unit/test_whyyou_fault.py` [FR-015~020, H03-A1, H03-A6, EV-02, EV-03, EV-08]
- [X] T025 [P] [US1] Add browser adapter tests for a sanitized visible-text projection, screenshot metadata, ready-content detection, decision-control visibility, timeout, and authentication failure in `tests/contract/test_whyyou_browser.py` [FR-028, FR-029, EV-04]
- [X] T026 [P] [US1] Add H03-A1~A6 rule tests covering safe PASS, visible failure-state FAIL, generic queued-through-deadline FAIL, accepted decision FAIL, rejected-without-explicit-report-reason FAIL, partial side-effect FAIL, automatic decision FAIL, environment-restore INCONCLUSIVE, and report-processing `FAILED|TIMEOUT` preserved as findings without overriding successful environment restore in `tests/unit/test_judge_h03.py` [FR-019, FR-027~034, FR-042~050]
- [X] T027 [P] [US1] Add a deterministic fake-adapter end-to-end test for readiness/model-fixture verification → seed → baseline → inject → trigger receipt → observe → decision attempt → post-state → absence window → environment restore + separate report-processing recovery → judgement → seal in `tests/integration/test_h03_orchestration.py` [FR-007~019, FR-027~050, FR-055]
- [X] T028 [P] [US1] Add cancellation, exception, marker-left-behind, worker-health failure, report-processing `FAILED|TIMEOUT` with environment restored, `RESTORE_FAILED`, and subsequent-Run blocking cases in `tests/integration/test_h03_restore_failure.py` [FR-018~020, FR-047, H03-A6]
- [X] T029 [P] [US1] In the WhyYou repository, add failing unit tests for default-disabled hooks, production startup rejection, session allowlisting, expiry, append-only trigger receipt plus structured logging, pre-side-effect `TimeoutError`, and the local/test-only fixed model substitute in `backend/tests/unit/runtime/test_controlproof_reporting_fault.py` and `backend/tests/unit/runtime/test_controlproof_model_substitute.py` [FR-015~017, FR-055]

### Implementation for User Story 1

- [X] T030 [P] [US1] Replace the DLQ-heavy spike with the Spec 001 minimum definition and version it as `1.0.0` in `scenarios/H-03.yaml`, including H03-A1~A6, EV-01~EV-09, explicit `EXACT` comparator entries for every assertion input key, exact timing policy, mandatory restore, and explicit Spec 002 exclusions [FR-001~002, FR-025, FR-034]
- [X] T031 [P] [US1] Implement the run-labelled pending-report fixture, invariants, idempotent upsert, explicit report trigger, and correlation-only teardown in `seeds/h03_pending_report.py`, leaving `seeds/state_seed.py` as the ready-report E-series fixture [FR-009~012]
- [X] T032 [P] [US1] Implement authenticated HTTP requests, status normalization, sanitized request/response capture, stable error codes, canonical TargetSnapshot capture/hash excluding `captured_at|target_version`, clean-git Run enforcement, deterministic dirty diagnostic manifest, required `backend|reporting-worker|company-console` image components, OpenAPI, migration/schema, and model fixture components, plus allowlisted target-only decision reason mapping that leaves generic 404/empty detail without a reason in `engine/adapters/whyyou/client.py` [FR-008, FR-023, FR-027, FR-030~031, EV-03, EV-05, EV-09]
- [X] T033 [P] [US1] Implement schema-signature checks, synthetic subject seed/trigger/teardown bindings, and correlation mapping in `engine/adapters/whyyou/seed.py` after T031 [FR-009~012]
- [X] T034 [P] [US1] Implement allowlisted state snapshots containing only invitation status, recruiting stage ID, pipeline version, final-decision count/actor, and report presence/status in `engine/adapters/whyyou/state.py` [FR-011, FR-032~033, EV-01, EV-06, EV-07, EV-08]
- [X] T035 [P] [US1] Implement marker apply/probe/restore with atomic files, TTL, session scope, append-only trigger receipt matching, marker+worker environment restore, separate report-processing recovery, and no command-success/log-absence inference in `engine/adapters/whyyou/fault.py` [FR-015~020, H03-A1, H03-A6]
- [X] T036 [P] [US1] Implement Playwright company-console authentication, review-route capture, visible-state normalization, screenshot artifact production, and browser cleanup in `engine/adapters/whyyou/browser.py` [FR-028~029, EV-04]
- [X] T037 [US1] In the WhyYou repository, implement the guarded marker reader, append+fsync `${CONTROLPROOF_FAULT_ROOT}/receipts/{run_id}.jsonl` trigger receipt, and matching `CONTROLPROOF_FAULT_TRIGGERED` log in `backend/src/interview_evidence/runtime/controlproof_faults.py` so production rejects enabled hooks and malformed/expired/wrong-session markers never inject [FR-015~017]
- [X] T038 [US1] In the WhyYou repository, call the test-only guard before any report side effect in `backend/src/interview_evidence/runtime/worker.py`, implement a local/test-only fixed result dependency substitute with fixture ID/digest health in `backend/src/interview_evidence/runtime/controlproof_model_substitute.py`, and add the shared fault/receipt mount with both test controls disabled by default in `compose.yaml` [FR-015~018, FR-055]
- [X] T039 [US1] Implement the six assertion evaluators and whole-verdict gate in `engine/judge.py`, treating accepted decisions or rejected decisions without a target-provided report-unavailable reason as H03-A3 FAIL, preserving direct protection failures as findings, separating report-processing findings from environment restore, and forcing `ABORTED|RESTORE_FAILED`, unevaluable A1/A6, missing required evidence, or integrity failure to INCONCLUSIVE [FR-019, FR-027~050, H03-A1~A6]
- [X] T040 [US1] Implement the synchronous RunOrchestrator and durable step checkpoints in `engine/runner.py`, with the exact order readiness/model-fixture verification → lock → seed → baseline → inject → trigger receipt probe → UI/API observation → decision attempt → post-state → absence window → finally environment restore → separate report-processing recovery → judgement → seal [FR-007~020, FR-026~050, FR-055]
- [X] T041 [US1] Wire `controlproof run H-03` to implementation-status/readiness refusal, canonical target snapshot capture before Run creation, orchestrator progress, terminal exit codes 0/3/4/6, and secret-safe JSON output that keeps `implementation_status`, readiness, Run state, and verdict separate in `engine/cli.py` [FR-006~008, FR-049~050]
- [X] T042 [US1] Implement `cleanup-confirm` so it requires an evidence file, re-probes marker absence and target safety, stores a hashed maintenance record, and has no force-only bypass in `engine/cli.py` and `engine/lifecycle.py` [FR-020]
- [X] T043 [US1] Add a credential-free deterministic adapter-harness integration test that validates all EV-01~EV-09 artifact links, target-provided decision reason semantics, trigger receipt linkage, and split recovery fields in `tests/integration/test_h03_bundle_links.py` [SC-003~005, SC-009]
- [X] T044 [US1] Run `pytest -q tests/unit/test_judge_h03.py tests/integration/test_h03_orchestration.py tests/integration/test_h03_restore_failure.py tests/integration/test_h03_bundle_links.py` and fix only US1 implementation files until the story passes independently

**Checkpoint**: ControlProof의 최소 제품 가치인 실제 장애 실행·결정 안전성 관찰·복구·판정 흐름이 독립 실행된다.

---

## Phase 4: User Story 2 — 판정의 근거와 한계를 검토한다 (Priority: P2)

**Goal**: 비개발자가 PASS·FAIL·INCONCLUSIVE의 기대값, 실제값, 증적, 누락·충돌, 복구 결과와 미검증 범위를 2분 안에 찾는다.

**Independent Test**: PASS, 보호조치 FAIL, 증적 누락, 증적 충돌, 중단, 복구 실패, 변조 fixture를 열어 verdict·reason·finding·artifact 연결과 무결성 결과가 모두 기대값과 일치하는지 확인한다.

### Tests for User Story 2 — write first

- [X] T045 [P] [US2] Add table-driven PASS, FAIL, missing-evidence, conflict, aborted, restore-failed, and FAIL-plus-missing fixture tests with exact verdict/reason precedence in `tests/unit/test_judgement_matrix.py` [FR-042~050, SC-002]
- [X] T046 [P] [US2] Add tests proving cross-phase/step/attempt changes are not conflicts, same-dimension PRESENT/ABSENT contradictions are conflicts, and UNAVAILABLE is evidence absence rather than conflict in `tests/unit/test_evidence_conflicts.py` [FR-023~026]
- [X] T047 [P] [US2] Add changed, missing, path-traversal, unregistered, and malformed artifact verification tests that never repair the original bundle in `tests/unit/test_bundle_verify.py` [FR-039~041, SC-006]
- [X] T048 [P] [US2] Add CLI contract tests for `show` and `verify` JSON schemas, exit code 5, canonical target version, explicit implementation status independent of verdict, six assertion summaries, missing evidence, findings, restore result, and unverified scope in `tests/contract/test_cli_review.py` [FR-035~050]

### Implementation for User Story 2

- [X] T049 [US2] Extend assertion aggregation in `engine/judge.py` so direct FAIL outranks unrelated evidence gaps only on normally restored Runs, while A1/A6 inability and `ABORTED|RESTORE_FAILED` force INCONCLUSIVE without hiding risk findings [FR-042~048]
- [X] T050 [P] [US2] Implement read-only manifest verification, artifact envelope/dimension checks, required EV mapping checks, scenario/target digest checks, and parent digest comparison in `engine/evidence.py` [FR-035~041]
- [X] T051 [P] [US2] Implement a Korean human summary projection with a fixed first-screen order of verdict → core reason → failed/inconclusive assertions → evidence links → environment restore, plus a separate `implementation_status`, `조회 결과 없음` vs `조회하지 못함`, report-processing recovery, findings, and unverified scope in `engine/presentation.py` [FR-023, FR-035, FR-049~050, SC-008]
- [X] T052 [US2] Implement `controlproof show` and `controlproof verify` over sealed bundles with stable JSON plus concise terminal output in `engine/cli.py` [FR-035~050]
- [X] T053 [P] [US2] Create non-PII canonical bundle fixtures for PASS, FAIL, missing, conflict, aborted, and restore-failed cases under `tests/fixtures/bundles/` [SC-002, SC-009]
- [X] T054 [US2] Add artifact ID and source requirement links from H03-A1~A6 through the presentation projection in `tests/integration/test_h03_review_traceability.py`, and create the exact canonical PASS/FAIL/INCONCLUSIVE answer sheet, five required answers, timer boundaries, reviewer eligibility, and result table in `specs/001-execution-evidence-h03/review-usability-checklist.md` [FR-035, SC-003, SC-008]
- [ ] T055 [US2] Run `pytest -q tests/unit/test_judgement_matrix.py tests/unit/test_evidence_conflicts.py tests/unit/test_bundle_verify.py tests/contract/test_cli_review.py tests/integration/test_h03_review_traceability.py`, fix only US2 implementation files until green, then have one non-author reviewer execute all three cases in `specs/001-execution-evidence-h03/review-usability-checklist.md` and record reviewer ref, start/end, duration, answers, and 3-of-3 pass/fail in `specs/001-execution-evidence-h03/validation.md` [SC-008]

**Checkpoint**: 판정의 이유와 한계, 원본 증적, 변조 여부가 독립적으로 검토 가능하다.

---

## Phase 5: User Story 3 — 수정 후 별도 Run으로 재시험한다 (Priority: P3)

**Goal**: 부모 결과를 바꾸지 않고 새 Run으로 재시험하며 target/scenario/config 차이와 FAIL→PASS 또는 PASS 유지 결과를 비교한다.

**Independent Test**: sealed terminal Run에서 retest를 시작해 새 Run ID와 parent link, diff artifact가 생기고 부모 bundle digest가 전후 동일한지 확인한다.

### Tests for User Story 3 — write first

- [X] T056 [P] [US3] Add lineage tests for terminal-parent requirement, new child UUID, no self/cycle relation, parent read-only access, independent child artifacts, unchanged parent digest, and canonical TargetSnapshot component-path diffs in `tests/unit/test_retest.py` [FR-051~054, SC-007]
- [X] T057 [P] [US3] Add CLI contract tests for `retest`, parent verification failure, target override, parent_run_id output, and no defect-version demand when parent PASSes in `tests/contract/test_cli_retest.py` [FR-051~054]

### Implementation for User Story 3

- [X] T058 [US3] Implement terminal-parent verification, new child Run creation, parent link validation, and parent bundle read-only enforcement in `engine/retest.py` [FR-051~052]
- [X] T059 [P] [US3] Implement scenario version/digest, canonical TargetSnapshot digest plus changed identity-only JSON field paths excluding `captured_at|target_version`, subject role, initial state, config, and fault-condition comparison into `retest-diff.json` in `engine/retest.py` [FR-053]
- [X] T060 [US3] Wire `controlproof retest` to verification, child orchestration, target-version capture, diff generation, and normal Run exit codes in `engine/cli.py` [FR-051~054]
- [X] T061 [US3] Add a fake target FAIL→PASS integration journey proving both independent bundles and linked evidence remain queryable in `tests/integration/test_h03_retest_lineage.py` [FR-051~053, SC-007]
- [X] T062 [P] [US3] Add a parent-PASS integration case proving retest never asks for or creates an artificial defect variant in `tests/integration/test_h03_retest_parent_pass.py` [FR-054]
- [X] T063 [US3] Run `pytest -q tests/unit/test_retest.py tests/contract/test_cli_retest.py tests/integration/test_h03_retest_lineage.py tests/integration/test_h03_retest_parent_pass.py` and fix only US3 implementation files until the story passes independently

**Checkpoint**: 최초 Run은 불변으로 남고 수정 후 검증이 별도 계보로 설명된다.

---

## Phase 6: User Story 4 — 실행할 수 없는 이유를 정확히 구분한다 (Priority: P3)

**Goal**: target 기능 부재, runner 미준비, 접근 차단, 완전 준비를 구분하고 READY가 아닐 때 Run을 만들지 않는다.

**Independent Test**: capability 조합 fixture 네 종류를 preflight해 정확한 readiness와 해결 안내가 나오며 Run root에 새 Run이 0개인지 확인한다.

### Tests for User Story 4 — write first

- [X] T064 [P] [US4] Add a readiness matrix for `NOT_IMPLEMENTED|PARTIAL` → RUNNER_NOT_READY, reporting present/hook, trigger receipt, or deterministic model substitute missing → RUNNER_NOT_READY, access denied with implementation complete → ACCESS_BLOCKED, all ready → READY, and reporting absent → NO_TEST_TARGET in `tests/unit/test_readiness.py` [FR-003~006, FR-050, FR-055, SC-010]
- [X] T065 [P] [US4] Add WhyYou capability probe tests for route/domain presence, credential access, schema signature, Chromium, shared fault marker+receipt root, hook health, fixed model fixture ID/digest, target block, and operator action text in `tests/contract/test_whyyou_capability.py` [FR-003~006, FR-055]
- [X] T066 [P] [US4] Add a CLI preflight test proving every non-READY result uses exit 2 and creates zero Run directories in `tests/contract/test_cli_preflight.py` [FR-006]

### Implementation for User Story 4

- [X] T067 [US4] Complete readiness precedence, `NOT_IMPLEMENTED|PARTIAL|IMPLEMENTED` projection, per-capability detail, checked_at, canonical `target_version`, and non-READY operator_action aggregation in `engine/readiness.py` [FR-003~006, FR-050]
- [X] T068 [US4] Implement and compose WhyYou-specific capability classification for route/access, browser, seed mapping, shared marker+receipt root, fault hook, deterministic model fixture ID/digest, restore probe, and target block in `engine/adapters/whyyou/capability.py` and `engine/adapters/whyyou/adapter.py`, without treating runner capability gaps as NO_TEST_TARGET [FR-003~005, FR-055, SC-010]
- [X] T069 [US4] Implement `controlproof preflight H-03 --target whyyou-local --json` and hard Run refusal for non-READY states in `engine/cli.py` and `engine/runner.py` [FR-004~006]
- [X] T070 [US4] Run `pytest -q tests/unit/test_readiness.py tests/contract/test_whyyou_capability.py tests/contract/test_cli_preflight.py` and fix only US4 implementation files until the story passes independently

**Checkpoint**: 검증 공백과 대상 기능 부재가 더 이상 같은 상태로 보고되지 않는다.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 보안, 추적성, 실제 재현성과 저장소 품질을 전체 스토리에 걸쳐 마감한다.

- [X] T071 [P] Add a repository-wide secret/PII redaction regression corpus for Authorization, cookies, access/refresh tokens, signed URLs, email/name/phone, DB credentials, and invitation token hashes in `tests/unit/test_redaction_security.py` [FR-038~040, SC-009]
- [X] T072 [P] In the WhyYou repository, add compose/production tests proving fault hooks and model substitute default to disabled, production startup rejects either test control, and local/test health exposes only fixture ID/digest in `backend/tests/integration/test_controlproof_fault_hook_safety.py` [FR-015, FR-055]
- [X] T073 Add an FR/SC/H03-A/EV → task → test → implementation traceability table in `specs/001-execution-evidence-h03/traceability.md` [Constitution VII]
- [X] T074 [P] Update installation, preflight, first Run, review, verify, retest, restore-failure recovery, and “target FAIL ≠ ControlProof implementation failure” guidance in `README.md`
- [ ] T075 Execute every command in `specs/001-execution-evidence-h03/quickstart.md` against a clean virtual environment and correct only the guide or implementation paths that fail
- [X] T076 Run `ruff check .` and the complete `pytest -q` suite, then record the verified commands and results in `specs/001-execution-evidence-h03/validation.md`
- [ ] T077 After T065, T068, T069, and T072 pass, execute one opt-in H-03 Run against the isolated WhyYou local stack with the fixed model fixture, verify EV-01~EV-09, trigger receipt, target-provided decision reason semantics, environment restore, and separate report-processing recovery, then record only the non-sensitive Run ID, canonical target snapshot digest and source-kind components, model fixture digest, implementation status, verdict, bundle digest, and test date in `specs/001-execution-evidence-h03/validation.md` [FR-008, FR-050, FR-055, SC-001, SC-003~005, SC-009]
- [ ] T078 Re-run `controlproof verify` on the first Run after a child retest and record that the parent bundle digest is unchanged in `specs/001-execution-evidence-h03/validation.md` [SC-006~007]

---

## Dependencies & Execution Order

### Phase dependencies

```text
Phase 1 Setup
    ↓
Phase 2 Foundation
    ↓
Phase 3 US1 — executable H-03 MVP
    ├──────────────→ Phase 4 US2 — review and integrity
    ├──────────────→ Phase 5 US3 — retest lineage
    └──────────────→ Phase 6 US4 — readiness UX
                         ↓
                  Phase 7 Polish/validation
```

- **Setup** has no dependency.
- **Foundation** depends on Setup and blocks every story.
- **US1** is the MVP and must complete before real WhyYou validation.
- **US2** consumes sealed Run bundles from US1 but its judgement/verify fixtures are independently testable.
- **US3** requires a terminal sealed Run contract from US1 and bundle verification from US2 for the final integrated path; unit work can begin after Foundation.
- **US4** can implement its fixture-based matrix after Foundation; the real WhyYou capability probe reuses the adapter configuration created in US1.
- **Polish** depends on every story selected for the release.

### Key task dependencies

- T011 blocks T012~T019.
- T014 and T016 block T018.
- T021~T029 are written before T030~T043.
- T029 must fail before T037~T038 modify WhyYou.
- T031 blocks T033; T032~T036 and T037 can proceed in parallel.
- T030, T032~T039 block T040; T040 blocks T041~T043.
- T045~T048 precede T049~T054.
- T056~T057 precede T058~T062.
- T064~T066 precede T067~T069.
- T077 requires ControlProof capability T065/T068/T069 and the WhyYou-side T037/T038/T072 changes to be complete; it is the first real local-stack Run and must not be executed at T043.

## Parallel Execution Examples

### Foundation

```text
T006 models tests | T007 lifecycle tests | T008 observation tests | T009 scenario tests | T010 bundle tests
after T011:
T012 lifecycle | T013 observations | T014 scenario | T015 evidence | T016 adapter protocols | T017 config
```

### User Story 1

```text
Tests: T021 | T022 | T023 | T024 | T025 | T026 | T027 | T028 | T029
Adapters after shared contracts: T032 | T033 | T034 | T035 | T036
WhyYou helper T037 can proceed beside ControlProof YAML T030 and seed T031
```

### User Story 2

```text
T045 judgement matrix | T046 conflicts | T047 tamper | T048 CLI contract
after tests: T050 bundle verify | T051 presentation | T053 fixtures
```

### User Story 3 and 4

```text
US3 tests T056 | T057; after T058, diff T059 can proceed before CLI T060
US4 tests T064 | T065 | T066; then readiness T067 and capability T068 can proceed in parallel
```

## Implementation Strategy

### MVP first

1. Phase 1 Setup
2. Phase 2 Foundation
3. Phase 3 User Story 1
4. Stop and run T044 against the deterministic local harness
5. Review the sealed result; a truthful FAIL is an acceptable target result

### Incremental delivery

1. **US1** proves active verification, recovery, and evidence capture end to end.
2. **US2** makes the result reviewable and tamper-evident.
3. **US3** proves improvement without rewriting history.
4. **US4** makes execution gaps reportable before a Run starts.
5. **Polish** runs T077 only after US4 capability/preflight completion and validates the actual isolated WhyYou path and documentation.

### Team split after Foundation

- Developer A: US1 orchestration, judge, CLI
- Developer B: WhyYou adapter, seed, fault/browser capture
- Developer C: WhyYou test hook and target-side safety tests
- US2/US3/US4 start from their fixture tests as soon as their declared shared contracts are stable.

## Notes

- Commit after each task or small coherent task group; never combine the first target FAIL Run with a WhyYou protection fix.
- WhyYou-side tasks are committed in the WhyYou repository, and ControlProof records the canonical TargetSnapshot including the exact target commit rather than copying target code.
- Do not add DLQ exhaustion, general Kanban bypass, post-recovery idempotency, or E-03 Outbox completeness to this Spec; they belong to Spec 002.
- Do not store actual applicant data, raw bearer values, full logs, or full database dumps.
- A task is complete only when its linked tests fail before implementation where applicable and pass afterward.

---

## Phase 8: Convergence

**Purpose**: 완료 표시된 구현과 승인된 Spec·Plan·계약 사이에 남은 실행 의미 차이를 제거한다. 이 Phase는 H-03의 제품 범위를 넓히지 않으며, T055·T075·T077·T078의 사람 검토·clean-environment·실제 스택 검증을 대체하지 않는다.

- [ ] T079 [US1] Add integration tests for delayed worker receipts, transient report states, no-stable-state deadlines, and delayed restore health; then wire `engine/runner.py`, `engine/observations.py`, and `engine/adapters/whyyou/fault.py` so EV-03 receipt probing uses the injected deadline, assertion inputs use the scenario's 3-consecutive/4-second stable observation rather than the last sample, all raw samples stay append-only, and marker/worker recovery is re-probed through the 120-second restore deadline while `environment_restore` remains separate from `report_processing_recovery` [FR-017~019, FR-026, H03-A1~A2, H03-A6]
- [ ] T080 [P] [US2] Add adversarial bundle tests for omitted canonical files, manifest/run ID mismatch, artifact envelope dimension mismatch, EV-to-envelope cross-link mismatch, wrong artifact type/cardinality per EV-01~EV-09, dirty actual-Run target snapshots, and PASS bundles containing an unverified mapped artifact; then harden read-only verification in `engine/evidence.py` without repairing the source bundle [FR-008, FR-035~041, SC-003, SC-006]
- [ ] T081 [P] [US3] Add lineage tests that vary the synthetic subject role and baseline initial state independently; then persist a canonical `TestSubject` projection with sanitized locators and a baseline-derived `initial_state_digest` in `engine/runner.py`, and compare parent/child subject role plus initial-state digest from their actual bundle records in `engine/retest.py` and `retest-diff.json` instead of emitting fixed subject text [FR-009~012, FR-051~053]
- [ ] T082 [P] [US1] Add CLI contract tests for `run`, `show`, and `retest` proving the outer machine envelope always keeps `schema_version=controlproof.cli.v1` and the command name cannot be overwritten by the review projection; then fix payload composition in `engine/cli.py`, preserving any review projection version under an unambiguous nested or separately named field [FR-049~050]
- [ ] T083 [US1] Add interruption tests after seed, baseline, trigger, decision attempt, and restore entry; then persist an append-only, fsync-backed step checkpoint record from `engine/runner.py` for every scenario step with Run/subject/phase/step/attempt, started/succeeded/failed outcome, timestamp, and sanitized error code so an unsealed or ABORTED bundle can prove the last completed step without inferring it from missing files [FR-007, FR-010, FR-013, FR-018, FR-021]
