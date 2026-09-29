# Spec 002 추적성

이 문서는 Spec 002의 요구사항·성과 기준·판정 assertion·필수 증적을 구현 작업, 자동 검증,
구현 위치에 연결한다. `A~B`는 양 끝을 포함한 연속 ID 전체를 뜻한다. 실제 스택의 Run ID,
verdict, manifest digest와 복구 결과는 `validation.md`를 단일 기록원으로 사용한다.

## 기능 요구사항(FR)

| 요구사항 | 작업 | 대표 자동 검증 | 구현·계약 위치 |
|---|---|---|---|
| FR-001~010 | T005~T010, T012, T018, T029, T049, T060, T072, T074~T075 | `test_models_spec002.py`, `test_scenario_profile_v2.py`, `test_spec001_v1_regression.py`, `test_spec002_retest_lineage.py` | `models.py`, `scenario.py`, `executors/sealed.py`, `retest.py`, 세 v2 scenario YAML |
| FR-011~020 | T013~T015, T017, T020, T027, T064, T070, T072, T076, T080 | `test_whyyou_capability.py`, `test_profile_registry_v2.py`, `test_cli_profiles_v2.py`, `test_whyyou_adapter_v2_composition.py` | `adapters/base.py`, `adapters/whyyou/capability.py`, `readiness.py`, `runner.py`, `cli.py` |
| FR-021~030 | T020~T027, T030~T031, T042~T051 | `test_whyyou_queue_adapter.py`, `test_h03_dlq_lineage.py`, `test_judge_h03_dlq.py`, `test_whyyou_queue_redrive.py`, `test_judge_e03_before.py` | `adapters/whyyou/queue.py`, `fault.py`, `execution.py`, `executors/h03_dlq.py`, `judges/h03_dlq.py` |
| FR-031~040 | T028~T040, T082~T083 | `test_whyyou_browser.py`, `test_whyyou_decision_adapter.py`, `test_judge_h03_decisions.py`, `test_h03_decision_paths.py`, WhyYou `test_recruiting_stage_decision.py` | `browser.py`, `decisions.py`, `effects.py`, `executors/h03_dlq.py`, `judges/h03_dlq.py`; WhyYou hiring/report failure API·UI |
| FR-041~050 | T042~T063 | `test_whyyou_effect_adapter.py`, `test_whyyou_queue_redrive.py`, `test_judge_e03_before.py`, `test_e03_before.py`, `test_whyyou_after_commit_fault.py`, `test_e03_after.py` | `effects.py`, `execution.py`, `executors/e03_before.py`, `e03_after.py`, `judges/e03.py`; WhyYou worker fault hook |
| FR-051~055 | T064~T071, T084~T085 | `test_whyyou_decision_replay.py`, `test_judge_e03_decision.py`, `test_e03_decision_replay.py`, WhyYou `test_final_decision_idempotency.py` | `decisions.py`, `effects.py`, `executors/e03_before.py`, `judges/e03.py`; WhyYou `FinalDecisionService` |
| FR-056~060 | T008, T016, T023~T031, T042~T052, T072~T079 | `test_bundle_profile_spec002.py`, `test_h03_bundle_links.py`, `test_presentation_spec002.py`, `test_spec002_verdict_matrix.py` | `evidence.py`, `executors/sealed.py`, `presentation.py` |
| FR-061~063 | T008, T016, T073~T075, T086 | `test_redaction_security.py`, `test_bundle_verify.py`, `test_bundle_profile_spec002.py`, `test_spec002_verdict_matrix.py` | `evidence.py`의 구조적 redaction gate·manifest verifier |
| FR-064~065 | T016, T074~T075, T078 | `test_evidence_conflicts.py`, `test_spec002_retest_lineage.py`, `test_bundle_profile_spec002.py` | `evidence.py`, `retest.py`, cross-Run artifact reference verifier |
| FR-066~074 | T007, T012, T047, T051, T056, T062, T072~T077 | `test_execution_session.py`, `test_judgement_matrix.py`, `test_spec002_verdict_matrix.py`, `test_cli_profiles_v2.py` | `execution.py`, `judges/*.py`, `executors/sealed.py`, `presentation.py`, `cli.py` |
| FR-075~080 | T074, T078~T085 | `test_spec002_retest_lineage.py`, `test_cli_profiles_v2.py`, bundle `verify` actual-stack 기록 | `retest.py`, `cli.py`, `evidence.py`, `validation.md`의 불변 FAIL→PASS 계보 |
| FR-081~087 | T004, T009, T017, T072~T073, T077~T081, T089 | `test_local_environment_guard.py`, `test_cli_profiles_v2.py`, `test_presentation_spec002.py` | `config.py`, `adapters/whyyou/environment.py`, `presentation.py`, environment/target snapshot |
| FR-088 | T020~T030, T080~T081 | `test_whyyou_queue_adapter.py`, `test_h03_dlq_lineage.py` | LocalStack `iep-reporting → iep-reporting-dlq` topology adapter와 snapshot |
| FR-089~090 | T053~T059 | WhyYou `test_worker_delivery.py`, `test_controlproof_reporting_fault.py`; ControlProof `test_whyyou_after_commit_fault.py` | WhyYou after-commit hook·processed short circuit; ControlProof `fault.py` |
| FR-091 | T033, T036, T038~T040, T082 | `test_whyyou_decision_adapter.py`, `test_h03_decision_paths.py`, `test_judge_h03_decisions.py` | 두 operation·세 canonical decision path capability와 batch 보호 |
| FR-092~093 | T042, T046, T051, T056, T062 | `test_whyyou_effect_adapter.py`, `test_judge_e03_before.py`, `test_judge_e03_after.py` | allowlisted reporting effect projection과 E-03 효과 판정 |
| FR-094~095 | T037, T064~T070, T084 | `test_whyyou_decision_replay.py`, `test_judge_e03_decision.py`, WhyYou `test_final_decision_idempotency.py` | 결정 effect projection, hashed key/body identity, `FinalDecisionService` |
| FR-096 | T081, T083~T085 | 실제 부모/자식 bundle `verify`, WhyYou 보완 회귀 | `implementation-decisions.md`, `validation.md`, 불변 FAIL→PASS retest link |

