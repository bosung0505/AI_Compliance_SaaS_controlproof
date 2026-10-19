# Quickstart: Spec 006 검증·실행 안내

이 문서는 구현 뒤 검증 절차다. **아래 명령은 Plan 단계에서 실행하지 않았다.** 실제 Run 준비(2절)와 실제 Run(4절)은 Implement 뒤
연우의 별도 승인으로 한다. python·pytest는 PowerShell에서 실행한다(이 PC의 Git Bash는 확장 DLL이 막힌다).

## 1. 자동 gate (Implement 뒤)

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m ruff check engine tests scripts seeds
```

기대: 전부 통과. `tests/unit/test_catalog_matrix_parity.py`는 5/4/3·7 프로필 그대로 통과(closure 전).

## 2. WhyYou 실행 checkout 준비 (별도 승인)

기존 기본 checkout(`gbsa_aws`, 현재 `bosung/controlproof-n02-integration`)과 E-01 worktree는 건드리지 않는다.

```powershell
git -C <WY> remote add bosung0505 https://github.com/bosung0505/gbsa_aws.git   # 없을 때만
git -C <WY> fetch bosung0505 fixes-and-remaining-work
git -C <WY> worktree add <WY-SPEC006> 33aa996 --detach
git -C <WY-SPEC006> status --short        # 비어 있어야 함
git -C <WY-SPEC006> rev-parse HEAD         # 33aa996…
```

- `<WY-SPEC006>`은 두 저장소 밖의 경로로 둔다.
- 지원자 앱 의존성: `<WY-SPEC006>`에서 `npm install`(다운로드, 별도 승인). Chromium이 없으면 ControlProof `.venv`에서
  `playwright install chromium`(다운로드, 별도 승인).
- WhyYou Python 환경은 Spec 004 하네스와 같은 방식(`--whyyou-python`)을 쓴다.

## 3. 스택 기동

```powershell
.\.venv\Scripts\python.exe scripts/spec006_local.py up --whyyou-repo <WY-SPEC006> --with-applicant-app
.\.venv\Scripts\python.exe scripts/spec006_local.py status
```

기대: API `127.0.0.1:8080`(API 프로세스 1개), 지원자 앱 `127.0.0.1:5174`, 외부 AI 차단 표시. 8080이 쓰이고 있으면 `up`이 거부한다.

## 4. 시나리오별 실제 Run (연우 승인 후, 시나리오마다 따로)

```powershell
.\.venv\Scripts\python.exe scripts/spec006_local.py cli preflight H-02 --profile H02_WRITE_SURFACE_V1 --target whyyou-local --json
.\.venv\Scripts\python.exe scripts/spec006_local.py cli run H-02 --profile H02_WRITE_SURFACE_V1 --target whyyou-local --label h02-initial --json
.\.venv\Scripts\python.exe scripts/spec006_local.py cli verify <run_id> --json
```

같은 순서로 `H-01`/`H01_DECISION_AUTHORITY_V1`, `N-01`/`N01_NOTICE_V1`, `N-03`/`N03_STALE_CONSENT_V1`을 실행한다.
인자 형식은 `engine/cli.py`의 `preflight`·`run`(위치 인자 `scenario_id`, `--target` 필수)·`verify`(위치 인자 run)와 같다.

기대:

- preflight `READY`. 접근이 없으면 `ACCESS_BLOCKED`, 실행기 준비 부족이면 `RUNNER_NOT_READY`.
- Run 종료 상태 `COMPLETED`(H-02 외는 복구·잔여 0 포함). 복구 실패면 `RESTORE_FAILED`와 후속 주입 차단.
- `verify` 결과 VERIFIED.
- 결과의 대상 접근 한 줄, 한계·미검증 범위(N-03은 N03-U1~U3와 후속 조건) 표시.

FAIL·INCONCLUSIVE가 나오면 덮어쓰지 않는다. 원인 분류 뒤 승인된 수정이 있으면 `cli retest <parent_run_id> --target whyyou-local`로 child Run만 만든다.

## 5. 워크벤치 확인

```powershell
.\.venv\Scripts\python.exe -m engine.web --run-root <실제-기록-폴더>
```

시나리오 화면과 결과 화면에서 대상 접근 한 줄과 한계 영역을 확인한다. closure 전 카탈로그 상태는 네 시나리오 모두 `NOT_RUN`이다.

## 6. 정리

```powershell
.\.venv\Scripts\python.exe scripts/spec006_local.py stop
```
