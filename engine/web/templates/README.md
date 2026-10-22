# Web templates

Server-rendered templates for the four approved screens (Spec 005 US1~US5).
Spec010 adds `public_base.html`, `product.html` and `guide.html`; existing pages retain their result content inside the new common frame.
Stage3 uses `overview.html` for `/` and `results.html` for the criterion-grouped results; the previous `workbench.html` is retained but no longer routed.
Subsequent stage4/5 entries below describe the current routed detail, compare and report bodies.
Stage4 now routes scenarios to `scenario_service.html` and upgrades `run.html`/`evidence.html` with service components.
Current/sealed definitions, actual Run selection, condition cards, provenance and reviewed PNG stay separate.
The old `scenario.html` and `_review.html` are retained but are no longer the active scenario/condition route.
Stage5 migrates compare.html/report.html and adds prepare.html. Comparison keeps actual child lineage/provenance and both sealed definitions. The report retains all22 content items, original version/evidence/history links, current partial scope and print disclosures. Preparation GET reads only current definitions and stored readiness; shared/DEMO have no POST forms. Run memos remain a separate local store, with the editor behind a disclosure.

Stage6 uses real page links with aria-current in workspace navigation; product workflow tabs retain their real tab semantics. Error HTML keeps the selected read mode/prefix, with unchanged JSON errors. Report print is validated on actual Edge A4 output; commit values are formatted without changing the API or sealed records.

2026-10-22: base.html의 기본 닫힌 verification-info가 공유 원천/환경/판정 안내를 통합한다.
overview 본문 중복 주석은 이동했으며 N03 일부·DEMO/공유 구분·결과 오류/보고서 내용은 보존한다.
