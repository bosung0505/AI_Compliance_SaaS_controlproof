# Spec 005 Validation

## Current status

- Workflow stage: Implement. Phase 1~8(T001~T018, T021~T060, T057a~T057d) 완료. T019(보성 PC 검사) 대기, T020(봉인 검사 v2 전환)과
  Phase 9(actual validation) 이후는 시작 전. ID-005-01은 2026-10-09 결정됨.
- Actual validation(웹 PC 재실행)·사용성 검토: 아직 없음(`NOT_RUN`). AWS: `NOT_RUN`.
- 이 문서는 시간순 기록이다. 실패·판정 불가 결과를 나중 결과로 덮어쓰지 않는다. 값·절대 경로·토큰은 쓰지 않는다.

## Source

| 항목 | 값 |
|---|---|
| ControlProof branch / 시작 HEAD | `005-web-workbench-report` / `c208604` |
| WhyYou | `bosung/controlproof-n02-integration` `374b122` (이번 세션에서 읽기·실행 없음) |
| Spec 004 재시험 정리 확인 경로 수정(PR #2) | 2026-10-08 세션 시작 시 원격 Spec 004 브랜치에 미병합 → merge 건너뜀(T061에서 다시 확인) |

## T001 starting regression (2026-10-08)

```text
.venv python -m ruff check .   -> All checks passed!
.venv python -m pytest -q      -> 943 passed in 252.88s
```

## 기록 틀 (T003)

### 엔진 보완 RED → GREEN (Phase 2)

| 작업 | 시험 파일 | RED(명령·수치) | GREEN(명령·수치) | 바꾼 기존 기대값 |
|---|---|---|---|---|
| T004 → T009·T010 | `tests/unit/test_output_paths.py` | `pytest -q <파일>` → 17 failed, 1 passed | 18 passed | 없음 |
| T005 → T011 | `tests/unit/test_scan_strict.py` | 4 failed, 1 passed | 5 passed | 없음 |
| T005 → T012 | `tests/contract/test_scan_bundles_script.py` | 수집 단계 ImportError(`scripts.scan_bundles` 없음) | 2 passed | 없음 |
| T006 → T010·T013·T014 | `tests/contract/test_cli_output_additions.py` | 10 failed(`result_kind` 없음, JSON 사용법 오류 없음, H-03 정리 traceback, show·verify가 환경 변수 무시) | 10 passed | 없음 |
| T007 → T015 | `tests/unit/test_evidence_index.py` | 5 failed(`evidence_index` 없음), 1 passed(`evidence_links` 그대로) | 6 passed | 없음 |
| T008 → T017 | `tests/contract/test_verify_redaction_profile.py` | 5 failed, 1 xfailed(strict, T020 대기) | 5 passed, 1 xfailed | 없음 |

- T006 노트: 기존 기대값 중 바꿀 것이 없다. `tests/unit/test_redaction_security.py`의 `bundle_path` 시험은 `redact()`를 직접 부르고 `redact()`는
  그대로라 영향이 없다. 실행 시험에서 깨진 기존 시험은 1개(`tests/contract/test_cli_profiles_v2.py::test_exit_codes_stay_stable_and_semantic_overrides_are_not_options`,
  `cli._parser()`를 직접 불러 `SystemExit`를 기대)였고, 시험은 고치지 않고 구현을 바꿨다(`--json`이 있을 때만 JSON 사용법 오류, 그 밖에는
  argparse 그대로).

### T018 Foundation gate (2026-10-09)

```text
.venv python -m pytest -q      -> 989 passed, 1 xfailed in 312.78s   (시작 943 + 새 시험 46; xfailed = T008의 T020 대기 strict 시험)
.venv python -m ruff check .   -> All checks passed!
git diff --check               -> 출력 없음
```

- 중간 실행(구현 직후)은 988 passed, 1 failed였다. 실패 1개는 위 T006 노트의 기존 시험이고 구현을 고쳐 통과했다(기존 기대값 변경 없음).

### 기존 bundle 검사 (T016, T019)

| PC | root 라벨 | bundle 수 | 규칙별 v1 | 규칙별 v2 | v2에서 새로 걸린 bundle |
|---|---|---|---|---|---|
| 연우 | `yeonwoo-repo`(저장소 `.controlproof/runs`, 추적 부모 `15cef078…` 포함) | 3 | 0건(모든 규칙) | 0건(모든 규칙) | 0 |
| 연우 | `yeonwoo-spec004-diagnostics`(`cp-local` 보관, Spec 004 진단) | 3 | 0건 | 0건 | 0 |
| 연우 | `yeonwoo-spec003-t084-zips`(`cp-local` 보관 zip 2개를 임시 폴더로 풀어 검사) | 2 | 0건 | 0건 | 0 |
| 연우 합계 | 3 root | 8 폴더(서로 다른 Run 6개; zip 2개는 저장소의 두 Run과 같은 Run) | 0건 | 0건 | 0 |

- T016 명령(2026-10-09): `python -m scripts.scan_bundles --run-root <root> --label <라벨> … --out <scratch>/scan-before-v2-yeonwoo.json` →
  `bundles=8 newly_flagged=0 v1={} v2={}`. 검사 전후 세 root의 파일 해시 126개와 zip 2개의 SHA-256이 같았다(읽기만 함). 보고서는 저장소에
  넣지 않았다. 범위 결정은 implementation-decisions ID-005-05.
- 결론: 이 PC의 기존 bundle에는 v2에서 새로 걸리는 것이 없다. 보성 PC(T019) 결과는 아직 없다.

### Phase 3 US1 RED → GREEN (2026-10-09)

| 작업 | 시험 파일 | RED | GREEN | 바꾼 기존 기대값 |
|---|---|---|---|---|
| T021 → T027 | `tests/unit/test_catalog_matrix_parity.py` | 7 errors(카탈로그 파일 없음) | 7 passed | 없음 |
| T022 → T028 | `tests/unit/test_web_badges.py` | 수집 단계 ImportError(`engine.web.badges` 없음) | 3 passed | 없음 |
| T023 → T029 | `tests/unit/test_web_readmodel_workbench.py` | 수집 단계 ImportError(`readmodel`) | 10 passed | 없음 |
| T024 → T030 | `tests/unit/test_web_preflight.py` | 수집 단계 ImportError(`preflight`) | 8 passed | 없음 |
| T025 → T031 | `tests/contract/test_web_http.py` | 수집 단계 ImportError(`server`) | 18 passed | 없음 |
| T026 → T032·T033 | `tests/web/test_workbench_screen.py` | 수집 단계 ImportError(`server`) | 20 passed(1280·1024px 각 10) | 없음 |

- 명령: `.venv python -m pytest -q <파일>`. 브라우저 시험은 Playwright 기본 Chromium(headless shell)이 이 PC에 설치돼 있지 않아 설치된 Edge 채널
  (`channel="msedge"`, 154.0.4258.53)로 실행했다(R-014). 시험이 띄운 서버는 시험 끝에 모두 종료했다(fixture shutdown).
- 간헐 실패 수정(ID-005-06): `tests/unit/test_bundle_verify.py` 30회 반복 실패 0회.

### T034 US1 gate (2026-10-09)

```text
.venv python -m pytest -q      -> 1055 passed, 1 xfailed in 432.81s   (Foundation 989 + US1 새 시험 66; xfailed = T020 대기)
.venv python -m ruff check .   -> All checks passed!
git diff --check               -> 출력 없음
```

- 기존 시험 기대값 변경 없음. 시험은 서버를 같은 프로세스의 스레드로 띄우고 끝에 모두 종료한다(남은 서버 프로세스 없음).

### Phase 4 US2 · Phase 5 US3 RED → GREEN (2026-10-09)

| 작업 | 시험 파일 | RED | GREEN | 바꾼 기존 기대값 |
|---|---|---|---|---|
| T035 → T038 | `tests/unit/test_web_readmodel_run.py` | 15 failed(`run` 없음) | 15 passed | 없음 |
| T036 → T038·T040 | `tests/unit/test_web_evidence_view.py` | 7 failed | 7 passed | 없음 |
| T036 → T039 | `tests/unit/test_web_memos.py` | 수집 단계 ImportError(`engine.web.memos` 없음) | 17 passed | 없음 |
| T036·T040 | `tests/contract/test_web_http_us2.py`(경로·422·메모·보고서·필드 가림 없음) | 구현과 함께 추가 | 8 passed | 없음 |
| T037 → T041 | `tests/web/test_run_screen.py` | 14 failed, 12 errors(화면 없음·콘솔 404) | 14 passed(1280·1024px 각 7) | 없음 |
| T043 → T045 | `tests/unit/test_web_readmodel_report.py` | 10 failed(`report` 없음) | 10 passed | 없음 |
| T044 → T046 | `tests/web/test_report_screen.py` | 6 failed, 2 errors | 6 passed(1280·1024px 각 3) | 없음 |
| (ID-005-08) | `tests/unit/test_catalog_matrix_parity.py::test_explanation_texts_are_whole_values` | 이전 카탈로그에서 20곳 잘림 확인 | 8 passed(파일 전체) | 없음(시험 추가) |
| (승인된 변경) | `tests/contract/test_web_http.py::test_route_table_has_no_run_retest_or_cleanup_start` | — | 18 passed(파일 전체) | POST 목록 `["/preflight"]` → `["/preflight", "/runs/{run_id}/memos"]`(연우 승인) |

- ID-005-01 세 경우(T035): ① ABORTED + 필수 증적 링크 누락만 → 실행 상태 "중단(ABORTED)"을 먼저, "봉인 무결성 확인됨 + 중단으로 빠진 증적: EV-06, EV-07",
  봉인 판정은 그대로 함께(대상 서비스 판정 아님) ② COMPLETED + 증적 링크 누락(EV-01, 재봉인 사본) → 무결성 실패, 판정·규칙·증적 없음 ③ 해시 불일치
  (판정 파일 변경) → 무결성 실패. 세 경우 모두 명령줄 `verify_bundle` 결과는 그대로(① INVALID).
- 브라우저: Playwright 기본 Chromium 없음 → 설치된 Edge 채널(154.0.4258.53). 시험이 띄운 서버는 fixture 끝에 모두 종료.

### T042 US2 · T047 US3 gate (2026-10-09)

```text
.venv python -m pytest -q      -> 1133 passed, 1 xfailed in 208.35s   (US1 1055 + US2·US3 새 시험 78; xfailed = T020 대기)
.venv python -m ruff check .   -> All checks passed!
git diff --check               -> 출력 없음
```

### 결과 화면 가독성 보정 T057a~T057d RED → GREEN (2026-10-09, ID-005-09)

| 작업 | 시험 파일 | RED | GREEN | 바꾼 기존 기대값 |
|---|---|---|---|---|
| T057a~d | `tests/unit/test_web_run_readability.py` | 11 failed | 11 passed | 없음 |
| T057a~d | `tests/web/test_run_readability_screen.py` | 8 failed | 8 passed(1280·1024px 각 4) | 없음 |

- 바뀌기 전 → 후: ① 중단된 Run "봉인 무결성 확인됨 (VERIFIED)" → "봉인 무결성 확인됨(봉인 파일·manifest 일치) · 명령줄 verify: INVALID(중단으로 빠진 필수 증적 EV-06, EV-07)"
  ② 단계 ID 나열 → 구간별 문장(정의된 단계 수, 적용·해제한 시험 조건, 복구 결과), 단계 ID는 개발자용 ③ "수집한 원본 기록" 반복 → "EV-03 장애 발동과 리포트 상태 · 주입 #n",
  규칙 칸은 묶어서 "… 16개" ④ 영어 미검증 범위·snapshot 해시 → 한국어 설명·"WhyYou commit aaaaaaa", 원문은 개발자용.
- 함께 고친 것: 수집 단계 값 `RECOVERED`를 화면이 `RECOVERY`로 찾아 "기록 없음"으로 보이던 US2 표시 오류. 새 필드 이름 `evidence_groups[].name`이 경계 가림에
  걸린 것을 ID-005-08 시험이 잡아 `label`로 바꿈.

### Phase 6 US4 RED → GREEN (2026-10-09)

| 작업 | 시험 파일 | RED | GREEN | 바꾼 기존 기대값 |
|---|---|---|---|---|
| T048 → T050 | `tests/unit/test_web_readmodel_scenario.py` | 15 failed | 15 passed | 없음 |
| T049 → T051 | `tests/web/test_scenario_screen.py` | 12 failed, 10 errors | 12 passed(1280·1024px 각 6) | 없음 |

- 준비 상태 확인은 실제 웹 실행기(`PreflightRunner`)에 가짜 하위 프로세스를 넣어 시험했다(E-01 READY, E-02 사용법 오류 → "확인 도구 오류"). 대상 서비스 호출 없음.

### T052 US4 gate (2026-10-09)

```text
.venv python -m pytest -q      -> 1179 passed, 1 xfailed in 568.74s, 그리고 같은 실행에 먼저 써 둔 US5 시험(T053·T054)의 RED 14 failed, 4 errors
.venv python -m ruff check .   -> All checks passed!
git diff --check               -> 출력 없음
```

- US5 시험 두 파일을 뺀 나머지는 모두 통과했다(US5 RED는 아래 US5 표에 다시 적음).
- 정정(같은 날): 위 `ruff` 줄은 잘못 적었다. 그 실행의 ruff 출력은 실제로 오류였고(US4 시험 파일의 SIM115 1건과 먼저 써 둔 US5 시험의 미사용 변수 4건),
  확인하지 않고 적었다. 커밋 `5eb907f`에 SIM115 1건이 들어갔다. US5 작업에서 모두 고쳤고, 고친 뒤의 ruff 결과는 T057 gate에 적는다.

### Phase 7 US5 RED → GREEN (2026-10-09)

| 작업 | 시험 파일 | RED | GREEN | 바꾼 기존 기대값 |
|---|---|---|---|---|
| T053 → T055 | `tests/unit/test_web_readmodel_compare.py` | 8 failed(T052 실행에 포함) | 8 passed | 없음 |
| T054 → T056 | `tests/web/test_compare_screen.py` | 6 failed, 4 errors(T052 실행에 포함) | 6 passed(1280·1024px 각 3) | 없음 |

- 계보 형식별 결과: Spec 004(E-01) `RETEST_LINK` 부모 불변 true, Spec 002(E-03) `CROSS_RUN_REFERENCE` true, Spec 001(H-03) `NONE_LEGACY` null(계보 문제 아님, 부모 무결성 표시).
  부모를 다시 봉인해 digest가 바뀐 계보 → `PARENT_DIGEST_CHANGED`, 부모 변조 → `PARENT_NOT_VERIFIED`, 두 경우 비교 항목 없음.

### T057 US5 gate (2026-10-09)

```text
.venv python -m pytest -q      -> 1193 passed, 1 xfailed in 379.20s
.venv python -m ruff check .   -> All checks passed!   (T052 정정분 포함)
git diff --check               -> 출력 없음
```

### Phase 8 Polish T058~T060 (2026-10-09)

| 작업 | 시험·확인 | 결과 |
|---|---|---|
| T058 | `tests/integration/test_web_response_redaction.py`: 모든 경로(HTML·JSON, ACTUAL·DEMO, 합성 bundle 전 종류 + 이스케이프된 Windows 사용자 경로를 담은 재봉인 bundle)의 응답 1235개를 `scan_bytes_strict`·v2 경로 정규식으로 검사 | 위반 0(200 응답 1180, 404 응답 55). 경로가 든 증적은 원문 대신 사유만 보임. 이미 만든 기능을 검사하는 시험이라 RED 단계 없음 |
| T059 | `tests/integration/test_web_performance.py`: bundle 30개, verify 캐시 데움 | 워크벤치 최대 0.217초, 결과 화면 첫 요청 0.366·0.252·0.221초, 데운 뒤 0.234초(기준 2초). RED 단계 없음 |
| T060 | 새 checkout: origin `005-web-workbench-report` `8a1fd2d`를 scratch 폴더에 clone(clean), 기존 `.venv` Python 3.12.10을 의존성만 재사용(`import engine`이 새 checkout을 가리킴 확인) | §3 `ruff` All checks passed · `pytest -q` 1196 passed, 1 xfailed in 532.59s · `pytest -q tests/web` 66 passed(Edge 채널). §4 문서 명령 그대로는 실패(`prepare_web_demo --out` 없는 인자) → 고친 명령으로 DEMO bundle 16개 생성, `python -m engine.web` 기동, `/demo/`(DEMO 띠, 12줄)·`/demo/report`·`/demo/scenarios/E-01` 200, `/`·`/report`는 DEMO 띠 없음, 서버 종료 확인(8765 대기 없음) |

- 고친 문서: `quickstart.md` §2(새 checkout에서 기존 환경 재사용 방법과 확인 명령, 브라우저 자동 선택), §3(예상 결과에 xfailed 1개·소요 시간·시험 서버 종료),
  §4(잘못된 `--out` 인자 삭제, 기본 DEMO root·다시 만들기·종료 방법, 화면 주소 목록).
- 개인 절대 경로 검사: 새 checkout의 `specs/005-web-workbench-report`·`docs`·`AGENTS.md`의 Markdown에서 사용자 홈 경로 형태 0건(시험용 가짜 이름 제외).

### 사용자 스토리 gate

| Phase | 시험 | 결과 |
|---|---|---|
| Phase 3 US1 | T021~T026 GREEN, 전체 회귀, ruff | PASS(2026-10-09, 위 T034) |
| Phase 4 US2 | T035~T037 GREEN, 전체 회귀, ruff | PASS(2026-10-09, 위 T042) |
| Phase 5 US3 | T043~T044 GREEN, 전체 회귀, ruff | PASS(2026-10-09, 위 T047) |
| Phase 6 US4 | T048~T049 GREEN, 전체 회귀, ruff | 시험 PASS(2026-10-09, 위 T052; US5 RED 시험 제외). ruff는 그때 실패였고 T057에서 통과(정정) |
| Phase 7 US5 | T053~T054 GREEN, 전체 회귀, ruff | PASS(2026-10-09, 위 T057) |
| Phase 8 Polish | T058·T059, 새 checkout 전체 회귀(`8a1fd2d`, 코드는 이후 문서만 바뀜), ruff, diff check | PASS(2026-10-09, 위 T060) |

### Phase 9 준비(공식 Run 아님, 2026-10-09)

Run·재시험·cleanup-confirm은 하지 않았다. 환경을 띄워 7개 프로필의 preflight만 확인했다. preflight 전후로 설정된 run root에 새 Run 폴더가 생기지 않았다.

| 항목 | 값 |
|---|---|
| ControlProof | `005-web-workbench-report` `621816f`(origin과 같음), dirty 없음, Python 3.12.10(기존 `.venv`) |
| WhyYou(통합 대상) | `bosung/controlproof-n02-integration` `374b122`, dirty 없음 |
| WhyYou(E-01 부모용) | git worktree `../gbsa_aws-ce8d862`(workspace 기준), `ce8d862` detached, 새 브랜치 없음, dirty 없음. 이 폴더에서는 커밋·push 안 함 |
| 실행 환경 | `LOCAL_EMULATED`, AWS `NOT_RUN`, WhyYou 로컬 Docker(PostgreSQL·LocalStack·Mailpit) + host API·작업자 4개 |

| 프로필 | 대상 commit | fixture | readiness | READY가 아닌 check |
|---|---|---|---|---|
| H03_DLQ_V2 | 374b122 | h03-report-v1 | RUNNER_NOT_READY (18 checks) | `reporting.ui.observe`: Playwright Chromium 미설치 |
| H03_MINIMAL_V1 | 374b122 | h03-report-v1 | RUNNER_NOT_READY (12 checks) | `reporting.ui.observe`: Playwright Chromium 미설치 |
| E03_BEFORE_V2 | 374b122 | h03-report-v1 | READY (15 checks) | 없음 |
| E03_AFTER_V2 | 374b122 | h03-report-v1 | READY (12 checks) | 없음 |
| N02_CONSENT_ORDER_V1 | 374b122 | h03-report-v1 | READY (16 checks) | 없음 |
| E02_SCORING_FREEZE_V1 | 374b122 | spec004-report-v1 | READY 16/16, scoring_rule_source MATCH | 없음 |
| E01_CITATION_EVIDENCE_V1 | 374b122 | spec004-report-v1 | READY 18/18 | 없음 |
| E01_CITATION_EVIDENCE_V1(부모용) | ce8d862 worktree | spec004-report-v1 | READY 18/18 | 없음 |

- H-03 원인 분류: **실행기 환경(ControlProof 쪽)**. 두 프로필 모두 실패 check는 회사 화면 관찰 하나이고 사유는 ControlProof의 브라우저 관찰 adapter가 쓰는
  Playwright 기본 Chromium이 이 PC에 설치되지 않은 것이다. seed·실행기 코드 결함이나 대상 버전(`374b122`) 차이로 보이는 신호는 없다(다른 check 모두 READY).
  고치지 않았다. 브라우저 check를 통과한 뒤에도 회사 콘솔(포트 5173)이 필요할 수 있는데, WhyYou checkout에 `node_modules`가 없어 `npm run dev:company`가
  시작되지 않았다(`npm ci` 필요). 이 둘은 공식 세션 전에 사람 승인 아래 설치해야 한다. Run을 해야만 확인할 수 있는 문제는 나오지 않았다.
- 대상 전환 방법(확인됨): fixture는 두 `.env`의 `CONTROLPROOF_MODEL_FIXTURE_ID`·`_DIGEST`를 `spec004-report-v1` 값으로 바꾸고(임베딩 fixture는
  `h03-embedding-v1` 유지) API·작업자를 다시 띄운다. ce8d862는 같은 Docker DB에 worktree 소스로 API·작업자를 띄우고(`PYTHONPATH`=worktree
  `backend/src`, 확인 출력이 worktree를 가리킴) ControlProof는 `WHYYOU_REPO_PATH`만 worktree로 바꿔 preflight했다(대상 commit `ce8d862` 확인).
  DB migration head는 374b122 기준 상태에서 ce8d862 코드의 `alembic upgrade heads`가 오류 없이 끝났다.
- 문서 차이: quickstart §5-1은 "Spec 004 quickstart §3·전환 절"을 가리키지만, Spec 004 quickstart §3의 격리 도구(`scripts/spec004_local.py`)는 `.env`가 없는
  별도 checkout만 받아(두 기본 checkout에는 `.env`가 있음) 이 PC 기본 배치로는 쓸 수 없고, "전환 절"도 없다. 위 `.env` 전환 방법이 실제로 동작했다.
  공식 세션 전에 quickstart §5를 이 방법으로 고친다.
- 이 PC 한정 사항(Spec 004 세션 인계와 같은 종류): Windows 앱 제어가 uv가 만든 `alembic.exe`·`uvicorn.exe` 실행을 막아 같은 명령을 WhyYou `.venv`
  Python의 `-m alembic`·`-m uvicorn`으로 실행했다(`scripts/local.ps1 up`은 Docker·local_infra까지 성공 후 alembic 단계에서 멈춤). PowerShell 5.1은 docker·
  alembic stderr를 오류로 보므로 그 출력은 따로 처리했다. WhyYou DB 포트 5433, ControlProof `.env` 수동 로드는 기존과 같다.
- 환경 정리: API·작업자 프로세스 0개, `docker compose down`(볼륨 2개 유지, 실행 컨테이너 0개). 두 `.env`는 시작 전 값으로 되돌렸고 SHA-256이 시작 전과 같다
  (작업 중 백업 사본은 삭제). 두 WhyYou checkout과 ControlProof의 `git status`는 비어 있다. 포트 5433·4566에는 Docker Desktop이 관리하는
  WSL 중계 프로세스(`wslrelay`)가 남아 있다(컨테이너는 없음). Docker Desktop 소유라 직접 종료하지 않았다. ce8d862 worktree는 공식 E-01 부모 Run용으로 남겨 둔다.

#### Phase 9 준비 2차(공식 Run 아님, 2026-10-09)

- 보성 승인(ID-005-10): PR 브랜치 선병합, T020을 T019보다 먼저.
- PR #2 브랜치 합치기(T061 일부): `origin/yeonwoo/004-retest-maintenance-path`(`cebf067`)를 005에 `--no-ff`로 합쳤다(merge `b106b55`, 충돌 없음; 변경 4파일,
  `engine/retest.py` 1줄). `tests/integration/test_spec004_retest_cleanup_path.py` 4 passed, 전체 `pytest -q` 1200 passed, 1 xfailed in 911.23s.
  PR #2는 004에 아직 병합 전이다(병합되면 004를 다시 합친다).
