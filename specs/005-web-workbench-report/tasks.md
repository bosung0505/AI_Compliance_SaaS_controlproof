---

description: "Spec 005 웹 워크벤치·12개 시나리오 카탈로그·결과 보고서의 구현 작업 목록"
---

# Tasks: 웹 워크벤치·12개 시나리오 카탈로그·결과 보고서

**Input**: `specs/005-web-workbench-report/`의 spec(Clarified, 목업 조건부 승인), plan, research, data model, contracts, quickstart, 승인 목업
**Tests**: Spec이 화면 판정의 봉인 기록 일치(SC-002), 노출 검사(SC-007), 화면 시험(1280·1024px), actual validation과 사용성 검토를 요구하므로
시험 작업을 구현보다 먼저 둔다. 각 구현 작업은 앞선 시험이 실패(RED)하는 것을 확인한 뒤 시작한다.
**Organization**: 웹이 기대는 엔진 보완을 Foundational에 두고, 사용자 스토리 US1~US5를 독립 검증 가능한 증분으로 구현한 뒤, 사람 승인이 필요한
actual validation, 사용성 검토(US6), converge 순서로 둔다. `[FR-*]`, `[SC-*]`, `[R-*]`(research)는 추적 ID다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 선행조건이 충족되면 다른 파일의 작업과 병렬 실행 가능
- **[Story]**: 기능 Spec의 사용자 스토리(US1~US6)
- 모든 작업은 수정하거나 생성할 정확한 파일 경로를 포함한다.
- **[HUMAN]**: 사람 승인이나 다른 사람의 실행이 필요한 작업. 승인 없이 시작하지 않는다.
- 화면 시험 공통 기준(이하 "화면 공통 기준"): Edge·Chrome 또는 Playwright Chromium으로 1280px·1024px에서 가로 넘침 0, 콘솔 오류 0, 시나리오 ID·
  동작 버튼·"대상 존재" 열 줄바꿈 0(목업 1024px에서 "있음"이 두 줄로 갈라졌던 문제), 모든 DEMO 기록 화면에 `DEMO DATA` 띠.
- 웹은 판정을 만들지 않는다(FR-016). 판정·개수를 계산하는 코드가 템플릿·JS·read model에 생기면 그 작업은 실패로 본다.
- 작업 하나는 한 세션 안에 끝날 크기다. 더 커지면 같은 번호에 `a`/`b`를 붙여 나누고 이유를 `validation.md`에 남긴다.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 웹 패키지 뼈대, 합성 bundle fixture, 구현 기록 뼈대를 준비한다.

- [X] T001 Create the empty package `engine/web/__init__.py` and `engine/web/__main__.py` (prints usage only), and add `catalog/`, `engine/web/templates/`, `engine/web/static/` directories with a placeholder `README.md` each; record the starting regression count (`pytest -q`, `ruff check .`) in `specs/005-web-workbench-report/validation.md` [FR-032]
- [X] T002 [P] Create synthetic bundle builders for PASS, FAIL, INCONCLUSIVE (each reason code), RESTORE_FAILED, ABORTED, tampered (one file changed after seal), unreadable, a FAIL parent → PASS child → grandchild lineage with `retest-link.json`/`retest-diff.json`, and Spec 001- and Spec 002-format lineages, reusing `tests/fixtures/bundles/cases.json`, `tests/fixtures/spec003.py` and `tests/fixtures/spec004.py`, in `tests/fixtures/web_bundles.py` [FR-013~024, SC-002, SC-005]
- [X] T003 [P] Create implementation-time record templates (source SHAs, commands, scan reports, actual-validation Run IDs and manifest SHA-256, usability results) in `specs/005-web-workbench-report/validation.md` and `specs/005-web-workbench-report/implementation-decisions.md`; do not claim an unexecuted result [SC-011]

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 웹이 기대는 엔진 결함(원천 기준선 §2 위험 1·2·3·5)을 실패 시험부터 고친다(FR-035, research R-009~R-012). 위험 4는 이 Spec 밖이다(FR-037).

**⚠️ CRITICAL**: 사용자 스토리 작업은 T018까지 끝난 뒤 시작한다. T019(보성 PC 검사)와 T020(검사 v2 전환)은 사용자 스토리를 막지 않는다.

### Tests for Foundation — write first, confirm RED

