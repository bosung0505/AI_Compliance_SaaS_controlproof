# Spec 003 Traceability

This matrix connects approved requirements to planned tasks, tests, implementation
and actual artifacts. `A~B` includes both endpoints. The actual-artifact cells below
refer only to the first local Run; they do not claim final requirement closure.

## Functional requirements

| Requirements | Tasks | Planned tests | Implementation / contract | Actual artifact |
|---|---|---|---|---|
| FR-001~006 | T005~T018, T023, T039, T067, T070 | scenario/profile/CLI/readiness contracts | scenario v3, profile registry, runner, config | T077 READY; initial parent below |
| FR-007~019 | T024~T040 | seed, path, observer, judge and lane-isolation tests | N-02 seed/processing adapters, executor, A1~A4 judge | Parent A1~A3 PASS, A4 FAIL |
| FR-020~025 | T041~T051 | consent, causality, normal-order and A5 judge tests | consent/causality adapters, normal-order executor | Parent A5 FAIL; causal facts absent |
| FR-026~033 | T010, T020~T022, T052~T064, T074~T084 | fault safety, rollback, restore and retest tests | local/test hook, fault adapter, A6/A7 judge, retest | Parent A6~A7 FAIL; RESTORE_FAILED; child blocked |
| FR-034~041 | T007, T011, T018, T065~T073, T085~T092 | verdict, presentation, CLI, bundle and security tests | judge aggregation, evidence, presentation, CLI | Parent INCONCLUSIVE; sealed bundle VERIFIED |

## Success criteria

| Criteria | Tasks | Planned verification | Actual result |
|---|---|---|---|
| SC-001~005 | T024~T073, T078 | deterministic A1~A7 gates and initial actual Run | Initial parent has mixed A1~A7 result; no blanket PASS |
| SC-006~008 | T055~T064, T077~T088, T093 | restore, timing, quickstart and independent reproduction | Initial restore FAILED; run/show/verify under 600 seconds; other gates pending |
| SC-009~012 | T065~T093 | projection, bundle, lineage, redaction and handoff gates | Initial bundle VERIFIED; child and closure gates pending |

## Assertions and evidence

| Contract | Tasks | Planned tests / files | Actual artifact |
|---|---|---|---|
| N02-A1~A4 | T024~T040, T065, T072, T078 | bypass/effect/fixture isolation and combined verdict | Parent PASS/PASS/PASS/FAIL; facts below |
| N02-A5 | T041~T051, T065, T072, T078 | normal order, policy identity and causal graph | Parent FAIL; facts below |
| N02-A6~A7 | T052~T065, T072, T078 | trigger, rollback, three blocked paths, restore and retry | Parent FAIL/FAIL; facts below |
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

## Source truth boundary

- Automated tests prove ControlProof contracts; they do not prove WhyYou's actual
  N-02 behavior.
- The first actual source mapping is frozen above by T077~T079.
- Conditional product changes T080~T083 require a cited parent artifact.
- A child Run never rewrites its parent bundle or this table's parent references.
