# Spec 005 Implementation Decisions

구현 중 계약·시험·작업 순서를 사실에 맞게 다듬은 결정을 기록한다. 제품 의미나 판정 규칙이 바뀌는 결정은 여기서 하지 않고 보고한다.
형식: 원인 · 결정 · 시험 · 영향.

## ID-005-01 — ABORTED bundle의 무결성 표시 (열림, US2 T035 입력)

- 사실: `cases.json` `aborted`(결함 주입 뒤 관찰 실패, 복구 성공)로 만든 H-03 v1 bundle은 필수 증적 EV-06·EV-07 링크가 없어
  `verify_bundle`(기본, 모든 증적 요구)이 `INVALID`, `require_all_evidence=False`이면 `VERIFIED`다. 명령줄 `verify`는 기본값을 쓰므로
  지금도 이 bundle을 INVALID로 보인다(엔진의 기존 동작, 이번 세션에서 바꾸지 않음).
- 영향: 웹이 기본 verify만 쓰면 중단된 Run이 "무결성 실패(변조)"로 보일 수 있다. 중단으로 증적이 빠진 것과 봉인 뒤 파일이 바뀐 것은 다른
  사실이다(Constitution II).
- 처리: US2(T035) 시험을 쓰기 전에 표시 규칙을 정한다. 후보: 파일 해시·manifest 검증이 통과하고 빠진 것이 증적 링크뿐이면 "무결성 확인됨 +
  누락 증적 목록"으로 보이고 실행 상태 `ABORTED`를 먼저 보인다. 판정 의미에 닿을 수 있어 그 전에 보성 확인을 받는다.

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
