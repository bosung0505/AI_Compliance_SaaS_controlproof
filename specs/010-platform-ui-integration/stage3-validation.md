# Spec010 3단계 — 현황과 테스트 결과

2026-10-21 · `010-platform-ui-integration` · T011/T012 완료. 업무 화면은 단계마다 바뀌며 전체 전환 완료는 아니다.

## 반영

- `/`: VERIFICATION OVERVIEW, 같은 서버 집계의 도넛/범례/접근성 설명(9 실행/0 미실행/3 대상 없음), N03 일부 범위 별도 안내.
- 네 기준의 목적·세 시나리오를 N/H/A/E 순서로 표시. A는 대상 기능 부재를 설명하고 실행 진행률을 만들지 않는다.
- Change review/Latest update를 별도 섹션으로 구분. 최초 실패→실제 child 비교 경로와 기존 보고서를 유지한다.
- `/results`, `/demo/results`: 기준별 결과·설명과 GET 검색/기준/공식 상태/처리 범위 필터.
  URL이 상태의 원천이다. 기준 카드에는 control만, 전체 진입에는 query가 없다. JS가 없으면 일반 GET form으로 작동한다.
  엄격한 1회 percent/UTF-8 decode, 중복/미등록 키·enum·제어문자·200 code point 초과는 400.
- 상세 경로/프로필·전체 이력/로컬 준비 form·확인 시각/무결성·불일치·부재 설명을 보존했다.
  주의가 필요한 원본 부재/무결성 경고는 행의 접힌 영역 밖에 표시한다. 세부 공식 상태/자료 링크는 펼쳐 읽는다.
- API v1의 기존 필드/배열 순서는 보존한다. `ui.coverage`, `ui.groups` 및 행 `ui.current_scope`만 추가한다.
  `ui.groups`는 N/H/A/E 표시 순서이며 원래 `groups`의 순서를 바꾸지 않는다. API query로 HTML 필터를 적용하지 않는다.
  N03 current scope는 현재 YAML의 A1~A3/U1~U3/L1/후속 조건에서 읽으며 과거 Run 정의로 주장하지 않는다.
- 공통 공유본 정보는 접어서 표시한다. snapshot ID·SHA·시각(KST)·누락 기록은 펼쳐 확인할 수 있다.
  소개/안내의 전체 시나리오 링크도 새 결과 목록으로 연결한다.

## 자동 검증

실패 단계: `test_platform_overview.py`가 새 표시 모듈 부재로 수집 실패한 것을 확인한 뒤 구현했다.
새 모듈 연결 뒤 fixture 준비 오류(readiness/check 호출명)를 바로잡았다. 실제 브라우저에서 기준 제목에 기존 개인정보
마스킹이 적용되는 문제를 발견해 `name` 대신 의미가 맞는 `title` 표시 필드를 사용했다. 마스킹 경계는 완화하지 않았다.

```powershell
$env:CONTROLPROOF_UI_TEST_SNAPSHOT='.controlproof/ui-integration-20261021/stage3-shared-r2/snapshot.json'
& .\.venv\Scripts\python.exe -m pytest tests/contract/test_platform_overview.py tests/contract/test_platform_public_pages.py specs/010-platform-ui-integration/checks/test_contract_baseline.py tests/unit/test_catalog_matrix_parity.py -q -p no:cacheprovider --basetemp .controlproof/ui-integration-20261021/pytest-stage3-final-02 --tb=short
& .\.venv\Scripts\python.exe -m pytest tests/contract/test_web_http.py tests/contract/test_web_http_us2.py tests/contract/test_shared_web.py -q -p no:cacheprovider --basetemp .controlproof/ui-integration-20261021/pytest-stage3-http-01 --tb=short
& .\.venv\Scripts\python.exe -m pytest tests/unit/test_web_readmodel_workbench.py -q -p no:cacheprovider --basetemp .controlproof/ui-integration-20261021/pytest-stage3-readmodel-01 --tb=short
node --check engine/web/static/platform.js
git diff --check
```

