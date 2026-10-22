# Spec010 통합 분석 — 0·1단계

2026-10-22 main 사전 분석: nested HTML의 display pin 누락을 발견해 RED add/edit2개 뒤 보완했다.
이전 실제 원본/판정은 불변이고 새 표시 공유본을 검증한다. [현재 게시 검증](main-publication.md).

2026-10-22 후속 FR-017: [발표 화면 정돈의 사전 분석·해소·검증](presentation-polish.md).
95개 관련 검사와8개 실제 화면 상태/키보드·원본 불변 확인 후 기본을 새 공유본으로 갱신했다. 미해결 CRITICAL/HIGH 0.

최종: 0~7단계 분석/구현/검수/기본 전환 완료. 사용자 팀 검토 완료 간주에 따라 T022를 마쳤다.
[최종 검증](stage7-validation.md)과 [실행/복구](quickstart.md)가 현재 기준이며 아래 단계별 미착수 상태는 이력이다.

2026-10-21 · 사용자 승인 범위: 명세·계약 준비. 제품 구현 gate는 이 분석과 Validation 뒤에 위치한다.

## 점검 범위

현재 HEAD·AGENTS/read-first·Constitution·Spec005/008/009·실제 server/readmodel/shared_records·디자인 5개와
M01~M14를 교차 대조했다. 명세 작성, 데이터 계약, HTTP/PNG 계약을 병렬 작성한 뒤 독립 읽기 검토를 수행했다.
각 담당의 파일 소유 범위를 나눴으며 엔진·웹 런타임·카탈로그·시나리오·공유 원본은 수정하지 않았다.

## 발견과 해소

| ID | 중요도 | 발견 | 해소 |
| --- | --- | --- | --- |
| A01 | HIGH | `latest_run`은 공식 final이 아닌 전체 실행 시간순이며 링크 5개는 전체 이력이 아님 | 기존 의미 유지, DATA-04의 별도 프로필 대표/전 이력 투영 |
| A02 | HIGH | 대표의 시각을 원본 부재 상태에서 추정하면 과거 PASS로 잘못 대체할 수 있음 | final/repeat 카탈로그 선언 순서·최신 확인 분리, selection 문제 유지·묵시 fallback 금지 |
| A03 | HIGH | N-03 현재 scope 문자열을 과거 실행의 사실로 사용하기 쉬움 | DATA-05 current/sealed 구조·해시/출처 분리, 원래 판정 불변 |
| A04 | HIGH | PNG를 일반 static mount나 텍스트 redaction으로 제공하면 경계 손실 | PNG 별도 Run/ref·strict verify·검토 allowset·동일 buffer·MIME/signature/8MiB 계약 |
| A05 | MEDIUM | 데이터 초안의 profile query는 HTTP 계약에 없었음 | 프로필 탭/anchor와 기존 Run 링크로 선택, 별도 query 추가 안 함 |
| A06 | MEDIUM | PNG 미등록 Run 404와 등록 자료의 허용 정책 실패 403 문구가 겹침 | png 계약 §3/오류표와 IMG-20을 동일 정책으로 명확화 |
| A07 | MEDIUM | HTTP-03에서 기존 NOT_RUN=0 키 생략이 신규 집계 필수 키와 혼동됨 | 기존 treatment_counts 키 구조 보존·누락만0 해석, 신규 ui.coverage와 구분 |
| A08 | MEDIUM | 준비한 83사례를 현재 API/새 경로 PASS로 보고할 위험 | cases 상태 PREPARED/NOT_EXECUTED 및 현행 특성 검사와 구분 |
| A09 | MEDIUM | 실행 환경의 socket 접속 차단으로 실제 HTTP 전송 검증 불가 | 기존 핸들러 in-process 검사로 한정, transport/브라우저 미검수 명시 |

독립 검토는 실제 `_scenario_runs`, `_scenario_profile`, legacy H03 null, ABORTED 텍스트 완화,
Host→shared POST 검사 순서, 오류 HTML/JSON 분기, PNG 게시 승인과 snapshot 필드를 대조했다.
초기 독립 검토에서 CRITICAL/HIGH 추가 발견은 없었고 A06/A07의 문구 권고를 반영했다.

## 추적성과 범위

FR-001~016은 tasks와 traceability에 전부 연결했고 M01~M14도 매핑했다.
SC-01/02는 0·1단계 준비, SC-03은 원본 보존, SC-04는 이후 실제 구현/화면 검수다.
클라이언트 판정 재계산·새 판정 enum·웹 실행 기능·WhyYou 변경·원본 재봉인이 없다.
Constitution I~VII는 plan의 점검과 데이터/PNG/모드 계약에 연결했다.

