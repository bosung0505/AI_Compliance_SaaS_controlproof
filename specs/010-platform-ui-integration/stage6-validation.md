# Spec010 6단계 — 통합·공유본·실제 PDF 검수

2026-10-21 · `010-platform-ui-integration` · **T020/T021 완료, T022(7단계) 대기**.
기준 HEAD는 `fb219d0c6923c6be09691fcae0ead670f9700b39`로 유지했다. 작업은 미커밋 상태이며 WhyYou/실제 Run은 변경하지 않았다.

## 확인한 문제와 수정

1. 공통 페이지 이동 메뉴가 tab/tablist로 선언돼 있었지만 방향키 탭 동작은 없었다. 페이지 링크와
   `aria-current=page`로 바꿨다. 실제 소개 화면의 workflow 탭/ArrowRight/End 동작은 별도로 보존했다.
   본문 건너뛰기/Tab·모바일 Enter/Escape·포커스 복귀를 실제 앱에서 확인했다.
2. 첫 실제 PDF에서 화면용 skip 링크가 매 페이지에 찍혔다. 인쇄에서 숨기고 A4 여백·페이지 번호·보고서 footer,
   흰 배경과 본문/제목 페이지 경계를 보완했다. 마지막 방법·한계 절은 새 페이지에서 읽는다.
3. 출력 버전 정보의 글자가 작고 ControlProof commit의 Python dict가 그대로 보였다. 버전 기술 문자는11px로
   읽게 하고 원래 commit_sha/dirty를 표시한다. 원본 API 값·봉인 파일은 바꾸지 않았다.
4. 원본에 environment snapshot이 없는 legacy2건에도 참조 이름이 있었다. 추가 report.ui source_refs를
   실제 존재하는 원본만 가리키게 고쳤다. 원래 버전 부재/null과 기존 v1 필드 의미는 유지한다.
5. DEMO 404 화면이 ACTUAL로 복귀하던 것을 확인했다. HTML 오류만 선택 모드의 헤더/탐색·복귀를 유지한다.
   API/POST 오류 JSON의 기존5개 키와 코드·HTTP 상태·Host/CSRF/공유 POST 검사는 그대로다.

탐색8개 경로·실제 workflow 탭·보고서 버전 출처·ACTUAL/DEMO 오류 복귀의 실패 시험 뒤 수정했다.
최종 신규 계약은 `tests/contract/test_platform_integration.py`12개다. 수정한 기존 UI suite의 selector는 새 페이지 링크에 맞췄다.

## 자동 회귀 — 최종 후보 코드

**324 passed /0 failed /0 skipped**,371.73초. 실제 loopback HTTP와 Windows junction 검사를 허용한 실행이다.
선정27개 파일: 모든 `tests/unit/test_web*.py`, `tests/contract/test_platform*.py`, `tests/contract/test_web*.py`,
`test_shared_web.py`, `tests/web/test_spec009_display.py`(HTTP), catalog parity, Spec010 baseline 계약.
이는 전체 엔진 suite나 별도 Playwright UI suite 전체 실행을 뜻하지 않는다.

실제 실행 환경: `CONTROLPROOF_UI_TEST_SNAPSHOT=.controlproof/ui-integration-20261021/stage6-shared-r3/snapshot.json`.
범위 목록은 ignored `stage6-test-files.txt`, 결과는 `stage6-full-tests.xml`, basetemp `pytest-stage6-full-01`에 보존한다.
재실행은 같은 파일27개와 새 basetemp를 선택한다.

```powershell
$env:CONTROLPROOF_UI_TEST_SNAPSHOT='.controlproof/ui-integration-20261021/stage6-shared-r3/snapshot.json'
$stage6TestFiles=@(Get-ChildItem -Path tests/unit/test_web*.py,tests/contract/test_platform*.py,tests/contract/test_web*.py -File | Select-Object -ExpandProperty FullName)
$stage6TestFiles+=@('tests/contract/test_shared_web.py','tests/web/test_spec009_display.py','tests/unit/test_catalog_matrix_parity.py','specs/010-platform-ui-integration/checks/test_contract_baseline.py')
& .\.venv\Scripts\python.exe -m pytest @stage6TestFiles -q -p no:cacheprovider --basetemp .controlproof/ui-integration-20261021/pytest-stage6-full-NEW --junitxml=.controlproof/ui-integration-20261021/stage6-full-NEW.xml --tb=short
```

Node 구문 검사·Python AST·`git diff --check` 통과. 기존 .gitignore 등의 LF/CRLF 안내만 있으며 검증 실패가 아니다.
실제 WhyYou preflight/Run·Docker/DB·외부 모델 요청이나 의존성 설치는 하지 않았다.

## 실제 앱 브라우저

- 소개 workflow ArrowRight/End로 한 탭/한 패널 선택과 포커스를 확인했다. 안내 checkbox Space는1/9로 바뀌며 서버 form이 없다.
- 모바일 메뉴 Enter/Escape로 열고 닫아 버튼으로 포커스가 돌아온다. 페이지 이동은 일반 링크이며 현재 링크는 정확히1개다.
  skip Enter는 main을, 이후 Tab은 본문 첫 summary를 포커스한다.
- 검색 “동의”는3개 결과와 URL q로 복원된다. 현황의 “결과 검토하기”는 query 없이12개로 초기화한다.
  “전체 시나리오”도 query 없는 `/results`다.
- N03 일부/조건3개와 근거 Enter/닫기·포커스, E01 원본4/표시7과 근거, N01 PC/모바일 실제 PNG1440/780 로드와 v2 ID를 확인했다.
- H02 실제 비교/보고서의 연결, SHARED/DEMO 준비 form0개/프로필11개, DEMO 오류의 banner와 모든 복귀/탐색 prefix를 확인했다.
- 소개·안내·현황·전체 결과·N03/E01 열린 근거·N01 캡처·H02 비교·보고서·준비·오류를
  1440/1280/1024/390px에서 **44개 root 너비 검사**했다. 가로 넘침0, 마지막 브라우저 console error0이다.

