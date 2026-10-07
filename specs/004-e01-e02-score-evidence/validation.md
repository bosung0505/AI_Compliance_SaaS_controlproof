# Spec 004 Validation

## Current status

- Workflow stage: Implement started. Phase 1 (T001~T004) done; Phase 2 failing tests (T005~T011) written and
  confirmed RED for the intended reasons; Phase 2 implementation (T012~T021) not started.
- WhyYou local/test fixture (Phase 3, T022~T029): done; PR jhkim0602/gbsa_aws#6 open.
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
| WhyYou fixture | T022~T029 | see below | PASS (PR open) | — |

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
  `e01-1-valid` … `e01-5-other-criterion`), emission receipts, citation cases, report records/reads, change
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

## Sandbox diagnostics

(none yet — Phase 8)

## Actual Run ledger

(none yet — Phase 9; requires preflight READY and explicit approval)
