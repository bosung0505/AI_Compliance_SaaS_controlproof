# Spec 004 Implementation Decisions

## Status

- Spec 004 closure: T001~T097 complete (T087 NOT_REQUIRED); final converge recorded in validation.
- WhyYou integration 374b122: PR #6 fixture, #7 report embedder wiring and #8 approved P1 availability fix.
- First E-01 FAIL and D1-only child FAIL preserved. Official product child a5ad4676… PASS; new second-checkout
  E-01 4030503c… and E-02 970108fe… PASS/SUCCEEDED/VERIFIED. AWS and another PC remain unverified.
- Full ControlProof 939 PASS once; WhyYou scoped 188 PASS; later portability corrections scoped setup 12 PASS.

This log preserves historical checkpoints below. First factual results and sealed evidence are immutable;
implementation gates and actual target verdicts remain separate. ID-004-36 is the explicit owner approval
for reason fields and second-clean-checkout completion wording.

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
| T084 | runner/observer defect in an initial Run | complete | ID-004-34, R3 four D1 modes; original result unchanged |
| T085 | E01-A3 `TARGET_CONTROL_DEFECT` (P1) | complete | R1 actual A3 FAIL, ID-004-30 six-file proposal/approval |
| T086 | approved T085 fix | complete | PR #8 merged 374b122, focused 15/related 184 PASS |
| T087 | A1/A2 or E02 assertion TARGET_CONTROL_DEFECT | NOT_REQUIRED | Initial A1/A2 and E02 all PASS; T094 review below |
| T088 | child retest | complete | R3 runner-only child; R4 approved P1 child PASS and parent bytes preserved |

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

## Phase 6 US3 implementation (T052~T060), 2026-10-07

Status: `CONFIRMED`. No judgement rule changed.

### ID-004-20 — Criteria-version routes and criterion IDs (T055)

The adapter contract named `/v1/company/positions/{id}/competency-model-versions`, `/v1/company/competency-model-
versions/{id}/publish` and `If-Match`. WhyYou registers both under `APIRouter(prefix="/v1")` without `/company`, and
publish reads `If-Match-Version` (`company_management/api/company_routes.py`). The contract now names the real routes
and header. The version view (`CompetencyModelVersionView`) omits `criterion_id`, so the adapter reads criterion IDs
for the latest published version from `evaluation_criteria` read-only; the other-positions digest is read the same
way from `competency_model_versions`.

### ID-004-21 — The fake's "report mutates after change" option was a no-op (T053)

`FakeSpec004Adapters(report_mutates_after_change=True)` set each criterion weight to `100 - w`, which leaves the H-2
v1 weights (50/50) unchanged, so the E02-A2 FAIL test passed as PASS. The fake now adds 1 to each weight. Test
infrastructure only.

### ID-004-22 — E02-A2's binding precondition uses the published v2 ID (T058)

"The second report is bound to v2" is checked against the version ID returned by the v2 publish call, not only
against `latest_published`, so a target that serves an older version as latest (fake `second_version_binding_wrong`)
is `PRECONDITION_NOT_MET` rather than a silent PASS.

### ID-004-23 — E-02 restore, drift and recompute details (T057, T059)

- The v2 publication is the change injection (`CRITERIA_VERSION_PUBLISH`, restore `TEARDOWN`); its pre/post digest
  is the other positions' version projection. Teardown failure or a changed digest is `RESTORE_FAILED` and blocks
  `e02-scoring-freeze`.
- `SCORING_RULE_SOURCE_DRIFT` is checked twice before any write: by the `scoring.rule.source.read` capability probe
  (real target) and by `E02Executor.preflight` (so fakes and the CLI refuse identically).
- `API_ITEM_AVERAGE_SCORE` is recomputed from the stored axes minus those WhyYou's report read drops (a score without
  a citation, `_restored_axes`); E-02 VALID axes always cite, so this matters only for unexpected target data.
- `scoring_rule_source_digest` = sha256 of the rule copy ID, the pinned sources and the blob SHAs read in the Run.

## Phase 7 US4 implementation (T061~T069), 2026-10-07

Status: `CONFIRMED`. No judgement rule changed.

