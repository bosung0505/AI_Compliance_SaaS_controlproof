# Spec010 4단계 — 테스트 상세·실행·증빙

2026-10-21 · `010-platform-ui-integration` · **T013~T017 완료**.
기존 Python/Jinja 서비스의 실제 기록 읽기 화면을 바꿨다. 새 WhyYou 실행·판정 변경·원본 재봉인·게시 작업은 없다.

## 반영한 화면과 데이터

- `/scenarios/{id}`: 시험 목적, 공식 이력, 프로필별 공식 대표 결과, 현재 정의, 전체 실행 이력과 준비 안내.
  H03/E03의 두 프로필은 서로 다른 시험 목적과 실제 Run 링크를 가진다. E01/E02는 final 뒤 승인된 repeat를 대표로 쓴다.
- 대표는 카탈로그 final/repeat 선언의 마지막 항목이다. `latest_run`의 기존 시간순 의미는 그대로다.
  대표 누락·INVALID·불일치는 문제 코드로 표시하며 과거 PASS로 바꾸지 않는다. 공식 대표의 최신 시각 확인도 별도다.
- `scenario.ui.history`는 공유 28개 원본과 문서상 미확보 N02 1건을 포함한다. 시각 확인 불가 항목은 뒤에 둔다.
  미확보 행에 성공 링크를 만들지 않는다. INVALID 행은 차단 상태를 확인하는 원래 Run 화면으로 연결한다.
  H03 legacy null은 확인된 H03/v1/무프로필 계약과 봉인 정의를 확인해 호환 표시하며 원본 null은 유지한다.
- 현재 YAML과 해당 Run의 봉인 정의를 source/ref/version/SHA-256으로 구분한다. 전제/단계/규칙·기대값/
  필수 자료/복구/제약 시간/capability/제외·미검증/후속 조건을 펼쳐 읽는다. 원래 정의나 판정은 바꾸지 않는다.
- `/runs/{id}`: 실제 Run ID 선택, 조건별 기대·관찰 카드, 연결된 다중 자료, 원본 규칙·전체 파일 목록·안전 상태.
  N03 A1~A3의 일부 실행과 U1~U3/L1을 유지한다. 현재 정의를 과거 실행의 확인 사실로 섞지 않는다.
  H/N/E별 기존 비교·관찰값 구성요소와 메모·명령/준비 안내는 보존한다.
- E01은 원본 규칙4개/표시 조건7개, AI 입력과 실제 저장값 비교를 유지한다. D1은 주 조건에 포함하지 않는다.
- N01은 PC/모바일 캡처, 다섯 고지의 측정 원문, 화면·서버·저장 정책 식별값을 함께 읽는다.
  과거 v1은 원본 `measurement_version=null`을 보존하고 별도의 호환 표시 버전1/출처를 제공한다.
  v2는 봉인 필드2를 읽는다. PASS→PASS는 ControlProof 측정 보강이며 WhyYou 수정/최초 FAIL로 만들지 않는다.
- `/runs/{id}/evidence`: 선택 조건으로 돌아가는 문맥, 발췌/전체 원문, 파일 형식/크기/SHA와 검토된 PNG 열람.
  고지 관련 자료명은 읽기 쉬운 표시 제목을 더하며 기존 evidence ref/원래 자료명·경로 정보는 유지한다.
- DEMO는 실제 공식 Run ID를 대표로 가져오지 않는다. 공식 대표 없음으로 표시하고 해당 DEMO root의 합성 이력을 선택한다.

## PNG content 경계

새 GET `/runs/{id}/evidence/content?ref=…`와 DEMO 대응 주소를 구현했다. ref를 서버 파일 경로로 사용하지 않는다.
SHARED는 선택한 검증 snapshot의 Run/files 해시, LOCAL/DEMO는 독립 서버 내부 `(Run, ref, SHA)` allowset을 사용한다.
명시적 로컬/DEMO 승인 목록은 기본 공집합이며 URL/form에서 변경하지 못한다.

매 요청에서 엄격한 원래 verify를 새로 수행한다. ABORTED의 텍스트 예외/기존 캐시를 이미지 승인으로 사용하지 않는다.
경로·전체 부모 reparse/link·MIME·suffix·manifest와 index의 크기/해시·snapshot manifest 해시를 확인한다.
Windows는 쓰기/삭제 공유 없는 안전한 handle과 최종 경로 확인, 읽기 전후 동일성 검사를 사용한다.
PNG signature/8MiB 상한/원본 SHA 검증을 통과한 동일 buffer만 반환한다. 변환·redaction·재압축은 하지 않는다.
원래 텍스트 응답의 redaction/CSP·Host·CSRF/공유 POST 거부는 유지한다.

경로/link는 메타데이터를 읽기 전에 방어하고, strict verify 후 index를 해석한다. 이는 여러 오류가 겹칠 때
검증 불가 Run의 내부 index 존재를 사실로 노출하지 않기 위한 순서다. PNG 계약의 4단계 보충 설명을 따른다.

## 검증 결과

실패 시험부터 작성했다. 초기 모듈 부재 실패 뒤 구현했다. 검수에서 다음을 발견해 고쳤다.

- 봉인 YAML은 `definition`에 감싸인 형태도 있었다. 전체 파일 SHA를 유지하며 내부 정의를 읽도록 했다.
- v1 측정 버전 필드는 없었다. 원본 null과 명시적 legacy 표시 출처를 분리했다.
- Windows path stat/handle fstat의 ctime 의미가 달랐다. 같은 API 안의 시간과 공통 identity/크기/mtime를 비교하며
  안전한 handle·최종 경로·원본 hash 검사는 유지했다.
- 긴 기술 원문은 접힌 정의에 보존하고, 여러 프로필의 첫 화면에는 짧은 시험 목적 설명을 제공했다.

