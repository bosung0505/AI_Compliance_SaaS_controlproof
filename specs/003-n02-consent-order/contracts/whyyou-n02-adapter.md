# Contract: WhyYou Adapter for N-02

**Target**: WhyYou local/test personal branch only
**Adapter ID**: `whyyou-local-n02-v1`
**Base**: Spec 001·002 WhyYou adapter contracts

## Boundary

adapter는 WhyYou HTTP/WebSocket, PostgreSQL, LocalStack과 local/test receipt를 최소 raw fact로 정규화한다.
adapter는 N-02 verdict를 결정하지 않는다. 전체 DB dump, 전체 로그, token, cookie, presigned URL, PII,
답변·이력서 원문과 report narrative를 반환하지 않는다.

## Path capability map

| Path | Entry | Directness | Start proof | Result proof |
|---|---|---|---|---|
| `DOCUMENT_ANALYSIS` | `createSubmissionUploadIntent` | pristine direct | upload/submission request receipt, analysis handler receipt | storage intent, submission, analysis, strategy projection |
| `RECORDING` | `createInterviewSession` | deep probe | session create/start receipt | session, recording chunk/asset projection |
| `AI_ASSESSMENT` | `report.generation_requested` | no independent applicant route; real worker event | reporting handler receipt | report/item/projection/processed marker |

source locator는 repo-relative path와 symbol만 저장한다. 대상 commit이 바뀌면 capability snapshot을 다시
만들고 digest를 변경한다.

## ConsentAdapter

### `read_policy(subject)`

`GET /v1/applicant/consents`를 호출하고 다음만 반환한다.

```json
{
  "policy_version": "2026-08-v1",
  "content_digest": "sha256-hex",
  "required_purposes": ["ai_assessment", "document_analysis", "recording"],
  "retention_days": 365,
  "request_id": "uuid",
  "received_at": "aware datetime"
}
```

정책 문구 원문과 화면 정보는 저장하지 않는다.

### `commit(subject, policy, request_id, trace_id)`

`POST /v1/applicant/consents`를 모든 필수 purpose와 현재 version/digest로 호출한다. raw cookie와
Idempotency-Key는 artifact에 저장하지 않는다. status, sanitized reason, response ID/version/purpose/time만
반환한다.

### `read_state(subject, phase)`

현재 company/invitation에 한정해 다음을 projection한다.

- invitation status와 row version
- consent record ID, active 여부, policy version, evidence digest, purposes, accepted_at
- `consented` invitation state-change ID/version/time
- `invitation.consent_completed` Outbox ID/version/trace digest/status/time

조회 성공+0건은 ABSENT, query 실패는 UNAVAILABLE다.

## N02SeedAdapter

`seed(run_id)`는 canonical 6개 lane을 한 deterministic fixture set으로 만든다. 모든 applicant는 synthetic
표식을 가지며 실제 이메일을 쓰지 않는다.

### Pristine invariant

- invitation status `identity_verified`
- active consent 0
- consent-completed state change/outbox 0
- submission/analysis/strategy/session/recording/report effect 0

### Recording probe fixture

- identity-verified invitation
- ready equipment check 1
- matching strategy 1
- consent/session/chunk/asset/report 0

### Assessment probe fixture

- identity-verified invitation
- completed session, final applicant turn과 final video input
- consent/report/report item/assistant projection/report request/processed marker 0

fixture는 해당 deep boundary의 authorization을 분리하기 위한 test precondition이며 정상 사용자 처리
결과로 표현하지 않는다. adapter는 fixture projection과 SHA-256을 반환한다.

`teardown(run_id)`는 seed correlation allowlist만 제거한다. 다른 Run이나 기존 local demo data를
삭제하지 않는다.

fault lane에는 다음 pair를 제공한다.

- `apply_probe_overlay(subject, path)`: failed-consent zero snapshot 뒤 recording 또는 assessment의
  canonical prerequisite만 추가하고 overlay digest를 반환한다.
- `remove_probe_overlay(subject, path)`: 그 overlay가 만든 row/object만 제거하고 원 seed digest 복원을
  확인한다.

