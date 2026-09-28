# Contract: ControlProof CLI — Spec 002 profiles

## 1. Compatibility

- 실행 진입점과 exit code는 Spec 001의 `python -m engine.cli` 계약을 유지한다.
- machine envelope는 `schema_version=controlproof.cli.v1`을 유지하고 필드를 additive하게 확장한다.
- 기존 `run H-03`은 `H03_MINIMAL_V1`으로 해석돼 기존 동작을 보존한다.
- Spec 002 실행은 `--profile`로 명시적으로 선택한다. scenario 파일 경로나 fault variant를 CLI에서
  임의로 덮어쓸 수 없다.
- `--production`, `--skip-restore`, raw credential 옵션은 제공하지 않는다.

## 2. Exit codes

| Code | Meaning |
|---:|---|
| 0 | command success; `run`/`retest` verdict PASS |
| 1 | CLI usage, profile mismatch, or configuration error |
| 2 | readiness is not READY; no Run created |
| 3 | completed Run verdict FAIL |
| 4 | completed/terminated Run verdict INCONCLUSIVE |
| 5 | bundle integrity verification failed |
| 6 | restore failed or manual cleanup required |

## 3. Profile selection

| Scenario | `--profile` | Fault variant |
|---|---|---|
| H-03 | `H03_DLQ_V2` | `BEFORE_RESULT_DURABLE` |
| E-03 | `E03_BEFORE_V2` | `BEFORE_RESULT_DURABLE` |
| E-03 | `E03_AFTER_V2` | `AFTER_RESULT_DURABLE_BEFORE_COMPLETION` |

scenario와 profile이 맞지 않으면 exit 1이다. E-03에서 `--profile`을 생략하면 두 variant 중 하나를
추정하지 않고 사용법 오류를 반환한다.

## 4. `preflight`

```powershell
python -m engine.cli preflight H-03 --profile H03_DLQ_V2 --target whyyou-local --json
python -m engine.cli preflight E-03 --profile E03_BEFORE_V2 --target whyyou-local --json
python -m engine.cli preflight E-03 --profile E03_AFTER_V2 --target whyyou-local --json
```

preflight는 Run directory를 만들지 않는다. 다음을 모두 확인한다.

- ControlProof와 WhyYou checkout identity·dirty 상태
- Docker services, WhyYou API·worker·company console health
- 모든 endpoint가 loopback이고 queue endpoint가 LocalStack임
- queue/DLQ redrive target, max receive count 3, visibility timeout 5초
- profile의 marker variant, observer, decision path, restore capability
- deterministic model/embedding fixture ID와 digest
- 필요한 DB/API/browser 접근과 test-only guard

성공 예시는 다음과 같다.

```json
{
  "schema_version": "controlproof.cli.v1",
  "command": "preflight",
  "scenario_id": "E-03",
  "execution_profile": "E03_AFTER_V2",
  "fault_variant": "AFTER_RESULT_DURABLE_BEFORE_COMPLETION",
  "claim_scope": "EXECUTED_SCENARIO_AND_EVIDENCE_ONLY",
  "target_id": "whyyou-local",
  "environment_kind": "LOCAL_EMULATED",
  "aws_deployment_status": "NOT_RUN",
  "readiness": "READY",
  "checks": [],
  "unverified_scope": ["AWS_SQS", "AWS_ECS", "AWS_IAM", "AWS_CLOUDWATCH", "AWS_NETWORK"],
  "checked_at": "2026-09-28T00:00:00Z"
}
```

실제 queue attribute가 timing policy와 다르거나 AFTER hook이 없으면 시간을 늘리거나 다른 variant로
대체하지 않고 `RUNNER_NOT_READY`와 exit 2를 반환한다. 접근권한 부족은 `ACCESS_BLOCKED`, 대상 기능
자체가 없을 때만 `NO_TEST_TARGET`이다.

## 5. `run`

```powershell
python -m engine.cli run H-03 --profile H03_DLQ_V2 --target whyyou-local --label h03-initial --json
python -m engine.cli run E-03 --profile E03_BEFORE_V2 --target whyyou-local --label e03-before-initial --json
python -m engine.cli run E-03 --profile E03_AFTER_V2 --target whyyou-local --label e03-after-initial --json
```

Spec 001 옵션에 `--profile`만 추가한다. `--fault-variant`, `--max-receive-count`, `--queue-url`은
받지 않는다. profile snapshot이 이를 소유한다.

terminal output은 다음 additive 필드를 포함한다.

