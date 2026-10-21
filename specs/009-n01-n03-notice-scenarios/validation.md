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

## N-01 측정 v2 child Run (2026-10-20)

소스: ControlProof `04f4f9e3a6cbd338ef06f414758d62936d4ce8a7`(`yeonwoo/spec009-cp-run` worktree), WhyYou
`0166d9eb5d25c7a95fafdbe39b802fdbd69a8713`(`yeonwoo/spec009-run` worktree, `node_modules`는 `gbsa_aws\node_modules` junction).
직전 확인: 두 worktree·원래 checkout 변경 없음, Docker `29.8.1`, 포트 네 개 비어 있음. 하네스 `up`은 첫 시도에 34초로 성공(compose
재시도 없음), status CP `04f4f9e…`·WhyYou `0166d9e…`·ready true, `interview_evidence.__file__` = `gbsa_aws-spec009\backend\src\…`,
5174 응답 200, preflight N-01 READY(모든 capability READY). 명령: `cli --instance s009 --state-root <STATE> -- retest
48a70f5e-aa62-41fc-bf58-3624a6102b4f --target whyyou-local --label n01-measure-v2 --json`.

| 항목 | 값 |
|---|---|
| child run_id | `d3aac7d9-0a52-4f9a-9c8f-f6e1f7b6de18` |
| 부모 | `48a70f5e-aa62-41fc-bf58-3624a6102b4f` (run.json `parent_run_id` 일치, retest-link `parent_bundle_digest` `65a49f31…4583`) |
| 시작·종료(KST, run.json) | 2026-10-20 15:38:10 → 15:38:18 (CLI 명령 전체 19.5초) |
| Run 상태 / verdict | COMPLETED / PASS |
| verify | VERIFIED, 17 files, missing·mismatched 없음 |
| manifest SHA-256 | `68220e0088e8468345cbdcc7fe1af3ba91547bca7c6188b2d6a97dc0273ccf0f` |
| retest-diff 소스 | ControlProof `914a4d9…` → `04f4f9e…`(둘 다 dirty false), WhyYou `0166d9e…` → `0166d9e…` |
| recovery.json | SUCCEEDED, `SPEC009_LANES_REMOVED`, product_rows_removed 12, 정리 1.44초 |
| 독립 잔여(읽기 전용 `spec009_recovery.recount`) | 44개 표 모두 0, 차단 `n01-notice`·`n03-stale-consent` 없음 |
| 부모 불변 | 실행 전 부모 폴더 16개 파일 SHA-256(`test-logs\parent-48a70f5e-before.json`)과 실행 뒤 비교 차이 0, 부모 verify VERIFIED 15 files |

| assertion | status | reason_code | 근거 |
|---|---|---|---|
| N01-A1 | PASS | — | pc 1440×900, `measurement_version` 2, step `ready`, 5항목 11조각 여섯 플래그 모두 참, `clip_ancestor` 모두 null, `computed_opacity` 1.0, `computed_visibility` visible, 조작 없음, token_absent_in_dom 참, 캡처 99409 bytes |
| N01-A2 | PASS | — | mobile 390×844, `measurement_version` 2, step `ready`, 5항목 11조각 여섯 플래그 모두 참, `clip_ancestor` 모두 null, `computed_opacity` 1.0, `computed_visibility` visible, scroll 1회(`ai_assist.description`), token_absent_in_dom 참, 캡처 178488 bytes |
| N01-A3 | PASS | — | 두 lane 모두 화면·서버·저장 `2026-08-v1`/`47bdb38b…d4e8` 같음, commit_status 201 |

캡처 관찰(사실만): 두 PNG 모두 지원자 포털 "CONSENT · 지원자 면접"의 "STEP 2 OF 2 개인정보 및 면접 처리 동의" 단계다. AI 역할 문장,
녹화 안내 문장, "보관기간 180일", "삭제 방법" 문장, 체크박스 세 개("문서 분석", "면접 녹화", "AI 평가 보조")와 설명이 보인다. 체크박스는
선택되지 않았고 "동의하고 계속" 버튼은 비활성으로 보인다. 잘리거나 가린 문구는 눈에 띄지 않는다.

원인 분류: PASS라 해당 없음. 스택은 Run 뒤 `stop`(STOPPED, 볼륨·증적 보존), 포트 네 개 비어 있음.

## Run 뒤 자동 시험

- Run 뒤 하네스 인자 수정·실제 Chromium 음성 대조·측정 v2 보강을 거친 `04f4f9e`에서 폴더별 전체 1701 passed, 1 skipped
  (unit 746, contract 522/1 skipped, integration 321, web 94, 폴더 밖 두 파일 18), xfail 0, ruff 통과.
- 그보다 앞서 하네스 스택이 떠 있던 상태의 `tests/integration` 1회 실행에서 1 failed / 316 passed / 6 xfailed가 나왔다. 실패한
  시험 이름은 출력에 남지 않았고, 같은 코드로 다시 돌린 2회차는 시스템 메모리 부족으로 중단, 스택을 내린 뒤 3회차는 317 passed /
  6 xfailed로 실패가 없었다. 원인은 확인하지 못했다.

## 공유본 제안과 새 checkout 확인 (2026-10-20)

