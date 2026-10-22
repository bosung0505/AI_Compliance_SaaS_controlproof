# UI 데이터·상태 계약

작성 2026-10-21 · 기준 `fb219d0c6923c6be09691fcae0ead670f9700b39` · 상태: **6단계 통합 검수 완료, 기본 전환은 후속**

현재 추가 구현: `scenario.ui.profile_results/history/current_definitions/default_profile`,
`run.ui.sealed_definition/profile/notice_measurements/related_runs/problems`와 표시용 제목·설명 맵.
기존 API 의미/필드는 유지하며 아래 계약의 source/ref/SHA와 현재/봉인 scope를 분리한다.
`history.time_confirmed`는 정렬·시각 불명 표시용이다. DEMO는 실제 카탈로그의 공식 ID를 승격하지 않고
`DEMO_HAS_NO_OFFICIAL_RESULT`로 안내하며 해당 DEMO root의 합성 이력만 고른다.
N01 `measurement_version` 원본 null은 유지하고 `measurement_display_version=1`,
`measurement_version_source=LEGACY_N01_COMPATIBILITY`로 기존 엔진 v1 호환 읽기를 명시한다.
프로필 `display_purpose/purpose_source`, 조건/자료의 쉬운 표시 제목은 출처를 구분하는 UI 설명이며 새 판정이 아니다.
아래 ‘추가 예정’ 원문은 계약 당시 표현이다. 현재 결과는 [4단계 검증](../stage4-validation.md)을 따른다.

현재 구현: `workbench.ui.coverage`, `workbench.ui.groups`(N/H/A/E 표시 순서, title/purpose),
`groups[].scenarios[].ui.current_scope`와 그룹 `ui.coverage`. 원래 groups 순서와 기존 API 필드는 유지한다.
current_scope는 해당 현재 파일의 source/source_ref/version을 함께 표시하며 N03에서 A/U/L 항목을 읽는다.
3단계 당시 다른 `scenario/run/report.ui` 정의/공식 대표/전 이력 투영은 추가 예정이었다. 이하 ‘추가 예정’ 원문은
0·1단계 계약 당시의 표현이며 현재 구현/검증 범위는 [3단계 기록](../stage3-validation.md)과 구분한다.

이 문서는 새 화면이 읽을 값과 파생 규칙을 고정한다. 기존 `controlproof.web.v1` 응답을 대체하지 않는다.
문서에 **추가 예정**으로 표시한 필드와 집계 fixture는 현재 구현되어 있다는 뜻이 아니다.
적용 대상은 실제 공유/로컬 기록 및 별도 DEMO의 표시 계층이며, Run 판정·봉인 원본·실행기는 변경하지 않는다.

## DATA-01 — 원천과 호환성

| 원천 | 현재 계약과 용도 |
| --- | --- |
| `catalog/mvp-scenarios.yaml` | 12개 시나리오, 기준, 대상 존재, `mvp_treatment`, 공식 상태, 프로필, 공식 Run 지정 |
| `WorkbenchReader` (`engine/web/readmodel.py`) | JSON과 HTML의 공통 읽기 모델; 무결성 확인·출력 마스킹 유지 |
| `review-data/snapshot.json` | 선택한 공유본 ID·시각·28개 Run·파일 해시·누락 기록; 숫자 하드코딩 금지 |
| 각 Run의 `run.json`, `judgement.json`, `manifest.json`, `scenario.snapshot.yaml` | 해당 실행의 상태·판정·증빙·당시 정의; 무결성 검사를 통과한 내용만 결과로 제공 |
| 현재 `scenarios/*.yaml` | 현재 시험 정의와 미검증/후속 조건; 과거 실행의 봉인 정의와 구분 |
| 준비 저장본·메모 저장본 | 로컬 모드에서만 사용; 공유본·봉인 원본 밖의 별도 데이터 |

