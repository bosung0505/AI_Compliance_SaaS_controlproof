---

description: "Spec 004 E-01·E-02 점수 근거·평가 기준 보존 검증의 구현 작업 목록"
---

# Tasks: E-01·E-02 점수 근거·평가 기준 보존 검증

**Input**: `specs/004-e01-e02-score-evidence/`의 spec, plan, research, data model, contracts, quickstart
**Tests**: Spec이 assertion별 단위·계약·통합 시험, 샌드박스 진단, 최초 actual Run과 불변 retest를 요구하므로 시험 작업을
구현보다 먼저 둔다. 각 구현 작업은 앞선 시험이 실패(RED)하는 것을 확인한 뒤 시작한다.
**Organization**: 공통 기반과 별도 WhyYou fixture Phase 뒤에 5개 사용자 스토리를 독립 검증 가능한 증분으로 구성한다.
`[FR-*]`, `[SC-*]`, `[E01-A*]`, `[E02-A*]`, `[E01-D1]`, `[EV4-*]`는 추적 ID다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 선행조건이 충족되면 다른 파일의 작업과 병렬 실행 가능
- **[Story]**: 기능 Spec의 사용자 스토리. **[WY]**는 WhyYou 저장소 작업
- 모든 작업은 수정하거나 생성할 정확한 파일 경로를 포함한다.
- `../gbsa_aws/` 작업은 `eec8f70`(또는 그때의 `bosung/controlproof-n02-integration` HEAD)에서 분기한 개인 브랜치에서만
  하고 remote `fork`에만 push한다. origin·`main`·`master`에는 commit·push하지 않는다.
- WhyYou **제품 코드**(`reporting/`, `runtime/worker.py`, `company_management/` 등)는 Phase 9의 조건부 보완에서, 최초
  actual Run 봉인·원인 분류·승인 뒤에만 바꾼다. 조건이 성립하지 않으면 증적 참조와 함께 `NOT_REQUIRED`로 기록한다.
- 공식 actual Run(T080, T081, T088, T092, T097)은 preflight READY 확인 뒤 사용자가 명시적으로 승인했을 때만 실행한다.
  샌드박스 진단(T073~T077)은 격리 대상에서만 하며 공식 Run이 아니다.
- 작업 하나는 한 세션 안에 끝날 크기다. 더 커지면 같은 번호에 `a`/`b`를 붙여 나누고 이유를 `validation.md`에 남긴다.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Spec 004 local/test 설정, 결정론 fixture와 구현 기록 뼈대를 준비한다.

- [X] T001 Add secret-free Spec 004 variable names (`CONTROLPROOF_MODEL_FIXTURE_ID=spec004-report-v1` example, shared observer root, scoring-source pin override disabled by default) to `.env.example` [FR-001, FR-003, FR-034]
- [X] T002 [P] Create deterministic builders for the six lanes, criterion markers and codes, emission receipts, citation cases, report record/read snapshots for every phase, change injections, version snapshots, frozen input sets, recompute records and PASS/FAIL/INCONCLUSIVE facts in `tests/fixtures/spec004.py` [FR-010~013, FR-020~022, FR-030~034, EV4-01~EV4-10]
- [X] T003 [P] Copy the WhyYou `eec8f70` scoring test cases from `../gbsa_aws/backend/tests/unit/reporting/test_weighted_scoring.py` into a data file `tests/fixtures/whyyou_scoring_vectors.json` with the source path and blob SHA in its header; read only, no WhyYou change [FR-033, FR-034]
- [X] T004 [P] Create implementation-time record templates (source SHAs, commands, sandbox diagnostics, Run IDs, manifest digests, conditional remediation) in `specs/004-e01-e02-score-evidence/validation.md` and `specs/004-e01-e02-score-evidence/implementation-decisions.md`; do not claim an unexecuted result [FR-050, SC-005]

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 두 profile이 공유하는 scenario v4, profile policy, Spec 004 모델, 재계산 사본, adapter protocol과 bundle profile을
고정한다.

**⚠️ CRITICAL**: 이 Phase가 끝나기 전에는 사용자 스토리 구현을 시작하지 않는다. Phase 3(WhyYou)과는 병렬로 진행할 수 있다.

### Foundation tests — write first and confirm failure

