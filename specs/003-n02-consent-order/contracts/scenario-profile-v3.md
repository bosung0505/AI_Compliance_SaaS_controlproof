# Contract: N-02 Scenario Profile v3

## Identity

- `schema_version`: `controlproof.scenario.v3`
- `scenario_id`: `N-02`
- `version`: `1.0.0`
- `execution_profile`: `N02_CONSENT_ORDER_V1`
- `bundle_profile_contract`: `controlproof.bundle-profile.spec003.v1`

## Canonical assertions

순서와 집합이 모두 고정된다.

```text
N02-A1
N02-A2
N02-A3
N02-A4
N02-A5
N02-A6
N02-A7
```

## Canonical evidence

```text
EV3-01 target/path/policy capability
EV3-02 policy received and consent committed
EV3-03 lane baseline and fixture descriptor
EV3-04 bypass/deep-boundary attempt
EV3-05 post-attempt protected effects
EV3-06 causal events and edges
EV3-07 consent fault marker and trigger receipt
EV3-08 failed-consent effects
EV3-09 restore and recovered flow
EV3-10 judgement and sealed manifest
```

## Canonical lanes

| Lane | Baseline | Purpose |
|---|---|---|
| `PRISTINE_BASELINE` | PRISTINE | N02-A1 |
| `DOCUMENT_BYPASS` | PRISTINE | N02-A2 |
| `RECORDING_BOUNDARY_PROBE` | PREREQUISITE_FIXTURE | N02-A3 |
| `ASSESSMENT_BOUNDARY_PROBE` | PREREQUISITE_FIXTURE | N02-A4 |
| `NORMAL_ORDER` | PRISTINE | N02-A5 |
| `CONSENT_FAULT_RECOVERY` | PRISTINE | N02-A6·A7 |

각 lane은 독립 subject를 사용하며 fault/recovery의 두 phase만 같은 subject를 유지한다.

## Required capabilities

```yaml
target.version.read: v1
target.environment.read: v1
consent.policy.read: v1
consent.commit.write: v1
consent.state.read: v1
n02.subjects.seed: v1
n02.subjects.teardown: v1
processing.paths.read: v1
processing.document.attempt: v1
processing.recording.attempt: v1
processing.assessment.attempt: v1
processing.effects.read: v1
processing.boundary.receipts.read: v1
consent.fault.inject: v1
consent.fault.receipt.read: v1
consent.fault.restore: v1
```

capability가 대상에 있으나 adapter가 실행·관찰하지 못하면 `RUNNER_NOT_READY`다. 접근이 차단되면
`ACCESS_BLOCKED`, 실제 처리 경계 자체가 없을 때만 `NO_TEST_TARGET`이다. AI assessment는 독립 HTTP
route가 없지만 실제 worker boundary가 있으므로 `NO_TEST_TARGET`이 아니다.

## Step contract

Scenario YAML에는 최소 다음 ordered step이 있어야 한다.

```text
capture-environment
capture-path-capabilities
seed-subject-lanes
capture-pristine-baseline
attempt-document-bypass
capture-document-effects
attempt-recording-boundary
capture-recording-effects
attempt-assessment-boundary
capture-assessment-effects
read-policy
commit-normal-consent
capture-normal-consent
run-normal-processing
capture-normal-causality
apply-consent-fault
attempt-faulted-consent
read-fault-trigger
capture-failed-consent-effects
restore-consent-fault          always_run
verify-safe-state              always_run
attempt-faulted-document-path
apply-fault-recording-overlay
attempt-faulted-recording-path
remove-fault-recording-overlay always_run
apply-fault-assessment-overlay
attempt-faulted-assessment-path
remove-fault-assessment-overlay always_run
verify-pristine-before-retry   always_run
retry-normal-consent
run-recovered-processing
capture-recovered-effects
teardown-subject-lanes         always_run
```

restore와 teardown은 예외, timeout, Ctrl+C 뒤에도 호출한다. marker가 한 번이라도 적용되면
`RESTORING`을 건너뛸 수 없다.

## Timing policy

```yaml
poll_seconds: 2
stability_consecutive: 3
stability_seconds: 4
fault_ttl_seconds: 600
environment_restore_deadline_seconds: 120
run_deadline_seconds: 540
bundle_verify_deadline_seconds: 60
```

Run과 bundle verify deadline을 합쳐 전체 600초 목표를 지킨다. CLI에서 임의 override하지 않는다.
변경은 scenario version 증가와 snapshot digest 변경을 요구한다.

## Validation rules

- assertion/evidence/lane/capability 집합은 canonical과 정확히 일치한다.
- recording probe fixture는 session/recording effect를 포함할 수 없다.
- assessment probe fixture는 report/event/processed effect를 포함할 수 없다.
- A2~A4는 attempt artifact와 post-effect artifact를 모두 요구한다.
- A5는 policy/consent와 causal event/edge를 모두 요구한다.
- A6는 marker apply가 아니라 matching trigger receipt를 요구한다.
- A6는 실패 직후 zero partial effect와 같은 subject의 세 path attempt를 요구한다. 임시 overlay는 시도 뒤
  제거되고 recovery 전 pristine digest로 복원돼야 한다.
- A7은 restore safe-state와 exactly-one recovered consent를 요구한다.
- allowed fixed model fixture ID/digest가 없으면 scenario는 유효하지 않다.
- N-01 viewport와 N-03 policy invalidation step은 포함할 수 없다.

## Verdict precedence

```text
RESTORE_FAILED → INCONCLUSIVE
direct prohibited effect → FAIL
same-dimension source contradiction → INCONCLUSIVE:EVIDENCE_CONFLICT
required evidence/causal edge unavailable → INCONCLUSIVE:INSUFFICIENT_EVIDENCE
all A1..A7 PASS + bundle VERIFIED → PASS
```

직접 FAIL은 다른 assertion의 부족 증적으로 숨기지 않는다.
