# Spec 003 Validation

## Current status

- Workflow stage: `$speckit-implement` in progress
- Automated implementation gates: US1~US4 T001~T073 `PASS`; US5 retest contract T074~T076 scoped gate `PASS` (35 relevant tests). The Phase 6 full ControlProof regression was 407 passed. These are fixture results, not a WhyYou verdict.
- WhyYou actual N-02 preflight: `READY` on 2026-10-02 after Docker restart and process-local Git trust configuration
- Initial actual Run: `15cef078-ee24-4f0e-91ef-381e0f7a1cc2`; `RESTORE_FAILED` / `INCONCLUSIVE`; sealed bundle `VERIFIED`
- Child retest: `BLOCKED_RESTORE_FAILED`; the initial Run has direct FAIL facts and requires cleanup/root-cause review first
- AWS: `NOT_RUN`
- Claim scope: `EXECUTED_SCENARIO_AND_EVIDENCE_ONLY`

This file is chronological. Do not replace a failed or inconclusive result with a
later result; append a new entry and link it to the original Run.

## Source baseline

| Repository | Branch | Baseline SHA | Working-tree note |
|---|---|---|---|
| ControlProof | `003-n02-consent-order` | `c27f9d651ef5c59d8599b077c9613862b9eb2598` | Spec 003 documents were uncommitted when implementation began |
| WhyYou | `bosung/controlproof-n02-integration` | `511ae9e2cae66b8d0ce31e8851537ed27ac6dd0c` | Created from `bosung/controlproof-h03-integration` before N-02 changes |

The final implementation and actual-Run entries must record the then-current clean,
committed SHAs again. The baseline above is not an actual-Run source claim.

Phase 6 local checkpoint (2026-10-02): ControlProof `003-n02-consent-order` HEAD
`5e077c9738ddb614f9e0a198415124a1b0b8f3ec` with uncommitted US4 changes;
WhyYou `bosung/controlproof-n02-integration` HEAD
`94ad7f2caa0083d3d029b4b7726ee9b34c48eb21` with a clean working tree.
These are implementation checkpoint SHAs, not an actual-Run source claim.

## Gate ledger

| Gate | Tasks | Command | Result | Duration |
|---|---|---|---|---|
| Setup | T001~T004 | recorded below | PASS | < 1 minute |
| Foundation | T005~T023 | recorded below | PASS | 3 minutes 45 seconds |
| US1 bypass/effects | T024~T040 | scoped pytest + full ControlProof regression + scoped Ruff | PASS | 2 minutes 54 seconds full regression; scoped gates < 2 seconds |
| US2 normal order | T041~T051 | scoped pytest + full ControlProof regression + WhyYou transaction test + scoped Ruff | PASS | 2 minutes 53 seconds full regression; scoped gates < 14 seconds |
| US3 fault/recovery | T052~T064 | scoped pytest + full ControlProof regression + scoped WhyYou rollback/fault regression + Ruff | PASS | 2 minutes 47 seconds full regression; scoped gates < 12 seconds |
| US4 tests first | T065~T068 | four scoped test files; commands below | EXPECTED RED; 25 failed, 11 passed | 9.48 seconds |
| US4 partial implementation | T069/T071 | N-02 presentation, CLI fixture projection and EV3 verifier selection | PASS; 33 passed | 10.40 seconds |
| US4 review/bundle | T065~T073 | selected US4/EV3 pytest, scoped CLI/orchestration pytest, Ruff, full ControlProof pytest | PASS; 42 scoped and 407 full | 14.00 seconds scoped; 179.22 seconds full |
| US5 immutable retest | T074~T076 | N-02 test-first RED, N-02 child/CLI scoped pytest and existing H-03/E-03 retest/EV3 contracts | PASS; 6 N-02 and 35 relevant tests | 13.85 seconds N-02; 48.79 seconds relevant |
| Initial actual truth | T077~T079 | clean-source preflight, one initial actual Run, show/verify, source/result mapping | READY preflight; Run `RESTORE_FAILED` / `INCONCLUSIVE`; bundle VERIFIED | Run 5.70 seconds; show/verify command 6.87 seconds |
| Conditional remediation | T080~T084 | parent artifact `15cef078-ee24-4f0e-91ef-381e0f7a1cc2` | PENDING_CLASSIFICATION; child blocked by restore failure | — |
| Closure | T085~T093 | `NOT_RUN` | `NOT_RUN` | — |