- [X] T005 [P] Add model tests for both profiles, `E01LaneId`/`E02LaneId`, `LaneCriterion` rules (matrix code order, `OTHER_APPLICANT` argument provenance, absent `NONEXISTENT` UUID, mandatory E-02 scores), `ModelEmissionReceipt`, `CitationCase`, report record/read snapshots, `ChangeInjection` lifecycle, `CriteriaVersionSnapshot`, `FrozenInputSet` and `RecomputeRecord` in `tests/unit/test_models_spec004.py` [FR-002, FR-012, FR-020~022, FR-030~034, FR-041]
- [X] T006 [P] Add scenario v4 contract tests for both canonical profiles: assertion/diagnostic IDs, per-profile EV4 subsets, lanes, capability sets (18 and 16), ordered steps, always-run set, timing values, single allowed fixture, `scoring-source-pinned` precondition and rejection of forbidden steps; v1/v2/v3 loading unchanged in `tests/contract/test_scenario_profile_v4.py` [FR-040, FR-043, SC-003]
- [X] T007 [P] Add bundle-profile tests for `controlproof.bundle-profile.spec004.v1`: required files per profile, EV4 mapping, missing/unregistered/tampered files, Spec 001~003 bundles still verifying in `tests/contract/test_bundle_profile_spec004.py` [FR-042, SC-004, EV4-01~EV4-10]
- [X] T008 [P] Add CLI/profile registry tests for `PROFILE_REQUIRED`/`PROFILE_MISMATCH` on E-01/E-02, registry dispatch, unchanged H-03/E-03/N-02 selection, and non-READY preflight leaving no Run directory, subject row, version or report request in `tests/contract/test_cli_spec004_profile.py` [FR-001, FR-043]
- [X] T009 [P] Add scoring-copy tests against `tests/fixtures/whyyou_scoring_vectors.json` plus `None` exclusion, zero weight total, missing axis key = 1.0, communication-separated config, zero denominator and the H-2 boundary cases 72.5→72 and 73.5→74 in `tests/unit/test_e02_scoring_copy.py` [FR-033, FR-034, E02-A3]
- [X] T010 [P] Extend the security corpus with report summary/observation/rationale/uncertainty/follow-up text, question/answer/transcript text, criterion description body, playback URL and Idempotency-Key in `tests/unit/test_redaction_security.py` [FR-042, SC-004]
- [X] T011 [P] Extend `tests/contract/test_package_layout.py` to load the new Spec 004 modules and add `tests/integration/test_spec003_v3_regression.py` proving the sealed N-02 fixtures and profile still execute and verify unchanged [FR-043]

T005~T011 RED tests are strict `xfail` with the intended exception (ID-004-01); each reason names the task that
removes its marker in the same change that turns it green. 113 RED, 15 new guards PASS (`validation.md`).

### Foundation implementation

- [ ] T012 Implement the `data-model.md` entities and invariants in `engine/models.py` (profiles, lane enums, `LaneCriterion`, receipts, cases, snapshots, injections, version snapshots, frozen inputs, recompute records) [FR-002, FR-012, FR-020~022, FR-030~034, FR-041]
- [ ] T013 Implement additive scenario v4 loading and canonical E-01/E-02 validation in `engine/scenario.py`; widen `lanes` to profile-specific enums; keep v1/v2/v3 behavior [FR-040, FR-043]
- [ ] T014 [P] Add the eight Spec 004 protocols (`Spec004SeedAdapter`, `ReportRequestAdapter`, `ReportRecordAdapter`, `EvidenceMutationAdapter`, `CriteriaVersionAdapter`, `ModelEmissionAdapter`, `ScoringSourceAdapter`, reused `ConsentAdapter`) with sanitized envelopes in `engine/adapters/base.py` after T012 [FR-001, FR-004]
- [ ] T015 [P] Extend `engine/config.py` with typed Spec 004 settings (expected fixture ID, observer root, scoring blob pins) and fail-closed validation [FR-001, FR-034]
- [ ] T016 Add Spec 004 profile policies to Run validation and the profile registry in `engine/runner.py` without inheriting Spec 002 queue requirements; executors are registered later by T040 and T057 [FR-040, FR-043]
- [ ] T017 [P] Implement the WhyYou scoring-rule copy with pinned source blobs (`scoring.py` `61d1e615…`, `report.py` `81428968…`) in `engine/judges/e02_scoring.py` [FR-033, FR-034]
- [ ] T018 [P] Add the Spec 004 profile registry, canonical writers and base verifiers to `engine/evidence.py` without rewriting existing sealed bundles [FR-042, EV4-01~EV4-10]
- [ ] T019 Extend deterministic fakes for all Spec 004 protocols (report generation outcomes, emission receipts, removal/restore outcomes, version create/publish, source unavailable, restore failure) in `tests/fixtures/fake_adapters.py` after T012 and T014 [FR-010~013, FR-020~022, FR-030~034]
- [ ] T020 Add E-01/E-02 to the CLI profile table and scenario path map in `engine/cli.py` [FR-043]
- [ ] T021 Run T005~T011 and record exact commands and results in `specs/004-e01-e02-score-evidence/validation.md` [FR-001, FR-040, FR-042, FR-043]

**Checkpoint**: Spec 001~003 회귀를 깨뜨리지 않는 Spec 004 공통 모델·계약·재계산 사본이 준비된다.

---

## Phase 3: WhyYou local/test fixture `spec004-report-v1` [WY]

