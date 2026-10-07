# Spec 004 Implementation Decisions

## Status

- Implementation: Phase 1 (T001~T004) and Phase 2 (T005~T021) done; Phase 3 user stories from T030 in progress.
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

## Phase 2 foundation implementation (T012~T021), 2026-10-07

Status of each entry: `CONFIRMED` — contract/test corrections from code facts; no product meaning or judgement
rule changed.

### ID-004-04 — Missing-file bundle test checked the wrong mechanism (T007/T018)

`EvidenceBundleWriter.seal()` refuses to seal when a canonical file is missing (existing Spec 001~003 rule), so a
Spec 004 bundle can only lose a profile file after sealing. The T007 test that wrote a bundle without the file and
expected verify `INVALID` was corrected to delete the file after sealing; a separate test asserts the seal refusal.
Evidence: `engine/evidence.py` `EvidenceBundleWriter.seal` (`canonical files missing`).

### ID-004-05 — `faults.jsonl` is not canonical for Spec 004 (T018)

The Spec 001~003 base set includes `faults.jsonl` for fault-marker receipts. Spec 004 injects changes through
`change-injections.jsonl` and has no fault marker, so its base set is the common set without `faults.jsonl` plus
`environment.snapshot.json` (`SPEC004_BASE_FILES`). The bundle contract never listed `faults.jsonl` for Spec 004.

### ID-004-06 — Run policy lives in `engine/models.py`, not `engine/runner.py` (T016)

tasks.md T016 placed the Spec 004 Run policy in `engine/runner.py`, but every profile policy (Spec 002, N-02) is
enforced in `Run.validate_run` (`engine/models.py`); `runner.py` only maps profiles to executors. The Spec 004 policy
(canonical scenario, no fault variant, `LOCAL_EMULATED`, AWS `NOT_RUN`, environment/lane/capability digests,
`scoring_rule_source_digest` on every and only E-02 Run, AWS/N-01/N-03 unverified scope) was added there in T012.
`runner.py` is unchanged until T040/T057 register the executors.

### ID-004-07 — Earlier profiles' scenario snapshot digests are pinned (T013)

Adding `diagnostic_ids` to `ScenarioDefinition` would change every profile's snapshot digest. The new field is
excluded from non-Spec-004 snapshots, and `tests/integration/test_spec003_v3_regression.py` now pins the H-03,
H-03-DLQ, E-03-BEFORE, E-03-AFTER and N-02 digests (measured before and after the change: identical).
`diagnostic_ids` is optional in a v4 YAML; when present it must equal the canonical set (`E01-D1` for E-01, none
for E-02).

### ID-004-08 — Strict-xfail reasons follow progress (T012~T020)

When a task removes one cause of a RED test while another task still owns the rest, the marker's `raises=` and
reason were updated to the remaining cause (T007 after T012: `ValueError` until T018; T008 registry/preflight after
T012/T013: `AssertionError`/`UnregisteredExecutionProfile` until T040/T057). T008's cross-scenario test became a
guard: the existing CLI already returns `PROFILE_MISMATCH` once the enum exists.

### ID-004-09 — Spec 004 fakes are a separate module (T019)

`tests/fixtures/fake_spec004.py` holds `FakeSpec004Adapters` (one object for all eight protocols, modelling the
baseline WhyYou behaviour including P1). `make_adapters(spec004=...)` wires it, so `fake_adapters.py` gained only
the wiring. Options drive single facts wrong for FAIL/INCONCLUSIVE tests.

### ID-004-10 — Spec 004 settings validation and the scoring-copy cross-check (T015, T017)

`Settings.validate_spec004_safety` (new test `tests/unit/test_config_spec004.py`, RED first) fails closed on a
non-spec004 fixture, a wrong digest (`sha256("controlproof:" + id)`), external AI, non-local claims, or a main/dirty
WhyYou checkout. The scoring copy was additionally compared with WhyYou's own `aggregate` on 2000 random inputs
(WhyYou checkout read-only): 0 mismatches.
