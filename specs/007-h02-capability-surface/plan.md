# Plan — H-02 stage1

Current: **Complete — H-02 stage2 LOCAL_EMULATED actual PASS, VERIFIED19, restore SUCCEEDED, independent44-table residue0, shared browser QA complete (2026-10-19).** See [actual closure](actual-closure.md) and [validation](validation.md). Earlier stage1 scope/status below is historical, preserved as evidence of sequence.

Design before implementation, 2026-10-19. Python3.12 stdlib AST/hashlib/pathlib + existing Pydantic,
PyYAML/pytest/Ruff. No migrations/dependencies/WhyYou behavior changes. Continuing user branch retained.

## Architecture

- `engine/h02.py`: strict immutable preparation data, source references, issues and deterministic digest;
  no product verdict or new Run model/profile. Validate links and unknown/coverage semantics.
- `engine/adapters/whyyou/h02_source.py`: bounded source-only adapter. Hash/parse full allowed Python
  tree, inventory explicit composition anchors, resolve local constructor symbols/imports, attach
  direct call names and local import closure. Rehash before return to detect changing inputs.
- `scripts/h02_prepare.py`: explicit target path, optional output outside target. Git read-only identity;
  no target imports, subprocess of product code, HTTP/DB/Docker or inherited .env loading. Codes only
  on failure. Default stdout, no official engine CLI registration.
- `scenarios/_H-02-preparation.yaml`: explicit stage1 identity, roots, planned assertions and effects.
- Unit/contract tests use miniature source repositories containing hostile changes; real workspace
  collection is a preparation check, never actual H-02 acceptance.

## Sequence

T001 discovery → T002 specify/clarify/plan/contracts/tasks/analyze → T003 expected RED → T004 models
→ T005 collector → T006 CLI → T007 regression/source preparation → T008 documentation convergence.
Stage2 tasks remain unchecked. New official execution uses a future canonical profile only after
runtime binding, semantic verification and sealed result design, not by reusing preparation output.

## Constitution check

I: no name-only PASS; II: preparation NOT_RUN; III: hiring writes separated from allowed persistence,
human independent score selection retained; IV: adapter separate from data; V: read-only source,
synthetic later controls, no credentials; VI: existing runs untouched; VII: FR/SC/tasks/evidence mapped.
All seven satisfied by staged plan. Missing runtime proof is a stage2 gate, not a hidden pass/skip.

## Main design decisions

Inspect existing literal registrations and emit blocking issues for unsupported/dynamic forms.
New literal routes/events are included rather than compared against a fixed name allowlist.
Do not call a source-only inventory a runtime attestation. Hash all local imports and store direct
calls for review, but leave every item UNREVIEWED. Even a fully parsed tree must await source and
actual composition review in stage2; static reconstruction cannot establish every dynamic binding.
Capture API runtime helpers separately: they are not identical to queue subscriptions.

Stage2 must follow model output and worker dependencies including broad concrete company/hiring
objects. Contract presence, reachability and real hiring persistence are different facts. A shared
DB connection or a report save is not by itself a hiring-write exposure. Source proof of a forbidden
exposed tool may be enough for FAIL; no destructive invocation is needed merely to show presence.
