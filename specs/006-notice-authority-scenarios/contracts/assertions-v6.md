# Contract: Spec 006 Assertions and Verdict Rules

공통: PASS·FAIL은 기대·관찰·근거 EV를 가진다. `INCONCLUSIVE`는 D-011 사유 코드를 가진다. 판정에 필요한 원본이 없으면
`INSUFFICIENT_EVIDENCE`, 같은 Run·lane·phase·step·attempt의 같은 사실이 모순되면 `EVIDENCE_CONFLICT`, 접근이 막혀 관찰하지
못하면 `ACCESS_LIMITED`. 시나리오 전체 PASS는 필수 assertion 전부 PASS일 때만이다(spec FR-050). 복구 미확인이면 Run은
`RESTORE_FAILED`, 시나리오 판정 `INCONCLUSIVE`다(FR-052).

## N-01

다섯 항목: `ai_assist`(AI 평가 보조), `human_final`(사람의 최종 결정), `recording_purpose`(녹화·처리 목적),
`retention`(보관기간), `deletion`(삭제 방법). 기대 문구는 서버 정책 값에서 만든다(research R5).

항목 "읽을 수 있게 표시됨" = 아래 넷이 모두 참:

1. `text_present`: 기대 문구와 일치하는 요소가 동의 단계 DOM에 있다.
2. `in_viewport`: 필요한 세로 스크롤 뒤 요소 경계 상자가 viewport 가로 범위 안에 있고 세로로 viewport에 들어온다.
3. `not_occluded`: 요소 중심점의 `elementFromPoint`가 그 요소 또는 자손이다.
4. `no_horizontal_overflow`: 문서와 요소 모두 `scrollWidth <= clientWidth`.

| ID | PASS | FAIL | INCONCLUSIVE |
|---|---|---|---|
| N01-A1 | PC에서 다섯 항목 모두 표시됨, 캡처 있음 | 한 항목이라도 넷 중 하나 거짓 | 동의 단계 도달 실패·측정 오류·캡처 없음 → `INSUFFICIENT_EVIDENCE` |
| N01-A2 | 모바일 390×844에서 같은 조건 | 같음 | 같음 |
| N01-A3 | 화면 값 = 서버 현재 값 = 저장 기록(`policy_version`, `evidence_digest`) | 셋 중 하나라도 다름 | 화면 값·저장 기록을 읽지 못함 → `INSUFFICIENT_EVIDENCE` |

A1과 A2는 서로의 결과를 쓰지 않는다(spec US2 수용 4). 서버 정책 자체를 읽지 못하면 세 assertion 모두 `INSUFFICIENT_EVIDENCE`.

## N-03

| ID | PASS | FAIL | INCONCLUSIVE |
|---|---|---|---|
| N03-A1 | 이전 식별값 제출이 성공 응답 없이 거부되고 `stale`의 동의 기록·초대 상태·상태 이력·outbox가 전후 같음 | 성공 응답, 또는 하나라도 바뀜 | 전후 projection을 못 읽음 |
| N03-A2 | 재조회 값으로 제출이 저장되고 저장 `policy_version`·`evidence_digest`가 재조회 값과 같음 | 저장 실패 또는 값 다름 | 저장 기록을 못 읽음 |
| N03-A3 | `past` 동의 기록이 전후 같음(행 수, 모든 열) | 바뀜 | 전후를 못 읽음 |

N03-U1~U3는 판정하지 않는다. 결과에 미검증 범위로만 나온다.

## H-01

경로 `FD`(최종결정 POST), `BM`(일괄 이동 PATCH 최종합격). 거부 주체 `ANON`(인증 없음), `APPLICANT`(지원자 세션 쿠키),
`FORGED`(유효하지 않은 Bearer).

| ID | PASS | FAIL | INCONCLUSIVE |
|---|---|---|---|
| H01-A1 | 두 경로 모두 정상 회사 사용자 결정이 2xx이고 저장 결정이 관찰됨 | (기준 동작 실패는 FAIL이 아님) | 기준 실패·관찰 불가 → `INSUFFICIENT_EVIDENCE`, 해당 경로의 A2~A4도 `INSUFFICIENT_EVIDENCE` |
| H01-A2 | 경로×주체 6개 시도 모두 2xx 아님 | 하나라도 2xx | 응답 수집 실패 |
| H01-A3 | 6개 시도 전후 `*-denied` projection 같음(아래 대상) | 하나라도 바뀜 | 전후 projection 못 읽음 |
| H01-A4 | 6개 시도 각각 감사 행 존재: 주체 구분 + 시각 + 대상 지원자 + 실패 사유 | 한 시도라도 요건 미충족 | 감사 표 조회 실패 → `INSUFFICIENT_EVIDENCE` |

H01-A3 projection 대상: `invitations`(`status`, `row_version`, `recruiting_stage_id`, `pipeline_row_version`),
`human_reviews`, `invitation_state_history`, `recruiting_stages`(포지션), `command_idempotency`(회사·시도 키).
재전송 방지 행동 관찰(최종결정 경로)은 A3의 보조 관찰이다: 같은 키의 정상 결정이 재생이면 A3 FAIL, 새 생성이면 A3 근거에 더한다,
관찰 실패면 A3에 `INSUFFICIENT_EVIDENCE`를 주지 않고 관찰 실패 사실만 기록한다(DB 비교가 주 근거).

H01-A4 주체 구분 요건(spec FR-025): `ANON` → 익명으로 구분됨, `FORGED` → 인정되지 않은 자격으로 구분됨, `APPLICANT` → 지원자
유형 + 지원자 식별자. 거부 응답 본문은 판정하지 않고 상태 코드 종류만 기록한다.

## H-02

| ID | PASS | FAIL | INCONCLUSIVE |
|---|---|---|---|
| H02-A1 | 어시스턴트 공개 경로 전부가 분류·근거 위치를 가짐, 목록이 라우터 데코레이터 전수와 같음 | (열거 누락은 FAIL이 아님) | 한 경로라도 열거·분류 불가 → `INSUFFICIENT_EVIDENCE` |
| H02-A2 | 작업자 사건 키 전부와 운영 처리기 대응 전부가 분류·근거 위치를 가짐 | — | 같음 |
| H02-A3 | 두 목록 어느 항목도 금지 집합에 도달하지 않음 | 한 항목이라도 도달(도달 경로와 바꿀 수 있는 상태 기록) | 도달 여부를 정할 수 없는 항목이 하나라도 있고 도달 항목은 없음 → `INSUFFICIENT_EVIDENCE` |

금지 집합과 도달 규칙: [h02-write-surface-v1.md](./h02-write-surface-v1.md). Q-P1·Q-P2 답 전에는 이 계약의 H02-A3 판정 규칙이
확정되지 않는다.
