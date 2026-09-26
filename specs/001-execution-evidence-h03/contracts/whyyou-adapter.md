# Contract: WhyYou Adapter for H-03

**Target baseline**: `jhkim0602/gbsa_aws` 현재 공개 구현  
**Adapter ID**: `whyyou-local-v1`

## 목적과 경계

adapter는 ControlProof 공통 엔진을 WhyYou의 HTTP API, 회사 콘솔, PostgreSQL, reporting worker와 연결한다. adapter가 assertion verdict를 결정하지 않는다. raw facts와 artifact만 반환한다.

## Required capabilities

H-03 scenario의 capability contract version은 모두 `v1`이다. adapter는 capability ID와 구현 contract version을 함께 등록하며 누락 또는 `v1` 불일치는 `implementation_status=PARTIAL`이다.

| Capability | 의미 | 현재 WhyYou 접점 |
|---|---|---|
| `target.version.read` | canonical 대상 snapshot 및 digest | git SHA+dirty/diff, service image digests, OpenAPI, migration/schema, model fixture |
| `reporting.status.read` | report 상태 조회 | `GET /v1/interview-sessions/{session_id}/report` |
| `reporting.ui.observe` | 회사 사용자 화면 상태 캡처 | `/review/{session_id}?invitationId=...` |
| `hiring.final_decision.attempt` | 정상 회사 사용자 결정 경로 | `POST /v1/invitations/{invitation_id}/final-decisions` |
| `hiring.state.read` | invitation/stage/version 조회 | 회사 API + 제한 DB projection |
| `hiring.decision_history.read` | final decision count/actor | human review 제한 projection |
| `h03.subject.seed` | pending-report 합성 대상 생성 | H-03 전용 SQLAlchemy fixture |
| `reporting.trigger` | generation event 발행 | outbox event fixture |
| `reporting.fault.inject` | run/session 한정 장애 | test-only marker hook |
| `reporting.fault.probe` | 실제 발동 확인 | shared trigger receipt; structured worker log는 보조 |
| `reporting.fault.restore` | marker 제거와 환경 복구 확인 | fault root + worker health |
| `reporting.model.deterministic` | 외부 AI 호출 없는 고정 결과 확인 | fixture ID + canonical digest health probe |

## Configuration

환경변수 값은 artifact나 CLI JSON에 출력하지 않는다.

| 이름 | 용도 |
|---|---|
| `CONTROLPROOF_TARGET_ID` | 기본 `whyyou-local` |
| `WHYYOU_BASE_URL` | backend API base |
| `WHYYOU_CONSOLE_URL` | company console base |
| `WHYYOU_COMPANY_TOKEN` | 합성 회사 사용자 bearer |
| `WHYYOU_DATABASE_URL` | 격리 DB 접속 |
| `WHYYOU_REPO_PATH` | git SHA와 schema mapping 확인 |
| `CONTROLPROOF_FAULT_ROOT` | worker와 공유한 test-only marker root |
| `CONTROLPROOF_RUN_ROOT` | evidence bundle root |
| `CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED` | local/test에서만 `true`; 고정 report 모델 대역 활성화 |
| `CONTROLPROOF_MODEL_FIXTURE_ID` | 허용된 고정 fixture 식별자 |

## Preflight

adapter는 쓰기 전에 다음 순서로 확인한다.

1. URL과 DB가 local/test allowlist에 해당하는지 확인한다.
2. git commit·dirty diagnostic manifest digest, canonical component `backend`·`reporting-worker`·`company-console`의 image digest, OpenAPI digest, migration head/schema signature와 model fixture ID/digest를 읽어 `controlproof.target-snapshot.v1` canonical JSON과 `target-snapshot:sha256:<digest>`를 만든다. Git 또는 image identity가 없거나 세 container component 중 하나가 없으면 `RUNNER_NOT_READY`다. H-03 actual Run에서 dirty checkout도 `RUNNER_NOT_READY`이며 diff digest는 operator diagnostic에만 사용한다.
3. company bearer로 read endpoint 접근을 확인한다.
4. report와 final-decision route contract가 존재하는지 확인한다.
5. seed table signature와 outbox signature를 확인한다.
6. Chromium 실행 가능 여부를 확인한다.
7. fault root의 marker 디렉터리는 양쪽에서 접근 가능하고 `receipts/`는 worker write·ControlProof read가 가능한지 확인한다.
8. hook enabled와 deterministic model substitute enabled, 허용 fixture ID, fixture digest를 health probe로 확인한다.
9. 동일 target/subject의 block marker와 active lock이 없는지 확인한다.

