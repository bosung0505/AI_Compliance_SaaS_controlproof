# Spec 003 Traceability

This matrix connects approved requirements to planned tasks, tests, implementation
and actual artifacts. `A~B` includes both endpoints. The actual-artifact cells below
refer to the first local Run (parent `15cef078-ee24-4f0e-91ef-381e0f7a1cc2`) and, where noted, to the
evidence-backed child `7b59237e-0a96-403a-9add-28b91011e950` (T084 attempt 3).

## Functional requirements

| Requirements | Tasks | Planned tests | Implementation / contract | Actual artifact |
|---|---|---|---|---|
| FR-001~006 | T005~T018, T023, T039, T067, T070 | scenario/profile/CLI/readiness contracts | scenario v3, profile registry, runner, config | T077 READY; parent below; child preflight 16/16 READY on the teammate PC |
| FR-007~019 | T024~T040 | seed, path, observer, judge and lane-isolation tests | N-02 seed/processing adapters, executor, A1~A4 judge | Parent A1~A3 PASS, A4 FAIL; child A1~A4 PASS (A4 via the target refusal receipt, ID-003-17/T083) |
| FR-020~025 | T041~T051 | consent, causality, normal-order and A5 judge tests | consent/causality adapters, normal-order executor | Parent A5 FAIL; child A5 `INCONCLUSIVE`: recording and assessment chains complete, document result unreachable on the isolated target (ID-003-18) |
| FR-026~033 | T010, T020~T022, T052~T064, T074~T084 | fault safety, rollback, restore and retest tests | local/test hook, fault adapter, A6/A7 judge, retest | Parent A6~A7 FAIL; child A6 PASS, A7 `INCONCLUSIVE`, restore SUCCEEDED, no block (ID-003-14) |
| FR-034~041 | T007, T011, T018, T065~T073, T085~T092 | verdict, presentation, CLI, bundle and security tests | judge aggregation, evidence, presentation, CLI | Parent and child INCONCLUSIVE; both bundles VERIFIED (19 and 21 files) |

## Success criteria

| Criteria | Tasks | Planned verification | Actual result |
|---|---|---|---|
| SC-001~005 | T024~T073, T078 | deterministic A1~A7 gates and initial actual Run | Parent mixed; child A1~A4, A6 PASS with A5/A7 INCONCLUSIVE; no blanket PASS |
| SC-006~008 | T055~T064, T077~T088, T093 | restore, timing, quickstart and independent reproduction | Child restore SUCCEEDED; child Run 132.7 s, retest+verify 402 s wall clock; quickstart commands executed with real ids; teammate reproduction recorded with portability defects |
| SC-009~012 | T065~T093 | projection, bundle, lineage, redaction and handoff gates | Both bundles VERIFIED; security corpus extended (T086); handoff update T092 |

## Assertions and evidence

| Contract | Tasks | Planned tests / files | Actual artifact |
|---|---|---|---|
| N02-A1~A4 | T024~T040, T065, T072, T078 | bypass/effect/fixture isolation and combined verdict | Parent PASS/PASS/PASS/FAIL; child PASS×4 |
| N02-A5 | T041~T051, T065, T072, T078 | normal order, policy identity and causal graph | Parent FAIL; child INCONCLUSIVE (document result event missing) |
| N02-A6~A7 | T052~T065, T072, T078 | trigger, rollback, three blocked paths, restore and retry | Parent FAIL/FAIL; child PASS/INCONCLUSIVE |
| EV3-01~EV3-05 | T007, T018, T024~T040, T068, T071~T072 | capabilities, lanes, baseline, attempts and effects | Parent manifest maps required files; bundle VERIFIED; A4 effect found |
| EV3-06~EV3-10 | T007, T018, T041~T089 | causality, fault, recovery, judgement and manifest | Parent manifest maps required files; empty receipt/causal files and restore failure remain |

## Initial actual parent mapping (T077~T079)

The immutable parent is Run `15cef078-ee24-4f0e-91ef-381e0f7a1cc2` at `.controlproof/runs/15cef078-ee24-4f0e-91ef-381e0f7a1cc2`. Its ControlProof source is `b92b9ada48e82c5290d5b6eb99883e5dcc50f0ee` and its WhyYou source is `94ad7f2caa0083d3d029b4b7726ee9b34c48eb21`; both were clean before preflight and Run. `manifest.json` SHA-256 is `d2306f3cd6e2b15ce87d94e4844a2278c7ea3c0b3c052a2aac45e1bff8f2bc9b`, and CLI verify returned VERIFIED for 19 files. The fixture digest is `ce09b95403b34e1390502c90f5c5edc518ddf65d38c8ce881617a37cac6d16b1`. Run-owned path/policy/lane digests are recorded in `validation.md` and the sealed manifest.

