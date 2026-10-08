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
