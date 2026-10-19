# ControlProof repository instructions

## Read first

Before changing this repository, read these files in order:

1. `docs/TEAM_HANDOFF.md`
2. `docs/product/ControlProof_MVP_Scenario_Coverage_Matrix.md`
3. `docs/AI_SPEC_KIT_PLAYBOOK.md`
4. The active feature's files under `specs/`
5. `.specify/memory/constitution.md`

Do not infer current status from chat history alone.

## Product invariants

- AI scores are reference information, never automatic hiring thresholds.
- Only an authorized human records the final hiring decision.
- PASS applies only to the executed scenario and verified evidence. It is not legal certification.
- Preserve the first factual FAIL; fixes are verified in a new child Run.
- Keep `LOCAL_EMULATED` distinct from AWS, which is currently `NOT_RUN`.
- Use only synthetic applicants and local/test credentials.
- A missing runner is not `NO_TEST_TARGET`; use the documented readiness and reason codes.

## Workflow

Use one vertical Spec Kit cycle at a time:

`specify → clarify → plan → tasks → analyze → implement → actual validation → converge`

Do not start implementation before clarify, plan, tasks and analyze are complete. Do not mark a Spec complete
without actual validation or an explicit truthful non-execution status. Update Validation, Traceability,
`docs/TEAM_HANDOFF.md`, the scenario coverage matrix and README in the same closure change.

## Repository safety

- ControlProof feature work stays on its feature branch.
- WhyYou integration uses `jhkim0602/gbsa_aws` branch `bosung/controlproof-n02-integration` (`374b122`) or a personal
  branch based on it. Never commit or push ControlProof work directly to WhyYou `main`.
- Inspect both repositories' branch, HEAD and dirty state before an actual Run.
- Never commit `.env`, credentials or production data. Keep raw `.controlproof/` and `runs/` ignored.
  User decision D-029 (2026-10-19) authorizes sharing reviewed actual evidence and lineage in a dedicated
  tracked snapshot (proposed `review-data/bundles/`), after redaction/allowlist/integrity checks.
  Read `docs/research/Run_Record_Sharing_Preparation.md` before implementing this transition.
  Shared viewing is not independent re-execution; preserve frozen source SHAs, verdicts and original bytes.
- Historical one-time exception approved on 2026-10-02: the exact synthetic Spec 003 N-02 parent bundle
  `15cef078-ee24-4f0e-91ef-381e0f7a1cc2`, its matching cleanup maintenance record, and the matching
  WhyYou cleanup evidence JSON were published on the two Spec 003 feature branches for teammate handoff.
  Preserve those bytes. Later shared records follow D-029's reviewed snapshot policy rather than extending
  this raw-directory exception. Probe logs and credentials remain excluded.
- Do not rewrite or delete prior validation history to make a result look successful.

## Active web review work (2026-10-15)

User approved T093 (2026-10-16, `terminology.md`): UI uses 테스트/재테스트/테스트용 and compares
테스트에 넣은 AI 평가 with 서비스가 실제 저장한 결과. Preserve sealed text/history/user memos.

Current UX branch: `refactor/controlproof-web-ux` (based on `005-web-workbench-report`). The local web workbench is implemented. User approved T079~T084
in `specs/005-web-workbench-report/ux-redesign.md`: condition/expected/observed/evidence-first reading,
E-01 case observations and E-02 explanations, consistent shared styles and navigation across all screens.
Do not change sealed bundles, verdicts, execution safety, or add web Run/retest actions. Distinguish four
original E-01 rules from seven display conditions. Unsupported or missing facts must remain explicit.
Read current Spec005 validation for the UI check status; internal review is not non-author usability validation.
Spec005 final converge and external usability work remain separate.
User approved T089~T092 in `readable-results.md`: original V4 names, factual run summaries, human descriptions,
model-output/stored-value comparison and preparation last. E01-D1 remains documented separately, excluded from
primary condition sources and result summaries. Preserve its bundle/full inventory and never relabel it as a
model-validated result. E-01 primary cases did traverse the worker's model-response validation; fixtures are fixed
synthetic model outputs, not a test of autonomous external model generation.

## Earlier completed engine baseline

