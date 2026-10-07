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

## Phase 4 US1 implementation (T030~T043), 2026-10-07

Status: `CONFIRMED` unless marked `PROPOSED`. No product meaning or judgement rule changed.

### ID-004-11 — Criterion codes are uppercase (T035)

WhyYou validates every competency criterion code against `^[A-Z0-9_-]{2,40}$` on each read, so the lowercase codes
in data-model.md would make every seeded version unreadable. Codes are uppercase (`E01-1-VALID` …
`E01-5-OTHER-CRITERION`, `E01-REF-1-VALID`, `E01-REM-1/2-VALID`, `E01-PROBE-1-VALID`, `E02-A`, `E02-B`) and
`LaneCriterion.code` carries the same pattern. Code order, which WhyYou uses to evaluate criteria, is unchanged.

### ID-004-12 — Contract reason codes ride as a `detail` prefix (T041)

`InconclusiveReason` has only `NO_TEST_TARGET`, `ACCESS_LIMITED`, `INSUFFICIENT_EVIDENCE`, `EVIDENCE_CONFLICT`
(shared with Spec 001~003 bundles). The contract codes `PRECONDITION_NOT_MET` and `FIXTURE_EMISSION_MISMATCH` are
reported as `reason_code=INSUFFICIENT_EVIDENCE` with the code as the first token of `detail`; tests assert the prefix.
Extending the shared enum would change earlier bundles' schema and was not needed.

### ID-004-13 — Report/timeline API route has no `/company` segment (T037, T042)

The adapter contract, plan.md and the source-baseline note named `GET /v1/company/interview-sessions/{id}/report`.
WhyYou registers `/interview-sessions/{session_id}/report` and `/timeline` under `APIRouter(prefix="/v1")`
(`reporting/api/company_routes.py`), the same route the H-03 feature probe already checks. The documents and the
adapter now use `/v1/interview-sessions/{session_id}/report|timeline` (company token unchanged).

### ID-004-14 — Report presence comes from the DB, receipts are best effort (T037, T040)

WhyYou's observer writes receipts only for N-02 lanes (`runtime/controlproof_consent.py` `LANES`), so Spec 004
lanes get none. The executor waits on the stored report (DB projection) and ends the wait early only if a
`REPORT_ASSESSMENT_REFUSED` receipt exists; a report that never appears is `PRECONDITION_NOT_MET`, never FAIL.
`PROPOSED` (non-blocking, no task skipped): add Spec 004 lanes to the WhyYou local/test observer so refusals are
explicit instead of timing out at the Run deadline. Options: (a) leave as is — correct but slow on refusal;
(b) extend `LANES` in WhyYou local/test (WhyYou change, needs approval). Recommendation: (a) until Phase 8 SD shows
refusal latency matters.

### ID-004-15 — US1 scope of the E-01 executor and capabilities (T040, T042)

All Spec 004 capability names are registered at `v1` (`model.fixture.read` checks the target's fixture ID and
digest). Mutation (T047) and criteria-version/scoring-source (T055) capabilities report `RUNNER_NOT_READY` with an
operator action until their adapters are composed, so a real E-01/E-02 preflight cannot be READY yet. On fakes, the
E-01 executor runs the citation steps; E01-A3/A4 are `PRECONDITION_NOT_MET` INCONCLUSIVE and `storage-probe.json`
records `NOT_RUN` until US2, so an E-01 Run cannot PASS before Phase 5. Spec 004 consent reuses
`WhyYouConsentAdapter` with a separate credential store. Tests point the fake target at the spec004 fixture with
`use_spec004_fixture` (fake target defaults stay h03 for earlier profiles).

## Phase 5 US2 implementation (T044~T051), 2026-10-07

Status: `CONFIRMED`. No judgement rule changed; ID-004-16 fills a gap without widening PASS or FAIL.

### ID-004-16 — Affected item changed without an H-4 indicator is INCONCLUSIVE (T049)

E01-A3 lists PASS (an indicator on every affected axis/item) and FAIL (P1: same score and citation as PRE_REMOVAL;
an unaffected item changed; POST_REMOVAL 5xx). An affected item that changed but shows none of the four
indicators fits neither. It is reported INCONCLUSIVE (`INSUFFICIENT_EVIDENCE`, detail `INDICATOR_AMBIGUOUS`), the
same treatment as `unknown_fields`: the scenario needs a revision before such a shape can be judged.

### ID-004-17 — Storage probe writes three modes in WhyYou's stored axis shape (T048)

E01-D1 writes three axes on the probe lane's single item: `EMPTY` (no citation), `NONEXISTENT` (the Run's absent
UUID) and `OTHER_APPLICANT` (the reference report's Evidence ID). `OTHER_CRITERION` is not written: the probe lane has
one criterion, so there is no second item of the same report to cite. Each written axis carries `axis`, `label`,
`score`, `rationale` and `quoted_evidence_ids` because WhyYou `_restored_axes` drops entries without `rationale`.
Exposure is recorded per mode in `storage-probe.json`; it is never an assertion and never changes the verdict.

### ID-004-18 — Spec 004 cleanup-confirm lives in `engine/cli.py` (T050)

Before T050 a block on `e01-citation-evidence`/`e02-scoring-freeze` fell through to the H-03 `fault.target_safe`
probe (new test RED). `cleanup-confirm` now accepts a Spec 004 subject only when the block names a verified sealed
parent of that profile in `RESTORE_FAILED`, and `spec004_mutation.target_safe` re-reads every recorded change
injection read-only and finds its pre-change digest. `engine/execution.py` needed no change (the executor writes
the block itself, as N-02 does). H-03 and N-02 cleanup paths are unchanged.

### ID-004-19 — Removal restore order and step failures (T048)

The removal is restored right after the POST_REMOVAL read (scenario step order), before the storage probe, and
again in a `finally` if still applied. An adapter exception in a step is recorded as a step fact and leaves the
dependent assertion INCONCLUSIVE; cancellation runs restores and teardown, then propagates. Reads past the Run
deadline are skipped; restores and teardown are not. Only restore and teardown calls count toward the 120 s
restore budget.