- T020 봉인 검사 v2 전환: 새 manifest에 `redaction_profile: controlproof.redaction.v2`, 작성기 쓰기 검사는 v2. T008 시험 6개 + 새 시험 1개 통과(strict-xfail 해제).
  추적 부모 `15cef078…`은 VERIFIED·v1 유지. 전환 직후 기존 시험 4개가 준비 단계 이유로 실패해 멈추고 보고했고, 승인을 받아 준비 단계만 고쳤다(ID-005-10
  "T020에 따른 시험 정리"). T019는 보성 검사 대기(ID-005-10).
- 환경 보완(연우 승인 뒤 다운로드):
  - Playwright Chromium: ControlProof `.venv` Python으로 `-m playwright install chromium` → Chrome Headless Shell 153.0.8010.12 설치, headless 실행 확인. 앱 제어 차단 없음.
  - 회사 콘솔: Node v24.19.0, WhyYou checkout에서 `npm ci` 성공(npm 11이 esbuild 설치 스크립트를 `allowScripts`로 건너뜀). `npm run dev:company`로 Vite가 뜨고 HTTP 200,
    끈 뒤 5173 대기 없음. `node_modules`는 git status에 나오지 않음. 앱 제어 차단 없음.
  - quickstart §5: "대상 환경 띄우기와 fixture 전환" 절(방법 A `.env` 전환, 방법 B Spec 004 격리 도구의 사용 조건, 이 PC 한정 사항)을 더했다.
