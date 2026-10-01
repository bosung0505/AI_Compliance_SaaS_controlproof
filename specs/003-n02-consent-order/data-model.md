# Data Model: N-02 동의·AI 처리 순서 검증

Spec 001·002의 `Run`, `TestSubject`, `Observation`, `EvidenceArtifact`, `AssertionResult`, `Judgement`,
`RetestLink`, `TargetSnapshot`, `TargetEnvironmentSnapshot`과 restore lifecycle을 유지한다. 아래 모델은
N-02 profile에 additive하게 추가한다.

## 1. ExecutionProfile

새 enum value를 추가한다.

```text
N02_CONSENT_ORDER_V1
```

profile policy는 다음을 고정한다.

| Field | Value |
|---|---|
| `scenario_id` | `N-02` |
| `schema_version` | `controlproof.scenario.v3` |
| `assertion_ids` | `N02-A1`~`N02-A7` |
| `evidence_ids` | `EV3-01`~`EV3-10` |
| `environment_kind` | `LOCAL_EMULATED` |
| `aws_deployment_status` | `NOT_RUN` |
| `requires_restore` | true |
| `requires_queue_policy_snapshot` | false |
| `bundle_profile_contract` | `controlproof.bundle-profile.spec003.v1` |

## 2. RunSubjectLane

한 Run 안의 독립 합성 subject와 판정 책임을 표현한다.

| Field | Type | Rules |
|---|---|---|
| `lane_id` | enum | 아래 canonical 6개 중 하나 |
| `subject_ref` | string | Run 안에서 unique |
| `invitation_id` | UUID | WhyYou 합성 지원 건 |
| `applicant_id` | UUID | 합성 지원자 |
| `baseline_kind` | enum | `PRISTINE`, `PREREQUISITE_FIXTURE` |
| `fixture_kind` | string/null | fixture lane에 필수 |
| `fixture_digest` | SHA-256/null | fixture의 canonical projection digest |
| `allowed_preexisting_effects` | map | fixture lane에만 허용; count/identity set |
| `probe_overlays` | ordered list | fault lane의 임시 deep-boundary fixture; 기본은 빈 목록 |
| `target_effect_groups` | ordered set | 이 lane에서 증분 판정할 effect group |
| `trace_namespace` | string | `controlproof:{run_id}:{lane_id}` 형식 |
| `seed_correlation_id` | string | teardown과 증적 연결 |

Canonical lane:

```text
PRISTINE_BASELINE
DOCUMENT_BYPASS
RECORDING_BOUNDARY_PROBE
ASSESSMENT_BOUNDARY_PROBE
NORMAL_ORDER
CONSENT_FAULT_RECOVERY
```

### Validation

- `PRISTINE_BASELINE`, `DOCUMENT_BYPASS`, `NORMAL_ORDER`, `CONSENT_FAULT_RECOVERY`는
  `baseline_kind=PRISTINE`이고 fixture field가 null이다.
- recording probe의 fixture는 equipment/strategy만 허용하며 session/chunk/asset은 0건이다.
- assessment probe의 fixture는 completed session/final turns/final video를 허용하되 report, report item,
  projection, report event와 processed marker는 0건이다.
- fixture projection이 digest 또는 allowlist와 다르면 Run을 시작하지 않는다.
- lane 간 invitation/applicant ID 재사용은 금지한다.
- fault lane overlay는 failed-consent zero snapshot 뒤에만 적용하고, 각 path 시도 뒤 제거하며 정상 동의
  복구 전에 빈 목록과 원 seed digest를 회복해야 한다.

## 3. ProtectedProcessingPath

대상 버전에 존재하는 실제 경계와 관찰 가능한 효과를 고정한다.