| Verdict fact | Parent source artifacts | Actual result |
|---|---|---|
| A1~A3 | `assertions.json`, `baseline-effects.jsonl`, `bypass-attempts.jsonl`, `protected-effects.jsonl` | PASS/PASS/PASS; document and recording requests denied with no new protected effects. |
| A4 | `assertions.json`, `bypass-attempts.jsonl`, `protected-effects.jsonl` | Direct FAIL: assessment request accepted before consent and new effect `event:497fd25e-9939-5ccf-9118-287fd1053b25` observed. |
| A5 | `assertions.json`, `policy-and-consent.json`, `causal-events.jsonl`, `causal-edges.jsonl` | FAIL: policy identity mismatch, consent source absent, zero causal events/edges; normal-order chain unproven. |
| A6 | `assertions.json`, `policy-and-consent.json`, `fault-receipts.jsonl`, `bypass-attempts.jsonl`, `protected-effects.jsonl` | FAIL: `CONSENT_POLICY_MISMATCH`, no trigger receipt, assessment request accepted with new effect `event:a3a48891-2564-57d5-bb72-913827ee2e7a`. |
| A7 | `assertions.json`, `recovery.json`, `run.json` | FAIL: restore FAILED, manual cleanup required, no successful normal retry. A persistent runtime block points to this parent Run. |
| Overall | `judgement.json`, `run.json`, `manifest.json` | RESTORE_FAILED / INCONCLUSIVE with `INSUFFICIENT_EVIDENCE`; the A4~A7 FAIL facts remain visible. No individual assertion is INCONCLUSIVE. |

The manifest maps EV3-01~EV3-10 to sealed files. `fault-receipts.jsonl`, `faults.jsonl`, `causal-events.jsonl` and `causal-edges.jsonl` are empty; VERIFIED establishes integrity of those files, not the missing facts. Path results are document PASS, recording PASS and AI assessment FAIL. AWS, N-01 and N-03 were not run. Root-cause classes remain unassigned pending T080~T083; the RESTORE_FAILED block prevents an actual child Run. The sealed parent bundle was not edited.

After the Run, WhyYou also has an untracked local observer receipt at `.controlproof/observers/receipts/15cef078-ee24-4f0e-91ef-381e0f7a1cc2.jsonl` (SHA-256 `61874278514f93f35acdc8242546539eb6fc5ab8297a02bb0b12b11b3095c833`). Preserve it for diagnosis. It does not change the clean WhyYou SHA captured in the parent bundle and is not a replacement for sealed evidence.

## Evidence-backed child mapping (T084 attempt 3)

Child `7b59237e-0a96-403a-9add-28b91011e950` at `.controlproof/runs/7b59237e-0a96-403a-9add-28b91011e950`; parent `15cef078-ee24-4f0e-91ef-381e0f7a1cc2`. ControlProof `14f9868d01acc2b070ea5588008ba6f68374eb3e`, WhyYou `be81ebccc6d4921ce7bc6610be9b0e7d0277c8a2` (personal branch with T083 and T082 on `c8e9970`). Verdict `INCONCLUSIVE`, state `COMPLETED`, bundle VERIFIED (21 files), manifest SHA-256 `2a0e7862d103a5702b5102ea2564a8077f8ed84eb71e6de52719877e9c996f28`.

| Verdict fact | Child source artifacts | Actual result |
|---|---|---|
| A1~A3 | `assertions.json`, `baseline-effects.jsonl`, `bypass-attempts.jsonl`, `protected-effects.jsonl` | PASS: document and recording requests denied before consent with no new effect (recording denial now from the T082 consent check, not from an invalid fixture). |
| A4 | `assertions.json`, `bypass-attempts.jsonl`, `protected-effects.jsonl`, `observations.jsonl` | PASS: runner input refused by the target worker (`REPORT_ASSESSMENT_REFUSED`, T083), zero new effects. |
| A5 | `assertions.json`, `policy-and-consent.json`, `causal-events.jsonl`, `causal-edges.jsonl`, `bypass-attempts.jsonl` (`drive_steps`) | INCONCLUSIVE: recording and assessment chains REQUESTED→STARTED→RESULT complete (10 events, 9 edges); the document chain stops at STARTED because the isolated target cannot run LLM analysis. |
| A6 | `assertions.json`, `fault-receipts.jsonl`, `recovery.json` | PASS: fault triggered, receipt request matches the failed commit (ID-003-13), consent atomic, three paths closed (assessment refused), zero leaked effects. |
| A7 | `assertions.json`, `recovery.json` | INCONCLUSIVE: restore SUCCEEDED, one consent set after retry, recovered order unproven for the same document reason. |
| Overall | `judgement.json`, `run.json`, `manifest.json`, `retest-link.json` | COMPLETED / INCONCLUSIVE with `INSUFFICIENT_EVIDENCE`; no direct FAIL; parent unchanged. |

## Source truth boundary

- Automated tests prove ControlProof contracts; they do not prove WhyYou's actual
  N-02 behavior.
- The first actual source mapping is frozen above by T077~T079.
- Conditional product changes T080~T083 require a cited parent artifact.
- A child Run never rewrites its parent bundle or this table's parent references.