- 정정(1차 기록): 1차 준비의 "API·작업자 프로세스 0개"는 틀렸다. 정지 확인이 `run_workers.py`·`uvicorn` 명령줄만 봤는데, 작업자 풀은 그와 다른 명령줄의
  multiprocessing 자식 프로세스라 남아 있었다(1차에서 띄운 세 번의 작업자 풀, 각 4개). 2차에서 부모가 없어진 고아 프로세스 16개(2차의 실패한 첫 기동분 4개
  포함)를 찾아 멈췄다. 이 고아 작업자의 heartbeat 때문에 N-02 preflight가 한 번 `an unmanaged worker attestation is active`로 막혔다. 이후 정지는 WhyYou
  `.venv`의 모든 python 프로세스를 대상으로 하고 남은 수를 센다.
- 2차 preflight(374b122는 WhyYou 기본 checkout, ce8d862는 worktree; 모두 dirty 없음):

| 프로필 | 대상 commit | fixture | readiness | READY가 아닌 check |
|---|---|---|---|---|
| H03_DLQ_V2 | 374b122 | h03-report-v1 | READY | 없음 |
| H03_MINIMAL_V1 | 374b122 | h03-report-v1 | READY | 없음 |
| E03_BEFORE_V2 | 374b122 | h03-report-v1 | READY | 없음 |
| E03_AFTER_V2 | 374b122 | h03-report-v1 | READY | 없음 |
| N02_CONSENT_ORDER_V1 | 374b122 | h03-report-v1 | READY | 없음(고아 작업자 정리 뒤) |
| E02_SCORING_FREEZE_V1 | 374b122 | spec004-report-v1 | READY 16/16, scoring_rule_source MATCH | 없음 |
| E01_CITATION_EVIDENCE_V1 | 374b122 | spec004-report-v1 | READY 18/18 | 없음 |
| E01_CITATION_EVIDENCE_V1(부모용) | ce8d862 worktree | spec004-report-v1 | READY 18/18 | 없음 |

  - 같은 날 앞서 한 번 띄운 API가 그 기동 작업이 끝나며 같이 종료돼 연결 오류로 나온 preflight 결과는 환경 문제로 버리고 위 표에 넣지 않았다.
