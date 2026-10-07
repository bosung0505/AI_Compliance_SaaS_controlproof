# Quickstart: Spec 004 E-01·E-02 Local Actual Run

> Plan 산출물(초안)이다. 아래 E-01·E-02 명령은 Tasks·Analyze·Implement와 WhyYou fixture PR이 끝난 뒤 쓰는 계약이다.
> 지금은 실행기가 없으므로 실행하지 않는다. `<…>`는 실제 Run 뒤 채울 자리표시자다.

## 1. 목적과 주장 범위

1. E-01: 잘못된 인용 네 종류와 유효 인용이 보고서 작업자의 검증·저장을 거쳐 어떻게 저장되는지
2. E-01: 저장된 점수의 근거(자막 구간)를 지우면 회사 보고서 조회가 근거 부족을 드러내는지, 복원하면 돌아오는지
3. E-01 진단: 저장소에 직접 쓴 잘못된 인용이 조회에서 어떻게 보이는지(판정 아님)
4. E-02: 새 평가 기준 버전을 발행해도 과거 보고서가 그대로이고 저장 입력으로 총점을 다시 계산할 수 있는지

공식 범위는 `EXECUTED_SCENARIO_AND_EVIDENCE_ONLY`다. 면접 입력은 fixture, 모델은 고정 대체물이며 실제 AI 모델 품질,
실제 AWS, N-01·N-03, 법적 준수 전체를 검증하지 않는다.

## 2. 저장소 배치와 브랜치

```text
workspace/
├── AI_Compliance_SaaS_controlproof/   # 004-e01-e02-score-evidence
├── gbsa_aws/                          # bosung/controlproof-n02-integration + spec004 fixture
└── cp-local/                          # FAULT_ROOT·OBSERVER_ROOT, archive/
```

ControlProof 루트에서 실행한다.

```powershell
git branch --show-current
```

예상: `004-e01-e02-score-evidence`

```powershell
git status --short
```

예상: 출력 없음

```powershell
git -C ..\gbsa_aws branch --show-current
```

예상: `main`이 아닌 브랜치. fixture PR 병합 전이면 `yeonwoo/controlproof-e01-e02-fixture`, 병합 뒤면
`bosung/controlproof-n02-integration`

```powershell
git -C ..\gbsa_aws status --short
```

예상: 출력 없음

```powershell
git -C ..\gbsa_aws log --oneline -1
```

예상: `<whyyou-sha> …`(Validation에 기록)

## 3. 로컬 환경 (팀원 PC 기준, Spec 003 T093 이식성 기록과 같음)

- WhyYou DB는 `.env`의 `POSTGRES_PORT`·`DATABASE_URL`·`MIGRATION_DATABASE_URL`이 가리키는 포트를 쓴다(기존 PostgreSQL과
  겹치면 5433 등으로 바꾼다).
- ControlProof `.env`는 자동으로 읽히지 않는다. CLI를 실행하는 터미널마다 먼저 로드한다.

```powershell
Get-Content .env | ForEach-Object { if ($_ -match '^\s*([^#=][^=]*)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process') } }
```

예상: 출력 없음

- `CONTROLPROOF_FAULT_ROOT`·`CONTROLPROOF_OBSERVER_ROOT`는 workspace의 `cp-local` 아래를 가리키고, API·작업자·ControlProof가
  같은 값을 쓴다.
- Spec 004에 필요한 WhyYou 설정(실제 값은 `.env`에만, commit 금지):

```text
APP_ENVIRONMENT=local
CONTROLPROOF_EXTERNAL_AI_ALLOWED=false
CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED=true
CONTROLPROOF_MODEL_FIXTURE_ID=spec004-report-v1
CONTROLPROOF_TEST_HOOKS_ENABLED=true
```

### 고정 모델 fixture 전환

fixture는 프로세스마다 하나이고 기동 시 정해진다. 시나리오에 맞는 fixture로 **두 저장소의 `.env`를 같이** 바꾸고 API와
작업자 4개를 모두 재기동한다. digest는 `sha256("controlproof:" + fixture_id)`이며 WhyYou health의 `fixture_digest`와
ControlProof `.env`의 값이 정확히 같아야 preflight가 READY다.

| 실행할 시나리오 | `CONTROLPROOF_MODEL_FIXTURE_ID` | `CONTROLPROOF_MODEL_FIXTURE_DIGEST` (ControlProof `.env`) |
|---|---|---|
| E-01, E-02 | `spec004-report-v1` | `e15ec3790b64b2fba10e0caa9372f08c917edbbaa99ce308076952b838668b3f` |
| N-02, H-03 | `h03-report-v1` | `ce09b95403b34e1390502c90f5c5edc518ddf65d38c8ce881617a37cac6d16b1` |