증거: ignored `browser-checks-stage6.json`, `stage6-report-desktop.jpg`와 단계4/5의 상세 동선 캡처.
별도 Playwright UI suite는 실행하지 않았으며 앱 브라우저 실제 조작과 구분한다. 비작성자 이해도는7단계/별도다.

## 실제 브라우저 PDF

설치된 **Edge155 headless print**로 실제 `http://127.0.0.1:8782/report`를 출력했다. 화면의 JavaScript와 beforeprint·CSS를
실행한 Chromium 출력이며, 보고서 내용을 reportlab로 다시 작성하거나 대체 HTML 렌더러로 바꾼 결과가 아니다.
일반 웹 UI의 조작은 앱 브라우저에서 했다. PDF 렌더러는 별도 임시 프로필·숨김 모드이며 사용자 브라우저 프로필/원본을 건드리지 않는다.

최종 A4 **26페이지**,586,813 bytes, SHA-256 `a6e86287cf33c854e983d753a8db7e34286ee4de811f293f82df77ae2989748e`.
파일: `.controlproof/ui-integration-20261021/output/pdf/ControlProof-report.pdf`(로컬 검수 산출물, Git 제외).
원본652개 파일과 별개의 출력물이며 새 봉인 증거·판정이 아니다. 서버 PDF endpoint/의존성은 추가하지 않았다.

`checks/check_print_pdf.py`는 해당 시점의 실제 sanitized `/api/report`와 PDF를 대조한다.

- R1~R13/C1~C9 **22개 실제 내용 전부 통과**. 단순 items_present 복사가 아니라 원래 문장·상태·버전·URL을 대조했다.
- 전체 이력29개 ID/실제28개 Run 링크·검증된27개 버전/해시·모든 실제 child 비교 링크, 미확보 링크 없음.
- N03 A1~A3/U1~U3/L1·후속 조건·D-019 인정 범위·원래 INVALID와 법적 비보증 보존.
- 화면용 skip 없음, 한글 replacement glyph0, 빈 페이지0, 모든 footer/페이지 번호와 A4 확인.
- pdfplumber 문자 좌표의 물리 페이지 바깥0개. Poppler로26페이지 모두 이미지화하고 전체 montage와
  표/버전/마지막 절 확대 페이지를 직접 확인했다. 겹침·잘림·검은 사각형을 발견하지 않았다.
- PDF 추출 UTF-8 텍스트도 기존 sensitive scan을 통과했다. PDF/font 분석기가 일부 FontBBox 진단을 출력했지만
  검사 실패/글리프 손상은 없으며 전체 페이지 시각 확인과 좌표/문자 검사 결과를 함께 보존한다.

PDF 검증은 bundled PDF Python의 pypdf/pdfplumber와 Poppler를 사용했다. 검수 도구를 제품 의존성으로 추가하지 않았다.
`stage6-pdf-r1/r2`는 발견/수정 전후의 이력이며 최종은 `stage6-pdf-r3/{report-api.json,pdf-checks.json,page-*.png,montage-*.jpg}`다.
후자는 PDF SHA와 최종 snapshot ID를 `stage6-snapshot-audit.json`에 연결했다.
Windows의 native 인쇄 대화상자 조작·실물 프린터 출력·인쇄 취소 뒤 UI 상태는 별도 확인하지 않았다.

## 공유본·민감정보·원본 불변

최종 후보 `.controlproof/ui-integration-20261021/stage6-shared-r3/snapshot.json`.
ID `shared-ui-stage6-20261021-r3`, digest `5c1cfd81dd20a4d441141f889ae9837eac32be453620f1e25d0f938ff625a8ad`.

- load_snapshot의 표시 code/catalog/scenario pin·snapshot digest·전체 파일·원래 검증 상태를 통과했다.
- 기본 snapshot SHA는 `26df887d6a8b26bf2a29b311e805de7a7eaebb0eb6ccdcf19710e358d64d99df`로 불변이다.
- 원래 records/target/미확보 선언과 최종 후보를 그대로 대조했다. 양쪽28건/652파일 SHA가 모두 같다.
- 11프로필,27 VERIFIED/원래 INVALID1개, 미확보 N02 1건,12/9/0/3(N03 일부)와 모든 source SHA/계보/판정을 보존했다.
- 28개 후보를 check_shareable로 다시 검사했다. 기존 검토 해시의PNG6개만 사용하며 새로운 이미지 승인을 만들지 않았다.
  원래INVALID는 검토된 해당 ID로만 허용하고, 누락 자료를 만들거나 재봉인하지 않았다.

## 현재 실행과 다음 단계

```powershell
& .\.venv\Scripts\python.exe -m engine.web --shared-snapshot .controlproof/ui-integration-20261021/stage6-shared-r3/snapshot.json --port 8782
```

미리보기 `/`, `/report`, `/prepare`를8782에서 유지한다. 기본 `review-data/snapshot.json` 전환은 하지 않았으므로
현재 code에서 기본 실행의 display mismatch를 우회하지 말고 위 후보를 명시한다.
**다음은7단계 T022**: 팀 이해도 확인, matching code/snapshot의 기본 전환·복구 안내와 최종 인수인계다.
팀 이해도/비작성자 사용성·Spec005 전체 마감은 이번 내부 검수로 완료되지 않는다.
새 actual/WhyYou 수정·원본 재봉인·설치·외부 게시·commit/push/PR/main 병합은 없다.