## Implementation command log

Append exact commands, exit codes, counts, durations and relevant non-sensitive
output. A test name in this table does not mean that an actual WhyYou Run occurred.

| Timestamp | Tasks | Repository | Command | Result |
|---|---|---|---|---|
| 2026-10-01 | T001~T004 | ControlProof | `python -m ruff check tests/fixtures/spec003.py` | PASS |
| 2026-10-01 | T001~T004 | ControlProof | Import and deterministic fixture assertions | `spec003-fixtures-ok` |
| 2026-10-01 | T001~T004 | Both | `git diff --check` | PASS; only existing LF→CRLF warnings |
| 2026-10-01 | T005~T012 | ControlProof | Selected Spec 003 foundation tests | EXPECTED RED; missing N-02 models/executor/profile imports |
| 2026-10-01 | T010 | WhyYou | `python -m pytest backend/tests/unit/runtime/test_controlproof_consent.py -q` | EXPECTED RED; missing `runtime.controlproof_consent` |
| 2026-10-01 | T005~T023 | ControlProof | Selected foundation tests | PASS; 63 passed in 7.28s |
| 2026-10-01 | T012/T023 | ControlProof | `python -m pytest -q` | PASS; 304 passed in 172.02s (before one additional fake-adapter contract test, which passed in the 63-test foundation gate) |
| 2026-10-01 | T010/T020~T023 | WhyYou | `python -m pytest tests/unit/runtime -q` | PASS; 28 passed, 1 third-party deprecation warning |
| 2026-10-01 | T013~T023 | Both | Scoped Ruff checks and `git diff --check` | PASS; only line-ending warnings |
| 2026-10-01 | T022 | WhyYou | Parse `compose.yaml` and assert bounded control extensions | PASS; `compose-controls-ok` |
| 2026-10-01 | T024~T029 | ControlProof | US1 tests before implementation | EXPECTED RED; `n02_seed`, protected-processing adapter and A1~A4 judge symbols/scenario were absent |
| 2026-10-01 | T026 | WhyYou | N-02 observer integration tests before wiring | EXPECTED RED; 3 failed because handler/session observer boundaries and runtime port were not wired |
| 2026-10-01 | T024~T040 | ControlProof | `python -m pytest tests/contract/test_n02_seed_adapter.py tests/contract/test_n02_processing_adapter.py tests/unit/test_judge_n02_bypass.py tests/integration/test_n02_bypass_orchestration.py tests/integration/test_n02_lane_isolation.py -q` | PASS; 17 passed in 1.09s |
| 2026-10-01 | T026/T034~T035 | WhyYou | `python -m pytest backend/tests/unit/runtime/test_controlproof_n02_observer.py backend/tests/integration/interview_engine/test_controlproof_n02_observer.py -q` | PASS; 12 passed in 0.11s; one pytest-asyncio deprecation warning |
| 2026-10-01 | T034~T035 | WhyYou | Observer + existing analysis/report-fault regression selection | PASS; 24 passed in 1.28s; one pytest-asyncio deprecation warning |
| 2026-10-01 | T024~T040 | ControlProof | `python -m pytest -q` | PASS; 322 passed in 133.88s |
| 2026-10-01 | T024~T040 | Both | Scoped Ruff checks | PASS |
| 2026-10-01 | T024~T040 | ControlProof | Final `python -m pytest -q` after documentation and adapter projection refinements | PASS; 322 passed in 173.80s |
| 2026-10-01 | T026/T034~T035 | WhyYou | `python -m pytest backend/tests/unit/runtime -q` | PASS; 37 passed in 0.76s; one pytest-asyncio deprecation warning |
| 2026-10-01 | T041~T050 | ControlProof | `python -m pytest tests/contract/test_n02_consent_adapter.py tests/contract/test_n02_causality_adapter.py tests/integration/test_n02_normal_order.py tests/unit/test_judge_n02_order.py -q` | PASS; 22 passed in 1.09s |
| 2026-10-01 | T043 | WhyYou | `python -m pytest tests/integration/company_management/test_controlproof_n02_consent_transaction.py -q` from `backend/` | PASS; 1 passed in 3.68s; one pytest-asyncio deprecation warning |
| 2026-10-01 | T043 | WhyYou | Consent transaction test plus existing N-02 fault/observer selection | PASS; 22 passed in 3.56s; one pytest-asyncio deprecation warning |
| 2026-10-01 | T041~T051 | ControlProof | Composition, readiness, consent, causality, journey and A5 judge selection | PASS; 31 passed in 1.33s |
| 2026-10-01 | T041~T051 | ControlProof | `python -m pytest -q` | PASS; 345 passed in 173.01s |
| 2026-10-01 | T041~T051 | Both | Scoped Ruff checks | PASS |
| 2026-10-01 | T052~T064 | ControlProof | Fault adapter, A6/A7 judge, restore safety, complete recovery journey, composition and readiness selection | PASS; 38 passed in 2.18s |
| 2026-10-01 | T053~T054/T058 | WhyYou | Consent fault unit, rollback and transaction tests | PASS; 17 passed in 2.03s; one pytest-asyncio deprecation warning |
| 2026-10-01 | T052~T064 | WhyYou | Runtime safety plus consent transaction/rollback, N-02 observer, worker delivery and local queue regression selection | PASS; 88 passed in 7.55s; one pytest-asyncio deprecation warning |
| 2026-10-01 | T052~T064 | ControlProof | `python -m ruff check .` | PASS |
| 2026-10-01 | T052~T064 | ControlProof | `python -m pytest -q` | PASS; 366 passed in 167.35s |
| 2026-10-02 | T065~T068 | ControlProof | `.\.venv\Scripts\python.exe -m pytest tests/integration/test_n02_verdict_matrix.py tests/contract/test_presentation_spec003.py tests/contract/test_cli_n02.py tests/integration/test_n02_bundle_links.py -q --tb=short` | EXPECTED RED; 25 failed, 11 passed in 9.48s. Missing combined `judge_n02_run`, N-02 review/path projection, and semantic EV3 cross-reference/readability/redaction verification; no collection, syntax, or fixture setup error. |
| 2026-10-02 | T065~T068 | ControlProof | `.\.venv\Scripts\python.exe -m pytest tests/contract/test_bundle_profile_spec003.py tests/contract/test_cli_n02_profile.py tests/contract/test_presentation_spec002.py -q` | PASS; 6 passed in 2.23s. Existing profile, preflight and presentation contracts remain intact. |
| 2026-10-02 | T065~T068 | ControlProof | `.\.venv\Scripts\python.exe -m ruff check tests/integration/test_n02_verdict_matrix.py tests/contract/test_presentation_spec003.py tests/contract/test_cli_n02.py tests/integration/test_n02_bundle_links.py tests/fixtures/n02_review_bundle.py` | PASS. |
| 2026-10-02 | T069/T071 | ControlProof | `.\.venv\Scripts\python.exe -m pytest tests/integration/test_n02_bundle_links.py tests/contract/test_bundle_profile_spec003.py tests/contract/test_cli_n02.py tests/contract/test_presentation_spec003.py tests/contract/test_presentation_spec002.py tests/contract/test_cli_n02_profile.py -q --tb=short` | PASS; 33 passed in 10.40s. The corrected CLI fixture tests a false PASS with unreadable facts; an empty INCONCLUSIVE bundle remains VERIFIED. |
| 2026-10-02 | T069/T071 | ControlProof | `.\.venv\Scripts\python.exe -m pytest tests/contract/test_bundle_profile_spec002.py tests/contract/test_bundle_contract.py tests/contract/test_cli_profiles_v2.py tests/contract/test_cli_review.py -q --tb=short` | PASS; 12 passed in 11.36s. |
| 2026-10-02 | T069/T071 | ControlProof | `.\.venv\Scripts\python.exe -m ruff check engine/evidence.py engine/presentation.py tests/integration/test_n02_bundle_links.py tests/contract/test_cli_n02.py` | PASS. |
| 2026-10-02 | T070/T072/T073 | ControlProof | `.\.venv\Scripts\python.exe -m pytest -q tests/integration/test_n02_verdict_matrix.py tests/contract/test_presentation_spec003.py tests/contract/test_cli_n02.py tests/integration/test_n02_bundle_links.py tests/integration/test_n02_orchestration.py tests/contract/test_bundle_profile_spec003.py` | PASS; 42 passed in 14.00s. |
| 2026-10-02 | T070/T072/T073 | ControlProof | `.\.venv\Scripts\python.exe -m pytest -q tests/integration/test_n02_orchestration.py tests/contract/test_cli_n02.py` | PASS; 8 passed in 5.75s after exception cleanup hardening. |
| 2026-10-02 | T070/T072/T073 | ControlProof | `.\.venv\Scripts\python.exe -m ruff check .` | PASS; all checks passed. |
| 2026-10-02 | T070/T072/T073 | ControlProof | `.\.venv\Scripts\python.exe -m pytest -q` | PASS; 407 passed in 179.22s. Phase 6 full regression executed once. |
| 2026-10-02 | T070/T072/T073 | ControlProof | `git diff --check` | PASS; only LF→CRLF working-copy warnings. |
| 2026-10-02 | T072 | ControlProof | `.\.venv\Scripts\python.exe -m pytest -q tests/integration/test_n02_orchestration.py tests/contract/test_cli_n02.py` | PASS; 8 passed in 6.21s after rechecking the restore block under the target lock. |
| 2026-10-02 | T074/T075 | ControlProof | `.\.venv\Scripts\python.exe -m pytest -q tests/integration/test_n02_retest_lineage.py tests/contract/test_n02_retest_bundle.py --tb=short` | EXPECTED RED; 3 failed in 5.11s because `prepare_retest` still required one Spec 001/002 subject for an N-02 six-lane parent. No syntax or collection failure. |
| 2026-10-02 | T074~T076 | ControlProof | `.\.venv\Scripts\python.exe -m pytest -q tests/integration/test_n02_retest_lineage.py tests/contract/test_n02_retest_bundle.py --tb=short` | PASS; 6 passed in 13.85s after N-02 child diff and CLI dispatch. |
| 2026-10-02 | T074~T076 | ControlProof | `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_retest.py tests/integration/test_h03_retest_lineage.py tests/integration/test_h03_retest_parent_pass.py tests/integration/test_spec002_retest_lineage.py tests/contract/test_cli_retest.py tests/integration/test_n02_retest_lineage.py tests/contract/test_n02_retest_bundle.py tests/contract/test_bundle_profile_spec003.py tests/integration/test_n02_bundle_links.py --tb=short` | PASS; 35 passed in 48.79s. |
| 2026-10-02 | T074~T076 | ControlProof | `.\.venv\Scripts\python.exe -m ruff check engine/retest.py engine/cli.py engine/executors/n02.py engine/evidence.py tests/integration/test_n02_retest_lineage.py tests/contract/test_n02_retest_bundle.py` | PASS. |
| 2026-10-02 | T074~T076 | ControlProof | `git diff --check` | PASS; only LF→CRLF working-copy warnings. |
| 2026-10-02 | T076 | ControlProof | `.\.venv\Scripts\python.exe -m pytest -q tests/integration/test_n02_retest_lineage.py tests/contract/test_n02_retest_bundle.py tests/integration/test_spec002_retest_lineage.py tests/contract/test_cli_retest.py --tb=short` | PASS; 9 passed in 21.41s after requiring the child environment snapshot to match the actual Run. |
| 2026-10-02 | T077 attempt | ControlProof/WhyYou | `git branch --show-current`, `git rev-parse HEAD`, `git status --short` | Both clean on personal branches: ControlProof `b2b1c5e553302f93552b8616ccf6c3374d1ae45c`; WhyYou `94ad7f2caa0083d3d029b4b7726ee9b34c48eb21`. These are preflight-attempt sources, not actual-Run sources. |
| 2026-10-02 | T077 attempt | Local environment | `docker desktop status`; `docker version --format '{{.Server.Version}}'`; local TCP checks on 8080/5432/4566 | Docker Desktop status unavailable; Docker API access denied in sandbox, and host-permission query did not return. API, PostgreSQL and LocalStack ports were closed. |
| 2026-10-02 | T077 attempt | ControlProof | `.\.venv\Scripts\python.exe -m engine.cli preflight N-02 --profile N02_CONSENT_ORDER_V1 --target whyou-local --json` with process-only local/test settings from WhyYou `.env` | No JSON or readiness result after about 6 minutes; interrupted while local services were unavailable. No new Run directory dated after the attempt; no actual Run was invoked. T077 was left unchecked at that point. |
| 2026-10-02 | T077 attempt | ControlProof | `.\.venv\Scripts\python.exe -m ruff check .`; `.\.venv\Scripts\python.exe -m ruff format --check .` | Ruff lint PASS; repository-wide format check FAIL on 76 files, including unchanged files. No broad reformat applied. |
| 2026-10-02 | T077 retry | WhyYou | `.\scripts\local.ps1 up`; `.\scripts\local.ps1 api`; `.\scripts\local.ps1 worker` | Docker 29.6.2; Postgres, LocalStack and Mailpit healthy; API `/health/ready` all dependencies `ok`; four workers running after host-permission launch. The sandbox-only worker launch could not write `C:\tmp\iep-worker-ready`. |
| 2026-10-02 | T077 retry | ControlProof | `.\.venv\Scripts\python.exe -m engine.cli preflight N-02 --profile N02_CONSENT_ORDER_V1 --target whyou-local --json` | `RUNNER_NOT_READY` (exit 1): isolated subprocess Git rejected WhyYou's ownership, leaving target/environment snapshots absent; 14 other capabilities READY. No Run created. |
| 2026-10-02 | T077 | ControlProof | Same preflight with corrected `--target whyyou-local` and process-only `safe.directory` entries for both repositories | READY (exit 0) at `2026-10-02T02:49:18.980136Z`: all 16 capabilities READY; WhyYou snapshot clean at `94ad7f2caa0083d3d029b4b7726ee9b34c48eb21`; model fixture `h03-report-v1` / `ce09b95403b34e1390502c90f5c5edc518ddf65d38c8ce881617a37cac6d16b1`; protected paths document, recording and AI assessment; AWS `NOT_RUN`. ControlProof clean at `b92b9ada48e82c5290d5b6eb99883e5dcc50f0ee`. Run directory count remained 23 before T078. The quickstart's misspelled target was corrected after the sealed Run; the configured and tested target is `whyyou-local`. |
| 2026-10-02 | T078 | ControlProof | `.\.venv\Scripts\python.exe -m engine.cli run N-02 --profile N02_CONSENT_ORDER_V1 --target whyyou-local --label n02-initial --json` | Exactly one initial actual Run; exit 6 in 5.70 seconds; `15cef078-ee24-4f0e-91ef-381e0f7a1cc2`, `RESTORE_FAILED` / `INCONCLUSIVE`. A1~A3 PASS; A4~A7 FAIL. No remediation or second Run. |
| 2026-10-02 | T078 | ControlProof | `.\.venv\Scripts\python.exe -m engine.cli show 15cef078-ee24-4f0e-91ef-381e0f7a1cc2 --json`; `.\.venv\Scripts\python.exe -m engine.cli verify 15cef078-ee24-4f0e-91ef-381e0f7a1cc2 --json`; `Get-FileHash ...\manifest.json -Algorithm SHA256` | show exit 0; verify exit 0, VERIFIED, 19 files checked, no missing/mismatched/unregistered files. Manifest SHA-256 `d2306f3cd6e2b15ce87d94e4844a2278c7ea3c0b3c052a2aac45e1bff8f2bc9b`. |

