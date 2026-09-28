# Contract: Scenario Profile v2

## Compatibility

- `scenarios/H-03.yaml`은 Spec 001 v1 계약을 그대로 유지한다.
- v2 profile은 `schema_version: controlproof.scenario.v2`를 선언한다.
- 같은 `scenario_id`를 가진 여러 파일은 허용하지만 `(scenario_id, version, execution_profile)`은
  유일해야 한다.
- v1 loader·bundle·retest는 v2 추가 필드가 없어도 계속 동작해야 한다.

## Required top-level fields

```yaml
schema_version: controlproof.scenario.v2
scenario_id: H-03
version: 2.0.0
execution_profile: H03_DLQ_V2
fault_variant: BEFORE_RESULT_DURABLE
title: reporting 재시도 소진과 결정 안전성
applicable_assertion_ids: [H03-A1, H03-A2, H03-A3, H03-A4, H03-A5, H03-A6, H03-A7, H03-A8, H03-A9]
required_capabilities: {}
preconditions: []
steps: []
assertions: []
required_evidence: []
timing_policy: {}
restore_policy: {}
observation_comparators: {}
source_requirements: []
allowed_model_fixtures: {}
excluded_scope: []
```

`fault_variant`, assertion 집합과 step 집합은 execution profile의 canonical contract와 일치해야 한다.
CLI 인자로 variant를 덮어쓸 수 없다.

## Canonical profiles

### `H03_DLQ_V2`

- scenario: `H-03`
- fault: `BEFORE_RESULT_DURABLE`
- assertions: H03-A1~A9
- required evidence: Spec 001 EV-01~EV-09 + EV2-01~EV2-09, EV2-12
- required decision paths:
  - `FINAL_DECISION`
  - `BATCH_MOVE_FINAL_ACCEPT`
  - `BATCH_MOVE_FINAL_REJECT`

### `E03_BEFORE_V2`

- scenario: `E-03`
- fault: `BEFORE_RESULT_DURABLE`
- assertions: E03-A1~A4, E03-A7, E03-A8
- required evidence: EV2-01~EV2-05, EV2-09~EV2-12
- decision replay: 같은 `Idempotency-Key`의 `FINAL_DECISION` 2회

### `E03_AFTER_V2`

- scenario: `E-03`
- fault: `AFTER_RESULT_DURABLE_BEFORE_COMPLETION`
- assertions: E03-A1, E03-A5, E03-A6, E03-A8
- required evidence: EV2-01~EV2-04, EV2-09, EV2-10, EV2-12

## Development-time partial verification

Canonical profile보다 먼저 구현되는 action pipeline이나 judge subset은 pytest에서 컴포넌트로 직접
호출한다. 이를 위한 별도 scenario profile, CLI option 또는 저장 가능한 subset verdict는 정의하지
않는다. 특히 `E03_BEFORE_V2`는 E03-A7과 필수 adapter composition까지 완료돼 runner에 등록되기 전에는
실행 가능한 profile이 아니며, E03-A1~A4/A8 테스트 성공을 profile PASS로 표시하거나 bundle로 seal할
수 없다.
- terminal DLQ evidence는 비적용이다. 이 profile이 DLQ를 만들면 예상 경계와 다른 것이므로
  assertion을 PASS로 만들 수 없다.

## Canonical action IDs

| Action | Adapter owner | Output purpose |
|---|---|---|
| `target.environment.read` | target | local/cloud claim boundary |
| `messaging.reporting.topology.read` | queue | redrive snapshot |
| `subject.pending_report.seed` | seed | synthetic subject |
| `state.baseline.read` | state/effect | baseline effects |
| `fault.reporting.apply` | fault | variant marker |
| `reporting.trigger` | seed | one logical domain event |
| `fault.reporting.effect.read` | fault | boundary receipt |
| `messaging.reporting.attempts.read` | queue/fault | attempt timeline |
| `messaging.reporting.dlq.read` | queue | terminal failure |
| `reporting.ui.observe` | browser | 담당자 visible state |
| `hiring.decision_path.attempt` | decision | path별 요청·응답 |
| `state.effects.read` | effect | report/decision effect snapshot |
| `fault.reporting.restore` | fault | marker clear and safe-state probe |
| `messaging.reporting.dlq.redrive` | queue | same domain event recovery |
| `reporting.duplicate_ack.read` | queue/fault | processed-message short circuit |
| `hiring.final_decision.replay` | decision | same-key decision replay |

Target route, DB table, queue URL과 selector는 YAML에 쓰지 않는다.

## Profile step order

### H03-DLQ

```text
environment → topology → seed → baseline → apply BEFORE → trigger
→ attempts/DLQ → UI/API state → three decision paths + post-state
→ restore marker → redrive → recovered state → seal/judge
```

### E03-BEFORE

```text
environment → topology → seed → baseline effects → apply BEFORE → trigger
→ attempts/DLQ → injected effect absence → restore marker → redrive
→ recovered reporting effects → same-key human decision replay
→ recovered decision effects → safe-state → seal/judge
```

### E03-AFTER

```text
environment → topology → seed → baseline effects → apply AFTER → trigger
→ commit/pre-ack boundary receipt → committed effects
→ redelivery duplicate-ack → final reporting effects
→ restore marker/safe-state → seal/judge
```

## Timing contract

```yaml
timing_policy:
  poll_seconds: 2
  dlq_deadline_seconds: 360
  duplicate_ack_deadline_seconds: 60
  environment_restore_deadline_seconds: 180
  run_deadline_seconds: 600
  stability_consecutive: 3
  stability_seconds: 4
  expected_queue:
    max_receive_count: 3
    visibility_timeout_seconds: 5
```

queue attribute가 expected 값과 다르면 시간을 늘려 추정 실행하지 않고 readiness 실패로 끝낸다.

## Validation rules

1. profile과 fault variant가 canonical mapping과 일치해야 한다.
2. applicable assertion ID와 YAML assertion ID는 정확히 같아야 한다.
3. assertion이 참조하는 observation/evidence는 선언돼 있어야 한다.
4. H-03과 E-03 assertion을 한 profile에 섞을 수 없다.
5. `restore_policy.mandatory`는 항상 true다.
6. RECOVERED의 restore/safe-state step은 `always_run: true`여야 한다.
7. AWS endpoint 또는 실제 credential은 scenario data에 포함할 수 없다.
8. `E03_AFTER_V2`는 DLQ 도달을 기대값으로 선언할 수 없다.
9. score threshold 또는 자동 채용 결과를 assertion input으로 선언할 수 없다.
10. scenario snapshot digest에는 profile, variant, timing과 assertion ownership을 모두 포함한다.

## Result projection

```json
{
  "scenario_id": "E-03",
  "execution_profile": "E03_AFTER_V2",
  "fault_variant": "AFTER_RESULT_DURABLE_BEFORE_COMPLETION",
  "verdict": "PASS",
  "evaluated_assertions": ["E03-A1", "E03-A5", "E03-A6", "E03-A8"],
  "remaining_variant_coverage": ["E03-A2", "E03-A3", "E03-A4", "E03-A7"],
  "environment_kind": "LOCAL_EMULATED",
  "aws_deployment_status": "NOT_RUN"
}
```

`remaining_variant_coverage`는 현재 Run의 INCONCLUSIVE가 아니라 다른 profile에서 검증할 범위다.
