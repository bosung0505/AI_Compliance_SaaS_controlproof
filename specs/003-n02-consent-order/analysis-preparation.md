# N-02 문서 분석 후속 작업 — 1단계

Date: 2026-10-18. User authorized preparation only, then a separate actual-validation stage.
Status: stage-1 implementation and scoped automatic validation finished; local source changes
are not committed. Actual-stack validation, official verdict and UI closure remain stage 2.
Source: ControlProof `bafe019` + existing uncommitted web changes; WhyYou `374b122`.
Both work branches: `feature/n02-analysis-preparation`. Existing changes are preserved.

## Specify / clarify

The recorded child remains `INCONCLUSIVE`. ID-003-18 lacked document result evidence because
the isolated worker used external analysis dependencies while the substitute covered reports only.
Prepare a deterministic local/test document strategy model and embedding wiring. Preserve product
consent authorization, strategy validation, persistence, observer and judge contracts.
No new actual N-02 Run, faults, official verdict changes, web changes or publication in stage 1.
Stage 2 performs preflight, parent-linked actual validation, cleanup/verify, readable N-02 UI and closure.

Clarified choices (no open product decisions):
- A new opt-in fixture `n02-analysis-v1`, digest
  `092de5950a39ba3a7255c8696ffb073cddc65cda4615237044e3d910e32f9828`.
- It delegates report requests to the unchanged H-03 model and handles `build_interview_strategy`
  using only supplied criterion/source UUIDs. No guessed IDs, answers or final hiring decisions.
- Analysis replacement is enabled only for that fixture, local/test, external AI disabled and
  validated loopback endpoints. Legacy H-03/Spec004 analysis routing stays unchanged.
- Reuse the existing fixed embedder and native-text synthetic PDF; no OCR network response required.
- New explicit scenario file `scenarios/_N-02-analysis.yaml` (version 1.1.0, same profile/rules),
  excluded from default discovery. Legacy scenario snapshots and catalog remain unchanged in stage 1.
- Existing API/worker isolation digest includes the new fixture identity; stale or mismatched
  workers remain NOT_READY under the existing attestation checks.

## Plan / contract

WhyYou: extend the model registry, add strategy response and an analysis-dependency resolver;
wire only the analysis pipeline. Production/off defaults return original dependencies.
Use real StrategyService/pipeline validation and in-memory persistence in integration tests.
ControlProof: opt-in scenario permits only the new fixture; exercise readiness mismatch and
successful fake executor + sealed bundle verification. Test old snapshots unchanged.
The new fixture must not fall back to external AI for unsupported tasks or empty/malformed inputs.

## Tasks / traceability

- [x] T094 Specify, clarify, plan and analyze this extension before implementation.
- [ ] T095 Test-first WhyYou fixture identity, deterministic/source-bound strategy and routing.
- [ ] T096 Implement model/resolver and worker composition; preserve legacy routing.
- [ ] T097 Test native PDF → chunks → validated strategy, replay and consent regression.
- [ ] T098 Add opt-in scenario and readiness mismatch / executor bundle checks.
- [ ] T099 Run scoped regression/lint; record exact outcomes and limitations.
- [ ] T100 Synchronize Spec/Plan/Tasks/Traceability/Validation and entry documents with stage-1 status.

T095~T100 implementation/automatic-check work is finished as recorded below. Checkboxes remain
open pending source commits, following the existing task completion rule; they do not imply
missing implementation. No commit/push or actual execution was requested for this checkpoint.

FR-020~025 → T095~098 → strategy/pipeline, A5/A7 evidence contracts.
FR-034~041 → T098~100 → readiness, isolation, snapshot/bundle/history preservation.

## Analyze gate (before implementation)

CRITICAL/HIGH: 0; ambiguous MEDIUM: 0. New fixture identity prevents changing legacy semantics.
Opt-in scenario avoids changing old snapshots. Tests must prove real validation/persistence,
worker composition and missing-evidence rejection; automatic PASS never becomes actual verdict.
Known external conditions for stage 2: clean/versioned sources, local stack and managed workers,
valid local credentials/company, no active restore block, fresh preflight and accessible parent.

## Validation

Actual N-02: NOT_RUN for this extension. Historical bundles unchanged.

| Check | Result |
|---|---|
| New WhyYou model/routing tests before implementation | Expected RED: 11 failures (missing fixture/resolver) |
| CP opt-in scenario before implementation | Expected RED: missing scenario; then legacy model wrongly READY before allowlist fix |
| Bounded retest revision before implementation | Expected RED: 2 failures (snapshot argument unsupported) |
| WhyYou model + legacy fixture checks | 64 PASS in 0.75 s |
| WhyYou worker wiring + pipeline checks | 22 PASS in 10.36 s |
| CP N-02/readiness/scenario/CLI/adapters/lineage/bundle regression | 203 PASS in 87.24 s |
| CP final revision guards + new synthetic executor/lineage/tamper checks | 17 PASS in 10.01 s (7 overlap earlier regression) |
| CP E-01/E-02 orchestration and retest regression | 19 PASS in 23.20 s |
| WhyYou runtime/submission/reporting/interview/PDF/pipeline/delivery regression | 385 PASS in 11.76 s; deprecation warnings only |
| Ruff for changed code and `git diff --check`, both repositories | PASS |
| Published parent definition vs opt-in revision | Compatible, read-only check; parent integrity test PASS |

