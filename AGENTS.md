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
Stage 1 done 2026-10-20: commits `6bf2a53`..this docs commit (T001~T014 plus recovery path), automatic gate 1674 passed /
1 skipped with ruff clean (`specs/009-n01-n03-notice-scenarios/validation.md`); actual N-01·N-03 NOT_RUN; catalog 12/7/2/3 unchanged.

Closure 2026-10-20 (D-030): N-03 final `f27b68e8-0df8-46b3-a198-c7917c2f08bb` PASS (N03-A1~A3 only; policy swap injection,
near-swap submission and analysis policy attribution stay unverified). N-01 parent `48a70f5e-aa62-41fc-bf58-3624a6102b4f` PASS
(measurement v1, preserved) → final child `d3aac7d9-0a52-4f9a-9c8f-f6e1f7b6de18` PASS (measurement v2). The v2 change was a
ControlProof executor defect (missed hidden/transparent/clipped/line-clamped notices found by real-Chromium negative controls),
not a WhyYou change; `engine/n01.py` keeps the v1 rule for v1 records so sealed parents re-verify unchanged. All three Runs are
VERIFIED with 44-table residue 0. Catalog/matrix are now 12/9/0/3 (`tests/unit/test_catalog_matrix_parity.py`). Do not rewrite
`cp-local/spec009-local/s009/runs`. The proposed shared snapshot adding these three records needs 보성's review before publishing.
Closure follow-up 2026-10-20 (branch `009-closure-followups`): harness uses `getattr(subprocess, "CREATE_NO_WINDOW", 0)`; the N-03 scenario screen shows its unverified scope and limit from `scenarios/N-03.yaml`; shared snapshot is now `shared-actual-20261020-r2` (same 28 records and bundle bytes, display code re-pinned).

## Platform frontend preparation (2026-10-21)

User authorized stages 0 and 1 in parallel: baseline/specify/clarify/plan/tasks/analyze and data/HTTP/state/PNG contracts.
Feature branch `010-platform-ui-integration`, baseline `fixes-and-remaining-work` `fb219d0` + shared r2.
Read `specs/010-platform-ui-integration/spec.md`, contracts, tasks and validation before continuing.
This stage does not implement the new UI/routes/PNG endpoint or change engine behavior. Keep existing API v1 semantics;
future UI projections are explicitly additive. Preserve 12/9/0/3 (N03 partial), 28 records/11 profiles/652 files,
27 VERIFIED/1 original INVALID, missing N02 history, source SHAs and original bytes. No new actual target Run.
Stage2+ implementation follows its own tasks after stage0/1 analysis; do not infer completion from prepared contract cases.
Keep the existing dirty `.gitignore` change and ignored UI proposal/design archives. No commit/push/PR/main merge in this preparation.

User subsequently authorized the next stage. Stage2 T009/T010 is complete: `/product`, `/guide`, catalog-based introduction,
common workspace shell and accessible local menu/tabs/checklist. Read `specs/010-platform-ui-integration/stage2-validation.md`.
Current preview requires the NEW local candidate `.controlproof/ui-integration-20261021/stage2-shared-r3/snapshot.json`;
its matching display code was verified, 28 records/652 sealed files unchanged. Default tracked r2 is preserved and intentionally
rejects this changed display code until the later reviewed default transition. Do not disable the check or rewrite sealed bytes.
Stage3+ (overview graph/list, detail migration, PNG endpoint) remains pending. No new actual target Run or publication.

Subsequent authorization completed stage3 T011/T012: `/` overview and `/results`/`/demo/results`, additive ui projections,
strict GET filters and whole-results reset. Existing API groups order and verdicts stay unchanged; ui groups order N/H/A/E.
Read `specs/010-platform-ui-integration/stage3-validation.md`. Current preview uses NEW candidate
`.controlproof/ui-integration-20261021/stage3-shared-r2/snapshot.json` (28 records/652 files unchanged).
Earlier stage2/stage3-pending statements above are historical. Stage4 detail/PNG and later stages remain pending.
Do not rewrite original snapshot or sealed bytes, disable display pinning, execute actual target Runs or publish from this UI closure.

Stage4 T013~T017 was subsequently authorized and completed: scenario_service, selected Run/condition cards,
current/sealed definition hashes, profile representatives/full history and strict reviewed PNG content endpoints.
Read `specs/010-platform-ui-integration/stage4-validation.md`. Current code/preview pair is
`.controlproof/ui-integration-20261021/stage4-shared-r4/snapshot.json`; original28 records/652 files remain unchanged.
Earlier stage4-pending statements are historical. Stage5 compare/report/preparation migration and default snapshot transition remain pending.
Keep original API v1 fields/semantics, null legacy fields, partial N03 and all original evidence. No new actual Run/publication.

