# Spec 005 Implementation Decisions

구현 중 계약·시험·작업 순서를 사실에 맞게 다듬은 결정을 기록한다. 제품 의미나 판정 규칙이 바뀌는 결정은 여기서 하지 않고 보고한다.
형식: 원인 · 결정 · 시험 · 영향.

## ID-005-01 — ABORTED bundle의 무결성 표시 (결정됨 2026-10-09, US2 T035 입력)

- 사실: `cases.json` `aborted`(결함 주입 뒤 관찰 실패, 복구 성공)로 만든 H-03 v1 bundle은 필수 증적 EV-06·EV-07 링크가 없어
  `verify_bundle`(기본, 모든 증적 요구)이 `INVALID`, `require_all_evidence=False`이면 `VERIFIED`다.
- 결정(보성 2026-10-09 "추천안대로" 승인): 실행 상태가 `ABORTED`이고 파일 해시·manifest·봉인 값이 모두 맞으며 문제가 "필수 증적 링크
  누락"뿐이면 웹은 `ABORTED` 상태를 먼저 보이고 "봉인 무결성 확인됨 + 중단으로 빠진 증적 목록"으로 보인다. 그 밖의 경우(`COMPLETED`인데
  증적 누락, 해시 불일치 등)는 무결성 실패로 보인다. 명령줄 `verify` 결과는 바꾸지 않는다.
- 반영: spec.md Clarifications Session 2026-10-09, FR-017·FR-018, tasks.md T035 노트(시험 경우 3개). 구현은 US2(T038)에서 한다.

## ID-005-02 — v1 검사 정규식은 T020 전까지 바꾸지 않는다 (T004·T009)

- 원인: plan R-009(a)는 `USER_PATH_RE`를 고치라고 했지만, 그 정규식은 봉인·verify의 v1 검사(`assert_redacted`)가 쓴다. 지금 바꾸면 FR-036이
  요구한 "강화 전 기존 bundle 검사(T016)·보성 PC 검사(T019)" 전에 v1 의미가 바뀐다.
- 결정: 강화된 정규식은 새 이름(`USER_PATH_RE_V2`)으로 두고 v2 검사(`scan_bytes_strict`)와 출력 경계 경로 정책에만 쓴다. `USER_PATH_RE`(v1)는
  T020에서 봉인 검사를 v2로 바꿀 때 함께 정리한다.
- 영향: 출력(명령줄·웹)은 지금부터 강화 규칙으로 가려지고, 봉인·verify 의미는 T020 전까지 그대로다.

## ID-005-03 — 증적 색인의 참조 표기 (T007·T015)

- 원인: 봉인된 manifest의 참조 형식이 Spec마다 다르다(Spec 001 접두사 없는 artifact ID, Spec 002 `artifact:`·`file:`·`intrinsic:`와 교차 Run 객체,
  Spec 004 `file:`·`intrinsic:`).
- 결정: 색인의 `ref`를 하나로 맞춘다. artifact가 있는 파일은 `artifact:<id>`, 없는 파일은 `file:<경로>`, 봉인 manifest는
  `intrinsic:sealed-manifest`, 교차 Run은 `run:<원 Run ID>/artifact:<id>`(같은 run root의 원 bundle manifest에서 digest가 맞을 때만 해석).
  `scenario.snapshot.yaml`은 `definition` 아래의 `assertions[].required_evidence_ids`를 읽는다. 하나라도 해석되지 않은 참조가 있는 요구는
  `missing_requirement_ids`에 넣는다. bundle은 읽기만 한다.
- 영향: 기존 `evidence_links`는 그대로다(시험으로 고정).

## ID-005-04 — 명령줄 오류 분류의 세부 (T006·T013)

- `CliContractError`가 아닌 일반 `ValueError`·`ValidationError`도 `error_kind=CONTRACT`로 둔다(입력·계약 위반). 처리하지 않던 예외는 지금처럼
  그대로 올라간다(`UNEXPECTED`는 예약만 함; 새 catch-all을 더하면 기존 동작이 바뀜).
