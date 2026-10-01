# Contract: WhyYou Consent Fault and Processing Observer

## Safety boundary

이 계약은 local/test 전용이다. `CONTROLPROOF_TEST_HOOKS_ENABLED=true`인데 `APP_ENVIRONMENT`가
`local` 또는 `test`가 아니면 WhyYou startup은 실패해야 한다. hook은 외부 HTTP endpoint를 제공하지
않고 filesystem marker를 읽는다.

## Marker

경로:

```text
{CONTROLPROOF_FAULT_ROOT}/consent/{invitation_id}.json
```

payload:

```json
{
  "schema_version": "controlproof.whyyou-consent-fault.v1",
  "run_id": "uuid",
  "lane_id": "CONSENT_FAULT_RECOVERY",
  "subject_ref": "synthetic-ref",
  "invitation_id": "uuid",
  "applicant_id": "uuid",
  "fault_type": "consent_after_record_before_state_v1",
  "fault_variant": "AFTER_CONSENT_RECORD_BEFORE_STATE",
  "issued_at": "2026-10-01T00:00:00Z",
  "expires_at": "2026-10-01T00:10:00Z",
  "one_shot": true
}
```

Validation:

- 모든 ID는 canonical UUID/string이고 current request subject와 일치한다.
- `issued_at <= now < expires_at`, TTL은 600초 이하다.
- schema/fault/variant/lane/one-shot이 정확히 일치한다.
- invalid/expired/mismatched marker는 발동하지 않고 sanitized warning만 남긴다.

## Injection boundary

호출 순서:

```text
validate policy/purposes
build ConsentRecord and consented Invitation
repository.save_consent(...)
CONTROLPROOF boundary hook
save invitation and state change
append invitation.consent_completed
HTTP middleware commit
```

hook은 `save_consent()`이 현재 SQLAlchemy transaction에 row를 추가한 뒤 호출한다. marker가 일치하면
one-shot consumed token을 원자적으로 만든 뒤 trigger receipt를 fsync하고 전용 runtime exception을
발생시킨다. handler는 이 exception을 422로 바꾸지 않으며 request middleware가 rollback하고 5xx를
반환한다.

## One-shot token

경로:

```text
{CONTROLPROOF_FAULT_ROOT}/consumed/{run_id}-{invitation_id}.consent
```

`O_CREAT|O_EXCL` 또는 동등한 원자 연산으로 하나만 만든다. 이미 존재하면 다시 발동하지 않는다.

## Trigger receipt

경로:

```text
{CONTROLPROOF_FAULT_ROOT}/receipts/{run_id}.jsonl
```

payload:

```json
{
  "schema_version": "controlproof.whyyou-consent-fault-receipt.v1",
  "receipt_id": "uuid",
  "run_id": "uuid",
  "lane_id": "CONSENT_FAULT_RECOVERY",
  "subject_ref": "synthetic-ref",
  "invitation_id": "uuid",
  "applicant_id": "uuid",
  "request_id": "uuid",
  "fault_type": "consent_after_record_before_state_v1",
  "fault_variant": "AFTER_CONSENT_RECORD_BEFORE_STATE",
  "boundary": "AFTER_CONSENT_RECORD_BEFORE_INVITATION_STATE",
  "triggered_at": "aware datetime",
  "one_shot_consumed": true
}
```

append 뒤 stream flush와 `fsync`를 완료한 후 예외를 발생시킨다. raw policy body, applicant name/email,
cookie, token은 포함하지 않는다.

## Restore

ControlProof restore 순서:

1. marker를 current Run/invitation과 다시 대조한다.
2. marker와 consumed token을 제거한다.
3. 같은 subject에 fault가 inactive인지 probe한다.
4. 별도 DB connection으로 consent row/state change/outbox가 0건인지 확인한다.
5. 아직 미동의인 같은 subject에서 세 path를 시도한다. recording/assessment 임시 overlay는 각 시도 뒤
   제거한다.
6. 원 pristine seed digest와 worker/API health를 확인한다.
7. restore receipt를 bundle에 저장한다.

삭제 대상은 resolved fault root 아래 current Run 파일로 제한한다. marker 소유권이 다르거나 path가 root를
벗어나면 삭제하지 않고 restore failure로 처리한다.

marker 제거 또는 안전 상태 확인이 실패하면 Run state는 `RESTORE_FAILED`, verdict는 INCONCLUSIVE,
`manual_cleanup_required=true`다. `cleanup-confirm` 전 같은 target의 새 fault Run을 막는다.

## Processing observer

observer는 `CONTROLPROOF_OBSERVER_ENABLED=true`와 local/test에서만 동작한다. trace가
`controlproof:{run_id}:{lane_id}:...` 형식이고 UUID/lane validation을 통과할 때만 receipt를 남긴다.

Allowed boundary:

```text
ANALYSIS_HANDLER_ENTERED
INTERVIEW_SESSION_CREATED
INTERVIEW_SESSION_STARTED
RECORDING_CONFIRMED
REPORT_HANDLER_ENTERED
```

WhyYou source boundary:

| Boundary | Source symbol |
|---|---|
| `ANALYSIS_HANDLER_ENTERED` | `workers/analysis/event_handler.py::AnalysisRequestedEventHandler.__call__` |
| `INTERVIEW_SESSION_CREATED` | `interview_engine/application/session_service.py::_create_session_once` |
| `INTERVIEW_SESSION_STARTED` | `interview_engine/application/session_service.py::_start_session_once` |
| `RECORDING_CONFIRMED` | `interview_engine/application/session_service.py::confirm_recording_upload` |
| `REPORT_HANDLER_ENTERED` | `runtime/worker.py::ReportRequestedEventHandler.__call__` |

observer는 `interview_engine/api/__init__.py`의 optional port를 통해 주입하고 `runtime/production.py`가
local/test에서만 실제 writer를 연결한다. 도메인/application 모듈이 runtime 구현을 직접 import하지 않는다.

receipt:

```json
{
  "schema_version": "controlproof.whyyou-processing-receipt.v1",
  "receipt_id": "uuid",
  "run_id": "uuid",
  "lane_id": "NORMAL_ORDER",
  "subject_ref": "synthetic-ref",
  "path_id": "AI_ASSESSMENT",
  "boundary": "REPORT_HANDLER_ENTERED",
  "request_or_event_id": "uuid",
  "trace_id_digest": "sha256-hex",
  "observed_at": "aware datetime"
}
```

observer failure는 product transaction을 실패시키지 않는다. 다만 필요한 receipt를 읽지 못한 Run은
PASS가 아니라 INCONCLUSIVE다. fault trigger receipt failure는 장애가 실제 발동했는지 증명할 수 없으므로
fault를 발생시키지 않고 안전하게 반환한다.

## Required tests

- production/staging enable 시 startup failure
- disabled 상태 no-op
- expired, long TTL, wrong Run/subject/schema/fault type no-op
- one-shot concurrency에서 receipt 1건
- receipt fsync failure 시 fault 미발동
- trigger 뒤 transaction 전체 rollback
- restore ownership/path traversal guard
- observer에 PII/credential field가 없는지 contract test
- 다른 lane trace가 current Run receipt로 선택되지 않는지 isolation test
