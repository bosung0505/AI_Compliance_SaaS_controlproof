# Quickstart: H-03 최소 수직 흐름

이 문서는 Spec 001 구현 완료 후 로컬 격리 환경에서 최초 Run을 재현하는 절차다. 현재 plan 단계에서는 명령 계약을 고정하며, 구현 전에는 일부 명령이 아직 존재하지 않는다.

## 1. 전제조건

- Python 3.12
- Docker Desktop과 Docker Compose
- Chromium을 설치할 수 있는 Playwright 환경
- ControlProof 저장소 checkout
- WhyYou `jhkim0602/gbsa_aws` checkout
- 실제 지원자 데이터가 없는 WhyYou local/test stack
- WhyYou 회사 사용자 test credential

운영 환경 URL, 운영 DB, 실제 지원자 계정은 사용하지 않는다.

## 2. ControlProof 설치

```powershell
cd C:\Users\aaaa2\AI 기본법\AI_Compliance_SaaS_controlproof
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

정적 검사와 단위 테스트:

```powershell
ruff check .
pytest -q
```

## 3. WhyYou 격리 환경 준비

WhyYou는 local/test profile로 시작하고 다음 조건을 만족해야 한다.

- PostgreSQL, local SQS/LocalStack, object storage가 격리됨
- 외부 LLM/음성 호출은 WhyYou의 deterministic local substitute 사용
- `CONTROLPROOF_TEST_HOOKS_ENABLED=true`
- `CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED=true`와 허용된 고정 fixture ID 사용
- `CONTROLPROOF_FAULT_ROOT`가 WhyYou worker와 ControlProof host가 공유하는 test-only 경로를 가리킴
- `${CONTROLPROOF_FAULT_ROOT}/receipts/`는 worker가 append+fsync하고 ControlProof가 읽을 수 있음
- production profile이 아님

fault hook이 없는 WhyYou commit에서는 ControlProof가 `RUNNER_NOT_READY`로 멈추는 것이 정상이다. hook을 우회해 실행하지 않는다.

## 4. 로컬 환경변수

비밀값은 `.env`를 git에 커밋하지 않고 현재 shell 또는 비밀 저장소에서 주입한다.

```powershell
$env:CONTROLPROOF_TARGET_ID = "whyyou-local"
$env:CONTROLPROOF_RUN_ROOT = ".controlproof/runs"
$env:WHYYOU_BASE_URL = "http://localhost:8000"
$env:WHYYOU_CONSOLE_URL = "http://localhost:5173"
$env:WHYYOU_DATABASE_URL = "postgresql+psycopg://<local-test-credential>@localhost:5432/<local-test-db>"
$env:WHYYOU_COMPANY_TOKEN = "<local-test-company-token>"
$env:WHYYOU_REPO_PATH = "C:\path\to\gbsa_aws"
$env:CONTROLPROOF_FAULT_ROOT = "C:\path\to\shared\controlproof-faults"
$env:CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED = "true"
$env:CONTROLPROOF_MODEL_FIXTURE_ID = "h03-report-v1"
```

ControlProof 출력에 위 credential이 보이면 실행을 중단하고 evidence redaction 결함으로 처리한다.

## 5. Preflight

```powershell
python -m engine.cli preflight H-03 --target whyyou-local --json
```

기대 결과:

- `readiness=READY`
- `implementation_status=IMPLEMENTED`
- `target_version=target-snapshot:sha256:<digest>`와 canonical TargetSnapshot 존재
- 실행 형태에 맞는 git commit·dirty/diff 또는 image digest와 OpenAPI·schema·model fixture digest 존재
- report read, final-decision, seed, browser, fault apply/trigger-receipt probe/restore capability 모두 READY
- deterministic model substitute의 fixture ID와 canonical digest가 scenario 허용값과 일치
- active fault/block marker 없음

대표 비정상 결과:

- reporting 기능은 있으나 hook 미설치 → `RUNNER_NOT_READY`
- 회사 bearer 거부 → `ACCESS_BLOCKED`
- H-03 대상 기능 자체 없음 → `NO_TEST_TARGET`

READY가 아니면 Run이 생성되어서는 안 된다.

## 6. 최초 H-03 Run

```powershell
python -m engine.cli run H-03 --target whyyou-local --label first-h03 --json
```

실행기는 다음을 자동 수행한다.

1. target/subject lock 획득
2. pending-report 합성 지원자 seed
3. baseline 상태와 버전 수집
4. session-scoped fault marker 적용
5. reporting event trigger와 현재 Run·session·event가 일치하는 worker trigger receipt로 실제 fault 발동 확인
6. report API polling과 회사 콘솔 screenshot
7. 정상 final-decision endpoint 시도
8. decision/stage/invitation 전후 비교와 자동결정 부재 관찰
9. marker 비활성·worker health로 환경 복구 확인하고 report 처리 결과를 별도 상태로 기록
10. assertion, verdict, bundle manifest 생성 및 봉인

WhyYou가 FAIL하더라도 ControlProof가 정확한 증적과 verdict를 만들었다면 구현 실행은 성공한 것이다. exit 3은 실행기 오류가 아니라 target FAIL 결과다.

## 7. 결과 검토

```powershell
python -m engine.cli show <RUN_ID> --json
python -m engine.cli verify <RUN_ID> --json
```

bundle 경로:

```text
.controlproof/runs/<RUN_ID>/
```

검토자는 다음을 확인한다.

- Run state와 H-03 verdict가 구분됨
- H03-A1~A6 각각 expected/actual/evidence가 있음
- EV-01~EV-09가 manifest에 연결됨
- screenshot에 실제 담당자 표시가 있음
- final decision request/response와 사후 state snapshot이 있음
- 환경 복구 성공 여부와 별도 `report_processing_recovery` 및 미검증 범위(DLQ 등)가 명시됨
- bundle verify가 VERIFIED임

SC-008은 눈으로 “빨리 찾을 수 있다”고 판단하지 않는다. bundle을 만들지 않은 검토자 1명이 `specs/001-execution-evidence-h03/review-usability-checklist.md`에 따라 canonical PASS·FAIL·INCONCLUSIVE 3건을 각각 검토한다. Run ID를 받은 시점부터 타이머를 시작하고 `controlproof show`만 사용해 verdict, 핵심 이유, 실패/판정 불가 assertion, 증적 링크, 환경 복구 상태를 답한다. 세 건 모두 정답이고 각각 120초 이하여야 하며 결과를 `validation.md`에 기록한다.

## 8. Tamper smoke test

실제 최초 Run을 훼손하지 않고 복사본 fixture에서만 수행한다.

```powershell
Copy-Item -Recurse .controlproof\runs\<RUN_ID> .controlproof\tamper-check\<RUN_ID>
# 복사본 artifact 한 개를 테스트용으로 변경
python -m engine.cli verify .controlproof\tamper-check\<RUN_ID> --json
```

기대 결과는 integrity failure와 exit 5다. 원본 bundle을 자동 수정하면 안 된다.

## 9. WhyYou 수정 후 재시험

최초 Run에서 실제 보호조치 FAIL이 확인되고 WhyYou 변경이 별도 검토·승인된 뒤에만 진행한다.

```powershell
python -m engine.cli retest <PARENT_RUN_ID> --target whyyou-local --label after-fix --json
```

기대 결과:

- 새 Run ID
- `parent_run_id=<PARENT_RUN_ID>`
- parent bundle digest 불변
- target version 차이 기록
- TargetSnapshot digest가 다르면 변경된 JSON field path 기록
- 첫 FAIL과 새 결과를 둘 다 조회 가능

최초 Run이 이미 PASS라면 데모를 위해 WhyYou에 인위적인 결함을 만들지 않는다.

## 10. Restore failure 대응

Run이 `RESTORE_FAILED`이면 같은 target+subject의 다음 장애 Run은 차단된다.

1. WhyYou worker와 shared fault root를 수동 확인한다.
2. marker가 없고 reporting 처리가 정상임을 확인한다.
3. 확인 결과를 비식별 JSON evidence로 만든다.
4. 다음 명령으로 block 해제를 요청한다.

```powershell
python -m engine.cli cleanup-confirm --target whyyou-local --subject candidate-01 --evidence cleanup-note.json --json
```

단순 강제 해제는 지원하지 않는다.

## 11. 완료 기준

- `ruff check .` 성공
- 전체 pytest 성공
- fake adapter H-03 통합 테스트 성공
- 격리 WhyYou 최초 Run 생성
- Run이 PASS/FAIL/INCONCLUSIVE 중 실제 사실과 일치
- EV-01~EV-09 연결과 SHA-256 검증 성공
- canonical TargetSnapshot/run linkage와 implementation status 분리 확인
- 환경 복구 성공 또는 RESTORE_FAILED 안전 차단 확인, report 처리 결과는 별도 필드로 보존
- SC-008 비작성자 검토 3건 모두 정답·각 120초 이하
- 실제 개인정보 0건
