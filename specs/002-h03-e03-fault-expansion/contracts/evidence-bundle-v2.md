# Contract: Evidence Bundle — Spec 002 additive profile

## 1. Compatibility boundary

- Spec 001의 `controlproof.bundle.v1` 구조와 봉인 규칙을 유지한다.
- Spec 002는 `manifest.json.schema_version`을 바꾸지 않고 `execution_profile`에 따라 canonical 파일과
  EV2 검증 규칙을 additive하게 적용한다.
- 기존 H-03 v1 bundle은 새 파일이 없어도 그대로 검증돼야 한다.
- Spec 002 bundle은 `run.json.execution_profile`과
  `manifest.json.profile_contract=controlproof.bundle-profile.spec002.v1`을 반드시 가진다.
- verifier는 먼저 schema version을, 그다음 profile contract를 dispatch한다. 알 수 없는 profile
  contract를 임의로 v1처럼 검증해 PASS로 만들 수 없다.

## 2. Directory structure

```text
.controlproof/runs/{run_id}/
├── run.json
├── scenario.snapshot.yaml
├── target.snapshot.json
├── environment.snapshot.json       # Spec 002 required
├── queue-topology.snapshot.json    # Spec 002 required
├── subjects.json
├── faults.jsonl
├── observations.jsonl
├── checkpoints.jsonl
├── delivery-attempts.jsonl         # Spec 002 required
├── effects.jsonl                   # Spec 002 required
├── terminal-failure.json           # DLQ profile only
├── redrive-receipts.jsonl          # DLQ redrive profile only
├── assertions.json
├── judgement.json
├── retest-diff.json                # retest only
├── artifacts/
│   └── {artifact_id}.{json|png|log}
└── manifest.json
```

모든 경로, atomic write, fsync, redaction, seal 불변성 규칙은 Spec 001 계약을 따른다. 새 JSONL도 한
record마다 flush하고 phase 경계에서 fsync한다. `manifest.json`이 봉인된 뒤에는 새 파일을 추가하거나
기존 파일을 고칠 수 없다.

## 3. `run.json` additions

```json
{
  "schema_version": "controlproof.run.v1",
  "run_id": "0199...",
  "scenario_id": "E-03",
  "execution_profile": "E03_AFTER_V2",
  "fault_variant": "AFTER_RESULT_DURABLE_BEFORE_COMPLETION",
  "target_id": "whyyou-local",
  "environment_kind": "LOCAL_EMULATED",
  "aws_deployment_status": "NOT_RUN",
  "environment_snapshot_digest": "sha256:<64-lowercase-hex>",
  "queue_topology_digest": "sha256:<64-lowercase-hex>",
  "source_event_id": "uuid",
  "unverified_scope": ["AWS_SQS", "AWS_ECS", "AWS_IAM", "AWS_CLOUDWATCH", "AWS_NETWORK"]
}
```

`LOCAL_EMULATED` Run에서 `aws_deployment_status`는 항상 `NOT_RUN`이다. 로컬 결과를 cloud 검증으로
표현하는 문자열이나 필드는 허용하지 않는다.

## 4. Environment and queue snapshots

`environment.snapshot.json`은 다음 identity를 포함한다.

- ControlProof·WhyYou commit SHA와 dirty 상태
- host OS, compose 파일 digest
- PostgreSQL·LocalStack·Mailpit·API·worker·company console 실행 mode/version
- loopback endpoint의 scheme/host/port
- model substitute와 embedding fixture ID/digest
- `environment_kind=LOCAL_EMULATED`, `aws_deployment_status=NOT_RUN`, 미검증 cloud 범위

`queue-topology.snapshot.json`은 queue URL 원문 대신 비민감 locator를 쓰며 다음을 포함한다.

```json
{
  "schema_version": "controlproof.queue-topology.v1",
  "source_queue_name": "iep-reporting",
  "dead_letter_queue_name": "iep-reporting-dlq",
  "endpoint_kind": "LOCALSTACK",
  "max_receive_count": 3,
  "visibility_timeout_seconds": 5,
  "redrive_target_matches": true,
  "captured_at": "2026-09-28T00:00:00Z"
}
```

실제 attribute가 scenario timing contract와 다르면 preflight에서 중단하므로 부정확한 snapshot을 가진
Run은 만들지 않는다.

## 5. Delivery, terminal failure, and recovery records

### `delivery-attempts.jsonl`

```json
{
  "schema_version": "controlproof.delivery-attempt.v1",
  "run_id": "0199...",
  "subject_ref": "candidate-01",
  "source_event_id": "uuid",
  "message_fingerprint": "sha256:<digest>",
  "delivery_attempt": 2,
  "approximate_receive_count": 2,
  "fault_variant": "BEFORE_RESULT_DURABLE",
  "outcome": "FAULT_TRIGGERED",
  "error_code": "CONTROLPROOF_INJECTED_BEFORE_DURABLE",
  "observed_at": "2026-09-28T00:00:10Z",
  "artifact_ids": ["0199..."]
}
```

같은 `source_event_id`와 `message_fingerprint`만 하나의 전달 계보로 묶는다. SQS receipt handle 원문과
message body 전체는 저장하지 않는다.

### `terminal-failure.json`

H03_DLQ_V2와 E03_BEFORE_V2에서 필수다. DLQ record가 없다는 관찰과 DLQ 조회 자체가 실패한 상태를
구분한다. 필수 필드는 `source_event_id`, `message_fingerprint`, 실제 receive count, 마지막 안정 오류
code, DLQ locator, 관찰 시각이다.

### `redrive-receipts.jsonl`