Meaningful integration checks exercise native PDF extraction, persisted analysis/chunks,
StrategyService validation/persistence, repeat processing/finalization without duplicate strategy,
and malformed output refusing strategy creation. Worker composition is tested with infrastructure
stubs; this is not a live API/worker proof. CP temporary synthetic bundles prove fixture-only
lineage, independent revision-diff verification and rejection after a rehashed false comparison.
Ten guard cases reject altered rule/step/timing/lane/evidence/capability or untrusted identity/digest.

Environment notes: initial default pytest temp/cache paths were inaccessible in the Windows
sandbox. A workspace `--basetemp` fixed pytest fixtures. Broader reporting tests also needed
TEMP/TMP in the workspace; an in-process HTTP TestClient then stalled under sandbox restrictions.
Those incomplete diagnostic attempts are not recorded as product failures or full-suite success.
The identical 385-test selection passed outside the sandbox with workspace temp directories.
No product change was made to work around these host restrictions.

Commands (repository-relative; temp roots are ignored, synthetic outputs only):

```powershell
# ControlProof: select all test_ files matching n02/spec003/readiness/whyyou_capability/scenario_profile_v3
$testFiles = @(rg --files tests | Where-Object { $_ -match '(n02|spec003|readiness|whyyou_capability|scenario_profile_v3)' -and $_ -match '[\\/]test_' })
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .controlproof/test-tmp/n02-cp-regression-1 --tb=short @testFiles
# The 203 count precedes the added 10 unit guards; final focused check:
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .controlproof/test-tmp/n02-new-final-1 --tb=short tests/unit/test_n02_fixture_revision.py tests/integration/test_n02_analysis_preparation.py
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .controlproof/test-tmp/n02-spec004-regression-1 --tb=short tests/integration/test_spec004_orchestration.py tests/integration/test_spec004_retest_lineage.py tests/integration/test_e01_citation_orchestration.py tests/integration/test_e02_orchestration.py
# WhyYou; TEMP/TMP point to an existing writable workspace directory:
.\.venv\Scripts\python.exe -m pytest -q -x -p no:cacheprovider --basetemp ../AI_Compliance_SaaS_controlproof/.controlproof/test-tmp/n02-wy-regression-unsandboxed --tb=short backend/tests/unit/runtime backend/tests/unit/submission_analysis backend/tests/unit/reporting backend/tests/unit/interview_engine backend/tests/unit/shared/test_pdf_document_extraction.py backend/tests/integration/submission_analysis/test_analysis_pipeline.py backend/tests/integration/test_worker_delivery.py
```

Use fresh bounded temp leaf directories on repetition; do not reuse/delete historical Run roots.

## Stage-2 entry conditions

Review/commit these sources and reconcile preserved prior UX changes; capture clean source identities.
Start local stack/API/managed workers with the same new fixture and verified loopback isolation.
Check current cleanup state and parent accessibility; perform fresh explicit-scenario preflight.
Then execute/verify a new parent-linked actual Run, inspect A1~A7 and recovered causal evidence,
check teardown/parent immutability, and only then update catalog, web records/readable N-02 text and
official closure documents. Stage 1 does not establish real environment READY, N-02 PASS or Spec003 Complete.

## Analyze follow-up — fixture-only scenario revision

Source inspection during T098 found that N-02 retest requires an identical scenario digest.
The opt-in definition therefore needs an explicit, tightly bounded exception before stage 2.
T098 includes this preparation: accept only legacy N-02 1.0.0 → analysis 1.1.0 with the exact
new fixture ID/digest, identical definition except `version` and `allowed_model_fixtures`,
and cryptographically validated parent/child snapshots. Record `scenario.changed=true` and
`revision_kind=MODEL_FIXTURE_ONLY`; independently verify this relation in the child bundle.
Any rule, step, timing, lane, evidence or other definition change remains refused. Ordinary
retests retain the identical-snapshot requirement; no broad bypass flag is introduced.
This is a preparation contract change, not an actual verdict change. Add positive child
lineage/verify and negative changed-rule/missing-snapshot tests before implementation.

Additional prerequisite found during implementation: default WhyYou submission requirements include
both resume and cover_letter. The old driver submitted only resume, preventing the normal completion
handler from generating a strategy. For the new fixture only, drive both through upload/PUT/register
with separate idempotency keys. Legacy adapter behavior and all frozen scenario rules stay intact.
