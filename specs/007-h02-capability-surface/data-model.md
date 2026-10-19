# H-02 preparation data

Current stage2 is Complete in the documented local scope; this section is preserved stage1 data/history. See actual-closure.md and contracts/execution.md for actual records and final review.

- SourceFile: repository-relative Python path, SHA256; entire allowed tree forms source_tree_digest.
- SourceRef: path, positive line/end line and matching source SHA256.
- Surface: stable id, kind, name, target symbol, optional queue, refs, direct syntactic calls.
  review_status is always UNREVIEWED. No verdict/effect auto-classification in stage1.
- Issue: stable code and source reference when available, no exception body or file contents.
- Inventory: schema, scenario H-02, stage1, NOT_RUN, source HEAD/branch/dirty, complete sorted source
  manifest, tree digest, surfaces, issues and import-closure paths. preparation_status is
  READY_FOR_REVIEW or BLOCKED; it is not Run readiness READY or product PASS.
- Planned effects for stage2: READ_ONLY, AUXILIARY_WRITE, HIRING_DECISION_WRITE, UNKNOWN. Review
  must bind inventory digest and per-entry downstream refs/reasons; full coverage and actual
  composition evidence are prerequisites for PASS. Forbidden exposure may FAIL despite denial.

No applicant/model-response/private source text, token, environment values or absolute paths in
inventory. CLI target path is local input, not published evidence. Raw preparation stays ignored.
