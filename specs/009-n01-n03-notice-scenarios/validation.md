# Spec 009 Validation — 1단계 자동 gate (T013)

## 실행 정보

| 항목 | 값 |
|---|---|
| 실행 일시 | 2026-10-20 09:02 KST 시작(폴더별 순서대로 포그라운드 실행) |
| ControlProof HEAD | `2dd1194368b477faef0113349d6ce19aee28a417` (`009-n01-n03-notice-scenarios`, push 없음) |
| 기준 | `fixes-and-remaining-work` `b76af4c`, WhyYou `0166d9e`(읽기만) |
| 실행 방식 | `& .\.venv\Scripts\python.exe -m pytest <폴더> -q -p no:cacheprovider`, PowerShell, 메모리 때문에 폴더별로 나눔 |

## 자동 시험

| 대상 | 결과 | 시간 |
|---|---|---|
| `tests/unit` | 737 passed | 225.80s |
| `tests/contract` | 522 passed, 1 skipped | 264.48s |
| `tests/integration` | 303 passed | 542.91s |
| `tests/web` | 94 passed | 405.58s |
| `tests/test_judge.py`, `tests/test_state_seed.py`(폴더 밖 두 파일) | 18 passed | 1.81s |
| **합계** | **1674 passed, 1 skipped** | |

## 고정·회귀 gate

| 검사 | 명령 | 결과 |
|---|---|---|
| ruff | `& .\.venv\Scripts\python.exe -m ruff check engine tests scripts seeds` | `All checks passed!` |
| 기존 시나리오 digest 고정, 공유 bundle 25건 verification 불변, 카탈로그 12/7/2/3 | `pytest tests/contract/test_scenario_digests_frozen.py tests/contract/test_review_data_bundles_unchanged.py tests/unit/test_catalog_matrix_parity.py` | 48 passed (세 파일 모두 무수정) |
| 공유 snapshot 확인 | `& .\.venv\Scripts\python.exe -m scripts.share_records --verify` | 종료 코드 1, `engine.shared_records.SnapshotError: Snapshot display code/catalog differs; select its matching code version` |

공유 snapshot 거부는 plan Compatibility (b)에서 정한 이 브랜치의 예상 동작이다. snapshot의 `display_files`가 `b76af4c` 코드에
고정돼 있기 때문이며, 실제 gate는 위 `test_review_data_bundles_unchanged.py`(25건 각각의 verification이 snapshot 기록과 같음)다.

## 2단계 준비 (2026-10-20, 실제 Run 아님)

| 항목 | 값 |
|---|---|
| Docker | `docker info` ServerVersion `29.8.1` |
| WhyYou 실행 worktree | `gbsa_aws-spec009`, 로컬 전용 브랜치 `yeonwoo/spec009-run`, HEAD `0166d9eb5d25c7a95fafdbe39b802fdbd69a8713`, `.env` 없음, push 없음 |
| ControlProof 실행 worktree | `AI_Compliance_SaaS_controlproof-spec009`, 로컬 전용 브랜치 `yeonwoo/spec009-cp-run`, HEAD `914a4d957bfa8b52654d3c05defde0a807599d93`, `.env` 없음. 원래 checkout에는 `.env`가 있어 하네스(`checked_git(CP)`)가 거부했다. Python은 원래 checkout의 `.venv`를 쓰며 `engine`은 worktree에서 읽힌다 |
| node_modules | 설치하지 않고 `gbsa_aws-spec009\node_modules` → `gbsa_aws\node_modules` junction. 연결 뒤 `git status --porcelain` 비어 있음, `vite.js` 있음. 워크스페이스 패키지(`node_modules\@iep\*`)는 `gbsa_aws` 원본 폴더를 가리킨다(같은 커밋 `0166d9e`, 변경 없음) |
| 하네스 | `scripts.spec009_local up --instance s009 ... --with-applicant-app`. 첫 시도는 Docker 기동 직후 `docker compose up --wait` 120초 제한 초과(이미지는 로컬 고정 digest, 내려받기 없음) → 같은 프로젝트를 `docker compose stop`으로 내리고 재시도, 56초에 `STARTED`·`APPLICANT_APP_STARTED` |
| 상태 | `status`: sources CP `yeonwoo/spec009-cp-run` `914a4d9…`, WhyYou `yeonwoo/spec009-run` `0166d9e…`, ready true. 프로세스 api·workers·applicant_app 기록 |
| 실행 코드 경로 | 하네스와 같은 PYTHONPATH로 `interview_evidence.__file__` = `gbsa_aws-spec009\backend\src\interview_evidence\__init__.py` |
| 지원자 앱·API | `http://127.0.0.1:5174/` 200, `http://127.0.0.1:8080/openapi.json`에 `/v1/applicant/consents` 있음 |
| 하네스 결함(미수정) | `cli` 모드에서 `scripts/spec009_local.py` `main`이 `--api-port 8080`을 argv 끝에 붙여 `--` 뒤 엔진 명령으로 들어간다(`unrecognized arguments: --api-port 8080`). `--api-port 8080`을 `--` 앞에 직접 주어 우회했다 |

