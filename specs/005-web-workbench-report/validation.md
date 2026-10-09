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

| 순서 | 시나리오·프로필 | WhyYou | ControlProof HEAD·dirty | preflight | Run ID | verdict / 복구 | manifest SHA-256 |
|---|---|---|---|---|---|---|---|

### 사용성 검토 (Phase 10)

| 참여자(익명) | 역할 | 질문별 정답·시간 | 치명적 오독 |
|---|---|---|---|
