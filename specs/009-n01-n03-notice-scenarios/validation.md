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

## 범위

- 이 기록은 코드·자동 시험·하네스까지의 1단계 gate다. 모든 시험은 fake adapter·fake 트랜잭션으로 돌았고 WhyYou·DB·브라우저·
  Docker에 접속하지 않았다.
- **actual N-01·N-03: NOT_RUN**(1단계 준비 완료, 실제 Run은 2단계 승인 뒤).
- 카탈로그·범위표·README·Product Brief는 바꾸지 않았다(D-030 3항).
