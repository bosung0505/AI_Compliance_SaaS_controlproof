# Spec 004 Validation

## Current status

- Workflow stage: Implement started. Phase 1 (T001~T004) done; Phase 2 failing tests (T005~T011) written and
  confirmed RED for the intended reasons; Phase 2 implementation (T012~T021) not started.
- WhyYou local/test fixture (Phase 3, T022~T029): PR jhkim0602/gbsa_aws#6 reviewed, fixed and merged into `bosung/controlproof-n02-integration` at `42aaaba206ced4288c8ee477b73f5f1ccf078bf3`; main unchanged.
- Sandbox diagnostics: none. Actual E-01/E-02 Runs: none (`NOT_RUN`).
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

## Sandbox diagnostics

(none yet — Phase 8)

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

## 세션 인계 (2026-10-07, 자율 진행 세션)

- 마지막 완료: Phase 7 US4 T061~T069. 결정 ID-004-24~26.
- WhyYou: PR #6 병합(`42aaaba`), 로컬 `bosung/controlproof-n02-integration` = `42aaaba`, clean. WhyYou 변경 없음.
- 진행 중: 없음.
- 건너뛴 PROPOSED: 없음. ID-004-14(observer에 Spec 004 lane 추가)는 비차단 제안.
- 다음 작업: Phase 8 T070(retest 실패 시험) → T071. T072 이후 sandbox 진단은 이번 범위 밖.