preflight(`cli --api-port 8080 -- preflight <ID> --profile <P> --target whyyou-local --json`, 각 11초):

| 시나리오 | 전체 | capability별 status |
|---|---|---|
| N-03 `N03_STALE_CONSENT_V1` | READY (IMPLEMENTED) | target.version.read·target.environment.read·n02.subjects.seed·n02.subjects.teardown·consent.policy.read·consent.commit.write·consent.state.read 모두 READY |
| N-01 `N01_NOTICE_V1` | READY (IMPLEMENTED) | target.version.read·target.environment.read·applicant.screen.open·browser.chromium.available·n01.invitations.seed·n01.invitations.teardown·consent.policy.read·consent.state.read 모두 READY |

두 preflight의 target_version은 `target-snapshot:sha256:f96c0bd16df6def1e0cc6e29bec706337a75288c3a2cfeead4dbcb4e255f3d4e`, model fixture
`n02-analysis-v1`. 스택은 Run 승인을 위해 켜 둔 상태다. actual N-01·N-03은 아직 NOT_RUN이다.

## 2단계 실제 Run (2026-10-20)

공통: 소스 ControlProof `914a4d957bfa8b52654d3c05defde0a807599d93`(`yeonwoo/spec009-cp-run` worktree), WhyYou
`0166d9eb5d25c7a95fafdbe39b802fdbd69a8713`(`yeonwoo/spec009-run` worktree, `node_modules`는 `gbsa_aws\node_modules` junction).
하네스 instance `s009`, run root `cp-local\spec009-local\s009\runs`. 명령은
`scripts.spec009_local cli --instance s009 --state-root <STATE> --api-port 8080 -- <엔진 명령>`. 직전 확인: 두 worktree 변경 없음,
status ready true, 각 Run 직전 preflight READY(모든 capability READY).

### N-03 `n03-initial`

| 항목 | 값 |
|---|---|
| run_id | `f27b68e8-0df8-46b3-a198-c7917c2f08bb` |
| 시작·종료(KST, run.json) | 2026-10-20 09:56:48 → 09:56:51 (CLI 명령 전체 12.6초) |
| Run 상태 / verdict | COMPLETED / PASS |
| verify | VERIFIED, 17 files, missing·mismatched 없음, `controlproof.bundle-profile.spec009.v1` |
| manifest SHA-256 | `2a8511c3884548a34974d0aa6e4dfd167e49a8fb525742b109761661aae2f59a` |
| recovery.json | SUCCEEDED, `SPEC009_LANES_REMOVED`, product_rows_removed 6, 정리 1.44초 |
| 독립 잔여(읽기 전용 `spec009_recovery.recount`) | 44개 표 모두 0, 차단 `n03-stale-consent`·`n01-notice` 없음 |

