# Spec 003 Implementation Decisions

## Status

- Implementation foundation: in progress
- Initial actual N-02 Run: `NOT_RUN`
- Evidence-gated product remediation: `PENDING_INITIAL_RUN`

This log records implementation choices that cannot be inferred from Tasks alone.
It must not predict a WhyYou FAIL from source review or mark a conditional fix
`REQUIRED` before T078 seals the first actual Run.

## Decision template

### ID-003-XX — Title

- Date:
- Task:
- Requirement/assertion:
- Status: `PROPOSED | CONFIRMED | NOT_REQUIRED`
- Source baseline:
- Triggering test or parent Run:
- Exact evidence artifact:
- Root-cause class:
  `TARGET_CONTROL_DEFECT | RUNNER_OR_OBSERVER_DEFECT | RESTORE_OPERATOR_DEFECT`
- Decision:
- Alternatives considered:
- Safety and compatibility impact:
- Regression command and result:
- Child Run / parent immutability result:

## Pre-actual implementation decisions

### ID-003-01 — Keep Spec 003 instrumentation separate from product guards

- Date: 2026-10-01
- Task: T001~T004
- Requirement/assertion: FR-026~027, FR-037~039
- Status: `CONFIRMED`
- Source baseline: ControlProof `c27f9d6`; WhyYou `511ae9e`
- Triggering test or parent Run: approved Plan and D-015/D-016; no actual Run yet
- Exact evidence artifact: `NOT_RUN`
- Decision: Add only disabled-by-default local/test configuration, deterministic
  fixtures and implementation records during Setup. Do not add analysis,
  recording or assessment consent guards before the first actual Run.
- Alternatives considered: pre-fix suspected WhyYou boundaries; rejected because
  it would destroy the first factual FAIL/PASS evidence.
- Safety and compatibility impact: no production enablement, no actual applicant
  data, no existing sealed bundle mutation.
- Regression command and result: recorded in `validation.md` after Setup checks
- Child Run / parent immutability result: `NOT_REQUIRED` before T078

### ID-003-02 — Inject the consent fault inside the request transaction

- Date: 2026-10-01
- Task: T052~T064
- Requirement/assertion: FR-026~032, N02-A6~A7, EV3-07~EV3-09
- Status: `CONFIRMED`
- Source baseline: ControlProof `c27f9d6`; WhyYou `511ae9e`; both working trees remain uncommitted
- Triggering test or parent Run: automated US3 contract and integration tests; no actual Run yet
- Exact evidence artifact: `NOT_RUN`; automated command results are recorded in `validation.md`
- Root-cause class: not applicable before the initial actual Run
- Decision: Place a disabled-by-default, local/test-only one-shot hook immediately after
  `save_consent()` and before invitation state/Outbox mutation. Bind marker and receipt to the
  current Run, lane, subject and request. Restore only owned marker/token files, verify zero
  durable consent effects, remove each temporary deep-boundary overlay, and allow same-subject
  retry only after the safe-state check passes.
- Alternatives considered: fail outside the request transaction, infer activation from a 5xx,
  or auto-delete foreign markers. Rejected because these choices cannot prove rollback, trigger
  identity or cleanup ownership.
- Safety and compatibility impact: production/default execution is a no-op. No document,
  recording or assessment product guard was added before T078. Uncertain restore records
  `RESTORE_FAILED` and blocks a later fault Run until evidence-backed `cleanup-confirm`.
- Regression command and result: ControlProof 366 passed; scoped WhyYou regression 88 passed;
  full commands and durations are in `validation.md`
- Child Run / parent immutability result: `NOT_REQUIRED` before T078

## Conditional remediation decisions

| Task | Boundary | Parent artifact required | Status |
|---|---|---|---|
| T080 | A5~A7 or runner/restore ownership | Yes | `PENDING_INITIAL_RUN` |
| T081 | document analysis | Yes | `PENDING_INITIAL_RUN` |
| T082 | recording | Yes | `PENDING_INITIAL_RUN` |
| T083 | AI assessment/reporting | Yes | `PENDING_INITIAL_RUN` |
| T084 | child retest or parent reverify | Yes | `PENDING_INITIAL_RUN` |
