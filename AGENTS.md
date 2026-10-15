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

Current UX branch: `refactor/controlproof-web-ux` (based on `005-web-workbench-report`). The local web workbench is implemented. User approved T079~T084
in `specs/005-web-workbench-report/ux-redesign.md`: condition/expected/observed/evidence-first reading,
E-01 case observations and E-02 explanations, consistent shared styles and navigation across all screens.
Do not change sealed bundles, verdicts, execution safety, or add web Run/retest actions. Distinguish four
original E-01 rules from seven display conditions. Unsupported or missing facts must remain explicit.
Read current Spec005 validation for the UI check status; internal review is not non-author usability validation.
Spec005 final converge and external usability work remain separate.

## Earlier completed engine baseline

Spec 004 E-01·E-02 is Complete: T001~T097 and converge, T087 NOT_REQUIRED. ControlProof branch
yeonwoo/004-e01-e02-score-evidence; code checkpoint f75ada7, WhyYou integration 374b122 (PR #8).
Original E-01 FAIL preserved; official remedy child a5ad4676… PASS. Second clean-checkout actual Q1
4030503c… E-01 and Q2 970108fe… E-02 PASS/SUCCEEDED/VERIFIED, residue 0. Full CP 939 PASS once,
WhyYou scoped 188 PASS; subsequent wrapper portability fixes scoped setup 12 PASS. See final Spec004
validation/traceability, ID-004-36 and product Decision Log D-017 for approved completion criteria.
Another-PC reproduction/main integration remain pending; AWS NOT_RUN. Spec003 remains INCONCLUSIVE
with final converge pending. Spec005 is the active web work; its final closure remains pending.
For Spec004 reproduction use its quickstart and scripts/spec004_local.py, not historical N-02 setup.