- H-03 `cleanup-confirm`은 차단 파일이 있을 때만 안전 확인 실패를 `H03_SAFE_STATE_NOT_CONFIRMED`로 낸다. 차단 파일이 없으면 지금처럼
  `NOT_FOUND`(FileNotFoundError)다.
- `verify` 결과에 `redaction_profile`·`strict_scan_findings` 두 키가 더해진다(키 삭제 없음, 종료 코드 그대로).

## ID-005-05 — T016 검사 범위 (이 PC)

- 실제 bundle이 있는 곳: 저장소 `.controlproof/runs`, `cp-local/archive/spec004-diagnostics`, 그리고 `cp-local/archive`의 Spec 003 T084 zip 2개.
- zip은 원본을 열지 않고 임시 폴더로 풀어 검사했다(zip SHA-256은 검사 전후 같음). `t084-attempt1`·`t084-attempt2` 폴더에는 bundle이 없다
  (receipt·차단 파일만 있음).
- zip 2개의 Run ID는 저장소 `.controlproof/runs`의 두 Run과 같다. 그래서 검사한 bundle 폴더는 8개, 서로 다른 Run은 6개다.

## ID-005-06 — bundle verify 시험의 간헐 실패 (시험만 수정)

- 원인: `tests/unit/test_bundle_verify.py`의 두 시험(`test_malformed_artifact_envelope_is_invalid_even_with_updated_file_hash`,
  `test_artifact_dimensions_must_match_manifest_metadata`)이 manifest의 "첫 artifact"를 골랐다. manifest 파일 목록은 경로순이고 artifact
  경로는 무작위 UUID라, H-03 fixture에서 첫 artifact가 JSON envelope이 아니라 PNG가 되는 경우가 있다(보고: Linux 865b0ed 30회 중 3회,
  4c56d0e 30회 중 1회).
- RED: PNG가 첫 artifact인 bundle을 나올 때까지 만들어 두 시험 함수를 직접 돌렸다 → 2개 모두 실패(AssertionError, JSONDecodeError).
- 수정: 시험이 `mime_type == "application/json"`인 artifact를 명시적으로 고르게 했다(`_json_artifact_record`). 제품 코드는 그대로다. 같은
  패턴을 저장소 시험 전체에서 찾았고 이 두 곳뿐이었다.
- GREEN: 같은 강제 조건에서 2개 모두 통과. `pytest -q tests/unit/test_bundle_verify.py` 30회 반복 → 실패 0회(매회 9 passed, Windows).

## ID-005-07 — US1 워크벤치 표시 세부 (T023·T027·T029~T032)

- 카탈로그 공식 기록: `records[]`의 `role`은 `parent`·`child`·`final`·`repeat`(새 checkout 재현)다. H-03의 Spec 001 기록처럼 시나리오 문서와 다른
  Validation에 있는 기록은 기록마다 `validation_ref`를 둔다. manifest SHA-256은 Validation에 적힌 것만 옮겼다(Spec 001은 bundle digest만,
  E-01 D1 child `ec0c895d…`는 없음).
- 준비 상태 열: `NOT_RUN` 항목은 실행 프로필이 없어 카탈로그 값으로 `RUNNER_NOT_READY`, `NO_TEST_TARGET` 항목은 `NO_TEST_TARGET`을 보인다(승인 목업과
  같음; 확인 시각 없음). 실제 실행 항목은 프로필별 최신 확인 저장본을 읽고, 프로필이 둘인 행(H-03·E-03)은 모든 프로필이 같으면 그 값,
  아니면 카탈로그 순서에서 READY가 아닌 첫 프로필 값을 행 값으로 보이며 프로필별 값은 그 아래에 그대로 보인다. 확인 기록이 없으면 배지 없이
  "확인 기록 없음"이다. 사용법 오류·시간 초과는 준비 상태 값이 아니라 "확인 도구 오류" 배지다.