현재 `/api/workbench`, `/api/scenarios/{id}`, `/api/runs/{run_id}`, `/api/compare/{child_run_id}`, `/api/report`의
필드·형식·오류 의미를 유지한다. API의 `schema_version`은 `controlproof.web.v1`을 유지한다.
새 화면을 위해 필요한 값은 각 관련 응답의 선택적 **`ui` 객체에 additive projection으로 추가 예정**이다.
아래의 `ui.*`는 전부 Spec010 신규 표시 필드이며 현재 API 필드로 오인하지 않는다. 기존 클라이언트는 이 객체를 무시할 수 있어야 한다.
HTML과 API의 `ui`는 같은 서버 표시 계층에서 생성한다. 브라우저가 파일을 읽거나 독립적으로 verdict를 재계산하지 않는다.

## DATA-02 — 상태를 합치지 않는다

| 차원 | 기존 원천 | 화면 원칙 |
| --- | --- | --- |
| 대상 존재 | `target_exists` | `false`는 실제 기능 부재의 근거가 있을 때만 허용 |
| 처리 범위 | `mvp_treatment` = `EXECUTED / NOT_RUN / NO_TEST_TARGET` | 도넛 집계 원천; FAIL·판정 불가도 실행한 범위일 수 있음 |
| 공식 결과 | `official.result`, `official.reason_code` | 카탈로그의 승인된 결과; 28개 이력 verdict의 합과 별개 |
| 실행 상태 | `run.run_state` | `PENDING / RUNNING / RESTORING / COMPLETED / ABORTED / RESTORE_FAILED` 그대로 유지 |
| 준비 상태 | 기존 `readiness` | `READY / RUNNER_NOT_READY / ACCESS_BLOCKED / NO_TEST_TARGET`, 오류·설정 필요의 기존 null 처리 유지 |
| 무결성 | `integrity.status`, `integrity.problems` | VERIFIED와 판정은 별개; INVALID 등을 대상 서비스 FAIL로 바꾸지 않음 |
| 복구 | `restore.status`, `safety_badges` | 실패·수동 확인을 우선 표시; READY나 PASS로 대체하지 않음 |
| 원본 존재 | `records_on_this_pc`, 공유본 `missing_records` | 부재를 NOT_RUN 또는 대상 부재로 재분류하지 않음 |
| 일부 범위 | 정의·봉인 scope 자료 | PASS 옆 범위 설명; 새 verdict enum을 만들지 않음 |

`NO_TEST_TARGET`은 독립 판정 enum이 아니다. 현재 A-01~A-03은 처리 범위 `NO_TEST_TARGET`,
공식 판정 `INCONCLUSIVE`, 사유 `NO_TEST_TARGET`, `target_exists=false`다.
어떤 기준의 PASS 수가 0이라는 이유로 ‘대상 기능 없음’을 표시하지 않는다.
대상 존재와 처리 범위가 모순되는 입력은 계약 오류로 식별하며 임의 보정하지 않는다.

## DATA-03 — 현황·기준 카드 집계 (3단계 구현 `workbench.ui.coverage`)

기존 `workbench.treatment_counts`는 실제 구현되어 있으나 0개인 key가 생략될 수 있다.
신규 projection은 항상 세 key를 제공하고 누락 key만 0으로 채운다.

```json
{
  "total": 12,
  "counts": {"EXECUTED": 9, "NOT_RUN": 0, "NO_TEST_TARGET": 3},
  "partial_count": 1,
  "segments": [
    {"treatment": "EXECUTED", "count": 9, "draw": true},
    {"treatment": "NOT_RUN", "count": 0, "draw": false},
    {"treatment": "NO_TEST_TARGET", "count": 3, "draw": true}
  ]
}
```

