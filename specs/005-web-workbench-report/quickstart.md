# Quickstart: Spec 005 웹 워크벤치·보고서

이 문서는 구현 뒤 검증 절차의 안내다. 명령은 저장소 루트에서 실행한다. 개인 절대 경로 대신 `<ControlProof checkout>`,
`<WhyYou checkout>`을 쓴다. 공식 Run이 아니라 Spec 005 웹 검증 기록을 만드는 절차이며 각 시나리오의 공식 상태는 해당 Spec Validation을 따른다
(D-018 추가 결정 3).

## 1. 범위와 전제

- 화면은 PC 전용(1280px 기준, 1024px 이상)이고 `127.0.0.1`에서만 열린다. 로그인은 없다.
- 웹에서 시작할 수 있는 동작은 준비 상태 확인과 수정 메모뿐이다. Run·재시험·정리 확인은 명령줄로 한다.
- 실행 환경은 `LOCAL_EMULATED`, 실제 AWS는 `NOT_RUN`, 데이터는 합성, 외부 AI는 차단, 고정 모델 대체물을 쓴다.

## 2. 소스와 환경

1. 두 저장소의 branch·HEAD·dirty를 기록한다. ControlProof는 `005-web-workbench-report`, WhyYou는 `bosung/controlproof-n02-integration`
   (`374b122`)이며 둘 다 clean이어야 한다.
2. ControlProof 가상환경을 준비한다(Spec 004 quickstart §2: 최초 설치는 `uv sync --extra dev`). 새 checkout에서는 기존 설치 환경의 Python을
   의존성만 재사용해도 된다. 이때 명령은 새 checkout 루트에서 실행하고, `import engine`이 새 checkout의 `engine`을 가리키는지 확인한다
   (`<ControlProof .venv python> -c "import engine; print(engine.__file__)"`). Validation에 Python 버전과 source SHA를 적는다.
   화면 시험용 브라우저: `.venv` Python으로 `-m playwright install chromium`. 설치가 막힌 PC는 설치된 Edge·Chrome 채널을 쓴다(시험이 자동으로
   Chromium → Edge → Chrome 순서로 고르고, 셋 다 없으면 화면 시험을 건너뛴다).
3. 각 PC 고유 환경 사항(DB 포트, `.env` 수동 로드, 보안 정책 우회 등)은 그 PC 담당자의 기록을 따른다. 이 문서에는 넣지 않는다.

## 3. 자동 gate

```text
.venv 의 python -m ruff check .
.venv 의 python -m pytest -q
.venv 의 python -m pytest -q tests/web        # 브라우저 화면 시험
```

예상: ruff 통과, 실패 0(T020 대기 시험 1개는 xfailed). 카탈로그 일치 시험이 범위표와 12/12, 응답 경로·토큰 스캔 위반 0. 전체 시험은
브라우저 시험을 포함해 수 분이 걸린다. 시험이 띄우는 웹 서버는 시험 프로세스 안의 스레드이며 끝나면 모두 닫힌다.

## 4. DEMO 데이터로 화면 열기

```text
.venv 의 python -m scripts.prepare_web_demo
.venv 의 python -m engine.web
```

- 첫 줄은 합성 bundle 16개와 합성 준비 상태 기록을 DEMO root(기본 `.controlproof/web-demo/runs`, 다른 위치는 `--demo-root <경로>`)에 쓴다.
  다시 실행하면 합성 기록이 더 쌓인다. 처음부터 다시 만들려면 DEMO root 폴더(합성 기록만 있음)를 지운 뒤 다시 실행한다. 실제 run root에는 쓰지 않는다.
- 둘째 줄은 `127.0.0.1:8765`에 서버를 띄운다(`--port`, `--run-root`, `--demo-root`, `--target`). 끝낼 때는 그 터미널에서 Ctrl+C.

브라우저로 `http://127.0.0.1:8765/demo/`를 연다. 모든 화면 상단에 `DEMO DATA` 띠가 있어야 하고 실제 개수·보고서에 합성 기록이 섞이지 않아야 한다.
DEMO 화면 주소: 워크벤치 `/demo/`, 시나리오 상세 `/demo/scenarios/<ID>`, 실행 결과 `/demo/runs/<실행 ID>`(워크벤치 표의 기록 링크),
재시험 비교 `/demo/compare/<재시험 실행 ID>`(결과 화면의 "재시험 비교"), 보고서 `/demo/report`. DEMO 화면에서는 준비 상태 확인과 메모를 받지 않는다.

## 5. actual validation (웹 PC 재실행)