`scripts.share_records`로 기존 `review-data/bundles` 25건과 `cp-local\spec009-local\s009\runs`의 세 건을 새 폴더에 다시 구성했다
(`--snapshot-id shared-actual-20261020`, `--preserve-invalid ce5f2750…`, 검토 PNG는 기존 공유본의 H03 PNG 1종과 N-01 캡처 4장).
결과 `shared-actual-20261020 records=28 missing=1 sha256=0c51f56e67f753047635399c2c66ee146cd7f3d520d05195171910c0e62068ee`, 652개 파일.
이전 snapshot의 25건은 record(파일 해시·무결성 상태·메타데이터)와 바이트 모두 차이 0, 새 세 건은 VERIFIED이고 원본과 바이트가
같다. 누락 기록(N-02 `7b59237e…`) 메모는 그대로다. 세 bundle의 문자열 검사에서 세션 쿠키·초대 토큰 키·접근 경로는 0건이다.
review-data에는 snapshot.json과 새 세 폴더만 더했다. 커밋 `cbdc716`을 `git worktree add … --detach`로 별도 폴더에 꺼내 원래
`.venv` Python으로 `scripts.share_records --verify`를 실행했고(`engine.__file__`이 그 폴더를 가리킴) 같은 출력을 얻었다. 같은
폴더에서 `engine.web --shared-snapshot review-data/snapshot.json --port 8768`을 띄워 `/`, `/scenarios/N-01`, `/scenarios/N-03`, 세
Run 결과 화면, `/compare/d3aac7d9…`가 모두 HTTP 200이었다. 대상 접근 줄은 N-01 화면들에 "화면 + API", N-03 화면들에 "API"로
보였고 N-03 결과 화면에 미검증·한계 네 줄이 있었다. 어느 화면에도 WhyYou 코드 보완 문구는 없었다. 서버를 내리고 확인용 worktree를
지웠다. 이 공유본은 보성 검토 전 제안본이다. Closure 전체 자동 시험: 1700 passed, 1 skipped(unit 744, contract 525/1 skipped,
integration 321, web 92, 폴더 밖 두 파일 18), ruff 통과.

## closure 후속 (2026-10-20)

브랜치 `009-closure-followups`(`f5d0e5e`에서). Run·설치·WhyYou 수정 없음, `review-data/bundles` 28건 바이트 불변.

- 하네스 이식성: `scripts/spec009_local.py`의 지원자 앱 기동이 `getattr(subprocess, "CREATE_NO_WINDOW", 0)`을 쓴다. Windows 동작은
  같고, 상수가 없는 환경에서는 `creationflags=0`으로 기동한다(`tests/unit/test_spec009_local_setup.py`에 상수를 지운 시험 1개).
  scripts/는 공유본이 고정하지 않으므로 이 수정 뒤에도 `share_records --verify`는 `shared-actual-20261020`으로 통과했다.
- N-03 시나리오 화면: 실행된 N-03의 시나리오 화면(`/scenarios/N-03`)에 "대상 접근" 줄 아래로 결과 화면과 같은 형식의 미검증 세 줄
  (문구 — 후속 조건)과 한계 N03-L1을 보인다. 값은 `scenarios/N-03.yaml`의 `unverified_scope_items`·`limitations`에서 대상 접근과
  같은 경로로 읽고, 실행 상태와 무관하다. N-01·H-01·E-01 시나리오 화면에는 없다. NOT_RUN 표시 로직은 그대로다. 시험은
  `tests/web/test_spec009_display.py`에 RED 먼저(세 줄·후속 조건·한계, 다른 화면 부재, HTML 이스케이프 — 5개).
- 공유본: 표시 코드가 바뀌어 `shared-actual-20261020-r2`를 새로 만들었다. 원천은 `review-data/bundles` 28건 그대로(`--run-root
  review-data/bundles`, 카탈로그 밖 두 건 `691abd8a…`·`ce5f2750…`는 같은 폴더를 `--bundle`로), `--preserve-invalid ce5f2750…`,
  검토 PNG는 직전 snapshot.json 기록의 PNG 해시 5종 그대로. 결과
  `shared-actual-20261020-r2 records=28 missing=1 sha256=8e88ccf5bcccce7a870124cbd711b1ebe38e3fceab1c6c4484783e05d9e18bcb`.
  직전 snapshot과 비교: 28건 record(files·hashes·verification·메타) 차이 0, missing_records(N-02 `7b59237e…`)·target 같음,
  bundle 652개 파일 바이트 차이 0. 바뀐 최상위 키는 `snapshot_id`·`display_files`(`engine/web/readmodel.py`,
  `engine/web/templates/scenario.html` 두 항목)·`snapshot_digest`, 그리고 빌드 시각 `reviewed_at`이다.
- 자동 시험: 폴더별 1706 passed, 1 skipped(unit 745, contract 525/1 skipped, integration 321, web 97, 폴더 밖 두 파일 18), ruff 통과.
  web 폴더는 이번 실행에서 46분이 걸렸다(원인 미조사).

## 범위

- 1단계 gate(위 자동 시험)는 fake adapter·fake 트랜잭션으로만 돌았고 WhyYou·DB·브라우저·Docker에 접속하지 않았다.
- 실제 Run은 2단계 절의 세 건이다: N-03 `f27b68e8-0df8-46b3-a198-c7917c2f08bb` PASS, N-01 부모
  `48a70f5e-aa62-41fc-bf58-3624a6102b4f` PASS(측정 v1), N-01 child `d3aac7d9-0a52-4f9a-9c8f-f6e1f7b6de18` PASS(측정 v2).
  모두 `LOCAL_EMULATED`, 합성 데이터, 외부 AI 차단, AWS `NOT_RUN`. N-03은 N03-A1~A3만 판정했고 N03-U1~U3는 미검증 범위다.
- 마감 기록은 [actual-closure.md](./actual-closure.md).
