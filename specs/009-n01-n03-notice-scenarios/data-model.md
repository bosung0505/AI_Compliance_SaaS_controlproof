# Data Model: Spec 009

ControlProof 쪽 모델만 정의한다. WhyYou 표는 읽기 대상이며 바꾸지 않는다(research R1·R2).

## 공통 (기존 재사용)

`Run`, `ScenarioProfile`, `ScenarioReadiness`, `AssertionResult`, `Judgement`, `RetestLink`, `TargetSnapshot`,
`TargetEnvironmentSnapshot` — `engine/models.py`. 상태 값은 Constitution 그대로다. 프로필 등록·Run 검증·bundle 계약의 확장
지점은 보성이 H-01·H-02에서 쓴 것과 같다(plan.md "Registration map").

## 새 값·필드

| 이름 | 위치 | 내용 |
|---|---|---|
| `ExecutionProfile` 2값 | `engine/models.py` | `N01_NOTICE_V1`, `N03_STALE_CONSENT_V1` |
| `SPEC009_PROFILES` | `engine/models.py` | 위 두 값의 frozenset |
| `TargetAccessKind` | `engine/models.py` | `SCREEN`, `API`, `SOURCE` (값·표시 문구는 contracts/scenario-profile-v9.md) |
| `ScenarioDefinition.target_access` | `engine/scenario.py` | `tuple[TargetAccessKind, ...]`, v9 필수 |
| `ScenarioDefinition.unverified_scope_items`, `limitations` | `engine/scenario.py` | `ScopeItem{id, text, follow_up?}` 목록, v9 선택 |

## N-01

- `NoticeItemId`: `ai_assist`, `human_final`, `recording_purpose`, `retention`, `deletion`.
- `ViewportSpec{lane, width, height}`: `pc` 1440×900, `mobile` 390×844.
- `NoticeFragmentMeasurement{fragment_id, expected_text_digest, text_present, bbox, viewport, in_viewport, center_hit,
  not_occluded, doc_scroll_width, doc_client_width, el_scroll_width, el_client_width, no_horizontal_overflow, operations[]}`.
  - 측정 v2(2026-10-20, 코드 `N01Fragment`)에서 더한 필드: `style_visible`, `not_clipped`, `clip_ancestor`(잘림을 만든 조상의
    태그·클래스 요약 또는 null), `computed_opacity`(조상 누적), `computed_visibility`(요소 자신). v1 기록에는 없거나 null이다.
- `NoticeItemMeasurement{item_id, fragments[1..]}` — 항목은 조각 전부가 표시될 때만 표시됨.
- lane 기록(코드 `N01LaneRecord`, `n01-measurements.json`)의 `measurement_version`: 없거나 1이면 v1, 2면 v2. 그 밖의 값은 판정 불가.
- `ScreenObservation{lane, viewport, step_reached, capture_ref, items[5], token_absent_in_dom, observed_at}`.
- `PolicyIdentifierTriple{lane, screen{version, digest}, server{version, digest}, stored{policy_version, evidence_digest},
  consented_at, subject_ref}`.

규칙: `items`는 다섯 항목 정확히 한 번씩. `step_reached != consent`이면 측정 없음과 함께 A1/A2 `INSUFFICIENT_EVIDENCE`.
`expected_text_digest`는 조각 문구의 SHA-256이며 문구 원문은 서버 정책 값이라 증적에 그대로 둔다(개인정보 아님).

## N-03

- `StaleConsentAttempt{subject_ref, submitted{version, digest}, current{version, digest}, response_status, adapter_code}`.
- `ConsentProjection{consent_records[], invitation{status, row_version}, state_history[], outbox_events[]}` — 기존
  `ConsentStateSnapshot` 재사용.
- `LatestConsentCommit{reread{version, digest}, stored{policy_version, evidence_digest}, response_status}`.

규칙: `submitted`는 `current`와 버전·해시 둘 다 달라야 한다(시드 검증, 어긋나면 실행기 결함으로 중단).

## 상태 전이

Run 상태 전이는 기존 `engine/lifecycle.py` 그대로다. 두 프로필 모두 `RUNNING → RESTORING → COMPLETED | RESTORE_FAILED`.