### ID-004-24 — Read ordering uses phase and file order, not `captured_at` (T067)

The bundle contract orders E01-A3/A4 reads by "phase and `captured_at`", but `ReportReadSnapshot` has no capture time
(data-model §7). The executor appends reads in step order, so verify checks that the removal lane's reads appear as
PRE_REMOVAL → POST_REMOVAL → POST_RESTORE in `report-reads.jsonl`; a restored injection must carry
`post_restore_digest == pre_projection_digest`.

### ID-004-25 — Which PASS facts verify re-derives from files (T067)

Verify re-derives E01-A1 PASS (four invalid modes `EMPTIED`, each with an existing receipt for the same criterion),
E02-A2 PASS (PRE_CHANGE and POST_CHANGE record digests equal in `report-records.jsonl`) and E02-A3 PASS (recompute
re-executed with the pinned copy; every comparison's `equal` re-evaluated). The record `state_digest` itself is not
recomputed: it is the adapter's digest over the full projection, which the bundle does not repeat. Results are
returned as `cross_reference_errors`, `redaction_violations` and `recompute_reexecution`; any error is `INVALID`
(exit 5).

### ID-004-26 — T061 verdict matrix was GREEN on first run (T061)

The matrix covers behaviour built in Phases 4~6 (executors and `judge_spec004_run`), so it had no RED state; it is a
regression guard. The other Phase 7 tests were RED first: T062 3 and T063 7 (missing projection fields), T064 8
(tampered and re-sealed bundles still VERIFIED), T068 4 (no cross-reference result before T067).

## Phase 8 retest machinery (T070~T071), 2026-10-07

Status: `CONFIRMED`. Sandbox diagnostics T072~T078 were not started (out of this session's scope).

### ID-004-27 — Spec 004 retest lineage (T071)

- A Spec 004 parent with an active `e01-citation-evidence`/`e02-scoring-freeze` block is refused; a `RESTORE_FAILED`
  parent additionally needs the `cleanup-confirm` maintenance record (`maintenance/<parent>.json`).
- The child inherits the parent scenario snapshot and profile, uses the same target, and has no queue topology. Its
  lanes, position and versions come from its own Run ID; any reused invitation/applicant/position/session ID refuses
  the child.
- `retest-diff.json` adds a `spec004` section: model fixture before/after, scoring-rule-source digest before/after,
  lane manifest digests and reused identities. `retest-link.json` carries the parent bundle digest and parent
  judgement SHA-256. Both are linked to EV4-10; verify reuses the Spec 003 retest-link checker with `EV4-10`
  (label `spec004-retest`), so a child is valid only while its parent bundle verifies unchanged.
- `cli retest` gives Spec 004 children a local environment snapshot with AWS/N-01/N-03 scope and no queue capture.

## Phase 8 sandbox diagnostics (T072~T078), 2026-10-07 — 진단, 공식 아님

### ID-004-28 — A failed timeline read stays visible (T078, CONFIRMED)

SD-1 showed `timeline: null` in every removal read: `read_api` dropped a non-200 timeline response silently, so the
bundle could not show whether the timeline read failed. The adapter now records
`{"status_code": N, "entries": null, "playback_status": null}` for a non-200 timeline (test RED first). The judge does
not use the timeline; it is supporting evidence only. The real timeline status is still unmeasured (rerun SD-1).

### ID-004-29 — E-02 diagnostics are blocked by WhyYou's report embedder wiring (PROPOSED at handoff; applied in update below)

Every E-02 report request failed with `RetryableError` (no report, no emission receipt). Captured by calling WhyYou's
own report handler once from a scratch harness (no WhyYou file changed, transaction rolled back): the requirement
retrieval calls `self._embedder.embed(...)` (`runtime/worker.py:553`) and the handler receives
`embedder=aws.embedder` (`runtime/worker.py:922`), the real provider, which raises `AwsEmbeddingProviderError` with
external AI blocked. The fixture embedder `report_embedder` (`runtime/worker.py:765`) is built but not passed. E-01
never reaches this path (Run-seeded versions have no job requirements); E-02 always does (product API
`job_requirements` `min_length=1`). Seeding E-02 versions directly would change H-1 (product-API versions), so no
ControlProof-side workaround is taken.
Options: (a) WhyYou one-line change `embedder=aws.embedder` → `embedder=report_embedder` with two tests (substitute on
→ fixed embedder; substitute off → the same `aws.embedder` object, production unchanged), PR to
`bosung/controlproof-n02-integration`, then rerun SD-2·SD-3; (b) leave E-02 unvalidated. Recommendation: (a). The
official E-02 Run requires this fix merged.

### ID-004-30 — T085 WhyYou minimal fix for P1 (PROPOSED, not applied)

SD-1 confirmed P1 on the diagnostic target: the company report read (`reporting/api/company_routes.py:401-436`
`get_report` → `repositories/postgres.py:911-925` `_latest_report` → `:818` `_report_from_row`) reads report items and
Evidence only, never `transcript_segments` (only the timeline does, `:613`). Proposal for T085, inside the H-4 (a)
indicator set: when building the report view, look up each Evidence's `transcript_segment_id`; if the segment is
absent, mark that Evidence `available=false` (indicator 4) — or return the citing axis score as `null`
(indicator 1). Stored rows are not rewritten. Apply only after the first official E-01 FAIL is sealed (Phase 9).

### ID-004-31 — E-01 teardown leaves worker-created reports (runner finding, open)

After E-01 teardown the DB still held 4 `reports` rows (and their items/Evidence) created by the worker for Run-owned
sessions: they reference the session without a foreign key, so the FK-catalog teardown does not reach them. They do
not affect later Runs (new session IDs) but are Run-owned residue. Fix in T078 continuation: delete `reports` (and
dependents) by the Run's `interview_session_id`s before deleting the seeded rows, with a failing test first.

### ID-004-14 — Update

E-02 diagnostics measured what an absent report costs: the Run waits to its deadline (557 s and 558 s wall for the
whole command, 540 s journey budget). A refused report behaves the same because Spec 004 lanes get no refusal
receipt. Decision (a) stands; (b) observer extension remains PROPOSED and becomes worth doing if refusals are expected
in official Runs.

### ID-004-29 — Update: option (a) approved and merged (2026-10-07)

The user authorized step 1. WhyYou PR #7 changes only the report handler embedder argument to `report_embedder`
and adds two worker-composition tests. Before the fix the enabled case fails on the AWS fallback and the disabled
case passes; after it, runtime/reporting scoped suites pass (172 tests). Disabled mode retains the same AWS
embedder object. Fix `77df3137aaf61003d4679f20276333b5eac2c290` merged into `bosung/controlproof-n02-integration`
at `ce8d8620d2b2fec7f448ae312cf13334b408c01a`; main unchanged. See validation continuation for commands and limits.
This closes the wiring change, not SD-2/SD-3 or an actual E-02 verdict: T074/T075 remain pending, official Runs
remain NOT_RUN. ID-004-30 / P1 and ID-004-31 are unchanged.

## Phase 8 continuation decisions (2026-10-07)

### ID-004-31 — Update: Run-owned report and search projection cleanup (CONFIRMED, resolved)

T078 adds transactionally scoped deletion of worker-created reports whose company/session IDs come from the
adapter's stored Run seed rows, before the FK-catalog seed walk. Report FK descendants and the no-FK
`assistant_retrieval_documents` projections are deleted only for those company/report IDs. No caller-supplied
unregistered session is a deletion root. Failure preserves rows, ownership and credential entries for retry.
RED first, then transaction-backed ownership/rollback tests and real PostgreSQL E-01/E-02 zero-residue checks
PASS (validation continuation). Other-Run/company data and protected position/version digests survive.
Historical residue was handled separately by artifact-owned IDs; sealed evidence was not rewritten.

### ID-004-32 — Contribution order is presentation, criterion identity is the comparison key (CONFIRMED)

Live SD-2 exposed equal keyed values in different array orders. T078 compares only `scoring_inputs.criteria`
and API `scoring_breakdown.contributions` by unique string criterion_id, checking every field/value with the
existing exact integer and 1e-9 float rules. Missing/duplicate/wrong IDs and changed values still FAIL; raw
observed order is preserved. Other arrays keep positional equality. FR-033 arithmetic and pinned rule-copy
blobs are unchanged. New recompute records declare `CRITERION_ID_V2`; absent policy means `POSITIONAL_V1`,
unknown policy is invalid. The verifier applies the declared rule only to the two named field/target pairs.
This keeps the original positional FAIL bundle VERIFIED unchanged. The intermediate judge/verifier mismatch
bundle stays INVALID; a new diagnostic proves the corrected judge+verifier together. RED/GREEN and live
source/manifest mapping are in validation. This is runner comparison alignment, not a relaxed score verdict.

### ID-004-33 — Synthetic recording locator follows the tenant contract (CONFIRMED)

SD-1 supporting timeline GET returned 500: the synthetic `controlproof/{asset_id}` key violated WhyYou's
existing tenant prefix guard. Change only the seed recording key and its matching transcript audio key to
`companies/{company_id}/controlproof/{asset_id}`. The IDs remain Run/lane-owned; no real media upload or
WhyYou product change is needed. Existing seed test gains tenant-prefix and audio/video-link assertions;
EXPECTED RED then scoped GREEN. New diagnostic timeline reads are 200 with 2/1/2 entries across removal and
restore. ID-004-28 is now measured; its error visibility behavior remains. P1/E01-A3 FAIL remains unchanged,
and ID-004-30 stays PROPOSED until the first official E-01 result is sealed. See validation for preserved 500
bundle and new Run. These changes stay in the T035/T036/T018/T058/T067 owning files under T078.

### ID-004-34 — T083 factual cause classification (CONFIRMED, 2026-10-07)

Initial official E-01 parent `09c9d9bb-82a3-4485-9c9d-e9721f2452e4`, manifest SHA256
`7f622a3381e6c03dac907f55604f1f82c03e5101e33736b4f22bde50cc8475b2`, has one failing assertion:
`E01-A3` → `TARGET_CONTROL_DEFECT` (P1). Exact artifacts: `judgement.json` assertion E01-A3 identifies
item `01a1166d-1035-754c-a329-7b8bc954f0fc` as unexposed; `report-records.jsonl` E01_EVIDENCE_REMOVAL
PRE_REMOVAL/POST_RESTORE; `report-reads.jsonl` same lane PRE_REMOVAL/POST_REMOVAL/POST_RESTORE;
`change-injections.jsonl` EVIDENCE_SEGMENT_REMOVAL target `6e06f7e9-2041-5f99-ac78-b0fc83e107c6`.
Removal was confirmed, Timeline decreased from 2 segments to 1, but the report retained the affected score
and citation without H-4. Reinsertion restores the original projection digest. At WhyYou `ce8d862`,
`reporting/api/company_routes.py` get_report / _report_view and `reporting/repositories/postgres.py`
get_report_for_session / _report_from_row do not check current transcript availability. This is not an
observer failure or unsafe restore. ID-004-30 remains the separate PROPOSED WhyYou remedy (T085/T086).

The same parent's `storage-probe.json` (SHA256
`5ded79933b98472a57e36a42e70983b0772d43212ac1d9bc3330647ceda625ab`) contains three modes and no
OTHER_CRITERION write/read. Class: `RUNNER_OR_OBSERVER_DEFECT` (FR-013 coverage omission, T084), not an
additional target assertion FAIL. ID-004-17's single-criterion design caused the omission. T084 keeps
FR-013 and the diagnostic-only verdict contract; it adds a second Run-owned VALID criterion and uses its
actual same-report, different-criterion Evidence. Seed identities select the target and donor regardless
of row order. Report/run/lane/subject/version/item/answer/segment/quoted-axis provenance is checked before
any write; unverifiable prerequisites produce NOT_RUN / PROBE_PREREQUISITE_UNVERIFIED, never partial
four-mode coverage. The source IDs are recorded in additive `other_criterion_source`; legacy parent
bundles remain valid and unchanged. This supersedes ID-004-17 for new Runs without rewriting its history.

E-01 A1/A2/A4 and E-02 A1~A3 all PASS; there are no INCONCLUSIVE assertions in either initial Run.
Both restores SUCCEEDED, digests match and owned residue is zero: no RESTORE_OPERATOR_DEFECT observed.
T087 is evidence-backed NOT_REQUIRED for the current initial Runs. The original FAIL remains sealed;
fixing D1 cannot resolve the independent E01-A3 product FAIL or complete Spec 004.

T084 actual child follow-up: `ec0c895d-4617-457a-94ce-7d0198e1c6a5` (ControlProof `69d3c00`,
WhyYou `ce8d862` unchanged) observes all four D1 modes. Evidence, exact restoration and immutable parent
hashes VERIFIED; no reused lane identities. The child remains FAIL only for unchanged P1 / E01-A3.
T088 partial, not complete. The existing generic retest reason text wrongly implies a WhyYou change;
source snapshots and retest-diff show the actual ControlProof-only change. Preserve the sealed text and
review its wording separately; no retest implementation scope was added here. See validation for commands,
manifest, timings and the full-command failure / scoped correction record.

### ID-004-30 — T085 review: transcript availability read projection (PROPOSED, 2026-10-08)

The first official P1 FAIL is sealed and classified by ID-004-34. The next-step request authorizes this
review; the concrete product change and discovered contract-file expansion require confirmation before
T086 implementation (FR-051, plan §8 step 4, and the user's stop/report rule for unexpected scope).

Recommended H-4 indicator: EvidenceView.transcript_available, a boolean describing the currently matching
transcript row at report-read time. Present owned row → true; missing/mismatched row → false; reinserting
the same row → true again. This does not assert recording playback, citation sufficiency, external AI
accuracy or hiring suitability. It is response metadata, not a frozen scoring input. Axis/average/overall
scores, original Evidence, stored report rows and scoring inputs are not rewritten or recomputed.
The alternative axis score=null is allowed by H-4, but would also require resolving how item averages,
aggregate breakdown and frozen score presentation relate to that hidden score; it is not recommended for
this minimal correction. No scenario version or ControlProof judge/adapter change is needed: both already
accept transcript_available=false as the agreed H-4 availability indicator.

Implementation design:
- Add transcript_availability_for_report(context, report) to the ReportingRepository protocol and
  SQLAlchemyReportingRepository in postgres.py. Reject a report outside the tenant; use a single bounded
  query selecting referenced segment/turn IDs with company_id, interview_session_id and segment IDs.
  Map each report Evidence ID to whether its own segment and answer_turn_id match. No transcript text or
  media locator is selected; no per-item queries. No Evidence → empty map without querying. A database
  error propagates as an error, not a fabricated false or true.
- get_report fetches the owned report, obtains this availability map and passes it into _report_view.
  Only a checked Evidence gets transcript_available. Existing pure view callers without a map omit the
  optional field, rather than inventing availability. Report-not-ready/failure branches and existing audit
  behavior retain their contracts. The company report API is the observed path; no console UI work is
  included in this proposal.

Required concrete T086 file allowlist (WhyYou, relative paths):
1. backend/src/interview_evidence/reporting/repositories/postgres.py
2. backend/src/interview_evidence/reporting/api/company_routes.py
3. packages/contracts/openapi/root.yaml (EvidenceView optional boolean property)
4. packages/contracts/generated/typescript/openapi.d.ts (same optional field)
5. backend/tests/unit/reporting/test_report_evidence_availability.py (new)
6. backend/tests/unit/reporting/test_report_view_contract.py (EvidenceView schema coverage)

Files 3/4 expand the original two product-code candidates. EvidenceView currently sets
additionalProperties=false and lacks this field; returning it without updating the API contract would be
incorrect. The consumed TypeScript contract also needs the additive optional property. The generator was
removed in 7d977f7: package.json has no contracts:generate/check; generated/README.md explicitly requires
manual OpenAPI/TypeScript edits. The Python generated contract is documented as stale and has no consumer,
so it is outside this allowlist. No generator reinstall or broad regenerated-file changes are proposed.

Tests before implementation (intended RED): genuine report Evidence has true with an owned segment;
deleting that segment yields false only on the affected Evidence; exact reinsertion restores the entire
report view; stored report/items/Evidence and frozen weights/scoring remain unchanged. Negative tests cover
wrong company/session/answer turn, missing segment, tenant rejection and DB query failure. Empty Evidence
performs no lookup and a multi-item report uses one lookup. A company-report route wiring test verifies
that the HTTP path supplies the map; the schema test validates EvidenceView properties for true/false and
legacy omitted-field responses. Existing unquoted/unaffected items remain identical.

Gates after approval: personal branch yeonwoo/controlproof-e01-e02-report-evidence from integration ce8d862;
RED → minimum implementation → reporting/runtime unit suites + focused repository/schema/wiring tests;
ruff on changed Python and TypeScript contract typecheck. Record existing unrelated failures separately,
never call them PASS. Push to fork and open a PR with base bosung/controlproof-n02-integration (never main).
T086 ends with a reviewable PR; merging and T088 official product-remedy child are separate actions.
All original parent/D1-child bundles remain immutable. Approval pending; no WhyYou code/contract/test was
changed, no branch/PR/Run was created during this T085 review.

### ID-004-30 — T085 approved / T086 implemented (CONFIRMED, 2026-10-08)

After the explicit six-file approval question, the user said "바로 진행시켜봐". This confirms the recommended
response-only transcript_available indicator and all six files in the preceding proposal. T085 complete.
Personal WhyYou branch yeonwoo/controlproof-e01-e02-report-evidence started from integration ce8d862;
commit b15ba8a88be1f31b354638e42a9b828b34c06875 contains exactly that allowlist. Repository lookup selects only
segment/turn IDs in the tenant/session and compares each Evidence's segment/answer pair; one batch, no
lookup without Evidence, foreign report rejection before SQL, DB errors propagated. Company report GET
passes the map to the view. Checked fields are true/false; unchecked pure-view calls omit them. OpenAPI
and consumed TypeScript declare an optional boolean. Stored report/items/Evidence and frozen scoring are
unchanged; restoration restores the original response. No ControlProof judge/scenario change or UI work.

Intended RED: availability 8 failed / 1 passed; schema 3 failed / 3 passed (only missing implementation /
contract). GREEN focused 15 passed; reporting/runtime 184 passed; scoped ruff, test format, diff and company
console typecheck PASS. Existing dependency deprecation warnings remain. Initial lint formatting issues
were corrected within the approved files; no unexpected test failure remains.

Fork bosung0505/gbsa_aws created/reused for T086, branch pushed at b15ba8a. PR
https://github.com/jhkim0602/gbsa_aws/pull/8 targets bosung/controlproof-n02-integration (ce8d862);
OPEN/unmerged, six files. T086 complete as a reviewable PR, separate from fixture PR #6 and wiring PR #7.
GitHub connector PR creation returned integration-permission 403; existing authorized user Git credentials
created the PR through GitHub API, with credentials only in process memory. PR metadata re-read confirms
correct base/head; no merge or actual Run performed. Parent/D1-child evidence and both mains unchanged.
T088 product-remedy validation and T089~T097 remain; automatic gate is not actual A3 PASS. Existing generic
retest-reason wording caveat remains separate from this six-file change.

### ID-004-30 — T088 live confirmation / Phase 9 closure (2026-10-08)

User authorized the next integration/fresh-READY child step. PR #8 merged to integration at
`374b122e1296c0159ccd88ed4763d358973c59cb`; merged source tree equals tested b15ba8a, no extra scope.
Official child `a5ad4676-333b-44d0-8657-95ab434f3b3d` of original E-01 `09c9d9bb…`, ControlProof
`8bbf36cdbef4c627dc078b40d3eca41441d471e9`, confirms A3 H-4 via transcript_available true/false/true and
A4 exact record/read restoration. A1~A4 PASS, restore SUCCEEDED, bundle VERIFIED, residue 0.
Original P1 FAIL and D1-only FAIL remain immutable; this later result does not replace their verdicts.

T084 runner coverage and T085/T086 approved product remedy are complete; T087 stays NOT_REQUIRED because
neither INCONCLUSIVE nor unsafe restore defect was found. T088 complete for the product-remedy child,
with all three previous manifests/files unchanged. Four D1 modes are observations, not target PASS claims.
E-02 PASS remains at ce8d862; latest 374b122 READY/MATCH is readiness, not a new official Run.
Earlier D1-only retest reason wording remains a bounded follow-up; current product-remedy reason is accurate.
Phase 10 T089~T097 remains required, including T094 conditional review and T091 final full gate. No
Spec Complete or AWS claim; Phase 9 status sync does not satisfy final T096/converge.

### ID-004-35 — approved verifier scan completion (CONFIRMED, 2026-10-08)

T090 exposed missing scans for manifest, YAML-named scenario snapshot and both child-lineage files:
8 genuine failures with synthetic secrets and matching hashes. User approved the proposed correction and
requested full Spec closure. The existing redaction policy now covers those files and registered structured
evidence; paths resolve inside the bundle before reads. This fixes FR-042/SC-004 enforcement, not WhyYou
behavior or assertion meanings. Original evidence is never rewritten. Related 192 PASS, final ControlProof
939 PASS and WhyYou scoped 188 PASS. Earlier stopped/red entries remain checkpoint facts.

Portable setup is confined to T092/T097 reproduction: dedicated loopback Docker resources, fixed synthetic
model/credentials, clean source checkout, no .env/cloud authentication, fresh observer roots and owned-process
stop without deleting evidence/volumes. It is not a new scenario, product UI or AWS validation capability.


### ID-004-36 — closure criterion clarification (CONFIRMED, 2026-10-08)

- Tasks: T092/T093/T096/T097; FR-040, SC-001/006.
- Conflict 1: original SC-001/FR-040 asked for a reason code on every status, while the inherited
  AssertionResult contract allows InconclusiveReason only for INCONCLUSIVE. PASS/FAIL detail, expected
  and actual already describe reasons. Owner explicitly chose the existing common contract: require
  reason_code for INCONCLUSIVE and factual reasons for PASS/FAIL. No model, verdict or sealed-row edit.
- Conflict 2: SC-006 said team PC, but T097 explicitly allowed a second clean checkout or teammate.
  Owner explicitly approved that second-checkout alternative after Q1/Q2 actual PASS, restore and verify.
  It demonstrates a separate source/resource setup on the same PC; it does not demonstrate another PC.
  The separate main-integration external-reproduction gate remains pending. AWS remains NOT_RUN.
- Authorization: user answer "두 문구를 위 방향으로 확정하고 완료" to the two concrete choices.
- Alternatives: introduce new PASS/FAIL code types and migration, or wait for a teammate PC. Neither is
  silently treated as done. Spec/Traceability/Product Brief/Decision Log reflect the approved choice.

### T094 — final conditional review and claim boundary (2026-10-08)

T084~T088 table above now carries evidence-backed completion/NOT_REQUIRED. T087's precise predicate
is an E01-A1/A2 or E02 assertion classified TARGET_CONTROL_DEFECT, not INCONCLUSIVE or unsafe restore.
All those initial assertions PASS, so that predicate is false. This supersedes the imprecise T088
explanation without changing its correct NOT_REQUIRED outcome. R1 A3 P1 triggered T085/T086/R4 only.

ID-004-34's approved two-criterion D1 correction and ID-004-23's five recompute comparison targets are
now reflected in Plan/Traceability. Four D1 modes are diagnostic observations, never four target PASSes.
ID-004-14(b) refusal-receipt extension stays optional PROPOSED and NOT_REQUIRED for Spec 004 v1: actual
report success was proved from DB records, all final assertions pass; absence still uses bounded polling.
Future refusal-heavy scenarios may propose the observer contract separately. R3's generic retest reason
mentions WhyYou despite its CP-only correction; source diff proves WhyYou unchanged. Keep those sealed
bytes and this bounded metadata wording limitation; it does not change linkage, classification or verdict.

No early WhyYou protection was added: R1 first truth preceded the six-file P1 fix. Automatic 939/188 gates
establish implementation regression safety; R4/Q1/Q2 independently establish the executed target facts.
No new product meaning, cloud verification, external AI quality or legal certification is claimed.