- `total`은 카탈로그 관리 항목 수다. 비율의 분모도 동일하며 9/12는 75%의 항목에 실행 범위가 있다는 의미다.
- 도넛·범례·접근성 설명은 위 객체 하나에서 생성한다. 0개 segment는 경로를 그리지 않고 범례에는 0개를 유지한다.
- `partial_count`는 추가 예정의 구조화된 **현재 범위** projection으로 일부 실행이 확인된 항목 수다. PASS 수나 주석 문자열 검색으로 계산하지 않는다.
- 기존 `counts`와 `count_members`는 공식 판정 집계로 그대로 둔다. 현재 값은 PASS9, FAIL0, NOT_RUN0,
  INCONCLUSIVE3(그중 NO_TEST_TARGET3)이다. 이 3개를 ‘증빙 부족인 실행 3개’로 표현하지 않는다.
- 28개 Run의 역사적 PASS/FAIL/INCONCLUSIVE는 별도 이력 통계다. 현재 12개 시나리오의 결과 집계에 합산하지 않는다.
- 추가 예정 `groups[].ui.coverage`는 `counts`, `partial_count`, `targeted_progress`를 가진다.
  `targeted_progress`는 대상이 있는 항목에 대해서만 `{executed, targeted}`를 제공한다. 대상이 전부 없는 A 기준은 **null**이다.
  이는 실행 범위 안내이며 검증 완료율·PASS율로 표기하지 않는다. 혼합 기준은 대상 없는 항목 수/사유를 별도로 병기한다.
- 화면 정렬만 N/H/A/E와 ID 숫자순으로 고정한다. 현재 카탈로그 원천의 N/H/E/A 배열과 원본을 재작성하지 않는다.

## DATA-04 — 기본 결과·프로필·전체 이력

현재 `scenario.latest_run`은 `_scenario_runs()`가 모든 기록을 `started_at` 내림차순으로 정렬한 첫 항목이다.
공식 final만의 선택이 아니다. 기존 `result_links`는 최대 5개이고 `previous_runs`에는 전체 발견 기록이 있다.
기존 필드 의미는 유지하되 새 화면에서 `latest_run`을 ‘최신 공식 결과’로 그대로 쓰지 않는다.

추가 예정 `scenario.ui.profile_results[]`:

- 카탈로그의 각 프로필을 정확히 한 번 포함하며 `execution_profile`, `selected_run_id`, `selection_problems[]`, `catalog_role`,
  `latest_temporally_confirmed`를 제공한다. 정상은 문제 배열이 비어 있다.
- 프로필별 후보는 카탈로그 `official_status.records`의 **`role=final` 또는 `role=repeat`**로 한정한다.
  공식 추가 재현도 최신 공식 결과 후보이며 부모·중간 child·임의 로컬 실행으로 승격하지 않는다.
- 후보 중 카탈로그 선언 순서의 마지막 항목을 승인된 **공식 대표**로 선택한다. 현재 E-01/E-02는 추가 재현 repeat가 대표이며
  원래 final도 별도 역할로 유지한다. 이 규칙은 검토한 카탈로그의 명시 순서에 기반하며 파일명·디렉터리 시각을 대신 쓰지 않는다.
- 후보 원본의 `started_at`을 모두 확인할 수 있을 때만 시각 최신 여부를 검증해 ‘가장 최근 공식’이라고 병기한다.
  시각 동률이면 카탈로그의 마지막 후보를 대표로 유지한다. 후보 하나라도 시각 누락·해석 실패 또는 대표보다 최신인 다른 공식 후보가 있으면
  `selection_problems[]`에 `TEMPORAL_ORDER_UNCONFIRMED`를 기록하고 ‘공식 대표 / 최신 시각 확인 불가’로 표시한다.
  시각이 없다고 오래된 기록으로 간주하거나 snapshot 레코드 목록에 없는 started_at을 추정하지 않는다.
- 대표 후보가 **누락·INVALID·읽기 실패·카탈로그와 원본 불일치**면 그 후보 ID와 `selection_problems[]`를 유지한다.
  과거 PASS를 자동으로 골라 성공처럼 대체하지 않는다. 원본이 없어 시각을 확인할 수 없는 후보도 누락 이력에서 숨기지 않는다.