- [X] T004 [P] Add unit tests for the path regex and output-boundary path policy: JSON-escaped `C:\\Users\\<name>`, single-separator Windows paths, `/home/<name>`, `/Users/<name>`, a path inside the run root → `<run_root>/…`, any other absolute path → `[PATH]`, and the human `show` text going through the same boundary, in `tests/unit/test_output_paths.py` [FR-031, FR-035, SC-007, R-009]
- [X] T005 [P] Add unit tests for `scan_bytes_strict` (v2: escaped separators, every absolute user path, existing v1 rules) and contract tests for `scripts/scan_bundles.py` (reads only, reports bundle ID, file relative path, rule, count; never values) in `tests/unit/test_scan_strict.py` and `tests/contract/test_scan_bundles_script.py` [FR-036, R-012]
- [X] T006 [P] Add contract tests for CLI output additions per `contracts/cli-output-additions.md`: `result_kind` on every `--json` output, `error_kind` values, JSON `USAGE` error on argument errors with exit code still 2, not-ready `run`/`retest` with `command="run"`/`"retest"` and `result_kind="READINESS"`, H-03 cleanup safety failure as `error_kind=CONTRACT` exit 1, `bundle_path` = `<run_root>/<run_id>`, `show`/`verify` honoring `--run-root` > `CONTROLPROOF_RUN_ROOT` > `.controlproof/runs`, all exit code values unchanged, in `tests/contract/test_cli_output_additions.py`; list in the task notes every existing expectation that changes (`tests/unit/test_redaction_security.py` line with `bundle_path`/`[USER_ROOT]`, and any match in `tests/contract/test_cli_preflight.py`, `test_cli_review.py`, `test_cli_retest.py`, `test_cli_n02.py`, `test_cli_spec004.py`) [FR-035, SC-010, R-004, R-009, R-010]
- [X] T007 [P] Add unit tests for `evidence_index`: `artifact:`, `file:`, `intrinsic:` and cross-run references resolve with relative path, SHA-256, size and MIME; `by_assertion` = assertion `artifact_ids` ∪ references of its `required_evidence_ids` from the sealed scenario snapshot; required but unresolved references listed as missing; `evidence_links` unchanged, using Spec 001~004 fixtures, in `tests/unit/test_evidence_index.py` [FR-014, FR-015, SC-003, R-011]
- [X] T008 [P] Add contract tests for verify by seal-time scanner: manifests without `redaction_profile` verify with v1, new seals write `controlproof.redaction.v2`, v2 findings on a v1 bundle appear only in non-blocking `strict_scan_findings` and never change `bundle_status`, the tracked parent `15cef078…` stays VERIFIED, in `tests/contract/test_verify_redaction_profile.py` [FR-036, R-012]

### Implementation for Foundation

- [X] T009 Fix `USER_PATH_RE` to accept one or more separators and JSON-escaped separators, and add the output-boundary path policy function in `engine/evidence.py` (after T004 RED) [FR-031, R-009]
- [X] T010 Apply the boundary in `engine/cli.py` `_emit` (JSON and human text, including `render_human` output) and set `bundle_path` to `<run_root>/<run_id>`; update the existing expectations listed in T006 notes [FR-035, R-009]
- [X] T011 [P] Add `scan_bytes_strict` (v2) beside the unchanged v1 scanner in `engine/evidence.py` (after T005 RED) [FR-036, R-012]
- [X] T012 Implement `scripts/scan_bundles.py` (`--run-root`, `--out`; per bundle v1 and v2 results and their difference; read only) (after T005 RED) [FR-036, R-012]
- [X] T013 Add `result_kind`/`error_kind`, JSON usage errors with exit code 2, not-ready `run`/`retest` `command` values and the H-03 cleanup JSON error in `engine/cli.py` (and the raising point in `engine/lifecycle.py` only if needed) (after T006 RED) [FR-035, R-010]
- [X] T014 Apply the run root rule to `show` and `verify` in `engine/cli.py` (after T006 RED) [FR-035, R-004]
- [X] T015 Implement `evidence_index` and add it to the review projection in `engine/presentation.py`, keeping `evidence_links` (after T007 RED) [FR-015, R-011]
- [X] T016 Run `scripts/scan_bundles.py` on this PC's real run root and on the tracked parent `15cef078…`, and record the summary (no values) in `specs/005-web-workbench-report/validation.md` before any scanner switch [FR-036, R-012]
- [X] T017 Implement verify by seal-time scanner and `strict_scan_findings` in `engine/evidence.py`, still sealing with v1 (switch happens in T020) (after T008 RED) [FR-036, R-012]
- [X] T018 Run the Foundation gate: full `pytest -q`, `ruff check .`, `git diff --check`; record RED→GREEN evidence for T004~T008 and changed expectations in `specs/005-web-workbench-report/validation.md` [FR-035]
- [ ] T019 [HUMAN] Waiting task: after T012 exists, ask 보성 to run `scripts/scan_bundles.py` on his PC (bundles are not moved) and record only the received report summary in `specs/005-web-workbench-report/validation.md` [FR-036, R-012]
- [ ] T020 Switch sealing to v2 and write `redaction_profile: controlproof.redaction.v2` in new manifests in `engine/evidence.py`, only after T016 and T019 are recorded; rerun T008 and the full regression [FR-036, R-012]