- 환경 정리: WhyYou `.venv` python 프로세스 0개, 회사 콘솔 node 프로세스 0개, `docker compose down`(볼륨 2개 유지, 실행 컨테이너 0개), 8080·5173 대기 없음.
  두 `.env`는 시작 전 값으로 되돌려 SHA-256이 같음(백업 사본 삭제). WhyYou 두 checkout의 git status는 비어 있다. ce8d862 worktree는 유지.
- 2차 gate: `ruff check .` All checks passed · `pytest -q` 1202 passed in 763.80s(xfailed 0: T020 대기 시험이 통과로 바뀜, 새 시험 1개) · `git diff --check` 출력 없음.

### Actual validation (웹 PC 재실행, Phase 9)

공식 세션 2026-10-10(연우 PC). 이 기록들은 Spec 005 웹 검증용이며 각 시나리오의 공식 상태를 바꾸지 않는다(D-018 추가 결정 3).

- 시작 조건: 세 checkout clean(ControlProof `005-web-workbench-report` `9856a03`, WhyYou `bosung/controlproof-n02-integration` `374b122`,
  worktree `../gbsa_aws-ce8d862` `ce8d862` detached), PR #2 브랜치 `cebf067`이 005의 조상(T061 일부), T020 완료(`1c7e366`), 준비 2차 preflight 8/8 READY.
- tasks와 다르게 진행한 점(사유: 세션 지시, 연우 승인 2026-10-10):
  1. T063: H03_DLQ_V2가 예상과 다르면 원인만 분류하고 멈춘다. 고치지 않는다(실행기 수정은 남은 Run의 ControlProof source를 바꾸므로 따로 정한다).
  2. 독립 재현 gate는 "gate 후보"로만 기록한다(새 clone이 아닌 이 PC의 기존 clone, clean, 대상 `374b122`). 인정 여부는 보성이 정한다.
     → 2026-10-13 인정됨(D-019). 당시 지시는 그대로 두고, 현재 상태는 아래 Run 1 기록과 D-019로 판단한다.
  3. T069: tasks 범위(SC-001~007, SC-010, SC-011) 전체를 확인하고, 세션 지시의 세 가지(공식 상태와 분리 표시, VERIFIED, E-01 재시험 비교)를 따로 표시한다.
  4. 순서는 tasks·quickstart를 따르되, Run 8 뒤 WhyYou를 멈추기 전에 웹을 실제 root로 띄워 "준비 상태 확인"을 한 번 실행·저장 확인하고,
     그다음 WhyYou를 멈추고 fixture·`.env`를 되돌린 뒤 나머지 웹 확인을 한다(웹이 run root만으로 동작함을 보이기 위해).
  5. preflight는 시작 일괄(T062)과 Run마다 둘 다 한다.
- 예상(Run별 비교 기준): 1~4 PASS, 5 INCONCLUSIVE(A5·A7만 INSUFFICIENT_EVIDENCE), 6 PASS, 7 FAIL(A3만 FAIL, 공식 부모 `09c9d9bb`와 같은 모양), 8 PASS.
- 환경(방법 A, fixture `h03-report-v1`): 두 `.env` 시작 SHA-256 ControlProof `4E998770…0450`, WhyYou `0B7C4D1D…E942`(백업 사본은 checkout 밖).
  `docker compose up -d --wait`(PostgreSQL·LocalStack·Mailpit healthy), WhyYou `.venv` Python으로 `local_infra`·`alembic upgrade heads`(오류 없음),
  API(`uvicorn`, 8080) `/health/ready` ok(의존성 10개 ok), 작업자 "Started 4 workers", 회사 콘솔 5173 HTTP 200. run root `.controlproof/runs`(기존 Run 3개 있음).
- T062 일괄 preflight(374b122, dirty 없음, `LOCAL_EMULATED`, AWS `NOT_RUN`): H03_DLQ_V2 READY 18/18 · H03_MINIMAL_V1 READY 12/12 ·
  E03_BEFORE_V2 READY 15/15 · E03_AFTER_V2 READY 12/12 · N02_CONSENT_ORDER_V1 READY 16/16.
- Run마다: 실행 전 두 저장소 branch·HEAD·dirty와 preflight를 기록하고 연우 승인("실행") 뒤 실행, 실행 뒤 `show`·`verify`.

