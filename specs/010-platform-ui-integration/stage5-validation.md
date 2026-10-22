# Spec010 5단계 — 비교·보고서·테스트 준비

2026-10-21 · `010-platform-ui-integration` · **T018/T019 완료**.
기존 Python/Jinja 서비스의 비교·보고서·준비와 메모 외형을 반영했다. 웹 실행 동작·새 의존성·WhyYou 변경은 없다.

## 반영과 제품 의미

- `/compare/{child}`: 실제 직전 부모/선택 child의 봉인 판정·무결성·실행 상태를 나란히 읽는다.
  규칙별 전후와 양쪽 모든 증거 ref/원문 링크, 변경 차원, 부모 digest, 전체 계보와 각 sealed 정의를 보존한다.
- 추가 `compare.ui`에서 부모 링크/시나리오·프로필 불일치, 순환, 잘못된 ID, 이전 원본 부재·무결성,
  중단/복구 실패를 차단한다. 기존 API 필드·문제 코드·`parent_unchanged=null/NONE_LEGACY` 의미는 유지한다.
  비교 불가일 때 차이·변경 원인을 추정하지 않는다. 원래 양쪽 상태는 차단 안내와 함께 확인한다.
- H02는 검토된 기존 보완 이력을 재사용한다. N01은 정확한 부모/child ID·검토 manifest SHA·측정 버전·
  PASS/PASS·부모 불변 확인을 모두 통과해야 ControlProof 측정 보강 설명을 제공한다. WhyYou 수정이나 최초 FAIL을 만들지 않는다.
  그 밖의 SHA/판정 차이는 수정 원인으로 단정하지 않는다. 별도 로컬 메모와 봉인 재테스트 사유도 출처를 구분한다.
- `/report`: 요약→네 기준 범위/상태→주요 결과→발견·재테스트→증거/버전 부록→방법/한계로 구성했다.
  R1~R13/C1~C9의 실제 내용과 원래 연결은 유지하며 내부 추적 번호는 기본 화면에서 숨긴다.
  주요 공식 child와 중간 기록을 구분해 전체 비교를 펼쳐 읽는다. N01 PASS→PASS도 포함한다.
- 보고서는 현재 N03 범위와 U1~U3/L1·후속 조건을 표시하며 각 실행의 sealed 정의로 연결한다.
  28개 원본과 미확보 N02 1건의 전체 이력, 원래 INVALID, 실행별 원본 버전/해시와 값 부재를 보존한다.
  공유 기록을 “이 PC의 기록”이라고 부르지 않는다. DEMO의 실제 실행 링크는 해당 합성 root에서만 생성한다.
- 구 카탈로그의 별도 PC 재현/출력 문구는 기존 API에서 보존한다. 새 보고서에는 상위 플레이북 §6/D-019의
  H03 DLQ 한 건 인정 범위와 출처를 표시하며 다른 시나리오·현재 버전·AWS 전체로 확대하지 않는다.
  인쇄/PDF 버튼은 브라우저 인쇄 기능을 사용한다. 별도 서버 PDF 생성 기능은 추가하지 않았다.
- 인쇄 전 모든 보고서 details를 펼치고 종료 후 기존 펼침 상태를 복원하는 동작과 인쇄 CSS를 준비했다.
  **실제 PDF 생성·페이지별 시각 검수는 6단계에 남아 있다.** HTML 내용 보존과 PDF 검수 통과를 혼동하지 않는다.
- `/prepare`·`/demo/prepare`: 현재 정의/프로필 목적과 저장된 준비 정보만 읽는다. GET은 실행·확인·저장을 하지 않으며
  과거 Run을 스캔/검증하지 않는다. 11개 프로필을 N/H/A/E로 묶고 A 대상 기능 부재를 별도 안내한다.
  SHARED는 PC 준비/개인 메모를 읽지 않으며 SHARED/DEMO에는 실제 POST form이 없다.
- LOCAL의 기존 `/preflight`·CSRF·프로필 검사를 유지한다. 귀환 입력에 정확한 `/prepare`만 추가 허용하고,
  성공 시 서버가 검증한 scenario ID로 `/prepare#prepare-{id}`를 만들어 해당 항목을 다시 연다.
  외부/이중 slash/query/DEMO 귀환은 거부한다. 명령 복사는 실제 실행을 시작하지 않는다.