**Checkpoint**: 출력 경계·증적 색인·출력 구분 필드가 준비됐다. 사용자 스토리를 시작할 수 있다.

---

## Phase 3: User Story 1 - 12개 시나리오의 현재 상태를 한 화면에서 본다 (Priority: P1) 🎯 MVP

**Goal**: 워크벤치에서 12개 시나리오의 대상 존재·준비 상태(확인 시각)·실행 방식·최근 결과와 네 범주 개수를 범위표 그대로 보이고, 준비 상태 확인을
웹에서 시작한다.

**Independent Test**: 카탈로그와 합성(DEMO) 기록만으로 워크벤치를 열어 12개 상태가 범위표와 12/12 같고, 판정 불가가 reason code 배지로 나뉘며,
필터 결과가 5/0/4이고, A-01~A-03에 실행 요소가 없고, 준비 상태 확인이 저장·표시되는지 확인한다(화면 공통 기준 포함).

### Tests for User Story 1 — write first, confirm RED

- [X] T021 [P] [US1] Add catalog parity tests per `contracts/catalog.md` rules 1~6 (matrix §3 12/12 on id, question, treatment, owner spec; counts 5·4·3; fixed sentence equals matrix §2 quote; 7 profiles map to existing scenario files; every explanation has `source`; no legal article numbers in `policy_basis`; no WhyYou internal, fixture or bundle file names in plain text; every `records[].run_id` appears in its `validation_ref`) in `tests/unit/test_catalog_matrix_parity.py` [FR-003, FR-009, FR-019, SC-001]
- [X] T022 [P] [US1] Add unit tests for the badge table: exactly the 15 rows of spec "승인된 화면 구조와 상태 이름" with label, standard name, icon, shape (`round`·`square`·`filled`) and description, in `tests/unit/test_web_badges.py` [FR-005, SC-006, R-016]
- [X] T023 [P] [US1] Add unit tests for the workbench read model: counts copied from catalog statuses with `INCONCLUSIVE.total` = sum of `by_reason`; groups by control; `readiness.differs_from_common` only for rows checked at another time; `mismatch` when a real-root official bundle verdict differs from the catalog; ACTUAL and DEMO never in one view; no PASS badge on `NOT_RUN`/`NO_TEST_TARGET`/`INCONCLUSIVE` rows; an executed scenario without its official bundle on this PC shows "이 화면에 기록 없음" and the Validation location, never `NOT_RUN`; a file changed after a cached verify is re-verified and shown as an integrity failure, in `tests/unit/test_web_readmodel_workbench.py` [FR-001~007, FR-030, SC-001, SC-011, R-005, R-006]
- [X] T024 [P] [US1] Add unit tests for the web preflight runner: subprocess command built from catalog profiles only, 120-second timeout → `result_kind=ERROR`, `error_kind=UNEXPECTED`; `USAGE` stored as a tool error not a readiness value; `checked_at` from payload; latest file and `history.jsonl` written under `.controlproof/web/preflight/`; a second concurrent request rejected; exit code stored but not interpreted, in `tests/unit/test_web_preflight.py` [FR-011, FR-012, SC-010, R-007]
- [X] T025 [P] [US1] Add HTTP contract tests per `contracts/web-http.md`: bind address fixed to `127.0.0.1`, foreign `Host` → 421, POST without token → 403, security headers, `/api/workbench` schema per `contracts/web-read-model.md`, route table contains no Run/retest/cleanup start route, concurrent preflight POST → 409, in `tests/contract/test_web_http.py` [FR-012, FR-031, SC-010, R-002]
- [X] T026 [P] [US1] Add browser tests for the workbench at 1280px and 1024px (화면 공통 기준; filters 5/0/4; neutral INCONCLUSIVE card with `?` INSUFFICIENT_EVIDENCE 1 and `∅` NO_TEST_TARGET 3 matching the table badges; one common checked-at above the table; A-01~A-03 rows without run buttons or progress; `RUNNER_NOT_READY` vs `NO_TEST_TARGET` badges differ in name, icon and shape) in `tests/web/test_workbench_screen.py` [FR-001~007, SC-001, SC-006]

### Implementation for User Story 1

