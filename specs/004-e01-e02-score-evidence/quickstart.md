# Quickstart: Spec 004 격리 로컬 재현

Spec 004 실행기와 WhyYou PR #6~#8이 구현된 절차다. 최초 공식 E-01 FAIL과 수정 child PASS는
validation에 보존되어 있다. 아래 Run은 새 재현 결과이며 기존 최초 결과를 덮어쓰지 않는다.

## 1. 전제조건과 범위

- Windows, Docker Desktop의 Linux engine, Git, Python 3.12 이상.
- ControlProof 개발 의존성과 WhyYou 개발 의존성이 설치된 Python 환경.
- 두 저장소의 **clean feature checkout**. 기존 작업 폴더는 보존하고 별도 clone을 권장한다.
  .env 없이 실행한다. 이 도구는 실제 API 키나 기존 DB를 읽지 않는다.
- 사용자가 재현 Run을 승인한 뒤 실행한다. 2026-10-08 Spec 004 완료 요청은 T092/T097 재현을 포함한다.
- 실제 WhyYou API와 작업자를 실행하되 입력은 합성 fixture, 모델은 spec004-report-v1 고정 대체물이다.
  주장 범위는 EXECUTED_SCENARIO_AND_EVIDENCE_ONLY, LOCAL_EMULATED이며 AWS는 NOT_RUN이다.
  모델 품질, 실제 AWS, N-01·N-03, 법적 준수 전체를 검증하지 않는다.

## 2. 소스와 Python 환경

같은 workspace 아래 두 저장소를 준비한다. main을 변경하거나 병합하지 않는다.

