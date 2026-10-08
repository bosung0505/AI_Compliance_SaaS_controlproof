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
