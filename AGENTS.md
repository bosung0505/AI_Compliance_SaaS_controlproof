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
- WhyYou integration uses `jhkim0602/gbsa_aws` branch `bosung/controlproof-h03-integration` or a personal branch
  based on it. Never commit or push ControlProof work directly to WhyYou `main`.
- Inspect both repositories' branch, HEAD and dirty state before an actual Run.
- Never commit `.env`, credentials, production data, `.controlproof/`, or `runs/`.
- Do not rewrite or delete prior validation history to make a result look successful.

## Current next feature

Spec 003 is N-02: consent must be durably completed before document analysis, recording or AI assessment starts.
Specify, clarify, plan, tasks and analyze are complete; the re-analysis has no CRITICAL, HIGH or interpretation-
changing MEDIUM findings. The next step is `$speckit-implement`. Use every artifact under
`specs/003-n02-consent-order/` and the source baseline. Keep pristine baselines,
deep-boundary prerequisite fixtures and post-attempt effect deltas distinct. Do not pre-fix a suspected WhyYou
consent guard before sealing the first factual actual-Run result.
