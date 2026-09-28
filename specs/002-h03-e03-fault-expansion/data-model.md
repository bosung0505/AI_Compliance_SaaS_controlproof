# Data Model: H-03·E-03 장애·재시도·DLQ 확장

Spec 001의 `Run`, `TestSubject`, `Observation`, `EvidenceArtifact`, `AssertionResult`, `Judgement`,
`RetestLink`를 유지한다. 아래 모델은 Spec 002에서 additive하게 추가하거나 기존 모델에 선택 필드로
연결한다.

## 1. ScenarioProfile

한 YAML이 어떤 executor와 assertion 집합을 사용하는지 동결한다.

| Field | Type | Rules |
|---|---|---|
| `execution_profile` | enum | `H03_MINIMAL_V1`, `H03_DLQ_V2`, `E03_BEFORE_V2`, `E03_AFTER_V2` |
| `scenario_id` | string | `H-03` 또는 `E-03` |
| `scenario_version` | semver | profile 의미 변경 시 증가 |
| `fault_variant` | enum/null | v2 fault profile은 정확히 하나, v1은 null 허용 |
| `applicable_assertion_ids` | ordered set | profile별 canonical 집합과 정확히 일치 |
| `required_capabilities` | map | capability ID → contract version |
| `required_evidence` | ordered set | profile이 요구하는 EV 또는 EV2 ID |
| `timing_policy` | object | snapshot digest에 포함 |

### Canonical assertion ownership

| Profile | Assertions |
|---|---|
| `H03_MINIMAL_V1` | H03-A1~A6 |
| `H03_DLQ_V2` | H03-A1~A9 |
| `E03_BEFORE_V2` | E03-A1~A4, E03-A7, E03-A8 |
| `E03_AFTER_V2` | E03-A1, E03-A5, E03-A6, E03-A8 |

한 profile에서 비적용 assertion을 PASS나 INCONCLUSIVE로 저장하지 않는다. `show`는 적용 assertion과
다른 변형에서 검증해야 하는 assertion을 구분한다.

## 2. Run additions

기존 `Run`에 다음 선택 필드를 추가한다. v1 bundle에는 없어도 된다.

| Field | Type | Rules |
|---|---|---|
| `execution_profile` | enum/null | Spec 002 Run에는 필수 |
| `fault_variant` | enum/null | H03_DLQ/BEFORE/AFTER 중 profile과 일치 |
| `environment_snapshot_digest` | SHA-256/null | Spec 002 Run에는 필수 |
| `queue_topology_digest` | SHA-256/null | queue를 쓰는 Spec 002 Run에는 필수 |
| `source_event_id` | UUID/null | trigger 뒤 저장, 동일 logical event 연결 |

`Run.state` 전이는 Spec 001과 같다.

```text
PENDING → RUNNING → RESTORING → COMPLETED
                    ├────────→ ABORTED
                    └────────→ RESTORE_FAILED
```

장애가 한 번이라도 적용되면 `RESTORING`을 건너뛸 수 없다.

## 3. FaultVariant

| Value | Boundary | Required proof |
|---|---|---|
| `BEFORE_RESULT_DURABLE` | report side effect 전 | matching marker/trigger receipt, report·projection·processed marker 부재 |
| `AFTER_RESULT_DURABLE_BEFORE_COMPLETION` | DB commit 후 SQS ack 전 | boundary receipt, report·projection·processed marker 존재, ack 미수행, 이후 duplicate-ack |

기존 `FaultCondition`에 `fault_variant`, `boundary_receipt_id`, `one_shot`을 추가한다.

### Fault lifecycle

```text
REQUESTED → APPLIED → EFFECT_OBSERVED → RESTORING → RESTORED
                └────────────────────→ RESTORE_FAILED
```

- BEFORE는 `EFFECT_OBSERVED` 후 반복 attempt와 DLQ 도달을 기다린다.
- AFTER는 첫 boundary receipt 뒤 같은 marker가 handler를 다시 중단시키면 안 된다.

## 4. TargetEnvironmentSnapshot

파일: `environment.snapshot.json`  
Schema: `controlproof.environment-snapshot.v1`

| Field | Type | Rules |
|---|---|---|
| `target_id` | string | 공식 profile은 `whyyou-local` |
| `environment_kind` | enum | 공식 profile은 `LOCAL_EMULATED` |
| `host_os` | string | 비밀값 없는 OS/version |
| `controlproof_commit` | git SHA + dirty | 실행기 identity |
| `whyyou_commit` | git SHA + dirty | target snapshot과 일치 |
| `components` | map | PostgreSQL, LocalStack, Mailpit, API, worker, console의 mode/version |
| `endpoints` | map | scheme/host/port만 저장, credential/query 금지 |
| `model_fixture_id` | string | scenario allowlist와 일치 |
| `model_fixture_digest` | SHA-256 | scenario allowlist와 일치 |
| `external_ai_allowed` | boolean | 반드시 false |
| `aws_deployment_status` | enum | 공식 profile은 `NOT_RUN` |
| `unverified_scope` | set | `AWS_SQS`, `AWS_ECS`, `AWS_IAM`, `AWS_CLOUDWATCH`, `AWS_NETWORK` |
| `captured_at` | UTC datetime | identity digest에서는 제외 |
| `snapshot_digest` | SHA-256 | `captured_at`, 자기 digest 제외 canonical JSON hash |

