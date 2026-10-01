# Spec 003 Traceability

This matrix connects approved requirements to planned tasks, tests, implementation
and eventual actual artifacts. `A~B` includes both endpoints. Empty actual-artifact
cells remain `NOT_RUN` until Validation records a sealed bundle.

## Functional requirements

| Requirements | Tasks | Planned tests | Implementation / contract | Actual artifact |
|---|---|---|---|---|
| FR-001~006 | T005~T018, T023, T039, T067, T070 | scenario/profile/CLI/readiness contracts | scenario v3, profile registry, runner, config | `NOT_RUN` |
| FR-007~019 | T024~T040 | seed, path, observer, judge and lane-isolation tests | N-02 seed/processing adapters, executor, A1~A4 judge | `NOT_RUN` |
| FR-020~025 | T041~T051 | consent, causality, normal-order and A5 judge tests | consent/causality adapters, normal-order executor | `NOT_RUN` |
| FR-026~033 | T010, T020~T022, T052~T064, T074~T084 | fault safety, rollback, restore and retest tests | local/test hook, fault adapter, A6/A7 judge, retest | `NOT_RUN` |
| FR-034~041 | T007, T011, T018, T065~T073, T085~T092 | verdict, presentation, CLI, bundle and security tests | judge aggregation, evidence, presentation, CLI | `NOT_RUN` |

## Success criteria

| Criteria | Tasks | Planned verification | Actual result |
|---|---|---|---|
| SC-001~005 | T024~T073, T078 | deterministic A1~A7 gates and initial actual Run | `NOT_RUN` |
| SC-006~008 | T055~T064, T077~T088, T093 | restore, timing, quickstart and independent reproduction | `NOT_RUN` |
| SC-009~012 | T065~T093 | projection, bundle, lineage, redaction and handoff gates | `NOT_RUN` |

## Assertions and evidence

| Contract | Tasks | Planned tests / files | Actual artifact |
|---|---|---|---|
| N02-A1~A4 | T024~T040, T065, T072, T078 | bypass/effect/fixture isolation and combined verdict | `NOT_RUN` |
| N02-A5 | T041~T051, T065, T072, T078 | normal order, policy identity and causal graph | `NOT_RUN` |
| N02-A6~A7 | T052~T065, T072, T078 | trigger, rollback, three blocked paths, restore and retry | `NOT_RUN` |
| EV3-01~EV3-05 | T007, T018, T024~T040, T068, T071~T072 | capabilities, lanes, baseline, attempts and effects | `NOT_RUN` |
| EV3-06~EV3-10 | T007, T018, T041~T089 | causality, fault, recovery, judgement and manifest | `NOT_RUN` |

## Source truth boundary

- Automated tests prove ControlProof contracts; they do not prove WhyYou's actual
  N-02 behavior.
- The first actual source mapping is written only by T077~T079.
- Conditional product changes T080~T083 require a cited parent artifact.
- A child Run never rewrites its parent bundle or this table's parent references.
