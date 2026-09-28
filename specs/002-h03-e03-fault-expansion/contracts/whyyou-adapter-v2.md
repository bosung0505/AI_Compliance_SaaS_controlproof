# Contract: WhyYou Adapter v2 for H-03·E-03

**Target**: WhyYou local/test personal branch only  
**Adapter ID**: `whyyou-local-v2`  
**Base contract**: [Spec 001 WhyYou adapter](../../001-execution-evidence-h03/contracts/whyyou-adapter.md)

## Boundary

adapter는 WhyYou HTTP, company-console, PostgreSQL과 LocalStack SQS를 raw fact로 정규화한다.
adapter가 H-03/E-03 PASS·FAIL을 결정하지 않는다. 전체 DB dump, worker 전체 로그, token과 PII를
반환하지 않는다.

## Required capabilities

| Capability | Contract | Current target contact |
|---|---|---|
| `target.environment.read` | v1 | local URLs, component versions, model health |
| `messaging.reporting.topology.read` | v1 | LocalStack GetQueueAttributes |
| `messaging.reporting.attempts.read` | v1 | correlated fault receipts |
| `messaging.reporting.dlq.read` | v1 | `iep-reporting-dlq` ReceiveMessage |
| `messaging.reporting.dlq.redrive` | v1 | DLQ send-to-source then delete |
| `reporting.fault.before.inject` | v1 | pre-side-effect marker |
| `reporting.fault.after_commit.inject` | v1 | post-commit/pre-ack one-shot marker |
| `reporting.fault.boundary.read` | v1 | receipt + independent DB projection |
| `reporting.duplicate_ack.read` | v1 | worker receipt/metric for processed short circuit |
| `reporting.effects.read` | v1 | report, assistant docs, processed message, Outbox projection |
| `hiring.decision_paths.read` | v1 | OpenAPI operations + final stage snapshot |
| `hiring.decision_path.attempt` | v1 | normal final decision and batch move |
| `hiring.final_decision.replay` | v1 | same Idempotency-Key twice |
| `hiring.decision_effects.read` | v1 | stage, invitation, HumanReview, audit projection |

Spec 001 capabilities도 해당 profile에서 계속 요구한다. capability 누락은 target 결함이 아니라
`RUNNER_NOT_READY`이며 Run을 만들지 않는다.

## Configuration

| Name | Meaning | Storage rule |
|---|---|---|
| `CONTROLPROOF_TARGET_ID` | `whyyou-local` | plain |
| `WHYYOU_BASE_URL` | loopback API | sanitized URL only |
| `WHYYOU_CONSOLE_URL` | loopback console | sanitized URL only |
| `WHYYOU_DATABASE_URL` | local PostgreSQL | never persist credential |
| `WHYYOU_REPO_PATH` | source checkout | store commit, not absolute user path |
| `WHYYOU_AWS_ENDPOINT_URL` | LocalStack `http://localhost:4566` | sanitized URL |
| `WHYYOU_AWS_REGION` | LocalStack region | plain |
| `WHYYOU_REPORTING_QUEUE_NAME` | `iep-reporting` | plain |
| `WHYYOU_REPORTING_DLQ_NAME` | `iep-reporting-dlq` | plain |
| `CONTROLPROOF_FAULT_ROOT` | shared marker/receipt root | relative locator only |
| `CONTROLPROOF_MODEL_FIXTURE_ID` | fixed model fixture | ID + digest |

AWS access key/secret, bearer, cookies와 DB password는 artifact·exception detail·CLI JSON에 출력하지 않는다.

## Environment guard

READY 전에 다음을 모두 확인한다.

1. target ID가 `whyyou-local`이다.
2. API와 console host가 loopback이다.
3. PostgreSQL endpoint가 loopback 또는 허용된 local container network다.
4. SQS endpoint가 LocalStack loopback이고 queue ARN이 실제 AWS account/resource로 보이지 않는다.
5. target health가 local/test profile, fault hook enabled, fixed model/embedder enabled를 반환한다.
6. fixture ID/digest가 scenario allowlist와 일치한다.
7. source queue와 DLQ의 redrive policy가 서로 연결되고 max receive/visibility가 profile과 일치한다.
8. WhyYou source checkout이 clean하며 `main` branch가 아닌 개인 검증 브랜치다.

