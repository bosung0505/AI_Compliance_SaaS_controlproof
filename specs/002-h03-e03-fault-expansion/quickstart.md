# Quickstart: Spec 002 구현 후 로컬 검증 절차

이 문서는 지금 당장 완성된 기능을 실행한다는 뜻이 아니다. `tasks.md`에 따라 구현이 끝난 뒤,
`whyyou-local`에서 H-03 확장과 E-03 두 장애 경계를 같은 조건으로 재현하기 위한 검증 순서다.

## 1. 주장 범위

- 공식 target: `whyyou-local`
- 실행환경: `LOCAL_EMULATED`
- 검증 구성: Docker Desktop의 PostgreSQL·LocalStack·Mailpit + host의 WhyYou API·worker·company console
- AWS deployment status: `NOT_RUN`
- 검증하지 않는 범위: 실제 AWS SQS/ECS/IAM/CloudWatch, production network/traffic, 운영 credential

로컬 PASS는 WhyYou의 한 사이클과 ControlProof 증적·판정 동작을 검증할 뿐 AWS 운영환경 PASS가 아니다.
향후 cloud 환경을 다시 만들면 별도 target ID와 새 Run이 필요하다.

## 2. Branch and source prerequisites

```powershell
cd "C:\Users\aaaa2\AI 기본법\AI_Compliance_SaaS_controlproof"
git branch --show-current
git status --short

cd "C:\Users\aaaa2\AI 기본법\gbsa_aws"
git branch --show-current
git status --short
```

예상 branch는 다음과 같다.

- ControlProof: `002-h03-e03-fault-expansion`
- WhyYou: `bosung/controlproof-h03-integration` 계열 개인 branch

WhyYou 변경을 `main`에 직접 push하지 않는다. 실제 Run을 만들 때는 두 checkout 모두 clean이어야 한다.
구현 중 dirty 상태는 허용하지만 preflight는 Run 생성을 거부해야 한다.

## 3. Install ControlProof development dependencies

```powershell
cd "C:\Users\aaaa2\AI 기본법\AI_Compliance_SaaS_controlproof"
$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    uv venv --python 3.12 .venv
    uv pip install --python $python -e ".[dev]"
    & $python -m playwright install chromium
}
& $python --version
& $python -c "import pytest, ruff, pydantic, playwright; print('ControlProof dependencies: ready')"
& $python -m playwright install --list
```

이 저장소는 Windows Python launcher `py -3.12`의 존재를 가정하지 않는다. 기존 `.venv`가 있으면
build isolation을 다시 실행하지 않고 dependency와 browser 설치 상태만 확인한다. 새 환경을 만드는
최초 한 번은 package와 Chromium 다운로드를 위한 네트워크가 필요하다.

## 4. Configure WhyYou local-only test profile

WhyYou `.env`에는 비밀값을 문서나 bundle에 복사하지 않는다. 최소한 다음 의미가 충족돼야 한다.

```dotenv
APP_ENVIRONMENT=local
AWS_ENDPOINT_URL=http://localhost:4566
LOCAL_REPORTING_QUEUE_NAME=iep-reporting
SQS_REPORTING_MAX_RECEIVE_COUNT=3
SQS_REPORTING_VISIBILITY_TIMEOUT_SECONDS=5
RETRIEVAL_BACKEND=aurora
CONTROLPROOF_TEST_HOOKS_ENABLED=true
CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED=true
```

두 ControlProof flag는 local/test에서만 유효해야 하고 production-like environment에서는 시작 자체가
거부돼야 한다. Run/session/subject allowlist가 없는 marker도 적용되면 안 된다.

ControlProof CLI는 `.env`를 암묵적으로 읽지 않는다. WhyYou를 시작한 것과 **같은 로컬 설정을**
ControlProof 터미널에 다음처럼 가져오고, 이름이 다른 값만 명시적으로 매핑한다. 이 block은 값을
출력하지 않으며 현재 PowerShell process에만 보존한다.

