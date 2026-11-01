# 소개 홈페이지 개편 — 2026-11-01

## Specify / Clarify

연우가 팀에서 받은 단독 HTML `ControlProof_홈페이지.html`(1,034,422 bytes, CSS·JS·로고 내장, 결과·보고서 링크는
로컬 8767 서버)을 기준으로 `/product` 소개 화면과 공용 헤더·푸터를 갱신하도록 요청했다.

- 반영 범위: `/product` 본문(기능 미리보기 탭 3개, 실제 검증 사례 3개, 네 보호조치, 검증 방식, 보고서, 안내·FAQ, 마무리)과
  공용 `public_base.html`의 헤더(로고 이미지·5개 펼침 메뉴)·푸터(로고·대표자 표기). `/guide`는 같은 공용 틀을 쓰므로
  헤더·푸터만 바뀌고 본문은 그대로다.
- 내장 자원은 원래 파일로 분리했다. `theme.css`(`.cp-logo` 블록 추가), `explore.css`·`explore.js`·`navigation.js`(신규).
  내장된 `platform.css`·`platform.js`는 저장소 파일과 바이트가 같아 바꾸지 않았다. 로고 PNG(2172×724 RGBA,
  sha256 `546482e47812089def9c5e6798d83ee856774af18e2a075b2546948bb40dcaf4`)는 바이트 그대로 `controlproof-logo.png`로 둔다.
- 링크: `http://127.0.0.1:8767/…`은 같은 서버의 상대 경로로, 페이지 안 앵커(`#product` 등)는 `/product#…`로 바꿨다.
  안내 화면의 헤더에서도 같은 위치로 이동한다.
- 내보내기 파일 끝의 브라우저 확장 주석 요소(`codex-browser-sidebar-comments-root`, inline style)는 화면 내용이 아니라서 제외했다.
- 수치: 전체 12/9/3과 보호조치별 라벨(예: `3개 실행 · N-03 일부 범위`)은 카탈로그에서 계산한다. NOT_RUN은 0이면 표시하지 않고,
  생기면 범위 문구·보고서 요약·보호조치 라벨에 나타난다. 나머지 설명 문구(N-03 일부, A-01~A-03 대상 없음, 사례 카드, N-02 대표 Run 링크)는
  내보내기 그대로 두고, 그 사실이 카탈로그에서 바뀌면 실패하는 검사로 묶었다.
- 바꾸지 않은 것: 워크스페이스(`/`·결과·상세·증빙·비교·보고서·준비) 화면, API v1, 판정·원본 28/652, 카탈로그·시나리오, WhyYou.

## Plan / Tasks

- T038: 정적 자원 분리, 로고 정적 응답(`.png` → `image/png`), `public_base.html`·`product.html`, `public_view`의 보호조치별 집계.
- T039: 기존 검사 갱신(소개 수치·미리보기 탭), 신규 계약·브라우저 검사, 이전 기본 보존·새 공유본 전환, 문서 수렴.

## Analyze — 구현 전

- CSP `default-src 'self'; script-src 'self'; style-src 'self'`는 그대로다. 내장 `<style>`·`<script>`·data: 로고는 CSP에 막히므로
  `/static/` 파일로만 제공한다(FR-014). 인라인 style·이벤트 속성은 없다.
- 정적 경로는 이름 규칙 `[a-z0-9_-]+\.(css|js|png)`에 맞는 `engine/web/static/` 파일만 응답한다. 이 폴더의 PNG는 로고 하나이고
  봉인 증적 PNG는 기존 strict content 경로만 쓴다. 로고는 표시 pin 대상(`*.py`·`*.html`·`*.css`·`*.js`)이 아니다.
- `platform.js`의 `[data-step]` 탭 처리와 `explore.js`의 미리보기 탭은 대상이 겹치지 않는다(새 탭에는 `data-step`이 없다).
  모바일 메뉴 열기·닫기는 계속 `platform.js`, 펼침 패널은 `navigation.js`가 맡는다.