8번은 실제 target 변경을 포함하는 Run의 안전 gate다. read-only baseline 검사는 branch 이름을 기록하되
dirty checkout이면 Run을 생성하지 않는다.

## Fault marker

경로는 기존 `reporting/{interview_session_id}.json`을 유지한다.

```json
{
  "schema_version": "controlproof.whyyou-fault.v1",
  "run_id": "uuid",
  "interview_session_id": "uuid",
  "fault_type": "reporting_after_commit_drop_ack_v1",
  "issued_at": "2026-09-28T00:00:00Z",
  "expires_at": "2026-09-28T00:10:00Z",
  "one_shot": true
}
```

Allowed `fault_type`:

- 기존 `reporting_handler_timeout_v1` → `BEFORE_RESULT_DURABLE`
- 신규 `reporting_after_commit_drop_ack_v1` → `AFTER_RESULT_DURABLE_BEFORE_COMPLETION`

production/staging에서 test controls가 enabled면 startup 실패다. UUID/schema/TTL/fault type이 틀린
marker는 적용하지 않고 sanitized warning만 남긴다.

## BEFORE boundary

`ReportRequestedEventHandler`의 report 조회·쓰기·model 호출 전에 marker를 확인한다. 일치하면 receipt를
fsync하고 TimeoutError를 발생시킨다. worker의 기존 rollback+retry path를 사용한다.

Receipt 최소 필드:

```json
{
  "schema_version": "controlproof.whyyou-fault-receipt.v2",
  "run_id": "uuid",
  "session_id": "uuid",
  "outbox_event_id": "uuid",
  "delivery_attempt": 2,
  "fault_variant": "BEFORE_RESULT_DURABLE",
  "boundary": "BEFORE_REPORT_SIDE_EFFECT",
  "triggered_at": "2026-09-28T00:00:15Z",
  "one_shot_consumed": false
}
```

## AFTER commit/pre-ack boundary

`MessageConsumer.consume_once`의 순서를 다음처럼 유지한다.

```text
handler
→ ProcessedMessage record
→ transaction commit
→ optional local/test after-commit hook
→ SQS acknowledge
```

hook이 일치하면 boundary receipt를 fsync하고 현재 delivery의 acknowledge를 한 번 생략한다. handler
transaction을 rollback하거나 queue `retry()`를 호출하지 않는다. hook은 해당 run/session/event에서
한 번만 발동해야 한다.

두 번째 delivery는 기존 `_processed.contains(...)` 분기에서 handler를 호출하지 않고 acknowledge한다.
WhyYou는 이때 다음 sanitized receipt 또는 동등한 관찰 신호를 남긴다.

```json
{
  "event": "CONTROLPROOF_DUPLICATE_ACK",
  "run_id": "uuid",
  "session_id": "uuid",
  "outbox_event_id": "uuid",
  "delivery_attempt": 2,
  "consumer_name": "reporting-worker",
  "observed_at": "2026-09-28T00:00:05Z"
}
```

## Queue topology read

source queue에서 다음 attribute를 읽는다.

- `QueueArn`
- `VisibilityTimeout`
- `MessageRetentionPeriod`
- `RedrivePolicy`
- `ApproximateNumberOfMessages`
- `ApproximateNumberOfMessagesNotVisible`

DLQ에서는 ARN, retention과 depth를 읽는다. raw queue URL과 credential은 저장하지 않는다.

## Terminal DLQ read

DLQ receive는 다음 조건을 만족하는 message만 현재 Run의 실패로 선택한다.

- body의 domain `outbox_event_id`가 trigger 결과와 일치
- event type이 `report.generation_requested`
- payload session ID가 subject와 일치
- attempt receipt의 마지막 event와 일치

다른 message는 변경하거나 현재 Run의 증적으로 사용하지 않는다. 조회 성공+일치 없음은 ABSENT,
LocalStack/API 오류는 UNAVAILABLE이다.

## Safe redrive