| 순서 | 시나리오·프로필 | WhyYou | ControlProof HEAD·dirty | preflight | Run ID | verdict / 복구 | manifest SHA-256 |
|---|---|---|---|---|---|---|---|
| 1 | H-03 `H03_DLQ_V2` | `374b122` dirty 0 | `9856a03` dirty 0 | READY 18/18 | `277d3f5a-766a-45ab-9f1d-28a3a30a82e6` | PASS(A1~A9 PASS) / 복구 SUCCEEDED, verify VERIFIED(33 files) | `3d6b0a85d2c657e4c3bedbfb5938399b8235ada488c0616bd641a340184fbcdf` |
| 2 | H-03 `H03_MINIMAL_V1` | `374b122` dirty 0 | `9856a03` dirty 0 | READY 12/12 | `1d573850-7635-4d96-b427-018f2a8a5d30` | PASS(A1~A6 PASS) / 복구 SUCCEEDED, verify VERIFIED(48 files) | `7f82de7059d73fb93d0d67f81bc641d6047a5df6d58f56075f4eea234bbace09` |
| 3 | E-03 `E03_BEFORE_V2` | `374b122` dirty 0 | `9856a03` dirty 0 | READY 15/15 | `fd48f7ff-f6bc-4bd3-9fc3-9083acfd0b23` | PASS(A1·A2·A3·A4·A7·A8 PASS) / 복구 SUCCEEDED, verify VERIFIED(23 files) | `aadcd70a9043423c937766a0113010bce59e6531edb3216e2e36bbf8275a2a92` |
| 4 | E-03 `E03_AFTER_V2` | `374b122` dirty 0 | `9856a03` dirty 0 | READY 12/12 | `064afdb0-a04b-4ce7-a283-b1a59aec0051` | PASS(A1·A5·A6·A8 PASS) / 복구 SUCCEEDED, verify VERIFIED(19 files) | `79037d811220d0a44f37de30a3e03d6d8a07f649101af2b730e25d688520c577` |
| 5 | N-02 `N02_CONSENT_ORDER_V1` | `374b122` dirty 0 | `9856a03` dirty 0 | READY 16/16 | `1767fb73-6a4f-4b0a-853d-d306052d5aa6` | INCONCLUSIVE(A1·A2·A3·A4·A6 PASS, A5·A7 INCONCLUSIVE `INSUFFICIENT_EVIDENCE`) / 복구 SUCCEEDED, verify VERIFIED(19 files) | `dc301399e8320205bc6ac3c5830d65c9fc2cc3ecacb25c1ea7e841744b0cf106` |
| 6 | E-02 `E02_SCORING_FREEZE_V1` | `374b122` dirty 0 | `9856a03` dirty 0 | READY 16/16, scoring_rule_source MATCH | `4a404c73-7690-4963-bf50-67fb5e9c9028` | PASS(A1~A3 PASS) / 복구 SUCCEEDED, verify VERIFIED(17 files, recompute MATCH) | `f3dbc56586458bbeab030a75e5b5334b4730f7e93c70e6eabf9f11008216a55a` |
| 7 | E-01 `E01_CITATION_EVIDENCE_V1`(부모) | `ce8d862` worktree, detached, dirty 0 | `9856a03` dirty 0 | READY 18/18 | `86cd0010-6f9c-48ef-99a3-5908dda0037c` | FAIL(A1·A2·A4 PASS, A3 FAIL) / 복구 SUCCEEDED, verify VERIFIED(17 files) | `fe5ac508ef664383d90990076de77ff3a34e4c0c9099630a1467d61afe18c6e5` |
| 8 | E-01 재시험(부모 `86cd0010`) | `374b122` dirty 0 | `9856a03` dirty 0 | READY 18/18 | `7f25b475-b3ad-4877-b185-8b83cb397047` | PASS(A1~A4 PASS, A3 FAIL→PASS) / 복구 SUCCEEDED, verify VERIFIED(19 files), 부모 불변 | `173d34dd222562550b4a869333655d33bec25f5e76294a47cc2a624e2ee8cb3f` |

Run 상세:

- Run 1(H03_DLQ_V2): 예상(공식 상태 PASS)과 같음. `redaction_profile: controlproof.redaction.v2`(manifest 최상위; 파일 항목의 `redaction_profile`은
  `controlproof-redaction-v1` 표기, 관찰만 기록), 소요 207.6초(started→ended). label `spec005-web-h03-dlq`.
  **독립 PC 재현 gate 인정됨**(플레이북 §6, D-019, 제품 책임자 승인 2026-10-13). 인정 범위:
  (1) 새로 clone한 checkout이 아니라 이 PC의 **기존 clean clone**을 사용한 별도 PC 재현이다.
  (2) 실행 환경은 ControlProof `9856a03` dirty 0, WhyYou `bosung/controlproof-n02-integration` `374b122` dirty 0, `LOCAL_EMULATED`,
  fixture `h03-report-v1`, preflight READY 18/18이다.
  (3) 결과는 A1~A9 PASS, 복구 SUCCEEDED, bundle verify VERIFIED(33 files),
  manifest SHA-256 `3d6b0a85d2c657e4c3bedbfb5938399b8235ada488c0616bd641a340184fbcdf`이다.
  (4) 플레이북 §6이 지정한 과거 commit과 **동일 조건의 재현이 아니다.** 현재 통합 대상에 대한 교차 PC 재현이다.
  이 인정은 H-03 `H03_DLQ_V2` 한 건에만 적용한다. 다른 시나리오나 AWS까지 독립 검증한 것으로 확대하지 않으며(AWS는 `NOT_RUN` 유지),
  main 병합은 별도 승인이 남는다.
  봉인 뒤 서비스 정지: Run 1 봉인(08:25:51Z)·verify(08:26:09Z) 뒤, Claude Code가 세션 대기 중 메모리 부족으로 자기 백그라운드 셸(API·작업자·콘솔)을
  정리했다. 08:27:03Z Run 2 preflight가 READY 12/12(API 로그 응답 있음)였으므로 정지는 봉인 뒤다. 연우가 Run 1을 공식 기록으로 확정했다(2026-10-10).
  다시 띄운 서비스도 대기 중 같은 이유로 정리돼 09:11:58Z Run 2 preflight는 무효로 했다. 이후 WhyYou API·작업자·콘솔은 연우가 별도 PowerShell 창에서
  checkout 밖 로컬 폴더의 실행 스크립트(WhyYou `.env`를 프로세스에 불러와 WhyYou `.venv` Python으로 실행, `WY_SRC`가 없으면 `PYTHONPATH`를 지움)로
  띄웠다. 고아 작업자는 두 번 모두 0개였다.
- Run 2(H03_MINIMAL_V1): 예상(PASS)과 같음. preflight READY 12/12(13:40:28Z, 연우가 띄운 서비스). `redaction_profile: controlproof.redaction.v2`,
  소요 71.3초. label `spec005-web-h03-minimal`. 이 프로필(Spec 001 bundle)은 ControlProof commit을 bundle에 담지 않아 실행 전 기록(`9856a03` dirty 0)이 근거다.
- Run 3(E03_BEFORE_V2): 예상(PASS)과 같음. bundle 환경 snapshot: ControlProof `9856a03` dirty false, WhyYou `374b122` dirty false(Run 1도 같음).
  `redaction_profile: controlproof.redaction.v2`, 소요 193.0초. label `spec005-web-e03-before`.
- Run 4(E03_AFTER_V2): 예상(PASS)과 같음. bundle 환경 snapshot ControlProof `9856a03` dirty false, WhyYou `374b122` dirty false.
  `redaction_profile: controlproof.redaction.v2`, 소요 11.0초. label `spec005-web-e03-after`. preflight(13:59:50Z)와 Run 시작(15:03:40Z) 사이 승인 대기 약 64분.
- Run 5(N02_CONSENT_ORDER_V1): 예상(INCONCLUSIVE, A5·A7만 `INSUFFICIENT_EVIDENCE`)과 같음. CLI 종료 코드 4(INCONCLUSIVE). 사유: A5 "DOCUMENT_ANALYSIS 경로의
  요청·시작·결과 사건 중 일부가 없습니다", A7 "정상 재시도 뒤 A5 처리 순서를 PASS로 확인하지 못했습니다"(격리 환경 예상과 같음). FAIL 0.
  bundle 환경 snapshot ControlProof `9856a03` dirty false, WhyYou `374b122` dirty false. `redaction_profile: controlproof.redaction.v2`, 소요 124.2초.
  label `spec005-web-n02`. 웹 검증용 기록이며 N-02 공식 상태는 Spec 003 converge를 따른다.