| Field | Type | Rules |
|---|---|---|
| `path_id` | enum | `DOCUMENT_ANALYSIS`, `RECORDING`, `AI_ASSESSMENT` |
| `entry_boundary` | string | 실제 operation/event/handler 이름 |
| `entry_kind` | enum | `HTTP`, `WEBSOCKET`, `DOMAIN_EVENT` |
| `independent_direct_route` | boolean | 전제 없이 직접 호출 가능한지 |
| `earliest_real_boundary` | string | independent route가 없을 때 필수 |
| `required_fixture_kind` | string/null | deep probe가 필요할 때만 |
| `request_effect_keys` | ordered set | 권한·intent·event 등 |
| `start_effect_keys` | ordered set | handler receipt/state 등 |
| `result_effect_keys` | ordered set | row/object/projection 등 |
| `consent_purpose` | enum | 세 purpose 중 정확히 하나 |
| `contract_version` | string | MVP는 `v1` |
| `source_locator` | map | repo-relative path와 symbol; 절대 경로 금지 |

path는 대상 `TargetSnapshot`과 함께 EV3-01에 저장한다. source locator는 증거 보조 정보이며 실제 Run의
요청·effect observation을 대신하지 않는다.

## 4. ConsentPolicySnapshot

| Field | Type | Rules |
|---|---|---|
| `policy_version` | string | 서버 응답 값 |
| `content_digest` | SHA-256 | 서버 canonical content digest |
| `required_purposes` | ordered set | 정확히 document_analysis, recording, ai_assessment |
| `retention_days` | integer | 1 이상 |
| `received_at` | aware datetime | client 수신 시각 |
| `request_id` | UUID | sanitized correlation |
| `source_ref` | string | HTTP artifact locator |

AI role, notice 원문과 전체 정책 본문은 N-02 bundle에 저장하지 않는다. 화면 표시 품질은 N-01 범위다.

## 5. ConsentStateSnapshot

특정 lane/subject의 allowlist DB projection이다.

| Field | Type | Rules |
|---|---|---|
| `run_id` | UUID | Run 연결 |
| `lane_id` | enum | lane 연결 |
| `subject_ref` | string | subject 연결 |
| `phase` | enum | `BASELINE`, `INJECTED`, `RECOVERED` |
| `step_id` | string | scenario step |
| `attempt` | integer | 1 이상 |
| `invitation_status` | string | 현재 상태 |
| `invitation_row_version` | integer | 0 이상 |
| `consent_record_ids` | ordered UUID set | 현재 subject만 |
| `active_consent_count` | integer | 0 이상 |
| `consent_policy_versions` | ordered string set | PII 없음 |
| `consent_content_digests` | ordered SHA set | PII 없음 |
| `accepted_purpose_sets` | ordered list | canonical purpose set |
| `consented_state_change_ids` | ordered UUID set | state transition identity |
| `consent_completed_event_ids` | ordered UUID set | Outbox identity |
| `trace_ids` | ordered digest set | raw trace 대신 digest 허용 |
| `captured_at` | aware datetime | 수집 시각 |
| `source_status` | enum | `PRESENT`, `ABSENT`, `UNAVAILABLE` |
| `source_error_code` | string/null | UNAVAILABLE에 필수 |
| `state_digest` | SHA-256 | projection canonical digest |

조회 성공+0건은 ABSENT이고 DB 접근 실패는 UNAVAILABLE다.

## 6. ProtectedEffectSnapshot

Spec 002의 `BusinessEffectSnapshot` 패턴을 확장한다.

| Field | Type | Rules |
|---|---|---|
| `effect_group` | enum | `DOCUMENT_ANALYSIS`, `RECORDING`, `AI_ASSESSMENT` |
| `request_ids` | ordered ID set | upload intent/submission/outbox 등 |
| `start_receipt_ids` | ordered ID set | handler/session start receipt |
| `result_ids` | ordered ID set | analysis/strategy/chunk/asset/report/projection |
| `status_projection` | map | allowlist된 status/count만 |
| `fixture_effect_ids` | ordered ID set | fixture lane에서만 |
| `new_effect_ids` | ordered ID set | current minus baseline minus fixture |
| `source_status` | enum | PRESENT/ABSENT/UNAVAILABLE |
| `state_digest` | SHA-256 | 전체 allowlist projection digest |

### Delta rule

```text
new_effect_ids = current_effect_ids - baseline_effect_ids - allowed_fixture_effect_ids
```