책임은 두 계층으로 나눈다. queue adapter는 일치 message 조회와 단일 message의
send-to-source → receipt 반환 → DLQ delete만 수행한다. 공통 `ExecutionSession`은 marker 해제와 worker
health를 선행 확인하고 adapter를 호출하며, receipt 영속화·restore 상태 전이·복구 effect polling을
소유한다. executor와 다른 adapter가 queue mutation을 재구현해서는 안 된다.

1. marker 비활성과 worker health를 확인한다.
2. DLQ message 원본 body·message attributes와 SHA-256을 artifact로 저장한다.
3. 같은 body·attributes를 `iep-reporting`에 send한다.
4. send response와 republished message ID를 저장한다.
5. send 성공일 때만 원 DLQ receipt handle을 delete한다.
6. source event ID의 report 처리 결과를 polling한다.
7. DLQ 잔여와 target safe state를 다시 확인한다.

send 성공·delete 실패 또는 결과 조회 불가는 성공으로 추정하지 않는다. restore uncertainty로 기록하고
후속 장애 Run을 차단한다.

## Decision paths

아래 표는 **operation capability 2개와 canonical path ID 3개**를 나타낸다. batch의 두 path는 같은
operation을 공유하지만 목표 단계와 업무 의미가 달라 독립 case로 실행한다.

| Path ID | Operation | Request |
|---|---|---|
| `FINAL_DECISION` | `recordHumanFinalDecision` | stage ID, expected pipeline version, Idempotency-Key |
| `BATCH_MOVE_FINAL_ACCEPT` | `moveApplicantsToRecruitingStage` | target=`최종합격`, one applicant/version |
| `BATCH_MOVE_FINAL_REJECT` | `moveApplicantsToRecruitingStage` | target=`불합격`, one applicant/version |

H-03 adapter는 path 호출 전후 같은 state/effect projection을 수집한다. HTTP 거부만으로 부분 변경 0건을
추정하지 않는다.

E03-A7은 `FINAL_DECISION`만 호출한다. 최초·재전송 요청의 sanitized body와
`Idempotency-Key` SHA-256을 저장하고 raw key는 저장하지 않는다.

## Reporting effect projection

allowlist query는 현재 company/session/event에 한정해 다음만 반환한다.

```json
{
  "report_ids": ["uuid"],
  "projection_documents": [
    {"document_id": "uuid", "report_id": "uuid", "source_version": "string"}
  ],
  "processed_keys": [
    {"consumer_name": "reporting-worker", "event_id": "uuid", "event_version": 1}
  ],
  "source_outbox": {
    "event_id": "uuid",
    "event_type": "report.generation_requested",
    "publish_status": "published"
  }
}
```

조회 성공+빈 배열과 query 실패를 구분한다.

## Decision effect projection

```json
{
  "invitation_id": "uuid",
  "stage_id": "uuid-or-null",
  "pipeline_row_version": 2,
  "invitation_status": "reviewed",
  "human_reviews": [
    {"human_review_id": "uuid", "actor_type": "COMPANY_USER", "stage_id": "uuid"}
  ],
  "audit_events": [
    {"audit_event_id": "uuid", "action": "final_decision.create", "request_id": "uuid"}
  ]
}
```

display name, email, answer text, report narrative, model prompt와 raw score는 수집하지 않는다.

## Error mapping

| Condition | Mapping |
|---|---|
| non-local endpoint or external AI fallback possible | `RUNNER_NOT_READY` |
| LocalStack credential/endpoint inaccessible before Run | `ACCESS_BLOCKED` |
| queue/DLQ route absent | target exists but runner cannot execute: `RUNNER_NOT_READY` |
| route operation absent | capability mismatch; target meaning에 따라 `NO_TEST_TARGET` 또는 `RUNNER_NOT_READY` |
| Run 중 queue/DB/API access lost | `INCONCLUSIVE: ACCESS_LIMITED` |
| successful query with required row/message absent | assertion FAIL candidate |
| fault boundary not independently confirmed | `INCONCLUSIVE: INSUFFICIENT_EVIDENCE` |
| restore/redrive uncertainty | Run `RESTORE_FAILED`, verdict INCONCLUSIVE |

Adapter error를 WhyYou 보호조치 PASS 또는 FAIL로 자동 변환하지 않는다.