새 표시 시험29개: COV01~09 집계 fixture, 처리 범위와 판정 분리, 빈 항목/0개, 모순 입력 거부, N03 구조,
A 진행률 없음, strict query·AND 검색·빈 결과·HTML escape·초기화·DEMO·GET 무실행·API 호환을 검사한다.
합성 계약 fixture와 화면 경계 시험이며 실제 WhyYou 실행이 아니다.
기존 소개/공통9개, 기준 handler8개(`/results` 미구현 확인은 제거), 카탈로그8개를 합쳐 **54개**다.
기존 HTTP/공유/무결성 회귀 **30개**, 기존 workbench 읽기 모델 **11개 통과**. 총 **95개 통과**.
실제 loopback 전송 시험은 환경 권한을 승인받아 실행했다.
전체 엔진 suite는 실행하지 않았다. 기존 default snapshot 코드 일치 시험은 원본 r2와 새 코드가 다른 상태이므로
후속 기본 전환까지 미적용이며, 새 후보의 전체 `load_snapshot` 검증과 원본 불변 시험을 사용한다.
65 HTTP/PNG 계약 사례나 공식 대표/이력 관련 COV 사례 전체가 구현/통과한 것으로 계산하지 않는다.

## 브라우저

실제 앱 브라우저에서 `/`와 `/results`를 1440/1280/1024/900/390px로 확인했다. 가로 넘침 없음.
도넛은 2개 조각(0개 NOT_RUN은 미표시), 범례는 9/0/3 세 항목이다. 제목 4개가 정상 표시된다.
N 카드→결과3개→N03 검색1개, canonical URL, 새로고침 유지, 뒤로 가기 복원,
대시보드 두 전체 진입의 검색 초기화12개, A+PASS의 0개와 초기화, N03 U1~U3/L1 펼침을 확인했다.
모바일 메뉴 이동 후 aria-expanded=false, DEMO 배너/주소와12개 항목, console error0을 확인했다.
새 화면에는 기존 CSP와 자체 CSS/JS를 유지한다. 보고서 PDF·전체 상세 개편·비작성자 사용성은 후속 단계다.
기존 `tests/web/test_workbench_screen.py`의 구형 표/checkbox 전제는 현황→결과 흐름과 GET 필터에 맞게 갱신했다.
이 Playwright 회귀 파일 자체는 이번 실행에 포함하지 않았고 위 실제 앱 브라우저 검수와 구분한다. 구문 검사만 수행했다.

이미지와 기계 판독 기록은 ignored `.controlproof/ui-integration-20261021/` 아래
`stage3-overview-desktop.jpg`, `stage3-overview-mobile.jpg`, `stage3-results-desktop.jpg`, `stage3-results-mobile.jpg`,
`browser-checks-stage3.json`에 있다.

## 후보·실행

현재 후보 `.controlproof/ui-integration-20261021/stage3-shared-r2/snapshot.json`.
ID `shared-ui-stage3-20261021-r2`, digest `ce8f43a2e61049c85b29a20e05ff05c9f0c3a73aebcf5b2d7e027a17b630c655`.
원본28개 records 전체/652개 파일·target·missing records·검토 PNG 해시를 보존했고 전체 load 검증이 성공했다.
27 VERIFIED/원래 INVALID1개, N02 원본 미확보1개를 유지한다. 기본 `review-data/snapshot.json`은 그대로다.
r1은 기준 제목의 표시 필드 수정 전 후보로 보존한다. 현재 코드는 r2와 짝을 이룬다.

```powershell
& .\.venv\Scripts\python.exe -m engine.web --shared-snapshot .controlproof/ui-integration-20261021/stage3-shared-r2/snapshot.json --port 8782
```

현재 미리보기 `http://127.0.0.1:8782/`, 결과 `/results`, 소개 `/product`.
종료 후 다시 볼 때 위 명령으로 같은 코드/후보를 실행한다. 기본 전환/배포/커밋/push/PR/main 병합은 하지 않았다.
WhyYou 변경·실제 Run·Docker/DB/모델 호출은 없다. 4단계 T013 이후는 상세→실행→자료와 PNG 제공 작업이다.
