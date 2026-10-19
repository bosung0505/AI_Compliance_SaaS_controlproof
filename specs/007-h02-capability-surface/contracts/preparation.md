# Preparation contract

`python -m scripts.h02_prepare --whyyou-repo <path> [--output <outside-target.json>]`

Source-only; never imports target modules, creates a runtime or loads .env. Optional JSON is not a
Run/bundle. stdout includes stage1/NOT_RUN/product_verdict:null and source/review inventory.
Exit0 = READY_FOR_REVIEW; exit2 = BLOCKED/incomplete preparation, not target FAIL. Error payloads
contain stable codes, not source text/exception messages. Output must not be inside target repo.

Required anchors: assistant router, search/answer services, prompt builder/answer schema; production
API composition, production worker constructor/routing/create_worker_runtime; model adapter generate,
MessageConsumer dispatch and actual worker entry. Constructors resolve via static import/local aliases.
Additional literal registrations are captured. Dict expansion, computed registration or unresolved
target never disappears; issue blocks readiness. A routing-only event is inventory information,
not proof that a handler runs or that an ignored event is safe. Runtime reconciliation is stage2.

Source references include file hash and line range. Whole-tree digest uses sorted relative paths
and byte hashes. Rehash after collection; reject path escapes and changing tree. Local import
closure is dependency review context, not a complete call graph. All surface items UNREVIEWED.

Stage2 will separately define official profile/Run, immutable bundles, semantic recomputation,
actual binding, per-surface classification, human functional control and shared UI. No such contract
is satisfied by successful stage1 collection alone.