- 공통 확인 시각은 행 확인 시각 중 가장 늦은 값이고, 분 단위로 다른 행만 자기 시각을 보인다. 여러 프로필 행의 시각은 가장 이른 확인 시각이다.
- 준비 상태 확인 폼은 카탈로그의 7개 프로필 중 하나를 고르고(`scenario_id`·`execution_profile`로 보냄) 끝나면 `return_to`(워크벤치 `/` 또는
  `/scenarios/<ID>`)로 303한다. 서버도 카탈로그 프로필만 받는다(400). DEMO 화면에서는 버튼을 비활성화한다(실제 대상에 확인을 보내지 않음).
  DEMO 준비 상태는 `prepare_web_demo.py`가 DEMO root 옆 `preflight/`에 쓴 합성 기록이다.
- 시나리오 상세(②)·실행 결과(③)·비교·보고서(④) 탭과 "상세"·"보고서 열기"는 해당 사용자 스토리 전까지 비활성 표시다(없는 화면으로 이동하지 않음).
- `/favicon.ico`는 204로 답한다(브라우저 콘솔 404 오류 방지).
- (2026-10-09, US2·US3) 머리글의 주장 범위 문장 뒤 코드 `EXECUTED_SCENARIO_AND_EVIDENCE_ONLY`는 기본 문장에서 빼고 머리글의 "개발자용 정보" 펼치기로 옮겼다(FR-019).
  ③ 결과·④ 보고서 탭과 워크벤치의 결과 링크·"보고서 열기"는 활성화했고, ② 상세와 ④의 재시험 비교는 계속 비활성 표시다.

## ID-005-08 — 출력 경계와 겹친 필드 이름, 카탈로그 문장 잘림, 바꾼 기존 기대값 (US2·US3)

- 필드 이름: 엔진 v1 redaction은 `display_name`·`name` 같은 키의 값을 개인정보로 보고 `[REDACTED]`로 바꾼다. 웹 출력은 모두 이 경계를 거치므로
  계약의 `evidence[].display_name`은 `evidence_name`으로, 워크벤치 `target.name`은 `target.service`로 바꿨다(contracts/web-read-model.md·
  data-model.md 반영). 세 뷰 JSON에 `[REDACTED]`가 없음을 시험으로 고정했다(`tests/contract/test_web_http_us2.py`).
- 카탈로그 잘림(US1에서 생김): YAML 흐름 표기(`{text: …, source: …}`)에서 따옴표 없는 쉼표가 문장을 끊어 일부 설명이 잘려 있었다(20곳). 모든
  `text` 값에 따옴표를 붙이고, 설명 항목이 `text`·`source`(·`status`) 외 키를 갖지 않는지 시험을 더했다(`test_explanation_texts_are_whole_values`).
- 바꾼 기존 기대값 1개(연우 승인 2026-10-09): `tests/contract/test_web_http.py::test_route_table_has_no_run_retest_or_cleanup_start`의 POST 경로 목록을
  `["/preflight"]` → `["/preflight", "/runs/{run_id}/memos"]`(contracts/web-http.md의 메모 경로). Run·재시험·정리 확인 시작 경로가 없다는 검사는 그대로다.
- 실행 결과 화면: 복구 시간·예산 준수는 bundle에 기록된 값(`recovery.json` `restore_timing`)만 보이고, 기록이 없는 형식(H-03 Spec 001·002)은 "시간 기록 없음"이다
  (웹이 계산하지 않음). 기대·관찰 원본 값과 봉인 파일 이름은 "원본 값"·"개발자용 원본 정보" 펼치기에만 둔다. DEMO 기록에는 메모를 받지 않는다.
- 보고서의 고정 문구는 범위표 §2 인용문과 같은 글자(JSON 값)이며, 화면에서는 백틱으로 감싼 `NOT_RUN`·`NO_TEST_TARGET`을 굵은 글자로 보인다.
- 서버는 POST 본문을 응답 전에 먼저 읽는다. 없는 POST 경로에 404를 본문을 읽지 않고 보내면 Windows 클라이언트가 연결 끊김(WinError 10053)을 보는
  간헐 실패가 있었다(`test_web_http.py` 3회 중 1회). 수정 뒤 두 HTTP 시험 파일 10회 반복 실패 0회.