```powershell
cd "C:\Users\aaaa2\AI 기본법\AI_Compliance_SaaS_controlproof"
$controlProofRepo = (Get-Location).Path
$whyYouRepo = (Resolve-Path -LiteralPath "..\gbsa_aws").Path
$whyYouEnv = Join-Path $whyYouRepo ".env"
foreach ($line in Get-Content -LiteralPath $whyYouEnv -Encoding UTF8) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith("#")) { continue }
    if ($trimmed -notmatch "^([^=]+)=(.*)$") { continue }
    $name = $matches[1].Trim()
    $value = $matches[2].Trim().Trim('"').Trim("'")
    [Environment]::SetEnvironmentVariable($name, $value, "Process")
}

# Codex sandbox처럼 파일 소유 계정과 실행 계정이 다른 경우에도 전역 git config는 바꾸지 않는다.
# 이 PowerShell process에서 정확히 이 두 저장소만 safe.directory로 전달한다.
$env:GIT_CONFIG_COUNT = "2"
$env:GIT_CONFIG_KEY_0 = "safe.directory"
$env:GIT_CONFIG_VALUE_0 = $controlProofRepo
$env:GIT_CONFIG_KEY_1 = "safe.directory"
$env:GIT_CONFIG_VALUE_1 = $whyYouRepo

$env:CONTROLPROOF_TARGET_ID = "whyyou-local"
$env:CONTROLPROOF_ENVIRONMENT_KIND = "LOCAL_EMULATED"
$env:CONTROLPROOF_AWS_DEPLOYMENT_STATUS = "NOT_RUN"
$env:CONTROLPROOF_RUN_ROOT = (Join-Path (Get-Location) ".controlproof\runs")
$env:CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED = "true"
$env:CONTROLPROOF_MODEL_FIXTURE_ID = "h03-report-v1"
$env:CONTROLPROOF_MODEL_FIXTURE_DIGEST = "ce09b95403b34e1390502c90f5c5edc518ddf65d38c8ce881617a37cac6d16b1"
$env:CONTROLPROOF_EMBEDDING_FIXTURE_ID = "h03-embedding-v1"
$env:CONTROLPROOF_EMBEDDING_FIXTURE_DIGEST = $env:CONTROLPROOF_MODEL_FIXTURE_DIGEST
$env:CONTROLPROOF_EXTERNAL_AI_ALLOWED = "false"
$env:WHYYOU_BASE_URL = "http://localhost:8080"
$env:WHYYOU_CONSOLE_URL = "http://localhost:5173"
$env:WHYYOU_DATABASE_URL = $env:DATABASE_URL
$env:WHYYOU_COMPANY_TOKEN = $env:LOCAL_COMPANY_ACCESS_TOKEN
$env:WHYYOU_COMPANY_ID = $env:LOCAL_COMPANY_ID
$env:WHYYOU_COMPANY_USER_ID = $env:LOCAL_COMPANY_USER_ID
# Python은 현재 ControlProof 작업 디렉터리를 기준으로 이 ASCII 상대 경로를 resolve한다.
# 한글이 포함된 절대 경로를 환경변수로 왕복시키지 않는다.
$env:WHYYOU_REPO_PATH = "..\gbsa_aws"
$env:WHYYOU_AWS_ENDPOINT_URL = "http://localhost:4566"
$env:WHYYOU_AWS_REGION = $env:AWS_REGION
$env:WHYYOU_REPORTING_QUEUE_NAME = "iep-reporting"
$env:WHYYOU_REPORTING_DLQ_NAME = "iep-reporting-dlq"
$env:WHYYOU_REPORTING_MAX_RECEIVE_COUNT = "3"
$env:WHYYOU_REPORTING_VISIBILITY_TIMEOUT_SECONDS = "5"
```

`CONTROLPROOF_FAULT_ROOT`는 WhyYou `.env`에서 가져온 동일한 절대 경로를 유지해야 한다. 두 프로세스가
서로 다른 marker/receipt 디렉터리를 보면 preflight 또는 실행이 실패하는 것이 정상이다.

## 5. Start the WhyYou local stack

WhyYou repository에서 터미널을 나눠 실행한다.

```powershell
cd "C:\Users\aaaa2\AI 기본법\gbsa_aws"
.\scripts\local.ps1 up
```

```powershell
cd "C:\Users\aaaa2\AI 기본법\gbsa_aws"
.\scripts\local.ps1 api
```

```powershell
cd "C:\Users\aaaa2\AI 기본법\gbsa_aws"
.\scripts\local.ps1 worker
```

```powershell
cd "C:\Users\aaaa2\AI 기본법\gbsa_aws"
.\scripts\local.ps1 company
```

Docker Desktop의 PostgreSQL·LocalStack·Mailpit과 host process의 health를 먼저 확인한다. 과거 남은
queue/message가 있으면 임의 삭제하지 말고 local reset 절차로 합성 시험환경을 새로 준비한다.

```powershell
cd "C:\Users\aaaa2\AI 기본법\gbsa_aws"
.\scripts\local.ps1 status
```

## 6. Run regression and contract tests

```powershell
cd "C:\Users\aaaa2\AI 기본법\AI_Compliance_SaaS_controlproof"
.\.venv\Scripts\python.exe -m pytest -q
```

```powershell
cd "C:\Users\aaaa2\AI 기본법\gbsa_aws"
uv run --cache-dir .uv-cache --no-sync pytest backend/tests/unit/shared/test_local_queue_topology.py backend/tests/unit/runtime/test_controlproof_reporting_fault.py backend/tests/unit/runtime/test_controlproof_model_substitute.py backend/tests/integration/test_worker_delivery.py backend/tests/integration/test_controlproof_fault_hook_safety.py -q
```