| assertion | status | reason_code | 근거 |
|---|---|---|---|
| N03-A1 | PASS | — | 제출 `2026-08-v1-stale`/`…d4e0` ≠ 현재 `2026-08-v1`/`…d4e8`, 응답 422 `CONSENT_POLICY_MISMATCH`, 전후 state_digest `8ea201ed…` 같음(ABSENT) |
| N03-A2 | PASS | — | 재조회 `2026-08-v1`/`47bdb38b…d4e8`, 응답 class 2xx, 저장 policy_version·evidence_digest 같음 |
| N03-A3 | PASS | — | past 동의 기록 `01a156cf-9e6e-7add-92cd-6afcb08f3697`, 전후 state_digest `7eae210b…` 같음 |

### N-01 `n01-initial`

| 항목 | 값 |
|---|---|
| run_id | `48a70f5e-aa62-41fc-bf58-3624a6102b4f` |
| 시작·종료(KST, run.json) | 2026-10-20 09:58:21 → 09:58:30 (CLI 명령 전체 20.4초) |
| Run 상태 / verdict | COMPLETED / PASS |
| verify | VERIFIED, 15 files, missing·mismatched 없음, `controlproof.bundle-profile.spec009.v1` |
| manifest SHA-256 | `82c1b6ce554873d78b8c121bb35a1c19c1c7b4d03f6c5339dd8eaeb408c542a9` |
| recovery.json | SUCCEEDED, `SPEC009_LANES_REMOVED`, product_rows_removed 12, 정리 1.47초 |
| 독립 잔여(읽기 전용 `spec009_recovery.recount`) | 44개 표 모두 0, 차단 `n01-notice`·`n03-stale-consent` 없음 |

| assertion | status | reason_code | 근거 |
|---|---|---|---|
| N01-A1 | PASS | — | pc 1440×900, step `ready`, 5항목 11조각 모두 text_present·in_viewport·not_occluded·no_horizontal_overflow 참, token_absent_in_dom 참, 캡처 `n01-pc-capture.png` 99579 bytes |
| N01-A2 | PASS | — | mobile 390×844, step `ready`, 5항목 11조각 네 조건 모두 참, 조작 scroll 1회(`ai_assist.description`), token_absent_in_dom 참, 캡처 `n01-mobile-capture.png` 179372 bytes |
| N01-A3 | PASS | — | 두 lane 모두 화면·서버·저장 `2026-08-v1`/`47bdb38b…d4e8` 같음, commit_status 201, consented_at pc 00:58:25Z·mobile 00:58:27Z |

캡처 관찰(사실만): 두 PNG 모두 지원자 포털 "CONSENT · 지원자 면접" 화면의 "STEP 2 OF 2 개인정보 및 면접 처리 동의" 단계다. 정책 영역에
AI 역할 문장(최종 채용 결정은 기업의 사람이 수행), 녹화 안내 문장, "보관기간 180일", "삭제 방법" 문장이 보이고, 그 아래 체크박스 세
개("문서 분석", "면접 녹화", "AI 평가 보조")와 각 설명이 있다. 체크박스는 선택되지 않았고 "동의하고 계속" 버튼은 비활성으로 보인다.
PC는 오른쪽에 INTERVIEW BRIEF 카드가, 모바일은 동의 카드 아래에 같은 카드가 있다. 두 캡처 모두 문구가 잘리거나 다른 요소에 가린
곳은 눈에 띄지 않는다.

원인 분류: 두 Run 모두 PASS라 해당 없음.

## 범위

- 이 기록은 코드·자동 시험·하네스까지의 1단계 gate다. 모든 시험은 fake adapter·fake 트랜잭션으로 돌았고 WhyYou·DB·브라우저·
  Docker에 접속하지 않았다.
- **actual N-01·N-03: NOT_RUN**(1단계 준비 완료, 실제 Run은 2단계 승인 뒤).
- 카탈로그·범위표·README·Product Brief는 바꾸지 않았다(D-030 3항).