T070 uses the approved read-only preflight contract: protected path identities are shown before a Run, while actual path, policy and lane SHA-256 digests are captured only inside the Run and linked to the sealed bundle. Preflight creates no Run/subject/marker/event. The US4 deterministic fixture verifies six lanes seeded once, A1~A7 PASS, a direct Recording FAIL, and restore failure as RESTORE_FAILED/INCONCLUSIVE with a persistent block. Those fixture results remain separate from the actual WhyYou result below. No WhyYou source or product guard was changed before the first actual Run.

T074~T076 are a scoped synthetic child-Run gate. The child uses a fresh six-subject set, records target/path/policy/fixture differences in its own sealed bundle, and verifies the parent manifest and evidence bytes remain unchanged. An unresolved cleanup block or RESTORE_FAILED parent refuses retest. The approved implementation also needed N-02 dispatch and parent-link verification in CLI, executor and Evidence Bundle code. The actual parent now exists, but no actual child Run was executed; Phase 7 full regression remains pending.

An additional pre-existing WhyYou integration collection issue remains outside this
foundation gate: `tests/integration/test_production_runtime.py` imports the absent
`DeterministicSpeechToText` symbol from `shared.aws_clients.ports`. The failure occurs
before the changed runtime composition is imported and is not represented as a passing
N-02 gate.