```json
{
  "schema_version": "controlproof.cli.v1",
  "command": "run",
  "run_id": "0199...",
  "scenario_id": "E-03",
  "execution_profile": "E03_AFTER_V2",
  "fault_variant": "AFTER_RESULT_DURABLE_BEFORE_COMPLETION",
  "target_id": "whyyou-local",
  "environment_kind": "LOCAL_EMULATED",
  "aws_deployment_status": "NOT_RUN",
  "run_state": "COMPLETED",
  "verdict": "PASS",
  "evaluated_assertions": ["E03-A1", "E03-A5", "E03-A6", "E03-A8"],
  "remaining_variant_coverage": ["E03-A2", "E03-A3", "E03-A4", "E03-A7"],
  "failed_assertions": [],
  "inconclusive_assertions": [],
  "environment_restore_status": "SUCCEEDED",
  "bundle_path": ".controlproof/runs/0199...",
  "unverified_scope": ["AWS_SQS", "AWS_ECS", "AWS_IAM", "AWS_CLOUDWATCH", "AWS_NETWORK"]
}
```

`remaining_variant_coverage`는 현재 Run의 실패나 INCONCLUSIVE가 아니다. E-03 전체 범위를 설명하려면
BEFORE와 AFTER 두 Run을 각각 보여줘야 하며 CLI는 둘을 하나의 verdict로 합치지 않는다.

모든 `run`·`show` JSON은 `claim_scope=EXECUTED_SCENARIO_AND_EVIDENCE_ONLY`와
`unverified_scope`를 포함한다. 사람이 읽는 출력은 다음 의미를 명시해야 한다.

> 이 결과는 실행된 시나리오와 확보한 증적에 한정되며 법적 준수 전체를 인증하거나 보증하지 않습니다.

같은 의미의 번역은 허용하지만 전체 법적 준수, 인증 또는 보증을 암시하는 표현은 허용하지 않는다.

## 6. `show`

```powershell
python -m engine.cli show 0199... --json
```

Spec 001 summary에 다음을 추가한다.

- execution profile과 fault boundary
- `claim_scope=EXECUTED_SCENARIO_AND_EVIDENCE_ONLY`와 법적 준수 전체 비인증·비보증 문구
- 환경 종류, AWS `NOT_RUN`, 미검증 범위
- source event와 delivery attempt/DLQ 또는 duplicate-ack 계보
- 적용 assertion과 다른 profile의 잔여 범위
- effect identity별 baseline/injected/recovered 논리 건수
- restore와 redrive 결과

원문 message body, 전체 DB row, token, 실제 지원자 정보는 출력하지 않는다.

## 7. `verify`

```powershell
python -m engine.cli verify 0199... --json
```

```json
{
  "schema_version": "controlproof.cli.v1",
  "command": "verify",
  "run_id": "0199...",
  "execution_profile": "E03_AFTER_V2",
  "profile_contract": "controlproof.bundle-profile.spec002.v1",
  "bundle_status": "VERIFIED",
  "checked_files": 24,
  "checked_evidence_requirements": ["EV2-01", "EV2-02", "EV2-03", "EV2-04", "EV2-09", "EV2-10", "EV2-12"],
  "missing_files": [],
  "mismatched_files": [],
  "verified_at": "2026-09-28T00:03:00Z"
}
```

required EV2 집합은 profile에서 계산한다. 비적용 EV2를 누락으로 보지 않으며, 적용 EV2 하나라도
누락·변조되면 exit 5다. 검증은 read-only다.

## 8. `retest`

```powershell
python -m engine.cli retest 0199... --target whyyou-local --label after-fix --json
```

- parent의 scenario, profile, fault variant를 그대로 상속하며 override하지 않는다.
- parent가 terminal이고 bundle verify가 성공해야 한다.
- 새 Run·bundle을 만들고 parent bundle은 수정하지 않는다.
- target/environment/queue/scenario digest 차이를 `retest-diff.json`에 기록한다.
- parent의 AWS 상태가 `NOT_RUN`이면 child도 실제 cloud target을 실행하지 않는 한 `NOT_RUN`이다.
- 안전한 redrive 또는 cleanup이 확인되지 않으면 retest를 시작하지 않는다.

최초 실행이 FAIL이어도 정상적인 제품 결과다. 수정 전 parent를 봉인하고, WhyYou 수정은 개인
브랜치에서 수행한 뒤 이 명령으로 별도의 PASS/FAIL 결과를 만든다.

## 9. Cleanup and operational safety

Ctrl+C, timeout, 내부 오류에서도 marker 해제와 worker safe-state 확인을 먼저 수행한다. 환경 복구 성공
후 업무 결과만 미복구면 verdict는 해당 assertion 규칙을 따르고, marker 또는 worker 안전성 확인 실패는
`RESTORE_FAILED`/INCONCLUSIVE/exit 6이다. 수동 정리는 Spec 001 `cleanup-confirm` 계약을 재사용한다.
