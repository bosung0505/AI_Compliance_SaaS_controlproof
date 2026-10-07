# Traceability: E-01·E-02 점수 근거·평가 기준 보존 검증

**Status**: 초안(Tasks 단계). "실제 산출물" 열은 구현·actual Run 뒤 T082·T093에서 채운다. 빈칸은 미실행을 뜻하며 PASS를
뜻하지 않는다.

경로 약어: `tests/u` = `tests/unit`, `tests/c` = `tests/contract`, `tests/i` = `tests/integration`, `adp` =
`engine/adapters/whyyou`, `WY` = `../gbsa_aws/backend`.

범위 밖(추적 대상 아님): 직무 요건 평가(`reports.requirement_assessments`)의 판정·인용 — spec Excluded, research R-015.
projection은 `report-records.jsonl`에 넣지 않으며 fixture는 요건 평가 receipt를 쓰지 않는다.

## Functional Requirements

| ID | 요약 | Task | Test | 구현 | 실제 산출물 |
|---|---|---|---|---|---|
| FR-001 | LOCAL_EMULATED 격리 대상, preflight 계약 | T001, T015, T042, T047, T059, T066, T079 | tests/c/test_cli_spec004_profile.py, tests/c/test_cli_spec004.py | engine/config.py, adp/adapter.py, engine/cli.py | |
| FR-002 | Run 소유 합성 데이터, Run 소유 행만 제거 | T012, T030, T036 | tests/u/test_models_spec004.py, tests/c/test_spec004_seed_adapter.py | adp/spec004_seed.py, seeds/spec004_subjects.py | |
| FR-003 | fixture 위 실제 보고서, 한계 표시 | T030, T037, T062, T065, T072 | tests/c/test_spec004_seed_adapter.py, tests/c/test_presentation_spec004.py | adp/spec004_seed.py, adp/report_records.py, engine/presentation.py | |
| FR-004 | 보고서 요청 전 제품 API 동의 | T034, T040 | tests/i/test_e01_citation_orchestration.py, tests/i/test_e02_orchestration.py | engine/executors/report_lanes.py | |
| FR-010 | 인용 모드 fixture로 다섯 입력, 원래 출력·저장 수집 | T023, T025~T027, T032, T037, T038, T040, T073 | WY/tests/unit/runtime/test_controlproof_model_substitute.py, tests/c/test_spec004_model_emission_adapter.py | WY/src/interview_evidence/runtime/controlproof_model_substitute.py, adp/model_emission.py, engine/executors/e01.py | |
| FR-011 | 저장 레코드로 판정, 출력 불일치는 INCONCLUSIVE | T033, T041 | tests/u/test_judge_e01_citation.py | engine/judges/e01.py | |
| FR-012 | 타 지원자 ID는 참조 lane 실제 ID, 타 기준 ID는 같은 호출 기억 | T024, T030, T035, T036 | WY/tests/unit/runtime/test_controlproof_model_substitute.py, tests/c/test_spec004_seed_adapter.py | WY/.../controlproof_model_substitute.py, seeds/spec004_subjects.py | |
| FR-013 | deep probe는 진단 E01-D1, 원복 | T044, T045, T047~T049, T077 | tests/c/test_spec004_evidence_mutation_adapter.py, tests/u/test_judge_e01_removal.py | adp/evidence_mutation.py, engine/judges/e01.py | |
| FR-020 | 자막 구간 직접 삭제, 세 번 조회 | T044, T047, T048, T076 | tests/c/test_spec004_evidence_mutation_adapter.py | adp/evidence_mutation.py, engine/executors/e01.py | |
| FR-021 | 근거 부족 미노출·다른 항목 변화 FAIL | T045, T049 | tests/u/test_judge_e01_removal.py | engine/judges/e01.py | |
| FR-022 | 같은 값 재삽입, 실패는 RESTORE_FAILED·차단 | T044~T046, T050 | tests/i/test_e01_removal_restore.py | adp/evidence_mutation.py, engine/execution.py | |
| FR-030 | 첫 보고서 동결 입력 수집 | T053, T058 | tests/u/test_judge_e02.py | engine/judges/e02.py | |
| FR-031 | 제품 API 버전 생성·발행, 최신 발행 버전 묶음 | T052, T054~T056, T075 | tests/c/test_spec004_criteria_version_adapter.py, tests/i/test_e02_orchestration.py | adp/criteria_versions.py, scenarios/E-02.yaml | |
| FR-032 | 첫 보고서 불변, 두 번째 전제 | T053, T054, T057 | tests/u/test_judge_e02.py | engine/executors/e02.py | |
| FR-033 | 독립 재계산, 세 비교 대상 | T003, T009, T017, T053, T058, T074 | tests/u/test_e02_scoring_copy.py, tests/u/test_judge_e02.py | engine/judges/e02_scoring.py, engine/judges/e02.py | |
| FR-034 | 원본 blob 고정, drift는 RUNNER_NOT_READY | T009, T015, T017, T052, T055, T059 | tests/u/test_e02_scoring_copy.py, tests/c/test_spec004_criteria_version_adapter.py | engine/judges/e02_scoring.py, adp/criteria_versions.py | |
| FR-040 | assertion별 판정, 시나리오별 전체 PASS | T006, T013, T061, T066 | tests/c/test_scenario_profile_v4.py, tests/i/test_spec004_verdict_matrix.py | engine/scenario.py, engine/judges/e01.py, engine/judges/e02.py | |
| FR-041 | 변경 주입 복구·안전 상태 | T046, T048, T050, T054 | tests/i/test_e01_removal_restore.py, tests/i/test_e02_orchestration.py | engine/executors/e01.py, engine/executors/e02.py, engine/execution.py | |
| FR-042 | 봉인·검증·redaction, 텍스트는 해시만 | T007, T010, T018, T064, T067, T090, T095 | tests/c/test_bundle_profile_spec004.py, tests/u/test_redaction_security.py, tests/i/test_spec004_bundle_links.py | engine/evidence.py | |
| FR-043 | profile·Run·bundle·계보 분리 | T006, T008, T011, T013, T020 | tests/c/test_cli_spec004_profile.py, tests/i/test_spec003_v3_regression.py | engine/cli.py, engine/runner.py | |
| FR-050 | 최초 결과 봉인·원인 분류 | T004, T078, T080~T084 | — (actual Run) | specs/004-e01-e02-score-evidence/implementation-decisions.md | |
| FR-051 | P1 대상 결함 시 승인된 최소 수정 | T076, T085~T087 | WY/tests/unit/reporting/test_report_view_contract.py (조건부) | WY/src/interview_evidence/reporting/… (조건부) | |
| FR-052 | 보완 뒤 child만 | T070, T071, T088 | tests/i/test_spec004_retest_lineage.py | engine/retest.py | |