- 최종 후보가 없는 프로필은 `selected_run_id=null`, `selection_problems=[NO_OFFICIAL_RESULT]`다. 기존 카탈로그 판정을 재작성하지 않는다.
- H-03·E-03은 각각 두 프로필의 대표 결과를 나란히 보인다. 기본 상세는 카탈로그 프로필 순서의 첫 프로필이며
  프로필 선택은 페이지 안의 탭·anchor로 제공하고 해당 실행은 기존 `/runs/{run_id}` 링크로 연다.
  별도 profile query를 추가하지 않는다. 서로 다른 프로필을 ‘최근/이전’ 둘로 합치지 않는다.
- `/runs/{run_id}` 직접 접근은 항상 그 Run을 연다. 부모를 열었는데 자동으로 자식 화면으로 바꾸지 않는다.

추가 예정 `scenario.ui.history[]`는 선택 모드의 전체 발견 기록과 문서상 누락 기록을 합친 Run ID별 한 행이다.
`run_id`, `execution_profile`, `raw_execution_profile`, `profile_source`, `catalog_role`, `record_role`, `parent_run_id`,
`started_at`, `present`, `integrity`, `verdict`, `run_state`, `problem`을 제공한다. 없는 값은 null이며 추정 생성하지 않는다.
무결성이 막힌 이력은 verdict=null로 유지하고 오류 기록으로 연다. 카탈로그 밖 공유 이력도 `SHARED_HISTORY`로 보존한다.
누락 N02 `7b59237e-0a96-403a-9add-28b91011e950`는 `present=false`; 상세 링크가 성공하는 원본처럼 만들지 않는다.
history는 확인 가능한 started_at 내림차순·동률 Run ID 사전순으로 표시하고, 시각 미확인 행은 별도 묶음으로 명시한다.
페이지 분할할 수 있지만 총수와 모든 행에 도달하는 경로를 제공한다. `result_links[:5]`를 전체 이력으로 쓰지 않는다.

현재 legacy H-03 원본의 `execution_profile=null`은 기존 API가 `H03_MINIMAL_V1`으로 표시한다.
신규 `raw_execution_profile=null`, `profile_source=LEGACY_H03_COMPATIBILITY`로 이 사실을 구분한다.
이 fallback은 확인된 legacy H-03에만 적용하며 임의의 다른 시나리오 null 프로필을 H-03으로 분류하지 않는다.
11개는 카탈로그의 이름 있는 프로필 수이며 raw null을 12번째 프로필로 세지 않는다. 봉인 `run.json`은 고치지 않는다.

## DATA-05 — 현재 정의와 해당 실행 정의

현재 `profiles[].definition.source`는 `sealed_snapshot` 또는 `scenario_file`, `run_id`로 출처를 표시한다.
실행이 존재하면 최신 VERIFIED 기록의 정의를 택하므로 이것을 무조건 ‘현재 YAML’이라고 표시하지 않는다.
현재 `_definition()`은 `target_access`, `unverified_scope_items`, `limitations`의 구조를 그대로 노출하지 않는다.
`scenario.scope_items`는 **현재 YAML에서 만든 문자열 배열**이며 과거 Run scope의 증명으로 쓰지 않는다.

추가 예정 `scenario.ui.current_definitions[]`는 프로필별 현재 파일의 읽기 projection이다.
`execution_profile`, `source=scenario_file`, `version`, `source_ref`, `sha256`, `definition`, `scope`를 제공한다.
추가 예정 `run.ui.sealed_definition`은 해당 실행의 봉인 snapshot을 읽은 같은 구조에
`source=sealed_snapshot`, `run_id`, `source_ref`, `sha256`을 제공한다. 무결성 차단 시 null이다.
`definition`에는 기존 의도/전제조건/단계/규칙/증빙/복구/제외 범위를 유지하고 `timing_policy`·필요 capability를 추가 표시한다.
원본에 없는 정의 항목은 null/누락으로 남긴다. 현재 정의와 봉인 정의가 같다는 판단은 버전 문자열만이 아니라 원본 해시와 내용을 확인한다.

