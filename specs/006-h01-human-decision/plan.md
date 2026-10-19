# Implementation Plan: H-01 preparation

**Branch**: fixes-and-remaining-work | **Date**: 2026-10-18 | **Spec**: spec.md
**Status**: Complete — LOCAL_EMULATED stage2 actual PASS, VERIFIED17, restore SUCCEEDED, independent44-table residue0; final web QA/convergence completed 2026-10-19. Design/analyze preceded implementation. The original stage1 plan below is historical; stage2.md records the authorized extension.

## Summary

Build a staged preparation module, isolated actor HTTP adapter, real-state observer, strict
assessment and cleanup-guaranteed driver. Add only a disabled local/test SYSTEM boundary helper
to WhyYou; keep all product guards, routes, actor types, fixed models and application wiring intact.
The opt-in manifest is not a registered official Run profile. Live lifecycle/profile/evidence and
AI execution binding are stage2, expressly unavailable facts cannot pass.

## Technical Context

- Python3.12, existing Pydantic/httpx/SQLAlchemy/PyYAML; pytest/Ruff. No new runtime dependency.
- Local files for preparation data; PostgreSQL observer prepared but never connected in stage1.
- Automatic mocked transports/lifecycles and WhyYou real product service with SQLite transaction fixture.
- Windows workspace; no Docker/service/credentials necessary to validate preparation.
- Scope: five canonical cases, isolated final-decision HTTP operation, company/invitation-scoped
  state projection, real internal SYSTEM transaction helper. No changes to existing engine registry.
- Preparation must be deterministic; request IDs and applicant/invitation IDs derive from Run/case.
- Exceptions expose types/stable codes only. No free text, raw tokens, applicant data or provider payloads.

## Constitution Check

| Principle | Design check | Status |
|---|---|---|
| I | Missing evidence/AI observation cannot PASS; pre/post independent facts required | PASS |
| II | Stage1 NOT_RUN; no READY or official/catalog promotion | PASS |
| III | Normal company control, no automatic hiring threshold, no new AI role | PASS |
| IV | Intent in manifest, product calls/SQL in adapter, assessment in engine/h01.py | PASS |
| V | synthetic owned IDs/local/test helper/default disabled/finally cleanup | PASS |
| VI | no old bundle/verdict changes; future FAIL requires child retest | PASS |
| VII | FR/SC/task/test mapping in traceability and validation | PASS |

## Project Structure

- engine/h01.py: strict preparation models, canonical ownership, manifest loader and assessment.
- engine/adapters/whyyou/h01.py: isolated HTTP and read-only DB projections.
- engine/executors/h01_preparation.py: lifecycle protocol and cleanup-safe execution driver.
- scenarios/_H-01-preparation.yaml; scripts/h01_prepare.py: explicitly preparation-only plan.
- WhyYou runtime/controlproof_h01.py: trusted local/test SYSTEM probe, factory/transaction injection.
- tests/unit/test_h01_preparation.py; tests/contract/test_h01_adapter.py;
  tests/integration/test_h01_preparation_driver.py; WhyYou test_controlproof_h01.py.
- specs/006-h01-human-decision/: spec, plan, research, data-model, contracts, tasks, analysis,
  validation, traceability, quickstart, checklist.

## Stage sequence

T001/T002 must finish before expected-RED tests. Implement tests then modules in task order.
Run preparation-only commands and meaningful target regressions. Converge stage1 status in
handoff/coverage/README/Product Brief/decision log; leave H-01 official NOT_RUN.
Stage2 is separately authorized actual source freezing/binding/execution/evidence/UI closure.

## Post-design recheck

No violation or open product choice. Existing unsupported assistant tasks and batch routes are
explicit binding gates, not hidden skips. No research agent was necessary: no new technology or
unresolved stage1 dependency; source research uses inspected repository code.
Optional commit hooks are skipped; mandatory before_specify hook successfully reused the user
branch with GIT_BRANCH_NAME and AllowExistingBranch. setup-plan JSON BRANCH reflects its feature
context identifier; actual git branch remains fixes-and-remaining-work.