1. WhyYou `.env`의 `CONTROLPROOF_MODEL_FIXTURE_ID`를 위 표 값으로 바꾼다.
2. ControlProof `.env`의 `CONTROLPROOF_MODEL_FIXTURE_ID`와 `CONTROLPROOF_MODEL_FIXTURE_DIGEST`를 위 표 값으로 바꾼다.
3. 터미널 A의 API와 터미널 B의 작업자 4개를 멈췄다가 아래 기동 순서대로 다시 띄운다(각 터미널에서 `.env`를 다시 로드).
4. ControlProof 터미널에서 `.env`를 다시 로드하고 해당 시나리오의 preflight로 `model_fixture_id`를 확인한다.

AI 격리 digest(`ai_isolation_digest`)는 활성 fixture ID·digest를 포함하므로 fixture를 바꾸면 값이 바뀌고, 작업자
attestation도 새 값으로 다시 써진다. 이전 fixture로 기동한 작업자가 하나라도 남아 있으면 attestation이 맞지 않아
preflight가 READY가 되지 않는다. E-01·E-02 Run을 끝낸 뒤 N-02·H-03을 돌릴 때는 `h03-report-v1`로 되돌리고 같은 절차로
재기동한다.

### 기동 순서

터미널 A (WhyYou):

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
```

예상: 출력 없음

```powershell
.\scripts\local.ps1 up
```

예상: PostgreSQL·LocalStack 기동, 큐 생성 메시지. Docker를 다시 켰다면 API 전에 반드시 다시 실행한다.

```powershell
.\scripts\local.ps1 api
```

예상: API가 `http://127.0.0.1:8080`에서 대기

터미널 B (WhyYou 작업자, WhyYou `.env`를 위 로드 명령으로 먼저 로드):

```powershell
uv run --cache-dir .uv-cache --no-sync python scripts/run_workers.py
```

예상: 작업자 기동 로그, ControlProof 작업자 attestation 기록