Stage5 T018/T019 subsequently completed: child comparison and cause provenance/relationship safety, report22 items,
`/prepare` and DEMO counterpart, existing local preflight/memo presentation. Preparation GET reads current definitions/stored
readiness only, never scans Run archives or runs preflight. Only exact `/prepare` return input is newly allowed; server
redirects to the validated scenario anchor. Shared/DEMO forms remain absent; original API fields and immutable records stay intact.
Current preview requires `.controlproof/ui-integration-20261021/stage5-shared-r4/snapshot.json`. Read stage5-validation.
Earlier pending statements are historical. Stage6 integrated/PDF QA and stage7 default transition/team review remain pending.
Keep default snapshot/28 records/652 files unchanged. No new actual Run/WhyYou change/publication.

Stage6 T020/T021 subsequently completed:324 web/readmodel/security checks passed without skips, actual app keyboard/44 viewport
checks and Edge155 actual report PDF26 pages/22 content items validated. Use page links/aria-current in workspace nav; real product
workflow tabs remain tabs. HTML errors retain selected mode, JSON errors stay unchanged. Print hides skip links and uses A4/footer;
legacy missing environment refs stay absent and commit display retains raw source values. Read stage6-validation.md for evidence/limits.
Current preview uses `.controlproof/ui-integration-20261021/stage6-shared-r3/snapshot.json`; original28/652/default snapshot preserved.
Earlier pending stage6 paragraphs are history. Stage7 T022 team understanding/default transition/rollback remains pending.
No new actual Run, WhyYou edits, installs, publication, commit/push/PR/main merge.

## Spec010 final local frontend transition (2026-10-21)

Stage7 T022 completed on the user's instruction to treat team review as done and proceed. This records user acceptance,
not a newly observed non-author usability session. Spec010 local frontend scope is Complete (T001~T022).
Default `review-data/snapshot.json` is now the exact reviewed stage6 r3 JSON (`shared-ui-stage6-20261021-r3`), matching current
display code. Old r2 bytes are preserved at `review-data/snapshot.shared-actual-20261020-r2.json`; baseline.json is unchanged.
Earlier default-preservation/pending-transition instructions describe their stage, superseded by this authorized promotion.
Keep all28 records/652 sealed files, INVALID/missing states, N03 partial scope and API meanings unchanged. Candidate builder
resolves only the exact frozen SHA of the original or named archived source. Never disable display pins or reseal evidence.
Read `specs/010-platform-ui-integration/quickstart.md` and `stage7-validation.md` for current launch/rollback/evidence/limits.
Default CLI/HTTP17 requests,51 distinct transition/shared checks, actual app navigation and old fb219d0 loader+r2 verification
passed; stage6 code/viewport/PDF checks still apply to identical display bytes. Current normal-launch preview uses8784;
existing8782 stays alive. Work is uncommitted/unpublished; remote delivery, Spec005 full closure and external usability remain
separate. No new actual Run, WhyYou edits, installs, publication, commit/push/PR/main merge.

## Presentation information hierarchy follow-up (2026-10-22)

User requested on-demand annotations and a cleaner real-product presentation. T023/T024/FR-017 completed. Base shell now has
one native closed `verification-info` details containing source/snapshot/hash, target/environment/AWS and interpretation notes.
Keep N03 partial/result/error states and SHARED/DEMO distinction visible; report's22 contents and sealed evidence remain intact.
Default is now `shared-ui-presentation-20261022-r1`; preceding r3 JSON is preserved byte-for-byte beside it. New display pin verified;
all28/652 original bytes/records/target/missing states unchanged. Read `presentation-polish.md` for95 tests and8 actual viewport/open
state/keyboard checks. Latest preview8785 uses the verified candidate identical to default. Earlier r3 default/8784 is history.
No new actual Run, dependencies, PDF generation, publication or commit/push/main merge.

## Explicit ControlProof main publication approval (2026-10-22)

The user explicitly authorized committing and pushing the completed project to ControlProof origin/main. This supersedes
earlier no-publication/no-main instructions for this release only; WhyYou remains untouched. Future feature work still uses
feature branches. Release scope includes the existing fb219d0 ancestry (172 commits beyond initial main) and Spec010 UI work.
Read `specs/010-platform-ui-integration/main-publication.md` for checks and provenance. Recursive display hashes now include
all5 nested HTML partials; add/edit rejection tests prevent missing these in future shared contexts. Preserve old snapshot
JSONs and immutable28/652 records; current default is `shared-ui-main-20261022-r2`. Source/UI scope/interpretation unchanged.
No force push, new actual Run, external SaaS deployment or source change in WhyYou is authorized by this publication.