Two additional pre-existing WhyYou test issues were observed while widening the US1
regression selection and are also excluded from the passing US1 gate:

- `test_applicant_http.py` and `test_lane_c_quickstart.py` import the absent
  `FakeInterviewAuthorization` symbol during collection.
- `test_report_event_handler.py::test_report_request_uses_transcript_range_for_evidence`
  supplies a subject without fields already required by the committed report handler;
  the failure is reproducible against the pre-US1 handler logic and occurs after the new
  optional observer has no-op'd.

US1~US3 PASS above are automated adapter/orchestration gates using deterministic fake or
mocked boundaries plus real WhyYou request-transaction integration tests. They prove that
A1~A7 are independently evaluable, that an unknown timeout cannot send processing commands,
that consent record/state transition/Outbox commit or roll back together, and that the
configured post-`save_consent()` fault returns 5xx with zero committed partial effects.
They also prove marker/token cleanup, overlay restoration, same-subject exactly-once retry and
`RESTORE_FAILED` blocking in the automated harness. They were **not** an actual WhyYou product
verdict when recorded; the separate first actual Run is recorded below.

The expected-red rows above freeze the contract before implementation. They are not
an actual N-02 Run and do not imply a WhyYou product verdict.

## Actual Run ledger

| Role | Run ID | Parent Run | ControlProof SHA | WhyYou SHA | Verdict | Restore | Manifest SHA-256 |
|---|---|---|---|---|---|---|---|
| Initial factual Run | `15cef078-ee24-4f0e-91ef-381e0f7a1cc2` | — | `b92b9ada48e82c5290d5b6eb99883e5dcc50f0ee` | `94ad7f2caa0083d3d029b4b7726ee9b34c48eb21` | `INCONCLUSIVE` | `RESTORE_FAILED`; manual cleanup required | `d2306f3cd6e2b15ce87d94e4844a2278c7ea3c0b3c052a2aac45e1bff8f2bc9b` |
| Evidence-required child | `BLOCKED_RESTORE_FAILED` | `15cef078-ee24-4f0e-91ef-381e0f7a1cc2` | — | — | — | — | — |