**Purpose**: 인용 모드·기준별 점수·emission receipt를 가진 고정 모델 대체물을 별도 WhyYou 작업과 PR로 만든다. 제품 코드는
바꾸지 않는다. 계약: `contracts/whyyou-spec004-fixture.md`.

**Independent Test**: WhyYou 단위 시험만으로 다섯 모드, 표식 없음 = `h03-report-v1`, 세션 경계 기억, receipt를 검증한다.

- [X] T022 [WY] Create `yeonwoo/controlproof-e01-e02-fixture` from `eec8f70` in `../gbsa_aws`, confirm clean state and record branch/HEAD in `specs/004-e01-e02-score-evidence/validation.md` [FR-001]
T023~T025 edit the same WhyYou test file, so run them in order (not in parallel). They can run alongside Phase 2.

- [X] T023 [WY] Add failing tests for marker parsing, the five modes, `score=`, no marker = `h03-report-v1` output, empty answers, `MARKER_INVALID`, unknown fixture ID startup rejection and unchanged `h03-report-v1` digest in `../gbsa_aws/backend/tests/unit/runtime/test_controlproof_model_substitute.py` [FR-010, FR-012, SC-007]
- [X] T024 [WY] Add failing tests for `OTHER_CRITERION` memory in the same test file: same-call UUIDv7 timestamp guard, refusal across calls (`MODE_SOURCE_MISSING`), 256-entry bound, and `OTHER_APPLICANT` using only the marker argument, never memory [FR-012]
- [X] T025 [WY] Add failing tests for emission receipts in the same test file: fields, atomic write under `{observer_root}/model/`, no write without observer root, write failure not blocking the response, no question/answer/criterion text [FR-010, FR-042]
- [X] T026 [WY] Implement fixture `spec004-report-v1` (identity/digest, marker parser, modes, scores, bounded memory with timestamp guard, health fixture reporting) in `../gbsa_aws/backend/src/interview_evidence/runtime/controlproof_model_substitute.py` [FR-010, FR-012, SC-007]
- [X] T027 [WY] Implement the emission receipt writer in the same file [FR-010, FR-042]
- [X] T028 [WY] Run the scoped WhyYou tests, the `backend/tests/unit/reporting` and `backend/tests/unit/runtime` suites and `ruff check` on changed files; record counts and the known pre-existing failure in `specs/004-e01-e02-score-evidence/validation.md` [FR-010]
- [X] T029 [WY] Push the branch to remote `fork` and open a PR with base `bosung/controlproof-n02-integration`; record PR number and head SHA in `specs/004-e01-e02-score-evidence/validation.md`. Merging is the reviewer's decision; Phases 8~9 use the PR head or the merged base, whichever the reviewer designates [Dependencies]

**Checkpoint**: 인용 모드 fixture가 단위 시험으로 검증되고 PR이 열려 있다. 제품 코드 변경 없음.

---

## Phase 4: User Story 1 — 유효하지 않은 인용으로 점수 저장을 시도한다 (Priority: P1) 🎯 First Slice

**Goal**: 인용 모드 fixture의 출력이 작업자 검증·저장을 거쳐 어떻게 저장되는지 E01-A1·A2로 판정한다.

**Independent Test**: fake 대상에서 E-01의 참조·matrix lane만 실행해 네 잘못된 모드는 비워져 PASS, 점수가 남으면 FAIL,
receipt가 없거나 다르면 INCONCLUSIVE인지 확인한다.

### Tests for User Story 1 — write first

- [ ] T030 [P] [US1] Add seed/teardown contract tests: atomic multi-lane seed with rollback, criterion markers and matrix code order, per-criterion question/answer turns, rationale `target_criterion_id`, segment inside its turn range, `final_video` asset, no seeded consent/report, matrix seeded only after the reference report with its real Evidence ID, absent `NONEXISTENT` UUID, FK-catalog teardown of Run-owned rows only, in `tests/contract/test_spec004_seed_adapter.py` [FR-002, FR-003, FR-012, EV4-02]
- [ ] T031 [P] [US1] Add report adapter contract tests: report request outbox identity, handler/started/refused receipts, record projection allowlist with text hashing, report/timeline API projection, `unknown_fields`, `ABSENT` versus `UNAVAILABLE`, in `tests/contract/test_spec004_report_adapters.py` [FR-003, FR-004, FR-010, EV4-04, EV4-05]
- [ ] T032 [P] [US1] Add emission adapter tests (Run filtering by criterion ID, malformed receipt → `UNAVAILABLE`) in `tests/contract/test_spec004_model_emission_adapter.py` [FR-010, EV4-03]
- [ ] T033 [P] [US1] Add E01-A1/A2 judge tests: all four modes emptied PASS, residual score FAIL, invalid ID in axis or Evidence row FAIL, reference report changed FAIL, receipt missing/mismatch/`MODE_SOURCE_MISSING` INCONCLUSIVE, unverified notice not required for PASS, VALID PASS/FAIL in `tests/unit/test_judge_e01_citation.py` [FR-010~012, E01-A1, E01-A2]
- [ ] T034 [P] [US1] Add the citation journey on fakes (consent before request, refused receipt → `PRECONDITION_NOT_MET`, reference-first ordering) in `tests/integration/test_e01_citation_orchestration.py` [FR-004, FR-010~012]

