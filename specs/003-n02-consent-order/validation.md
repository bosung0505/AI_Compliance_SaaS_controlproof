# Spec 003 Validation

## Current status

- Workflow stage: `$speckit-implement` in progress
- Automated implementation gates: US1 A1~A4, US2 A5 and US3 A6~A7 `PASS`; US4 `NOT_RUN`
- WhyYou actual N-02 preflight: `NOT_RUN`
- Initial actual Run: `NOT_RUN`
- Child retest: `NOT_REQUIRED` until the initial Run proves a direct FAIL
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

## Gate ledger

| Gate | Tasks | Command | Result | Duration |
|---|---|---|---|---|
| Setup | T001~T004 | recorded below | PASS | < 1 minute |
| Foundation | T005~T023 | recorded below | PASS | 3 minutes 45 seconds |
| US1 bypass/effects | T024~T040 | scoped pytest + full ControlProof regression + scoped Ruff | PASS | 2 minutes 54 seconds full regression; scoped gates < 2 seconds |
| US2 normal order | T041~T051 | scoped pytest + full ControlProof regression + WhyYou transaction test + scoped Ruff | PASS | 2 minutes 53 seconds full regression; scoped gates < 14 seconds |
| US3 fault/recovery | T052~T064 | scoped pytest + full ControlProof regression + scoped WhyYou rollback/fault regression + Ruff | PASS | 2 minutes 47 seconds full regression; scoped gates < 12 seconds |
| US4 review/bundle | T065~T073 | `NOT_RUN` | `NOT_RUN` | — |
| Initial actual truth | T077~T079 | `NOT_RUN` | `NOT_RUN` | — |
| Conditional remediation | T080~T084 | `PENDING_INITIAL_RUN` | `NOT_RUN` | — |
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
`RESTORE_FAILED` blocking in the automated harness. They are **not** an actual WhyYou product
verdict: no live N-02 Run, six-subject seed or evidence bundle was created.

The expected-red rows above freeze the contract before implementation. They are not
an actual N-02 Run and do not imply a WhyYou product verdict.

## Actual Run ledger

| Role | Run ID | Parent Run | ControlProof SHA | WhyYou SHA | Verdict | Restore | Manifest SHA-256 |
|---|---|---|---|---|---|---|---|
| Initial factual Run | `NOT_RUN` | — | — | — | `NOT_RUN` | — | — |
| Evidence-required child | `NOT_REQUIRED` | — | — | — | — | — | — |

## Assertion and bundle ledger

| Run ID | A1 | A2 | A3 | A4 | A5 | A6 | A7 | EV3-01~10 | Bundle verify |
|---|---|---|---|---|---|---|---|---|---|
| `NOT_RUN` | — | — | — | — | — | — | — | — | — |

## Conditional remediation ledger

Do not fill this table from source review alone. Each decision requires an initial
Run artifact and one root-cause class:
`TARGET_CONTROL_DEFECT`, `RUNNER_OR_OBSERVER_DEFECT`, or
`RESTORE_OPERATOR_DEFECT`.

| Task | Assertion/path | Parent artifact | Root-cause class | Decision | Regression | Child Run |
|---|---|---|---|---|---|---|
| T080 | A5~A7/general | `PENDING_INITIAL_RUN` | — | `PENDING_INITIAL_RUN` | — | — |
| T081 | A2/document | `PENDING_INITIAL_RUN` | — | `PENDING_INITIAL_RUN` | — | — |
| T082 | A3/recording | `PENDING_INITIAL_RUN` | — | `PENDING_INITIAL_RUN` | — | — |
| T083 | A4/assessment | `PENDING_INITIAL_RUN` | — | `PENDING_INITIAL_RUN` | — | — |
| T084 | child/reverify | `PENDING_INITIAL_RUN` | — | `PENDING_INITIAL_RUN` | — | — |

## Portability and limitations

- Only synthetic applicants and local/test credentials are permitted.
- Runtime bundles remain ignored and are not copied into Git.
- A local result does not establish AWS or production behavior.
- N-01 and N-03 remain outside Spec 003.
- A passing automated fixture is not an actual WhyYou N-02 verdict.