각 Run 전: 두 저장소 branch·HEAD·dirty 기록 → 해당 프로필 preflight `READY`(웹의 "준비 상태 확인" 또는 명령줄) → 사람 승인. 각 Run 뒤:
`show`·`verify` 결과와 Run ID·manifest SHA-256을 Spec 005 Validation에 기록한다.

0. 위험 4 보완(Spec 004 재시험 정리 확인 경로, FR-037)이 005에 들어 있는지 확인한다(ID-005-10: PR 브랜치를 먼저 합쳤고, PR #2가 004에 병합되면 004를 다시 합친다).
1. fixture `h03-report-v1`로 WhyYou를 띄운다(아래 "대상 환경 띄우기와 fixture 전환").
2. H-03 `H03_DLQ_V2` 한 건을 `374b122`로 먼저 실행한다(Spec 002 quickstart §7~§9). 새 checkout 조건을 갖췄으면 "현재 통합 대상(`374b122`) 기준"
   독립 재현 gate 기록으로도 남기고, 플레이북 §6의 원래 지정 commit과 다르다는 점을 함께 적는다.
   결과가 공식 상태(PASS)와 다르면 원인을 먼저 분류한다. seed·실행기 결함이면 실패 시험부터 쓰고 고친 뒤 다시 실행한다. 대상 버전 문제면 멈추고,
   `511ae9e`로 바꿀지는 보성이 정한다(research R-015, 보성 확인 2026-10-08).
3. H-03 `H03_MINIMAL_V1`(Spec 001 quickstart), E-03 `E03_BEFORE_V2`, `E03_AFTER_V2`(Spec 002 quickstart §7~§9).
4. N-02 `N02_CONSENT_ORDER_V1`(Spec 003 quickstart §6~§7). 결과는 웹 검증용이며 N-02 공식 상태는 Spec 003 converge를 따른다.
5. fixture `spec004-report-v1`로 전환하고 API·작업자를 다시 띄운다(아래 "대상 환경 띄우기와 fixture 전환").
6. E-02 `E02_SCORING_FREEZE_V1`(`374b122`, Spec 004 quickstart §5~§6).
7. E-01 부모: WhyYou를 `ce8d862`로 둔 별도 checkout에서 실행한다(FAIL 예상, 봉인만 하고 고치지 않음).
8. E-01 재시험: WhyYou `374b122`로 같은 run root에서 `retest <부모 Run ID>`.
9. 웹을 실제 root로 띄운다: `.venv 의 python -m engine.web`(run root 규칙: `--run-root` > `CONTROLPROOF_RUN_ROOT` > `.controlproof/runs`).
   네 화면에서 SC-001~SC-007·SC-010·SC-011을 확인하고 결과를 Validation에 적는다.
10. 끝나면 API·작업자를 멈추고 fixture를 원래대로 되돌린다(Spec 004 quickstart §8).

### 대상 환경 띄우기와 fixture 전환 (2026-10-09 Phase 9 준비에서 확인)

두 가지 방법이 있다. 웹 PC의 두 기본 checkout(`<ControlProof checkout>`, `<WhyYou checkout>`)에 `.env`가 있으면 방법 A를 쓴다.

**방법 A — 기본 checkout과 `.env`로 띄우기(7개 프로필 모두)**

1. 시작 전 두 `.env`의 SHA-256을 기록하고, 값은 옮기지 않은 채 백업 사본을 checkout 밖 임시 폴더에 둔다(끝나면 되돌리고 사본은 지운다).
2. WhyYou checkout에서 `scripts/local.ps1 up`(Docker의 PostgreSQL·LocalStack·Mailpit, 로컬 인프라, migration) → API(`local.ps1 api`) →
   작업자(`local.ps1 worker`, "Started 4 workers" 확인) → 회사 콘솔(`local.ps1 company`, 화면 관찰이 필요한 H-03용; 처음이면 `npm ci` 필요, Node 20 이상).
   API `/health/ready`가 `ok`인지 확인한다.
3. fixture 전환: 두 `.env`의 `CONTROLPROOF_MODEL_FIXTURE_ID`와 `CONTROLPROOF_MODEL_FIXTURE_DIGEST`만 바꾼다. `h03-report-v1`(H-03·E-03·N-02)과
   `spec004-report-v1`(E-01·E-02)의 digest는 각각 `controlproof:<fixture ID>` 문자열의 SHA-256이다. 임베딩 fixture(`h03-embedding-v1`)는 그대로 둔다.
   바꾼 뒤에는 API·작업자를 멈췄다가 다시 띄운다(같은 Docker DB 사용, 볼륨 유지).
4. ControlProof 쪽은 같은 PowerShell 프로세스에 ControlProof `.env`를 불러온 뒤(Spec 002 quickstart §4의 불러오기 블록) `engine.cli preflight …`를 실행한다.
5. E-01 부모(`ce8d862`): WhyYou의 git worktree(`git worktree add --detach <폴더> ce8d862`, 새 브랜치 없음, 그 폴더에서 커밋·push 금지)를 만들고,
   같은 Docker DB에 worktree 소스로 API·작업자를 띄운다(`PYTHONPATH`를 worktree의 `backend/src`로, `.env`는 WhyYou 기본 checkout 값).
   ControlProof는 `WHYYOU_REPO_PATH`만 worktree로 바꿔 preflight·Run을 한다(결과의 대상 commit이 `ce8d862`인지 확인).
6. 끝나면 API·작업자·콘솔을 멈추고 `docker compose down`(볼륨 유지), 두 `.env`를 시작 전 값으로 되돌려 SHA-256을 확인한다.

**방법 B — Spec 004 격리 도구(`scripts/spec004_local.py`, E-01·E-02 전용)**

- 쓸 수 있는 조건: ControlProof와 WhyYou 모두 `.env`가 **없는** 별도 깨끗한 checkout(main이 아닌 브랜치)이어야 한다. 도구는 `.env`가 있는 checkout을 거부한다.
  fixture는 `spec004-report-v1`로 고정이며 H-03·E-03·N-02에는 쓸 수 없다. 별도 Docker project와 루프백 포트(PG 15734, Moto 14767, API 18085)를 쓰고
  상태·bundle은 workspace의 `cp-local/spec004-local/<instance>/`에 둔다. E-01 부모는 `--whyyou-repo <ce8d862 checkout>`과 다른 `--instance`로 띄운다.

**이 PC 한정(연우 PC, 다른 PC에는 해당 없을 수 있음)**

- Windows 앱 제어가 uv가 만든 `alembic.exe`·`uvicorn.exe` 실행을 막는다. `local.ps1 up`은 Docker·로컬 인프라까지 끝난 뒤 migration 단계에서 멈추므로
  같은 명령을 WhyYou `.venv`의 Python으로 실행한다: `-m alembic -c backend/alembic.ini upgrade heads`, API는 `-m uvicorn interview_evidence.main:app --host 127.0.0.1 --port 8080`,
  작업자는 `scripts/run_workers.py`(모두 WhyYou `.env`를 프로세스 환경에 불러온 뒤).
- PowerShell 5.1은 docker·alembic의 stderr를 오류로 본다. `local.ps1`은 별도 `powershell.exe -File`로 실행하거나 그 출력을 따로 처리한다.
- WhyYou DB 포트 5433, ControlProof `.env`는 프로세스마다 수동으로 불러온다(Spec 004 validation "세션 인계"). `.venv`의 SQLAlchemy `*_cy*.pyd`는 앱 제어 때문에
  `.blocked`로 바꿔 두었다(되돌리지 않음).
- npm 11은 esbuild의 설치 스크립트를 `allowScripts`로 건너뛰지만 회사 콘솔 dev 서버(Vite)는 그대로 뜬다(2026-10-09 확인).

## 6. 사용성 검토 (SC-008·SC-009)

- 진행: 태오. 참여자: 비작성자 6명(실행 담당자·검증 책임자·결과 검토자 각 2명).
- 화면: §5의 실제 기록으로 연 웹(DEMO가 아님).
- 과업 3개: (1) 12개 상태 읽기, (2) E-01 최초 FAIL의 판정 근거 증적 찾기, (3) E-01 재시험 비교에서 달라진 점 찾기.
- 질문 7개: Product Brief §10.3. 질문당 3분.
- 통과: 질문마다 6명 중 5명 이상 정답, 치명적 오독(`NOT_RUN`·`NO_TEST_TARGET`·`INCONCLUSIVE`를 통과로, AI 점수를 채용 결정으로, 결과를 법적
  인증으로 읽음) 0건, "무엇은 아직 검증하지 못했는가"에 6명 중 5명 이상이 범위표와 같은 답.
- 기록: 참여자 익명 ID·역할, 질문별 시간·정답·오독 유형, 사용한 Run ID를 Validation에 남긴다.

## 7. 스캐너 강화 전 기존 bundle 검사 (FR-036)

```text
.venv 의 python -m scripts.scan_bundles --run-root <실제 run root> --out .controlproof/web/scan-before-v2.json
```

검사 스크립트가 생긴 뒤 보성이 자기 PC에서 같은 명령을 실행하고 보고서의 요약(bundle ID·파일 상대 경로·규칙·건수)만 전달하면 Validation에
적는다. bundle은 옮기지 않는다.
두 PC 결과를 기록한 뒤에만 봉인 시점 검사를 v2로 바꾼다.