### Implementation for User Story 1

- [ ] T035 [P] [US1] Create deterministic lane, criterion code/marker/score and synthetic identity definitions in `seeds/spec004_subjects.py` [FR-002, FR-003, FR-012]
- [ ] T036 [US1] Implement `Spec004SeedAdapter` (atomic seed, late matrix seed, Run-only FK teardown reusing `n02_seed.py` helpers) in `engine/adapters/whyyou/spec004_seed.py` [FR-002, FR-003, FR-012, EV4-02]
- [ ] T037 [P] [US1] Implement `ReportRequestAdapter` (reusing the `protected_processing.py` outbox insert) and `ReportRecordAdapter` (DB projection, report/timeline API) in `engine/adapters/whyyou/report_records.py` [FR-003, FR-004, EV4-04, EV4-05]
- [ ] T038 [P] [US1] Implement `ModelEmissionAdapter` in `engine/adapters/whyyou/model_emission.py` [FR-010, EV4-03]
- [ ] T039 [P] [US1] Create the canonical `scenarios/E-01.yaml` from `contracts/scenario-profile-v4.md` [FR-040, FR-043]
- [ ] T040 [US1] Implement shared lane orchestration (seed, consent, report request, stabilized report wait) in `engine/executors/report_lanes.py` and the citation steps of `engine/executors/e01.py`; register the E-01 executor in `engine/runner.py` [FR-004, FR-010~012]
- [ ] T041 [US1] Implement E01-A1/A2 in `engine/judges/e01.py` and register it in `engine/judge.py` [E01-A1, E01-A2]
- [ ] T042 [US1] Compose the E-01 citation-path capabilities (12 common + `model.emission.read`, `timeline.api.read`) and readiness (fixture ID, observer root, emission directory) with non-empty `operator_action` in `engine/adapters/whyyou/adapter.py`; the mutation capabilities follow in T047 [FR-001]
- [ ] T043 [US1] Run T030~T034 and the implementation tests; record the citation gate in `specs/004-e01-e02-score-evidence/validation.md` [FR-010~012, E01-A1, E01-A2, EV4-02~EV4-04]

**Checkpoint**: 잘못된 인용 네 종류와 기준 사례를 독립 판정할 수 있다. E-01 전체 완료를 주장하지 않는다.

---

## Phase 5: User Story 2 — 저장 뒤 근거를 제거하고 노출을 확인한다 (Priority: P1)

**Goal**: Run 소유 자막 구간을 지우고 다시 넣으며 E01-A3·A4를 판정하고, 보조 deep probe를 진단 E01-D1로 기록한다.

**Independent Test**: fake 대상에서 removal·storage-probe lane만 실행해 H-4 네 지표 각각 PASS, P1 형태 FAIL, 복원 실패
`RESTORE_FAILED`, D1이 verdict에 영향 없음을 확인한다.

### Tests for User Story 2 — write first

- [ ] T044 [P] [US2] Add mutation adapter contract tests: segment ownership and no cross-lane reference, delete affects one row, absence on a separate connection, reinsert digest equality, digest mismatch → `RESTORE_FAILED`, axis JSON write/restore touching only `axis_assessments`, foreign rows untouched, in `tests/contract/test_spec004_evidence_mutation_adapter.py` [FR-013, FR-020, FR-022, FR-041, EV4-09]
- [ ] T045 [P] [US2] Add E01-A3/A4 judge tests: each of the four H-4 indicators PASS, unchanged score/citation FAIL (P1), unaffected item changed FAIL, POST_REMOVAL 5xx FAIL, removal unconfirmed or `unknown_fields` INCONCLUSIVE, A4 PASS/FAIL, restore failure precedence, D1 not affecting verdict or exit code, in `tests/unit/test_judge_e01_removal.py` [FR-013, FR-020~022, E01-A3, E01-A4, E01-D1]
- [ ] T046 [P] [US2] Add restore integration tests: always-run restore on exception, timeout and cancellation; block on unsafe restore; restore budget counts only restore work (ID-003-19) in `tests/integration/test_e01_removal_restore.py` [FR-022, FR-041, SC-002]

### Implementation for User Story 2

