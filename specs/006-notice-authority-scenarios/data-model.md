# Data Model: Spec 006

ControlProof 쪽 모델만 정의한다. WhyYou 표는 읽기 대상이며 바꾸지 않는다(research R1~R6).

## 공통 (기존 재사용)

`Run`, `ScenarioProfile`, `ScenarioReadiness`, `AssertionResult`, `Judgement`, `RetestLink`, `TargetSnapshot`,
`TargetEnvironmentSnapshot` — `engine/models.py`. 상태 값은 Constitution 그대로다.

## 새 값·필드

| 이름 | 위치 | 내용 |
|---|---|---|
| `ExecutionProfile` 4값 | `engine/models.py` | `N01_NOTICE_V1`, `N03_STALE_CONSENT_V1`, `H01_DECISION_AUTHORITY_V1`, `H02_WRITE_SURFACE_V1` |
| `SPEC006_PROFILES` | `engine/models.py` | 위 네 값의 frozenset |
| `TargetAccessKind` | `engine/models.py` | `SCREEN`, `API`, `SOURCE` |
| `ScenarioDefinition.target_access` | `engine/scenario.py` | `tuple[TargetAccessKind, ...]`, v5 필수 |
| `ScenarioDefinition.unverified_scope_items`, `limitations` | `engine/scenario.py` | `ScopeItem{id, text, follow_up?}` 목록 |
| `RestorePolicy.kind = NONE_STATIC` | `engine/scenario.py` | H-02 전용 |

## N-01

- `NoticeItemId`: `ai_assist`, `human_final`, `recording_purpose`, `retention`, `deletion`.
- `ViewportSpec{lane, width, height}`: `pc` 1440×900, `mobile` 390×844.
- `NoticeItemMeasurement{item_id, expected_text_digest, text_present, bbox, viewport, in_viewport, center_hit, not_occluded,
  doc_scroll_width, doc_client_width, el_scroll_width, el_client_width, no_horizontal_overflow, operations[]}`.
- `ScreenObservation{lane, viewport, step_reached, capture_ref, items[5], token_absent_in_dom, observed_at}`.
- `PolicyIdentifierTriple{screen{version, digest}, server{version, digest}, stored{policy_version, evidence_digest}, consented_at,
  subject_ref}`.

규칙: `items`는 다섯 항목 정확히 한 번씩. `step_reached != consent`이면 측정 없음과 함께 A1/A2 `INSUFFICIENT_EVIDENCE`.

## N-03

- `StaleConsentAttempt{subject_ref, submitted{version, digest}, current{version, digest}, response_status, adapter_code}`.
- `ConsentProjection{consent_records[], invitation{status, row_version}, state_history[], outbox_events[]}` — 기존
  `ConsentStateSnapshot` 재사용.
- `LatestConsentCommit{reread{version, digest}, stored{policy_version, evidence_digest}, response_status}`.

규칙: `submitted`는 `current`와 버전·해시 둘 다 달라야 한다(시드 검증).

## H-01

- `DecisionPath`: `FD`(=`DecisionPathId.FINAL_DECISION`), `BM`(=`BATCH_MOVE_FINAL_ACCEPT`).
- `DeniedPrincipal`: `ANON`, `APPLICANT`, `FORGED`.
- `PrincipalCredential{kind, raw(메모리 전용, repr 숨김), fingerprint(SHA-256 앞 12자)}`.
- `DecisionAttempt{path, principal, lane, idempotency_key_fingerprint?, request_id, trace_id, started_at, finished_at,
  response_status}`.
- `DecisionProjection{invitation{status, row_version, recruiting_stage_id, pipeline_row_version}, human_reviews[],
  state_history[], recruiting_stages[], command_idempotency[]}`.
- `AuditRow{audit_event_id, actor_type, actor_id, action, resource_type, resource_id, result, occurred_at, request_id, trace_id,
  metadata}` 와 `AuditRequirement{attempt_ref, subject_ok, time_ok, target_ok, reason_ok, matched_rows[]}`.
- `IdempotencyProbe{path: FD, key_fingerprint, response_status, outcome: CREATED|REPLAYED|FAILED}`.

규칙: 시도 6개(경로 2 × 주체 3). `APPLICANT` 자격은 Run 소유 lane의 세션이다.

## H-02

- `SurfaceItem{kind: assistant_route|worker_event|worker_handler, key, location, classification, mutable_state[],
  reach_paths[][], unresolved[], held_capabilities[]}`.
- `SurfaceScan{commit, rule_version, depth_limit, forbidden[], items[]}`.

규칙: `classification`은 `READ_ONLY|WRITES|NO_HANDLER|UNRESOLVED`. `WRITES`는 `reach_paths` 1개 이상.

## 상태 전이

Run 상태 전이는 기존 `engine/lifecycle.py` 그대로다. H-02는 `RUNNING → COMPLETED`(복구 단계 없음), 나머지는
`RUNNING → RESTORING → COMPLETED | RESTORE_FAILED`.