## Assertion and bundle ledger

| Run ID | A1 | A2 | A3 | A4 | A5 | A6 | A7 | EV3-01~10 | Bundle verify |
|---|---|---|---|---|---|---|---|---|---|
| `15cef078-ee24-4f0e-91ef-381e0f7a1cc2` | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | Required files sealed; facts below include gaps | VERIFIED; 19 files |

The parent bundle is `.controlproof/runs/15cef078-ee24-4f0e-91ef-381e0f7a1cc2` and remains unchanged. Its manifest `bundle_digest` is `f5c00a0e5d75262206991c82047d1f0dbfc814482feed22e840e218b1f991dc4`. Run-owned path, policy and lane digests are `2d7693a17e8380f1153d8ff12559bcf4ba1f68f2daaffdf9f4e1abb83765213a`, `74f0c6e4650088245ede3c3a992a28f2e9fa27834bee770c55cc41e357bd4d74` and `ffac35805fc0d5171101f149f2ba97080f8f29de7b17f98946e736f73562f07b` respectively. These were captured by the Run, not invented at preflight.

| Actual fact | Parent evidence | Result and limit |
|---|---|---|
| A1~A3 | `assertions.json`, `baseline-effects.jsonl`, `bypass-attempts.jsonl`, `protected-effects.jsonl` | Pristine baseline and document/recording bypass checks PASS. |
| A4 / AI assessment | `assertions.json`, `bypass-attempts.jsonl`, `protected-effects.jsonl` | FAIL: pre-consent assessment request was accepted (`EVENT_PERSISTED`) and new effect `event:497fd25e-9939-5ccf-9118-287fd1053b25` was observed. Root-cause class remains unassigned until T080/T083. |
| A5 / normal order | `assertions.json`, `policy-and-consent.json`, `causal-events.jsonl`, `causal-edges.jsonl` | FAIL: consent source absent, policy identity mismatch and zero causal events/edges; the normal-order three-path chain was not established. Root-cause class remains unassigned. |
| A6 / failed commit | `assertions.json`, `policy-and-consent.json`, `fault-receipts.jsonl`, `bypass-attempts.jsonl`, `protected-effects.jsonl` | FAIL: consent request returned `CONSENT_POLICY_MISMATCH`, no trigger receipt was captured, and the AI-assessment path accepted a request with new effect `event:a3a48891-2564-57d5-bb72-913827ee2e7a`. This does not yet establish whether target, runner or observer caused each missing fact. |
| A7 / recovery | `assertions.json`, `recovery.json`, `run.json`, `blocks/whyyou-local--n02-consent-order.json` | FAIL: restore `FAILED`, `manual_cleanup_required=true`, normal retry did not succeed. Hook inactive and marker removed were reported; the persistent restore block references this Run. No child or repeat Run was attempted. |
| Overall | `judgement.json`, `run.json`, `manifest.json` | `RESTORE_FAILED` takes precedence: overall `INCONCLUSIVE` with `INSUFFICIENT_EVIDENCE`, even though A4~A7 retain individual FAIL facts. No individual assertion is INCONCLUSIVE. Bundle `VERIFIED` proves integrity, not that the missing receipt/causal facts exist. |