- [ ] T047 [US2] Implement `EvidenceMutationAdapter` in `engine/adapters/whyyou/evidence_mutation.py` and compose the `evidence.segment.remove/restore` and `report.axes.probe_write/probe_restore` capabilities in `engine/adapters/whyyou/adapter.py`; E-01 preflight reaches 18/18 only after this task [FR-001, FR-013, FR-020, FR-022, EV4-09]
- [ ] T048 [US2] Add removal, restore, storage-probe and probe-restore steps with always-run cleanup to `engine/executors/e01.py` [FR-013, FR-020~022, FR-041]
- [ ] T049 [US2] Implement E01-A3/A4 and the E01-D1 diagnostic projection in `engine/judges/e01.py` [E01-A3, E01-A4, E01-D1]
- [ ] T050 [US2] Extend `engine/execution.py` only where needed so an unsafe Spec 004 restore writes the block for subject `e01-citation-evidence`/`e02-scoring-freeze` and `cleanup-confirm` accepts matching read-only evidence; keep H-03/N-02 behavior [FR-022, FR-041, SC-002]
- [ ] T051 [US2] Run T044~T046 and the implementation tests; record the removal gate in `specs/004-e01-e02-score-evidence/validation.md` [FR-020~022, E01-A3, E01-A4, EV4-05, EV4-09]

**Checkpoint**: 근거 제거·복원과 진단 노출을 판정할 수 있다. 실제 WhyYou 결과는 Phase 9를 기다린다.

---

## Phase 6: User Story 3 — 기준 변경 뒤 과거 리포트가 보존되는지 확인한다 (Priority: P1)

**Goal**: 제품 API로 v1·v2를 발행하고 두 지원자를 처리해 E02-A1~A3을 판정한다.

**Independent Test**: fake 대상에서 E-02를 끝까지 실행해 동결·불변·재계산 PASS, 각 비교 대상 불일치 FAIL, 두 번째 보고서가
v2가 아니면 INCONCLUSIVE인지 확인한다.

### Tests for User Story 3 — write first

- [ ] T052 [P] [US3] Add criteria-version adapter contract tests: create body (job requirement, 30 minutes, weights 100, axis weights, markers), 201/422 mapping, publish with `If-Match`, `latest_published` = published with max `version_number`, `other_positions_digest`, scoring blob read, no token in output, in `tests/contract/test_spec004_criteria_version_adapter.py` [FR-031, FR-034, EV4-06]
- [ ] T053 [P] [US3] Add E02 judge tests: A1 missing field and weight mismatch FAIL; A2 unchanged PASS, changed FAIL, second report not on v2 INCONCLUSIVE; A3 mismatch on each of the five comparison targets FAIL, float tolerance `1e-9`, integer exactness, in `tests/unit/test_judge_e02.py` [FR-030~033, E02-A1~E02-A3]
- [ ] T054 [P] [US3] Add the E-02 journey on fakes (v1 publish → first report → v2 publish → latest-published seed → second report → compare/recompute → Run-owned teardown with other positions unchanged; restore failure path) in `tests/integration/test_e02_orchestration.py` [FR-031, FR-032, FR-041, SC-002]

### Implementation for User Story 3

- [ ] T055 [US3] Implement `CriteriaVersionAdapter` and `ScoringSourceAdapter` in `engine/adapters/whyyou/criteria_versions.py` [FR-031, FR-034, EV4-01, EV4-06]
- [ ] T056 [P] [US3] Create the canonical `scenarios/E-02.yaml` with the H-2 score markers and weights from `plan.md` [FR-031, FR-040]
- [ ] T057 [US3] Implement `engine/executors/e02.py` on top of `engine/executors/report_lanes.py` and register it in `engine/runner.py` [FR-030~032, FR-041]
- [ ] T058 [US3] Implement E02-A1~A3 in `engine/judges/e02.py` using `engine/judges/e02_scoring.py`, and register it in `engine/judge.py` [FR-030~034, E02-A1~E02-A3]
- [ ] T059 [US3] Compose E-02 capabilities and the preflight scoring-source check (`SCORING_RULE_SOURCE_DRIFT`) in `engine/adapters/whyyou/adapter.py` [FR-001, FR-034]
- [ ] T060 [US3] Run T052~T054 and the implementation tests; record the E-02 gate in `specs/004-e01-e02-score-evidence/validation.md` [FR-030~034, E02-A1~E02-A3, EV4-06~EV4-08]

**Checkpoint**: E-02 동결·불변·재계산을 자동 fixture에서 판정할 수 있다.

---

## Phase 7: User Story 4 — 결과와 증적 한계를 검토한다 (Priority: P2)

**Goal**: 두 profile의 결과·증적·한계를 CLI에서 혼동 없이 보여 주고 bundle을 완전하게 검증한다.

**Independent Test**: PASS, 직접 FAIL, 증적 부족, 전제 실패, 복구 실패 fixture를 show/verify해 verdict·사유·증적 참조·한계
문구를 확인한다.

### Tests for User Story 4 — write first