### Validation

- API·console·PostgreSQL·SQS endpoint는 loopback 또는 명시된 Docker local network여야 한다.
- LocalStack queue를 실제 AWS queue로 표기할 수 없다.
- `external_ai_allowed=false`와 target health의 fixed model/embedder가 일치해야 한다.
- 실제 AWS용 credential 값은 저장하거나 출력하지 않는다.

## 5. QueueTopologySnapshot

파일: `queue-topology.snapshot.json`  
Schema: `controlproof.queue-topology.v1`

| Field | Type | Rules |
|---|---|---|
| `source_queue_name` | string | `iep-reporting` |
| `source_queue_url_digest` | SHA-256 | raw URL 대신 digest 저장 가능 |
| `dead_letter_queue_name` | string | `iep-reporting-dlq` |
| `dead_letter_queue_arn` | sanitized string | LocalStack account/region까지만 |
| `max_receive_count` | integer | 공식 profile은 3 |
| `visibility_timeout_seconds` | integer | 공식 profile은 5 |
| `source_retention_seconds` | integer | 실제 attribute |
| `dlq_retention_seconds` | integer | source보다 길어야 함 |
| `redrive_policy_digest` | SHA-256 | canonical policy hash |
| `captured_at` | UTC datetime | 필수 |
| `snapshot_digest` | SHA-256 | canonical identity hash |

redrive 연결·queue name·공식 timing이 다르면 Run을 만들지 않는다.

## 6. DeliveryAttemptRecord

파일: `delivery-attempts.jsonl`  
Schema: `controlproof.delivery-attempt.v1`

| Field | Type | Rules |
|---|---|---|
| `run_id` | UUID | 필수 |
| `subject_ref` | string | 필수 |
| `source_event_id` | UUID | 원 Outbox event |
| `consumer_name` | string | `reporting-worker` |
| `delivery_attempt` | integer | 1 이상, 같은 event에서 증가 |
| `fault_variant` | enum | Run과 일치 |
| `outcome` | enum | `FAULT_TRIGGERED`, `COMMITTED_ACK_DROPPED`, `DUPLICATE_ACK`, `COMPLETED` |
| `observed_at` | UTC datetime | 필수 |
| `receipt_artifact_id` | UUID | 원본 receipt 연결 |

전달 횟수는 업무 효과 건수가 아니다. 같은 event/version의 여러 attempt를 허용한다.

## 7. TerminalFailureRecord

Schema: `controlproof.terminal-failure.v1`

| Field | Type | Rules |
|---|---|---|
| `route_type` | enum | 공식 target은 `INFRASTRUCTURE_DLQ` |
| `route_locator` | string | `localstack:sqs:iep-reporting-dlq` |
| `source_event_id` | UUID | message body에서 추출 |
| `subject_ref` | string | seed mapping으로 연결 |
| `last_delivery_attempt` | integer | attempt receipt 시계열과 일치 |
| `last_failure_code` | string | 민감정보 없는 안정 code |
| `message_body_digest` | SHA-256 | raw body artifact와 연결 |
| `observed_at` | UTC datetime | 필수 |

DLQ 조회 성공 후 일치 message 0건은 `ABSENT`, 조회 실패는 `UNAVAILABLE`이다.

## 8. FaultBoundaryReceipt

Schema: `controlproof.whyyou-fault-receipt.v2`

| Field | Type | Rules |
|---|---|---|
| `run_id` | UUID | marker와 일치 |
| `session_id` | UUID | subject와 일치 |
| `outbox_event_id` | UUID | trigger와 일치 |
| `delivery_attempt` | integer | 1 이상 |
| `fault_variant` | enum | marker와 일치 |
| `boundary` | enum | `BEFORE_REPORT_SIDE_EFFECT` 또는 `AFTER_DB_COMMIT_BEFORE_SQS_ACK` |
| `triggered_at` | UTC datetime | 필수 |
| `one_shot_consumed` | boolean | AFTER에서 true |

receipt만으로 AFTER 경계를 PASS하지 않는다. DB effect snapshot과 ack/duplicate receipt가 함께 필요하다.

## 9. DecisionPathCapability

