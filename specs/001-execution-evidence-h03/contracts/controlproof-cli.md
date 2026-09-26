# Contract: ControlProof CLI

**Version**: `v1`  
**Feature**: `001-execution-evidence-h03`

## 공통 규칙

- 실행 진입점: `python -m engine.cli`
- 사람용 기본 출력과 별개로 모든 명령은 `--json`을 지원한다.
- JSON stdout에는 비밀값·실제 개인정보를 포함하지 않는다.
- 오류 설명은 stderr, machine result는 stdout으로 분리한다.
- Run 생성 전 실패는 verdict를 만들지 않는다.
- exit code는 shell 자동화 계약이다.

| Exit code | 의미 |
|---:|---|
| 0 | 명령 성공. `run`의 경우 verdict가 PASS임 |
| 1 | 명령 사용/설정 오류 |
| 2 | readiness가 READY가 아님; Run 미생성 |
| 3 | Run 완료, verdict FAIL |
| 4 | Run 완료/종료, verdict INCONCLUSIVE |
| 5 | bundle integrity 검증 실패 |
| 6 | restore 실패 또는 수동 정리 필요 |

## `preflight`

```powershell
python -m engine.cli preflight H-03 --target whyyou-local --json
```

### 성공 출력

```json
{
  "schema_version": "controlproof.cli.v1",
  "command": "preflight",
  "scenario_id": "H-03",
  "scenario_version": "1.0.0",
  "target_id": "whyyou-local",
  "target_version": "target-snapshot:sha256:<64-lowercase-hex>",
  "target_snapshot": {
    "source_kind": "GIT_AND_CONTAINER",
    "git_commit_sha": "40-lowercase-hex",
    "git_dirty": false,
    "container_image_digests": {"backend": "sha256:<64-lowercase-hex>"},
    "openapi_digest": "64-lowercase-hex",
    "schema_migration_head": "migration-head",
    "schema_signature_digest": "64-lowercase-hex",
    "model_fixture_id": "h03-report-v1",
    "model_fixture_digest": "64-lowercase-hex"
  },
  "model_fixture_id": "h03-report-v1",
  "model_fixture_digest": "64-lowercase-hex",
  "implementation_status": "IMPLEMENTED",
  "readiness": "READY",
  "checks": [
    {
      "capability": "reporting.status.read",
      "status": "READY",
      "detail": "GET report contract and company credential available"
    }
  ],
  "checked_at": "2026-09-24T00:00:00Z"
}
```

### READY가 아닌 출력

```json
{
  "schema_version": "controlproof.cli.v1",
  "command": "preflight",
  "scenario_id": "H-03",
  "target_id": "whyyou-local",
  "implementation_status": "IMPLEMENTED",
  "readiness": "RUNNER_NOT_READY",
  "checks": [
    {
      "capability": "reporting.fault.inject",
      "status": "RUNNER_NOT_READY",
      "detail": "test-only reporting fault hook is not enabled",
      "operator_action": "enable the hook only in the isolated WhyYou test profile"
    }
  ],
  "checked_at": "2026-09-24T00:00:00Z"
}
```

대상 reporting API가 존재하고 fault hook, shared trigger receipt 또는 deterministic model substitute만 없으면 `NO_TEST_TARGET`가 아니라 `RUNNER_NOT_READY`를 반환해야 한다.
대상 기능이 존재할 때 `implementation_status=PARTIAL|NOT_IMPLEMENTED`도 `RUNNER_NOT_READY`다. 대상 기능 자체가 없으면 구현 상태와 독립적으로 `NO_TEST_TARGET`가 우선하며 어떤 경우에도 Run은 생성하지 않는다.

## `run`

```powershell
python -m engine.cli run H-03 --target whyyou-local --label first-h03 --json
```

### 옵션

| 옵션 | 필수 | 설명 |
|---|---|---|
| `SCENARIO_ID` | yes | `H-03` |
| `--target` | yes | adapter 설정 ID |
| `--label` | no | 비식별 실행 label |
| `--operator` | no | 기본 `local-operator` |
| `--run-root` | no | 기본 `.controlproof/runs` |
| `--json` | no | machine output |