- [ ] T061 [P] [US4] Add verdict matrix and precedence cases for both profiles (`RESTORE_FAILED`, direct FAIL, conflict, insufficient evidence, precondition) in `tests/integration/test_spec004_verdict_matrix.py` [FR-040, SC-001]
- [ ] T062 [P] [US4] Add presentation contracts for mode results, removal comparison, D1, version binding, recompute table, `limitations` (fixture input, external AI blocked, fixed model) and claim boundary in `tests/contract/test_presentation_spec004.py` [FR-003, SC-007]
- [ ] T063 [P] [US4] Add CLI contracts for E-01/E-02 preflight (capability counts 18/16, fixture, scoring source), run/show/verify projections, stable exit codes, non-empty `operator_action`, zero preflight side effects, no automatic retest in `tests/contract/test_cli_spec004.py` [FR-001, FR-040, FR-043]
- [ ] T064 [P] [US4] Add bundle-link integration tests for every cross-reference in `contracts/evidence-bundle-v4.md`: case↔receipt, injection phase ordering for A3/A4 reads, digest recomputation, recompute re-execution in verify, redaction failures in `tests/integration/test_spec004_bundle_links.py` [FR-042, SC-004, EV4-01~EV4-10]

### Implementation for User Story 4

- [ ] T065 [P] [US4] Extend `engine/presentation.py` with Spec 004 projections and limitation wording [FR-003, SC-007]
- [ ] T066 [US4] Implement E-01/E-02 preflight/run/show/verify dispatch and additive output in `engine/cli.py` [FR-001, FR-040, FR-043]
- [ ] T067 [US4] Complete Spec 004 cross-reference, readable-fact validation and recompute re-execution in `engine/evidence.py` [FR-042, EV4-01~EV4-10]
- [ ] T068 [US4] Add deterministic complete E-01 and E-02 orchestration tests with sealed, verified bundles and show projections in `tests/integration/test_spec004_orchestration.py` [SC-001~SC-004]
- [ ] T069 [US4] Run T061~T064 plus T068; record the review/bundle gate in `specs/004-e01-e02-score-evidence/validation.md` [FR-040~043, SC-001~SC-004, SC-007]

**Checkpoint**: 자동 fixture에서 두 시나리오의 결과와 한계를 검토할 수 있다. 실제 WhyYou 판정은 아니다.

---

## Phase 8: Retest machinery and isolated sandbox diagnostics

**Purpose**: child 경로를 먼저 준비하고, 공식 Run 전에 격리 대상에서 SD-1~SD-5를 확인한다. 진단은 공식 Run·verdict가
아니며 WhyYou 제품 결함 후보(P1)는 여기서 고치지 않는다.

### Retest (US5) — tests first

- [ ] T070 [P] [US5] Add retest tests for both profiles: inherited scenario/profile, fresh lanes/position/versions, new Run ID, target/fixture/scoring-source diff, parent read-only digest, refusal on unresolved block in `tests/integration/test_spec004_retest_lineage.py` [FR-050, FR-052, SC-005]
- [ ] T071 [US5] Extend `engine/retest.py` and the retest branch of `engine/cli.py` for E-01/E-02 without modifying parent files [FR-052]

### Sandbox diagnostics

- [ ] T072 Build the isolated sandbox (PostgreSQL 16+pgvector, moto S3/SQS, WhyYou API and workers from the T029 head with `spec004-report-v1`, loopback AI endpoints, separate observer root) as in Spec 003 ID-003-18; record setup and source SHAs, never the shared local DB, in `specs/004-e01-e02-score-evidence/validation.md` [FR-001, FR-003]
- [ ] T073 SD-4: run a diagnostic E-01 pass in the sandbox; record emission receipts against stored axes for all five modes and the full diagnostic Run duration against the 540-second budget in `specs/004-e01-e02-score-evidence/validation.md`; if the budget is at risk, record it as a runner finding for T078 before any official Run [FR-010~012, SC-003]
- [ ] T074 SD-2: on a diagnostic report, read `reports.overall_score`, `scoring_inputs`, items and the API `scoring_breakdown` (read-only SELECT/GET) and confirm the comparison shape and tolerance; record in `validation.md` [FR-033]
- [ ] T075 SD-3: diagnostic E-02 pass (v1→v2 publish, latest-published seed); confirm the second report uses v2 ID/weights and the H-2 totals (72, 74), and record the diagnostic Run duration against the 540-second budget in `validation.md` [FR-031, FR-032, SC-003]
- [ ] T076 SD-1: diagnostic segment removal/reinsert on a Run-owned segment; record report and timeline differences; if P1 is observed, record it as a prediction confirmed in the sandbox only and do not change WhyYou [FR-020~022, FR-051]
- [ ] T077 SD-5: diagnostic storage-probe write/read/restore; record exposure per mode [FR-013]
- [ ] T078 For every runner/observer defect found in T072~T077, add a failing test, apply the minimal fix in the file that owns it, rerun the full regression and record ID-004-xx in `specs/004-e01-e02-score-evidence/implementation-decisions.md`; if none, record `NOT_REQUIRED` [FR-050, SC-005]