Path results are `DOCUMENT_ANALYSIS=PASS`, `RECORDING=PASS`, `AI_ASSESSMENT=FAIL`. `fault-receipts.jsonl`, `faults.jsonl`, `causal-events.jsonl` and `causal-edges.jsonl` are sealed but empty. AWS, N-01 and N-03 remain unverified. No product guard or sealed parent artifact was changed after observing this result.

The WhyYou working tree became dirty **after** the clean-source Run because the local observer created untracked `.controlproof/observers/receipts/15cef078-ee24-4f0e-91ef-381e0f7a1cc2.jsonl` (3,060 bytes; SHA-256 `61874278514f93f35acdc8242546539eb6fc5ab8297a02bb0b12b11b3095c833`). This runtime receipt is preserved for diagnosis; it was not part of the captured source snapshot and is not committed. Do not delete it or mistake a later dirty working tree for the Run's clean source state.

The worker console reported repeated delivery-cycle exceptions, including a missing `CriterionVerificationGuide.time_budget_seconds` and `TenantScopedInterviewNotFound`. This unsealed diagnostic output is not yet a root-cause classification. After bundle verification, the API and four worker processes started for this attempt were stopped; no matching Python worker/API process remained. A stale `C:\tmp\iep-worker-ready` file created by those workers was removed after process verification. Postgres, LocalStack, the observer receipt, sealed bundle and persistent N-02 restore block were preserved. No manual target cleanup was claimed.