`scope` 구조는 `{partial, applicable_assertion_ids, target_access, unverified_items, limitations}`다.
`unverified_items`는 `{id,text,follow_up}`, `limitations`는 `{id,text}` 배열이고 각 scope 객체는 출처를 상위 정의에서 상속한다.
`partial`은 N-03의 확정된 일부 실행 규칙과 구조화된 미검증 항목에서만 파생한 **표시 boolean**이며 새로운 판정이 아니다.
다른 시나리오의 일반 AWS/외부모델 제외 범위가 있다는 이유만으로 모두 partial=true로 만들지 않는다.
추가 예정 `workbench.groups[].scenarios[].ui.current_scope`, `report.ui.scenario_scopes[]`의 `{id,current_scope}`에는 현재 범위를,
개별 Run의 `ui.sealed_definition.scope`·비교의 `ui.scopes={parent,child}`에는 각자의 sealed scope를 연결한다.
서로 다른 출처의 텍스트는 라벨과 함께 병기한다.

N-03 필수 보존:

- 현재 실제 범위: N03-A1~A3 PASS, `mvp_treatment=EXECUTED`, target_access API.
- N03-U1 실행 중 정책 교체 주입 / N03-U2 교체 시점 근접 제출 / N03-U3 분석 작업의 정책 귀속.
- 각 항목 후속 조건: WhyYou 시험용 정책 교체 수단과 분석 작업 정책 귀속 저장 필드.
- N03-L1: 이전 정책 식별값은 실제 교체 없이 만든 값.
- 현황·목록·상세·Run·보고서에서 일부 실행을 유지한다. 전체 실행·정책 교체 검증 완료로 바꾸지 않는다.

N-01의 parent PASS(v1)→child PASS(v2)는 ControlProof 측정 보강 이력이다.
WhyYou 수정이나 최초 FAIL을 생성하지 않는다. 측정 버전은 해당 봉인 증빙과 검토된 설명 출처에서 읽으며
`execution_profile=N01_NOTICE_V1`이 같다는 이유로 두 측정 버전을 합치지 않는다.

## DATA-06 — 모드와 공유본 맥락

기존 공통 `data_origin`, `demo`, `shared_snapshot`, `environment_kind`, `aws_deployment_status`, `claim_scope`를 그대로 쓴다.
추가 예정 공통 `ui.context`는 `{mode, read_only, readiness_allowed, memo_allowed}`다. mode는 표시용 `SHARED / LOCAL / DEMO`이며
판정·Run 상태 enum과 무관하다. 기존 라우트/POST 검사를 대신하는 권한 근거로 신뢰하지 않는다.

| 모드 | 원천·상단 표시 | 허용 동작 |
| --- | --- | --- |
| SHARED | ACTUAL + shared_snapshot 있음, ID·KST 검토 시각·누락 기록 | 읽기 전용; 현재 PC 준비 상태/개인 메모를 읽거나 저장하지 않음; POST 차단 유지 |
| LOCAL | ACTUAL + shared_snapshot 없음, 해당 PC의 기록 | 기존 preflight·메모만 명시적 사용자 동작으로 허용; 웹 Run/retest/cleanup 추가 금지 |
| DEMO | DEMO + demo=true, 지속적인 DEMO 표시 | 합성 데이터 검토; 실제 결과/준비·메모와 혼합 금지; 현재 preflight/memo 거부 유지 |