## 성공 기준(SC)

| 성공 기준 | 작업 | 대표 검증·증적 | 구현·결과 위치 |
|---|---|---|---|
| SC-001 | T081, T087 | `test_spec002_timing.py`; actual Run 시작·종료 시각 | scenario snapshot의 360/60/180/600초 정책, `executors/sealed.py` Run deadline |
| SC-002 | T020, T024, T044, T075 | `test_judge_h03_dlq.py`, `test_judge_e03_before.py`, `test_spec002_verdict_matrix.py` | H03/E03 lineage judge |
| SC-003 | T033~T040, T082, T085 | `test_judge_h03_decisions.py`, `test_h03_decision_paths.py`; H03 child PASS | decision/effect adapters와 H03-A7 judge |
| SC-004 | T042~T052, T075, T085 | `test_whyyou_effect_adapter.py`, `test_judge_e03_before.py`; E03 BEFORE child PASS | BEFORE executor·effect judge |
| SC-005 | T053~T063, T075, T081 | `test_worker_delivery.py`, `test_e03_after.py`; E03 AFTER PASS | AFTER hook·duplicate-ack executor/judge |
| SC-006 | T064~T071, T084~T085 | replay contract/judge, WhyYou idempotency 회귀, E03 grandchild PASS | `FinalDecisionService`, decision replay/effect judge |
| SC-007 | T072~T079 | `test_spec002_verdict_matrix.py`, `test_presentation_spec002.py` | profile별 독립 judgement/presentation |
| SC-008 | T008, T016, T073~T075, T079, T081, T085 | bundle profile·tamper·required-evidence·actual `verify` | `evidence.py`와 sealed manifest |
| SC-009 | T007, T047, T056, T074~T075 | `test_execution_session.py`, `test_h03_restore_failure.py`, `test_spec002_verdict_matrix.py` | restore block·safe redrive·후속 Run 차단 |
| SC-010 | T074, T078, T085 | `test_spec002_retest_lineage.py`; 부모/자식 manifest hash 재검증 | `retest.py`, cross-Run reference, `validation.md` |
| SC-011 | T081, T086 | `test_redaction_security.py`; 합성 subject actual Runs | 구조적 secret/PII gate와 synthetic seed |
| SC-012 | T073, T077, T089 | `test_presentation_spec002.py` | 결과의 실패 위치·경로·효과·미검증 범위 projection |
| SC-013 | T004, T009, T072, T080~T081 | local environment guard·CLI contract·actual snapshots | `whyyou-local`, `LOCAL_EMULATED`, AWS `NOT_RUN` |
| SC-014 | T073, T077, T089 | `test_presentation_spec002.py` | cloud-unverified scope와 결과 재사용 금지 문구 |
| SC-015 | T081~T085 | 부모 FAIL→자식 PASS bundle 5개 무결성 재검증 | `validation.md` T085 계보와 manifest SHA-256 |

## 판정 Assertion