- fixture 전환(Run 5 뒤): 두 `.env`의 `CONTROLPROOF_MODEL_FIXTURE_ID`·`_DIGEST` 두 줄만 `spec004-report-v1`(digest `e15ec379…`, `controlproof:spec004-report-v1`의
  SHA-256)로 바꿨다(임베딩 fixture `h03-embedding-v1` 유지). 전환 뒤 SHA-256 ControlProof `A79A5BAA…`, WhyYou `83ACB28A…`. 연우가 API·작업자 창을 멈추고
  남은 WhyYou 프로세스 0개 확인 뒤 다시 띄웠다(같은 Docker DB, 볼륨 유지). 새 프로세스 생성 시각 15:33Z, API ready ok.
- Run 6(E02_SCORING_FREEZE_V1): 예상(PASS)과 같음. preflight `model.fixture.read` READY(spec004-report-v1), `scoring.rule.source.read` READY.
  bundle 환경 snapshot ControlProof `9856a03` dirty false, WhyYou `374b122` dirty false, fixture `spec004-report-v1`. verify `recompute_reexecution=MATCH`.
  `redaction_profile: controlproof.redaction.v2`, 소요 38.0초. label `spec005-web-e02`.
- Run 6 뒤 약 15시간 쉬고 이어 감(2026-10-11). 재개 확인: 두 `.env`는 `spec004-report-v1` 그대로(SHA-256과 수정 시각이 전환 직후와 같음),
  run root의 Run 폴더는 이전 3개 + 이 세션 6개로 그 사이 새 Run 없음, `locks` 비어 있음, `blocks`에는 이전부터 있던 maintenance 기록 1개뿐.
  API·작업자·회사 콘솔 모두 15:29~15:30 KST에 새로 띄운 프로세스였다.
- E-01 부모 전환: 연우가 API·작업자 창을 ce8d862 worktree 소스로 다시 띄웠다. 두 창의 확인 출력에서 `PYTHONPATH`와 `interview_evidence.__file__`이
  모두 worktree의 `backend/src`를 가리켰다(창 1 Uvicorn running, 창 2 Started 4 workers, 프로세스 6개, 8080 listen). API
  `/internal/controlproof/health`의 fixture는 `spec004-report-v1`. ControlProof는 `WHYYOU_REPO_PATH`만 worktree로 바꿨다(`.env` 파일은 그대로).
  Run 7 동안 백엔드(API·작업자)는 `ce8d862` worktree, 회사 콘솔 프론트는 기본 checkout(`374b122`)이었다. 판정에는 무관하다고 보지만 기록으로 남긴다.
  worktree에서는 커밋·push·브랜치 생성을 하지 않았다(detached 유지).
- Run 7(E-01 부모, `ce8d862`): 예상(FAIL, A3만 FAIL)과 같음. CLI 종료 코드 3(FAIL). A3 "P1: an affected item kept its score and citation after evidence
  removal"(근거 제거 뒤 영향 항목 1개가 표시 없이 점수·인용을 유지). 공식 부모 `09c9d9bb`(Spec 004 validation: 3 / FAIL, A1 PASS·A2 PASS·A3 FAIL·A4 PASS,
  SUCCEEDED / VERIFIED 17 files)와 같은 모양. 봉인만 하고 고치지 않았다. bundle 환경 snapshot ControlProof `9856a03` dirty false, WhyYou `ce8d862`
  dirty false, target snapshot `GIT_WORKTREE` `ce8d862`, fixture `spec004-report-v1`. `manual_cleanup_required: false`라 cleanup-confirm 불필요.
  `redaction_profile: controlproof.redaction.v2`, 소요 40.1초. label `spec005-web-e01-parent`.
  소스 구분: target snapshot `git_commit_sha` `ce8d8620…`, ControlProof `WHYYOU_REPO_PATH`=ce8d862 worktree. (`source_kind`는 WhyYou 어댑터가 항상
  `GIT_WORKTREE`로 고정하는 "git 작업 트리 identity" 표시라 기본 checkout과 git worktree를 구분하지 못하므로 쓰지 않는다. Run 1~8 모두 같은 값.)
- E-01 재시험 전환: 연우가 API·작업자 창을 기본 checkout(`374b122`)으로 다시 띄웠다(새 프로세스 15:44:21·15:44:36 KST). 확인 출력: 창 1 `file=`이
  기본 checkout `backend/src`(`PYTHONPATH=` 줄은 화면 위로 잘림), 창 2 `PYTHONPATH= None`, `file=` 기본 checkout. API ready ok, fixture `spec004-report-v1`.
  Run 8 동안 백엔드(API·작업자)와 회사 콘솔 프론트 모두 기본 checkout `374b122`였다. ControlProof `WHYYOU_REPO_PATH`는 `.env` 원래 값(기본 checkout).
- Run 8(E-01 재시험, `retest 86cd0010… --label spec005-web-e01-retest`, 같은 run root `.controlproof/runs`): 예상(PASS, A3 FAIL→PASS)과 같음.
  A3 actual: 영향 항목 1개가 availability 표시를 노출(`indicators` 1건, `unexposed`·`changed_without_indicator` 비어 있음). A4 read_equal·record_equal true.
  공식 child `a5ad4676`(COMPLETED / PASS, A1~A4 PASS, SUCCEEDED / VERIFIED, 19 registered files, block·manual cleanup 없음)과 같은 모양.
  retest-diff: 바뀐 필드는 `whyyou_commit.commit_sha` `ce8d862`→`374b122` 하나, 시나리오·프로필·fixture 불변, 새 lane manifest, `reused_identities` 없음.
  bundle 환경 snapshot ControlProof `9856a03` dirty false, WhyYou `374b122` dirty false, fixture `spec004-report-v1`. `parent_run_id` `86cd0010…`,
  `manual_cleanup_required: false`. `redaction_profile: controlproof.redaction.v2`, 소요 42.1초.
  부모 불변: 실행 전·후 manifest SHA-256 `fe5ac508…` 같음, `bundle_digest` `75c10fe6…` 같음, 폴더 18개 파일 해시 목록 SHA-256 `3ed62134…` 같음
  (파일별 차이 0), 실행 뒤 부모 `verify` VERIFIED. retest 명령 자체의 부모 불변 검사(`assert_parent_unchanged`)도 통과.
- 웹 준비 상태 확인(WhyYou를 멈추기 전, 세션 지시 4): 연우가 웹을 `--run-root .controlproof/runs`로 띄웠다(127.0.0.1:8765). E-02 시나리오 상세에서
  "준비 상태 확인"을 한 번 눌렀다. 화면: READY 배지와 확인 시각 2026-10-11 15:56(KST) 표시(화면에는 체크 수를 표시하지 않음). 저장: run root가 아닌
  웹 상태 폴더 `.controlproof/web/preflight/E-02--E02_SCORING_FREEZE_V1.json`과 `history.jsonl`(git 무시 대상)에 readiness READY, capabilities 16/16,
  checked_at 06:56:10Z, exit 0, 대상 `374b122`, fixture `spec004-report-v1`. `/api/scenarios/E-02`의 readiness도 같은 값(READY, 16/16, 같은 checked_at,
  recorded true). Run 폴더 수는 확인 전후 모두 11개(이전 3 + 이 세션 8)로 새 Run을 만들지 않았다. ControlProof git status 비어 있음.