주 회귀: **198 passed /1 skipped**(제한 실행 환경의 junction 생성). 명령은 다음과 같다.

```powershell
$env:CONTROLPROOF_UI_TEST_SNAPSHOT='.controlproof/ui-integration-20261021/stage4-shared-r2/snapshot.json'
& .\.venv\Scripts\python.exe -m pytest tests/contract/test_platform_public_pages.py tests/contract/test_platform_overview.py tests/contract/test_platform_details.py tests/contract/test_platform_detail_pages.py tests/contract/test_platform_png.py specs/010-platform-ui-integration/checks/test_contract_baseline.py tests/unit/test_catalog_matrix_parity.py tests/unit/test_web_readmodel_workbench.py tests/unit/test_web_readmodel_scenario.py tests/unit/test_web_readmodel_run.py tests/unit/test_web_readmodel_compare.py tests/unit/test_web_readmodel_report.py tests/unit/test_web_evidence_view.py tests/unit/test_web_n02_review.py tests/unit/test_web_review.py tests/unit/test_web_run_readability.py tests/unit/test_web_remediation_history.py -q -p no:cacheprovider --basetemp .controlproof/ui-integration-20261021/pytest-stage4-final-01 --tb=short
```

실제 loopback HTTP·공유/무결성·Spec009 표시 회귀와 PNG 경계는 환경 권한을 사용해 **71 passed /skip0**.
위에서 skip한 실제 junction 차단도 여기서 통과했다. PNG27개가 두 명령에 겹치며 중복을 제거하면 **243개 통과**다.

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/contract/test_web_http.py tests/contract/test_web_http_us2.py tests/contract/test_shared_web.py tests/web/test_spec009_display.py tests/contract/test_platform_png.py -q -p no:cacheprovider --basetemp .controlproof/ui-integration-20261021/pytest-stage4-http-final-01 --tb=short
```

프로필 목적 문구 보완 후 관련 상세/HTML 계약 **24개 재통과**(`pytest-stage4-labels-final-01`).
마지막 상단 결과 이동 버튼 보완 후 같은 **24개 재통과**(`pytest-stage4-cta-final-01`,15.83초).
단일 공식 대표는 상단에서 직접 열고, 여러 프로필은 프로필별 결과 영역으로 이동한다. 모바일 상단 동선도 확인했다.
Node 구문 검사와 `git diff --check`도 통과했다. 원래 `.gitignore` 등 LF/CRLF 안내는 오류가 아니다.
PNG 검사는 실제 PC/모바일·부모 바이트, strict ref, unknown/INVALID/비PNG, 모드·tuple·snapshot hash,
파일 변경/누락/경로·junction, 크기/해시/signature/정확한8MiB, Range200/헤더와 no-inline 정책을 포함한다.
합성 메타데이터로 분기 검사를 할 때만 verifier를 명시적으로 대역 처리하며 실제 원본 변조 검사는 임시 복사본에서 한다.
계약 JSON의 모든83개 사례가 새로 실행됐다는 뜻은 아니다. 이 명령들은 새 WhyYou 실제 Run이 아니다.

## 실제 브라우저

앱 브라우저에서 N03 상세→Run→제출 응답 원문→같은 조건 복귀, 원문 펼침과 닫기 포커스를 확인했다.
N01 PC/모바일 PNG가 실제 로드되며 정책3곳의 버전/해시를 읽을 수 있고 v2→원래 v1 ID 전환도 유지된다.
H03/E03의 두 프로필, N02 미확보 링크 없음/INVALID 판정·관찰 차단, E01 4/7과 입력/저장값 비교를 확인했다.
N01 v1 실행·E01 열린 근거·N03 상세/실행·PNG 화면을 1440/1280/1024/390px에서 확인했으며 가로 넘침이 없다.
데스크톱/모바일 캡처와 기록은 ignored `.controlproof/ui-integration-20261021/stage4-*.jpg`,
`browser-checks-stage4.json`에 보존한다. Playwright UI suite 전체는 실행하지 않았으며 위 실제 앱 검수와 구분한다.
전체 엔진 suite, PDF/5단계 비교·보고서 본문 개편, 비작성자 사용성은 미실시다.

## 현재 후보와 실행

최종 후보 `.controlproof/ui-integration-20261021/stage4-shared-r4/snapshot.json`, ID `shared-ui-stage4-20261021-r4`.
digest `a2a01f6cb235d0b6544f3c40afb3b23c92c9ef9ef05b8387f5606f65fb9b4c84`.
원본28개 records/652개 파일·27 VERIFIED/원래 INVALID1개·미확보1건·target/source SHA·검토 PNG 해시는 동일하다.
각 후보는 새 경로로 생성했고 전체 load 검증을 통과했다. r1/r2/r3는 문구·상단 동선 보완 전 맥락으로 보존한다.
기본 `review-data/snapshot.json`은 보존하며 기본 전환은 하지 않았다. 이전 기본 r2는 새 표시 코드와 짝이 아니므로
해시 검사를 우회하지 말고 아래 후보를 지정한다.

```powershell
& .\.venv\Scripts\python.exe -m engine.web --shared-snapshot .controlproof/ui-integration-20261021/stage4-shared-r4/snapshot.json --port 8782
```

미리보기 `http://127.0.0.1:8782/`, N03 `/scenarios/N-03`, N01 `/scenarios/N-01`.
서버를 종료한 뒤에는 위 명령으로 다시 실행한다. T020은 후보 검증까지 부분 수행이다.
5단계 T018/T019(비교·보고서·별도 준비 화면/메모 개편), 기본 게시/전환은 아직 남아 있다.
설치·새 actual Run·WhyYou 변경·커밋/push/PR/main 병합은 수행하지 않았다.