- 표시 코드가 바뀌어 기존 기본 공유본은 시작을 거부한다. 기존 JSON을 보존하고 같은 28개 기록으로 새 ID 공유본을 만든다(재봉인 없음).

## 검증

- 화면 일치: 내보내기 HTML과 새 `/product`를 Chromium 153(Playwright 1.63)에서 1920·1440·1280·1024·760·390·360px 전체 페이지로 캡처해
  비교했다. 7개 너비 모두 크기 동일·픽셀 차이 0, 가로 넘침 0, 콘솔 오류 0. 메뉴 hover/Escape, ↓키 열기,
  미리보기 탭 클릭·→키, 390px 모바일 메뉴 펼침의 상태값과 캡처도 내보내기와 같았다.
- 검사: 신규 `tests/contract/test_platform_homepage.py` 7개(로고 바이트·정적 허용 경계, 두 공용 화면의 펼침 메뉴/잔여물 없음,
  모든 링크 상대 경로·GET 응답, 카탈로그 수치·라벨, 정적 문구와 카탈로그 사실 대응, 미리보기 탭 초기 상태),
  신규 `tests/web/test_homepage_screen.py` 6개(CSP 아래 로고 로드·메뉴 열고 닫기·키보드, 탭, 390px 메뉴·넘침, 1280/1024px).
  기존 `test_platform_public_pages`(소개 수치: NOT_RUN 0은 숨김, N-01을 NOT_RUN으로 바꾸면 8/1과 N 라벨 변경)와
  `test_platform_integration`(미리보기 탭)을 새 화면에 맞췄다.
- 관련 묶음(신규 2파일·소개/통합·공유본 일치·`specs/010…/checks`) 47 passed / 1 skipped(기존 PDF 확인 skip).
  변경·신규 Python Ruff 통과, 전역 Ruff 22건은 main과 같은 기존 진단. `git diff --check` 통과.
- 전체 `tests`(Linux 샌드박스, Python 3.13·Chromium 153): 이 브랜치 1853 passed / 32 failed, 같은 환경의 main `f631af4`는
  1839 passed / 33 failed. 브랜치의 실패 32개는 모두 main에서도 실패하는 `tests/web`의 기존 선택자·문구 기대
  (예: `a.detail-link` 대기 시간 초과, 이전 워크벤치 문구)이며 이번 변경으로 새로 실패한 검사는 없다.
  main에서만 실패한 1개(`test_report_scenario_link_opens_detail[1024px]`)는 브랜치에서 통과했다. 전체 suite 통과로 표현하지 않는다.
- 공유본: 새 기본 `shared-ui-homepage-20261101-r1`, digest `ea95f9dee8215281a995787a5b29d1f08156e771904775748e09a2cbd94802a8`,
  JSON SHA `1606a2c925a209beea131d5c2bbb2f96c9701404092967a1aef7863545fa1710`. 표시 pin 변경은 이번에 바꾼 8개 파일뿐이다.
  이전 기본은 `review-data/snapshot.shared-ui-n02-capture-20261023-r3.json`(SHA `c608290e3b5d0a82053d11fe223f8a30a7be21d053d887051d9dce1361e222aa`)에
  그대로 보존했다. records/target/missing 선언 동일, 28개 실행/652파일·INVALID 1건·미확보 1건·판정/계보 불변.

## 한계

- 내보내기 동작 그대로 두었다: 메뉴 버튼에서 ↓키로 열면 패널이 표시 전환 중이라 첫 링크로 초점이 바로 옮겨지지 않는다.
  다음 Tab으로 패널 첫 링크에 들어간다.
- 안내 화면 푸터 로고에는 소개 화면 전용 크기 규칙(`:has(.cp-explore)`)이 적용되지 않아 기본 크기(230px)로 보인다.
- 워크스페이스 화면의 브랜드 표기(✓ 마크)는 이번 범위에 넣지 않았다.
- 검증은 Linux 샌드박스 Chromium 기준이다. Windows Edge/Chrome 실제 확인과 비작성자 사용성 시험은 하지 않았다.
  새 WhyYou 실제 Run·모델·AWS 실행은 없다.
