# HTTP·탐색 계약

2026-10-21 · 0·1단계 계약 확정 후 2·3단계 구현. **`/product`, `/guide`, `/results`, `/demo/results` 구현 완료**.
4단계에서 PNG content와 DEMO 대응,5단계에서 `/prepare`·`/demo/prepare`를 구현했다.
아래의 ‘1단계 미구현’ 설명은 계약 당시 이력이며 현재 검증은 [6단계 기록](../stage6-validation.md)을 따른다.
기준 `fb219d0`, 기존 계약은 [Spec005 HTTP](../../005-web-workbench-report/contracts/web-http.md)와
[read model](../../005-web-workbench-report/contracts/web-read-model.md), 공유 경계는 Spec008을 따른다.
검사할 사례는 [http-cases.json](http-cases.json)에 있으며 작성만으로 HTTP 시험 통과를 뜻하지 않는다.

## 1. 기존 주소 보존과 추가 주소

| 종류 | GET 주소 | 계약 |
| --- | --- | --- |
| 기존 | `/`, `/demo/` | 전체 현황. `/`를 소개 화면으로 바꾸지 않는다. 기존 `/demo` → `/demo/` 301 유지 |
| 기존 | `/scenarios/{scenario_id}`, `/demo/scenarios/{scenario_id}` | 실제 정의·프로필·실행 이력. 없는 ID는 404, 임의 사례로 대체하지 않음 |
| 기존 | `/runs/{run_id}`, `/demo/runs/{run_id}` | 고유 실행. INVALID도 200 화면에서 차단 상태를 표시하며 정상 판정/관찰은 숨김. 봉인 원본은 보존 |
| 기존 | `/runs/{run_id}/evidence?ref=…&condition=…`, `/demo/runs/{run_id}/evidence?ref=…&condition=…` | 텍스트 원문·조건 문맥 계약 유지. PNG를 억지로 텍스트로 표시하지 않음 |
| 기존 | `/compare/{child_run_id}`, `/demo/compare/{child_run_id}` | 요청한 child의 실제 계보. 없는 부모·불완전 비교도 사실대로 표시 |
| 기존 | `/report`, `/demo/report` | 해당 읽기 모드의 보고서 |
| 신규 | `/product` | 팀원 `index.html`의 서비스 소개. 실제 결과 `/`와 DEMO `/demo/` 진입을 별도 표시 |
| 신규 | `/guide` | 팀원 `guide.html`의 안내. 체크와 TXT 다운로드는 브라우저 내부 동작이며 실행 승인 아님 |
| 신규 | `/results`, `/demo/results` | 12개 시나리오를 N/H/A/E 기준과 숫자순으로 묶은 목록. §2 필터 적용 |
| 신규 | `/prepare`, `/demo/prepare` | GET은 안내·기존 준비 정보 열람만. 공유에서는 읽기 전용, DEMO는 합성 정보만 |
| 신규 | `/runs/{run_id}/evidence/content?ref=…`, `/demo/runs/{run_id}/evidence/content?ref=…` | [PNG 전용 계약](png-evidence.md). 폴더 전체 공개 경로 아님 |

`/product`, `/guide`는 기록을 담지 않는 공통 안내이므로 `/demo/product`, `/demo/guide` 별칭을 추가하지 않는다.
소개에서 실제/DEMO를 선택하고 업무 화면부터 모드를 유지한다. `/results/`, `/prepare/` 등 신규 trailing-slash 별칭은
추가하지 않으며 일치하지 않는 경로는 기존 정책대로 404다. 이 문서는 기존 경로의 임의 정규화를 요구하지 않는다.

실행·비교·자료 URL에 시나리오 ID나 최근/이전 boolean을 Run ID 대신 사용하지 않는다. 기존 `ref`는 불투명한
증빙 식별값이고 기존 `condition`은 연결된 조건 문맥이다. 클라이언트는 `URLSearchParams` 등으로 인코딩한다.
각 화면은 새로고침·직접 주소·뒤로 가기에서 같은 항목을 열며 선택 Run을 다른 Run으로 묵시 대체하지 않는다.

## 2. 신규 목록 query