- 로컬 수정 메모는 실행 화면의 펼침 영역에 배치했다. 기존 별도 저장·CSRF·검증/마스킹과 봉인 원본 분리를 유지한다.
  공유/DEMO는 메모 입력 form을 제공하지 않는다.

## 실패 시험과 자동 검증

신규 모듈 부재의 RED 후 구현했다. 별도 준비 화면이 과거 결과를 불필요하게 읽는 것을 실제 DEMO 첫 로딩에서 발견해,
SHARED/LOCAL/DEMO 세 모드의 기록 조회 금지 실패 시험을 먼저 만들고 현재 정의/저장 준비만 읽도록 개선했다.
구 workbench JS가 보고서의 기준별 표 제목까지 숨기던 문제는 `tr.group[data-group]`에만 필터를 적용해 고쳤다.
제목이 빈 준비 항목은 실제 `test_plan` 제목·설명으로 연결했다.

1. r1 시점 주 회귀 **252 passed /1 skipped**(제한 환경 junction). platform 전체·baseline·catalog parity와
   기존 읽기 모델/관찰/메모/준비 단위를 포함한다. `pytest-stage5-regression-01`,443.02초.
2. 최종 HTTP·공유/Host/CSRF·Spec009·PNG·보고서 링크 **74 passed /skip0**. 실제 junction 차단도 통과했다.
   `pytest-stage5-http-01`,106.14초, `stage5-http-tests.xml`.
3. 보고서 내용·계보/안전성·귀환 보완 뒤 r3 계약/기존 비교·보고서/baseline **51 passed**.
   `pytest-stage5-final-01`,242.30초, `stage5-final-tests.xml`.
4. 준비 기록 스캔 제거 뒤 관련 모드/페이지/귀환/보고서 **11 passed /18 deselected**.
   `pytest-stage5-preparation-final`,30.12초, `stage5-preparation-tests.xml`.

위 명령들의 중복을 제거한 관련 항목은309개이며 junction도 별도 권한 검사에서 통과했다.
후반 수정은 해당 검사와 실제 화면으로 재검증했으며 전체 엔진 suite나 Playwright UI suite 전체를 실행한 것은 아니다.
실제 WhyYou preflight/Run·모델/DB 요청은 없다. 테스트 fixture·대역 결과는 공식 결과가 아니다.

주 회귀 명령:

```powershell
$env:CONTROLPROOF_UI_TEST_SNAPSHOT='.controlproof/ui-integration-20261021/stage5-shared-r1/snapshot.json'
& .\.venv\Scripts\python.exe -m pytest tests/contract/test_platform_delivery.py tests/contract/test_platform_detail_pages.py tests/contract/test_platform_details.py tests/contract/test_platform_overview.py tests/contract/test_platform_public_pages.py tests/contract/test_platform_png.py specs/010-platform-ui-integration/checks/test_contract_baseline.py tests/unit/test_catalog_matrix_parity.py tests/unit/test_web_readmodel_workbench.py tests/unit/test_web_readmodel_scenario.py tests/unit/test_web_readmodel_run.py tests/unit/test_web_readmodel_compare.py tests/unit/test_web_readmodel_report.py tests/unit/test_web_evidence_view.py tests/unit/test_web_n02_review.py tests/unit/test_web_review.py tests/unit/test_web_run_readability.py tests/unit/test_web_remediation_history.py tests/unit/test_web_preflight.py tests/unit/test_web_memos.py -q -p no:cacheprovider --basetemp .controlproof/ui-integration-20261021/pytest-stage5-regression-01 --tb=short
```

