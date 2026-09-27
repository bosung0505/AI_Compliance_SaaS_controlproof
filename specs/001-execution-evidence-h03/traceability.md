# Spec 001 추적성

요구사항, 실행 작업, 자동 검증, 구현 위치를 한 표에서 추적한다. 범위 표기는 해당 ID의
연속 구간 전체를 뜻하며, 실제 WhyYou 격리 스택 실행과 비작성자 사용성 시험은
`validation.md`에서 별도 상태로 관리한다.

| 요구/성과 | 작업 | 자동 검증 | 구현 |
|---|---|---|---|
| FR-001~006, FR-050 | T009, T014, T018, T064~070 | `test_scenario_contract.py`, `test_readiness.py`, `test_cli_preflight.py`, `test_whyyou_capability.py` | `scenario.py`, `readiness.py`, `capability.py`, `cli.py` |
| FR-007~014 | T006, T011, T021~023, T030~034 | `test_models.py`, `test_h03_scenario.py`, `test_whyyou_adapter_contract.py` | `models.py`, `client.py`, `seed.py`, `state.py` |
| FR-015~020 | T007, T024, T028~029, T035, T037~038, T042, T072 | `test_lifecycle.py`, `test_whyyou_fault.py`, WhyYou ControlProof 안전 테스트 | `lifecycle.py`, `fault.py`, WhyYou test guard |
| FR-021~026 | T008, T013, T046 | `test_observations.py`, `test_evidence_conflicts.py` | `observations.py` |
| FR-027~034 | T025~027, T032~040, T084~085 | `test_judge_h03.py`, `test_h03_orchestration.py`, `test_whyyou_browser.py`, WhyYou API/UI 보호 테스트 | `judge.py`, `runner.py`, WhyYou adapters와 보호조치 |
| FR-035~041 | T010, T043, T047, T050, T052~054 | `test_bundle_contract.py`, `test_bundle_verify.py`, `test_cli_review.py` | `evidence.py`, `presentation.py`, `cli.py` |
| FR-042~049 | T026, T039, T045, T049, T051 | `test_judgement_matrix.py`, `test_judge_h03.py` | `judge.py`, `presentation.py` |
| FR-051~054 | T056~063 | `test_retest.py`, `test_cli_retest.py`, retest 통합 테스트 | `retest.py`, `runner.py`, `cli.py` |
| FR-055 | T021, T029, T038, T064~069, T072 | model substitute/health 및 readiness 테스트 | WhyYou fixed model, `config.py`, `capability.py` |
| H03-A1~A6 | T021, T026~027, T039~044, T054, T084~085 | H-03 judge/orchestration/review 테스트와 실제 FAIL→PASS retest | `scenarios/H-03.yaml`, `judge.py`, `runner.py`, WhyYou API/UI 보호조치 |
| EV-01~EV-09 | T021, T027, T030, T032~043, T050, T054 | bundle link, manifest, traceability 테스트 | `evidence.py`, `runner.py`, adapters |
| SC-001~005, SC-009~010 | T043~044, T064~072, T077 | fake harness와 안전/보안 테스트; 실제 스택 T077 대기 | runner, adapter, target guard |
| SC-006~007 | T047, T056~063, T078, T085 | tamper, parent 불변 retest, 실제 FAIL→PASS 계보 | `verify_bundle`, `retest.py` |
| SC-008 | T051, T054~055, T086 | 자동 projection·익명 review package 검증 완료; 비작성자 3건 시험 대기 | `presentation.py`, `prepare_sc008_review.py`, review checklist |
| SC-009 | T043, T071, T077, T086 | bundle 링크, redaction corpus, UUID false-positive 회귀, 실제 스택 증적 | `evidence.py`, `runner.py`, review package |