| 키 | 값 | 기본값·의미 |
| --- | --- | --- |
| `q` | UTF-8 문자열, trim 뒤 최대 200 Unicode code point | 빈 문자열. ID·제목·질문·쉬운 설명에서 casefold 부분 문자열 검색 |
| `control` | `N`, `H`, `A`, `E` | 생략/빈값이면 네 기준 전체. `ALL` 값은 사용하지 않음 |
| `status` | `ALL`, `PASS`, `FAIL`, `INCONCLUSIVE`, `NOT_RUN` | `ALL`. 카탈로그 공식 `official.result` 필터 |
| `treatment` | `ALL`, `EXECUTED`, `NOT_RUN`, `NO_TEST_TARGET` | `ALL`. 카탈로그 `mvp_treatment` 필터 |

네 조건은 AND로 적용한다. status와 treatment는 서로 다른 축이다. 예를 들어 대상 없는 A의 원래 공식 결과는
`INCONCLUSIVE`/`NO_TEST_TARGET`이며 `status=NO_TEST_TARGET`라는 새 판정을 만들지 않는다.
INVALID는 Run 무결성 상태이므로 status 필터 값으로 추가하지 않는다. `EXECUTED`는 PASS 개수가 아니다.
`control=A&status=PASS`처럼 문법상 유효하지만 일치하지 않는 조합은 200 빈 결과다.
그룹 안의 일치 항목이 없으면 그룹의 결과 수 0을 표시하고 가짜 시나리오를 만들지 않는다.

디코딩은 percent-encoding 1회와 UTF-8 strict로 한다. `+`는 공백이다. 잘못된 percent escape/UTF-8, 알 수 없는 키,
중복 키(같은 값이어도), 소문자 등 열거값 불일치, trim 후 200자 초과, 제어 문자 U+0000~U+001F/U+007F는
**400 `USAGE` / `RESULT_FILTER_INVALID`**로 안내한다. q의 앞뒤 공백만 제거하며 HTML은 반드시 escape한다.
빈 값은 기본값으로 해석하고 정상 GET을 강제 redirect하지 않는다. 화면이 만드는 링크는 기본값을 생략하고
`q`, `control`, `status`, `treatment` 순서로 출력한다. 이 정규 링크 규칙은 API v1이나 기존 자료 query의 계약을 바꾸지 않는다.

### 탐색에서 필터를 지우는 규칙

- 전체 현황의 **전체 시나리오**, **결과 검토하기**, 전체 결과 메뉴는 언제나 `/results`다.
  이전 검색·기준·상태·treatment를 query나 localStorage에서 재사용하지 않는다.
- DEMO에서는 같은 동작이 `/demo/results`다. 실제 기록과 DEMO 사이 필터·선택 Run을 공유하지 않는다.
- 기준 카드의 **결과 보기**는 `/results?control=N`과 같이 해당 기준만 넘긴다. 지난 q/status/treatment는 지운다.
- 검색/필터 적용은 GET form 또는 동등한 URL 갱신이며 브라우저 history와 일치한다.
- 결과 목록의 **초기화**는 현재 모드의 query 없는 목록 주소다. 소개의 대표 사례 링크는 ‘대표 사례’로 표시한다.

## 3. API·모드·실행 경계

`/api/workbench`, `/api/scenarios/{id}`, `/api/runs/{id}`, `/api/compare/{id}`, `/api/report` 및
기존 `/demo/api/…`는 **`controlproof.web.v1`의 필드·의미·오류 계약을 유지**한다. 신규 JSON 목록 API를 만들지 않는다.
기존 JSON에 HTML 필터 처리를 몰래 적용하거나 필수 키를 제거하지 않는다. UI용 투영이 필요하면 동일 읽기 모델을
서버 표시 계층에서 가공하며 불가피한 additive 필드 변경은 명세·회귀 시험에 먼저 연결한다.

ACTUAL의 SHARED/LOCAL 구분은 서버가 선택한 실제 읽기 모드로 정한다. `mode`, `run_root`, `snapshot`, `path` 등의
query로 root를 바꾸지 않는다. 공유 화면은 snapshot ID·검토 시각(KST)·읽기 전용을 표시하고 PC READY/메모를 읽지 않는다.
LOCAL의 준비 상태는 실제 확인 시각과 프로필을 보이며 GET 진입으로 preflight를 실행하지 않는다.
DEMO는 `/demo/` 읽기 모델만 사용하고 모든 업무 화면에 합성 자료 표시를 유지한다.

