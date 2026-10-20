# Contract: Spec 009 Assertions and Verdict Rules

공통: PASS·FAIL은 기대·관찰·근거 EV를 가진다. `INCONCLUSIVE`는 D-011 사유 코드를 가진다. 판정에 필요한 원본이 없으면
`INSUFFICIENT_EVIDENCE`, 같은 Run·lane·phase·step·attempt의 같은 사실이 모순되면 `EVIDENCE_CONFLICT`, 접근이 막혀 관찰하지
못하면 `ACCESS_LIMITED`. 시나리오 전체 PASS는 필수 assertion 전부 PASS일 때만이다(spec FR-050). 복구 미확인이면 Run은
`RESTORE_FAILED`, 시나리오 판정 `INCONCLUSIVE`다(FR-052). 전체 판정 순서는 기존 Spec 004·006·007과 같다(복구 실패 → FAIL →
충돌 → 증적 부족).

## N-01

다섯 항목: `ai_assist`(AI 평가 보조), `human_final`(사람의 최종 결정), `recording_purpose`(녹화·처리 목적),
`retention`(보관기간), `deletion`(삭제 방법). 항목마다 기대 문구 조각(fragment) 하나 이상을 서버 정책 값에서 만든다(research R1).

| 항목 | 기대 문구 조각 (서버 정책 값에서) | 화면 요소 |
|---|---|---|
| `ai_assist` | `processing_purposes[ai_assessment].title`, 같은 항목의 `description` | 처리 목적 체크박스 행 |
| `human_final` | `ai_role` 전문 | 정책 영역 첫 문단 |
| `recording_purpose` | `recording_notice` 전문, `processing_purposes[document_analysis]`·`[recording]`·`[ai_assessment]`의 `title` | 정책 영역 둘째 문단, 처리 목적 체크박스 행 셋 |
| `retention` | 라벨 "보관기간", `"{retention_days}일"` | 정책 영역 정의 목록 |
| `deletion` | 라벨 "삭제 방법", `deletion_method` 전문 | 정책 영역 정의 목록 |

조각 "읽을 수 있게 표시됨" = 아래 넷이 모두 참. 항목은 조각 전부가 표시될 때만 표시됨이다.

1. `text_present`: 조각 문구를 포함하는 요소가 동의 단계 DOM에 있다(공백 정규화 뒤 부분 일치).
2. `in_viewport`: 필요한 세로 스크롤 뒤 요소 경계 상자가 viewport 가로 범위 안에 있고 세로로 viewport에 들어온다.
3. `not_occluded`: 요소 중심점의 `elementFromPoint`가 그 요소 또는 자손·조상 라벨이다.
4. `no_horizontal_overflow`: 문서와 요소 모두 `scrollWidth <= clientWidth`.

| ID | PASS | FAIL | INCONCLUSIVE |
|---|---|---|---|
| N01-A1 | PC에서 다섯 항목 모두 표시됨, 캡처 있음 | 한 항목이라도 조각 하나가 넷 중 하나 거짓 | 동의 단계 도달 실패·측정 오류·캡처 없음 → `INSUFFICIENT_EVIDENCE` |
| N01-A2 | 모바일 390×844에서 같은 조건 | 같음 | 같음 |
| N01-A3 | 화면 값 = 서버 현재 값 = 저장 기록(`policy_version`, `evidence_digest`), 두 lane 모두 | 셋 중 하나라도 다름(어느 lane이든) | 화면 값·저장 기록을 읽지 못함 → `INSUFFICIENT_EVIDENCE` |

### 측정 v2 (2026-10-20)

첫 실제 Run 뒤 음성 대조(analysis.md "Run 뒤 음성 대조")에서 v1 네 조건이 `visibility:hidden`, `opacity:0`, 조상 `overflow` 잘림,
`line-clamp`를 잡지 못했다(실행기 결함: 측정 누락). v2에서 조각 "읽을 수 있게 표시됨"은 다음 여섯 조건이 모두 참이다.

1~4. `text_present`, `in_viewport`, `not_occluded`, `no_horizontal_overflow`(v1과 같다. 다만 `not_occluded`는 아래처럼 좁힌다).
5. `style_visible`: 요소와 모든 조상의 계산 스타일에 `display:none`이 없고, 요소 자신의 계산 `visibility`가 `visible`이며, 조상까지
   곱한 `opacity`가 0보다 크다.
6. `not_clipped`: 요소 경계 상자가 `overflow`가 `visible`이 아닌 모든 조상의 안쪽 상자(테두리 제외) 안에 완전히 들어가고(1px
   허용), 요소 자신의 `scrollHeight ≤ clientHeight + 1`·`scrollWidth ≤ clientWidth + 1`이다.
- `not_occluded`(v2): 중심점의 `elementFromPoint`가 대상 자신 또는 자손일 때만 참. 조상은 그것이 `label`이고 대상이 그 안에 있을
  때만 허용한다(체크박스 행).
- 버전 선택: lane 기록의 `measurement_version`이 없거나 1이면 v1 네 조건, 2면 v2 여섯 조건, 그 밖의 값은 `INSUFFICIENT_EVIDENCE`.
  v2 기록에 5·6 측정값이 없어도 `INSUFFICIENT_EVIDENCE`. v1 규칙은 첫 Run(`48a70f5e…`) 봉인 기록을 같은 결과로 다시 판정하기 위해서만
  남긴다. 새 Run은 v2로 측정한다.

A1과 A2는 서로의 결과를 쓰지 않는다(spec US1 수용 4). 서버 정책 자체를 읽지 못하면 세 assertion 모두 `INSUFFICIENT_EVIDENCE`.
A3는 lane마다 세 값을 대조하고 두 lane이 모두 같아야 PASS다. 지원자 앱에 닿지 못하면 Run 전에 `ACCESS_BLOCKED`로 막히며
assertion 판정에 이르지 않는다(FR-004·FR-005).

## N-03

| ID | PASS | FAIL | INCONCLUSIVE |
|---|---|---|---|
| N03-A1 | 이전 식별값 제출이 성공 응답 없이 거부되고 `stale`의 동의 기록·초대 상태·상태 이력·outbox가 전후 같음 | 성공 응답, 또는 하나라도 바뀜 | 전후 projection을 못 읽음 → `INSUFFICIENT_EVIDENCE` |
| N03-A2 | 재조회 값으로 제출이 저장되고 저장 `policy_version`·`evidence_digest`가 재조회 값과 같음 | 저장 실패 또는 값 다름 | 저장 기록을 못 읽음 → `INSUFFICIENT_EVIDENCE` |
| N03-A3 | `past` 동의 기록이 전후 같음(행 수, 모든 열) | 바뀜 | 전후를 못 읽음 → `INSUFFICIENT_EVIDENCE` |

N03-A1의 "거부"는 2xx가 아닌 응답이다. 상태 코드 종류(422 등)는 기록만 하고 판정 조건으로 고정하지 않는다. 이전 식별값은 서버
현재 값과 버전·해시가 둘 다 달라야 하며(시드 검증), 다르지 않으면 실행기 결함으로 Run을 중단한다.
N03-U1~U3는 판정하지 않는다. 결과에 미검증 범위로만 나온다. N03-L1(이전 식별값은 실제 교체 없이 만든 값)은 결과 한계다.
