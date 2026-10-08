# Spec 005 Validation

## Current status

- Workflow stage: Implement. Phase 1(T001~T003)·Phase 2 Foundation(T004~T018) 완료. T019(보성 PC 검사) 대기, T020(봉인 검사 v2 전환)과
  Phase 3 이후는 시작 전.
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

### 사용자 스토리 gate

| Phase | 시험 | 결과 |
|---|---|---|

### Actual validation (웹 PC 재실행, Phase 9)

| 순서 | 시나리오·프로필 | WhyYou | ControlProof HEAD·dirty | preflight | Run ID | verdict / 복구 | manifest SHA-256 |
|---|---|---|---|---|---|---|---|

### 사용성 검토 (Phase 10)

| 참여자(익명) | 역할 | 질문별 정답·시간 | 치명적 오독 |
|---|---|---|---|
