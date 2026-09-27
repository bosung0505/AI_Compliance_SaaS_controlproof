# 결과 검토 정책과 웹 UX 검토 이관 기록

## 현재 결정

Spec 001의 CLI는 개발·검증용 인터페이스이므로 비작성자 1명이 PASS·FAIL·INCONCLUSIVE
세 건을 각각 120초 안에 읽는 시험을 완료 gate로 사용하지 않는다. 실제로 측정하지 않은 시간을
통과한 것으로 가정하지도 않는다.

대신 Spec 001에서는 canonical 세 verdict의 `controlproof show --json` projection이 다음 필드를
빠짐없이 제공하는지 자동 계약·통합 시험으로 검증한다.

1. 최종 verdict와 핵심 이유
2. 실패·판정 불가 assertion ID
3. assertion별 증적 상대 경로와 SHA-256
4. 환경 복구와 리포트 처리 복구 상태
5. findings, 누락 증적과 미검증 범위
6. 구현 상태와 WhyYou 판정의 분리

관련 자동 검증은 `tests/contract/test_cli_review.py`,
`tests/integration/test_h03_review_traceability.py`,
`tests/integration/test_sc008_review_package.py`에서 수행한다.

## 이관 이유

- CLI는 최종 고객이 사용할 결과 화면이 아니다.
- 정해진 필드의 존재와 연결은 사람의 눈보다 자동 시험이 정확하다.
- CLI 읽기 시간은 웹 화면의 정보 구조, 시각적 우선순위와 탐색성을 대표하지 않는다.
- 사람 검토는 실제 고객용 웹 결과 화면이 생긴 뒤 수행해야 제품 의사결정에 유효하다.

## 합성 검토 package의 지위

`python -m scripts.prepare_sc008_review`은 PASS·FAIL·INCONCLUSIVE bundle과 `show` projection을
개발자가 확인하기 위한 선택적 데모 도구로 유지한다. 이 package의 실행이나 사람 시간 측정은
Spec 001 완료 조건이 아니다.

## 후속 웹 결과 화면에서 검토할 내용

웹 결과 화면을 다루는 후속 Spec은 최소한 다음 사용성 과업을 별도로 정의한다.

1. 대상 사용자 역할을 채용 담당자·검증 담당자·감사 검토자 중에서 명시한다.
2. 실제 웹 화면에서 verdict, 핵심 이유, 실패 assertion, 대표 증적, 복구 상태와 미검증 범위를
   찾게 한다.
3. 완료 시간뿐 아니라 오답, 클릭 경로, 해석 오류와 추가 설명 필요 여부를 기록한다.
4. 화면이 만들어진 뒤 난이도를 보고 합격 시간과 표본 수를 결정한다. 기존 120초를 근거 없이
   그대로 승계하지 않는다.
5. 검토 결과는 해당 웹 UX Spec의 validation 문서에 기록한다.

## 결정 기록

- 결정일: 2026-09-27
- 변경 전: CLI 비작성자 1명, 세 verdict, 건별 120초 실측을 Spec 001 완료 gate로 사용
- 변경 후: CLI projection은 자동 검증하고 사람 사용성 시험은 웹 결과 화면 구현 후 수행
- 승인: 제품 책임자 요청
