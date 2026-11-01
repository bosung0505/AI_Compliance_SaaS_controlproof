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
- 바꾸지 않은 것: 워크스페이스(`/`·결과·상세·증빙·비교·보고서·준비) 화면의 본문 내용·배치(틀과 스타일은 아래 후속 T040),
  API v1, 판정·원본 28/652, 카탈로그·시나리오, WhyYou.

## Plan / Tasks

- T038: 정적 자원 분리, 로고 정적 응답(`.png` → `image/png`), `public_base.html`·`product.html`, `public_view`의 보호조치별 집계.
- T039: 기존 검사 갱신(소개 수치·미리보기 탭), 신규 계약·브라우저 검사, 이전 기본 보존·새 공유본 전환, 문서 수렴.
- T040(후속): 모든 화면에 같은 헤더·푸터·로고와 본문 스타일 적용(왼쪽 메뉴 유지), 검사 추가, r1 보존·r2 공유본 전환.

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

- Windows(연우 PC, Claude Code)에서 같은 커밋(tree `b29088702250ca19e5ed1043297c32904e020791`)을 적용해 확인했다:
  공유본 verify 일치, 관련 35 passed, `tests/contract` 681 passed / 1 skipped(Windows 일반 권한 symlink 생성 불가로
  `test_h02_source_inventory`의 링크 거부 시험 skip), `specs/010…/checks` 12 passed / 1 skipped.

## 후속 — 모든 화면에 같은 틀·로고·스타일 (T040)

### Specify / Clarify

팀 확인에서 "로고가 옛날 것"이라는 지적이 나왔다. 소개 화면의 로고는 팀 IR 발표자료(Figma)의 표지·마무리 로고와 같은 디자인이다
(같은 크기로 맞춰 비교, 평균 차이 255 중 2.6). 옛 로고는 워크스페이스 화면(`/`·결과·상세·증빙·비교·보고서·준비·DEMO·오류)
상단의 ✓ 마크였다. 연우가 소개 화면만이 아니라 다른 모든 화면에도 바뀐 레이아웃과 로고를 반영하자고 요청했고, 두 가지를 골랐다.

- 적용 범위: **틀+스타일 통일** — 모든 화면이 소개 화면과 같은 상단(로고·펼침 메뉴·실제 결과 열기)과 하단을 쓰고, 본문은 내용·배치를
  그대로 두되 글꼴·링크 색·소제목·카드 모서리·버튼 모양을 새 디자인에 맞춘다. 본문 재구성은 하지 않는다.
- 왼쪽 메뉴: **유지** — 화면 이동용 왼쪽 메뉴(전체 현황·테스트 결과·개요/실행·보고서·준비)는 그대로 둔다.

### 구현

- 공용 틀: 소개 화면의 헤더·푸터를 `templates/partials/site_header.html`·`site_footer.html`로 분리해 `public_base.html`과
  `base.html`이 같이 쓴다. 워크스페이스에서는 상단 메뉴 id만 `site-navigation`으로 쓰고(왼쪽 메뉴가 `primary-navigation` 유지),
  로고를 화면의 `h1`으로 감싼다(이전 브랜드 h1 구조 유지). 소개 화면 출력은 바뀌지 않았다(7개 너비 픽셀 차이 0).
- 워크스페이스 첫 줄은 얇은 맥락 줄(대상·환경, 공유/DEMO/로컬 표시, 검증 정보, 좁은 화면의 `화면 메뉴 ☰`)로 바꿨다. 상단의
  서비스 소개·도입 안내 링크는 공용 메뉴와 푸터로 옮겨졌다. DEMO 띠는 헤더와 함께 상단에 고정된다.
- `explore-workspace.css`(새 파일, 워크스페이스만 로드): ① 공용 헤더·푸터 규칙을 `.workspace-shell` 아래에 같은 값으로 둔다.
  공개 화면의 `platform.css`·`explore.css`는 내보내기와 같게 두었고, 그 안의 전역 규칙(`body`·`h2` 40px·`a`·`.eyebrow` 등)이
  워크스페이스 본문을 바꾸지 않도록 워크스페이스에는 싣지 않는다. ② 본문 스타일: 글꼴, 본문 링크 보라색(밑줄·hover 배경은
  D-022 클릭 가능 표시로 유지), 왼쪽 메뉴 글자색, 소제목(`section-kicker`) 12px·650·1.1px, 주요 카드 모서리 20px/16px,
  버튼 둥근 알약 모양. 판정·준비 배지의 모양(배지 표의 원/사각/채움)과 강조 테두리 색은 바꾸지 않았다.
