# Web static files

The existing workbench CSS/JS preserves filters, evidence disclosure and commands (no verdict logic).
Spec010 adds shared theme tokens, a workspace shell, and the supplied public-site design.
`platform.js` controls menus, workflow tabs, browser-local checklist TXT download and GET filter navigation; it makes no server writes.
Stage3 adds `overview.css` and canonical GET results-form navigation in `platform.js`; no browser verdict or count calculation.
Stage4 adds `service.css`, actual Run-ID selection and hash-target disclosure. The existing proof-panel logic is retained.
PNG bytes come only from the strict content endpoint, not static mounting or client-side file access.

Stage5 adds delivery.css for comparison/report/preparation, responsive layouts and report print. platform.js expands report details before print and restores their prior state afterwards; it performs no judgement or server action. workbench.js filters only catalog group rows carrying data-group, preserving report group headings.

Stage6 shell.css selects page links by aria-current. delivery.css print uses A4 margins, page counters/footer, readable technical type and section/page rules; it hides the screen skip link. Product workflow tabs keep their existing styles and keyboard handlers.

2026-10-22: shell.css의 verification-info/panel은 native details의 버튼/포커스와2열→모바일1열을 정의한다.
추가 JavaScript 없이 접근하며 기존 workspace-target 인쇄 숨김이 적용된다.
