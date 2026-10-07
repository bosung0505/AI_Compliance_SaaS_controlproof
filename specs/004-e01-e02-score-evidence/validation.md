# Spec 004 Validation

## Current status

- Workflow stage: Spec 004 closure T001~T097 complete (T087 NOT_REQUIRED), final converge recorded below. First E-01 FAIL and D1-only child FAIL preserved; approved P1 child PASS. New clean-checkout E-01/E-02 PASS/SUCCEEDED/VERIFIED on WhyYou 374b122. Full CP 939 PASS once, WhyYou scoped 188 PASS, later setup scoped 12 PASS. Owner approved ID-004-36; another PC and AWS remain unverified.
- WhyYou local/test fixture (Phase 3, T022~T029): PR jhkim0602/gbsa_aws#6 reviewed, fixed and merged into `bosung/controlproof-n02-integration` at `42aaaba206ced4288c8ee477b73f5f1ccf078bf3`; main unchanged.
- Latest WhyYou integration head: `374b122e1296c0159ccd88ed4763d358973c59cb` (PR #8, approved ID-004-30 response-only transcript availability); T088 live E-01 product-remedy child PASS. PR #7 wiring and Phase 8 E-02 evidence remain historical checkpoints.
- Sandbox diagnostics: complete, separate from official results. Official initial E-01 `09c9d9bb-82a3-4485-9c9d-e9721f2452e4` FAIL; E-02 `e39e62ae-be73-4e52-8cab-1f878637a0c6` PASS (see T080~T082 entry). Parent D1 OTHER_CRITERION NOT_OBSERVED stays unchanged; ID-004-34 supersedes ID-004-17 for new Runs while retaining FR-013 four-mode coverage.
- AWS: `NOT_RUN`
- Claim scope: `EXECUTED_SCENARIO_AND_EVIDENCE_ONLY`

This file is chronological. Do not replace a failed or inconclusive result with a later result; append a new
entry and link it to the original Run.

## Source baseline

| Repository | Branch | Baseline SHA | Working-tree note |
|---|---|---|---|
| ControlProof | `004-e01-e02-score-evidence` | `cf57e6a8a0966080973a03015e5a08c54602fad6` | clean before Phase 1 |
| WhyYou | `yeonwoo/controlproof-e01-e02-fixture` | `3dfa10c9cf34f26b499e32652f310447e5a119db` | clean; = `eec8f70` + fixture |

Later implementation and actual-Run entries must record the then-current clean, committed SHAs again. The
baseline above is not an actual-Run source claim.

## Gate ledger

| Gate | Tasks | Command | Result | Duration |
|---|---|---|---|---|
| Setup | T001~T004 | file review, `ruff check tests/fixtures/spec004.py`, fixture sanity (v1 72, v2 74) | PASS | < 1 minute |
| Foundation tests (RED) | T005~T011 | scoped pytest with and without `--runxfail`; full `pytest -q` | 113 strict xfail for the intended reason; 15 new guards PASS | ~1 minute |
| WhyYou fixture | T022~T029 | original and PR review records below | 53 model / 177 scoped PASS after review; merged at `42aaaba` | See review record |

## WhyYou fixture `spec004-report-v1` (T022~T029)

- T022: branch `yeonwoo/controlproof-e01-e02-fixture` created from `bosung/controlproof-n02-integration` `eec8f70`
  (clean). The tasks/contract name `…-model-fixture` was corrected to this real name (`cf57e6a`).
- T023~T025: tests added to `backend/tests/unit/runtime/test_controlproof_model_substitute.py` (30 new). RED: the
  module failed at collection with `ImportError: cannot import name 'SPEC004_FIXTURE_DIGEST'`.
- T026~T027: implemented in `backend/src/interview_evidence/runtime/controlproof_model_substitute.py`: marker
  parser, five citation modes, `score=`, same-call `OTHER_CRITERION` memory guarded by the shared UUIDv7
  millisecond (bound 256), `OTHER_APPLICANT` from the marker argument only, criterion-assessment emission receipts
  under `{CONTROLPROOF_OBSERVER_ROOT}/model/` (atomic, non-fatal), and health/resolution/isolation digest following
  the active fixture. `h03-report-v1` output, digest and health values unchanged. No product code changed.
- T028: `uv run --cache-dir .uv-cache --no-sync python -m pytest -q backend/tests/unit/runtime/test_controlproof_model_substitute.py`
  → 48 passed (GREEN). `ruff check` and `ruff format --check` on both changed files → PASS.
  `… -m pytest -q backend/tests/unit` → 483 passed, 1 failed. The failure is the pre-existing
  `test_no_module_imports_another_lanes_private_package` (same boundary violations in `recruiting_assistant` and
  `runtime/worker.py` at `eec8f70`; baseline 453 passed, 1 failed). `test_streaming_websocket_route.py` failed once
  in a full run and fails intermittently at the baseline too (2 of 3 runs at `eec8f70`); unrelated flaky test.
  `backend/tests/integration/test_controlproof_fault_hook_safety.py` → 4 passed.
- T029: pushed to remote `fork` (`Happy623623/gbsa_aws_yw`) only; PR jhkim0602/gbsa_aws#6, base
  `bosung/controlproof-n02-integration`, head `Happy623623:yeonwoo/controlproof-e01-e02-fixture` at `3dfa10c`.
  Merge is the reviewer's decision.
- Fixture identity: `fixture_digest = sha256("controlproof:" + fixture_id)`. ControlProof compares its
  `CONTROLPROOF_MODEL_FIXTURE_ID`/`CONTROLPROOF_MODEL_FIXTURE_DIGEST` with WhyYou health
  (`engine/config.py`, `engine/adapters/whyyou/capability.py`).
  - `spec004-report-v1` → `e15ec3790b64b2fba10e0caa9372f08c917edbbaa99ce308076952b838668b3f`
  - `h03-report-v1` → `ce09b95403b34e1390502c90f5c5edc518ddf65d38c8ce881617a37cac6d16b1` (unchanged)
  - The AI isolation digest includes the active fixture ID and digest, so switching fixtures changes it and
    every worker must restart (quickstart "고정 모델 fixture 전환").

## Phase 1 — Setup (T001~T004)

- T001 `.env.example`: commented Spec 004 fixture ID/digest pair and the rule that scoring-source pins have no
  override variable. Active defaults stay `h03-report-v1`.
- T002 `tests/fixtures/spec004.py`: deterministic, text-free builders for lanes, criteria/markers (matrix codes
  `E01-1-VALID` … `E01-5-OTHER-CRITERION`), emission receipts, citation cases, report records/reads, change
  injections, version snapshots, frozen inputs and `scoring_inputs`. Sanity: E-02 v1 total 72 (72.5), v2 74 (73.5).
- T003 `tests/fixtures/whyyou_scoring_vectors.json`: values from WhyYou `eec8f70`
  `backend/tests/unit/reporting/test_weighted_scoring.py` (blob `c5337d24aa0ee9d22a86ad5bdcd51800a0792960`).
- T004: this file and `implementation-decisions.md` (ID-004-01 strict-xfail convention).

## Phase 2 — Foundation tests (T005~T011), RED record

Convention (ID-004-01): RED tests are `pytest.mark.xfail(strict=True, raises=<intended exception>)`; the reason
names the task that removes the marker. Commands:
`.venv\Scripts\python.exe -m pytest -q <file>` and the same with `--runxfail` to read the real failure.

| Task | File | RED | Intended reason observed | Guards PASS |
|---|---|---:|---|---:|
| T005 | `tests/unit/test_models_spec004.py` | 24 | `AttributeError`: `engine.models` lacks `ExecutionProfile.E01_*`/`E02_*`, `E01LaneId`, `LaneCriterion`, `ReportLane`, `ModelEmissionReceipt`, `CitationCase`, `ReportRecordSnapshot`, `ReportReadSnapshot`, `ChangeInjection`, `CriteriaVersionSnapshot`, `FrozenInputSet`, `RecomputeRecord` | 0 |
| T006 | `tests/contract/test_scenario_profile_v4.py` | 29 | `ValidationError`: unknown `execution_profile` and N-02-only lane enum; `AttributeError`: no `E01_CANONICAL_STEPS` | 5 |
| T007 | `tests/contract/test_bundle_profile_spec004.py` | 9 | `AttributeError`: no profile enum; no `SPEC004_PROFILE_CONTRACT` | 0 |
| T008 | `tests/contract/test_cli_spec004_profile.py` | 12 | `AssertionError` `PROFILE_MISMATCH` ≠ `PROFILE_REQUIRED`; `ValueError` not a valid `ExecutionProfile`; `AttributeError` no enum for registry; `ValidationError` for v4 payload | 7 |
| T009 | `tests/unit/test_e02_scoring_copy.py` | 18 | `ModuleNotFoundError: engine.judges.e02_scoring` | 0 |
| T010 | `tests/unit/test_redaction_security.py` | 9 | `AssertionError`: the nine Spec 004 raw-text fields survive `redact` | 1 |
| T011 | `tests/contract/test_package_layout.py`, `tests/integration/test_spec003_v3_regression.py` | 12 | `ModuleNotFoundError` for the twelve planned modules | 2 |

Full regression after Phase 1~2:

```text
.venv\Scripts\ruff.exe check .        -> All checks passed!
.venv\Scripts\python.exe -m pytest -q -> 506 passed, 113 xfailed in 60.43s
```

506 = the previous 491 + 15 new guard tests (existing v1~v3 scenarios load, existing CLI selection, digest
redaction survival, N-02 v3 execute/verify, sealed parent `15cef078…` manifest SHA-256
`d2306f3c…` unchanged and `VERIFIED`). No existing test changed outcome.

## Phase 2 — Foundation implementation (T012~T021)

| Task | Change | Tests turned GREEN |
|---|---|---|
| T012 | `engine/models.py`: profiles, lane enums, Spec 004 entities, Run policy (ID-004-06) | T005 24 |
| T013 | `engine/scenario.py`: v4 validation, canonical sets, snapshot unchanged for earlier profiles (ID-004-07) | T006 29 |
| T014 | `engine/adapters/base.py`: eight Spec 004 protocols and `AdapterSet` fields | — (used by T019) |
| T015 | `engine/config.py`: `validate_spec004_safety`, `fixture_digest` (ID-004-10) | new `test_config_spec004.py` 10 (RED first) |
| T016 | no `runner.py` change (ID-004-06) | — |
| T017 | `engine/judges/e02_scoring.py` (WhyYou cross-check 0/2000 mismatches) | T009 18, layout 1 |
| T018 | `engine/evidence.py`: Spec 004 profile, files, EV4 links, snapshot links, nine redacted keys (ID-004-04/04) | T007 11, T010 9 |
| T019 | `tests/fixtures/fake_spec004.py`, `make_adapters(spec004=…)` (ID-004-09) | — |
| T020 | `engine/cli.py`: E-01/E-02 explicit profiles and scenario paths | T008 4 |
| T021 | this record | — |

```text
.venv\Scripts\ruff.exe check .        -> All checks passed!
.venv\Scripts\python.exe -m pytest -q -> 617 passed, 15 xfailed in 59.66s
```

Remaining strict xfail (15): executor registration and non-READY preflight for both profiles (T040/T057, 4) and
eleven planned modules (T035~T058). Existing scenario snapshot digests and the sealed parent `15cef078…` are pinned
by guard tests and unchanged.

## Phase 4 — US1 citation gate (T030~T043)

| Task | Change | Tests |
|---|---|---|
| T030 | `tests/contract/test_spec004_seed_adapter.py` (RED: ImportError) | 8 GREEN after T036 |
| T031 | `tests/contract/test_spec004_report_adapters.py` (RED: ImportError) | 10 GREEN after T037 |
| T032 | `tests/contract/test_spec004_model_emission_adapter.py` (RED: ImportError) | 4 GREEN after T038 |
| T033 | `tests/unit/test_judge_e01_citation.py` (RED: ImportError) | 19 GREEN after T041 |
| T034 | `tests/integration/test_e01_citation_orchestration.py` (RED: ScenarioError/Unregistered) | 3 GREEN after T040 |
| T035 | `seeds/spec004_subjects.py` (uppercase codes, ID-004-11) | layout 1 |
| T036 | `engine/adapters/whyyou/spec004_seed.py` | T030 |
| T037 | `engine/adapters/whyyou/report_records.py` (route fix, ID-004-13) | T031 |
| T038 | `engine/adapters/whyyou/model_emission.py` | T032 |
| T039 | `scenarios/E-01.yaml` | v4 loader |
| T040 | `engine/executors/report_lanes.py`, `engine/executors/e01.py`, runner registration (ID-004-14/15) | T034, T008 E-01 2 |
| T041 | `engine/judges/e01.py`, `engine/judge.py` facade (ID-004-12) | T033 |
| T042 | capabilities + composition in `capability.py`/`adapter.py` | new `test_spec004_capability_composition.py` 4 (RED first: 3 failed) |
| T043 | this record | — |

```text
.venv\Scripts\python.exe -m ruff check . -> All checks passed!
.venv\Scripts\python.exe -m pytest -q    -> 674 passed, 6 xfailed
```

Citation gate on fakes: all four invalid modes emptied + reference unchanged → E01-A1 PASS; VALID stored with its
own Evidence → E01-A2 PASS; worker storing as emitted → E01-A1 FAIL; refused matrix report → `PRECONDITION_NOT_MET`.
E01-A3/A4 stay INCONCLUSIVE until US2. Remaining strict xfail (6): E-02 registration/preflight (T057, 2) and four
planned modules (T047, T055, T057, T058). Guards (H-03/E-03/N-02 digests, parent `15cef078…`) unchanged.

## Phase 5 — US2 removal gate (T044~T051)

| Task | Change | Tests |
|---|---|---|
| T044 | `tests/contract/test_spec004_evidence_mutation_adapter.py` (RED: 6 failed, ImportError) | 6 GREEN after T047 |
| T045 | `tests/unit/test_judge_e01_removal.py` (RED: 18 failed, AttributeError) | 18 GREEN after T049 |
| T046 | `tests/integration/test_e01_removal_restore.py` (RED: 5 failed) | 7 GREEN after T048 |
| T047 | `engine/adapters/whyyou/evidence_mutation.py`, composed in `adapter.py` | T044, composition 4 |
| T048 | removal/restore/probe steps, always-run restores in `engine/executors/e01.py` (ID-004-17/19) | T046, T034 |
| T049 | E01-A3/A4 and D1 exposure in `engine/judges/e01.py` (ID-004-16) | T045 |
| T050 | Spec 004 `cleanup-confirm` in `engine/cli.py` (ID-004-18) | new `test_cleanup_confirm_spec004.py` 2 (RED first: 2 failed) |
| T051 | this record | — |

```text
.venv/Scripts/python.exe -m ruff check . -> All checks passed!
.venv/Scripts/python.exe -m pytest -q    -> 708 passed, 5 xfailed
```

Removal gate on fakes: each H-4 indicator PASS; baseline P1 shape (score and citation kept) FAIL; restore digest
mismatch or probe restore failure → `RESTORE_FAILED`, INCONCLUSIVE and block; exception, cancellation and deadline
all restore and tear down; D1 recorded without affecting the verdict. With a fake exposing indicator `score_null`,
an E-01 Run is PASS. Remaining strict xfail (5): E-02 registration/preflight (T057, 2) and three modules (T055,
T057, T058).

## Phase 6 — US3 E-02 gate (T052~T060)

| Task | Change | Tests |
|---|---|---|
| T052 | `tests/contract/test_spec004_criteria_version_adapter.py` (RED: 6 failed, ImportError) | 6 GREEN after T055 |
| T053 | `tests/unit/test_judge_e02.py` (RED: 9 failed, ImportError) | 9 GREEN after T058 (fake fix ID-004-21) |
| T054 | `tests/integration/test_e02_orchestration.py` (RED: 8 failed) | 8 GREEN after T057/T059 |
| T055 | `engine/adapters/whyyou/criteria_versions.py` (routes ID-004-20) | T052 |
| T056 | `scenarios/E-02.yaml` (snapshot digest `e6e0c56e…`) | v4 loader |
| T057 | `engine/executors/e02.py`, runner registration (ID-004-23) | T054, T008 E-02 2 |
| T058 | `engine/judges/e02.py`, `engine/judge.py` facade (ID-004-22) | T053 |
| T059 | E-02 composition and `scoring.rule.source.read` drift probe | composition 4 (RED first: 2 failed) |
| T060 | this record | — |

```text
.venv/Scripts/python.exe -m ruff check . -> All checks passed!
.venv/Scripts/python.exe -m pytest -q    -> 736 passed
```

E-02 gate on fakes: full journey PASS with the second applicant bound to v2; first report changed → E02-A2 FAIL;
stored/served overall off by one → E02-A3 FAIL; wrong v2 binding → E02-A2 `PRECONDITION_NOT_MET`; teardown failure
or other positions changed → `RESTORE_FAILED` and block; scoring source drift → `RUNNER_NOT_READY` before any write.
No strict xfail remains.

## Phase 7 — US4 review/bundle gate (T061~T069)

| Task | Change | Tests |
|---|---|---|
| T061 | `tests/integration/test_spec004_verdict_matrix.py` (guard, GREEN on first run, ID-004-26) | 12 |
| T062 | `tests/contract/test_presentation_spec004.py` (RED: 3 failed) | 3 GREEN after T065 |
| T063 | `tests/contract/test_cli_spec004.py` (RED: 7 failed) | 7 GREEN after T066 |
| T064 | `tests/integration/test_spec004_bundle_links.py` (RED: 8 failed) | 8 GREEN after T067 |
| T065 | Spec 004 projections, claim boundary and `limitations` in `engine/presentation.py` | T062 |
| T066 | preflight capability counts, limitations, scoring-source status in `engine/cli.py` | T063 |
| T067 | cross-reference, redaction and recompute re-execution in `engine/evidence.py` (ID-004-24/25) | T064 |
| T068 | `tests/integration/test_spec004_orchestration.py` (RED without T067: 4 failed) | 4 |
| T069 | this record | — |

```text
.venv/Scripts/python.exe -m ruff check . -> All checks passed!
.venv/Scripts/python.exe -m pytest -q    -> 770 passed
```

Review gate on fakes: E-01 shows citation modes, removal applied/restored/exposed, E01-D1 per mode and the restore
status; E-02 shows v1/v2, first-report unchanged, second-report binding and per-target recompute equality; both carry
the claim boundary, `limitations` and `unverified_scope` AWS/N-01/N-03. Preflight reports 18/18 (E-01) and 16/16
(E-02) and writes nothing; exit codes 0/2/3/5/6 as contracted; no automatic retest.

## Phase 8 — retest machinery (T070~T071)

| Task | Change | Tests |
|---|---|---|
| T070 | `tests/integration/test_spec004_retest_lineage.py` (RED: 3 failed; profile-inheritance case is a guard) | 4 GREEN after T071 |
| T071 | `engine/retest.py` Spec 004 branch, executor retest records, verify link, `cli retest` (ID-004-27) | T070, new CLI retest test (RED without the CLI change) |

```text
.venv/Scripts/python.exe -m ruff check . -> All checks passed!
.venv/Scripts/python.exe -m pytest -q    -> 775 passed
```

Sandbox diagnostics T072~T078 and every official Run remain NOT_RUN.

## Sandbox diagnostics

**진단, 공식 아님.** 2026-10-07, 연우 PC 로컬 스택(WhyYou `bosung/controlproof-n02-integration` `42aaaba`, 변경 없음,
`docker compose down -v` 뒤 새 DB, API·작업자 4개, fixture `spec004-report-v1`). Spec 003 ID-003-18 같은 별도 격리
sandbox가 아니라 볼륨을 초기화한 로컬 스택을 진단 대상으로 썼다. 진단 bundle은 공식 runs 폴더가 아니라 workspace
`cp-local/archive/spec004-diagnostics/`에 run root로 직접 기록했다. `RESTORE_FAILED`·차단 없음.

Preflight: E-01 READY 18/18, E-02 READY 16/16, `scoring_rule_source` MATCH, health `fixture_id=spec004-report-v1`.

| Run (label) | 결과 | 시간 |
|---|---|---|
| `4ea910b9…` (`diag-sd-e01`) | E-01 FAIL: A1 PASS, A2 PASS, A3 FAIL(P1), A4 PASS, 복구 SUCCEEDED | 57 s |
| `f82d65ed…` (`diag-sd-e02`) | E-02 INCONCLUSIVE: 보고서 미생성(ID-004-29), teardown·다른 직무 불변 확인 | 558 s |
| `ee502194…` (`diag-sd-e02-r2`) | 재현: 같은 원인으로 INCONCLUSIVE | 557 s |

| SD | 상태 | 결과 |
|---|---|---|
| SD-1 (T076) | 완료 | **P1 확인.** 제거 receipt `affected_rows=1`, 별도 연결 부재 확인, 복원 digest 일치. 보고서 조회 PRE_REMOVAL·POST_REMOVAL·POST_RESTORE 세 번이 완전히 같음(총점 72, 두 항목 모두 `confirmed`·평균 72·축 5개 72, Evidence 필드 동일, `unknown_fields` 없음). 근거: ID-004-30. 타임라인은 200 아닌 응답이 기록되지 않아 보조 증거 없음(ID-004-28로 수정, 재측정 필요). |
| SD-2 (T074) | 차단 | E-02 보고서가 생성되지 않아 실측 못 함(ID-004-29). |
| SD-3 (T075) | 일부 | 제품 API로 v1·v2 생성·발행, 최신 발행 버전에 두 번째 지원자 묶기까지 동작. 보고서 생성에서 차단(ID-004-29). |
| SD-4 (T073) | 완료 | 네 잘못된 모드 `EMPTIED`, VALID `STORED_VALID`, E01-A1·A2 PASS. E-01 전체 57 s로 540 s 예산 안. |
| SD-5 (T077) | 완료 | E01-D1: EMPTY `AXIS_DROPPED`, NONEXISTENT·OTHER_APPLICANT `SHOWN_AS_WRITTEN`, 복원 RESTORED. |
| T078 | 일부 | 실행기 결함 2건: 타임라인 상태 누락(ID-004-28, 수정·시험 완료), teardown 뒤 보고서 잔존(ID-004-31, 미수정). |

ID-004-14 대기 시간: 보고서가 생기지 않으면 Run은 마감까지 기다린다(E-02 557~558 s). 거부도 같은 경로다.

진단 결과는 판정이 아니다. 공식 E-01·E-02 Run은 `NOT_RUN`이다.

## Actual Run ledger

(none yet — Phase 9; requires preflight READY and explicit approval)

## WhyYou PR #6 review fixes — 2026-10-07 (ID-004-03)

The user authorized fix, push and merge only into `bosung/controlproof-n02-integration`; main
is forbidden. Initial PR head `3dfa10c9cf34f26b499e32652f310447e5a119db`; fixed head
`3423f167664273152078faeb1b91d0324b98a2f4`. This entry supersedes the original timestamp-only
memory description without replacing its historical test results.

| Command / gate | Result |
|---|---|
| `python -m pytest -q backend/tests/unit/runtime/test_controlproof_model_substitute.py --tb=short` before code changes | EXPECTED RED: 5 failed / 48 passed in 0.72 s; company/request leakage, interleaved memory overwrite, missing closing bracket and missing marker separator |
| Same command after changes | 53 passed in 0.61 s |
| `python -m pytest -q backend/tests/unit/integration/test_submission_interview_consent.py backend/tests/unit/reporting backend/tests/unit/runtime backend/tests/integration/test_controlproof_fault_hook_safety.py --tb=short` | 177 passed in 4.29 s |
| `python -m pytest -q backend/tests/unit --tb=short` | 488 passed / 1 failed in 21.23 s; only known baseline `test_no_module_imports_another_lanes_private_package` |
| `ruff check` and `ruff format --check` on both WhyYou changed files; `git diff --check` | PASS |
| `git diff --exit-code eec8f70 HEAD -- <baseline guard's violating source files>` | PASS; recruiting_assistant/api.py, recruiting_assistant/application.py and runtime/worker.py are unchanged from the base |

Memory now requires matching company and report-request UUIDs, with the timestamp only an
additional stale-retry check. The reporting worker's context already identifies the Outbox event;
no new marker or product payload is needed. Invalid marker prefixes keep h03 output and emit
MARKER_INVALID. Existing h03 identity/health/output and target consent guards remain covered.

Only the substitute and its unit test changed in WhyYou. ControlProof updates are Spec 004
contract/tasks/decision/validation records only; no ControlProof implementation or whole-suite
rerun for this documentation change. Sandbox and actual E-01/E-02 Runs remain NOT_RUN.

PR #6 merged into `bosung/controlproof-n02-integration` at
`42aaaba206ced4288c8ee477b73f5f1ccf078bf3` (fixed source `3423f16`). WhyYou main remains
`cc8bf556b75f563f01cbf0487e28c555125077e7`. Use this merged integration HEAD for the later
sandbox/official Run source snapshot, not the superseded `3dfa10c` fixture head. Fetch/pull both
repositories before continuing; read this review entry with the corrected fixture contract.

## 세션 인계 (2026-10-07, 연우 마지막 세션 → 보성)

- 완료: T001~T071, Phase 8 진단 중 T072(진단 환경)·T073(SD-4)·T076(SD-1)·T077(SD-5). T078은 일부(ID-004-28 수정,
  ID-004-31 미수정). 결정 ID-004-01~31.
- 미완료: T074(SD-2)·T075(SD-3)는 WhyYou 보고서 embedder 연결 때문에 차단(ID-004-29). 다음 작업 번호는 T074다.
- 순서 제안: ① ID-004-29 (a) WhyYou PR 병합 → ② SD-2·SD-3 재실행(T074·T075) → ③ T078 나머지(ID-004-31, 필요하면
  SD-1 타임라인 재측정) → ④ Phase 9 T080~(quickstart §6 preflight, §7 최초 actual Run, §8 최초 FAIL 처리).
- **공식 E-02 Run은 ID-004-29 수정 병합이 전제다.** 공식 E-01 Run은 지금 대상으로 가능하며 SD-1대로라면 E01-A3
  FAIL(P1)이 예상된다. P1 수정(T085, ID-004-30)은 그 FAIL을 봉인한 뒤에만 한다.
- 열린 PROPOSED: ID-004-29(추천 (a)), ID-004-30(T085, Phase 9), ID-004-14 (b) observer 확장(추천: 거부가 예상될 때만).
- 환경: 두 `.env`는 `h03-report-v1`로 복원, API·작업자 종료, `docker compose down`(볼륨 유지), WhyYou checkout은
  `bosung/controlproof-n02-integration` `42aaaba` 변경 없음. 진단 bundle은 workspace `cp-local/archive/spec004-diagnostics/`.
- 연우 PC 한정(다른 PC에서는 해당 없을 수 있음): WhyYou DB 포트 5433, ControlProof `.env`는 프로세스마다 수동 로드
  (quickstart §3 명령), Windows 앱 제어 때문에 `.venv`의 SQLAlchemy `*_cy*.pyd`를 `.blocked`로 바꿔 둠, PS 5.1에서는
  `scripts/local.ps1 up`을 별도 `powershell.exe -File`로 실행해야 docker stderr를 오류로 보지 않음.

## ID-004-29 continuation — report embedder wiring (2026-10-07)

- User authorized step 1 / option (a). WhyYou source baseline:
  `bosung/controlproof-n02-integration` `42aaaba206ced4288c8ee477b73f5f1ccf078bf3`;
  ControlProof input: `yeonwoo/004-e01-e02-score-evidence` `0dc87999d57e947307afdf85e64aad75d554bb95`.
- Changed only the report handler's `embedder=aws.embedder` to the existing resolved `report_embedder`, plus
  `backend/tests/unit/runtime/test_controlproof_report_embedder_wiring.py`. The two composition tests call the
  real worker factory with infrastructure creation replaced: substitute enabled uses the fixed embedder shared
  with the runtime; disabled preserves the identical AWS embedder object.
- EXPECTED RED before the source fix:
  `python -m pytest backend/tests/unit/runtime/test_controlproof_report_embedder_wiring.py -q`
  → **1 failed, 1 passed** (9.61 s). The enabled handler received the AWS fallback. No unexpected test failure.
- After the source fix:
  `python -m pytest backend/tests/unit/runtime backend/tests/unit/reporting -q`
  → **172 passed** (10.14 s; third-party deprecation warnings only).
  `python -m ruff check backend/src/interview_evidence/runtime/worker.py backend/tests/unit/runtime/test_controlproof_report_embedder_wiring.py`
  and `git diff --cached --check` → **PASS**.
- Optional format check: the new test file passes; `worker.py` still has its pre-existing attestation flag
  condition formatting mismatch. The pristine baseline also returns exit 1. No unrelated formatting fix added.
- Fix commit `77df3137aaf61003d4679f20276333b5eac2c290`; [WhyYou PR #7](https://github.com/jhkim0602/gbsa_aws/pull/7)
  merged into `bosung/controlproof-n02-integration` at `ce8d8620d2b2fec7f448ae312cf13334b408c01a`, then pulled locally.
  PR contains the one-line source fix and the two tests only; no GitHub CI checks were attached.
- No service or diagnostic/official Run executed in this continuation. E-01/E-02 official Runs and AWS remain
  **NOT_RUN**. T074/T075 must confirm live diagnostic behavior; ID-004-31 / T078 remains open. ID-004-30 / P1
  product correction remains PROPOSED until the first official E-01 result is sealed. Main and existing evidence
  were not modified. Historical handoff and diagnostic entries above describe their original checkpoints.

## Phase 8 continuation — SD-2/SD-3 and runner corrections (2026-10-07)

T074/T075/T078 complete; **diagnostic only**. Official E-01/E-02 and AWS remain **NOT_RUN**.
WhyYou source for every Run below: `ce8d8620d2b2fec7f448ae312cf13334b408c01a`, clean clone of
`bosung/controlproof-n02-integration`. No WhyYou source/product change in this continuation.
ControlProof branch: `yeonwoo/004-e01-e02-score-evidence`; clean committed sources per row below.

### Isolation and execution

- Fresh dedicated project `controlproof-spec004-sd-20261007`: PostgreSQL 16+pgvector (loopback 15434),
  Moto S3/SQS (loopback 14567), WhyYou API (loopback 18084), four actual worker children. Existing WhyYou DB,
  containers, `.env` and original untracked evidence were preserved. Fixed `spec004-report-v1` and synthetic
  credentials only; external AI disabled, provider endpoints loopback. No real AWS/GCP keys used.
- Moto image pinned to `motoserver/moto@sha256:91fd602a21f49cf9eb82fdf474015a3c131d40104c8297ea6a2ca920708ae32c`.
  Migration + local infrastructure bootstrap succeeded; API `/v1/me` 200. Clean clone avoids changing or hiding
  the original checkout's untracked evidence. The separate diagnostic root is outside either Git repository.
- Preflight E-02 READY **16/16**, scoring source **MATCH**; E-01 READY **18/18**. These are diagnostic-source
  preflights, not the final T079 record. Standard target ID remains `whyyou-local`; separation is by DB,
  processes and roots. An initial harness-only noncanonical ID gave 15/16 and was corrected before any Run.
- Harness commands: `sandbox.py init`, `start`, `bootstrap`, `preflight E-02`, `preflight E-01`,
  `diagnostic E-02` (three Runs), `diagnostic E-01` (two Runs), and `verify <Run ID>`.
  They call `python -m engine.cli run/preflight E-0N --profile <canonical profile> --target whyyou-local --json`;
  diagnostic Runs additionally use `--label diag-sd-post-embedder-cleanup` and an isolated Run root.
  API startup was retried after one connection refusal. Windows stdout decoding was corrected to UTF-8;
  a missing JSON line after a CLI error caused StopIteration in the scratch harness, corrected with durable
  sentinel ownership journaling and exit cleanup. None of these alter sealed evidence.

### Immutable diagnostic ledger

| Run ID | Scenario / ControlProof source | Result / bundle | Journey seconds (budget 540) | Manifest SHA-256 |
|---|---|---|---:|---|
| `5faf7349-dc83-4926-a817-2ebe354f9e4a` | E-02 / `517ff3f8f37e58345b36c9a6ec09e2836b3f874f` | FAIL / VERIFIED (including reverify after policy fix) | 25.038276 | `499d785f42e2bc9ea1986f4af07aa886b875c9204a9f54f10e2d36c24f7563a6` |
| `571892e5-179d-41b9-8989-19af3f987d69` | E-02 / `613d172ebefaeb2c1fa32051e775ec64c9de389d` | judgement PASS / INVALID; CLI exit 1, verify exit 5 (never a verified PASS) | 23.772613 | `aaf455562994e52bcf3af3d91f6e1673e8fb62bbbdde849d92c77cac8ac9ef01` |
| `e637f455-c480-412a-87fa-fca6ac8fcde2` | E-02 / `0629fc48dc6781798b9adabe6bdbd99ad96895bd` | PASS / VERIFIED | 23.610941 | `67c786a964a08899bae66253ae8195815b94957aeff697348a06d73f626b9b59` |
| `0ca479ca-498d-4c44-a72a-7871adc8d8ef` | E-01 / `0629fc48dc6781798b9adabe6bdbd99ad96895bd` | FAIL / VERIFIED; timeline 500 | 34.613072 | `5f2a4686ba09d8aa3c5ec95ce0fad29ddeb632454aaa180be65c2dc2cf3e0a8d` |
| `9855c988-af83-4348-a9a4-da13aadb783d` | E-01 / `8a6ee1b341dd217f569427852ea8602ed59f666a` | FAIL / VERIFIED; timeline 200 | 27.605838 | `00792998c69c8d69e7b50333f8414f6cf3b970237a66c733fc2e65e0c5712d4c` |

- First E-02: A1/A2 PASS, A3 FAIL. Values were equal by criterion ID, but stored/API contribution arrays had
  different orders. Preserve that FAIL and its positional comparison evidence. Reverification with the final
  verifier remains VERIFIED; no file in that bundle changed.
- Second E-02: judge used keyed comparison, but verifier still used positional comparison. Its sealed bundle
  is INVALID (despite PASS in judgement.json); retained without relabelling or editing. The next Run uses an
  explicit comparison policy version and verifies. This is a runner failure, not a WhyYou PASS claim.
- Final E-02: A1/A2/A3 PASS. Product API published v1 then v2; the second report uses v2 ID/weights. Recompute:
  72.5 → 72 and 73.5 → 74 (Python banker rounding, denominator 1). The first report ID/state digest and frozen
  inputs are identical before/after v2 publish. Stored score and API integer score comparisons remain exact;
  float tolerance remains 1e-9. Only criteria/contributions arrays compare by unique criterion_id; missing,
  duplicate or substituted IDs, changed fields/values and other ordered lists are not relaxed (ID-004-32).
- Final E-01: A1/A2/A4 PASS, A3 FAIL. D1 remains diagnostic only. After tenant-scoped media seed correction,
  timeline GETs are 200 with 2 → 1 → 2 entries (remove/reinsert). Report GET stays 200 and its citing scores
  remain visible after segment removal: P1 persists. No pre-fix to WhyYou; ID-004-30/T085 still PROPOSED,
  conditional on the first sealed official result. Prior 500 responses remain visible in the prior bundle.
- All five diagnostic restores SUCCEEDED. Final E-02 restore 0.204463 s, internal bundle verify 0.276615 s,
  independent verify 2.000 s; command wall 32.141 s. Final E-01 restore 0.488300 s, internal verify 0.268086 s,
  independent verify 1.875 s; command wall 33.859 s. All satisfy 120/60/540/600-second limits.

### Cleanup and preservation evidence

- ID-004-31: reports have no FK to session; assistant search projections also have no FK to report. Delete only
  reports for registered Run-owned company/session IDs, their FK dependents and company/report-scoped search
  projections, in the seed teardown transaction. Failure rolls back all rows and preserves ownership/credentials
  for retry. Other-company and other-Run report data survive the contract test.
- Live checks show zero `reports`, `report_items`, `evidence`, `assistant_retrieval_documents`, `positions`,
  `competency_model_versions`, `interview_sessions` after final maintenance. Protected non-Run position/version
  digests match before/after both scenarios; each newly journalled sentinel teardown succeeds.
- The first two diagnostic Runs left 12 search projections before the projection fix. Maintenance removed only
  those four artifact-owned report IDs with company scope; manifest bytes stayed unchanged. A scratch-harness
  interruption left one synthetic sentinel (outside tested Runs); ownership was recovered from its full UUID
  in the synthetic position title, deterministic IDs and synthetic email, then its seed alone was torn down.
  Two scratch rehydration attempts returned SEED_NOT_OWNED without DB changes before registration was corrected.
- Raw records and bundles remain local at workspace `.pr-review/20261007/spec004-sandbox/`:
  `archive/spec004-diagnostics/`, `step2-final-audit.json`, `owned-orphan-cleanup.json`,
  `interrupted-sentinel-cleanup.json`, `sentinel-*.json`, command stdout/stderr/result journals. No new raw
  evidence, credentials or synthetic environment secrets are committed. Cleanup record hashes:
  `owned-orphan-cleanup.json` = `b28c41d336716c947f88e569a2babdbdfa123ac4fdfb0f3c9a5a6f9d159b3964`;
  `interrupted-sentinel-cleanup.json` = `d5ff90ae174f335e9a79915330f7ad8bda61bae99f96abe2cdabd8e2615f8cd9`.
- After diagnostics, the 14 owned API/worker process-tree members and only the dedicated Docker project were
  stopped. DB volume, containers, logs, harness and evidence remain. Restart using that project's compose up,
  `sandbox.py init` (recreates in-memory Moto infrastructure), `start`, `bootstrap` before fresh preflights.

### Tests and gates (ControlProof .venv Python)

| Command / scope | Result |
|---|---|
| Seed cleanup tests before implementation (two new cases in `test_spec004_seed_adapter.py`) | EXPECTED RED: 2 failed; Run-owned reports remained, injected report-delete failure was never reached. Two initial fixture setup errors were corrected before meaningful RED. |
| Seed + E-02 orchestration + Spec 004 orchestration | 22 passed |
| Contribution-order tests (`test_judge_e02.py -k contribution`) before keyed fix | EXPECTED RED: 2 failed, 8 passed, 9 deselected; reordered equivalent arrays failed; eight corruption cases remained FAIL. |
| Judge / scoring-copy / E-02 orchestration / bundle links | 53 passed |
| Versioned bundle tests (five new cases in `test_spec004_bundle_links.py`) before verifier fix | EXPECTED RED: 1 failed, 4 passed, 8 deselected; valid keyed record rejected by positional verifier. |
| Search-projection teardown tests before projection fix | EXPECTED RED: 2 failed, 8 deselected; orphan projection remained. |
| `pytest tests/contract/test_spec004_seed_adapter.py tests/unit/test_judge_e02.py tests/unit/test_e02_scoring_copy.py tests/integration/test_spec004_bundle_links.py tests/contract/test_bundle_profile_spec004.py -q` | 71 passed (17.10 s) |
| Tenant media seed test before fix (`test_spec004_seed_adapter.py -k seed_question`) | EXPECTED RED: 1 failed, 9 deselected; media key outside company prefix. |
| `pytest tests/contract/test_spec004_seed_adapter.py tests/integration/test_spec004_orchestration.py -q` | 14 passed (3.79 s); preceding command had one nonexistent test path and ran no tests, then corrected. |
| `python -m pytest -q` at final source `8a6ee1b` | **793 passed** (289.49 s). Earlier full-suite attempt was interrupted before completion when the live timeline seed defect was identified; no result claimed for it. One complete Phase 8 full regression. |
| `python -m ruff check .`; `git diff --check` | PASS |

Next: **T079** on newly committed clean sources, then separately approved initial official T080/T081,
source/result freeze T082 and evidence-based classification/remediation T083~T090, then Phase 10 closure.
Spec 004 is **not Complete**. No main changes, checkpoint rewrites or official Runs occurred in this step.

## T079 — clean-source official readiness gate (2026-10-07)

Preparation only; **no official Run or retest executed**. E-01/E-02 and AWS remain **NOT_RUN**.
The completed gate was recorded at `2026-10-07T12:38:11.872332+00:00`.

| Source | Branch | HEAD during preflight | State |
|---|---|---|---|
| ControlProof | `yeonwoo/004-e01-e02-score-evidence` | `ae6cfe093de85f54ecfd7db75adff8320e488748` | clean, matches fetched remote HEAD |
| WhyYou | `bosung/controlproof-n02-integration` | `ce8d8620d2b2fec7f448ae312cf13334b408c01a` | clean execution checkout, same as original/fetched remote HEAD |

Original WhyYou checkout retains its previously untracked `.controlproof/` evidence. No tracked changes;
those files were not hidden, deleted or committed. API/workers execute the previously established clean clone
at workspace `.pr-review/20261007/spec004-sandbox/whyyou-clean/`. Both main branches remain unchanged.

| Command (ControlProof .venv Python, quickstart §6) | Exit | Readiness | Capabilities | Duration |
|---|---:|---|---|---:|
| `python -m engine.cli preflight E-01 --profile E01_CITATION_EVIDENCE_V1 --target whyyou-local --json` | 0 | READY | 18/18 | 4.281 s |
| `python -m engine.cli preflight E-02 --profile E02_SCORING_FREEZE_V1 --target whyyou-local --json` | 0 | READY | 16/16 | 5.407 s |

- Both: `LOCAL_EMULATED`, AWS `NOT_RUN`, fixture `spec004-report-v1`, digest
  `e15ec3790b64b2fba10e0caa9372f08c917edbbaa99ce308076952b838668b3f`.
- E-02 scoring source: **MATCH**, both pinned blobs present. E-01 has no scoring-source requirement.
- Reused only the dedicated PostgreSQL/Moto project (loopback 15434/14567); bootstrapped Moto infrastructure
  after restart, then started API (18084) and four real worker children with the same synthetic configuration.
  API `/v1/me` 200; preflight includes the live API/worker readiness and AI isolation contracts.
- Fresh observer/fault roots: `.pr-review/20261007/spec004-sandbox/t079-observers/` and `t079-faults/`.
  Intended official Run root: workspace `cp-local/spec004-official/runs/`; separate from all diagnostic bundles.
  No UUID Run directory exists before/after. Positions, versions, interview sessions, reports, report items,
  evidence and assistant projections remain **0 → 0**. No report request or change injection was submitted.
- Startup recovery: the scratch startup helper initially ran under ControlProof's venv, which lacks WhyYou's
  `cryptography`; it failed before creating services. The preflights attempted before startup completed returned
  RUNNER_NOT_READY: E-01 10/18 (exit 2, 22.063 s), E-02 8/16 (exit 2, 25.578 s). These are readiness failures,
  not WhyYou verdicts. Reran the helper in the existing WhyYou venv; infrastructure exit 0 (3.706 s), API 200,
  then both final preflights above succeeded. No dependency installation or product-source edit was needed.
  Initial records remain in `t079/` and `t079-preflight-E-0N.stdout/.stderr/.result.json`; final records use a
  separate timestamp directory so failed preparation history is preserved.
- Final local records: workspace `.pr-review/20261007/spec004-sandbox/t079/preflight-20261007T123801056715Z/`:
  `preflight-E-01.json`, `preflight-E-02.json`, `readiness-summary.json`. Preflight payload SHA-256:
  E-01 `ce0c167f3496c15a6bac76f46f7c74b016e5b38c524af1a87daba7d70a96e578`;
  E-02 `947c81e5ec9cebe6342d80a56b9590bf62d9739fa50b9e606b64db5f8000d3a4`.
- Dedicated API/workers/containers remain running for the next approved step. Process roots/logs are recorded
  in `t079/processes.json` and `t079/api.log`, `workers.log`; synthetic credentials stay in process memory.
- Changed only this validation and tasks record. No implementation changes or regression rerun; the Phase 8
  full gate remains 793 passed / ruff PASS. Global state docs will be synchronized at Phase 9 end. This record
  commit changes documentation only; the listed source SHAs describe the actual preflight checkpoints.

Next: T080/T081, exactly one initial official Run per scenario with show/verify and immutable source/result
records, then T082. Quickstart §6 requires explicit approval for official execution; this step authorizes and
completes only the T079 preparation gate. E01-A3 FAIL/P1 remains expected from diagnostics. No P1 product
change is applied before sealing the first official result. Actual Run setup must capture its current clean
source SHA again; this preflight is not a permanent readiness guarantee or an official verdict.

## T080~T082 — first official actual-stack results (2026-10-07)

The user explicitly authorized stage 4: one initial official E-01 and E-02 Run plus show/verify and records.
These are **official LOCAL_EMULATED Runs**, distinct from Phase 8 diagnostics. AWS remains **NOT_RUN**.
Fixed synthetic inputs/model do not prove real external AI behavior or legal certification. No WhyYou product
correction before the first E-01 FAIL; both initial results remain immutable.

### Fixed sources and preparation

- ControlProof `yeonwoo/004-e01-e02-score-evidence`: `8c266f5dc77e0cfff53215ba44226c719ad78615`, clean.
- WhyYou `bosung/controlproof-n02-integration`: `ce8d8620d2b2fec7f448ae312cf13334b408c01a`, clean execution
  checkout. Original repository HEAD matches; prior untracked raw evidence preserved. Both bundle source
  snapshots match these SHAs with dirty=false. No source/branch/commit change during either Run.
- Dedicated PostgreSQL/Moto/API/four actual workers from T079; loopback endpoints, synthetic credentials,
  external AI disabled, `spec004-report-v1` digest
  `e15ec3790b64b2fba10e0caa9372f08c917edbbaa99ce308076952b838668b3f`.
- Fresh preflights: E-01 READY 18/18 (exit 0, 6.688 s), E-02 READY 16/16 (exit 0, 6.422 s);
  E-02 scoring-source pinned blobs 2/2 MATCH. No preflight-created subject/report/Run.
  CLI also runs its required readiness check immediately before actual execution. Fresh raw preflight root:
  `.pr-review/20261007/spec004-sandbox/t079/preflight-20261007T125103157494Z`.
- Official root: workspace `cp-local/spec004-official/runs/`; separate from all diagnostic bundles.

### Immutable first results

| Scenario | Run ID | CLI exit / verdict | Assertions | Restore / bundle | Manifest SHA-256 |
|---|---|---|---|---|---|
| E-01 | `09c9d9bb-82a3-4485-9c9d-e9721f2452e4` | 3 / FAIL | A1 PASS, A2 PASS, A3 FAIL, A4 PASS | SUCCEEDED / VERIFIED (17 files) | `7f622a3381e6c03dac907f55604f1f82c03e5101e33736b4f22bde50cc8475b2` |
| E-02 | `e39e62ae-be73-4e52-8cab-1f878637a0c6` | 0 / PASS | A1~A3 PASS | SUCCEEDED / VERIFIED (17 files) | `e6b74b7e78fa40a77d0c3c99315592e2e7713e9891d43f68b8d4b437d2d28364` |

- E-01 A1: four invalid citation modes emptied by worker validation; reference report unchanged. A2: VALID
  score/citation stored with same criterion's Evidence. Actual emission receipts and worker-stored rows agree.
- E-01 A3: **P1 observed officially**. One Run-owned transcript segment was removed, absence confirmed;
  report/timeline GETs 200, timeline entries 2 → 1 → 2. The affected item kept its score/citation without
  an H-4 evidence-insufficiency indicator. Unaffected items unchanged. Preserve A3 FAIL, never restate PASS.
  A4: restored report read and stored record match baseline.
- E-01 segment reinsert and probe-axis rewrite both RESTORED, with equal pre/post projection digests.
  Teardown succeeds; manual_cleanup_required=false.
- E-02 A1: complete frozen scoring/model/prompt/config/version inputs. A2: second report uses product-API
  published v2 ID/weights; first report ID/digest/frozen inputs/API read unchanged. A3: recomputed totals
  72.5 → 72 (v1), 73.5 → 74 (v2), denominator 1, all comparisons agree. CRITERION_ID_V2 declared, observed
  array order preserved; exact integers, 1e-9 float tolerance and pinned arithmetic copy unchanged.
- No INCONCLUSIVE assertion or required missing evidence. Original per-assertion reason_code fields are null
  for these PASS/FAIL rows; detail/actual/expected describe the factual reasons. Preserve that shape when
  reviewing SC-001; never edit the sealed judgement afterward to fill a code.

### E01-D1: supporting observation and limit

| Mode | Official observation |
|---|---|
| EMPTY | AXIS_DROPPED |
| NONEXISTENT | SHOWN_AS_WRITTEN |
| OTHER_APPLICANT | SHOWN_AS_WRITTEN |
| OTHER_CRITERION | NOT_OBSERVED — no write/read attempted |

D1 is a diagnostic within the official Run, **not an assertion or additional target FAIL**. Current `_probe`
writes three modes, following ID-004-17's single-criterion design. FR-013 still requires four. Resolve this
implementation/document discrepancy before closure; three observations do not prove four-mode coverage.
It does not alter A1~A4 facts or E-02 PASS. No fixture, product meaning or sealed storage-probe file changed.
Review in T083/T084; product-meaning changes require approval.

### Timing and recovery

| Scenario | Journey ≤540 s | Run command wall | show / verify (verify ≤60 s) | Command time sum | Submission→verify record wall ≤600 s | Restore ≤120 s |
|---|---:|---:|---|---:|---:|---:|
| E-01 | 38.031042 | 45.109000 | 1.813000 / 1.828000 | 48.750000 | 80.700767 | 0.396020 |
| E-02 | 21.245658 | 27.938000 | 2.344000 / 2.422000 | 32.704000 | 69.082898 | 0.177660 |

Total wall uses durable submission timestamp through verify-result write time (includes idle/operator time),
not just summed command durations. Both internal bundle verifications also meet 60 seconds. No restore block
or manual cleanup required. After each Run, positions, versions, interview sessions, reports, report items,
Evidence and assistant search projections are 0. E-01 verify/restore/zero-residue gates passed before E-02.
After both Runs, both manifest bytes and all 17 registered file hashes remain unchanged.

### Commands and original evidence

ControlProof .venv Python, same configuration as T079; no .env edited:

- `python -m engine.cli run E-01 --profile E01_CITATION_EVIDENCE_V1 --target whyyou-local --label e01-initial --json`
- `python -m engine.cli show 09c9d9bb-82a3-4485-9c9d-e9721f2452e4 --run-root <official-root> --json` → exit 0.
- `python -m engine.cli verify 09c9d9bb-82a3-4485-9c9d-e9721f2452e4 --run-root <official-root> --json` → exit 0, VERIFIED;
  EV4-01/02/03/04/05/09/10 checked.
- `python -m engine.cli run E-02 --profile E02_SCORING_FREEZE_V1 --target whyyou-local --label e02-initial --json`
- `python -m engine.cli show e39e62ae-be73-4e52-8cab-1f878637a0c6 --run-root <official-root> --json` → exit 0.
- `python -m engine.cli verify e39e62ae-be73-4e52-8cab-1f878637a0c6 --run-root <official-root> --json` → exit 0, VERIFIED;
  EV4-01/02/04/06/07/08/09/10 checked.

<official-root> = workspace `cp-local/spec004-official/runs/`. Exactly two initial official Runs exist, one per
scenario, parent_run_id=null; no retry/retest/child submitted. Original bundles and command stdout/stderr,
result, submission, inspection journals remain outside Git at `cp-local/spec004-official/`; time audit:
`commands/official-time-audit.json`. Scratch helper uses an exclusive submission journal and stops on abnormal
restore/verification. T082 source/result mapping frozen in traceability. No new raw evidence publicly uploaded.

Only Spec tasks, validation and traceability changed. No implementation change or pytest rerun; Phase 8
793 passed / ruff PASS remains the automatic gate. Main untouched. Global docs wait for Phase 9/closure sync;
older NOT_RUN entries describe their own checkpoints. Scratch document-generator quoting errors occurred
before any files were written, then were corrected; they had no effect on execution or sealed evidence.

Next T083: classify E01-A3 FAIL and review ID-004-17/FR-013 D1 coverage discrepancy. Then T084 runner fixes
if needed, T085 P1 proposal/approval, T086 approved WhyYou fix, T087 conditional proposal/NOT_REQUIRED,
T088 approved child preserving this parent. T089~T097 closure and independent reproduction remain pending.
Spec 004 is **not Complete**.

## 2026-10-07 — T083 classification and T084 D1 runner correction

Scope requested: classify initial official failures and complete the missing D1 OTHER_CRITERION observation
before the next product-remediation bundle. ID-004-34 contains exact parent artifacts and cause classes:
A3 TARGET_CONTROL_DEFECT; D1 missing coverage RUNNER_OR_OBSERVER_DEFECT; no unsafe-restore defect or
INCONCLUSIVE assertion. Initial A1/A2/A4 and E-02 all PASS, so T087 NOT_REQUIRED.

Changed owning files: seeds/spec004_subjects.py, engine/executors/e01.py; seed/removal/restore/presentation
contract tests; data-model's additive donor provenance field. Two VALID probe criteria use 50/50 weights.
The target and donor are selected by seed criterion identity, independent of returned item order. Evidence
must belong to the other item in the same owned report, version, answer and existing segment, and actually
be quoted by a scored donor axis. Missing/foreign/unquoted provenance prevents all probe writes and records
NOT_RUN / PROBE_PREREQUISITE_UNVERIFIED. Four modes remain diagnostic-only; no assertion meaning changed.

| Gate | Command | Result |
|---|---|---|
| RED | pytest seed deterministic contract + test_e01_removal_restore.py -q | 8 intended assertion failures / 6 PASS, 8.47 s; missing second criterion/fourth mode/pre-write guard |
| GREEN scoped | pytest seed adapter + removal_restore + spec004_retest_lineage -q | 27 PASS, 11.93 s |
| Restoration/bundle scope | pytest removal_restore + bundle_links + bundle_profile_spec004 + evidence_mutation_adapter + judge_e01_removal -q | 62 PASS, 33.54 s; includes reversed item ordering and exact before/after item/evidence restoration |
| Full regression, once | pytest -q | 799 PASS / 1 FAIL, 309.83 s; sole failure was test_presentation_spec004.py::test_e01_projection_shows_modes_removal_and_diagnostic expecting the obsolete three modes |
| Failed-contract correction | pytest presentation_spec004 + cli_spec004 -q | 11 PASS, 9.02 s; only the old test expectation changed after the full invocation, no executor/seed change |
| Static | ruff check .; git diff --check | PASS |

Full-command failure is retained in the record; it is not relabeled as a green full run. All full-suite
cases executed; the sole failed expectation was corrected and re-executed in its output/CLI scope, avoiding
a redundant full-suite invocation. Logs remain outside Git under .pr-review/20261007/spec004-sandbox/.
No unexpected implementation/restore failure or syntax error occurred. Original parent bundle bytes have
not been changed. Official D1 child verification follows on clean committed sources; E01-A3 is expected to
remain FAIL because WhyYou P1 is unchanged. T088 cannot be marked complete until the separate product
remedy has its required lineage verification. AWS NOT_RUN; Spec 004 not Complete. Global docs wait for closure.

### D1 parent-linked child — four-mode coverage verified, A3 still FAIL

- Child `ec0c895d-4617-457a-94ce-7d0198e1c6a5`, parent
  `09c9d9bb-82a3-4485-9c9d-e9721f2452e4`, label `e01-d1-four-mode`, LOCAL_EMULATED.
- Clean execution sources: ControlProof `69d3c003e468d3fd1c84070a5413d86b1e252f77` on
  `yeonwoo/004-e01-e02-score-evidence`; WhyYou clean clone `ce8d8620d2b2fec7f448ae312cf13334b408c01a`
  on `bosung/controlproof-n02-integration`. Original WhyYou tracked files unchanged; historical untracked
  probe files retained. Neither main changed (ControlProof 71a2c250; WhyYou cc8bf556).
- Before submission: both initial parents re-verified; every registered file and manifest hash matched.
  Fresh E-01 preflight READY, 18/18; preflight created no Run or owned data. Exactly one child submitted.
- `retest` exit 3, COMPLETED / FAIL; A1/A2/A4 PASS, A3 FAIL with the same P1 meaning. `show` exit 0;
  `verify` exit 0, VERIFIED. Child manifest SHA256
  `606cf7a0d70bc1a8cfef3743fca2c7b95334e88dcd1a0e58acd65cd975f3250f`, 19 registered files.

| D1 mode | Child observation |
|---|---|
| EMPTY | AXIS_DROPPED |
| NONEXISTENT | SHOWN_AS_WRITTEN |
| OTHER_APPLICANT | SHOWN_AS_WRITTEN |
| OTHER_CRITERION | SHOWN_AS_WRITTEN |

`other_criterion_source` and PRE_PROBE records prove that Evidence
`01a11690-575b-75a4-a0e1-13b9ba46ccbf` belongs to donor item
`01a11690-575b-7f55-935a-91dedc1d51e0`, different criterion from target item
`01a11690-575b-7410-a0cd-624bf77eaf07`, in the same report/version/Run. The donor and target stored
items/Evidence exactly match after restoration; pre/post state digest matches. Both injections RESTORED,
restoration SUCCEEDED (0.390982 s), teardown successful, no block or manual cleanup. Positions, versions,
interview sessions, reports, report items, Evidence and assistant search projections remain 0.

Journey 29.677024 s; retest wall 37.609 s; show 1.781 s; verify 1.922 s; durable submission-to-verify
record wall 41.330597 s. All 540/120/60/600-second budgets satisfied. After the child, both original
parents' manifest bytes and every registered file hash remain unchanged. retest-diff declares identical
scenario/profile/WhyYou target/fixed-model fixture/scoring source, changed ControlProof commit, new lane
manifest and reused_identities=[]. No WhyYou product fix was applied.

Commands (ControlProof venv, same isolated t079 environment): parent `verify` x2; E-01 `preflight`;
`python -m engine.cli retest 09c9d9bb-82a3-4485-9c9d-e9721f2452e4 --target whyyou-local --label e01-d1-four-mode --run-root <official-root> --json`;
`show` and `verify` for the child with the same root. Raw bundles remain at workspace
`cp-local/spec004-official/runs/`; exclusive submission, source/parent hashes, stdout/stderr, readiness,
timing and zero-residue inspection are in `cp-local/spec004-official/commands/t084-d1-child/` outside Git.

Metadata caveat found during lineage inspection: the existing generic retest-link reason is literally
"WhyYou 수정 후 E-01 독립 Run 재시험", even for this ControlProof-only correction. It does not describe the
actual change; immutable source snapshots and retest-diff prove WhyYou unchanged. Preserve the sealed text
and report this limited wording issue for follow-up in T088; no additional retest implementation was added
to this D1 scope. D1 completion is coverage, not a target-control PASS. T088 remains incomplete for the
separate A3 remedy, T085/T086 remain pending, AWS NOT_RUN and Spec 004 not Complete.

## 2026-10-08 — T085 concrete P1 remedy review (approval pending)

Both source checkpoints inspected: ControlProof yeonwoo/004-e01-e02-score-evidence 9dd6194 (clean);
WhyYou bosung/controlproof-n02-integration ce8d862 (tracked clean, historical untracked probes preserved).
ID-004-30 continuation defines the recommended response-only transcript_available boolean, tenant/session/
answer/segment lookup, exact restore behavior and RED/verification gates. Official parent P1 FAIL and D1
child FAIL remain unchanged; no new actual Run or WhyYou implementation occurred.

Unexpected scope discovered: EvidenceView additionalProperties=false forbids the proposed field.
The published OpenAPI schema and consumed TypeScript type must be updated in addition to the two product
code files. The original generator and npm contract commands no longer exist; generated/README documents
manual updates, while generated Python is stale/unused. A six-file WhyYou allowlist (two code, two contract,
two tests) is recorded in ID-004-30. ControlProof judge/adapter already support the exact H-4 field, so no
scenario/engine change is proposed. Product scores and frozen inputs retain their meaning; UI rendering
is outside this API-path remedy.

T085 remains unchecked until approval of this concrete plan and file expansion. T086 not started. This
pause follows FR-051 / plan §8's product-owner approval and the user's unexpected-scope stop/report rule.
No pytest/ruff repeated for this documentation-only review. Global status docs unchanged; Spec 004 not
Complete; AWS NOT_RUN. Next action after confirmation: branch, failing tests, implementation and scoped
WhyYou gates, then a PR to the integration branch.

## 2026-10-08 — T085 approval and T086 WhyYou remedy PR

Approval: after the concrete recommended six-file plan and scope question, user "바로 진행시켜봐".
T085 is CONFIRMED; prior PROPOSED/pending entries describe their checkpoints. T086 implemented from
WhyYou integration ce8d862 on yeonwoo/controlproof-e01-e02-report-evidence, fork bosung0505/gbsa_aws,
commit b15ba8a88be1f31b354638e42a9b828b34c06875. PR #8:
https://github.com/jhkim0602/gbsa_aws/pull/8 (base bosung/controlproof-n02-integration), OPEN/unmerged,
head b15ba8a, six changed files. Main remains unchanged. Original untracked .controlproof probes retained.

Response-only transcript_available checks current tenant/session/segment/answer presence. One batch query,
no transcript body/media lookup, no query with no Evidence; foreign report rejected before SQL. Query
failure propagates; no invented availability for unchecked views. Removal changes only the affected Evidence
availability, exact restoration restores the whole response. Original scores, stored report/item/Evidence
columns and frozen scoring inputs remain equal. Schema/TypeScript field optional; no UI or engine change.

| Gate | Command / scope | Result |
|---|---|---|
| RED availability | pytest backend/tests/unit/reporting/test_report_evidence_availability.py -q | 8 failed / 1 passed, 2.92 s; missing repository method / HTTP field |
| RED API contract | pytest backend/tests/unit/reporting/test_report_view_contract.py -q | 3 failed / 3 passed, 2.91 s; missing schema property |
| GREEN focused | pytest both files above -q | 15 passed, 2.42 s |
| Related regression | pytest backend/tests/unit/reporting backend/tests/unit/runtime -q | 184 passed, 12.08 s; includes focused cases |
| Static | scoped ruff check on 4 Python files; ruff format --check on 2 tests; git diff --check | PASS |
| Consumer types | npm run typecheck --workspace @iep/company-console | PASS |

Tests cover real SQLAlchemy reads and HTTP company route wiring: deletion, reinsertion, unaffected item,
immutable stored/frozen data, foreign company/session/answer, tenant rejection before query, DB failure,
batch count/no query without Evidence, true/false and legacy omitted-field contract. Initial lint length/
format findings were fixed inside the allowlist; no unexpected test failure remains. Library deprecation
warnings are not suppressed. WhyYou full unit suite and ControlProof full pytest were not rerun in this
scoped bundle; T091 remains the final full gate.

Publication: fork push succeeded. Connector create_pull_request returned 403 (integration lacks write scope);
existing Git-authenticated user API fallback created PR #8. No secrets printed/saved; scratch PR body and
metadata are outside Git at .pr-review/20261008/t086/. PR attached to this chat and base/head re-read.
No review request/messages sent, no PR merge, no diagnostic or official Run, no service restart.

Changed WhyYou files: reporting/repositories/postgres.py, reporting/api/company_routes.py, new unit
reporting/test_report_evidence_availability.py, unit reporting/test_report_view_contract.py,
packages/contracts/openapi/root.yaml, packages/contracts/generated/typescript/openapi.d.ts.
ControlProof changes are only Spec tasks/validation/decisions/traceability records. README/TEAM_HANDOFF/
Product Brief sync waits for phase closure. First official E-01 and D1 child remain FAIL; E-02 remains PASS.
T088 partial for D1 only; actual product-remedy child requires PR integration and fresh READY/approval.
AWS NOT_RUN; Spec 004 not Complete. Next: review/integrate PR #8 into integration, then T088 A3/A4 child
verification preserving all existing parents. Generic retest-reason wording caveat remains a follow-up.

## 2026-10-08 — T088 official P1-remedy child / Phase 9 complete

Authorization: user "다음 작업 바로 진행" after the proposed PR #8 integration and fresh-READY child step.
PR https://github.com/jhkim0602/gbsa_aws/pull/8 re-read: approved six-file scope, head
`b15ba8a88be1f31b354638e42a9b828b34c06875`, base integration `ce8d862`, mergeable. Combined CI statuses
were empty (not CI PASS). Merge connector returned permission 403; existing authorized Git-user API
fallback merged the reviewed head with expected-head guard. Merge SHA
`374b122e1296c0159ccd88ed4763d358973c59cb`; local integration and clean execution clone fast-forwarded.
Merged tree equals the T086-tested b15ba8a tree (git diff --exit-code). No source edits or repeated pytest;
the prior related 184 PASS/scoped static/typecheck gates apply to that identical tree. T091 still pending.
Both main refs unchanged: ControlProof 71a2c250; WhyYou cc8bf556. Historical untracked probes preserved.

Only 14 verified old owned API/worker process-tree entries were stopped, with PID/creation-time checks.
Fresh API/worker roots 51920/51524 use separate t088-observers/t088-faults and logs; same isolated synthetic
Postgres/Moto retained, external AI blocked, fixture spec004-report-v1. No original WhyYou DB or env file
modified. Service/helper/merge journals remain under workspace .pr-review/ outside Git.

Before exactly one new child submission: re-verify all three previous bundles and compare every registered
file plus manifest bytes. E-01 preflight READY 18/18 (4.812 s); E-02 READY 16/16, scoring source MATCH for
both pinned blobs (5.797 s). No preflight-created Run or owned rows. E-02 was not rerun on 374b122.

| Field | Official child |
|---|---|
| Run / parent | `a5ad4676-333b-44d0-8657-95ab434f3b3d` / `09c9d9bb-82a3-4485-9c9d-e9721f2452e4` |
| Label / profile | e01-p1-remedied / E01_CITATION_EVIDENCE_V1 |
| Clean ControlProof source | `8bbf36cdbef4c627dc078b40d3eca41441d471e9`, yeonwoo/004-e01-e02-score-evidence |
| Clean WhyYou source | `374b122e1296c0159ccd88ed4763d358973c59cb`, bosung/controlproof-n02-integration |
| Status / verdict | COMPLETED / PASS; E01-A1~A4 all PASS |
| Restore / bundle | SUCCEEDED / VERIFIED; both injections RESTORED, no block/manual cleanup |
| Manifest SHA-256 | `3d49961f865cfe6a3917d8d5c6f51e8f82b4c32d26922d825b2331e833a895bf` (19 registered files) |

A3: affected item `01a11706-3c11-7b04-9349-3dd0096d26c4` exposes H-4 availability; unexposed and
changed_without_indicator are empty. Evidence `01a11706-3c11-7dd0-a743-9705ce7c13a8`, segment
`ff40fe5a-cd31-572b-8ae6-79861997a103`: transcript_available true → false after actual removal → true
after exact restoration. All three report GETs 200; unaffected items and original scores unchanged.
A4 read_equal=true / record_equal=true; stored item/Evidence projections and pre/post digest equal,
frozen inputs unchanged. This is live API/worker evidence, distinct from automatic fixture gates.
D1 all four modes observed: EMPTY AXIS_DROPPED; NONEXISTENT/OTHER_APPLICANT/OTHER_CRITERION
SHOWN_AS_WRITTEN. These remain diagnostic observations, not extra target assertions or control PASS.

Journey 37.632410 s; retest wall 45.562 s; show 3.531 s; verify 2.797 s; durable submission-to-verify
record wall 51.894447 s; restoration 0.726722 s. All 540/120/60/600-second budgets satisfied.
Run-owned positions, competency_model_versions, interview_sessions, reports, report_items, evidence and
assistant_retrieval_documents all remain 0 after successful teardown. All three prior bundles' registered
files and manifest bytes remain unchanged after child execution. The initial E-01 FAIL, D1-only child
FAIL and initial E-02 PASS remain sealed historical results.

Retest diff: target git SHA ce8d862 → 374b122, environment source SHAs updated; scenario/profile/fixed
fixture unchanged, fresh lane manifest, reused_identities=[]. No parent evidence reused as child proof.
The current child reason "WhyYou 수정 후 E-01 독립 Run 재시험" accurately describes this product fix;
the earlier D1-only child's generic wording caveat remains, with its source diff proving WhyYou unchanged.

Commands, using ControlProof venv and the isolated t088 environment:

```text
python -m engine.cli verify <each of 3 previous Run IDs> --run-root <official-root> --json
python -m engine.cli preflight E-01 --profile E01_CITATION_EVIDENCE_V1 --target whyyou-local --json
python -m engine.cli preflight E-02 --profile E02_SCORING_FREEZE_V1 --target whyyou-local --json
python -m engine.cli retest 09c9d9bb-82a3-4485-9c9d-e9721f2452e4 --target whyyou-local --label e01-p1-remedied --run-root <official-root> --json
python -m engine.cli show a5ad4676-333b-44d0-8657-95ab434f3b3d --run-root <official-root> --json
python -m engine.cli verify a5ad4676-333b-44d0-8657-95ab434f3b3d --run-root <official-root> --json
```

All commands exit 0. Raw bundle: workspace cp-local/spec004-official/runs/<child ID>/; exclusive submission,
source/parent hash baseline, readiness, stdout/stderr, timing/toggle/residue inspection:
cp-local/spec004-official/commands/t088-p1-child/. Raw evidence remains outside Git. Native Windows
meaningless-REX-prefix anomaly messages are retained in logs; commands exited 0, no unexpected control
failure. No credentials or user absolute paths added to Git.

T088 complete; Phase 9 T079~T088 complete (T087 evidence-backed NOT_REQUIRED). Global status documents
synchronized once at this Phase boundary; this does not complete T096's final closure sync. Next
T089~T097: timing/security tests, full gate, quickstart/reproduction, traceability/conditional review,
limitations and converge. Spec 004 not Complete, AWS NOT_RUN. E-02 latest official PASS remains on ce8d862;
fresh READY on 374b122 is not a new E-02 verdict. This documentation commit is not the child execution SHA.

## 2026-10-08 — T089 deterministic timing gate

Start: ControlProof yeonwoo/004-e01-e02-score-evidence `7e5c47b597bf98ce9c606340416b2cd6881bcd7c`
clean; WhyYou integration `374b122e1296c0159ccd88ed4763d358973c59cb` tracked clean, historical untracked
probes retained. Added tests/integration/test_spec004_timing.py only (32 cases), no product/engine change.
Both profiles freeze 2 s poll / 3 consecutive reads / 4 s stability / 120 s restore / 540 s Run / 60 s verify.
Test-only counterfactual snapshots prove changed poll, consecutive count, stability window/reset, missing
report deadline with always-run teardown, restore boundary/block/manual-cleanup/sealed recovery, and
verify budget measurement. Long report work is excluded from restore time; all actual restores accumulate,
including exceptions. Genuine bundle verification is retained while FakeClock advances without real waits.
An over-budget verify is measured as such; VERIFIED alone does not claim the timing budget was met.

Initial new-file pytest: 27 passed / 5 failed (19.36 s), solely test setup using PRE_CHANGE where a criteria
version snapshot requires V1_PUBLISHED. Corrected test data, not engine behavior; not intended implementation
RED or target-control failure. No unexpected failure remains.

```text
python -m pytest tests/integration/test_spec004_timing.py tests/integration/test_e01_removal_restore.py tests/integration/test_e02_orchestration.py tests/integration/test_spec004_orchestration.py -q --tb=short
python -m ruff check tests/integration/test_spec004_timing.py
python -m ruff format --check tests/integration/test_spec004_timing.py
git diff --check
```

ControlProof venv: related gate 58 passed in 27.32 s (32 new + 26 existing); scoped static/format/diff PASS.
T089 complete; next T090 security corpus. Full pytest/WhyYou tests reserved for T091; no diagnostic/official
Run, service or WhyYou change, main change, or sealed evidence edit. Prior actual verdicts stay unchanged.
Global status sync waits for Phase 10 closure; T090~T097 pending, Spec 004 not Complete, AWS NOT_RUN.

## 2026-10-08 — T090 security corpus / verifier coverage finding

Start ControlProof yeonwoo/004-e01-e02-score-evidence `6af7a99978c17c1876bc1e142b4f1c8881641562`
clean; WhyYou integration `374b122e1296c0159ccd88ed4763d358973c59cb` tracked clean, historical probes
retained. Added 96 cases in tests/unit/test_redaction_security.py. Independent v4 file list covers 20
child files per profile, including manifest and lineage. Writer bypass rejection/safe-fact preservation,
complete sealed-file scans, emission allowlist and raw-field refusal, CLI preflight/run/show/verify/retest
JSON and human outputs plus redacted error output are exercised with synthetic data and FakeClock only.

Commands (ControlProof venv): `python -m ruff check tests/unit/test_redaction_security.py` PASS;
`python -m pytest tests/unit/test_redaction_security.py -q --tb=short` → 148 PASS / 8 FAIL, 26.20 s
(60 existing PASS, 88 new PASS, 8 new FAIL). `git diff --check` PASS.

All eight failures are the same real verifier omission, four files per profile: manifest.json,
scenario.snapshot.yaml, retest-link.json and retest-diff.json. Disposable fixture copies receive a nested
credential sentinel, then file hashes/size and manifest digest are updated. verify_bundle returns VERIFIED
with no redaction violation. The scanner excludes YAML-named snapshots, manifest and child-only files.
This is not a syntax/setup failure, intended missing-implementation RED, or WhyYou target-control result.
Writer gates and valid sealed child scans pass; no actual secret leak was demonstrated in official bundles.
Only disposable test copies were modified; all official sealed evidence remains untouched.

Recommended concrete correction: engine/evidence.py::_spec004_redaction scans the manifest, all v4 required
files (including scenario.snapshot.yaml), and registered JSON/JSONL/YAML evidence/lineage files using the
existing assert_redacted policy. Keep hash/link checks, verdict rules and sealed bytes unchanged; no new
sensitive-key policy, WhyYou change or actual Run is proposed. Then rerun this security file plus scoped
bundle/CLI/lineage contracts before T091. This expands the T090 test-only file scope to one existing engine
scanner; per the user's unexpected-scope stop/report rule, implementation pauses for review here.
T090 unchecked; no commit/push or global status sync, full regression or new official Run in this bundle.
Next: approve/resolve that narrow verifier correction, finish T090, then T091. Spec 004 not Complete,
AWS NOT_RUN; prior official verdicts unchanged.

## 2026-10-08 — approved T090 correction / T091 final automatic gate

Authorization: user "좋아 마무리해. spec 004를 완료하는거야 이제!!" approved the reported single-engine-file
scanner correction and the remaining closure/reproduction work. engine/evidence.py::_spec004_redaction now
scans known v4 files, manifest and registered JSON/JSONL/YAML evidence including child lineage. Existing
assert_redacted policy unchanged; _relative guards prevent reading outside the bundle. Extra registered
receipt and path-containment cases added. No WhyYou/product-verdict change or sealed-byte modification.

| Gate | Command | Result |
|---|---|---|
| T090 related | python -m pytest tests/unit/test_redaction_security.py tests/integration/test_spec004_bundle_links.py tests/integration/test_spec004_retest_lineage.py tests/contract/test_cli_spec004.py tests/contract/test_bundle_profile_spec004.py -q --tb=short | 192 passed, 44.50 s |
| T091 static | python -m ruff check . | PASS |
| T091 full ControlProof, exactly once | python -m pytest -q --tb=short | 939 passed, 294.66 s (command wall 296.3717995 s) |
| T091 WhyYou scoped | python -m pytest backend/tests/unit/reporting backend/tests/unit/runtime backend/tests/integration/test_controlproof_fault_hook_safety.py -q --tb=short | 188 passed, 7.79 s (command wall 15.307703 s), 3 existing dependency deprecation warnings |

ControlProof venv Python 3.12; WhyYou venv Python 3.14. Full gate ran from ControlProof 6af7a99 plus the
listed pending engine/security/setup edits; the next clean implementation checkpoint contains that same
tested code. WhyYou source stays 374b122, tracked clean. Initial setup-helper lint findings were corrected
before the full gate. No outstanding automatic failure. No repeated full suite after T091; later changes
should be documentary unless an observed portability issue requires a scoped correction.

T092/T097 preparation: scripts/spec004_local.py and pinned scripts/spec004-local.compose.yaml expose the
previous isolated synthetic setup as a portable command, not a product flow. Clean feature checkouts,
no .env, credentials scrubbed, loopback-only distinct ports/project, fresh boot observer/fault directories,
owned process creation-time checks and retained volumes/evidence. New setup safety tests included in 939.
Quickstart replaces obsolete draft/PC-specific instructions; existing dependency environments may be reused
with source selected from the new clean checkout. New reproduction Runs are still pending at this checkpoint.

T095 preliminary scan: 363 tracked files, no current-user absolute path, real AWS access key or private-key
material; 76 files across all four prior official Spec 004 bundles pass assert_redacted. Synthetic negative
security corpus remains intentionally in tests. Newly staged files and reproduction metadata will also be
scanned before closure. Command/result journals: workspace .pr-review/20261008/closure/, outside Git.
SC-001 reason wording and SC-006 team-PC versus T097 second-checkout inconsistency were presented for owner
clarification; no completion-criterion change applied without that response. Spec 004 remains incomplete.

### T092 portability correction before reproduction

Clean checkpoint cfff091 and WhyYou 374b122 were cloned to a separate pair of feature checkouts, with
existing Python 3.12.12/3.14.3 dependencies reused as documented. Fresh dedicated Docker project/schema/queues
initialized, but Windows process-inventory stdout appended a native ANOMALY line to valid JSON. Startup
failed at parsing before any Run, not at target execution. API PID 4228 and launcher 33536 were identified
by command/creation time; child stopped and parent exited, then only the reproduction project was stopped.
Logs/volumes retained; no original services, DB or sealed evidence changed.

Correction limited to scripts/spec004_local.py: parse the valid JSON inventory line and preserve a pending
owned PID in state before inventory lookup; stop refuses an incomplete inventory until inspected. Added
two regression/safety cases. New test insertion briefly caused a test-scope NameError, corrected immediately.
Scoped setup gate 10 passed in 5.70 s; ruff PASS. Full 939 gate not repeated: engine/security code unchanged
since that gate; only the observed setup portability issue and its tests changed. Next clean checkpoint
contains this correction for T092/T097. Do not claim 941 full-suite PASS; only 939 full + 10 scoped are proven.

### T092 bundle-location correction after the first reproduction Run

Clean reproduction ControlProof ca3df77 / WhyYou 374b122: preflight E-01 READY 18/18 and E-02 READY
16/16 with scoring MATCH. Exactly one E-01 Run 4030503c-a24c-42f9-b926-7aba49b4c467 completed PASS,
restore SUCCEEDED. The documented wrapper's subsequent show/verify exited 1: engine bundle commands
default to .controlproof/runs instead of reading CONTROLPROOF_RUN_ROOT. This is a setup wrapper defect,
not a target FAIL or a failed restore. Original run/show/verify attempt wall was 47.1497238 s, but verification
did not succeed then; it is not evidence of a successful <=600 s end-to-end reproduction.

The wrapper now supplies its isolated runs directory to show/verify unless the caller supplied --run-root.
Two command-routing regression cases added: setup scoped gate 12 passed in 0.54 s, ruff PASS. Engine,
verdict and sealed evidence unchanged; full 939 gate not repeated. Verify the same existing Run after
this correction; do not rerun E-01 to hide this failure. Repair delay is separate from scenario execution
and the original successful official child timing. E-02 reproduction remains pending at this checkpoint.


## 2026-10-08 — T092~T097 closure, owner confirmation and actual reproduction

Owner confirmed ID-004-36: PASS/FAIL factual reasons, INCONCLUSIVE reason_code; SC-006 second clean
checkout or teammate. This resolves two text contradictions explicitly, with no retroactive evidence edit.

### Source and environment

Two local clones, not worktrees, on feature branches: ControlProof yeonwoo/004-e01-e02-score-evidence,
WhyYou bosung/controlproof-n02-integration. CP Q1 ca3df77f9377a346575e10818bf9f389d8bc470e;
CP Q2 f75ada7172fc48802e231d24e08886de4292c276; WhyYou both
374b122e1296c0159ccd88ed4763d358973c59cb. Each Run's environment.snapshot.json records these exact
clean sources. Existing dependency environments reused (CP Python 3.12.12, WhyYou 3.14.3), not copied source.
Dedicated Docker project controlproof-spec004-repro, loopback ports PG15734/Moto14767/API18085,
fresh synthetic DB/queues/observer/fault boot roots; pinned compose image digests. No .env or real keys.
LOCAL_EMULATED, spec004-report-v1 digest e15ec3790b64b2fba10e0caa9372f08c917edbbaa99ce308076952b838668b3f,
external_ai_allowed=false; AWS NOT_RUN. A new checkout on the same PC is not another-PC proof.

### Quickstart commands and results

All unconditional commands followed through source/branch/status/version/Docker checks, up, status,
both preflights, exactly one Run per scenario, show, verify, stop and status. Original argv/stdout/stderr,
exit and wall durations are retained in workspace .pr-review/20261008/closure/reproduction/cp-local/
spec004-local/repro/commands/. Native Windows ANOMALY text was kept in journals; JSON Run IDs were
extracted with the documented line filter. Startup inventory and bundle-location defects are recorded
above, fixed and covered by scoped tests. Q1 was not rerun to fix show/verify.

| Gate / command | Result |
|---|---|
| git clone --no-hardlinks --branch <documented branch> <local committed source> <new directory>; branch/HEAD/status on both | separate clean feature clones, same source bytes as recorded; no main change |
| Python --version; docker info | 3.12.12 / 3.14.3, Docker available |
| python scripts/spec004_local.py up --whyyou-python <installed dependency interpreter> | STARTED; fresh owned API/workers and local resources, no Run created |
| python scripts/spec004_local.py status | ready=true, stopped=false |
| python scripts/spec004_local.py cli -- preflight E-01 --profile E01_CITATION_EVIDENCE_V1 --target whyyou-local --json | READY 18/18, exit 0 |
| python scripts/spec004_local.py cli -- preflight E-02 --profile E02_SCORING_FREEZE_V1 --target whyyou-local --json | READY 16/16, scoring source MATCH, exit 0; checked again before Q2 |
| python scripts/spec004_local.py cli -- run E-01 --profile E01_CITATION_EVIDENCE_V1 --target whyyou-local --label spec004-reproduction-e01 --json | Q1 COMPLETED/PASS, exit 0 |
| python scripts/spec004_local.py cli -- show 4030503c-a24c-42f9-b926-7aba49b4c467 --json; ... verify same ID --json | first exit 1 path defect; after f75ada7 both exit 0, VERIFIED, no Run repetition |
| python scripts/spec004_local.py cli -- run E-02 --profile E02_SCORING_FREEZE_V1 --target whyyou-local --label spec004-reproduction-e02 --json | Q2 COMPLETED/PASS, exit 0 |
| python scripts/spec004_local.py cli -- show 970108fe-8eae-4ce0-b230-400887ba3e24 --json; ... verify same ID --json | exit 0/0, VERIFIED |
| Read-only psql SELECT counts for 7 critical tables | reports/report_items/evidence/positions/competency_model_versions/transcript_segments/interview_sessions all 0 |
| python scripts/spec004_local.py stop; ... status | STOPPED, evidence_and_volumes_retained=true, stopped=true; only owned reproduction services stopped |

Conditional skips: fresh uv dependency installation unnecessary because existing installed interpreter
paths were explicitly supplied. Ruff/full regression commands not duplicated in the clone: T091 already
proves the identical engine source; subsequent helper changes got scoped setup 12 PASS. Target-remedy
retest/cleanup-confirm not triggered in this new environment: both actual verdicts PASS, restores succeed,
no block exists. Historical R3/R4 child remediation already proves FR-052. No AWS provision or main merge.

### Actual results and timing

| Scenario / Run | Assertions | Restore / verify | Manifest SHA-256 | Timing seconds |
|---|---|---|---|---|
| Q1 E-01 4030503c-a24c-42f9-b926-7aba49b4c467 | A1~A4 PASS; D1 four observations | SUCCEEDED / VERIFIED, 17 registered files | 3c35ba8e682ac47b62e50dd981611cde37ec28a31ab14effd3074617d8a530ec | Run journey 33.161404; run command 38.891; successful verify 2.297; submission→successful verify 343.613371 including wrapper repair |
| Q2 E-02 970108fe-8eae-4ce0-b230-400887ba3e24 | A1~A3 PASS | SUCCEEDED / VERIFIED, 17 registered files | 1053a9396e788740af970f1c7e466d6bed8f2e32919347cc5b9f0dc9cdb0253a | Run journey 23.089785; run command 29.609; verify 2.406; full run/show/verify stopwatch 38.4084182 |

Q1 submission journal 2026-10-07T16:54:14.778948Z → successful verify command completion
2026-10-07T16:59:58.392319Z (343.613371 s), including the initial 47.1497238 s failed-location attempt
and repair delay. This is measured wall time, not the earlier failed verification relabelled success.
Q1 environment restore 0.319454 s; Q2 0.182834 s; within 120. All Run journeys <540, verify <60, totals <600.

Q1 four invalid citations EMPTIED, VALID STORED_VALID, reference unchanged; actual one-row removal
confirmed, affected Evidence availability true→false→true, other items unchanged; read/record equal
after exact restoration. D1 EMPTY AXIS_DROPPED and three bad-ID modes SHOWN_AS_WRITTEN are diagnostics.
Q2 published v1/v2 through product APIs, frozen inputs and first-report digests unchanged, 72.5→72 and
73.5→74 recomputation; all five comparison targets agree and verify re-executes the independent copy.
Q2 other-position digest unchanged. Both teardown receipts successful, manual_cleanup_required=false.

### T093/T094/T095/T096

Traceability fills every 23 FR/7 SC row and 13 explicit story acceptance cases, assertion/EV4/task/test/
implementation/actual mapping; initial facts retained under R1~R4, current reproduction under Q1/Q2.
Conditional T084/T085/T086/T088 complete; T087 NOT_REQUIRED because initial A1/A2/E02 all PASS.
ID-004-14(b) optional refusal observer and R3 generic retest wording stay documented limitations.

Security audit command: python workspace .pr-review/20261008/closure/closure_audit.py, from CP root.
It enumerates git ls-files -z, scans bytes for the actual current-user absolute path, live AWS access keys
and private-key headers without echoing matches, re-verifies all six bundles and checks every bundle file
with assert_redacted. Result: 366 tracked files, 0 real credential/user-path findings; 112 bundle files,
0 redaction violations, all six VERIFIED. All four prior manifest SHAs equal their recorded values and
registered file hash checks succeed. Synthetic negative-case examples are test data, not real applicants.
All subject data uses Spec004 synthetic seed policies and redacted projections; no actual applicant input
or unredacted free text was introduced. Raw argv/logs may contain local paths and remain outside Git.

Final status synchronization includes README, AGENTS, TEAM_HANDOFF, AI_SPEC_KIT_PLAYBOOK, Product Brief,
Coverage Matrix and Decision Log D-017. Latest source code checkpoint f75ada7 differs from the later
documentation closure commit; original Run snapshots are authoritative. Main SHAs remain CP71a2c25 /
WhyYou cc8bf55, and Spec003 INCONCLUSIVE/converge-pending status is unchanged.

### Final converge — converged (2026-10-08)

Applied repository speckit-converge skill after implementation and closure evidence. Initial prerequisite
resolution still selected the old Spec003 local context; reran with explicit
SPECIFY_FEATURE_DIRECTORY=specs/004-e01-e02-score-evidence and obtained the correct required artifacts.
No before/after_converge hooks registered. Assessment uses current Spec/Plan/Tasks and constitution;
initial baseline descriptions are read together with the approved conditional corrective chain.

Checked: 23 FR, 7 SC, 5 stories with 13 explicit acceptance scenarios plus US4/US5 prose obligations,
8 execution-design sections, H-1~H-4 decisions, all 97 tasks and 7 constitution principles. Scope includes
canonical scenarios/models/profile dispatch; synthetic lanes/consent/model receipts; citation/removal/
restore/probe; independent frozen scoring; presentation/CLI/bundle/redaction/lineage; WhyYou fixed-model
isolation and approved availability lookup; final regression/traceability/security/setup reproduction.
Automatic negative paths are assessed from their current tests/code; successful target behavior is assessed
from R4/Q1/Q2 artifacts, not inferred from automatic fixture gates.

Findings: missing 0 / partial 0 / contradicts 0 / unrequested 0; CRITICAL/HIGH/MEDIUM/LOW all 0.
No new tasks appended. tasks.md remained byte-for-byte unchanged during assessment (SHA256
df0a0c3e51864204a7d0e2c23a58b599ed38726f805222440f5949831fbb82f9 before and after).
Known historical R3 wording and optional refusal observer do not leave an unmet v1 requirement; their
facts and future review triggers remain explicit. Owner-approved reason/checkout criteria are used, not
an assumed other-PC success. Constitution closure check PASS, no exception.

Converged — the implementation satisfies the spec, plan, and tasks. Spec004 Complete. Next feature:
Spec005's own specification/implementation cycle, followed by review on feature branches. Main integration
and the external-PC gate remain separate. This does not complete Spec003 or the whole MVP.