기존 상태 변경 주소는 LOCAL의 `POST /preflight`, `POST /runs/{run_id}/memos`뿐이다. 유효한 CSRF가 필요하다.
공유 서버는 route 존재나 CSRF에 앞서 모든 POST를 403 `CONTRACT/SHARED_READ_ONLY`로 거부한다.
DEMO를 이유로 실제 POST나 preflight에 연결하지 않는다. `/demo/preflight`와 `/demo/runs/{id}/memos`는 추가하지 않는다.
기존 `/preflight`의 `return_to` 허용식은 현재 `/` 또는 시나리오 상세뿐이며, 1단계에서 `/prepare` 허용으로 확장하지 않는다.
실제 준비 form을 새 화면에 붙일 때 이 귀환 주소 확장은 별도 구현·보안 시험 작업이다.
Run·재테스트·복구·cleanup·서버 재시작을 실행하는 웹 endpoint는 추가하지 않는다.

## 4. 보안·오류와 기존 동작

- 바인딩 `127.0.0.1`과 허용 Host `127.0.0.1:<port>`/`localhost:<port>` 유지. 불일치는 **421**이다.
- CSP `default-src 'self'; script-src 'self'; style-src 'self'`, `nosniff`, `no-store`, `Referrer-Policy: no-referrer` 유지.
- Jinja autoescape, 출력 redaction·경로 마스킹을 유지한다. redaction을 HTML escape 대신 사용하지 않는다.
- 기존 400/403/404/409/421/422/500 분류와 오류 payload 키를 유지한다. 새 query 오류 코드는 기존 USAGE 분류를 쓴다.
  HTML 주소 오류는 오류 HTML, API/POST 오류는 JSON이라는 현재 동작을 보존한다.
  Host 421도 모든 주소에서 무조건 JSON이라고 가정하지 않는다(현재 `_wants_json`의 경로·메서드에 따름).
- 없는 시나리오/Run/증빙은 404, 잘못된 Run 무결성의 원문은 422다. 원본 미확보와 미실행을 섞지 않는다.
  PNG는 일반 텍스트 원문보다 엄격한 [별도 기본거부 경계](png-evidence.md)를 적용한다.
- 정적 배포 파일은 현재 CSS/JS 허용 경로를 사용한다. snapshot/bundle 디렉터리를 static mount하지 않는다.

## 5. 1단계 완료와 후속 구현

이 문서는 신규 라우트·query·모드의 선택을 고정한다. 제품 `server.py`, 템플릿, API, snapshot은 이 단계에서 수정하지 않는다.
사례 JSON의 기존 회귀/미래 계약 구분을 유지하고 후속 구현 때 서버 harness에 연결한다. 링크·조회 상태·400/빈 결과와
PNG 차단을 실제 검증하기 전까지 신규 화면이 동작하거나 보안 검수가 통과했다고 보고하지 않는다.

## 5단계 준비 귀환의 구현 보충

GET `/prepare`·`/demo/prepare`는 현재 정의/저장 준비만 읽으며 과거 Run을 스캔하지 않는다.
LOCAL만 기존 `/preflight` form을 제공한다. 귀환 입력은 기존 허용 주소와 정확한 `/prepare`만 허용한다.
`/prepare` 성공 귀환에는 서버가 검증한 scenario_id로 `#prepare-{id}`를 붙이며 해당 details가 열린다.
외부 URL·이중 slash·query·trailing slash·`/demo/prepare`를 귀환 입력으로 허용하지 않는다.
SHARED의 모든 POST403과 Host 우선 검사는 그대로이며 DEMO 준비/메모 POST는 추가하지 않는다.

## 6단계 탐색·오류 검수 보충

업무 페이지 이동은 표준 nav/a와 aria-current=page이며 tablist/방향키 탭으로 선언하지 않는다.
소개의 실제 workflow 탭은 기존 data-step/패널/키보드를 유지한다. DEMO HTML 오류도 DEMO header/배너와
`/demo/` 복귀·탐색을 유지한다. HTTP 상태/오류 코드·API/POST JSON 키·Host 우선·공유 POST 거부는 불변이다.
