# Spec 009 Traceability — FR·SC → assertion·EV9 → 코드 → 시험 (T014)

1단계 기준(2026-10-20). 실제 Run 증적은 2단계에서 생긴다. SC 중 실제 Run이 있어야 확인되는 항목은 "2단계"로 표시한다.

| 요구 | assertion·EV9 | 코드 | 시험 |
|---|---|---|---|
| FR-001 격리·외부 AI 차단·clean 소스 | EV9-01 | `engine/executors/spec009.py`(preflight), `scripts/spec009_local.py` | `tests/contract/test_spec009_preflight.py`, `tests/unit/test_spec009_local_setup.py` |
| FR-002 프로필·정의·Run·bundle·계보 분리 | 전체 | `engine/models.py`, `engine/scenario.py`, `engine/runner.py`, `engine/cli.py`, `engine/evidence.py`, `engine/retest.py`, `scenarios/N-01.yaml`, `scenarios/N-03.yaml` | `tests/contract/test_scenario_spec009.py`, `tests/contract/test_spec009_registry_cli.py` |
| FR-003 Run 소유 합성 데이터·정리 | EV9-02, EV9-06 | `seeds/spec009_subjects.py`, `engine/adapters/whyyou/spec009_seed.py`, `engine/adapters/whyyou/spec009_cleanup.py` | `tests/contract/test_spec009_seed_plan.py`, `tests/contract/test_spec009_seed_adapter.py` |
| FR-004 준비 상태 네 값 | — | `engine/executors/spec009.py`, `engine/executors/n01.py`(`_extra_checks`), `engine/readiness.py` | `tests/contract/test_spec009_preflight.py` |
| FR-005 대상 접근 종류 | EV9-01 | `engine/scenario.py`(`target_access`), `engine/web/readmodel.py`, `templates/run.html`, `templates/scenario.html` | `tests/contract/test_scenario_spec009.py`, `tests/web/test_spec009_display.py` |
| FR-010 PC·390px 동의 단계 | N01-A1, N01-A2 / EV9-03 | `engine/adapters/whyyou/applicant_browser.py`, `engine/executors/n01.py` | `tests/contract/test_applicant_browser_adapter.py`, `tests/integration/test_n01_executor.py` |
| FR-011 다섯 항목 판정·캡처 | N01-A1, N01-A2 / EV9-03 | `engine/n01.py`(`expected_fragments`, `assess_lane`) | `tests/unit/test_n01_judge.py`, `tests/unit/test_n01_expected_fragments.py` |
| FR-012 화면·서버·저장 식별값 | N01-A3 / EV9-04 | `engine/n01.py`(`assess_identifiers`), `spec009_seed.read_consent_facts`, `engine/executors/n01.py` | `tests/unit/test_n01_judge.py`, `tests/integration/test_n01_executor.py` |
| FR-013 동의 전 처리 차단은 N-02 소유 | 미검증 범위 `N02_PRE_CONSENT_BLOCK_NOT_RETESTED` | `engine/executors/n01.py`(`UNVERIFIED_SCOPE`) | `tests/integration/test_n01_executor.py` |
| FR-030 이전 식별값 거부·최신 저장·과거 불변 | N03-A1, N03-A2, N03-A3 / EV9-05 | `engine/n03.py`, `engine/executors/n03.py` | `tests/unit/test_n03_judge.py`, `tests/integration/test_n03_executor.py` |
| FR-031 이전 식별값 규칙·미검증 범위 | N03-U1~U3, N03-L1 / EV9-01 | `engine/n03.py`(`stale_identifier`), `n03-scope.json` | `tests/unit/test_n03_stale_identifier.py`, `tests/integration/test_n03_executor.py` |
| FR-032 정책 교체 수단 없음 | — | WhyYou 무수정, `engine/executors/n03.py` | `tests/integration/test_n03_executor.py` |
| FR-050 PASS·FAIL·INCONCLUSIVE·사유 | 모든 assertion / EV9-07 | `engine/n01.py`, `engine/n03.py`, `engine/executors/spec009.py` | 판정 단위 시험, 실행기 통합 시험 |
| FR-051 봉인·verify·redaction | EV9-07 | `engine/evidence.py`(`FORBIDDEN_KEYS`, spec009 분기), `engine/spec009_evidence.py`, `engine/n01_evidence.py`, `engine/n03_evidence.py` | 실행기 통합 시험(redaction·재봉인 위조), `tests/contract/test_review_data_bundles_unchanged.py` |
| FR-052 복구·`RESTORE_FAILED`·차단 | EV9-06 | `engine/executors/spec009.py`, `engine/spec009_recovery.py`, `scripts/spec009_recover.py`, `engine/cli.py`(cleanup-confirm) | 실행기 통합 시험, `tests/contract/test_spec009_recovery.py` |
| FR-053 최초 기록 보존·child | — | `engine/retest.py` | 실행기 통합 시험(retest child), `tests/contract/test_spec009_registry_cli.py` |
| FR-054 기존 워크벤치 표시 | — | `engine/presentation.py`, `engine/web/readmodel.py` | `tests/web/test_spec009_display.py`, `tests/contract/test_spec009_registry_cli.py`(show) |
| FR-055 closure 전 숫자 불변 | — | catalog·범위표 무수정 | `tests/unit/test_catalog_matrix_parity.py` |
| FR-056 범위 주장 | EV9-01 | `n0X-scope.json`, `Judgement.unverified_scope` | 실행기 통합 시험 |
| SC-001 시나리오별 봉인 Run | 전체 | — | 2단계 |
| SC-002 VERIFIED·원문 없음 | EV9-07 | 위 FR-051 | 실행기 통합 시험(fake), 실제는 2단계 |
| SC-003 N-01 5/5·캡처·세 출처 | N01-A1~A3 | 위 FR-010~012 | 판정·실행기 시험(fake), 실제는 2단계 |
| SC-004 N-03 판정·과거 변경 0 | N03-A1~A3 | 위 FR-030 | 판정·실행기 시험(fake), 실제는 2단계 |
| SC-005 복구·잔여 0 | EV9-06 | 위 FR-052 | `tests/contract/test_spec009_seed_adapter.py`, 실제는 2단계 |
| SC-006 재시험 부모 불변 | — | `engine/retest.py` | 실행기 통합 시험(부모 해시 불변) |
| SC-007 10분 안 실행·검증 | — | — | 2단계 |
| SC-008 기존 워크벤치에서 열림 | — | 위 FR-054 | `tests/web/test_spec009_display.py` |
| SC-009 closure 전 숫자 변경 0 | — | — | `tests/unit/test_catalog_matrix_parity.py`, `validation.md` |
| SC-010 범위 주장 100% | — | 위 FR-056 | 실행기 통합 시험(scope 고정값) |
| SC-011 대상 접근 한 줄 | — | 위 FR-005 | `tests/web/test_spec009_display.py` |