이 명령은 당시 r1 코드와 초기20개 신규 계약의 이력이다. 현재 새 계약29개를 포함해 재실행할 때는 현재 r4 후보와
새 basetemp를 사용한다. 최종 사용한 나머지 범위는 다음과 같다.

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/contract/test_web_http.py tests/contract/test_web_http_us2.py tests/contract/test_shared_web.py tests/web/test_spec009_display.py tests/contract/test_platform_png.py tests/contract/test_web_report_links.py -q -p no:cacheprovider --basetemp .controlproof/ui-integration-20261021/pytest-stage5-http-01 --junitxml=.controlproof/ui-integration-20261021/stage5-http-tests.xml --tb=short
$env:CONTROLPROOF_UI_TEST_SNAPSHOT='.controlproof/ui-integration-20261021/stage5-shared-r3/snapshot.json'
& .\.venv\Scripts\python.exe -m pytest tests/contract/test_platform_delivery.py tests/unit/test_web_readmodel_compare.py tests/unit/test_web_readmodel_report.py specs/010-platform-ui-integration/checks/test_contract_baseline.py -q -p no:cacheprovider --basetemp .controlproof/ui-integration-20261021/pytest-stage5-final-01 --junitxml=.controlproof/ui-integration-20261021/stage5-final-tests.xml --tb=short
& .\.venv\Scripts\python.exe -m pytest tests/contract/test_platform_delivery.py -k 'preparation or service_pages or report_reproduction or shared_rejects' -q -p no:cacheprovider --basetemp .controlproof/ui-integration-20261021/pytest-stage5-preparation-final --junitxml=.controlproof/ui-integration-20261021/stage5-preparation-tests.xml --tb=short
```

## 실제 앱 브라우저

- 보고서의 네 기준 제목/22개 내용·현재 N03 범위·8개 주요 비교와 나머지 중간 이력 접근을 확인했다.
  증거 부록29행과 미확보7b59237e의 링크0개, 버전 원본 연결을 확인했다.
- N01의 실제 부모/child·PASS/PASS·측정v1/v2·원인 설명을 확인했다. 키보드 Enter로 양쪽 자료를 펼치고,
  실제 부모 증거 원문으로 이동한 뒤 브라우저 뒤로 가기로 같은 child 비교에 돌아왔다.
- H02의 실제 FAIL/PASS·별도 서비스 보완 설명·전후 관찰 패널을 확인했다.
- 원래 INVALID ce5f2750 비교는 CHILD_NOT_VERIFIED 안내·원래 무결성 실패 표시·비교 규칙0개다.
- 별도 로컬 QA 서버8783은 임시 합성 E02 기록과 FakeRunner만 사용했다. 준비 확인 대역2회/선택 항목 자동복귀/
  명령 복사/별도 메모 저장·귀환을 확인하고 fixture 재검증 VERIFIED를 확인했다. 실제 대상 요청 없이 검수 후 종료했다.
- SHARED/DEMO 준비에 실제 form0개와 프로필11개를 확인했다. 최종 후보에서 DEMO 첫 진입이 완료되는 것도 다시 확인했다.
- 준비/DEMO·로컬 메모·보고서 기본/증거 펼침·N01/H02 비교를1440/1280/1024/390px에서 확인했다.
  모든 root scrollWidth는 viewport 이하. 표는 모바일에서 내부 가로 스크롤을 사용한다.

캡처/기록: ignored `.controlproof/ui-integration-20261021/stage5-*.jpg`, `browser-checks-stage5.json`.
브라우저 전체 오류/키보드 순회·PDF 페이지 검수·비작성자 이해도는6단계/별도 검수에 남는다.

## 최종 후보와 실행

후보 `.controlproof/ui-integration-20261021/stage5-shared-r4/snapshot.json`.
ID `shared-ui-stage5-20261021-r4`, digest `d0daceb2f744da4d8dcffc087266d3ca73f4d07c6c7ca61302f0263888130cde`.
load_snapshot 전체 검증과 원래 snapshot SHA 불변,28개 records/미확보/target 일치 및 양쪽652파일 SHA 일치를 확인했다.
27 VERIFIED/원래 INVALID1개·미확보1개·12/9/0/3(N03 일부)·11프로필·검토 PNG와 source SHA는 그대로다.
r1/r2/r3는 각 당시 코드/검수 맥락으로 보존하며 기본 snapshot은 변경하지 않는다.

```powershell
& .\.venv\Scripts\python.exe -m engine.web --shared-snapshot .controlproof/ui-integration-20261021/stage5-shared-r4/snapshot.json --port 8782
```

미리보기 `/report`, `/compare/d3aac7d9-0a52-4f9a-9c8f-f6e1f7b6de18`, `/prepare`를 같은8782에서 연다.
현재 코드는 원래 기본r2와 맞지 않으므로 위 후보를 명시한다. 표시 해시 검사를 우회하거나 원본을 다시 봉인하지 않는다.
T020은 최종 후보 생성/해시 검증까지 부분 수행이다. 6단계 통합·PDF QA,7단계 팀 검수·기본 전환/복구·인계가 남아 있다.
새 실제 Run·WhyYou 수정·설치·게시·기본 전환·commit/push/PR/main 병합은 수행하지 않았다.