분류 규칙:

- route/domain 자체가 없음 → `NO_TEST_TARGET`
- credential/DB 접근 불가 → `ACCESS_BLOCKED`
- hook, browser, seed mapping, shared mount, trigger receipt, deterministic model substitute 중 하나라도 없음 → `RUNNER_NOT_READY`
- 모두 통과 → `READY`

## H-03 subject seed

### 생성 상태

- company와 active company user
- position과 recruiting stage
- synthetic applicant와 invitation
- invitation status `completed`
- interview session completed/review-generation 가능한 상태
- final applicant turns, transcripts, final video asset
- report/report item/evidence 없음
- final decision human review 없음
- `report.generation_requested` outbox event 없음

### 출력

```json
{
  "subject_ref": "candidate-01",
  "synthetic": true,
  "seed_correlation_id": "cp-<run-id>",
  "company_id": "uuid",
  "company_user_id": "uuid",
  "position_id": "uuid",
  "invitation_id": "uuid",
  "interview_session_id": "uuid",
  "target_stage_id": "uuid",
  "pipeline_row_version": 1
}
```

raw email/name/token은 출력하지 않는다. seed는 run label에 대한 idempotent upsert여야 하며 다른 label의 row를 변경하지 않는다.

## Fault marker

marker 상대 경로:

```text
reporting/{interview_session_id}.json
```

내용:

```json
{
  "schema_version": "controlproof.whyyou-fault.v1",
  "run_id": "uuid",
  "interview_session_id": "uuid",
  "fault_type": "reporting_handler_timeout_v1",
  "issued_at": "2026-09-24T00:00:00Z",
  "expires_at": "2026-09-24T00:05:00Z"
}
```

worker hook requirements:

- production profile에서 marker를 무시하는 것이 아니라 enabled 설정 자체를 거부한다.
- schema/UUID/TTL이 틀리면 fault를 적용하지 않고 warning을 남긴다.
- 대상 session이 아닌 message에는 영향이 없어야 한다.
- 발동 시 기존 handler side effect 전에 `TimeoutError`를 발생시킨다.
- 구조화 로그는 `event=CONTROLPROOF_FAULT_TRIGGERED`, `run_id`, `session_id`, `outbox_event_id`, `delivery_attempt`, `fault_type`, `triggered_at`을 포함한다.
- 같은 필드의 receipt를 `${CONTROLPROOF_FAULT_ROOT}/receipts/{run_id}.jsonl`에 한 줄 JSON으로 append하고 `fsync`한 뒤 `TimeoutError`를 발생시킨다.
- receipt의 `run_id`, `session_id`, `outbox_event_id`가 현재 Run의 marker와 trigger 결과에 모두 일치할 때만 fault effect를 확인한다. marker 생성 성공이나 로그 검색 실패만으로 발동 여부를 추론하지 않는다.

## Deterministic report model substitute

- WhyYou의 기존 report 생성 의존성 주입 경계에 local/test 전용 고정 결과 대역을 연결한다.
- `CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED=true`는 production profile에서 startup 실패다.
- health probe는 `enabled=true`, `fixture_id`, canonical fixture SHA-256을 반환한다. secret이나 fixture 본문은 반환하지 않는다.
- ControlProof는 scenario가 허용한 fixture ID와 실제 digest가 일치할 때만 `reporting.model.deterministic=READY`로 분류한다.
- 대역이 비활성, digest 불일치 또는 probe 불가이면 `RUNNER_NOT_READY`이며 실제 외부 LLM으로 fallback해서는 안 된다.

## Reporting trigger

fault marker 존재를 확인한 뒤 exactly one logical `report.generation_requested` event를 발행한다. event의 idempotency key는 session 기준으로 결정론적이어야 한다. Spec 001은 retry/DLQ 중복을 판정하지 않지만 trigger 자체의 중복으로 시험을 오염시키면 안 된다.

## Status normalization

### Report API

