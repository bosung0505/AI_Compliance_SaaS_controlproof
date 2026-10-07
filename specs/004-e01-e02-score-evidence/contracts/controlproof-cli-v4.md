# Contract: ControlProof CLI — E-01·E-02 Profiles

## Compatibility

- 기존 command, exit code, `controlproof.cli.v1` machine envelope를 유지하고 additive field만 추가한다.
- H-03·E-03·N-02 profile 선택과 기존 봉인 bundle read/verify 동작을 바꾸지 않는다.
- E-01은 `--profile E01_CITATION_EVIDENCE_V1`, E-02는 `--profile E02_SCORING_FREEZE_V1`을 명시해야 한다. 없으면
  `PROFILE_REQUIRED`, 다른 시나리오 profile이면 `PROFILE_MISMATCH`.

## Preflight

```powershell
python -m engine.cli preflight E-01 --profile E01_CITATION_EVIDENCE_V1 --target whyyou-local --json
python -m engine.cli preflight E-02 --profile E02_SCORING_FREEZE_V1 --target whyyou-local --json
```

성공 결과(예: E-02):

```json
{
  "scenario_id": "E-02",
  "execution_profile": "E02_SCORING_FREEZE_V1",
  "environment_kind": "LOCAL_EMULATED",
  "aws_deployment_status": "NOT_RUN",
  "readiness": "READY",
  "operator_action": null,
  "model_fixture_id": "spec004-report-v1",
  "scoring_rule_source": {"status": "MATCH", "pinned_blobs": 2},
  "capabilities": {"ready": 16, "required": 16},
  "claim_scope": "EXECUTED_SCENARIO_AND_EVIDENCE_ONLY",
  "unverified_scope": ["AWS", "N-01", "N-03"],
  "limitations": ["FIXTURE_INTERVIEW_INPUT", "EXTERNAL_AI_BLOCKED", "FIXED_MODEL_SUBSTITUTE"]
}
```

E-01 capability 수는 18개(공통 12 + 6), E-02는 16개(공통 12 + 4)다. preflight는 Run directory, subject row, 버전, 보고서
요청을 만들지 않는다. `readiness != READY`이면 `operator_action`은 비민감 조치 문자열이다. 대표 사유:

| 상황 | readiness | operator_action 요지 |
|---|---|---|
| 고정 모델이 `spec004-report-v1`이 아님 | `RUNNER_NOT_READY` | API·작업자를 Spec 004 fixture로 재기동 |
| emission observer root 미설정·불일치 | `RUNNER_NOT_READY` | 같은 observer root로 API·작업자 재기동 |
| scoring 원본 blob 불일치 | `RUNNER_NOT_READY` | 사본 갱신 또는 기준 checkout 확인 |
| DB/API 접근 불가 | `ACCESS_BLOCKED` | 막힌 source와 권한 범주만 |
| 차단 파일 존재 | `RUNNER_NOT_READY` | `cleanup-confirm` 절차 |

## Run

```powershell
python -m engine.cli run E-01 --profile E01_CITATION_EVIDENCE_V1 --target whyyou-local --label e01-initial --json
python -m engine.cli run E-02 --profile E02_SCORING_FREEZE_V1 --target whyyou-local --label e02-initial --json
```

E-01 terminal projection 예:

```json
{
  "run_id": "uuid",
  "scenario_id": "E-01",
  "execution_profile": "E01_CITATION_EVIDENCE_V1",
  "run_state": "COMPLETED",
  "verdict": "FAIL",
  "evaluated_assertions": ["E01-A1", "E01-A2", "E01-A3", "E01-A4"],
  "failed_assertions": ["E01-A3"],
  "inconclusive_assertions": [],
  "citation_modes": {"VALID": "STORED_VALID", "EMPTY": "EMPTIED", "NONEXISTENT": "EMPTIED",
                     "OTHER_APPLICANT": "EMPTIED", "OTHER_CRITERION": "EMPTIED"},
  "evidence_removal": {"applied": true, "restored": true, "exposed_as_insufficient": false},
  "diagnostics": {"E01-D1": {"EMPTY": "AXIS_DROPPED", "NONEXISTENT": "SHOWN_AS_WRITTEN"}},
  "change_injection_restore_status": "SUCCEEDED",
  "model_fixture_id": "spec004-report-v1",
  "bundle_path": ".controlproof/runs/...",
  "claim_scope": "EXECUTED_SCENARIO_AND_EVIDENCE_ONLY",
  "unverified_scope": ["AWS", "N-01", "N-03"],
  "limitations": ["FIXTURE_INTERVIEW_INPUT", "EXTERNAL_AI_BLOCKED", "FIXED_MODEL_SUBSTITUTE"]
}
```

`unverified_scope`는 실행하지 않은 범위(Spec 003과 같은 의미), `limitations`는 실행한 범위 안의 격리 한계(SC-007)다.

위 FAIL 값은 형식 예시이며 예상 결과를 주장하지 않는다. E-02 projection은 `versions`(v1·v2 ID·번호·상태),
`first_report_unchanged`, `second_report_bound_to`, `recompute`(보고서별 비교 대상 다섯 개 equal 여부)를 가진다.
CLI는 보호조치 수정이나 자동 retest를 하지 않는다.

## Show

```powershell
python -m engine.cli show <run-id> --json
```

추가 projection: lane·기준 모드·점수 표식, 모드별 emission과 저장 결과, 제거 전·후·복원 후 보고서·타임라인 차이(점수·
지표·Evidence 필드), 진단 노출, 버전 V1·V2와 두 보고서의 묶임, 재계산 비교표, 변경 주입 생명주기와 복구, assertion별
evidence refs, parent/child 관계. 원문 텍스트·token·cookie·playback URL은 출력하지 않는다.

## Verify

```powershell
python -m engine.cli verify <run-id> --json
```

```json
{
  "run_id": "uuid",
  "execution_profile": "E01_CITATION_EVIDENCE_V1",
  "profile_contract": "controlproof.bundle-profile.spec004.v1",
  "bundle_status": "VERIFIED",
  "checked_evidence_requirements": ["EV4-01", "EV4-02", "EV4-03", "EV4-04", "EV4-05", "EV4-09", "EV4-10"],
  "missing_files": [],
  "mismatched_files": [],
  "unregistered_files": []
}
```

verify는 read-only다. E-02는 재계산을 다시 실행해 결과가 다르면 exit 5다.

## Retest

```powershell
python -m engine.cli retest <parent-run-id> --target whyyou-local --label e01-after-fix --json
```

- parent scenario/profile을 그대로 상속하고 parent bundle verify와 terminal state를 요구한다.
- 새 lane·subject·직무·버전을 만들고 parent 파일을 수정하지 않는다.
- scenario, target(WhyYou 수정 commit 포함), fixture, scoring 원본 blob 차이를 `retest-diff.json`에 기록한다.
- 미해결 차단·수동 정리가 있으면 시작하지 않는다.

## Cleanup-confirm

Spec 003과 같다. subject는 `e01-citation-evidence` 또는 `e02-scoring-freeze`이며, 증거 파일은 차단된 Run의 Run 소유
행(자막 구간·축 JSON·직무)이 복원 또는 제거됐음을 읽기 전용으로 확인한 결과다.

## Exit codes

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

> 이 결과는 로컬 환경에서 fixture 면접 입력과 고정 모델 대체물로 실행한 E-01(또는 E-02) 경로와 확보한 증적에
> 한정되며, 실제 AI 모델 품질, 실제 AWS 또는 법적 준수 전체를 인증하거나 보증하지 않습니다.