baseline/current source 중 하나가 UNAVAILABLE이면 delta를 0으로 추정하지 않는다. fixture effect가
allowlist에 없거나 current에서 사라져도 evidence conflict 후보로 기록한다.

## 7. ProcessingAttemptReceipt

HTTP, WebSocket 또는 domain event 시도를 공통 형식으로 정규화한다.

| Field | Type | Rules |
|---|---|---|
| `attempt_id` | UUID | unique |
| `run_id`, `lane_id`, `subject_ref` | identity | 모두 필수 |
| `path_id` | enum | 처리 종류 |
| `entry_kind` | enum | HTTP/WEBSOCKET/DOMAIN_EVENT |
| `operation_id` | string | OpenAPI operation 또는 event type |
| `request_id` | UUID/string | raw credential 아님 |
| `trace_id_digest` | SHA-256 | raw trace 노출 최소화 |
| `sent_at`, `response_at` | aware datetime | response가 없으면 null 허용 |
| `response_class` | enum | `ACCEPTED`, `DENIED`, `ERROR`, `NO_RESPONSE` |
| `status_code` | integer/null | HTTP에만 |
| `sanitized_reason_code` | string/null | allowlist code |
| `source_ref` | string | artifact locator |

body, cookie, bearer, presigned URL과 raw idempotency key는 저장하지 않는다.

## 8. CausalEvent and CausalEdge

### CausalEvent

| Field | Type | Rules |
|---|---|---|
| `causal_event_id` | UUID | ControlProof identity |
| `kind` | enum | POLICY_RECEIVED, CONSENT_REQUESTED, CONSENT_COMMITTED, PROCESSING_REQUESTED, PROCESSING_STARTED, RESULT_CREATED |
| `run_id`, `lane_id`, `subject_ref` | identity | 필수 |
| `path_id` | enum/null | processing event에 필수 |
| `domain_identity` | map | request/event/aggregate/result ID allowlist |
| `occurred_at` | aware datetime/null | 원본이 제공할 때 |
| `observed_at` | aware datetime | 항상 필수 |
| `source_type`, `source_ref` | string | 원본 연결 |

### CausalEdge

| Field | Type | Rules |
|---|---|---|
| `from_event_id`, `to_event_id` | UUID | 같은 Run/lane/subject |
| `relation` | enum | `PROGRAM_ORDER`, `SAME_TRANSACTION`, `EMITTED`, `HANDLED`, `PRODUCED` |
| `proof_refs` | non-empty artifact/observation refs | 최소 1개 |
| `status` | enum | `PROVEN`, `UNAVAILABLE`, `CONFLICTING` |

N02-A5 PASS에는 policy→consent commit→각 path request→start→result의 적용 가능한 edge가 모두 PROVEN이어야
한다. timestamp는 보조 observation이며 edge를 단독 대체하지 않는다.

## 9. ConsentFaultCondition

기존 `FaultCondition` lifecycle을 재사용하고 다음 N-02 field를 추가한다.

| Field | Type | Rules |
|---|---|---|
| `fault_kind` | const | `consent_after_record_before_state_v1` |
| `fault_variant` | const | `AFTER_CONSENT_RECORD_BEFORE_STATE` |
| `invitation_id`, `applicant_id` | UUID | marker subject와 정확히 일치 |
| `marker_digest` | SHA-256 | raw path 대신 content identity |
| `one_shot` | boolean | true |
| `trigger_receipt_id` | UUID/null | 실제 발동 후 필수 |
| `requested_at`, `expires_at` | datetime | TTL ≤ 600초 |
| `restored_at` | datetime/null | restore 성공 후 필수 |
| `environment_restore_success` | boolean/null | 종료 시 필수 |

Lifecycle:

```text
REQUESTED → APPLIED → TRIGGERED → RESTORING → RESTORED
                                  └────────→ RESTORE_FAILED
```

APPLIED만으로 fault가 실제 발동했다고 판정하지 않는다.

## 10. ConsentFaultReceipt