| HTTP/Body | Normalized observations |
|---|---|
| `200` + report | `report.presence=PRESENT`, `report.status=<ready|partial|failed...>` |
| `202` + `queued` | `report.presence=ABSENT`, `report.status=queued` |
| `404` | API 접근 성공이나 session/report 의미에 따라 `ABSENT`; target detail을 있는 그대로 보존하며 reason을 추론하지 않음 |
| auth/network error | `presence=UNAVAILABLE`, error code 보존 |

### Console

Playwright는 실제 company user context로 review route를 연다. screenshot과 다음 text projection을 저장한다.

```json
{
  "route": "/review/{session_id}",
  "role": "status|alert|main",
  "visible_text": "sanitized text",
  "ready_content_visible": false,
  "decision_control_visible": false,
  "captured_at": "...",
  "viewport": {"width": 1440, "height": 900}
}
```

DOM selector 자체는 adapter 내부 detail이며 scenario rule은 normalized field를 사용한다.

## Final decision attempt

- company bearer 사용
- 공개된 정상 route 사용
- body는 target recruiting stage와 baseline `expected_pipeline_version`
- DB 직접 write 금지
- 요청 전후에 같은 state snapshot을 수집
- request/response는 authorization을 제거하고 EV-05로 저장

Normalized output:

```json
{
  "accepted": false,
  "http_status": 404,
  "reason_present": false,
  "reason_code": null,
  "reason_source": null,
  "idempotency_key_digest": "sha256"
}
```

`reason_present=true`와 `reason_code=REPORT_NOT_AVAILABLE`은 target response body 또는 target의 안정된 error code가 리포트 부재를 명시한 경우에만 허용하며 `reason_source=target_body|target_error_code`를 함께 기록한다. 일반 404, 빈 detail, route 문구나 adapter의 사전 지식에서 이유를 추론하지 않는다. adapter의 `reason_code`는 raw target detail을 allowlist로 정규화한 것이며 assertion verdict가 아니다. 거부됐지만 `reason_present=false`이면 H03-A3은 FAIL이다.

## State snapshot projection

DB/API에서 아래 필드만 읽는다.

```json
{
  "invitation_status": "completed",
  "recruiting_stage_id": "uuid-or-null",
  "pipeline_row_version": 1,
  "final_decision_count": 0,
  "latest_final_decision_actor_type": null,
  "report_presence": "ABSENT",
  "report_status": null
}
```

H03-A4는 baseline과 post-attempt의 첫 5개 필드가 모두 동일한지 비교한다. H03-A5는 관찰 창 전체에서 `final_decision_count=0`, actor null, 상태 변화 없음인지 평가한다.

## Restore

1. marker를 atomic delete한다. 이미 없으면 idempotent success 후보로 기록한다.
2. hook probe로 session fault가 inactive인지 확인한다.
3. worker health가 정상인지 확인한다.
4. 120초 안에 marker 비활성 및 worker 정상성이 모두 확인되면 `environment_restore=SUCCEEDED`다.
5. 같은 창에서 reporting status를 poll해 `report_processing_recovery=READY|PARTIAL|FAILED|TIMEOUT|UNAVAILABLE`로 별도 기록한다.
6. `FAILED|TIMEOUT`은 제품 처리 finding으로 남기지만 환경 복구 성공을 실패로 덮어쓰지 않는다.
7. marker 활성/unknown, worker health 비정상/unknown이면 `environment_restore=FAILED`, Run `RESTORE_FAILED`다.

teardown은 restore 뒤에만 수행하며 bundle seal 전 synthetic fixture correlation을 기록한다. teardown 실패는 제품 verdict와 별도 maintenance finding으로 남긴다.

## Adapter error mapping

| Error | ControlProof 처리 |
|---|---|
| preflight auth failure | `ACCESS_BLOCKED`, Run 미생성 |
| hook missing/disabled | `RUNNER_NOT_READY`, Run 미생성 |
| target feature missing | `NO_TEST_TARGET`, Run 미생성 |
| Run 중 API 접근 소실 | assertion `INCONCLUSIVE: ACCESS_LIMITED` |
| required artifact 수집 실패 | `INCONCLUSIVE: INSUFFICIENT_EVIDENCE` |
| same-dimension source conflict | `INCONCLUSIVE: EVIDENCE_CONFLICT` |
| restore failure | Run `RESTORE_FAILED`, 전체 INCONCLUSIVE, exit 6 |

adapter 오류를 WhyYou 보호조치 FAIL로 바꾸지 않는다.