- E-01 준비 상태 확인(정지 전, 연우 지시): 누르기 전 서비스 생존 확인(API ready ok 의존성 10개, 콘솔 200, WhyYou python 12개 = API·작업자 부모·작업자 4개 각
  launcher+실행 Python 쌍, 8080·5173 listen). 브라우저 자동화로 누른 첫 시도는 제출되지 않았고(저장 파일·preflight 하위 프로세스 없음, 화면 "확인 기록 없음"),
  사람이 직접 누르니 정상 동작했다. UI 결함이 아니라 자동화 환경 문제로 분류한다. 화면: READY 배지, "확인 2026-10-12 11:47"(KST).
  저장 `.controlproof/web/preflight/E-01--E01_CITATION_EVIDENCE_V1.json`: READY, capabilities 18/18, checked_at 2026-10-12T02:47:07Z, exit 0,
  result_kind READINESS(error_kind 없음), 대상 `374b122` dirty false, fixture `spec004-report-v1`. `history.jsonl` 2줄(E-02, E-01).
  `/api/scenarios/E-01` readiness: READY, 18/18, 같은 checked_at, recorded true. Run 폴더 11개 그대로, ControlProof git status 비어 있음.
  T069 SC-010 확인에 이 화면을 쓴다. H-03·E-03·N-02는 fixture가 `h03-report-v1`이 아니라서 누르지 않았다.
- 환경 정지·원복(2026-10-12): 연우가 API·작업자·콘솔 창을 멈춘 뒤 남은 프로세스를 셌다. API·작업자 python 0개(launcher가 띄운 실행 Python 포함, 명령줄 기준),
  WhyYou `.venv` python 0개, 콘솔 node·vite 0개, 8080·5173 대기 없음. 두 `.env`는 백업 복사가 아니라 바뀐 두 줄(`CONTROLPROOF_MODEL_FIXTURE_ID`·`_DIGEST`)만
  `h03-report-v1` 값으로 되돌렸고, SHA-256이 시작 전과 같다(ControlProof `4E998770…`, WhyYou `0B7C4D1D…`). 같음을 확인한 뒤 checkout 밖 백업 사본을 지웠다.
  `docker compose down`(종료 코드 0): 실행 컨테이너 0개, 볼륨 2개 유지. ControlProof `9856a03`, WhyYou `374b122`, worktree `ce8d862`(detached) 모두
  git status 비어 있음. worktree는 남겨 둔다.

#### T069 웹 확인(실제 run root, WhyYou 꺼진 상태, 2026-10-12)

- 조건: WhyYou API(8080)·회사 콘솔(5173) 대기 없음, Docker 실행 컨테이너 0개인 상태에서 연우가 웹을 `--run-root .controlproof/runs`로 띄웠다
  (127.0.0.1:8765, ControlProof `.env`는 원복된 `h03-report-v1`). 준비 상태 확인 버튼은 누르지 않았다. 확인은 GET 화면·`/api/*` 111개 응답 수집과
  브라우저 화면으로 했다. 웹이 실행 없이 run root(와 웹 상태 폴더)만으로 읽힌다는 근거다.
- 띄운 직후: 저장된 준비 상태 2건이 그대로 보임(E-02 READY 16/16 2026-10-11T06:56:10Z, E-01 READY 18/18 2026-10-12T02:47:07Z, 출처 PREFLIGHT, recorded true,
  `history.jsonl` 2줄). `.env` 원복은 저장 기록에 영향이 없다. 웹이 run root의 Run 11개(이전 3 + 이 세션 8)를 모두 읽음(실행 상세 11개 모두 200).
- SC-001: PASS. 12개 상태가 범위표(`docs/product/ControlProof_MVP_Scenario_Coverage_Matrix.md`)와 12/12 일치. 집계 PASS 4 · FAIL 0 · 판정 불가 4
  (INSUFFICIENT_EVIDENCE 1 + NO_TEST_TARGET 3) · NOT_RUN 4. NOT_RUN·NO_TEST_TARGET·INCONCLUSIVE 행 중 PASS 표시·집계 0건. 실행 처리 EXECUTED 5 · NOT_RUN 4 · NO_TEST_TARGET 3.
- SC-002: PASS. Run 11개 모두 웹 `/api/runs/{id}`의 판정·assertion 상태·reason code·무결성이 CLI `show`·`verify`와 같다(불일치 0). 무결성이 깨진 실제 기록
  `e2e8e71d…`(Spec 003 T084 시도 2, 봉인 뒤 `verify` INVALID)는 웹에서 "봉인 뒤 기록이 바뀌었습니다 (INVALID)"로 표시되고 판정을 보이지 않는다(CLI verify도 INVALID).
  복구 실패 기록 `15cef078…`는 복구 FAILED·INCONCLUSIVE로 CLI와 같다.
- SC-003: PASS. 이 세션 8개 Run의 PASS·FAIL assertion 41개 모두 실행 결과 화면에서 첫 증적 링크가 열리고(200) 증적 화면에 SHA-256이 보인다
  (워크벤치 → 실행 결과 → 증적, 2번 이동으로 기준 "3번 이하" 충족). 단서: Spec 002 형식 프로필(Run 1의 A1~A6, Run 3·4 E-03)은 봉인 기록에
  expected·actual이 null이라, 화면의 "원본 값"도 null로 보인다. 기대와 관찰은 규칙 설명과 detail 문장으로 제시된다. 웹은 봉인 기록을 그대로 표시한 것이다.
- SC-004: PASS. 보고서 `items_present` R1~R13·C1~C9 22/22 true. 보고서 집계와 12개 상태는 공식 상태에서 오고 "웹 검증" 기록은 섞이지 않는다.
- SC-005: PASS. E-01 재시험 비교(`/compare/7f25b475…`): 계보 86cd0010 FAIL → 7f25b475 PASS, 부모 판정 FAIL 그대로, assertion별 변화(A3만 FAIL→PASS,
  A1·A2·A4 그대로)와 assertion별 전후 증적 SHA-256, 바뀐 차원(실행 환경 바뀜, 대상 버전 바뀜 `git_commit_sha`, 고정 모델·시나리오·점수 규칙 원본 같음),
  "부모 기록 불변 확인"(기록된 부모 digest와 현재 부모 digest `75c10fe6…` 같음) 표시.
- SC-006: PASS. 12개 행 모두 구분 표시: NOT_RUN 4개는 실행 방식 NOT_RUN·"미실행"·준비 상태 RUNNER_NOT_READY(카탈로그), NO_TEST_TARGET 3개는 "판정 불가 ∅
  NO_TEST_TARGET"·준비 상태 NO_TEST_TARGET, N-02는 "판정 불가 ? INSUFFICIENT_EVIDENCE A5·A7", 실행 시나리오 5개는 실제 실행.
- SC-007: PASS. GET 응답 111개(HTML·JSON) + 웹 상태 폴더 저장 파일 4개, 총 115개 파일을 검사: Windows 경로(이스케이프 포함)·`/Users/`·사용자 이름·이메일·Bearer
  토큰·AWS 키 패턴과 두 `.env`의 비밀 값 10개(값은 출력하지 않음) 모두 0건. 증적 경로는 `<run_root>/…`로 표시된다. 준비 상태 확인 POST는 303 리디렉션만 돌려준다(본문 없음).
- SC-010: PASS. 모든 화면의 form action은 `/preflight`·`/runs/{id}/memos` 둘뿐이고 서버 POST 라우트도 이 둘뿐(Run·재시험·정리 확인 시작 경로 0건). 시나리오
  화면의 `run`·`retest` 명령은 복사용 문구이고 `cleanup-confirm` 문구는 없다. 준비 상태는 기록이 있는 E-01·E-02에서 확인 시각과 함께, 나머지는 "확인 기록 없음"
  또는 카탈로그 상태로 보인다. 사용법 오류 기록은 이 root에 없어 화면으로는 관찰하지 못했다(자동 시험 범위). E-01 화면은 사람이 직접 누른 확인 결과를 쓴다.
- SC-011: PASS. 실제 화면·API는 `data_origin ACTUAL`, `demo false`, "DEMO DATA" 표시 0건. `/demo/`는 `data_origin DEMO`, "DEMO DATA" 표시 있음, demo root에 기록
  없음(합성 Run 0개라 실제 개수·보고서에 섞일 것이 없음). 실제 기록 11개는 모두 이 PC에서 실행한 봉인 기록.