**Checkpoint**: 공식 Run 전에 실행기 경로가 실제 작업자·DB·API에서 동작함을 진단으로 확인했다. 공식 판정 없음.

---

## Phase 9: User Story 5 — 최초 결과를 보존하고 수정 후 재시험한다 (Priority: P3)

**Goal**: 최초 E-01·E-02 actual Run을 있는 그대로 봉인하고, 증거로 분류된 결함만 보완한 뒤 child로 차이를 증명한다.

### Actual-stack first truth gate

- [ ] T079 [US5] On clean committed ControlProof and WhyYou branches (WhyYou = T029 head or the merged base), run both preflights from `quickstart.md`; record source SHAs, readiness, capability counts, fixture ID, scoring-source status and AWS `NOT_RUN` in `validation.md`; create no Run unless READY and approved [FR-001, FR-034, SC-006]
- [ ] T080 [US5] With approval, execute exactly one initial E-01 actual Run before any WhyYou product change; run show/verify; record Run ID, A1~A4, D1, restore status, timing and manifest SHA-256 in `validation.md` [FR-040~042, FR-050, SC-001~SC-004]
- [ ] T081 [US5] With approval, execute exactly one initial E-02 actual Run; run show/verify; record the same facts in `validation.md` [FR-040~042, FR-050, SC-001~SC-004]
- [ ] T082 [US5] Freeze the T080/T081 source/result mapping in `specs/004-e01-e02-score-evidence/traceability.md`; document every FAIL, INCONCLUSIVE and unavailable fact without changing the sealed bundles [FR-050]

If T080 or T081 ends `RESTORE_FAILED` (exit 6), stop, start no new change-injection Run, and follow `quickstart.md` §9. Do not
delete block files.

### Evidence-gated classification and conditional remediation

- [ ] T083 [US5] For every FAIL and INCONCLUSIVE in T080/T081, record the assertion, exact artifacts and root-cause class `TARGET_CONTROL_DEFECT|RUNNER_OR_OBSERVER_DEFECT|RESTORE_OPERATOR_DEFECT` in `implementation-decisions.md` (plan §8 step 3) [FR-050, SC-005]
- [ ] T084 [US5] Only for `RUNNER_OR_OBSERVER_DEFECT`: add the failing test, apply the minimal ControlProof fix in the owning file listed in this tasks file, run the full regression and record it; changes outside the listed files or product meaning stay `PROPOSED` until approved; otherwise `NOT_REQUIRED` [FR-050]
- [ ] T085 [US5] Only if T083 classifies E01-A3 as `TARGET_CONTROL_DEFECT` (P1 observed): record the WhyYou minimal-fix proposal as `PROPOSED` (report read path exposing missing transcript segments through an H-4 indicator, candidate files `../gbsa_aws/backend/src/interview_evidence/reporting/repositories/postgres.py` and `../gbsa_aws/backend/src/interview_evidence/reporting/api/company_routes.py`) and obtain approval; otherwise `NOT_REQUIRED` [FR-051]
- [ ] T086 [US5] Only after T085 approval: create `yeonwoo/controlproof-e01-e02-report-evidence` from the current WhyYou base, add the failing regression in `../gbsa_aws/backend/tests/unit/reporting/test_report_view_contract.py` (or a new `test_report_evidence_availability.py`), apply the approved minimal fix, run reporting/runtime unit suites and `ruff`, push to `fork` and open a PR; keep it separate from the T029 fixture PR [FR-051]
- [ ] T087 [US5] Only if T083 classifies an E01-A1/A2 or E02 assertion as `TARGET_CONTROL_DEFECT`: record the proposal, obtain approval, then follow the T086 pattern on its own branch and PR with failing tests first; otherwise `NOT_REQUIRED` [FR-050, FR-051]
- [ ] T088 [US5] If any T080/T081 FAIL was remediated, run a parent-linked child retest for that profile with approval, verify parent and child bundles, confirm the parent manifest is unchanged, and record SHAs and result differences; if no remediation was needed, re-verify the parents and record that no child was required, in `validation.md` [FR-052, SC-005]

**Checkpoint**: 최초 사실은 보존되고, 필요한 경우에만 수정 전→후 계보가 별도 Run으로 남는다.

---

## Phase 10: 종료 품질 gate (Polish & Cross-Cutting)

**Purpose**: 시간·보안·회귀·재현·추적성·인계를 두 시나리오 전체에 걸쳐 마감한다.