- `platform.js`: 메뉴 버튼이 둘인 화면(공용 메뉴·화면 메뉴)을 위해 모든 `.menu-toggle`이 각자의 `aria-controls` 대상을 연다.
  공개 화면의 동작·라벨(`메뉴 열기/닫기`)은 같다. `navigation.js`는 워크스페이스에서도 펼침 메뉴를 맡는다.
- `shell.css`: 맥락 줄 배치와 화면 메뉴 버튼. `theme.css`: 모든 푸터 로고를 소개 화면 푸터와 같은 184×36으로(안내 화면의 230px 해소).
- 인쇄: 보고서 인쇄에서는 로고만 남기고 메뉴·버튼·푸터를 숨긴다. A4 PDF 26쪽(기존 검증과 같은 쪽수).

### 검증

- 공용 틀 일치: `/product`와 워크스페이스 화면의 헤더·푸터 계산 스타일과 위치(헤더·푸터 기준)를 1440·1100·1024·980·760·600·390px,
  닫힘/펼침(넓은 화면 펼침 패널, 좁은 화면 메뉴+아코디언)에서 비교해 차이 0. 같은 비교를 `tests/web/test_workspace_chrome.py`에 넣었다.
- 소개 화면: 내보내기 HTML과 7개 너비 픽셀 차이 0 유지. 안내 화면은 푸터 로고 크기만 바뀌었다.
- 검사: `test_platform_homepage.py`의 워크스페이스 11개 화면(DEMO·오류 포함) 검사 — 헤더 하나, 소개 화면과 같은 헤더(메뉴 id·h1만
  다름)·푸터, DEMO 띠 위치, 왼쪽 메뉴 5개, 자원. `test_workspace_chrome.py` — 계산 스타일 비교 4개 너비, DEMO 띠·헤더 상단 고정,
  390px 두 메뉴 분리, 5개 화면 가로 넘침 없음. 관련 묶음 결과는 아래 전체 실행에 포함된다.
- 전체 `tests`(Linux 샌드박스): 1875 passed / 33 failed. 새로 실패한 1개는 `test_web_report_links`의 허용 링크 목록이었다
  (공용 헤더의 `/product#product`·`#workflow`·`#report` 앵커). 목록에 이 세 앵커만 더한 뒤 해당 파일과 관련 묶음 73 passed / 1 skipped.
  나머지 32개는 같은 환경 main에서도 실패하는 기존 `tests/web` 기대와 같은 목록이다. 홈페이지·워크스페이스 관련 묶음은 58 passed.
  전체 suite 통과로 표현하지 않는다. 변경·신규 Python Ruff 통과, 전역 Ruff 22건은 main과 같다.
- 공유본: 새 기본 `shared-ui-homepage-20261101-r2`, digest `214b365e29fbb7aa5e66e4b33c1a1c6c112dde02989d7cb98233360eb28dc846`,
  JSON SHA `7d1f4dae59f87e6f8a13672690831dd4cf4f366f14d62d945e62e6488381af13`. r1 JSON은
  `review-data/snapshot.shared-ui-homepage-20261101-r1.json`에 바이트 그대로 보존했다. 표시 pin 변경은 `base.html`·`public_base.html`·
  두 partial·`explore-workspace.css`·`platform.js`·`shell.css`·`theme.css`다. records/target/missing 선언과 28개 실행/652파일은 r1과 같다.
- 팀이 더 새로운 로고 파일을 따로 갖고 있다면 `controlproof-logo.png`만 같은 이름으로 바꾸면 모든 화면에 반영된다
  (`LOGO_SHA256` 검사 값도 함께 바꾼다). 이 PNG는 표시 pin 대상이 아니라서 공유본을 다시 만들 필요는 없다.
- 공개 화면의 헤더·푸터 디자인(`platform.css`·`explore.css`)을 바꾸면 `explore-workspace.css` 1번 구역도 같은 값으로 맞춘다.
  맞추지 않으면 `test_workspace_chrome.py`가 실패한다.

## 한계

- 내보내기 동작 그대로 두었다: 메뉴 버튼에서 ↓키로 열면 패널이 표시 전환 중이라 첫 링크로 초점이 바로 옮겨지지 않는다.
  다음 Tab으로 패널 첫 링크에 들어간다.
- 워크스페이스 본문은 배치를 바꾸지 않았다(사용자 선택). 본문까지 소개 화면처럼 재구성하는 일은 별도 작업이다.
- 검증은 Linux 샌드박스 Chromium과 연우 PC의 자동 검사 기준이다. Windows Edge/Chrome 화면 실측과 비작성자 사용성 시험은 하지 않았다.
  새 WhyYou 실제 Run·모델·AWS 실행은 없다.