| Field | Type | Rules |
|---|---|---|
| `schema_version` | const | `controlproof.whyyou-consent-fault-receipt.v1` |
| `receipt_id`, `run_id` | UUID | 필수 |
| `lane_id`, `subject_ref` | identity | fault lane과 일치 |
| `invitation_id`, `applicant_id` | UUID | marker와 일치 |
| `fault_variant` | const | 위와 동일 |
| `boundary` | const | `AFTER_CONSENT_RECORD_BEFORE_INVITATION_STATE` |
| `request_id` | UUID/string | failed HTTP request 연결 |
| `triggered_at` | aware datetime | 필수 |
| `one_shot_consumed` | boolean | true |

receipt 파일은 예외를 발생시키기 전에 flush+fsync돼야 한다.

## 11. RecoveryRecord

| Field | Type | Rules |
|---|---|---|
| `run_id`, `lane_id`, `subject_ref` | identity | fault lane |
| `marker_removed` | boolean | 필수 |
| `consumed_token_removed` | boolean | 필수 |
| `hook_inactive` | boolean | 독립 probe |
| `failed_request_effects_zero` | boolean/null | effect read 성공 시 |
| `normal_retry_succeeded` | boolean/null | restore 뒤 |
| `logical_consent_count` | integer/null | 정상은 1 |
| `consent_completed_event_count` | integer/null | 정상은 1 |
| `processing_order_proven` | boolean/null | A5 graph 재사용 |
| `restore_status` | enum | `SUCCEEDED`, `FAILED`, `UNVERIFIED` |
| `manual_cleanup_required` | boolean | FAILED/UNVERIFIED면 true |

## 12. Assertion and Verdict Rules

| Assertion | Required model facts |
|---|---|
| A1 | pristine ConsentStateSnapshot + three ProtectedEffectSnapshot groups |
| A2 | document attempt + baseline/current delta |
| A3 | recording fixture descriptor + attempt + delta |
| A4 | assessment route-absence capability + fixture descriptor + worker attempt + delta |
| A5 | ConsentPolicySnapshot + committed ConsentStateSnapshot + complete causal graph |
| A6 | fault receipt + failed HTTP attempt + zero partial effects + 같은 subject의 세 path 차단 시도와 overlay cleanup |
| A7 | RecoveryRecord + exactly-one consent set + causal graph |

Aggregation order:

1. 직접 금지 effect가 관찰된 A2~A7은 FAIL이다.
2. 하나 이상의 FAIL이 있으면 전체 FAIL이며 다른 미평가/INCONCLUSIVE assertion을 숨기지 않는다.
3. 직접 FAIL이 없고 필수 source가 UNAVAILABLE 또는 causal edge가 끊기면 INCONCLUSIVE다.
4. 같은 dimension의 원본이 모순되면 EVIDENCE_CONFLICT다.
5. restore가 안전하지 않으면 Run은 `RESTORE_FAILED`, verdict는 INCONCLUSIVE다.
6. A1~A7이 모두 PASS이고 bundle profile verify가 성공할 때만 전체 PASS다.

## 13. Run Validation Refactor

현재 `Run`의 “H03 minimal이 아니면 Spec 002 field 강제” 조건을 profile policy로 교체한다.

```text
profile_policy(profile).validate_run(run)
```

Spec 001/002 policy는 기존 조건을 그대로 보존한다. N-02 policy는 다음을 요구한다.

- environment snapshot digest
- lane manifest digest
- path capability digest
- policy snapshot digest
- `LOCAL_EMULATED`, AWS `NOT_RUN`
- 실제 cloud 미검증 범위
- queue topology digest는 선택이며 N-02 verdict 필수값이 아님

## 14. Data Retention and Redaction

포함 가능:

- UUID, state, event type/version, count, hash, sanitized status/reason, timestamp
- 합성 fixture kind와 digest

포함 금지:

- 지원자 이름·이메일·답변 원문·이력서 내용
- 정책 고지 원문 전체
- cookie, token, DB password, presigned URL, raw idempotency key
- 전체 DB row·전체 로그·모델 prompt와 narrative

모든 artifact는 기존 `EvidenceArtifact`의 relative path, size, MIME, captured time, SHA-256 규칙을 따른다.
