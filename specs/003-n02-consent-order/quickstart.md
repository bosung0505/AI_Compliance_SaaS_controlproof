# Quickstart: Spec 003 N-02 Local Actual Run

> 이 문서는 Plan 산출물이다. 아래 N-02 명령은 `$speckit-implement`가 완료된 뒤 실제로 사용할 계약이다.
> 현재 Analyze 완료만으로 실행기가 구현됐다고 해석하지 않는다. `$speckit-implement` 이후에 사용한다.

## 1. 목적과 주장 범위

이 절차는 WhyYou local/test 환경에서 다음을 재현한다.

1. 미동의 자료 분석 경계 우회
2. 미동의 녹화 심층 경계 probe
3. 미동의 AI 평가 worker 경계 probe
4. 정상 동의 뒤 실제 처리 순서
5. 동의 저장 중 실패와 전체 rollback
6. fault 제거 뒤 실패한 같은 subject의 세 처리 경로 차단과 임시 deep-probe overlay 제거
7. pristine 안전 상태 확인과 같은 subject의 정상 복구
8. N02-A1~A7 판정과 EV3-01~EV3-10 bundle 검증

결과의 공식 범위는 `EXECUTED_SCENARIO_AND_EVIDENCE_ONLY`다. 실제 AWS, N-01 화면 가시성, N-03 정책
변경·재동의, 법적 준수 전체를 검증하지 않는다.

## 2. 저장소 배치

두 저장소를 같은 상위 폴더 아래 둔다. 개인 절대 경로를 문서나 commit에 넣지 않는다.

```text
workspace/
├── AI_Compliance_SaaS_controlproof/
└── gbsa_aws/
```

PowerShell 예시:

```powershell
$ControlProofRoot = (Resolve-Path .).Path
$WhyYouRoot = (Resolve-Path ..\gbsa_aws).Path
```

명령은 ControlProof 저장소 루트에서 실행한다.

## 3. 브랜치와 안전 확인

```powershell
git branch --show-current
git status --short
git -C $WhyYouRoot branch --show-current
git -C $WhyYouRoot status --short
```

요구 조건:

- ControlProof는 Spec 003 구현 branch이며 clean
- WhyYou는 `main`/`master`가 아닌 개인 N-02 branch이며 clean
- WhyYou branch는 `bosung/controlproof-h03-integration`의 검증 기반을 포함
- 실제 지원자·운영 credential을 사용하지 않음

WhyYou `main`에는 ControlProof 변경을 직접 push하지 않는다.

## 4. 환경 준비

ControlProof:

```powershell
python3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

`.env.example`을 참고해 local value를 session environment에 넣는다. 최소 의미는 다음과 같다.

```text
CONTROLPROOF_TARGET_ID=whyyou-local
CONTROLPROOF_ENVIRONMENT_KIND=LOCAL_EMULATED
CONTROLPROOF_AWS_DEPLOYMENT_STATUS=NOT_RUN
CONTROLPROOF_EXTERNAL_AI_ALLOWED=false
CONTROLPROOF_TEST_HOOKS_ENABLED=true
CONTROLPROOF_OBSERVER_ENABLED=true
WHYYOU_REPO_PATH=../gbsa_aws
WHYYOU_BASE_URL=http://localhost:8080
WHYYOU_CONSOLE_URL=http://localhost:5173
WHYYOU_AWS_ENDPOINT_URL=http://localhost:4566
```

실제 token/password는 shell 또는 승인된 secret store에만 두며 파일에 commit하지 않는다.

WhyYou local stack은 WhyYou 저장소의 현재 Docker 실행 문서를 따른다. 요구 service:

- API
- PostgreSQL
- LocalStack S3/SQS
- analysis/media/reporting worker
- fixed model/embedder substitute

company console/browser는 N-02 verdict에 필수 아니다.

## 5. 정적·자동 회귀

ControlProof:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest
```

WhyYou N-02 관련 gate는 WhyYou virtual environment에서 실행한다. 정확한 test path는 Tasks/구현에서
고정하지만 최소 범위는 다음을 포함한다.

- consent policy와 transaction rollback
- submission consent gate
- recording/assessment boundary characterization 또는 regression
- marker/observer local-only safety
- fixed model health

legacy cross-module suite 전체가 collection되는 것을 N-02 선행조건으로 삼지 않는다. 어떤 test를
실행했고 무엇이 legacy harness로 제외됐는지는 Validation에 정확히 기록한다.

## 6. Preflight

