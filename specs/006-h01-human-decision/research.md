# H-01 research decisions

- Decision: retain current integration branch and create Spec006 independently of branch name.
  Rationale: explicit user preference. Alternative: automatic new feature branch, rejected.
- Decision: require a valid report/actor/request precondition for every denial assertion.
  Rationale: report absence, expired token or stale pipeline can otherwise produce a false PASS.
- Decision: use a direct HTTP boundary for company/applicant/anonymous and a separately named
  internal transaction boundary for SYSTEM. Rationale: actual architecture has no SYSTEM bearer API.
- Decision: do not invent an AI principal. Require actual assistant observation independently;
  unavailable observation remains INCONCLUSIVE. Full tool inventory stays H-02.
- Decision: build an opt-in preparation manifest and driver outside the official Run registry.
  Rationale: stage1 is preparation only; existing historical schema/load_all/catalog remain stable.
- Decision: read current state with own company/invitation filters, not historical hardcoded actor labels.
- Decision: always run lifecycle cleanup in finally, including partially failed preparation;
  report cleanup uncertainty rather than overwrite the original error.
- Decision: test the WhyYou helper using the existing product decision service and a real local
  transactional SQLite persistence fixture. This proves automatic helper behavior, not live Postgres.

Full inspected paths and source IDs: [source baseline](../../docs/research/Spec006_H01_WhyYou_Source_Baseline.md).
No unresolved design questions within stage1. Stage2 binding/actual evidence remain explicit work.