**설계 분석의 미해결 CRITICAL 0 / HIGH 0.** 이는 신규 구현의 보안/성능/사용성 검수 통과를 뜻하지 않는다.
현재 자동 검사 결과와 한계는 [Validation](validation.md)에 기록한다. 이후 구현은 T009부터 별도 수행한다.

## 2단계 후속 승인·구현 전 점검

사용자가 다음 단계 진행을 승인했다. T009 실패 시험 뒤 T010을 수행한다. 기존 계약/명세 선택을 유지하며 새 미결 사항은 없다.
소개/안내는 기존 템플릿과 자체 정적 CSS/JS로 제공하고 새 외부 의존성·네트워크·호스팅을 추가하지 않는다.
공식 범위 요약만 카탈로그에서 읽고 준비 상태나 원본 Run을 소개 페이지 생성에 조회하지 않는다.
기존 워크벤치 공통 외형/탐색은 갱신하되 판정/증빙/보고서 본문은 보존한다. 새 경로로 연결하는 메뉴는 경로 구현 뒤에만 노출한다.
PNG·새 목록은 아직 제공하지 않는다. 후보 snapshot의 원본 28건/652파일·검토 PNG·INVALID/누락을 보존한다.
설계 미해결 CRITICAL/HIGH 0을 유지하며 실제 구현·동작 결과는 별도로 검증한다.

## 3단계 후속 승인·구현 전 점검

T011/T012 승인. 데이터/HTTP 계약의 범위 집계·N03 current scope·N/H/A/E 표시 순서와 strict URL query를 사용한다.
판정과 준비 상태를 다시 계산하지 않는다. 원래 API groups 순서는 보존하고 새 UI groups만 정렬한다.
기존 표의 상세 정보/로컬 준비 확인은 결과 목록의 접힌 영역에 남기고 기존 상세·실행·비교·보고서를 연결한다.
N03 미검증은 현재 YAML 출처로 명시하며 과거 Run의 검증 사실처럼 표현하지 않는다. A는 진행률을 만들지 않는다.
검색은 GET URL만 상태로 사용하고 전체 링크는 query를 붙이지 않는다. 새 외부 의존성/inline script/style 없음.
설계 미해결 CRITICAL/HIGH 0. 실패 시험→표시 구현→새 후보 snapshot 검증→브라우저 검수 순서다.

## 4단계 승인·구현 전 분석

T013~T017 승인. DATA04~08/PNG 계약의 선택과 기존 읽기 모델을 대조했다. 미해결 CRITICAL/HIGH 0.
공식 대표는 프로필별 final/repeat 선언의 마지막 ID로 고정하며 누락/INVALID를 과거 PASS로 대체하지 않는다.
현재 정의와 각 Run 봉인 정의는 SHA/출처와 함께 별도 제공한다. 기존 latest_run/previous_runs와 API 의미는 유지한다.
PNG는 strict verify를 요청마다 새로 수행한다. 선택 snapshot의 files만 SHARED 승인 원천으로 쓰고 LOCAL/DEMO는
별도 서버 내부 allowset 기본 공집합이다. 경로/link 검사, 안전한 file handle·동일 buffer hash 및 전후 상태 검사로
검증 뒤 파일 교체를 차단한다. Windows reparse/junction도 거부한다. 바이너리는 텍스트 redaction을 통과시키지 않는다.
텍스트 응답의 기존 마스킹은 유지한다. 8MiB 상한/PNG signature/MIME/manifest size·hash를 모두 검사한다.
새 모듈은 표시/읽기 전용이며 판정 엔진·WhyYou·652개 원본을 변경하지 않는다. 템플릿은 조건·자료·오류의 기존 내용을 보존한다.

4단계 검수 해소: wrapped sealed definition·v1 원본 버전 null·Windows ctime API 차이를 확인하고
원본 hash/null과 안전한 handle 검사를 유지하는 표시/읽기 방식으로 고쳤다. 승인된 후보에서243개 회귀를 확인했다.
PNG는 안전한 경로 검사와 strict verify를 index보다 먼저 적용한다. 중복 오류의 순서는 PNG 계약에 명시했다.
DEMO의 대표는 ACTUAL 카탈로그 ID를 쓰지 않고 합성 이력으로 선택한다. 미해결 CRITICAL/HIGH 0.

## 5단계 구현 전 분석