새 DB면 회사가 없다. 터미널 C에서 회사 토큰으로 한 번 호출해 만든다(토큰 값은 `.env`에만 있다).

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8080/v1/me -Headers @{ Authorization = "Bearer $env:WHYYOU_COMPANY_TOKEN" }
```

예상: 회사 사용자 JSON

알려진 로컬 우회: Windows 앱 제어 정책 때문에 `.venv`의 SQLAlchemy `*_cy*.pyd`를 `.blocked`로 바꿔 둔 상태를 유지한다.

## 4. 정적·자동 회귀

```powershell
.\.venv\Scripts\python.exe -m ruff check .
```

예상: `All checks passed!`

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

예상: `<N> passed`(PR #1 병합 뒤 기준 491 + Spec 004 시험; 실패 0)

WhyYou fixture 시험(WhyYou 루트, WhyYou venv):

```powershell
uv run --cache-dir .uv-cache --no-sync pytest backend/tests/unit/runtime/test_controlproof_model_substitute.py -q
```

예상: 모두 PASS

## 5. 격리 샌드박스 진단 (최초 공식 Run 전 필수)

[research.md](./research.md)의 SD-1~SD-5(tasks T072~T078)는 Spec 004의 최초 공식 Run 전에 반드시 Spec 003 ID-003-18 격리
대상에서 실행한다. 이후 팀원 재현(T097)에서는 생략할 수 있다. 진단 결과는 `validation.md`에 "진단"으로만 기록하고 공식
Run·verdict로 쓰지 않는다.

## 6. Preflight

```powershell
.\.venv\Scripts\python.exe -m engine.cli preflight E-01 --profile E01_CITATION_EVIDENCE_V1 --target whyyou-local --json
```

예상: `"readiness": "READY"`, `"capabilities": {"ready": 18, "required": 18}`, `"model_fixture_id": "spec004-report-v1"`

```powershell
.\.venv\Scripts\python.exe -m engine.cli preflight E-02 --profile E02_SCORING_FREEZE_V1 --target whyyou-local --json
```

예상: `"readiness": "READY"`, `"capabilities": {"ready": 16, "required": 16}`, `"scoring_rule_source": {"status": "MATCH", …}`

`READY`가 아니면 `operator_action`을 먼저 해결한다. `RUNNER_NOT_READY`는 WhyYou FAIL이 아니다. **공식 Run은 preflight
READY를 확인하고 사용자가 명시적으로 승인한 뒤에만 실행한다.**

## 7. 최초 actual Run

```powershell
.\.venv\Scripts\python.exe -m engine.cli run E-01 --profile E01_CITATION_EVIDENCE_V1 --target whyyou-local --label e01-initial --json
```

예상: `run_state` `COMPLETED`, `verdict` PASS/FAIL/INCONCLUSIVE 중 하나, `change_injection_restore_status` `SUCCEEDED`,
`run_id` `<e01-run-id>`. exit 0/3/4는 정상 종료이고 exit 6이면 §9.

```powershell
.\.venv\Scripts\python.exe -m engine.cli run E-02 --profile E02_SCORING_FREEZE_V1 --target whyyou-local --label e02-initial --json
```

예상: 같은 형식, `run_id` `<e02-run-id>`

최초 결과가 FAIL·INCONCLUSIVE여도 다시 돌려 덮어쓰지 않는다. Run 시작부터 verify 끝까지 600초 안인지 기록한다.

```powershell
.\.venv\Scripts\python.exe -m engine.cli show <e01-run-id> --json
```

예상: 모드별 emission·저장 결과, 제거 전·후·복원 후 조회 차이, E01-D1 노출, 한계 표시

```powershell
.\.venv\Scripts\python.exe -m engine.cli verify <e01-run-id> --json
```

예상: `"bundle_status": "VERIFIED"`, EV4-01·02·03·04·05·09·10

```powershell
.\.venv\Scripts\python.exe -m engine.cli verify <e02-run-id> --json
```

예상: `"bundle_status": "VERIFIED"`, EV4-01·02·04·06·07·08·09·10, 재계산 재실행 일치

확인 항목:

- E01-A1~A4, E02-A1~A3 모두 판정 또는 명시적 INCONCLUSIVE와 사유 코드
- 네 잘못된 모드의 emission receipt가 의도와 같음
- 근거 제거가 실제로 일어났고(행 부재·타임라인 차이) 복원 digest가 같음
- 두 번째 보고서가 v2 버전 ID·가중치, 첫 보고서 PRE/POST 동일
- 재계산 다섯 비교 대상 일치
- `LOCAL_EMULATED`, AWS `NOT_RUN`, fixture 입력·외부 AI 차단 표시

## 8. 최초 FAIL 처리 (예: E01-A3, 코드상 예측 P1)

1. `<e01-run-id>`의 verify 결과와 manifest SHA-256을 `validation.md`에 기록한다.
2. `show`로 제거 receipt, 타임라인 차이, 보고서 차이를 확인한다.
3. `implementation-decisions.md`에 원인을 `TARGET_CONTROL_DEFECT`/`RUNNER_OR_OBSERVER_DEFECT`/`RESTORE_OPERATOR_DEFECT`로
   분류해 기록한다. 대상 결함이면 WhyYou 최소 수정 범위를 `PROPOSED`로 두고 승인을 받는다.
4. 승인 뒤 WhyYou 기준 브랜치에서 개인 브랜치를 따 실패 시험 → 수정 → 시험 → fork push → PR.
5. preflight READY와 승인 뒤 child를 만든다.

```powershell
.\.venv\Scripts\python.exe -m engine.cli retest <e01-run-id> --target whyyou-local --label e01-after-fix --json
```

예상: 새 `<e01-child-run-id>`, `retest-diff.json`에 WhyYou commit 차이

```powershell
.\.venv\Scripts\python.exe -m engine.cli verify <e01-run-id> --json
```

예상: parent manifest SHA-256이 1단계 기록과 같음

```powershell
.\.venv\Scripts\python.exe -m engine.cli verify <e01-child-run-id> --json
```

예상: `VERIFIED`

## 9. Restore failure

Run이 `RESTORE_FAILED`(exit 6)면 즉시 멈추고 새 변경 주입 Run을 하지 않는다. 차단 파일을 임의로 지우지 않는다. `show`로
injection·대상 행을 확인하고, Run 소유 자막 구간·축 JSON·직무가 복원 또는 제거됐는지 읽기 전용으로 확인한 증거로
`cleanup-confirm`을 실행한다.

```powershell
.\.venv\Scripts\python.exe -m engine.cli cleanup-confirm --target whyyou-local --subject e01-citation-evidence --evidence <cleanup-evidence.json> --json
```

예상: 차단 해제 기록, 이후 retest에 같은 증거 파일을 `--cleanup-evidence`로 전달

봉인 전 중단이나 INVALID bundle로 `cleanup-confirm`을 쓸 수 없으면 Spec 003 ID-003-12 절차(합성 로컬 대상만 컨테이너·
볼륨 재생성, 차단 파일·receipt를 `cp-local/archive`에 보관, `validation.md` 기록)를 따른다. 공유 대상에서는 하지 않는다.

## 10. Bundle 공유

`.controlproof/runs/`와 `.controlproof/`는 Git에 넣지 않는다. Validation에는 실행 환경 비민감 요약, ControlProof·WhyYou
commit SHA, Run ID, verdict, 복구 결과, manifest SHA-256, verify 결과만 기록한다.

## 11. 완료 조건

Tasks·Analyze, 구현과 자동 gate, WhyYou fixture PR, preflight READY, E-01·E-02 최초 Run과 봉인 bundle, FAIL이면 승인된
보완과 child, 모든 assertion의 근거 있는 결과, 복구 안전 상태, validation·traceability·인수인계 갱신, `$speckit-converge`.
완료돼도 N-01·N-03, 실제 AWS, Spec 005는 자동 완료되지 않는다.
