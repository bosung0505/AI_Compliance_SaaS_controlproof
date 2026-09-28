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
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m playwright install chromium
```

기존 `.venv`가 있으면 새로 만들지 않고 dependency와 browser 설치 상태만 확인한다.

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

## 6. Run regression and contract tests

```powershell
cd "C:\Users\aaaa2\AI 기본법\AI_Compliance_SaaS_controlproof"
.\.venv\Scripts\python.exe -m pytest -q
```

```powershell
cd "C:\Users\aaaa2\AI 기본법\gbsa_aws"
py -3.12 -m pytest backend/tests/unit/shared/test_local_queue_topology.py backend/tests/unit/runtime/test_controlproof_reporting_fault.py backend/tests/unit/runtime/test_controlproof_model_substitute.py backend/tests/integration/test_worker_delivery.py backend/tests/integration/test_controlproof_fault_hook_safety.py -q
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