- [ ] T089 [P] Add deterministic timing tests proving poll/stability/restore/Run/verify budgets come only from the v4 scenario snapshots and the restore budget counts only restore work in `tests/integration/test_spec004_timing.py` [SC-003, SC-002]
- [ ] T090 [P] Extend the security corpus to every Spec 004 bundle file, emission receipts and CLI output in `tests/unit/test_redaction_security.py` [FR-042, SC-004]
- [ ] T091 Run `ruff check .`, the full `pytest -q` and the scoped WhyYou tests; record commands, counts, durations, target FAILs, restore statuses and source SHAs in `validation.md` [FR-001~FR-052, SC-001~SC-007]
- [ ] T092 Execute every unconditional `quickstart.md` command from a clean local environment, replace `<…>` placeholders with actual IDs, record skipped conditionals with reasons, and confirm each Run+verify ≤ 600 seconds [SC-003, SC-006]
- [ ] T093 Complete the FR/SC/assertion/EV4 → task → test → implementation → actual artifact matrix in `traceability.md` [FR-001~FR-052, SC-001~SC-007, E01-A1~A4, E02-A1~A3, Constitution VII]
- [ ] T094 Verify each conditional branch T084~T088 is completed or evidence-backed `NOT_REQUIRED`, and summarize the implementation versus target verdict distinction in `implementation-decisions.md` [FR-050~FR-052]
- [ ] T095 [P] Scan tracked files and bundle metadata for absolute user paths, raw credentials and real applicant identifiers; record the command and clean result in `validation.md` [FR-042, SC-004]
- [ ] T096 Update Spec 004 status, source SHAs, verdicts and next step consistently in `README.md`, `docs/TEAM_HANDOFF.md`, `docs/AI_SPEC_KIT_PLAYBOOK.md`, `docs/product/ControlProof_MVP_Product_Brief.md`, `docs/product/ControlProof_MVP_Scenario_Coverage_Matrix.md` and, for any product-meaning change, `docs/product/ControlProof_MVP_Decision_Log.md` [SC-006]
- [ ] T097 Have a second clean checkout or teammate follow only `README.md`, `docs/TEAM_HANDOFF.md` and `quickstart.md` through preflight and one Run per scenario; record SHAs, manifest digests and portability defects in `validation.md` [SC-006]

---

## Dependencies & Execution Order

### Phase dependencies

```text
Phase 1 Setup
    ↓
Phase 2 Foundation ─────────────┐        Phase 3 WhyYou fixture [WY] (parallel with Phase 2)
    ├──→ Phase 4 US1 (citation) │              │
    ├──→ Phase 5 US2 (removal)  │ needs T040    │
    └──→ Phase 6 US3 (E-02)     │              │
              ↓                 │              │
        Phase 7 US4 (review/CLI/bundle)        │
              ↓                                ↓
        Phase 8 retest + sandbox diagnostics (needs T029)
              ↓
        Phase 9 US5 actual Runs, classification, conditional fixes, child
              ↓
        Phase 10 closure gate
```

### Key task dependencies

- T012 → T013~T019; T014 → T019; T017 → T058; T020 → T066.
- T036 → T040; T037·T038 → T040; T040 → T048 and T057 (shared `report_lanes.py`).
- T047 → T048 → T049; T055 → T057 → T058.
- T026·T027 → T028 → T029 → T072 (sandbox uses the fixture).
- T069 and T071 → T072~T078 → T079.
- T079 → T080·T081 → T082 → T083 → T084~T087 → T088 → Phase 10.
- T085 → T086 (approval gate). T086/T087 never before T080/T081 are sealed.

### Parallel opportunities

- Phase 2 tests T005~T011 in parallel; T014, T015, T017, T018 in parallel after T012.
- Phase 3 runs alongside Phase 2 and Phase 4 tests (different repository).
- Within each story, all `[P]` tests in parallel; T035, T037, T038, T039 in parallel.
- Phase 5 and Phase 6 can proceed in parallel once T040 exists.
- T089, T090, T095 in parallel in Phase 10.

## Implementation Strategy

### First independently demonstrable slice

Phase 1 → Phase 2 → Phase 4 (US1) on fakes: E01-A1/A2 with deterministic emission receipts. The WhyYou fixture (Phase 3) can
proceed in parallel but is not needed until Phase 8.

### Core

US1 + US2 + US3 on fakes, then US4 for the combined CLI/bundle contract.

### Actual target closure

Phase 8 diagnostics → Phase 9 first truth → classification → approved minimal fixes → child → Phase 10.

### Suggested team split after Foundation

- 연우: Phase 4~5 (E-01), Phase 8~9 actual runs
- teammate: Phase 6 (E-02) and recompute copy
- WhyYou fixture (Phase 3) by whoever owns the WhyYou fork branch

## Notes

- 진단 Run(Phase 8)과 공식 Run(Phase 9)을 섞지 않는다. 진단 결과는 verdict가 아니다.
- 최초 FAIL·INCONCLUSIVE를 다시 돌려 덮어쓰지 않는다. `RESTORE_FAILED`면 즉시 멈춘다.
- 실제 AI 키·외부 AI 호출 금지(`CONTROLPROOF_EXTERNAL_AI_ALLOWED=false`).
- 문서에 개인 절대 경로·토큰·쿠키 값을 쓰지 않는다.