현재 공유 기준은 `shared-actual-20261020-r2`, 검토 시각 `2026-10-20T13:43:59.872762+00:00`
(KST 2026-10-20 22:43:59), 28 Run / 652 파일 / 27 VERIFIED·1 INVALID / 누락 이력1건이다.
이 수는 화면에 고정하지 않고 선택한 검증 snapshot에서 생성한다. 9·0·3은 snapshot 기록 수가 아니라 카탈로그 범위다.
추가 예정 `workbench.ui.record_inventory`는 `{run_count, profile_count, file_count, integrity_counts, missing_count}`다.
공유 모드에서는 검증 snapshot·catalog 프로필을, 로컬에서는 해당 root의 실제 발견 기록을 사용하고 원천 라벨을 병기한다.
로컬 화면에 공유본의 28/652를 로컬 보유 수처럼 표시하지 않는다. 표시 코드 변경 시 새 후보 snapshot 맥락을 검토하며 원본을 재봉인하지 않는다.

## DATA-07 — 결과·증빙·비교·보고서 연결

- 결과는 기존 `review.conditions`의 기대/실제/연결 자료와 원본 `assertions`를 연결한다. 조건별 `rule_status`를 새 판정으로 생성하지 않는다.
- E-01 원본 4규칙·표시 7조건을 구분한다. D1 진단은 주 조건 자료에서 제외하되 전체 증빙 색인에 보존한다.
- `evidence.ref`와 run_id를 키로 사용한다. 원문 경로를 브라우저가 조합하거나 서버 파일 경로를 요청받지 않는다.
- N-01 PNG의 신규 읽기 전용 제공 계약은 별도 이미지 계약을 따른다. 기존 `viewable=false`를 모든 파일에 대해 무조건 true로 바꾸지 않는다.
- compare는 실제 child ID·검증된 parent 관계와 `changed_dimensions`, `parent_unchanged`, `parent_integrity_source`를 쓴다.
  legacy `parent_unchanged=null/NONE_LEGACY`는 실제 변조와 구분한다. PASS나 SHA 변경만으로 제품 수정이라 추론하지 않는다.
- 보고서의 기존 `items_present` 22항목(R1~R13/C1~C9)은 실제 내용과 위치로 추적한다. boolean만 복사해 충족했다고 주장하지 않는다.
  현재 범위/원본 부재·sealed 범위/프로필별 결과·버전·판정/증빙/복구·계보·테스트 대역과 미검증을 함께 보존한다.

## DATA-08 — 오류·출력 경계

없는 시나리오/Run은 기존 NOT_FOUND 응답을 유지한다. 다른 정상 시나리오로 대체하지 않는다.
무결성이 VERIFIED가 아니면 기존 `verdict/assertions/evidence=null`, review 부재 정책을 유지한다.
ABORTED/RESTORE_FAILED의 봉인 판정이 보이더라도 `target_verdict=false`, 안전 배지·표시 우선순위를 유지한다.
catalog 공식 결과와 원본 판정이 다르면 기존 mismatch를 노출하며 둘 중 하나를 성공 쪽으로 선택하지 않는다.

기존 redaction·Jinja autoescape·CSP·Host/CSRF를 유지한다. `ui`의 사람 문구도 같은 출력 경계를 통과한다.
실제 텍스트와 메모를 `innerHTML`에 연결하지 않는다. raw 경로·secret·개인정보를 새 projection으로 우회 노출하지 않는다.
추가 projection 생성 실패는 null과 문제 설명으로 드러내며 성공한 예시 데이터로 fallback하지 않는다.

## DATA-09 — 계약 fixture와 구현 gate

`coverage-cases.json`은 **계약용 합성 입력/기대값**이다. 실제 실행 자료나 현재 엔진 판정이 아니다.
`case_type=aggregate`는 상태 분리·0개·대상 부재·일부 범위, `profile_compatibility`는 legacy null,
`official_selection`은 공식 후보·복수 프로필·부재/오류를 다룬다. JSON의 키는 fixture schema이며 API 신규 필드의 증거가 아니다.
0·1단계는 이 문서와 fixture를 준비하는 범위다. 후속 구현에서 실제 표시 함수를 fixture에 연결하고 계약 시험을 추가한다.
현재 시험을 실행한 것처럼 PASS 처리하거나 제품 코드·verdict enum을 이 단계에서 추가하지 않는다.