```powershell
.\.venv\Scripts\python.exe -m engine.cli preflight N-02 `
  --profile N02_CONSENT_ORDER_V1 `
  --target whyyou-local `
  --json
```

`readiness=READY` 전에 Run을 시작하지 않는다. 다음을 확인한다.

- 두 source snapshot과 clean/non-main 상태
- local-only API/DB/LocalStack
- external AI disabled, fixed fixture identity
- policy version/digest/purpose set
- canonical six-lane seed/teardown
- document/recording/assessment path와 effect observer
- consent fault apply/receipt/restore
- worker health

`READY`가 아니면 `operator_action`의 비민감 조치를 먼저 해결한다. preflight 전후에 Run directory,
subject row, marker와 event가 새로 생기면 계약 위반이므로 Run을 시작하지 않는다.

`RUNNER_NOT_READY`는 WhyYou FAIL이 아니다. 빠진 adapter/hook/fixture를 구현한 뒤 preflight를 다시 한다.

원본 로컬 DB에 미처리 outbox 이벤트가 남아 있다면 그 DB에 작업자를 바로 연결하지 않는다. 새로 마이그레이션한
로컬 DB와 전용 LocalStack 큐를 준비하고 API·모든 작업자·ControlProof가 같은 process-local 설정과
observer root를 사용하게 한다. WhyYou의 실행 중인 worker lock 같은 `.controlproof/` 생성 파일은
Git 대상 스냅샷의 미추적 파일 읽기를 방해할 수 있으므로 checkout 밖에 두거나 로컬 Git 제외 설정으로
분리한다. 이 조치는 추적 중인 소스 변경을 clean으로 만들지 않는다. 두 저장소의 실제 source gate가
clean일 때 새 preflight의 `READY`를 확인해야 한다.

## 7. 최초 actual Run

```powershell
.\.venv\Scripts\python.exe -m engine.cli run N-02 `
  --profile N02_CONSENT_ORDER_V1 `
  --target whyyou-local `
  --label n02-initial `
  --json
```

최초 Run이 FAIL이어도 자동 수정하거나 다시 실행해 덮어쓰지 않는다. 먼저 출력의 `run_id`와
`bundle_path`를 기록한다.

Run 시작 직전부터 아래 `verify` 완료까지 경과시간을 측정한다. 성공적인 Run은 540초 안에 terminal
상태에 도달하고 bundle verify까지 전체 600초 안에 끝나야 한다.

```powershell
.\.venv\Scripts\python.exe -m engine.cli show 15cef078-ee24-4f0e-91ef-381e0f7a1cc2 --json
.\.venv\Scripts\python.exe -m engine.cli verify 15cef078-ee24-4f0e-91ef-381e0f7a1cc2 --json
```

(`15cef078-ee24-4f0e-91ef-381e0f7a1cc2`는 T078 부모 Run의 실제 ID다. 새 Run은 출력의 `run_id`로 바꾼다.)

확인 항목:

- A1~A7 모두 평가 또는 명시적 INCONCLUSIVE
- A2~A4의 요청 결과와 post-effect delta가 함께 있음
- A5의 policy/consent와 causal edge가 있음
- A6의 matching trigger receipt와 partial effect 0건 여부
- A6에서 같은 failed-consent subject의 세 path가 모두 시도되고 임시 overlay가 제거됐는지
- A7의 restore와 recovered exactly-one effect
- manifest가 VERIFIED
- `LOCAL_EMULATED`, AWS `NOT_RUN`, N-01/N-03 미검증 표시

## 8. 최초 FAIL 처리

직접 위반이 확인되면 다음 순서를 지킨다.

1. parent bundle verify 결과와 manifest SHA-256을 Validation에 기록한다.
2. 어떤 path/assertion/effect가 FAIL인지 확인한다.
3. 원인을 `TARGET_CONTROL_DEFECT`, `RUNNER_OR_OBSERVER_DEFECT`, `RESTORE_OPERATOR_DEFECT`로 분류하고,
   실제 책임 경계의 최소 수정만 적용한다.
4. WhyYou 자동 회귀를 실행한다.
5. parent를 지정해 child retest를 만든다.

```powershell
.\.venv\Scripts\python.exe -m engine.cli retest 15cef078-ee24-4f0e-91ef-381e0f7a1cc2 `
  --target whyyou-local `
  --cleanup-evidence ..\gbsa_aws\.controlproof\n02-cleanup-evidence-375c2f2bfcaf.json `
  --label n02-after-fix `
  --json