overlay는 정상 동의 복구와 다른 lane에 사용할 수 없다. cleanup 실패는 restore uncertainty다.

## ProtectedProcessingAdapter

### `attempt_document(subject)`

미동의 applicant cookie로 upload-intent API를 직접 호출한다. 정상 기대는 403이다. 403이어도
post-effect read가 불가능하면 PASS 근거가 아니다.

### `attempt_recording(subject)`

fixture equipment/strategy ID로 create-session API를 호출한다. 동의 없음이므로 정상 기대는 403이다.
성공해 session row가 생기면 직접 FAIL 후보다.

### `attempt_assessment(subject)`

실제 schema의 `report.generation_requested` Outbox event를 current company/session에 한정해 삽입한다.
event ID와 trace는 Run/lane에서 결정론적으로 만든다. worker handler receipt 또는 report effect를 polling한다.
전용 product endpoint를 만들지 않는다.

### `read_effects(subject, path, phase)`

allowlist query:

- document: object intent identity if observable, submissions, analysis Outbox, analysis rows, strategies
- recording: sessions, session state, recording chunks, recording assets
- assessment: report request Outbox, handler receipt, reports, report items, assistant documents, processed marker

원문 JSON payload 전체는 저장하지 않고 allowlist ID/type/version/status만 정규화한다.

## CausalityAdapter

다음 source에서 event와 edge를 만든다.

- HTTP command sent/response received
- consent/state-change/Outbox transaction projection
- downstream Outbox event identity/trace
- worker boundary receipt
- result row identity

raw trace는 bundle에 필요하지 않으면 SHA-256으로 저장한다. 같은 trace라는 사실과 event identity는
유지해야 한다.

## Readiness

READY 전에 다음을 모두 확인한다.

1. ControlProof와 WhyYou checkout identity가 읽히며 둘 다 clean이다.
2. WhyYou는 `main`/`master`가 아닌 개인 branch다.
3. API, DB, LocalStack endpoint는 local allowlist다.
4. `APP_ENVIRONMENT`는 local/test다.
5. test hook과 observer가 enabled이고 production guard가 유효하다.
6. external AI는 disabled, model/embedder fixture ID/digest는 scenario allowlist와 일치한다.
7. policy version/digest/purpose set을 읽을 수 있다.
8. lane seed/teardown, 세 path attempt/effect, consent fault/receipt/restore capability가 모두 있다.
9. worker health와 필요한 queue가 접근 가능하다.

## Error mapping

| Condition | Mapping |
|---|---|
| non-local endpoint, external AI 가능, WhyYou main | `RUNNER_NOT_READY` |
| path exists but adapter/observer/fixture unavailable | `RUNNER_NOT_READY` |
| DB/API/LocalStack credential inaccessible before Run | `ACCESS_BLOCKED` |
| Run 중 source access loss | `INCONCLUSIVE: ACCESS_LIMITED` |
| successful query with prohibited new effect | assertion FAIL candidate |
| successful query with no effect and denied attempt | PASS candidate |
| denied attempt but post-effect UNAVAILABLE | `INCONCLUSIVE: INSUFFICIENT_EVIDENCE` |
| fixture digest mismatch | precondition abort; product FAIL 아님 |
| causal source contradiction | `INCONCLUSIVE: EVIDENCE_CONFLICT` |
| restore uncertainty | `RESTORE_FAILED`, INCONCLUSIVE |

모든 non-READY 결과는 공통 readiness envelope의 비어 있지 않은 `operator_action`을 반환한다.
`ACCESS_BLOCKED`는 접근이 막힌 API/DB/LocalStack source와 필요한 권한 범주를 설명하되 secret이나 실제
credential을 출력하지 않는다. preflight 실패는 Run directory, subject, marker와 event를 만들지 않는다.

## Conditional product remediation

adapter는 consent guard를 구현하지 않는다. 최초 actual FAIL 뒤 WhyYou product boundary를 보완할 때도
같은 adapter contract와 path IDs를 유지한다. parent/child 비교에서 바뀌는 것은 target snapshot과 실제
effect이며 scenario 의미는 바뀌지 않는다.