T018/T019 승인. 기존 compare/report/preflight/memo 구현과 DATA05~08/HTTP 계약을 대조했다.
기존 `parent_unchanged=null/NONE_LEGACY`는 오류가 아니며, 추가 ui 관계 오류는 원래 API 필드를 바꾸지 않는다.
parent 링크/Run 불일치·시나리오/프로필 불일치·순환은 ui 비교를 차단하고 원래 상태를 함께 읽는다.
변경 원인은 검토된 H02 설명/정확한 N01 부모·child 및 측정값 출처에서만 제공한다. 임의 SHA 차이는 원인으로 추정하지 않는다.
보고서 22개 내용과 현재/봉인 범위·전 이력·버전/원본 ref를 새 템플릿에 배치하며 인쇄 때 모든 본문을 펼친다.
DEMO에서 실제 공식 ID로 연결하지 않고 합성 root의 ID만 사용한다. SHARED는 PC 준비/메모를 조회하지 않는다.
준비 화면 GET은 저장된 정보만 읽는다. `return_to=/prepare`를 정확히 허용하며 query/외부/DEMO 주소는 거부한다.
로컬 메모는 기존 CSRF/출력 마스킹·원본과 별도 저장 정책을 유지한다. 새 웹 실행 동작/의존성은 없다.
설계 미해결 CRITICAL 0 / HIGH 0. 실제 구현 검수 결과는 별도 stage5-validation에 기록한다.

5단계 검수: 원래 JS의 보고서 그룹 숨김·빈 준비 제목·준비 화면의 과거 기록 스캔을 발견해 고쳤다.
D-019 인정 범위/브라우저 출력 문구를 현재 UI에서 구분하며 기존 API 텍스트 의미는 보존한다.
관련 자동 검사와 실제 모드/너비/키보드·메모 검수, 후보28/652 불변을 확인했다. 미해결 CRITICAL/HIGH 0.
전체 PDF/사용성/통합 gate는 후속이며 자세한 한계는 stage5-validation에 기록한다.

## 6단계 구현 전 분석

T020/T021 승인. 기존 판정/652원본·공유 모드와 출력 경계를 유지한 읽기/검수 작업이다. 기본 전환/새 실제 실행은 없다.
문제 발견 시 정의된FR/계약 안에서 UI만 수정한다. PDF 도구의 브라우저 엔진·출력/진단 지원을 먼저 확인하고,
인쇄 이벤트가 실행된 사실·대체 렌더링·최종 PDF 페이지 검수를 구분한다. 미지원 기능을 통과로 표시하지 않는다.
설계 미해결 CRITICAL/HIGH 0. 원본 동결과 새 후보·실제 검증/문서 수렴 순서는 유지한다.

6단계 해소: page link/tab 의미, PDF skip/작은 버전 글자/페이지 경계, raw commit dict와 없는 legacy ref,
DEMO HTML 오류의 ACTUAL 복귀를 관찰하고 실패 시험 뒤 고쳤다. 기존 JSON/API·판정은 보존한다.
최종324/skip0·앱44개 너비/키보드·실제 PDF26페이지/22내용·새후보28/652불변 확인. 미해결 CRITICAL/HIGH 0.
검수 한계와7단계 팀 이해도/기본 전환은 stage6-validation에 분리했다. 전체 Spec 완료를 뜻하지 않는다.

## 7단계 전환 전 분석

사용자가 팀 검토를 완료로 간주하여 T022 전환을 승인했다. 현재 default r2는 변경된 표시 코드와 불일치하며
정상 거부 중이다. 검증된 stage6 r3 JSON을 그대로 기본으로 승격하면 pin을 우회하거나 증거를 재봉인할 필요가 없다.
이전 r2를 같은 bundles 부모 아래 별도 이름으로 보존하여 fb219d0와 함께 복구할 수 있게 한다.
baseline은 역사 기록이므로 수정하지 않는다. 후보 생성기가 동결된 기본 파일 SHA를 전제하는 의존성을 발견했으므로
동일 SHA의 명명된 보존본만 허용하는 선택을 추가하고 누락/변조는 거부하도록 시험한다.
사용자의 전환 수용과 관찰하지 않은 외부 사용성 검수를 구분한다. 코드/봉인 원본/의존성 변경 없음.
미해결 CRITICAL 0 / HIGH 0. 전환 전 검증/보존, 일반 실행 검증, 별도 경로 복구 검증 뒤 문서를 마감한다.

7단계 해소: 기본 snapshot을 검증된 r3 그대로 승격하고 이전 r2 및 baseline을 보존했다.
51개 고유 전환/공유 검사·일반 CLI HTTP17개·앱 현황/12개 결과 복귀와 이전 코드 로더의 실제 r2 로드 검증을 마쳤다.
후보 생성기의 동결 원천 선택도 실제 새 후보 생성으로 확인했다. 원본/판정 변경·pin 우회는 없다.
기존 미리보기 종료는 자동 승인 검토가 거부하여 중단하고 별도 포트의 정상 기본 실행으로 검증했다.
미해결 CRITICAL 0 / HIGH 0. Spec010 로컬 프론트엔드 범위를 마감하며 외부 사용성·게시·새 actual을 완료로 추정하지 않는다.
