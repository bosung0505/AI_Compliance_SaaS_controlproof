# Spec 005 Validation

## Current status

- Workflow stage: Implement. Phase 1·2(T001~T018), Phase 3 US1(T021~T034), Phase 4 US2(T035~T042), Phase 5 US3(T043~T047) 완료.
  T019(보성 PC 검사) 대기, T020(봉인 검사 v2 전환)과 Phase 6(US4) 이후는 시작 전. ID-005-01은 2026-10-09 결정됨.
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

### 사용자 스토리 gate

| Phase | 시험 | 결과 |
|---|---|---|
| Phase 3 US1 | T021~T026 GREEN, 전체 회귀, ruff | PASS(2026-10-09, 위 T034) |
| Phase 4 US2 | T035~T037 GREEN, 전체 회귀, ruff | PASS(2026-10-09, 위 T042) |
| Phase 5 US3 | T043~T044 GREEN, 전체 회귀, ruff | PASS(2026-10-09, 위 T047) |
| Phase 6 US4 | T048~T049 GREEN, 전체 회귀, ruff | PASS(2026-10-09, 위 T052; US5 RED 시험 제외) |

### Actual validation (웹 PC 재실행, Phase 9)

| 순서 | 시나리오·프로필 | WhyYou | ControlProof HEAD·dirty | preflight | Run ID | verdict / 복구 | manifest SHA-256 |
|---|---|---|---|---|---|---|---|

### 사용성 검토 (Phase 10)

| 참여자(익명) | 역할 | 질문별 정답·시간 | 치명적 오독 |
|---|---|---|---|
