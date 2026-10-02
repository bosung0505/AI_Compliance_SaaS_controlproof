# Contract: ControlProof CLI — N-02 Profile

## Compatibility

- 기존 command와 exit code, `controlproof.cli.v1` machine envelope를 유지한다.
- additive field만 추가한다.
- H-03/E-03 profile 선택과 기존 sealed bundle read/verify 동작을 바꾸지 않는다.
- N-02는 명시적 `--profile N02_CONSENT_ORDER_V1`을 요구한다.

## Preflight

```powershell
python -m engine.cli preflight N-02 --profile N02_CONSENT_ORDER_V1 --target whyyou-local --json
```

성공 결과에는 다음이 포함된다.

```json
{
  "scenario_id": "N-02",
  "execution_profile": "N02_CONSENT_ORDER_V1",
  "environment_kind": "LOCAL_EMULATED",
  "aws_deployment_status": "NOT_RUN",
  "readiness": "READY",
  "operator_action": null,
  "protected_paths": ["DOCUMENT_ANALYSIS", "RECORDING", "AI_ASSESSMENT"],
  "claim_scope": "EXECUTED_SCENARIO_AND_EVIDENCE_ONLY",
  "unverified_scope": ["AWS", "N-01", "N-03"]
}
```

Preflight는 읽기 전용 capability와 설정 준비만 표시한다. 지원자 credential이 필요한 실제 정책
snapshot과 Run ID에 묶인 lane fixture digest는 subject를 시드한 Run에서만 확정한다. 이 두 값을
preflight의 실제 관찰 digest처럼 출력하지 않는다. Run bundle의 `policy_snapshot_digest`,
`lane_manifest_digest`, `path_capability_digest`가 실제 실행 증적이다. 정책 조회·lane 생성에
실패하면 PASS를 만들지 않는다.

preflight는 Run directory, subject row, marker 또는 event를 만들지 않는다.
`readiness != READY`이면 `operator_action`은 비어 있지 않아야 하며, 막힌 capability/source와 실행
담당자가 취할 조치를 비민감 문자열로 설명한다. 실제 credential 값은 포함하지 않는다.

## Run

```powershell
python -m engine.cli run N-02 --profile N02_CONSENT_ORDER_V1 --target whyou-local --label n02-initial --json
```

terminal projection:

```json
{
  "run_id": "uuid",
  "scenario_id": "N-02",
  "execution_profile": "N02_CONSENT_ORDER_V1",
  "run_state": "COMPLETED",
  "verdict": "FAIL",
  "evaluated_assertions": ["N02-A1", "N02-A2", "N02-A3", "N02-A4", "N02-A5", "N02-A6", "N02-A7"],
  "failed_assertions": ["N02-A3"],
  "inconclusive_assertions": [],
  "path_results": {
    "DOCUMENT_ANALYSIS": "PASS",
    "RECORDING": "FAIL",
    "AI_ASSESSMENT": "PASS"
  },
  "consent_fault_triggered": true,
  "environment_restore_status": "SUCCEEDED",
  "path_capability_digest": "sha256-hex",
  "policy_snapshot_digest": "sha256-hex",
  "lane_manifest_digest": "sha256-hex",
  "bundle_path": ".controlproof/runs/...",
  "claim_scope": "EXECUTED_SCENARIO_AND_EVIDENCE_ONLY",
  "unverified_scope": ["AWS", "N-01", "N-03"]
}
```

FAIL 예시는 정상적인 ControlProof 결과다. CLI가 보호조치 수정이나 자동 retest를 수행하지 않는다.

## Show

```powershell
python -m engine.cli show <run-id> --json
```

추가 projection:

- lane별 baseline kind와 fixture 여부/digest
- path별 entry boundary와 directness
- request response, prohibited new effect와 source status
- policy version/content digest/purpose match
- causal order와 끊긴 edge
- fault trigger와 rollback/restore/recovery
- assertion별 evidence refs
- parent/child relationship과 target change

PII, raw cookie/token/trace/idempotency key와 원문 report는 출력하지 않는다.

## Verify

```powershell
python -m engine.cli verify <run-id> --json
```

```json
{
  "run_id": "uuid",
  "execution_profile": "N02_CONSENT_ORDER_V1",
  "profile_contract": "controlproof.bundle-profile.spec003.v1",
  "bundle_status": "VERIFIED",
  "checked_evidence_requirements": ["EV3-01", "EV3-02", "EV3-03", "EV3-04", "EV3-05", "EV3-06", "EV3-07", "EV3-08", "EV3-09", "EV3-10"],
  "missing_files": [],
  "mismatched_files": [],
  "unregistered_files": []
}
```

verify는 read-only다. 적용 EV3 하나라도 없거나 hash/reference가 맞지 않으면 exit 5다.

## Retest

```powershell
python -m engine.cli retest <parent-run-id> --target whyou-local --label n02-after-fix --json
```

- parent scenario/profile을 그대로 상속한다.
- parent bundle verify와 terminal state를 요구한다.
- 새 subject set과 새 Run/bundle을 만든다.
- parent 파일은 수정하지 않는다.
- scenario, target, path capability, policy와 fixture digest 차이를 `retest-diff.json`에 기록한다.
- unresolved restore/manual cleanup가 있으면 시작하지 않는다.

## Exit codes

기존 계약을 유지한다.

| Code | Meaning |
|---:|---|
| 0 | command success 또는 PASS |
| 1 | usage/profile/config error |
| 2 | readiness not READY; Run 없음 |
| 3 | completed FAIL |
| 4 | INCONCLUSIVE |
| 5 | bundle integrity failure |
| 6 | RESTORE_FAILED/manual cleanup |

## Claim boundary

모든 `run`과 `show`는 다음 의미를 표시한다.

> 이 결과는 로컬 환경에서 실행한 N-02 경로와 확보한 증적에 한정되며, N-01·N-03, 실제 AWS 또는
> 법적 준수 전체를 인증하거나 보증하지 않습니다.