Spec 001 회귀, scenario/bundle/CLI contract, queue·fault hook 단위 시험이 모두 통과해야 실제 장애 Run을
시작한다.

## 7. Preflight all three profiles

```powershell
cd "C:\Users\aaaa2\AI 기본법\AI_Compliance_SaaS_controlproof"
.\.venv\Scripts\python.exe -m engine.cli preflight H-03 --profile H03_DLQ_V2 --target whyyou-local --json
.\.venv\Scripts\python.exe -m engine.cli preflight E-03 --profile E03_BEFORE_V2 --target whyyou-local --json
.\.venv\Scripts\python.exe -m engine.cli preflight E-03 --profile E03_AFTER_V2 --target whyyou-local --json
```

세 결과 모두 `READY`, `LOCAL_EMULATED`, AWS `NOT_RUN`이어야 한다. 하나라도 READY가 아니면 Run을
만들지 말고 `operator_action`을 해결한다. queue attribute가 다르면 대기시간을 늘려 우회하지 않는다.

## 8. Execute the initial Runs

각 Run은 새 합성 subject와 격리된 fault session을 쓴다.

```powershell
.\.venv\Scripts\python.exe -m engine.cli run H-03 --profile H03_DLQ_V2 --target whyyou-local --label h03-initial --json
.\.venv\Scripts\python.exe -m engine.cli run E-03 --profile E03_BEFORE_V2 --target whyyou-local --label e03-before-initial --json
.\.venv\Scripts\python.exe -m engine.cli run E-03 --profile E03_AFTER_V2 --target whyyou-local --label e03-after-initial --json
```

예상 총 제한은 profile당 10분이다. H03/BEFORE는 세 번 전달 뒤 DLQ, marker 복구, 안전한 redrive와
reporting 회복을 관찰한다. AFTER는 DB commit 후 ack만 한 번 떨어뜨리고 재전달에서 handler 재실행 없이
duplicate-ack 되는지 관찰한다.

최초 결과가 FAIL인 것은 시험 실패가 아니라 발견된 제품 결함일 수 있다. 원 bundle을 봉인하기 전에
WhyYou를 수정하거나 DB를 손으로 고치지 않는다.

## 9. Inspect and verify each Run

```powershell
.\.venv\Scripts\python.exe -m engine.cli show <RUN_ID> --json
.\.venv\Scripts\python.exe -m engine.cli verify <RUN_ID> --json
```

확인할 핵심은 다음과 같다.

- H03: 모든 최종 결정 경로가 report 부재를 우회하지 못했는가, DLQ와 담당자 실패 표시가 있는가
- E03 BEFORE: 장애 중 효과 0건, 복구 후 reporting 효과 각 1건, 같은 key의 사람 결정 효과 각 1건인가
- E03 AFTER: commit 경계 receipt가 있고 재전달 때 report/projection/processed marker가 중복되지 않는가
- 공통: marker 해제, worker 정상, environment/queue snapshot, AWS `NOT_RUN`, bundle verify 성공

E03 BEFORE PASS가 AFTER 미실행을 대신하지 않으며 그 반대도 같다.

## 10. Fix only after sealing FAIL

1. FAIL Run의 `verify`가 성공하는지 확인한다.
2. 실패 assertion, 실제 관찰값, 최소 원본 artifact를 기록한다.
3. WhyYou 개인 branch에서 확인된 결함만 수정한다.
4. 관련 unit/integration test를 추가한다.
5. WhyYou `main`에는 직접 push하지 않는다.

H03-A7 우회나 E03-A7 idempotency 결함처럼 최초 Run으로 입증된 사항만 보완한다. 담당자 실패 표시처럼
새 영속 상태가 필요한 변경은 제품 결정과 schema 변경을 별도 기록한다.

## 11. Retest without overwriting the original

```powershell
.\.venv\Scripts\python.exe -m engine.cli retest <FAIL_RUN_ID> --target whyyou-local --label after-fix --json
.\.venv\Scripts\python.exe -m engine.cli verify <FAIL_RUN_ID> --json
.\.venv\Scripts\python.exe -m engine.cli verify <NEW_RUN_ID> --json
```

새 Run은 parent ID와 source/config digest 차이를 갖는다. 첫 FAIL의 verdict, artifact, manifest digest는
변하지 않아야 한다. 웹 UI 검토는 CLI 결과의 대체가 아니라, 이후 사람이 읽기 쉬운 결과 화면을 만든
뒤 수행하는 별도 제품 검토다.

## 12. Stop and clean up

각 Run의 restore가 성공한 것을 확인한 뒤 WhyYou local stack을 정상 종료한다. `RESTORE_FAILED`가 있으면
후속 장애 Run을 실행하지 말고 Spec 001 `cleanup-confirm` 절차로 marker 부재와 target 안전 상태를 다시
확인한다. bundle이나 DLQ 기록을 수동 삭제해 성공처럼 만들면 안 된다.