- [X] T027 [US1] Create `catalog/mvp-scenarios.yaml` with the 12 entries per `contracts/catalog.md` (`mvp_treatment` one of `EXECUTED`·`NOT_RUN`·`NO_TEST_TARGET`; `NO_TEST_TARGET` entries `target_exists: false`, `profiles: []`, `official_status: {result: INCONCLUSIVE, reason_code: NO_TEST_TARGET}`; official records from Spec 001~004 Validation; every explanation with `source`; policy basis without legal articles) (after T021 RED) [FR-001~003, FR-009, FR-010, R-005]
- [X] T028 [P] [US1] Implement the badge table in `engine/web/badges.py` (after T022 RED) [FR-005, R-016]
- [X] T029 [US1] Implement the catalog loader, verify cache keyed by manifest `bundle_digest` plus every bundle file's (relative path, size, modification time) so any post-seal change forces re-verify, and the workbench view in `engine/web/readmodel.py` (after T023 RED) [FR-001~007, R-003, R-005, R-006]
- [X] T030 [US1] Implement the preflight runner in `engine/web/preflight.py` (after T024 RED) [FR-011, FR-012, R-007]
- [X] T031 [US1] Implement the server (`127.0.0.1` only, Host check, CSRF token, security headers, `/`, `/api/workbench`, `POST /preflight`, `/static/*`, `/demo/` prefix) and run-root/demo-root arguments in `engine/web/server.py` and `engine/web/__main__.py` (after T025 RED) [FR-012, FR-030, FR-031, R-002, R-004]
- [X] T032 [US1] Create `engine/web/templates/base.html` (DEMO band, header with `LOCAL_EMULATED`·AWS `NOT_RUN`·claim scope, four tabs) and `engine/web/templates/workbench.html`, plus `engine/web/static/workbench.css` (1280px base, `min-width: 1024px`, `white-space: nowrap` on ID, buttons and "대상 존재") and `engine/web/static/workbench.js` (filters, copy, form submit only) (after T026 RED) [FR-001~007, A-10]
- [X] T033 [P] [US1] Implement `scripts/prepare_web_demo.py` writing synthetic bundles from `tests/fixtures/web_bundles.py` to a DEMO root [FR-030, SC-011]
- [X] T034 [US1] Run the US1 gate (T021~T026 GREEN, full regression, ruff) and record it in `specs/005-web-workbench-report/validation.md` [SC-001, SC-006, SC-010]

**Checkpoint**: 워크벤치만으로 12개 상태와 준비 상태를 오해 없이 전달한다.

---

## Phase 4: User Story 2 - 실행 결과에서 판정 근거를 원본 증적까지 추적한다 (Priority: P1)

**Goal**: 결과 화면에서 무결성 확인 뒤 봉인 판정·assertion별 기대·관찰·증적(SHA-256)·복구를 보이고, 실패 규칙만 보기와 수정 메모를 제공한다.

**Independent Test**: 합성 PASS·FAIL·INCONCLUSIVE·RESTORE_FAILED·변조·읽기 실패 기록을 열어 화면 판정이 `verify`+`show`와 100% 같고, 변조·읽기 실패는
판정 없이 무결성 실패로 보이며, 모든 PASS·FAIL assertion에서 SHA-256 있는 증적에 닿는지 확인한다(화면 공통 기준 포함).

### Tests for User Story 2 — write first, confirm RED

- [X] T035 [P] [US2] Add unit tests for the run view: integrity first (`VERIFIED`·`INVALID`·`UNREADABLE`; non-VERIFIED → `verdict`/`assertions`/`evidence` null); verdict, assertion status and reason code copied verbatim; `RESTORE_FAILED` safety badge before the verdict; `ABORTED` shown as run state, never as a target verdict; restore seconds, deadline and within-deadline flag shown; `plain_meaning` without WhyYou internal, fixture or bundle file names; `record_origin`/`record_role`, in `tests/unit/test_web_readmodel_run.py` [FR-013~020, SC-002, R-003]
  - 노트(ID-005-01 결정, 2026-10-09): 무결성 시험 경우 3개를 넣는다. ① `ABORTED` + 필수 증적 링크 누락만 → "봉인 무결성 확인됨 +
    중단으로 빠진 증적 목록", `ABORTED` 상태를 먼저 표시 ② `COMPLETED` + 증적 링크 누락 → 무결성 실패 ③ 해시 불일치 → 무결성 실패.
    명령줄 `verify` 결과는 그대로다.
- [X] T036 [P] [US2] Add unit tests for the evidence viewer (text only, ≤256 KB, strict scan must pass, otherwise a reason; integrity-failed run → 422) and fix memos (`controlproof.fix-memo.v1`, author 1~80 chars, text 1~2000 chars, append only, strict scan before write, stored under `.controlproof/web/memos/`, bundle files and verify result unchanged), in `tests/unit/test_web_evidence_view.py` and `tests/unit/test_web_memos.py` [FR-015, FR-024, FR-031, R-008, R-009]
- [X] T037 [P] [US2] Add browser tests for the run screen at 1280px and 1024px (화면 공통 기준; plain explanation by default and developer details collapsed; failed-only toggle leaves only FAIL/INCONCLUSIVE rows; memo form labelled as separate from the sealed record; integrity-failure and restore-failure badges distinct from FAIL; click count workbench → result → evidence ≤3) in `tests/web/test_run_screen.py` [FR-013~020, SC-002, SC-003]