Spec 004 E-01·E-02 is Complete: T001~T097 and converge, T087 NOT_REQUIRED. ControlProof branch
yeonwoo/004-e01-e02-score-evidence; code checkpoint f75ada7, WhyYou integration 374b122 (PR #8).
Original E-01 FAIL preserved; official remedy child a5ad4676… PASS. Second clean-checkout actual Q1
4030503c… E-01 and Q2 970108fe… E-02 PASS/SUCCEEDED/VERIFIED, residue 0. Full CP 939 PASS once,
WhyYou scoped 188 PASS; subsequent wrapper portability fixes scoped setup 12 PASS. See final Spec004
validation/traceability, ID-004-36 and product Decision Log D-017 for approved completion criteria.
This paragraph records the older Spec004 baseline. Latest N-02 status is in the 2026-10-18 closure below.
Spec005 remains active; its final closure and external usability are separate.
For Spec004 reproduction use its quickstart and scripts/spec004_local.py, not historical N-02 setup.

## N-02 local closure (2026-10-18)

Current workspaces use `feature/n02-analysis-preparation`. Actual validation used separate clean
`validation/n02-20261018` local snapshots: CP `3ea1509`, WhyYou `e64ff9d`. Final child
`16dbd987…`: A1~A7 PASS, VERIFIED21, restore SUCCEEDED, owned DB residues0. Spec003 local scope
Complete; preserve all earlier INCONCLUSIVE/INVALID records. Use `scripts/n02_local.py` and latest
Spec003 Quickstart; explicitly select `scenarios/_N-02-analysis.yaml` (legacy default unchanged).
Original uncommitted UI edits are authorized and preserved. Fixed synthetic AI traverses real
product validation/storage; external model quality and AWS NOT_RUN. No main merge/remote push
authorized in that closure. Spec005 overall closure/external usability remain separate.

## Continuing integration branch (2026-10-18)

The user subsequently authorized a new branch, commits and push for the completed work.
Continue future fixes and remaining tasks on `fixes-and-remaining-work` in both workspaces.
ControlProof publishes to `origin` (`bosung0505/AI_Compliance_SaaS_controlproof`); WhyYou publishes
to the `fork` remote (`bosung0505/gbsa_aws`). Keep WhyYou upstream `main` unchanged.
The source SHAs in actual Run records remain the frozen validation SHAs, not later publication commits.
Exclude runtime logs, credentials and environment files from publication. The former exclusion of all new
bundles is superseded by D-029 for reviewed shared snapshots; raw runtime directories remain ignored.

## H-01 stage1 preparation (2026-10-18)

Active feature: `specs/006-h01-human-decision/`, branch `fixes-and-remaining-work` in both repos.
Stage1 specification/planning/analyze/preparation code and automatic checks completed; actual
H-01 remains NOT_RUN. No official profile/Run/catalog/UI promotion. The injected lifecycle is
not a live fixture lifecycle: stage2 must bind normal report preparation/owned cleanup, actual
principals, SYSTEM transaction/service, actual assistant operation and official evidence/CLI.
Do not invent AI authentication or treat company actor-header spoofing as an AI test. Missing
AI/refusal evidence and unresolved final-stage batch-route coverage cannot produce whole H-01 PASS.
WhyYou adds only a disabled local/test SYSTEM helper and restores a stale H-01 SQL test; existing
product authorization/composition unchanged. Final CP122 PASS / WhyYou224 PASS; see validation.

## H-01 stage2 actual validation (2026-10-18)

Final `39a0d317-b36d-4cf1-8b09-aebb404d5891` A1~A6 PASS, VERIFIED17, restore SUCCEEDED, independent read-only44-table
owned residue audit0. Sources CP2edd0b0 / Why08c397e; local validation clones, not publication SHAs.
First actual7d6024ce FAIL and9a297b8d/faa0a306 INCONCLUSIVE preserved. HiringService final-stage
human guard fixed only after sealed factual FAIL. H-01-only assistant API fixed model binding;
no new AI role. Current scope6 executed /3 NOT_RUN /3 NO_TEST_TARGET. H-02/AWS/external model
quality/Spec005 full closure remain separate. Web final QA and document convergence completed 2026-10-19; Spec006 local scope Complete.
Earlier stage1 NOT_RUN paragraph above is historical. Keep original fixes-and-remaining-work branches.

## H-02 stage1 preparation (2026-10-19)

Active Spec007, both fixes-and-remaining-work. Stage1 source discovery/spec/plan/analyze/collector
and automatic checks complete; actual H-02 NOT_RUN, no official profile or READY. Current source
inventory42 UNREVIEWED entries,204 Python files,161 import-closure paths. Collector BLOCKED on
privacy_deletion's indirect runtime attribute; source trace is documented, actual binding/effect
required in stage2. Do not suppress unknowns or infer safety from tool names/reader protocols.
Assistant stage lookup can invoke legacy null-stage backfill through ensure_default_stages;
preserve as an actual-review candidate, not an already-tested FAIL or a preauthorized product fix.
Stage2 must include source/actual composition, dispatch/effect review and low/high-score human
independence; no new AI actor. Existing H-01 source/history preserved,12/6/3/3 unchanged. See Spec007
validation/traceability/inventory-review/quickstart. No H-02 product change/actual/commit/push yet.

## H-02 stage2 local completion (2026-10-19)

Spec007 Complete. Final c12c2ce8-f607-4be3-9524-0dec27dc7260 A1~A6PASS/VERIFIED19/restoreSUCCEEDED;
independent44-table residue0. Frozen local sources CPf3ede39 / WhyYouaf36f25. First factual FAILdd52deb1
and initial INC9532d923 preserved. Legacy assistant answers could backfill final acceptance without
human review; after sealing FAIL, production pipeline reader narrowed to repository-only facade.
Actual4readers unchanged and same-position/version35accept/90reject human controls passed. Source42
items fully reviewed/actual runtime reconciled; fixed synthetic model, AWS/externalquality outside scope.
Shared QA22pages/20panels and catalog12/7/2/3 converged. Earlier stage1 NOT_RUN paragraphs are historical.
Keep fixes-and-remaining-work, original H01/N02 artifacts and historical exception unchanged. At this closure,
new bundles, credentials and runtime logs stayed ignored; reviewed bundle sharing later follows D-029.
No H02 commit/push in this closure. See Spec007 actual-closure.


## Remediation history display (2026-10-19)

User authorized Spec005 T096~098: H02 overview/result/compare shows discovery FAIL→separate WhyYou
development remedy→ControlProof retest PASS with actual before/after facts. Keep initial INC and
first FAIL, version/parent integrity checks, and development-note vs sealed-observation provenance.
Never infer a target fix from a later PASS or source SHA change. Other scenarios' remediation audit
is docs/research/WhyYou_Remediation_History_Audit.md; E03 includes a CP normalization fix, N02 includes
prior consent guards and later test-model setup, E02 started PASS. This UI/audit closure changes no
WhyYou source or sealed verdict. Full Spec005 external usability remains separate.

## Shared actual records preparation (2026-10-19)

D-029 replaces the local-only handoff policy with shared actual result snapshots so teammates can view
the same records. Spec008 implements review-data/snapshot.json and25 actual records/600 sealed files.
Default web mode verifies and opens the shared snapshot; explicit --run-root/env selects the original
local mode. Shared mode ignores PC readiness/memos, rejects POST and fixes display time to KST.
Keep missing N02 history explicit and the original INVALID attempt blocked; preserve all original
bytes/source SHAs/verdicts. Display code/catalog/scenario JSON hashes are pinned; future relevant
changes require a reviewed new snapshot context, never resealing evidence. Keep /review-data/** -text.
Read specs/008-shared-run-records/validation.md and review-data/README.md for current validation/launch.
The isolated Git clone test is shared-view validation, not independent WhyYou re-execution. Preserve
D-014/D-018 as historical decisions and D-019's actual reproduction scope.

## Spec 009 N-01·N-03 stage1 preparation (2026-10-19, 연우)

Active feature: `specs/009-n01-n03-notice-scenarios/`, branch `009-n01-n03-notice-scenarios` (from
`fixes-and-remaining-work` `b76af4c`; WhyYou `bosung0505/gbsa_aws` `fixes-and-remaining-work` `0166d9e`).
Decision D-030. The earlier `006-notice-authority-scenarios` branch (Spec 006 draft covering N-01·N-03·H-01·H-02,
its own D-024) is superseded and must not be merged; H-01/H-02 follow Spec006/Spec007 above. Register the two
profiles `N01_NOTICE_V1`/`N03_STALE_CONSENT_V1` the same way H-01/H-02 were registered (models canonical,
scenario validation branch, runner registry, CLI maps, evidence REQUIRED_FILES/verify_links/verify_facts,
retest branch, presentation). Scenario schema `controlproof.scenario.v9`, bundle contract
`controlproof.bundle-profile.spec009.v1`, evidence ids EV9-01~07. Keep catalog 12/7/2/3, N-01/N-03 official
NOT_RUN and `tests/unit/test_catalog_matrix_parity.py` unchanged until Spec 009 closure. Do not modify WhyYou;
the applicant app is started only by the harness (`scripts/spec009_local.py`, API port 8080 because the vite
proxy target is fixed). No actual Run, npm/playwright install, commit or push without the user's explicit approval.
Report documentation mismatches instead of editing other specs. On this branch `scripts.share_records --verify` and the
default shared web mode are expected to refuse ("Snapshot display code/catalog differs") because the snapshot pins
`b76af4c` code; the real gate is that each of the 25 `review-data/bundles` keeps its recorded verification result.
A new shared snapshot (new snapshot_id, bundle bytes and verdicts unchanged) is built at Spec 009 closure under 보성's review.
