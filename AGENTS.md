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
- Never commit `.env`, credentials, production data, `.controlproof/`, or `runs/`.
- Historical one-time exception approved on 2026-10-02: the exact synthetic Spec 003 N-02 parent bundle
  `15cef078-ee24-4f0e-91ef-381e0f7a1cc2`, its matching cleanup maintenance record, and the matching
  WhyYou cleanup evidence JSON were published on the two Spec 003 feature branches for teammate handoff.
  Preserve those bytes; do not extend this exception to later Runs, probe logs, credentials, or other artifacts.
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
Exclude runtime logs, new bundles, credentials and environment files from publication.