### Implementation for User Story 2

- [X] T038 [US2] Implement the run view in `engine/web/readmodel.py` using `verify_bundle`, `load_bundle_summary` and `evidence_index` (after T035 RED) [FR-013~019, R-003, R-011]
- [X] T039 [P] [US2] Implement fix memos in `engine/web/memos.py` (after T036 RED) [FR-024, R-008]
- [X] T040 [US2] Add routes `/runs/{run_id}`, `/runs/{run_id}/evidence`, `POST /runs/{run_id}/memos`, `/api/runs/{run_id}` in `engine/web/server.py` (after T036 RED) [FR-015, FR-024]
- [X] T041 [US2] Create `engine/web/templates/run.html` per the approved screen ③ (after T037 RED) [FR-013~020]
- [X] T042 [US2] Run the US2 gate and record it in `specs/005-web-workbench-report/validation.md` [SC-002, SC-003]

**Checkpoint**: 판정에서 원본 증적까지 끊김 없이 추적된다.

---

## Phase 5: User Story 3 - 검증 범위와 한계를 하나의 화면 보고서로 확인한다 (Priority: P1)

**Goal**: 한 화면 보고서에 V4 §8.7 13개(R1~R13)와 §12.4 9개(C1~C9) 항목, 범위표 고정 문구, AI 점수 참고 원칙, 실행 한계를 보인다.

**Independent Test**: 카탈로그와 합성 기록만으로 보고서를 열어 22/22 항목 표지가 있고 고정 문구가 범위표와 같은 글자이며 "12개 검증 완료"류 표현이 없는지
확인한다(화면 공통 기준 포함).

### Tests for User Story 3 — write first, confirm RED

- [X] T043 [P] [US3] Add unit tests for the report view: `items_present` R1~R13 and C1~C9 all true; `fixed_scope_sentence` equal to the matrix §2 quote; counts copied from catalog; AI-score principle and human-decision location; `test_only_additions`; `LOCAL_EMULATED`, AWS `NOT_RUN`, synthetic data, fixed model (name only in developer details), other-PC reproduction status, legal non-certification; forbidden phrases ("12개 검증 완료", "12개 PASS") absent, in `tests/unit/test_web_readmodel_report.py` [FR-025~029, SC-004]
- [X] T044 [P] [US3] Add browser tests for the report at 1280px and 1024px (화면 공통 기준; 22 item markers visible; DEMO report never mixes into ACTUAL counts) in `tests/web/test_report_screen.py` [FR-025~029, SC-004, SC-011]

### Implementation for User Story 3

- [X] T045 [US3] Implement the report view in `engine/web/readmodel.py` (after T043 RED) [FR-025~029]
- [X] T046 [US3] Add `/report`, `/api/report` routes in `engine/web/server.py` and create `engine/web/templates/report.html` per the approved screen ④ report part (after T044 RED) [FR-025~029]
- [X] T047 [US3] Run the US3 gate and record it in `specs/005-web-workbench-report/validation.md` [SC-004]

**Checkpoint**: 비개발자가 한 화면에서 범위와 한계를 읽는다.

---

## Phase 6: User Story 4 - 시나리오를 이해하고 실행 조건을 확인한다 (Priority: P2)

**Goal**: 시나리오 상세에서 정의·설명·준비 상태·실행 안내(복사 가능한 명령과 전제)를 보이고, `NOT_RUN`·`NO_TEST_TARGET` 상세에는 실행 요소를 두지 않는다.

**Independent Test**: 실행 프로필 7개와 미실행·대상 없음 7개 상세를 열어 정의가 원천과 같고 프로필이 구분되며 실행 요소 유무가 맞는지 확인한다(화면 공통 기준 포함).

### Tests for User Story 4 — write first, confirm RED

- [X] T048 [P] [US4] Add unit tests for the scenario view: definition from the sealed snapshot when a Run exists, else from `scenarios/*.yaml`; H-03 and E-03 split by profile; `NOT_RUN`/`NO_TEST_TARGET` with `profiles: []` and no command fields; legal mapping notice present; run/retest commands built only from catalog templates; readiness with checked-at, in `tests/unit/test_web_readmodel_scenario.py` [FR-008~012]
- [X] T049 [P] [US4] Add browser tests for scenario details at 1280px and 1024px (화면 공통 기준; E-01 shows the four preconditions and copyable command, no run button; H-01 and A-01 show no run button, progress or pass mark; "준비 상태 확인" from the detail stores a new checked-at; a usage error is shown as "확인 도구 오류", not as a readiness badge) in `tests/web/test_scenario_screen.py` [FR-008~012, SC-010]