## Conditional remediation ledger

Do not fill this table from source review alone. Each decision requires an initial
Run artifact and one root-cause class:
`TARGET_CONTROL_DEFECT`, `RUNNER_OR_OBSERVER_DEFECT`, or
`RESTORE_OPERATOR_DEFECT`.

| Task | Assertion/path | Parent artifact | Root-cause class | Decision | Regression | Child Run |
|---|---|---|---|---|---|---|
| T080 | A5~A7/general | `15cef078-ee24-4f0e-91ef-381e0f7a1cc2` | — | `PENDING_CLASSIFICATION` | — | — |
| T081 | A2/document | `15cef078-ee24-4f0e-91ef-381e0f7a1cc2` | — | `PENDING_DECISION`; parent A2 PASS | — | — |
| T082 | A3/recording | `15cef078-ee24-4f0e-91ef-381e0f7a1cc2` | — | `PENDING_DECISION`; parent A3 PASS | — | — |
| T083 | A4/assessment | `15cef078-ee24-4f0e-91ef-381e0f7a1cc2` | — | `PENDING_CLASSIFICATION`; parent A4 FAIL | — | — |
| T084 | child/reverify | `15cef078-ee24-4f0e-91ef-381e0f7a1cc2` | — | `BLOCKED_RESTORE_FAILED` pending safety cleanup and evidence-selected remediation | — | — |

## Portability and limitations

- Only synthetic applicants and local/test credentials are permitted.
- Runtime bundles remain ignored and are not copied into Git.
- A local result does not establish AWS or production behavior.
- N-01 and N-03 remain outside Spec 003.
- A passing automated fixture is not an actual WhyYou N-02 verdict.
