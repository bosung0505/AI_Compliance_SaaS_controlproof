# H-01 stage2 execution contract — 2026-10-18

User authorized stage2 in this turn. Stage1 records remain historical. This extends the same
Spec006 cycle: clarify → plan → tasks → analyze → implement → actual → converge.

## Clarified scope and plan

- Exercise final-decisions, batch final-accept and batch final-reject paths. Each path has five
  independent synthetic subjects: company control, valid applicant cookie, anonymous HTTP,
  SYSTEM product service/transaction, and actual authenticated assistant answers operation.
- Reuse existing report fixture rows, consent API and report worker. Never seed a ready report.
  A distinct deterministic report lane per case prevents prior accepted decisions contaminating denial.
- There is no AI principal. Ask the actual assistant to finalize the owned applicant; a new fixed
  local fixture emits a claimed decision plus an unsupported command. Verify real generation receipt,
  real assistant audit, response and independent unchanged DB state. This is ANSWER_ONLY, not a
  fabricated HTTP permission denial; external-model quality and H-02 tool-surface coverage remain out.
- SYSTEM uses the same SQL repositories, HiringService/ReportingHiringBoundary/FinalDecisionService,
  transaction rollback and reporting projection used by production. Observe batch writes as well.
- A denial HTTP response is a collector request/response record, not a product audit row. Distinguish
  those sources explicitly. Applicant session hash is checked against the owned DB row and liveness.
- Freeze clean local source clones before actual execution; originals stay on user branch.
  First factual FAIL stays sealed; product remedies run only as a child with source/diff lineage.
- New H01_HUMAN_DECISION_V1 profile, canonical scenario and bundle contract; existing CLI, hash
  verifier and read-only shared web review. Preserve every existing profile identity and bundle.
- Cleanup is company + explicit owned applicant/invitation/session/position/report IDs only, including
  HumanReview, idempotency, audit, outbox and assistant projections; independent residual count required.
  Errors retain safe codes, still attempt cleanup and seal INCONCLUSIVE/RESTORE_FAILED as appropriate.
- Actual result, source identities, hashes, restore and limitations drive catalog/docs closure.

## Tasks (dependency order)

- [X] S201 Add canonical profile/scenario, actual evidence links and semantic verification.
- [X] S202 Bind report preparation, HTTP identities, SYSTEM SQL services, assistant generation and cleanup.
- [X] S203 Add distinct opt-in assistant fixture/receipts; leave existing fixture identities unchanged.
- [X] S204 Verify meaningful regression/missing evidence/partial-write/tamper/ownership cases.
- [X] S205 Freeze sources, start separate local stack, preflight and first actual execution.
- [X] S206 Preserve any factual FAIL, repair scoped product defect, child actual retest if necessary.
- [X] S207 Independent bundle/residue audit; readable shared UI and browser validation.
- [X] S208 Converge validation/traceability/tasks/README/handoff/matrix/catalog/decision log.

## Preimplementation analyze

CRITICAL0 / HIGH0 / interpretation-changing MEDIUM0. Company caller and assistant operation are
separate facts. No-sources/generation-unavailable cannot PASS AI. Batch human controls require stage
change and real company audit, but do not falsely require a HumanReview the product batch path does
not create. SYSTEM acceptance is FAIL even if it is currently possible. Explicit field allowlists keep
credentials/raw model/report text outside evidence. Optional git commit hooks deferred; no mandatory
before_implement hook. Existing requirements checklist8/8 checked. No new technology/delegation needed.

## Actual preparation correction (before any product authorization remedy)

First frozen sources CP3fa2ddc/Why5012d9a passed isolated preflight. Actual preparation found
the reused report fixture commits consent but leaves invitation `consented`, despite containing a
completed synthetic interview and a real ready report. H-01 must not treat this as authorization
coverage. Preserve that attempt. The next source revision advances the synthetic prerequisite through
the real CompanyManagementPublic transition service (`consented → materials_submitted → analyzing →
ready → interviewing → completed`) before requesting the real report worker. This prepares fixture
state; it does not claim real document analysis or real interactive interview execution. Model
response validation/report persistence remain real. Record transition receipts and independent state.
Also add durable pre-write ownership journal, total deadline and independently recomputed cleanup gate.
No target authorization guard is changed by this preparation correction.

## First actual fact / scoped remedy

Actual 7d6024ce-02a6-4bac-ba35-35f85ae26af6 found SYSTEM batch accept/reject accepted with
pipeline writes. Final-decision service denied with rollback. Sealed first FAIL before remedy
(collector serialization was recovered from untouched pre/post journal, explicitly disclosed).
Add COMPANY_USER guard only for final stage names in HiringService.move_applicants, before writes.
Expected-RED8/normal nonfinal1 followed by236 PASS including SQL bidirectional regression.
Child faa0a306-678e-4af8-97ed-a842c52d8264 proved corrected SYSTEM denial but remained INCONCLUSIVE:
assistant API used real provider adapter against the loopback emulator, unlike the fixed worker.
H-01-only assistant composition resolver now binds fixed model/embedder to real API search/answers.
Legacy/default-disabled/production paths retain original dependencies; external endpoints remain loopback.
The earlier request hit the existing pipeline-answer shortcut; the next prompt avoids shortcut keywords
and requires actual model-emission + owned report source + audit + unchanged state before AI PASS.

## Final closure — 2026-10-19

Spec006 LOCAL_EMULATED scope Complete. Original execution dates and source SHAs above remain unchanged.
No actual Run was repeated merely because Docker was restarted. The independent DB audit was performed
while the isolated stack was running; its saved result is not represented as a fresh live DB check.

- Final WhyYou runtime/reporting/decision regression:237 PASS in10.76s; three known upstream deprecation warnings.
- CP readmodel/workbench/scenario/report, catalog parity and H-01 selection:44 PASS in11.23s.
- Browser workbench/scenario suite: initial32 PASS/2 FAIL because H-01 became runnable; moved the
  not-ready example to still-unexecuted H-02, then both failing cases PASS (27.66s). All34 cases green
  across the original run and targeted correction; no claim that an untouched full web suite was rerun.
- Final real-bundle browser QA after Korean audit-label changes:20 pages,32 proof panels,1280/1024px,
  all HTTP200, no horizontal overflow, page errors or console errors. Includes first FAIL, final PASS,
  compare/report, condition-scoped evidence and accepted E-01/N-02. AI proof screenshot visually reviewed.
- Local QA files stay outside Git in cp-local/h01-20261018/web-qa. All four original H-01 bundle hashes
  and copied viewer manifests preserved; independent ownership audit44 tables/residue0 retained.

Current catalog and matrix:12 total /6 executed /3 NOT_RUN /3 NO_TEST_TARGET. T001~T014 and
S201~S208 complete. H-02, N-01, N-03 remain unexecuted; AWS, external-model quality, other-PC
reproduction and Spec005 full/external-usability closure remain outside this completed scope.
No H-01 commit/push performed. Both user workspaces remain fixes-and-remaining-work.
