# SC-008 비작성자 검토 체크리스트

## 목적과 자격

구현·bundle 생성·정답표 작성에 참여하지 않은 팀원 1명이 수행한다. 검토자는 코드, 원본 DB,
`judgement.json` 직접 열람 없이 `controlproof show <RUN_ID>` 출력만 사용한다.

## 시험 자료와 정답표

운영자는 합성 PASS, FAIL, INCONCLUSIVE bundle을 무작위 순서로 제공하고 아래 정답표는 검토가
끝날 때까지 가린다.

| case | verdict | 핵심 이유 | 실패/판정 불가 assertion | 환경 복구 |
|---|---|---|---|---|
| PASS | PASS | 결정 안전성과 환경 복구 확인 | 없음 | SUCCEEDED |
| FAIL | FAIL | 화면이 실패/지연을 명확히 표시하지 않음 | H03-A2 실패 | SUCCEEDED |
| INCONCLUSIVE | INCONCLUSIVE | 장애 발동 또는 안전 복구 증적 부족 | H03-A1 또는 H03-A6 판정 불가 | fixture에 표시된 값 |

## 각 case에서 답할 다섯 항목

1. 최종 verdict는 무엇인가?
2. 핵심 이유 한 문장은 무엇인가?
3. 실패 또는 판정 불가 assertion ID는 무엇인가?
4. 그 assertion의 대표 증적 상대 경로 하나와 SHA-256은 무엇인가?
5. 환경 복구 상태와 아직 검증하지 않은 범위 하나는 무엇인가?

## 시간과 합격 경계

- 운영자가 Run ID를 전달하는 순간 타이머를 시작한다.
- 다섯 답을 모두 말한 순간 종료한다.
- case당 `duration_seconds <= 120`이고 다섯 답이 모두 정답이어야 해당 case PASS다.
- 세 case가 모두 PASS여야 SC-008 PASS다. `120.001초`는 FAIL이다.
- 도중에 정답표·코드·원본 artifact를 열면 해당 case를 무효 처리하고 새 검토자로 다시 한다.

## 결과 기록표

| reviewer_ref | case | started_at | ended_at | duration_seconds | verdict 답 | 이유 답 | assertion 답 | evidence 답 | restore/scope 답 | PASS/FAIL |
|---|---|---|---|---:|---|---|---|---|---|---|
| 미실행 | PASS |  |  |  |  |  |  |  |  |  |
| 미실행 | FAIL |  |  |  |  |  |  |  |  |  |
| 미실행 | INCONCLUSIVE |  |  |  |  |  |  |  |  |  |