```

이 명령은 T084에서 그대로 실행됐고(라벨 `n02-attempt3`), child `7b59237e-0a96-403a-9add-28b91011e950`를 만들었다.

```powershell
.\.venv\Scripts\python.exe -m engine.cli verify 15cef078-ee24-4f0e-91ef-381e0f7a1cc2 --json
.\.venv\Scripts\python.exe -m engine.cli verify 7b59237e-0a96-403a-9add-28b91011e950 --json
```

parent manifest digest는 수정 전과 같아야 한다. child의 target snapshot 차이가 WhyYou 수정 commit을
가리켜야 한다.

## 9. Restore failure

Run state가 `RESTORE_FAILED`이거나 exit 6이면 새 fault Run을 실행하지 않는다. 먼저 show 결과의
marker/subject와 operator action을 확인한다. N-02 대상의 marker/token 및 동의·처리 효과가 없는지
읽기 전용으로 확인하고, 해당 부모 Run·lane과 일치하는 증거로 `cleanup-confirm`을 실행한다. 이후
자식 retest에는 같은 증거 파일을 `--cleanup-evidence`로 전달한다. 파일 내용의 SHA-256이 정비 기록과
다르거나 새 차단 파일이 있으면 retest가 거부된다.

차단된 Run이 봉인 전에 중단됐거나 번들이 INVALID면 `cleanup-confirm`을 쓸 수 없다. 로컬 대상은
합성 데이터뿐이므로 WhyYou 컨테이너와 볼륨을 다시 만들고, 차단 파일과 그 Run의 receipt를 두
checkout 밖에 보관한 뒤 `validation.md`에 기록한다(ID-003-12, ID-003-14). 공유 대상에서는 절대
하지 않는다.

```powershell
.\.venv\Scripts\python.exe -m engine.cli cleanup-confirm `
  --target whyyou-local `
  --subject n02-consent-order `
  --evidence <n02-cleanup-evidence.json> `
  --json
```

marker를 수동으로 지울 때는 current Run과 invitation ID 및 resolved fault root를 확인해야 한다. 넓은
폴더나 다른 Run marker를 재귀 삭제하지 않는다.

## 10. Bundle과 일회성 부모 증거 인계

`.controlproof/runs/`는 Git 제외 대상이다. 한 PC의 bundle을 commit하면 독립 재현이 되지 않는다.
팀원은 같은 source SHA로 새 Run을 만들고 다음만 Validation에 기록한다.

예외적으로 2026-10-02에 사용자가 공개 Git 게시를 승인한 최초 부모
`15cef078-ee24-4f0e-91ef-381e0f7a1cc2`의 정확한 bundle과 정비 기록만 ControlProof
`003-n02-consent-order`에, 같은 부모의 cleanup 증거 JSON만 WhyYou
`bosung/controlproof-n02-integration`에 올렸다. 팀원은 두 브랜치를 pull한 뒤 별도 파일 복사 없이
기본 `.controlproof/runs` 위치에서 부모 `verify`를 실행하고 `--cleanup-evidence`에
`../gbsa_aws/.controlproof/n02-cleanup-evidence-375c2f2bfcaf.json`을 지정한다. manifest SHA-256은
`d2306f3cd6e2b15ce87d94e4844a2278c7ea3c0b3c052a2aac45e1bff8f2bc9b`, cleanup 증거
SHA-256은 `406a87bc88cf2f0ec0bcff1799f7ad4b8099937e507484d11ad9e3d801649eef`이어야 한다.
이 원본 전달은 T093의 독립 Run을 대신하지 않으며 이후 Run이나 진단 로그를 Git에 추가하라는
허가가 아니다.

- 실행자/환경 식별의 비민감 요약
- ControlProof와 WhyYou commit SHA
- Run ID, verdict, restore
- manifest SHA-256
- verify 결과

## 11. 완료 조건

Spec 003은 Plan이나 자동시험만으로 완료되지 않는다. 다음이 모두 필요하다.

- Tasks와 analyze 완료
- 구현과 자동 gate 통과
- preflight READY
- 최초 actual Run과 봉인 bundle
- 직접 FAIL이 있으면 최소 보완과 child Run
- 최종 A1~A7의 근거 있는 결과
- EV3-01~EV3-10 bundle VERIFIED
- restore safe-state
- validation·traceability·인수인계 갱신
- `$speckit-converge`

완료돼도 N-01/N-03, 실제 AWS, Spec 004/005는 자동 완료되지 않는다.