| Field | Type | Rules |
|---|---|---|
| `path_id` | enum | `FINAL_DECISION`, `BATCH_MOVE_FINAL_ACCEPT`, `BATCH_MOVE_FINAL_REJECT` |
| `operation_id` | string | OpenAPI operation ID |
| `target_stage_id` | UUID | snapshot된 stage |
| `target_stage_name` | string | `최종합격` 또는 `불합격` |
| `expected_effects` | set | 거부 시 empty, E03 정상 결정 시 decision effect set |
| `source_commit` | git SHA | capability snapshot과 일치 |

H-03은 세 path ID를 모두 실행한다. 두 batch path는 같은 operation이지만 stage 의미가 달라 별도
test case로 저장한다.

## 10. BusinessEffectSnapshot

파일: `effects.jsonl`  
Schema: `controlproof.effect-snapshot.v1`

공통 필드: `run_id`, `subject_ref`, `phase`, `step_id`, `attempt`, `logical_operation_id`,
`source_event_id`, `effect_group`, `state_digest`, `captured_at`,
`source_status(PRESENT|ABSENT|UNAVAILABLE)`, `source_error_code`.

### ReportingEffectSet

| Field | Expected after success |
|---|---|
| `logical_report_ids` | 정확히 1개 |
| `report_session_ids` | 현재 session 하나 |
| `projection_document_ids` | report가 만든 canonical set |
| `projection_source_versions` | report version과 일관 |
| `processed_keys` | 현재 event/version의 key 정확히 1개 |
| `source_outbox_event_ids` | 원 event 정확히 1개 |
| `source_outbox_publish_status` | 기존 published 상태 보존 |

projection document 개수는 report item 개수에 따라 달라질 수 있다. 따라서 고정 숫자가 아니라
중복 ID 없음, 모두 같은 report ID, expected deterministic ID set과의 일치로 판정한다.

### DecisionEffectSet

| Field | Expected after first and replay |
|---|---|
| `stage_assignment_ids` | 현재 invitation의 논리 배정 1개 |
| `stage_id` | 요청한 target stage |
| `invitation_status` | `reviewed` |
| `human_review_ids` | 정확히 1개 |
| `human_review_actor_types` | `COMPANY_USER` |
| `final_decision_audit_ids` | 정확히 1개 |
| `final_decision_request_ids` | 같은 logical decision에 귀속 |
| `completion_outbox_events` | 비적용, 필드 자체를 요구하지 않음 |

## 11. RedriveReceipt

Schema: `controlproof.dlq-redrive-receipt.v1`

| Field | Type | Rules |
|---|---|---|
| `source_event_id` | UUID | TerminalFailureRecord와 일치 |
| `dlq_message_id` | string | 원 DLQ message |
| `republished_message_id` | string/null | send 성공 시 필수 |
| `body_digest` | SHA-256 | send 전후 동일 |
| `send_succeeded` | boolean | 필수 |
| `delete_succeeded` | boolean | 필수 |
| `redriven_at` | UTC datetime | 필수 |

- send 실패 시 delete 금지.
- send 성공·delete 실패는 restore uncertainty이며 후속 장애 Run을 차단한다.
- send/delete 성공 뒤에도 report completion과 DLQ 잔여 여부를 별도로 관찰한다.

## 12. Relationships

```text
ScenarioProfile 1 ── * Run
Run 1 ── 1 TargetSnapshot
Run 1 ── 1 TargetEnvironmentSnapshot
Run 1 ── 1 QueueTopologySnapshot
Run 1 ── 1 TestSubject
Run 1 ── 1 FaultCondition
Run 1 ── * DeliveryAttemptRecord
Run 1 ── 0..1 TerminalFailureRecord
Run 1 ── * BusinessEffectSnapshot
Run 1 ── * EvidenceArtifact
Run 1 ── 1 Judgement
Run 0..1 ── * Run (RetestLink)

OutboxEvent 1 ── * DeliveryAttemptRecord
OutboxEvent 1 ── 0..1 TerminalFailureRecord
OutboxEvent 1 ── 0..1 ProcessedKey
Report 1 ── * ProjectionDocument
LogicalDecision 1 ── 1 StageAssignment
LogicalDecision 1 ── 1 HumanReview
LogicalDecision 1 ── 1 AuditEvent
```

## 13. Conflict and identity rules

- Observation conflict는 같은 Run·subject·phase·step·attempt·key에서 독립 출처가 모순될 때만 성립한다.
- source event identity는 WhyYou `outbox_event_id`와 `event_version`으로 비교한다.
- processed identity는 `(consumer_name,event_id,event_version)`이다.
- report identity는 session과 report ID를 함께 사용한다.
- projection identity는 report ID에 대한 deterministic document ID set이다.
- logical decision identity는 `(invitation_id, Idempotency-Key digest, requested_stage_id)`다.
- 서로 다른 Run의 artifact를 참조할 때는 원 Run ID, relative path와 SHA-256을 모두 보존한다.
