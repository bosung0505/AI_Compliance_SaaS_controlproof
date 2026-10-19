# Tasks: H-01 human decision

## Stage1 — preparation authorized

- [X] T001 Source discovery and scope clarification in `spec.md`, `research.md`, `docs/research/Spec006_H01_WhyYou_Source_Baseline.md` [FR-001~014].
- [X] T002 Plan/contracts/data model/checklist and preimplementation analyze in `plan.md`, `contracts/preparation.md`, `data-model.md`, `checklists/requirements.md`, `analysis.md` [FR-001~014, SC-001~006].
- [X] T003 [US1] Write expected-RED cases in `tests/unit/test_h01_preparation.py` for missing proof, partial writes and normal control [FR-001~010, SC-001~003/005].
- [X] T004 [US1] Implement `engine/h01.py` and `scenarios/_H-01-preparation.yaml` contracts, ownership and strict assessment [FR-001~010].
- [X] T005 [US1] Write transport isolation/state-query tests in `tests/contract/test_h01_adapter.py`, implement `engine/adapters/whyyou/h01.py` [FR-002~005/008~010, SC-003].
- [X] T006 [US2] Write guard/transaction/product-service tests in `../gbsa_aws/backend/tests/unit/runtime/test_controlproof_h01.py`, implement `../gbsa_aws/backend/src/interview_evidence/runtime/controlproof_h01.py` [FR-006/007/012/014, SC-001/002].
- [X] T007 [US3] Write lifecycle failure/cleanup tests in `tests/integration/test_h01_preparation_driver.py`, implement `engine/executors/h01_preparation.py` [FR-002/008~011, SC-004/005].
- [X] T008 Add `scripts/h01_prepare.py` and preparation-only CLI tests to `tests/unit/test_h01_preparation.py` [FR-013/014, SC-006].
- [X] T009 Scoped regression, Ruff and diff checks; restore stale `../gbsa_aws/backend/tests/integration/reporting/test_human_only_decision.py` SQL test and record commands/RED/GREEN and truthful actual status in `validation.md` [SC-001~006].
- [X] T010 Synchronize `traceability.md`, README, handoff, coverage, Product Brief/Decision Log and WhyYou doc [FR-013/014, SC-006].

Dependencies: T001→T002→T003→T004; T005/T006 depend on contract; T007 depends on strict assessment;
T008→T009→T010. No implementation before analysis. Tests precede code. No delegation required.
US1 independently tests transport/assessment; US2 independently tests SYSTEM boundary; US3 independently tests cleanup.

## Stage2 — user authorized 2026-10-18; Complete — actual, independent audit, web QA and convergence closed 2026-10-19

- [X] T011 Bind existing real report-producing fixture lifecycle, valid principals and owned cleanup; register official H-01 profile/CLI/evidence contracts.
- [X] T012 Bind/observe actual AI assistant operation without inventing identity; prove request/denial records and resolve batch route coverage.
- [X] T013 Freeze clean source, isolated setup, actual preflight/Run; preserve any first FAIL and verify remedy with child only.
- [X] T014 Independent evidence/restore/cleanup validation, shared result UI and official/document convergence.

Stage1 was preparation only. Stage2 is now complete in the documented LOCAL_EMULATED scope; actual results and limits are in validation.md and actual-closure.md.