`--skip-restore`, `--production`, raw DB password 인자는 제공하지 않는다.

### terminal 출력

```json
{
  "schema_version": "controlproof.cli.v1",
  "command": "run",
  "run_id": "0199...",
  "scenario_id": "H-03",
  "scenario_version": "1.0.0",
  "target_id": "whyyou-local",
  "target_version": "target-snapshot:sha256:<64-lowercase-hex>",
  "model_fixture_id": "h03-report-v1",
  "model_fixture_digest": "64-lowercase-hex",
  "run_state": "COMPLETED",
  "implementation_status": "IMPLEMENTED",
  "verdict": "FAIL",
  "reason_code": null,
  "summary": "리포트 생성 장애가 담당자 화면에서 기한 내 실패로 드러나지 않았습니다.",
  "failed_assertions": ["H03-A2"],
  "inconclusive_assertions": [],
  "environment_restore_status": "SUCCEEDED",
  "report_processing_recovery": "FAILED",
  "bundle_path": ".controlproof/runs/0199...",
  "started_at": "2026-09-24T00:00:00Z",
  "ended_at": "2026-09-24T00:02:00Z"
}
```

Run 시작 뒤 Ctrl+C 또는 내부 오류가 발생해도 restore를 먼저 수행한다. marker 비활성·worker 정상 확인으로 환경 복구가 성공하면 중단 Run은 `ABORTED`/INCONCLUSIVE이고, 환경 복구 실패는 `RESTORE_FAILED`/INCONCLUSIVE와 exit 6이다. `report_processing_recovery=FAILED|TIMEOUT`은 별도 finding이며 그 자체로 환경 복구 실패나 exit 6을 만들지 않는다.

## `show`

```powershell
python -m engine.cli show 0199... --json
```

Run summary, 6개 assertion, missing evidence, finding, restore 결과, parent/child 관계를 출력한다. artifact 원문은 기본 출력하지 않고 상대 경로와 hash만 보여준다.

## `verify`

```powershell
python -m engine.cli verify 0199... --json
```

```json
{
  "schema_version": "controlproof.cli.v1",
  "command": "verify",
  "run_id": "0199...",
  "bundle_status": "VERIFIED",
  "checked_files": 17,
  "missing_files": [],
  "mismatched_files": [],
  "verified_at": "2026-09-24T00:03:00Z"
}
```

하나라도 없거나 hash가 다르면 exit 5다. 기존 manifest를 수정하지 않는다.

## `retest`

```powershell
python -m engine.cli retest 0199... --target whyyou-local --label after-fix --json
```

- parent가 terminal이고 bundle verify가 성공해야 한다.
- 새 `run_id`를 생성한다.
- child `run.json.parent_run_id`에 parent를 기록한다.
- parent bundle은 읽기 전용으로 열고 어떤 파일도 수정하지 않는다.
- target/scenario/config 차이를 `retest-diff.json`에 저장한다. TargetSnapshot digest가 다르면 변경된 JSON field path와 before/after digest 또는 비민감 값을 함께 기록한다.

출력은 `run`과 같고 `parent_run_id`를 추가한다.

## `cleanup-confirm`

restore 실패 뒤 운영자가 WhyYou 환경을 수동 확인한 경우에만 사용한다.

```powershell
python -m engine.cli cleanup-confirm --target whyyou-local --subject candidate-01 --evidence cleanup-note.json --json
```

- 단순 `--force`는 지원하지 않는다.
- adapter가 marker 부재와 target 안전 상태를 다시 확인해야 block을 해제한다.
- 수동 evidence 파일도 마스킹·hash 후 별도 maintenance record에 저장한다.

## 출력 안정성

`schema_version` major가 같으면 필드 제거·의미 변경을 금지한다. 필드는 추가할 수 있다. 사람이 읽는 Korean detail은 비교 대상이 아니며 자동화는 enum, ID, code를 사용한다.

`run`, `show`, `retest`의 바깥 machine envelope는 항상
`schema_version=controlproof.cli.v1`을 유지한다. 내부 review projection의 버전은
`projection_schema_version=controlproof.review.v1`으로 별도 제공하며 바깥 `schema_version`이나
`command`를 덮어쓸 수 없다.
