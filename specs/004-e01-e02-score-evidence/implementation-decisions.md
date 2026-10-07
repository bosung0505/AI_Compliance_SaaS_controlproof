# Spec 004 Implementation Decisions

## Status

- Implementation: Phase 1 (T001~T004) done; Phase 2 failing tests (T005~T011) written; implementation from T012 not started.
- WhyYou local/test fixture: `spec004-report-v1`, reviewed/fixed source `3423f16`, PR
  jhkim0602/gbsa_aws#6 merged into `bosung/controlproof-n02-integration` at `42aaaba` (ID-004-03).
  No WhyYou product code or main changed.
- Actual E-01/E-02 Runs: none. Sandbox diagnostics: none.

This log records implementation choices that cannot be inferred from Tasks alone. The first actual Run of each
scenario will be sealed before any WhyYou product change (plan §8). A direct assertion FAIL is a preserved
observation, not by itself proof that a WhyYou product boundary is defective.

## Decision template

### ID-004-XX — Title

- Date:
- Task:
- Requirement/assertion:
- Status: `PROPOSED | CONFIRMED | NOT_REQUIRED`
- Source baseline: ControlProof `<sha>`, WhyYou `<sha>`
- Triggering test, diagnostic or parent Run:
- Exact evidence artifact:
- Root-cause class:
  `TARGET_CONTROL_DEFECT | RUNNER_OR_OBSERVER_DEFECT | RESTORE_OPERATOR_DEFECT`
- Decision:
- Alternatives considered:
- Safety and compatibility impact:
- Regression command and result:
- Child Run / parent immutability result:

## Pre-actual implementation decisions

### ID-004-01 — Phase 2 failing tests are recorded as strict expected failures

- Date: 2026-10-07
- Task: T005~T011
- Requirement/assertion: Constitution VII test-first, tasks.md "Foundation tests — write first and confirm failure"
- Status: `CONFIRMED` (operator instruction for this session: write failing tests only, keep the existing suite
  green and count the new RED tests separately)
- Decision: every Phase 2 test that must fail until its implementation task is marked
  `pytest.mark.xfail(strict=True, raises=…)` with the exact exception the missing implementation produces
  (`AttributeError`/`ImportError` for a missing symbol, `AssertionError` or `ValidationError` for a missing rule)
  and a reason naming the task that will remove the marker. `strict=True` makes an unexpected pass a failure,
  and `raises=` makes a failure for a different reason a failure, so the RED is the intended one. Guard tests
  that must already pass (v1~v3 regression, existing profiles) carry no marker.
- Removal rule: the implementation task named in each reason removes the marker in the same change that makes
  the test pass (T012~T020).
- Alternatives considered: leaving the tests failing (breaks the existing `pytest -q` gate the operator required
  to stay green); skipping them (hides whether they still fail for the intended reason).

### ID-004-02 — Conditional branches (to be filled after T080/T081)

| Task | Condition | Required? | Evidence |
|---|---|---|---|
| T084 | runner/observer defect in an initial Run | pending | |
| T085 | E01-A3 `TARGET_CONTROL_DEFECT` (P1) | pending | |
| T086 | approved T085 fix | pending | |
| T087 | other target defect | pending | |
| T088 | child retest | pending | |

### ID-004-03 — PR #6 review: explicit report-request memory scope

- Date: 2026-10-07
- Task: T024/T026/T028/T029; FR-012, SC-007
- Status: `CONFIRMED`; operator authorized fixes, feature-branch merge and push
- Source: WhyYou PR #6 initial head `3dfa10c`; fixed head `3423f167664273152078faeb1b91d0324b98a2f4`
- Finding: a shared UUIDv7 millisecond is not a report identity. Memory crossed company/request
  boundaries and interleaved requests overwrote one another. Incomplete markers also bypassed
  MARKER_INVALID or were accepted without the required separator.
- Decision: key the bounded memory by `(company_id, request_id, criterion_id)`. The existing
  messaging worker sets request_id to the report-request Outbox event ID and passes the same
  context through all criterion assessments. Keep the UUIDv7 timestamp as an additional stale
  retry check. Detect malformed marker prefixes and return h03 output with MARKER_INVALID.
- Alternatives: new marker scope fields or product payload changes are unnecessary; the existing
  context already carries the explicit request boundary. Timestamp-only identity rejected.
- Safety/compatibility: only local/test substitute and tests change; no product code, marker
  syntax, fixture identity/digest, raw receipt publication, external AI call or actual Run changes.
- Verification: 5 EXPECTED RED / 48 PASS, then 53 model PASS; scoped 177 PASS; full unit 488 PASS
  plus the known baseline repository-guard failure. Commands and durations are in validation.md.
- The fixed merged WhyYou integration HEAD is the target source for later sandbox/official Runs;
  these Runs still require their own readiness and approval gates.