## Success Criteria

| ID | 요약 | Task | Test | 실제 산출물 |
|---|---|---|---|---|
| SC-001 | 모든 assertion 판정·사유 코드 | T061, T068, T080, T081 | tests/i/test_spec004_verdict_matrix.py | |
| SC-002 | 변경 주입 복구·차단 | T046, T050, T054, T089 | tests/i/test_e01_removal_restore.py, tests/i/test_spec004_timing.py | |
| SC-003 | Run 540초, verify 포함 600초 | T006, T073, T075, T089, T092 | tests/i/test_spec004_timing.py | |
| SC-004 | bundle VERIFIED, redaction | T007, T010, T064, T090, T095 | tests/i/test_spec004_bundle_links.py | |
| SC-005 | FAIL은 분류 뒤 child | T070, T078, T083, T088 | tests/i/test_spec004_retest_lineage.py | |
| SC-006 | 팀원 PC 재현 | T079, T092, T096, T097 | — (actual) | |
| SC-007 | 한계 표시 | T023, T062, T065 | tests/c/test_presentation_spec004.py | |

## Assertions and diagnostic

| ID | Task | Judge test | Judge | Evidence | 실제 결과 |
|---|---|---|---|---|---|
| E01-A1 | T033, T041, T073, T080 | tests/u/test_judge_e01_citation.py | engine/judges/e01.py | EV4-02, EV4-03, EV4-04 | |
| E01-A2 | T033, T041, T073, T080 | tests/u/test_judge_e01_citation.py | engine/judges/e01.py | EV4-02, EV4-03, EV4-04 | |
| E01-A3 | T045, T049, T076, T080 | tests/u/test_judge_e01_removal.py | engine/judges/e01.py | EV4-04, EV4-05, EV4-09 | |
| E01-A4 | T045, T049, T076, T080 | tests/u/test_judge_e01_removal.py | engine/judges/e01.py | EV4-04, EV4-05, EV4-09 | |
| E01-D1 | T045, T049, T077, T080 | tests/u/test_judge_e01_removal.py | engine/judges/e01.py | EV4-04, EV4-05, EV4-09 | |
| E02-A1 | T053, T058, T081 | tests/u/test_judge_e02.py | engine/judges/e02.py | EV4-04, EV4-06, EV4-07 | |
| E02-A2 | T053, T058, T075, T081 | tests/u/test_judge_e02.py | engine/judges/e02.py | EV4-04, EV4-06, EV4-07, EV4-09 | |
| E02-A3 | T009, T053, T058, T074, T081 | tests/u/test_e02_scoring_copy.py, tests/u/test_judge_e02.py | engine/judges/e02.py, engine/judges/e02_scoring.py | EV4-04, EV4-08 | |

## Evidence

| EV4 | 파일 | Writer task | Verify test | 실제 manifest |
|---|---|---|---|---|
| EV4-01 | spec004-capabilities.json, snapshots | T018, T042, T059 | tests/c/test_bundle_profile_spec004.py | |
| EV4-02 | spec004-lanes.json | T036, T018 | tests/c/test_spec004_seed_adapter.py | |
| EV4-03 | citation-cases.jsonl, model-emissions.jsonl | T038, T040 | tests/c/test_spec004_model_emission_adapter.py | |
| EV4-04 | report-records.jsonl | T037 | tests/c/test_spec004_report_adapters.py | |
| EV4-05 | report-reads.jsonl | T037, T048 | tests/i/test_spec004_bundle_links.py | |
| EV4-06 | criteria-versions.json | T055 | tests/c/test_spec004_criteria_version_adapter.py | |
| EV4-07 | frozen-inputs.json | T057, T058 | tests/u/test_judge_e02.py | |
| EV4-08 | recompute.json | T058, T067 | tests/i/test_spec004_bundle_links.py | |
| EV4-09 | change-injections.jsonl, recovery.json | T047, T048, T057 | tests/c/test_spec004_evidence_mutation_adapter.py | |
| EV4-10 | assertions, judgement, manifest, retest-diff | T018, T067, T071 | tests/i/test_spec004_orchestration.py | |
