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

2026-11-01 소개 홈페이지: `ControlProof_홈페이지.html`의 내장 자원을 원래 파일로 분리했다. `explore.css`(소개 본문·공용 펼침 메뉴),
`explore.js`(기능 미리보기 탭, 자동 전환 없음), `navigation.js`(공용 헤더 hover/키보드/모바일 펼침), `theme.css`의 `.cp-logo` 블록,
`controlproof-logo.png`(제공 로고 원본 바이트). 정적 경로는 css/js와 이 폴더의 png만 응답하며 봉인 증적 PNG는 기존 content 경로만 쓴다.
같은 날 후속: `explore-workspace.css`는 워크스페이스에만 실어 공용 헤더·푸터 값을 `.workspace-shell` 아래에 두고(공개 화면의
`platform.css`·`explore.css`는 내보내기 그대로) 본문 글꼴·링크·소제목·카드 모서리·버튼을 맞춘다. `platform.js`는 모든 `.menu-toggle`이
각자의 `aria-controls` 대상을 연다(워크스페이스의 공용 메뉴·화면 메뉴). `theme.css`는 모든 푸터 로고를 184×36으로 맞춘다.