| 저장소 | checkout |
|---|---|
| bosung0505/AI_Compliance_SaaS_controlproof | yeonwoo/004-e01-e02-score-evidence |
| jhkim0602/gbsa_aws | bosung/controlproof-n02-integration (PR #8 병합 374b122) |

첫 설치일 때만 각 저장소에서 개발 환경을 만든다(이미 설치됐으면 생략).

```powershell
# ControlProof 루트에서, 최초 설치일 때만
uv sync --extra dev
# WhyYou 루트에서, 최초 설치일 때만
uv sync --group dev
```

깨끗한 checkout에서 기존 설치 환경을 재사용할 수도 있다. 그 경우 Python의 **의존성만 재사용**하며
소스는 새 checkout의 cwd/PYTHONPATH에서 가져온다. validation에 Python 버전·실제 source SHA를 기록한다.
아래 $cpPython과 $whyPython을 해당 환경의 python.exe 경로로 지정한다. 기본 배치라면:

```powershell
$cpPython = (Resolve-Path .\.venv\Scripts\python.exe).Path
$whyPython = (Resolve-Path ..\gbsa_aws\.venv\Scripts\python.exe).Path
```

이후 명령은 모두 ControlProof 루트에서 실행한다.

```powershell
git branch --show-current
git rev-parse HEAD
git status --short
git -C ..\gbsa_aws branch --show-current
git -C ..\gbsa_aws rev-parse HEAD
git -C ..\gbsa_aws status --short
& $cpPython --version
& $whyPython --version
docker info --format '{{.OSType}}'
```

두 status 출력은 비어 있어야 한다. WhyYou는 374b122, Docker는 linux.
ControlProof HEAD는 현재 전달 commit을 직접 기록한다. venv·과거 문서 commit과 Run source를 혼동하지 않는다.

## 3. 격리 환경 기동

```powershell
& $cpPython scripts\spec004_local.py up --whyyou-python $whyPython
& $cpPython scripts\spec004_local.py status
```

도구는 별도 Docker project controlproof-spec004-repro에서 pinned PostgreSQL/Moto를 기동하고
migration·합성 회사 bootstrap·API·작업자 4개를 준비한다. STARTED, actual_runs=0, AWS NOT_RUN이 예상값이다.
루프백 전용 포트는 PG 15734, Moto 14767, API 18085. 기존 WhyYou DB와 과거 증거를 변경하지 않는다.
상태·로그·observer·fault·새 bundle은 workspace/cp-local/spec004-local/repro/에만 저장한다.
합성 GCP 서명 키는 시작 프로세스 메모리에서만 생성하며 파일이나 Git에 저장하지 않는다.
.env 수정, 클라우드 인증, PC별 .pyd 우회는 필요 없다.

충돌하면 다른 instance와 포트를 up에 지정한다. 이후 같은 --instance를 모든 도구 호출에 붙인다.
STARTED 이전 실패는 commands/ 및 boot-*/ 로그를 보고 해결한다. 기존 상태가 있으면 status/stop으로 확인하며
PID나 컨테이너를 전체 종료하지 않는다. stop은 생성 시각이 맞는 소유 프로세스와 해당 project만 멈춘다.
볼륨·Run·복구 차단 기록은 보존한다.

## 4. 자동 gate

T091에서 현재 코드의 ruff/full pytest와 WhyYou reporting/runtime/fault-hook safety 시험을 한 번 실행한다.
동일 source에서 이미 gate를 기록했다면 중복 실행하지 않고 validation의 명령·수·시간을 참조한다.
gate가 없거나 소스가 변경됐다면 다음을 실행한다(조건부):

```powershell
& $cpPython -m ruff check .
& $cpPython -m pytest -q
# WhyYou 루트에서
& $whyPython -m pytest backend/tests/unit/reporting backend/tests/unit/runtime backend/tests/integration/test_controlproof_fault_hook_safety.py -q
```

자동 fixture PASS는 실제 WhyYou 판정이 아니다.

## 5. Preflight

```powershell
& $cpPython scripts\spec004_local.py cli -- preflight E-01 --profile E01_CITATION_EVIDENCE_V1 --target whyyou-local --json
& $cpPython scripts\spec004_local.py cli -- preflight E-02 --profile E02_SCORING_FREEZE_V1 --target whyyou-local --json
```

E-01 READY 18/18, E-02 READY 16/16 및 scoring_rule_source MATCH가 필요하다.
모델 fixture ID/digest와 모든 활성 작업자 증명이 일치해야 한다. READY가 아니면 operator_action을 해결하며
Run을 시작하지 않는다. preflight는 Run·지원자·보고서를 만들지 않는다.

## 6. 승인된 새 재현 Run·show·verify

아래는 실제 Run ID를 출력에서 받아 사용한다. 원본 명령·결과·시간은 도구의 commands/에 자동 기록된다.
Run부터 show/verify까지 600초, Run 540초, verify 60초, 복구 작업 120초를 각각 확인한다.

```powershell
$e01Clock = [Diagnostics.Stopwatch]::StartNew()
$e01 = (& $cpPython scripts\spec004_local.py cli -- run E-01 --profile E01_CITATION_EVIDENCE_V1 --target whyyou-local --label spec004-reproduction-e01 --json | Where-Object { $_ -match '^\s*\{' } | Select-Object -Last 1 | ConvertFrom-Json)
& $cpPython scripts\spec004_local.py cli -- show $e01.run_id --json
& $cpPython scripts\spec004_local.py cli -- verify $e01.run_id --json
$e01Clock.Stop()
$e01Clock.Elapsed.TotalSeconds
```

```powershell
$e02Clock = [Diagnostics.Stopwatch]::StartNew()
$e02 = (& $cpPython scripts\spec004_local.py cli -- run E-02 --profile E02_SCORING_FREEZE_V1 --target whyyou-local --label spec004-reproduction-e02 --json | Where-Object { $_ -match '^\s*\{' } | Select-Object -Last 1 | ConvertFrom-Json)
& $cpPython scripts\spec004_local.py cli -- show $e02.run_id --json
& $cpPython scripts\spec004_local.py cli -- verify $e02.run_id --json
$e02Clock.Stop()
$e02Clock.Elapsed.TotalSeconds
```

각 Run의 정상 판정 exit는 0/3/4이며 복구 실패는 6이다. 출력에 COMPLETED, assertion별 결과,
change_injection_restore_status=SUCCEEDED와 VERIFIED가 있어야 한다.
E-01은 A1~A4, true→false→true 가용성·정확한 원복, D1 네 모드 **진단 관찰**을 확인한다.
E-02는 A1~A3, v1 72/v2 74, 첫 보고서 불변·동결 입력·재계산 일치를 확인한다.
FAIL/INCONCLUSIVE면 그대로 봉인한다. 이유와 조치가 확정되기 전 같은 ID를 수정하거나 반복하지 않는다.

## 7. 조건부 결함·복구 처리

최초 공식 FAIL 분류와 수정은 Phase 9에서 완료됐다. 새 재현에 결함이 없다면 retest/cleanup-confirm은
NOT_REQUIRED로 기록한다. 결함이 있다면 validation과 implementation-decisions의 분류 절차를 따른다.
제품 수정은 범위를 먼저 검토하고 승인받으며 parent-linked child로만 검증한다.
RESTORE_FAILED면 즉시 멈춘다. 차단 파일 삭제·임의 DB reset을 하지 않는다.
읽기 전용 안전 상태 증거를 만든 뒤 engine.cli cleanup-confirm 계약에 따른다.

## 8. 종료·공유

```powershell
& $cpPython scripts\spec004_local.py stop
& $cpPython scripts\spec004_local.py status
```

STOPPED와 evidence_and_volumes_retained=true가 예상값이다. 새 Run·receipt·logs·.env는 Git에 넣지 않는다.
Validation에는 source SHA, Run ID, 결과, 복구, manifest SHA-256, 시간과 한계만 기록한다.
완료에는 T001~T097, 추적성·보안 스캔·전체 gate·second clean checkout 재현·converge가 필요하다.
second clean checkout 재현은 다른 PC 재현이나 AWS 검증 완료를 뜻하지 않는다.