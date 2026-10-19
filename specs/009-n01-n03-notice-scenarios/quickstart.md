# Quickstart: Spec 009 검증·실행 안내

이 문서는 구현 뒤 검증 절차다. **아래 명령은 Plan 단계에서 실행하지 않았다.** 실제 Run 준비(2절)와 실제 Run(4절)은 Implement 뒤
연우의 별도 승인으로 한다. python·pytest는 PowerShell에서 실행한다(이 PC의 Git Bash는 확장 DLL이 막힌다). ControlProof 명령은
저장소 루트에서, git 명령은 `git -C <경로>`로 친다.

## 1. 자동 gate (Implement 뒤)

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check engine tests scripts seeds
```

기대: 전부 통과. `tests/unit/test_catalog_matrix_parity.py`는 12/7/2/3·기존 프로필 수 그대로 통과(closure 전).

## 2. WhyYou 실행 checkout 준비 (별도 승인)

기본 checkout(`gbsa_aws`, 2026-10-19부터 로컬 `fixes-and-remaining-work` = `0166d9e`)을 그대로 쓴다. E-01 worktree는 건드리지 않는다.

```powershell
git -C <WY> status --short --branch        # ## fixes-and-remaining-work, 변경 없음
git -C <WY> rev-parse --short HEAD          # 0166d9e
```

- 지원자 앱 의존성: 루트 `node_modules`가 이미 있다(`node_modules/@iep/applicant-interview`). 없으면 WhyYou 루트에서 `npm install`
  (다운로드, 별도 승인).
- Chromium: `ms-playwright`에 `chromium-1243`·`chromium_headless_shell-1243`이 있다(playwright 1.63.0). 없으면 ControlProof `.venv`에서
  `playwright install chromium`(다운로드, 별도 승인).
- WhyYou Python 환경은 Spec 004 하네스와 같은 방식(`--whyyou-python`)을 쓴다.

## 3. 스택 기동

```powershell
.\.venv\Scripts\python.exe -m scripts.spec009_local up --instance s009 --whyyou-repo <WY> --whyyou-python <WY-python> --state-root <상태-루트> --with-applicant-app
.\.venv\Scripts\python.exe -m scripts.spec009_local status --instance s009 --state-root <상태-루트>
```

기대: API `127.0.0.1:8080`(API 프로세스 1개), 지원자 앱 `127.0.0.1:5174`, 외부 AI 차단 표시. 8080·5174가 쓰이고 있으면 `up`이
거부한다. `<상태-루트>`는 두 저장소 밖(예: `...\ControlProof\cp-local\spec009-local`).

## 4. 시나리오별 실제 Run (연우 승인 후, 시나리오마다 따로)

```powershell
.\.venv\Scripts\python.exe -m scripts.spec009_local cli --instance s009 --state-root <상태-루트> -- preflight N-01 --profile N01_NOTICE_V1 --target whyyou-local --json
.\.venv\Scripts\python.exe -m scripts.spec009_local cli --instance s009 --state-root <상태-루트> -- run N-01 --profile N01_NOTICE_V1 --target whyyou-local --label n01-initial --json
.\.venv\Scripts\python.exe -m scripts.spec009_local cli --instance s009 --state-root <상태-루트> -- verify <run_id> --json
.\.venv\Scripts\python.exe -m scripts.spec009_local cli --instance s009 --state-root <상태-루트> -- show <run_id> --json
```

같은 순서로 `N-03`/`N03_STALE_CONSENT_V1`을 실행한다. 인자 형식은 `engine/cli.py`의 `preflight`·`run`(위치 인자 `scenario_id`,
`--target` 필수)·`verify`(위치 인자 run)와 같다.

기대:

- preflight `READY`. 지원자 앱에 닿지 못하면 `ACCESS_BLOCKED`(N-01), 브라우저 실행 파일이 없으면 `RUNNER_NOT_READY`.
- Run 종료 상태 `COMPLETED`(복구·잔여 0 포함). 복구 실패면 `RESTORE_FAILED`와 후속 주입 차단.
- `verify` 결과 VERIFIED.
- 결과의 대상 접근 한 줄, 한계·미검증 범위(N-03은 N03-U1~U3와 후속 조건) 표시.

FAIL·INCONCLUSIVE가 나오면 덮어쓰지 않는다. 원인 분류 뒤 승인된 수정이 있으면 `cli ... -- retest <parent_run_id> --target
whyyou-local --label <label> --json`으로 child Run만 만든다.

## 5. 워크벤치 확인

```powershell
.\.venv\Scripts\python.exe -m engine.web --run-root <상태-루트>\<instance-run-root> --port 8767
```

로컬 모드(`--run-root`)로 연다. 기본 모드는 Spec 008 공유 기록 읽기 전용이라 새 Run이 보이지 않는다. 시나리오 화면과 결과 화면에서
대상 접근 한 줄과 한계 영역을 확인한다. closure 전 카탈로그 상태는 두 시나리오 모두 `NOT_RUN`이다.

## 6. 정리

```powershell
.\.venv\Scripts\python.exe -m scripts.spec009_local stop --instance s009 --state-root <상태-루트>
```

지원자 앱·API·작업자를 함께 내린다. Docker 컨테이너·볼륨 처리는 Spec 004 하네스 `stop`과 같다.