redrive는 같은 domain body·message attributes를 source queue에 전송한 성공 receipt를 먼저 남기고,
그 뒤 DLQ 원본 삭제 성공을 남긴다. 전송 성공 후 삭제 확인 실패는 `RESTORE_UNCERTAIN`이며 PASS 근거로
쓸 수 없다.

## 6. `effects.jsonl`

```json
{
  "schema_version": "controlproof.effect-snapshot.v1",
  "run_id": "0199...",
  "subject_ref": "candidate-01",
  "phase": "RECOVERED",
  "step_id": "state.effects.read",
  "attempt": 1,
  "logical_operation_id": "uuid",
  "source_event_id": "uuid",
  "effect_group": "REPORTING",
  "effects": {
    "report_ids": ["uuid"],
    "projection_document_ids": ["uuid"],
    "processed_keys": [{"consumer_name": "reporting-worker", "event_id": "uuid", "event_version": 1}],
    "source_outbox_event_ids": ["uuid"]
  },
  "state_digest": "sha256:<digest>",
  "source_status": "PRESENT",
  "observed_at": "2026-09-28T00:01:00Z",
  "artifact_ids": ["0199..."]
}
```

허용 effect group과 그 안의 identity는 다음과 같다.

- `REPORTING`: `REPORT`, `ASSISTANT_PROJECTION`, `PROCESSED_MESSAGE`, `SOURCE_OUTBOX_EVENT`
- `DECISION`: `RECRUITING_STAGE`, `INVITATION_REVIEWED`, `HUMAN_REVIEW`, `FINAL_DECISION_AUDIT`

전체 row dump 대신 식별자, 논리 건수, allowlist 상태와 digest만 저장한다. `ABSENT`는 조회 성공 후 0건,
`UNAVAILABLE`은 접근 실패이며 안정적인 `error_code`가 필요하다.

## 7. EV2 evidence mapping

`manifest.json.required_evidence` 값은 `artifact:<id>` 또는 `file:<relative-path>` reference다. manifest
자체의 봉인·digest는 `intrinsic:sealed-manifest`로 표시한다.

H03_DLQ_V2는 아래 EV2 집합과 함께 Spec 001 EV-01~EV-09 mapping도 그대로 충족해야 한다.

| ID | Required minimum references |
|---|---|
| EV2-01 | `environment.snapshot.json`, `queue-topology.snapshot.json`, capability artifact |
| EV2-02 | baseline `effects.jsonl` records, source Outbox/event artifact |
| EV2-03 | apply receipt와 해당 Run·session·trigger의 boundary receipt |
| EV2-04 | `delivery-attempts.jsonl`과 원 사건 연결 artifact |
| EV2-05 | `terminal-failure.json`과 matching DLQ record artifact |
| EV2-06 | 담당자 화면 screenshot+visible-text, report status HTTP exchange |
| EV2-07 | path별 decision HTTP exchange와 actor/path metadata |
| EV2-08 | decision 전후 `effects.jsonl` records |
| EV2-09 | fault restore, worker health, redrive receipt와 recovered status |
| EV2-10 | reporting effect 4종의 전후 `effects.jsonl` records |
| EV2-11 | 같은 Idempotency-Key의 두 HTTP exchange와 decision effect 4종 비교 |
| EV2-12 | scenario·target·environment snapshot과 `intrinsic:sealed-manifest` |

profile별 required EV2 집합은 `scenario-profile-v2.md`의 canonical profile과 정확히 일치해야 한다.
다른 Run의 artifact를 재사용하면 reference에 `origin_run_id`, 원 artifact ID와 digest가 필요하며 원 bundle
verify가 먼저 성공해야 한다.

## 8. Manifest additions

```json
{
  "schema_version": "controlproof.bundle.v1",
  "profile_contract": "controlproof.bundle-profile.spec002.v1",
  "run_id": "0199...",
  "execution_profile": "H03_DLQ_V2",
  "environment_snapshot_digest": "sha256:<digest>",
  "queue_topology_digest": "sha256:<digest>",
  "required_evidence": {
    "EV2-01": ["file:environment.snapshot.json", "file:queue-topology.snapshot.json", "artifact:0199..."],
    "EV2-12": ["file:scenario.snapshot.yaml", "file:target.snapshot.json", "intrinsic:sealed-manifest"]
  }
}
```

`files`에는 manifest 자신을 제외한 모든 canonical 파일이 포함돼야 한다. profile에서 비적용인 EV2를
빈 배열로 만들지 않고 아예 생략한다.

## 9. Verify contract

Spec 001 검증에 더해 다음을 확인한다.

1. scenario profile, fault variant, assertion 집합과 required EV2 집합의 일치
2. target/environment/queue digest와 canonical snapshot bytes의 일치
3. `whyyou-local`의 loopback·LocalStack endpoint 및 AWS `NOT_RUN` 주장
4. source event → delivery attempts → terminal failure 또는 duplicate-ack → effects의 lineage
5. attempt 번호의 단조 증가와 declared max receive count 일치
6. boundary receipt가 선택된 fault variant와 정확히 일치
7. effect identity별 logical count와 assertion actual value 일치
8. redrive send/delete 순서와 restore 안전 상태
9. cross-Run evidence의 원본 bundle digest와 불변성
10. sealed parent가 retest 이후에도 byte-for-byte 동일함

필수 reference 누락·hash 불일치는 integrity failure(exit 5)다. 필수 출처 접근 실패나 서로 충돌하는
증적은 Run verdict INCONCLUSIVE의 입력이며 verifier가 임의로 내용을 추정해 보완하지 않는다.