구현 전 검토: 기존 API shape 보존, additive `ui`의 출처, 도넛 분모/세 범주, 공식 후보 선택, 모든 이력,
current/sealed scope, shared/local/DEMO, 원본 부재/INVALID·복구 실패, 이미지 계약과의 경계가 서로 일치해야 한다.

## 확인한 소스

- `engine/web/readmodel.py`: `header`, `workbench`, `_row`, `_result_links`, `run`, `evidence`, `_run_block`, `scenario`, `_scenario_profile`, `_scenario_runs`, `compare`, `report`, `_definition`, `scope_item_lines`.
- `engine/web/server.py`, `engine/shared_records.py`, `catalog/mvp-scenarios.yaml`, `scenarios/N-03.yaml`.
- `specs/005-web-workbench-report/contracts/web-read-model.md`, `specs/008-shared-run-records/spec.md`, Spec009 closure.
- `.controlproof/platform-review-20261020/PLATFORM_REVIEW.md`, `FRONTEND_IMPLEMENTATION_PLAN.md` (현재 검수·반영 계획 입력).

## 5단계 추가 투영

기존 `compare`/`report`의 필드·enum·문제 코드·원문 텍스트를 바꾸지 않고 `ui`를 더했다.

- `compare.ui`: scenario_id, comparison_available, relationship_problem, cause(kind/label/text/source),
  assertions(원래 규칙 변화 + description + 양쪽 모든 evidence의 run_id/ref/label/SHA), execution_states,
  measurement_versions와 scopes={parent,child}. scopes 각 값은4단계 sealed_definition 문서 형식이며
  내부 scope와 source/ref/version/SHA/run_id를 함께 가진다. 무결성 불가 쪽은 null이다.
  새로운 관계/안전 문제는 표시 비교를 차단하며 원래 API의 기존 lineage_problem을 덮어쓰지 않는다.
- `report.ui`: 기존 workbench의 정렬된 groups/coverage, scenario_scopes의 현재 정의 출처,
  전체 records/history와 present/integrity/원본 부재, comparisons(실제 child/parent/프로필/primary), inventory,
  reproduction_context(플레이북 D-019 설명·출처). DEMO comparisons/records 링크는 합성 root만 쓴다.
- `records.versions`: VERIFIED 원본만 sealed_bundle 출처의 target/environment/run 버전 필드와
  scenario source/ref/version/SHA, N01 notice_policy를 읽는다. 원본에 없는 환경 문서/버전/프롬프트는 null이다.
  source_refs는 실제 존재하는 봉인 원본 파일 이름만 포함한다. 각 문서에 없는 값은 여전히 null이다.
  무결성 불가/미확보 기록의 versions는 null이다. 모델 고정 이름은 기존 developer에서만 노출한다.
- 준비 HTML view는 현재 프로필 정의/설명·저장 준비와 명령만 제공한다. GET은 archived Run/검증/실행을 읽거나 시작하지 않는다.
  기존 v1 API에 준비 상태를 성공으로 승격하지 않는다. SHARED는 PC 준비/메모를 읽지 않는다.

기존 보고서 API의 other_pc_reproduction/one_screen_notice는 과거 카탈로그 문구로 보존했다.
새 UI는 상위 D-019의 한 건 인정 범위와 브라우저 인쇄/출력 안내를 명확히 제공한다. 새 실행/별도 PDF 서버 기능이 아니다.

## 6단계 출처·오류 표시 보충

legacy2건의 없는 environment.snapshot.json은 report.ui source_refs에서 제외했다. 기존 v1 필드나 원본을 채우지 않는다.
보고서 CP commit은 원래 구조의 commit_sha/dirty로 읽기 쉽게 표시하며 raw API 구조는 유지한다.
HTML 오류는 기존 error payload 위에 선택한 reader.header 맥락을 더해 읽기 모드·DEMO와 복귀를 보존한다.
API/POST JSON 오류는 기존5개 키를 그대로 반환한다. 검증은 test_platform_integration과 stage6-validation을 따른다.
