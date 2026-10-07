# Contract: Evidence Bundle Profile for Spec 003

## Compatibility

canonical bundle schema는 `controlproof.bundle.v1`을 유지한다. N-02 manifest는 다음 profile contract를
추가한다.

```text
controlproof.bundle-profile.spec003.v1
```

Spec 001/002 bundle은 새 파일이 없어도 기존 contract로 계속 verify된다.

## Required canonical files

기존 Run/scenario/target/observations/judgement/artifacts/manifest 파일에 다음을 추가한다.

```text
n02-capabilities.json
n02-lanes.json
policy-and-consent.json
baseline-effects.jsonl
bypass-attempts.jsonl
protected-effects.jsonl
causal-events.jsonl
causal-edges.jsonl
fault-receipts.jsonl
recovery.json
```

retest child에는 기존 `retest-diff.json`도 필수다.

## Evidence mapping

| EV3 | Required source |
|---|---|
| EV3-01 | capabilities + lanes + environment/scenario/target snapshot |
| EV3-02 | policy-and-consent + consent HTTP artifact |
| EV3-03 | baseline-effects + lane fixture descriptor |
| EV3-04 | bypass-attempts |
| EV3-05 | protected-effects baseline/current/delta |
| EV3-06 | causal-events + causal-edges |
| EV3-07 | fault apply artifact + matching trigger receipt |
| EV3-08 | failed consent/effect snapshot |
| EV3-09 | recovery + recovered effects |
| EV3-10 | assertion results + judgement + manifest, retest diff if child |

Post-T078 additive evidence rule: a runner-inserted AI assessment outbox event is
recorded in `bypass-attempts.jsonl` as `SUBMITTED` with a `probe_input_effect_id`.
`protected-effects.jsonl` retains the row in `current_effect_ids` but excludes it
from `new_effect_ids` and lists it under `probe_input_effect_ids`. A target
`REPORT_ASSESSMENT_STARTED` receipt is stored in the existing
`observations.jsonl` stream and cross-linked through `start_receipt_ids` by
Run/lane/subject/path/event ID. The earlier sealed parent lacks these additive
fields and remains verifiable. A missing start/deny/result signal cannot be
promoted to PASS or target FAIL from the injected row alone. The consent
response evidence includes only an allowlisted target reason code, status and
request ID; recovery evidence distinguishes cleanup, safe state and retry.

한 파일이 여러 EV3를 충족할 수 있으나 manifest reference는 각 EV3에서 독립적으로 검증한다.

## Cross-reference rules

- 모든 lane/subject reference는 `n02-lanes.json`에 등록돼야 한다.
- fixture digest는 capability와 baseline artifact에서 동일해야 한다.
- attempt ID는 post-effect delta와 같은 path/lane을 가리켜야 한다.
- causal edge의 두 event는 같은 Run/lane/subject에 존재해야 한다.
- fault receipt는 current Run/fault lane/failed request와 일치해야 한다.
- A2~A4 PASS에는 denied attempt와 zero delta가 모두 있어야 한다.
- A5 PASS에는 consent commit부터 각 path result까지 적용 가능한 causal edge가 있어야 한다.
- A6 PASS에는 trigger receipt, 실패 직후 zero partial effect, 같은 subject의 세 path attempt와 임시
  overlay cleanup 증거가 있어야 한다.
- A7 PASS에는 restore safe-state, exactly-one consent set과 recovered order가 있어야 한다.

### Review closure: independently readable A7 proof (2026-10-07)

Future A7 PASS bundles seal `recovered_policy`, `safe_state`, `recovered_commit` and
`recovered_state` in `policy-and-consent.json`. The safe state is captured before retry;
the recovered state contains exactly one durable consent record, state transition and
completion event matching the recovered policy. Retry attempts/effects are tagged
`recovery_stage=AFTER_RETRY`; fault-phase attempts/effects use `BEFORE_RETRY` and remain
the only inputs to A6's denial/zero-effect check. The field is optional for historical rows.

The recovered lane's events and edges are sealed in the existing causal streams. Verification
recomputes the normal-order judge from these facts, checks Run/lane/subject identity, and
requires all three retry paths and target start/result effects. A7 summary flags alone are
insufficient. Missing consent, effects or causal proof fails verification even when the
manifest correctly seals the remaining bytes. Historical A7 FAIL/INCONCLUSIVE bundles do
not require new PASS evidence and are not rewritten.

`restore_timing` records the scenario's restore budget and the cumulative time spent removing
owned faults/overlays, checking the pre-retry safe state and performing final teardown.
Normal retry and processing time belongs to the Run budget, not the restore budget.
Cleanup exceeding the restore budget still fails closed and blocks the target.

## Integrity

모든 artifact는 상대 경로, SHA-256, byte size, MIME type, capture time, redaction profile을 가진다. manifest
seal 이후 파일 추가·삭제·변경은 verify 실패다. parent bundle의 manifest digest는 child retest 전후에
같아야 한다.

## Redaction

검출 시 verify 실패:

- bearer/cookie/password/access key
- presigned query credential
- applicant email/name, answer text, document text
- report narrative와 model prompt
- absolute user-specific filesystem path

허용:

- synthetic UUID, status, event type/version, count, hash
- policy version/content digest/purpose code
- repo-relative source locator
- sanitized local endpoint host와 environment kind

## Conflict rules

시간에 따른 baseline→injected→recovered 값 변화는 충돌이 아니다. 같은 Run/lane/phase/step/attempt/key의
동일 사실을 서로 다른 source가 모순되게 표현할 때만 `EVIDENCE_CONFLICT`다.

## Verification result

verify는 최소 다음을 반환한다.

- checked files/count
- checked EV3 set
- missing/mismatched/unregistered files
- broken lane/attempt/effect/causal/fault references
- secret/PII/path redaction violations
- bundle status

required fact를 읽을 수 없으면 hash가 맞더라도 assertion PASS를 복원하지 않는다.