| Assertion | 작업 | 대표 자동 검증 | 구현 |
|---|---|---|---|
| H03-A1~A6 | T029~T031, T072~T079, T081, T085 | Spec 001 H-03 회귀, `test_h03_bundle_links.py`, `test_spec002_verdict_matrix.py` | `executors/sealed.py::_complete_h03_assertions`, Spec 001 judge 의미 유지 |
| H03-A7 | T033~T040, T073, T082, T085 | `test_judge_h03_decisions.py`, `test_h03_decision_paths.py`, WhyYou batch guard 회귀 | `decisions.py`, `effects.py`, `judges/h03_dlq.py` |
| H03-A8 | T020~T031, T073, T081, T085 | `test_judge_h03_dlq.py`, `test_h03_dlq_lineage.py`, actual H03 retest | `queue.py`, `executors/h03_dlq.py`, `judges/h03_dlq.py` |
| H03-A9 | T020, T024, T028~T031, T073, T083, T085 | `test_whyyou_browser.py`, `test_judge_h03_dlq.py`, WhyYou API/UI 회귀 | `browser.py`, terminal failure projection/API/UI, H03 visibility judge |
| E03-A1~A2 | T042~T051, T056, T061~T062, T075, T081, T085 | `test_judge_e03_before.py`, `test_judge_e03_after.py`, `test_spec002_verdict_matrix.py` | 공통 lineage·재시도/DLQ judge |
| E03-A3~A4 | T042~T052, T075, T081, T085 | `test_whyyou_effect_adapter.py`, `test_judge_e03_before.py`, `test_e03_before.py` | BEFORE executor와 exact reporting effects |
| E03-A5~A6 | T053~T063, T075, T081 | `test_whyyou_after_commit_fault.py`, `test_judge_e03_after.py`, `test_e03_after.py` | AFTER executor와 duplicate-ack/effect judge |
| E03-A7 | T064~T071, T084~T085 | `test_judge_e03_decision.py`, `test_e03_decision_replay.py`, WhyYou idempotency 회귀 | decision replay, canonical actor/effect judge, `FinalDecisionService` |
| E03-A8 | T043~T051, T056, T061~T062, T074~T075, T081, T085 | queue redrive·restore failure·BEFORE/AFTER judge 테스트 | `execution.py`, fault restore, safe redrive, restore block |

## 필수 증적(EV2)

| Evidence | 작업 | 검증 | 생성·연결 위치 |
|---|---|---|---|
| EV2-01 | T020~T030, T072~T081 | queue/capability/environment contract, bundle profile | environment·queue topology snapshot, sealed artifact collector |
| EV2-02 | T029~T030, T042, T049~T050, T060~T061 | H03/E03 integration, bundle link test | baseline와 원 Outbox event projection |
| EV2-03 | T022, T048, T053, T055, T057~T061 | fault receipt·after-commit contract | BEFORE/AFTER boundary receipt와 `faults.jsonl` |
| EV2-04 | T020, T022~T026, T053~T061 | queue attempt·worker duplicate delivery tests | `delivery-attempts.jsonl` |
| EV2-05 | T020, T023~T031, T042~T051 | DLQ lineage/judge tests | `terminal-failure.json` |
| EV2-06 | T024, T028~T031, T083 | browser/visibility tests와 actual H03 | 담당자 API/UI projection artifact |
| EV2-07 | T033~T040, T082 | decision adapter/path/judge tests | path별 요청·응답의 sanitized artifact |
| EV2-08 | T034~T040, T082 | decision effect·partial-write tests | path별 pre/post decision effects |
| EV2-09 | T043, T047~T051, T056, T061~T062 | redrive·restore tests | restore artifact와 `redrive-receipts.jsonl` |
| EV2-10 | T042, T044~T051, T056, T061~T062 | effect adapter와 BEFORE/AFTER judge tests | allowlisted `effects.jsonl`과 effect artifact |
| EV2-11 | T064~T071, T084~T085 | replay contract/judge와 actual E03 retest | 최초/replay identity·효과 비교 artifact |
| EV2-12 | T008, T016, T029, T049, T060, T072~T079, T085 | bundle profile·tamper·retest lineage tests | scenario/target/environment/queue snapshots, manifest와 parent origin link |

## 실제 스택과 문서 경계

- 자동 테스트 행은 판정 규칙과 안전 경계를 검증한다. 실제 WhyYou 결과를 대신하지 않는다.
- `validation.md`의 T081/T085 Run이 로컬 실제 스택 verdict와 불변 FAIL→PASS 계보의 근거다.
- 모든 로컬 결과의 주장 범위는 `EXECUTED_SCENARIO_AND_EVIDENCE_ONLY`다. ControlProof는 전체 법적
  준수를 인증하거나 보증하지 않으며 실제 AWS 환경은 `NOT_RUN`이다.