### Implementation for User Story 4

- [X] T050 [US4] Implement the scenario view in `engine/web/readmodel.py` (after T048 RED) [FR-008~012]
- [X] T051 [US4] Add `/scenarios/{id}`, `/api/scenarios/{id}` routes in `engine/web/server.py` and create `engine/web/templates/scenario.html` per the approved screen ② (after T049 RED) [FR-008~012]
- [X] T052 [US4] Run the US4 gate and record it in `specs/005-web-workbench-report/validation.md` [SC-010]

---

## Phase 7: User Story 5 - 최초 FAIL과 재시험을 비교한다 (Priority: P2)

**Goal**: 부모·자식(·손자) 계보를 나란히 보이고 부모 불변 확인, 바뀐 차원, assertion별 이전·이후를 보인다.

**Independent Test**: 합성 FAIL 부모 → PASS child → grandchild 계보와 부모를 바꾼 계보로 비교를 열어 부모 판정 불변·변화가 보이고, 부모가 바뀐 계보는 계보 문제로
보이는지 확인한다(화면 공통 기준 포함).

### Tests for User Story 5 — write first, confirm RED

- [X] T053 [P] [US5] Add unit tests for the compare view: `parent_unchanged` from `retest-link.json` `parent_bundle_digest` vs current parent `bundle_digest`; `changed_dimensions` verbatim; assertion before/after with evidence; `lineage_problem` when the parent is not VERIFIED or digests differ; `parent_integrity_source` = `RETEST_LINK` (Spec 003·004), `CROSS_RUN_REFERENCE` (Spec 002) or `NONE_LEGACY` (Spec 001, `parent_unchanged: null`, parent's own integrity shown, not a lineage problem), in `tests/unit/test_web_readmodel_compare.py` [FR-021~023, SC-005]
- [X] T054 [P] [US5] Add browser tests for the compare screen at 1280px and 1024px (화면 공통 기준; two different run IDs side by side; parent verdict unchanged; retest shown only as a command) in `tests/web/test_compare_screen.py` [FR-021~023, SC-005]

### Implementation for User Story 5

- [X] T055 [US5] Implement the compare view in `engine/web/readmodel.py` (after T053 RED) [FR-021~023]
- [X] T056 [US5] Add `/compare/{child_run_id}`, `/api/compare/{child_run_id}` routes in `engine/web/server.py` and create `engine/web/templates/compare.html` per the approved screen ④ compare part (after T054 RED) [FR-021~023]
- [X] T057 [US5] Run the US5 gate and record it in `specs/005-web-workbench-report/validation.md` [SC-005]


### 결과 화면 가독성 보정 (2026-10-09 추가, 사용성 검토 전, ID-005-09)

- [X] T057a [US2] Aborted Run integrity wording: never show "VERIFIED" for the ID-005-01 exception; show "봉인 무결성 확인됨(봉인 파일·manifest 일치) · 명령줄 verify: INVALID(중단으로 빠진 필수 증적 …)" in the lead and the info table, keeping the ID-005-01 decision, in `engine/web/readmodel.py` and `engine/web/templates/run.html` (test first in `tests/unit/test_web_run_readability.py` and `tests/web/test_run_readability_screen.py`) [FR-017, FR-019]
- [X] T057b [US2] Step progress in plain words: per phase (기준선·주입·복구) the step count, applied/released test conditions in Korean and the restore result; step IDs move to developer details [FR-018, FR-019]
- [X] T057c [US2] Distinguishable evidence names: evidence requirement label (EV-xx short Korean label from the catalog), record kind and collection phase; the per-rule evidence cell groups equal names with a count so no name repeats [FR-015, FR-019]
- [X] T057d [US2] Korean labels for known unverified-scope items (raw text in developer details) and the header target version as a short WhyYou commit when recorded (snapshot hash in developer details) [FR-019, FR-013]

---

## Phase 8: Polish & Cross-Cutting (자동 gate)

- [X] T058 [P] Add an integration test that requests every route (HTML and JSON, ACTUAL and DEMO, all synthetic bundle kinds) and scans every response with `scan_bytes_strict`: 0 violations including escaped Windows paths, in `tests/integration/test_web_response_redaction.py` [FR-031, SC-007]
- [X] T059 [P] Add an integration test that the workbench and run screens render within 2 seconds with 30 synthetic bundles (verify cache warm) in `tests/integration/test_web_performance.py` [A-8]
- [X] T060 Run quickstart §3·§4 on a clean checkout (no personal absolute paths), fix any documentation gap in `specs/005-web-workbench-report/quickstart.md`, and record the full automatic gate in `specs/005-web-workbench-report/validation.md` [SC-007, SC-011]

---

## Phase 9: Actual Validation (웹 PC 재실행, 사람 승인 필요)

**Purpose**: quickstart §5. 공식 Run이 아니라 Spec 005 웹 검증 기록이다(D-018 추가 결정 3). 매 Run 전 두 저장소 branch·HEAD·dirty 기록과 preflight
`READY` 확인, 사람 승인. 매 Run 뒤 `show`·`verify`, Run ID와 manifest SHA-256 기록.

- [ ] T061 [HUMAN] Confirm the Spec 004 retest maintenance-path fix (FR-037, research R-013) is merged on `origin/yeonwoo/004-e01-e02-score-evidence`, merge it into `005-web-workbench-report` (stop on conflict), and record the commit in `specs/005-web-workbench-report/validation.md`; not merged as of 2026-10-08 [FR-037]
- [ ] T062 [HUMAN] Record both repositories' branch, HEAD and dirty state, start WhyYou `374b122` with fixture `h03-report-v1`, and record preflight for all five `h03-report-v1` profiles in `specs/005-web-workbench-report/validation.md` [FR-030, SC-011]
- [ ] T063 [HUMAN] Run H-03 `H03_DLQ_V2` once at `374b122` first; record it also as the independent reproduction gate record "현재 통합 대상(`374b122`) 기준" with the note that playbook §6 named a different commit; if it differs from the official status, classify the cause before anything else: seed/runner defect → failing test first, then fix and rerun; target-version problem → stop and ask 보성 whether to use `511ae9e`, in `specs/005-web-workbench-report/validation.md` [FR-030, R-015]
- [ ] T064 [HUMAN] Run H-03 `H03_MINIMAL_V1`, E-03 `E03_BEFORE_V2`, E-03 `E03_AFTER_V2` at `374b122` (each with state record and preflight first) and record them in `specs/005-web-workbench-report/validation.md` [FR-030]
- [ ] T065 [HUMAN] Run N-02 `N02_CONSENT_ORDER_V1` at `374b122` and record it as a web-validation record whose official status stays with Spec 003 converge, in `specs/005-web-workbench-report/validation.md` [FR-030]
- [ ] T066 [HUMAN] Switch both `.env` files to fixture `spec004-report-v1`, restart API and workers, run E-02 `E02_SCORING_FREEZE_V1` at `374b122`, and record it in `specs/005-web-workbench-report/validation.md` [FR-030]
- [ ] T067 [HUMAN] Run the E-01 parent at WhyYou `ce8d862` in a separate checkout (FAIL expected; seal only, no fix) and record it in `specs/005-web-workbench-report/validation.md` [FR-030, SC-005]
- [ ] T068 [HUMAN] Run the E-01 retest at `374b122` with `retest <parent Run ID>` in the same run root, then restore fixtures and stop processes, and record it in `specs/005-web-workbench-report/validation.md` [FR-030, SC-005]
- [ ] T069 [HUMAN] Start the web on the real run root and check SC-001~SC-007, SC-010, SC-011 on these records (screens, `/api/*` vs `show`/`verify`, response scan), and record the results in `specs/005-web-workbench-report/validation.md` [SC-001~007, SC-010, SC-011]

---

## Phase 10: User Story 6 - 역할별 이해도와 사용성을 실제 웹 화면으로 검토한다 (Priority: P3)

**Goal**: 태오 진행으로 비작성자 6명(세 역할 각 2명)이 실제 기록으로 연 웹에서 과업 3개와 질문 7개를 수행하고 SC-008·SC-009로 판정한다.

**Independent Test**: 검토 기록만으로 표본·과업·시간·정답·치명적 오독 기준 충족 여부를 판단할 수 있다.

- [ ] T070 [P] [US6] Prepare the review kit (participant brief, 3 tasks, 7 questions from Product Brief §10.3, 3-minute timer rule, answer key, critical-misreading list, anonymous record sheet) in `specs/005-web-workbench-report/usability/review-kit.md` [FR-034, SC-008, SC-009]
- [ ] T071 [HUMAN] [US6] 태오 conducts the review with 6 non-authors on the T069 records and fills `specs/005-web-workbench-report/usability/results.md` (no personal identifiers) [FR-034, SC-008, SC-009]
- [ ] T072 [US6] Judge SC-008 (each question ≥5 of 6 correct within 3 minutes, critical misreadings 0) and SC-009 (≥5 of 6 on the unverified-scope question); if failed, record the screen fixes as new tasks before converge, in `specs/005-web-workbench-report/validation.md` [SC-008, SC-009]

---

## Phase 11: Converge (문서 수렴)

- [ ] T073 Create `specs/005-web-workbench-report/traceability.md` mapping FR-001~FR-037 and SC-001~SC-011 to tests, Run IDs and evidence [SC-001~011]
- [ ] T074 Close `specs/005-web-workbench-report/validation.md` with the final gate, actual-validation records, usability result and remaining limits (AWS `NOT_RUN`, other-PC reproduction status) [SC-011]
- [ ] T075 Synchronize status documents in one change: `README.md`, `AGENTS.md`, `docs/TEAM_HANDOFF.md`, `docs/product/ControlProof_MVP_Scenario_Coverage_Matrix.md`, `docs/product/ControlProof_MVP_Product_Brief.md` §14.6 (and Decision Log only if a decision changed) [FR-003]
- [ ] T076 Run `$speckit-converge` and fix every cross-document status mismatch in `specs/005-web-workbench-report/` [SC-001~011]

---

## Dependencies & Execution Order

- Setup(T001~T003) → Foundational(T004~T018) → US1(T021~T034) → US2·US3·US4·US5(각각 US1 뒤, 서로 독립; 같은 `readmodel.py`·`server.py`를 고치므로 같은
  파일 작업은 순서대로) → Polish(T058~T060) → Actual Validation(T061~T069, 사람 승인) → US6(T070~T072) → Converge(T073~T076).
- T019(보성 PC 검사, 대기)와 T020(검사 v2 전환)은 T012·T016 뒤이며 사용자 스토리를 막지 않는다. T020은 T069 전에 끝나야 한다(실제 기록이 v2로 봉인되도록).
- T061(위험 4 병합 확인)은 T062보다 먼저다.
- US6(T071)은 T069의 실제 기록이 있어야 한다. T070은 언제든 준비할 수 있다.

### Parallel Opportunities

- Foundation 시험 T004~T008은 서로 다른 파일이라 병렬. 구현 T011·T012는 T009·T010과 병렬.
- US1 시험 T021~T026 병렬, 구현 T028·T033 병렬.
- US2~US5의 시험 작업([P])은 US1 뒤 서로 병렬로 쓸 수 있다.

## Implementation Strategy

1. **MVP**: Setup → Foundational → US1. 이것만으로 12개 상태와 준비 상태를 사실대로 보여 줄 수 있다.
2. US2(증적 추적) → US3(보고서): P1 완성.
3. US4·US5: P2.
4. Polish → Actual Validation(사람 승인) → US6 사용성 검토 → Converge.

## Notes

- 대기 작업: T019(보성 PC 검사, 스크립트 T012 뒤), T061(위험 4 병합, 2026-10-08 미병합), T071(태오 사용성 검토).
- 첫 구현 작업은 T009(T004 RED 확인 뒤)다.

## Analysis (`$speckit-analyze`, 2026-10-08)

- Coverage: FR 37/37, SC 11/11 have ≥1 task; 76 tasks, sequential IDs, every task traced; no placeholders.
- Fixed in Spec 005 documents (no product meaning change):
  - HIGH H1 — verify cache keyed only by manifest digest could miss a file changed after seal (FR-017). Key now includes every bundle
    file's relative path, size and modification time (plan, research R-003, T023, T029).
  - HIGH H2 — FR-023 required a parent integrity value that Spec 001-format retest links never recorded. Defined the source per format
    (`RETEST_LINK`, `CROSS_RUN_REFERENCE`, `NONE_LEGACY`); legacy shows the parent's own integrity and "부모 불변 값 기록 없음(이전 형식)",
    not a lineage problem (spec FR-023 and edge case, data model §6, web read model, T002, T053).
  - MEDIUM M1 — `ABORTED` runs had no display rule; FR-018 now forbids showing them as a target verdict (Constitution II; T002, T035).
  - MEDIUM M2 — FR-012/SC-010 "웹에서 시작하는 동작은 준비 상태 확인뿐" conflicted with memo writes; scoped to execution actions.
  - MEDIUM M3 — edge case "executed scenario without a local bundle → 이 화면에 기록 없음, not NOT_RUN" had no test (T023).
  - MEDIUM M4 — FR-018 restore-budget display had no test (T035).
- Remaining: CRITICAL 0, HIGH 0, MEDIUM 0. LOW 1 — FR-001 "적용 정책·평가기준 버전(기록이 있는 경우)" is shown in the report (R9) but not
  yet named in the workbench view contract; resolve during T029 by adding it to the workbench header when a record carries it.
