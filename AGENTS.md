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
- WhyYou integration uses `jhkim0602/gbsa_aws` branch `bosung/controlproof-n02-integration` (`ce8d862`) or a personal
  branch based on it. Never commit or push ControlProof work directly to WhyYou `main`.
- Inspect both repositories' branch, HEAD and dirty state before an actual Run.
- Never commit `.env`, credentials, production data, `.controlproof/`, or `runs/`.
- Historical one-time exception approved on 2026-10-02: the exact synthetic Spec 003 N-02 parent bundle
  `15cef078-ee24-4f0e-91ef-381e0f7a1cc2`, its matching cleanup maintenance record, and the matching
  WhyYou cleanup evidence JSON were published on the two Spec 003 feature branches for teammate handoff.
  Preserve those bytes; do not extend this exception to later Runs, probe logs, credentials, or other artifacts.
- Do not rewrite or delete prior validation history to make a result look successful.

## Current next feature

Spec 004 is E-01·E-02: scores require valid evidence and reports freeze scoring inputs. Active ControlProof
branch is `yeonwoo/004-e01-e02-score-evidence`; WhyYou is `bosung/controlproof-n02-integration` (`ce8d862`, PR #7
merged). T001~T078 complete, including Phase 8 diagnostics and runner corrections (ID-004-31~33). Diagnostic
E-02 A1~A3 PASS; E-01 A1/A2/A4 PASS and A3 FAIL (P1). Official E-01/E-02 and AWS remain `NOT_RUN`. Next T079:
fresh preflights on clean committed sources; T080/T081 require approval. Read the latest Phase 8 continuation
in validation. Spec 004 is not Complete. Do not pre-fix P1 before sealing the first official E-01 result.