- 세션 지시 세 가지:
  1. 공식 상태와 분리된 웹 검증 기록 표기: 워크벤치 각 행에 "이 PC 웹 검증 기록 N건(공식 상태와 별도)"과 기록별 "공식 기록"/"웹 검증 기록" 링크가 따로 보인다.
     화면 문구는 있는 그대로 "이 PC 웹 검증 기록"이다(화면은 고치지 않음). 공식 상태 열은 카탈로그 값 그대로다. 행별 웹 검증 기록:
     H-03 2건(Run 1 `277d3f5a…`, Run 2 `1d573850…`), E-01 2건(Run 7 `86cd0010…`, Run 8 `7f25b475…`), E-02 1건(Run 6 `4a404c73…`),
     E-03 2건(Run 3 `fd48f7ff…`, Run 4 `064afdb0…`), N-02 2건 = 이번 세션 Run 5 `1767fb73…` 1건 + 예전 `e2e8e71d…` 1건(Spec 003 T084 시도 2,
     2026-10-05, 봉인 뒤 verify INVALID; 이번 세션 Run 아님). N-02의 `15cef078…`·`7b59237e…`는 "공식 기록"으로 보인다.
  2. 각 결과 화면 VERIFIED: 이 세션 8개 Run 모두 "봉인 무결성 확인됨 (VERIFIED)"(CLI verify와 같음).
  3. E-01 재시험 비교: 부모 FAIL → 재시험 PASS, 부모 불변 확인 표시(SC-005와 같음). E-01 시나리오 화면 "이전 실행"에도 두 기록과 "재시험 비교" 링크가 보인다.
- 관찰(판정 무관, 코드·화면은 고치지 않음): 재시험 비교 화면 머리 줄은 "대상 버전 확인 기록 없음", 보고서 화면 머리 줄은 "대상 버전 WhyYou commit 374b122"로
  표시가 다르다. 원인 조사:
  - 머리 줄은 공통 틀(`engine/web/templates/base.html`)이 `view.target.target_commit` → `view.run.target_commit` → `view.target_commit_now` 순서로 읽고,
    셋 다 없으면 "확인 기록 없음"을 쓴다. 워크벤치·시나리오 화면은 `view.target`, 실행 결과 화면은 `view.run`(그 Run의 target snapshot), 보고서 화면은
    `target_commit_now`를 준다. 재시험 비교 화면의 view는 `parent`·`child`에만 commit을 담고 세 필드를 주지 않아 머리 줄이 "확인 기록 없음"으로 떨어진다.
  - 보고서와 워크벤치의 머리 줄 값은 Run의 commit이 아니라 "가장 최근 준비 상태 확인 기록"의 대상 snapshot이다(`readmodel.py` `_target_identity`,
    ID-005-09; 지금은 E-01 확인 2026-10-12T02:47:07Z의 `374b122`). 즉 머리 줄 "대상 버전 확인"은 준비 상태 확인 기록을 가리키며, 재시험의 완료 여부와 무관하다.
  - Run 8 bundle의 `target.snapshot.json`에는 `git_commit_sha` `374b122e…`가 실제로 들어 있고(Run 7은 `ce8d8620…`), 재시험 비교 화면 본문도 부모 `ce8d862`,
    재시험 `374b122`를 맞게 보인다.
  - 위험: T071 과업 3(재시험 비교)에서 검토자가 머리 줄 "확인 기록 없음"을 "재시험이 덜 끝났다/확인되지 않았다"로 읽으면 치명적 오독이 될 수 있다.
  - 조치(연우 결정 2026-10-12):
    - 채택(2026-10-12 조치 완료, T070): T070 검토 키트의 진행자 메모와 정답 키에 "상단 줄의 '대상 버전 확인'은 가장 최근 준비 상태 확인 기록의 대상이며, 재시험 완료 여부와
      무관하다."를 넣는다.
    - 조건부 후보(T072 판정 뒤 재검토): 비교 화면 상단 줄 표시 수정은 지금 하지 않는다. T071에서 실제 오독이 나오면 화면 수정을 새 작업으로 만들고, 나오지 않으면
      고치지 않는다. Phase 11 converge는 문서 동기화이므로 화면 수정을 끼우지 않는다.
- 8개 Run 모두 ControlProof `9856a03`(dirty 0)에서 실행했다(Run마다 실행 전 기록, Spec 001 형식인 Run 2 외에는 bundle 환경 snapshot에도 dirty false).

#### T061 Spec 004 브랜치 재병합 (2026-10-12)

- 보성이 PR #2(`yeonwoo/004-retest-maintenance-path`)를 Spec 004 브랜치에 병합했다(`origin/yeonwoo/004-e01-e02-score-evidence` tip `9f480d5`).
- 005에 `git merge --no-ff origin/yeonwoo/004-e01-e02-score-evidence` → merge `25417ad`, 충돌 없음.
- `git diff --stat ca393d0 25417ad`는 비어 있다(파일 변경 0). PR #2의 `engine/retest.py` 수정은 이미 `b106b55`(2026-10-09, 선병합)로 005에 들어와 있어
  이번 병합은 이력 연결만 한다. 트리가 바뀌지 않았으므로 회귀 재실행은 하지 않았고, Phase 9 Run 8개의 기준 트리(`9856a03`)도 그대로다.

#### T070 검토 키트 (2026-10-12)

- `specs/005-web-workbench-report/usability/review-kit.md` 작성. 구성: 참여자 안내문, 과업 3개, §10.3 질문 7개와 3분 규칙, 치명적 오독 5항목,
  진행자 메모, 정답 키, 익명 기록 시트와 집계표.
- Phase 9 관찰 조치 (a) 반영: 진행자 메모 §5-1과 정답 키 과업 3에 "상단 줄의 '대상 버전 확인'은 가장 최근 준비 상태 확인 기록의 대상이며 재시험 완료 여부와
  무관하다"를 넣었고, 상단 줄 관련 발언은 정답 판정과 별도로 전부 기록하게 했다(T071에서 실제 오독 여부를 세기 위함). 진행자가 그 자리에서 설명하지 않는다.
- 진행자 메모에 참고 3건도 넣었다: Spec 002 형식 프로필의 "원본 값" 비어 보임(결함 아님), `e2e8e71d` 무결성 실패 표시(의도된 상태),
  그리고 아래 영문 표시 관찰.
- 관찰(2026-10-13, T071 준비 중, 코드·화면은 고치지 않음): 실행 결과 화면 "규칙별 결과" 표의 **기대** 열은 `assertion.description`,
  "원본 값" 안의 `detail`은 `assertion.detail`인데 **둘 다 영문**이다(E-01 A3: 기대 `a score whose evidence was removed is exposed as
  insufficient`, detail `P1: an affected item kept its score and citation after evidence removal`). 시나리오 정의 원천
  (`scenarios/E-01.yaml`)의 문장을 그대로 표시한 것이고, FR-008이 "정의 원천의 assertion 설명과 기대를 그대로" 보이라고 요구하므로
  번역하면 그 요구사항을 어긴다. 결함이 아니다. 실패 내용을 한국어로 읽는 경로는 "비개발자용 설명" 카드의 `verdict.impact`
  ("근거가 사라진 뒤에도 점수만 남으면 …")와 `verdict.summary`("점수 근거 또는 평가 기준 보존의 직접 위반이 관찰되었습니다.")다.
  - 조치: T070 키트 정답 키 과업 2에 한국어·영문 경로 3개를 표로 적고, 진행자 메모 §5-3에 "영문을 못 읽어 막힌 것(가)"과 "화면에서
    어디를 볼지 못 찾은 것(나)"을 구분해 기록하게 했다. 번역해 주지 않는다. (가)가 여러 건이면 정의 원천의 번역·병기 여부를 별도로 논의한다.
- 정답 키의 화면 라벨은 2026-10-13에 실제 기록(Run `86cd0010`)의 `/api/runs/{id}`로 확인해 채웠다: 실패 규칙 행 4열, 전체 판정 문구,
  증적 묶음 라벨 5개(`EV4-04` 2건, `EV4-05` 1건, `EV4-09` 2건). 진행 당일 화면 문구가 다르면 화면이 기준이다.
- 기록 시트는 참여자를 P1~P6으로만 적고 개인 식별자를 넣지 않는다(T071 조건).
- 판정 기준은 SC-008·SC-009 그대로이며 판정은 T072에서 한다.

### 사용성 검토 (Phase 10)

| 참여자(익명) | 역할 | 질문별 정답·시간 | 치명적 오독 |
|---|---|---|---|
