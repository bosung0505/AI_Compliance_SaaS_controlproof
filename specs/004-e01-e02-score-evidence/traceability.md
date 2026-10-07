# Traceability: E-01·E-02 점수 근거·평가 기준 보존 검증

**Status**: 최초 공식 Run source/result/manifest 매핑 고정(T082). 전체 FR/SC 산출물 매핑 마감은 T093에 남아 있다.
아래 초기 결과와 assertion/EV4 열이 실제 기록이며, 아직 비어 있는 마감 열을 PASS로 해석하지 않는다.

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
| E01-A1 | T033, T041, T073, T080 | tests/u/test_judge_e01_citation.py | engine/judges/e01.py | EV4-02, EV4-03, EV4-04 | PASS — `09c9d9bb-82a3-4485-9c9d-e9721f2452e4` (최초 공식) |
| E01-A2 | T033, T041, T073, T080 | tests/u/test_judge_e01_citation.py | engine/judges/e01.py | EV4-02, EV4-03, EV4-04 | PASS — `09c9d9bb-82a3-4485-9c9d-e9721f2452e4` (최초 공식) |
| E01-A3 | T045, T049, T076, T080 | tests/u/test_judge_e01_removal.py | engine/judges/e01.py | EV4-04, EV4-05, EV4-09 | FAIL — `09c9d9bb-82a3-4485-9c9d-e9721f2452e4` (최초 공식) |
| E01-A4 | T045, T049, T076, T080 | tests/u/test_judge_e01_removal.py | engine/judges/e01.py | EV4-04, EV4-05, EV4-09 | PASS — `09c9d9bb-82a3-4485-9c9d-e9721f2452e4` (최초 공식) |
| E01-D1 | T045, T049, T077, T080 | tests/u/test_judge_e01_removal.py | engine/judges/e01.py | EV4-04, EV4-05, EV4-09 | EMPTY AXIS_DROPPED; NONEXISTENT/OTHER_APPLICANT SHOWN_AS_WRITTEN; OTHER_CRITERION NOT_OBSERVED — `09c9d9bb-82a3-4485-9c9d-e9721f2452e4` |
| E02-A1 | T053, T058, T081 | tests/u/test_judge_e02.py | engine/judges/e02.py | EV4-04, EV4-06, EV4-07 | PASS — `e39e62ae-be73-4e52-8cab-1f878637a0c6` (최초 공식) |
| E02-A2 | T053, T058, T075, T081 | tests/u/test_judge_e02.py | engine/judges/e02.py | EV4-04, EV4-06, EV4-07, EV4-09 | PASS — `e39e62ae-be73-4e52-8cab-1f878637a0c6` (최초 공식) |
| E02-A3 | T009, T053, T058, T074, T081 | tests/u/test_e02_scoring_copy.py, tests/u/test_judge_e02.py | engine/judges/e02.py, engine/judges/e02_scoring.py | EV4-04, EV4-08 | PASS — `e39e62ae-be73-4e52-8cab-1f878637a0c6` (최초 공식) |

## Evidence

| EV4 | 파일 | Writer task | Verify test | 실제 manifest |
|---|---|---|---|---|
| EV4-01 | spec004-capabilities.json, snapshots | T018, T042, T059 | tests/c/test_bundle_profile_spec004.py | E-01 `09c9d9bb-82a3-4485-9c9d-e9721f2452e4`; E-02 `e39e62ae-be73-4e52-8cab-1f878637a0c6` (manifest 고정, 아래 SHA 참조) |
| EV4-02 | spec004-lanes.json | T036, T018 | tests/c/test_spec004_seed_adapter.py | E-01 `09c9d9bb-82a3-4485-9c9d-e9721f2452e4`; E-02 `e39e62ae-be73-4e52-8cab-1f878637a0c6` (manifest 고정, 아래 SHA 참조) |
| EV4-03 | citation-cases.jsonl, model-emissions.jsonl | T038, T040 | tests/c/test_spec004_model_emission_adapter.py | E-01 `09c9d9bb-82a3-4485-9c9d-e9721f2452e4` (manifest 고정, 아래 SHA 참조) |
| EV4-04 | report-records.jsonl | T037 | tests/c/test_spec004_report_adapters.py | E-01 `09c9d9bb-82a3-4485-9c9d-e9721f2452e4`; E-02 `e39e62ae-be73-4e52-8cab-1f878637a0c6` (manifest 고정, 아래 SHA 참조) |
| EV4-05 | report-reads.jsonl | T037, T048 | tests/i/test_spec004_bundle_links.py | E-01 `09c9d9bb-82a3-4485-9c9d-e9721f2452e4` (manifest 고정, 아래 SHA 참조) |
| EV4-06 | criteria-versions.json | T055 | tests/c/test_spec004_criteria_version_adapter.py | E-02 `e39e62ae-be73-4e52-8cab-1f878637a0c6` (manifest 고정, 아래 SHA 참조) |
| EV4-07 | frozen-inputs.json | T057, T058 | tests/u/test_judge_e02.py | E-02 `e39e62ae-be73-4e52-8cab-1f878637a0c6` (manifest 고정, 아래 SHA 참조) |
| EV4-08 | recompute.json | T058, T067 | tests/i/test_spec004_bundle_links.py | E-02 `e39e62ae-be73-4e52-8cab-1f878637a0c6` (manifest 고정, 아래 SHA 참조) |
| EV4-09 | change-injections.jsonl, recovery.json | T047, T048, T057 | tests/c/test_spec004_evidence_mutation_adapter.py | E-01 `09c9d9bb-82a3-4485-9c9d-e9721f2452e4`; E-02 `e39e62ae-be73-4e52-8cab-1f878637a0c6` (manifest 고정, 아래 SHA 참조) |
| EV4-10 | assertions, judgement, manifest, retest-diff | T018, T067, T071 | tests/i/test_spec004_orchestration.py | E-01 `09c9d9bb-82a3-4485-9c9d-e9721f2452e4`; E-02 `e39e62ae-be73-4e52-8cab-1f878637a0c6` (manifest 고정, 아래 SHA 참조) |

## T082 — 최초 공식 Run source/result mapping (2026-10-07)

LOCAL_EMULATED 합성 입력·고정 모델 기반의 실제 WhyYou API/작업자 처리다. AWS NOT_RUN.
Phase 8 진단 ID와 구분한다. 두 Run 모두 수정 전 최초 결과, parent_run_id=null; child 없음.

| Scenario / profile | Run ID | ControlProof source | WhyYou source | Result | Restore / evidence | Manifest SHA-256 |
|---|---|---|---|---|---|---|
| E-01 / E01_CITATION_EVIDENCE_V1 | `09c9d9bb-82a3-4485-9c9d-e9721f2452e4` | `8c266f5dc77e0cfff53215ba44226c719ad78615` | `ce8d8620d2b2fec7f448ae312cf13334b408c01a` | FAIL | SUCCEEDED / VERIFIED | `7f622a3381e6c03dac907f55604f1f82c03e5101e33736b4f22bde50cc8475b2` |
| E-02 / E02_SCORING_FREEZE_V1 | `e39e62ae-be73-4e52-8cab-1f878637a0c6` | `8c266f5dc77e0cfff53215ba44226c719ad78615` | `ce8d8620d2b2fec7f448ae312cf13334b408c01a` | PASS | SUCCEEDED / VERIFIED | `e6b74b7e78fa40a77d0c3c99315592e2e7713e9891d43f68b8d4b437d2d28364` |

- E01-A3 FAIL: `change-injections.jsonl`의 실제 제거(affected_rows=1, absence_confirmed=true)·같은 digest 복원,
  `report-reads.jsonl`의 세 보고서·타임라인 GET 200(2→1→2), `judgement.json`의
  `P1: an affected item kept its score and citation after evidence removal`. 수정 후 판정으로 덮어쓰지 않는다.
- E01-A1/A2 PASS: `citation-cases.jsonl`, `model-emissions.jsonl`, `report-records.jsonl`의 다섯 모드 출력·저장.
  E01-A4 PASS: 제거 전/복원 후 조회·저장 동일, `recovery.json` 복구·teardown 성공.
- E01-D1: storage-probe의 세 모드 노출은 보조 관찰. OTHER_CRITERION NOT_OBSERVED. ID-004-17 한 기준 설계와
  FR-013 네 모드 요구 차이는 미해결이며 closure 전 검토한다. 최초 bundle을 보완해 채우거나 verdict를 바꾸지
  않는다. D1은 E01-A1/A2 판정 근거가 아니다.
- E02-A1/A2/A3 PASS: `frozen-inputs.json`, `criteria-versions.json`, `report-records.jsonl`, `report-reads.jsonl`,
  `recompute.json`. v2 제품 API 발행 뒤 두 번째 74점, 첫 보고서 72점·원본 digest 그대로.
  INCONCLUSIVE/필수 누락 evidence 없음. PASS는 실행된 E-02와 확인된 증거에 한정한다.
- 원본: workspace `cp-local/spec004-official/runs/<Run ID>/`. 별도 명령·잔여행·시간 원장:
  `cp-local/spec004-official/commands/inspection-E-01.json`, `inspection-E-02.json`, `official-time-audit.json`.
  명령·시간·한계는 validation T080~T082. 각각 17개 파일과 manifest 해시가 show/verify·두 실행 후 동일하다.
- 초기 Run에는 retest-diff가 없으며 EV4-10의 child 계보 파일은 해당 없음이다.
- T083 분류, 조건부 수정·child T084~T088, 전체 매핑·완료 gate T089~T097은 미완료다.

## T084 D1 correction child (2026-10-07; T088 partial)

| Parent → child | ControlProof / WhyYou execution sources | Assertions | D1 | Restore / evidence | Child manifest SHA256 |
|---|---|---|---|---|---|
| `09c9d9bb-82a3-4485-9c9d-e9721f2452e4` → `ec0c895d-4617-457a-94ce-7d0198e1c6a5` | `69d3c003e468d3fd1c84070a5413d86b1e252f77` / `ce8d8620d2b2fec7f448ae312cf13334b408c01a` | A1/A2/A4 PASS, A3 FAIL | EMPTY AXIS_DROPPED; NONEXISTENT/OTHER_APPLICANT/OTHER_CRITERION SHOWN_AS_WRITTEN | SUCCEEDED / VERIFIED; residue 0 | `606cf7a0d70bc1a8cfef3743fca2c7b95334e88dcd1a0e58acd65cd975f3250f` |

- FR-013/D1 runner omission is resolved for new Runs by two VALID probe criteria, verified donor provenance
  and four-mode writes (T084, ID-004-34). Tests: seed_adapter, e01_removal_restore, presentation_spec004;
  implementations: seeds/spec004_subjects.py and engine/executors/e01.py.
- EV4-02/04/05/09/10: child spec004-lanes.json, storage-probe.json (other_criterion_source),
  report-records.jsonl PRE_PROBE/POST_RESTORE, report-reads.jsonl POST_PROBE, change-injections.jsonl,
  recovery.json, retest-link.json and retest-diff.json. Before/after stored item/Evidence projections match;
  no lane identities reused. Source diff is ControlProof-only; WhyYou/model/scenario unchanged.
- Both original parent manifests and all 17 registered files are unchanged. Original result mappings above
  remain historical facts; the parent's missing fourth D1 observation is not filled retrospectively.
- Commands/inspection: workspace cp-local/spec004-official/commands/t084-d1-child/. Raw evidence outside Git.
  Generic retest reason wording caveat and exact timing/full-suite records are in validation.
- A3 TARGET_CONTROL_DEFECT remains. T085/T086, A3 lineage portion of T088 and T089~T097 incomplete.
  No claim of four-mode target PASS, AWS validation or Spec completion.

## T085/T086 approved WhyYou remedy PR (2026-10-08)

FR-051 / E01-A3: ID-004-30 six-file availability plan approved; implementation WhyYou b15ba8a on
yeonwoo/controlproof-e01-e02-report-evidence (base ce8d862). Repository scoped transcript lookup + company
report view wiring expose the existing H-4 transcript_available boolean without modifying stored scoring.
OpenAPI/TypeScript optional-field contracts synchronized. Tests: new test_report_evidence_availability and
expanded test_report_view_contract; focused 15 and reporting/runtime 184 PASS; consumer typecheck and
scoped ruff PASS. PR https://github.com/jhkim0602/gbsa_aws/pull/8 OPEN, targeting integration, not merged.

This is implementation/automatic evidence, not a new actual A3 verdict. Original E-01 parent and D1 child
remain sealed FAIL; E-02 parent remains PASS. No new EV4 actual manifest exists for this product fix.
T088 product-remedy child and full FR/SC mapping/closure T089~T097 remain pending.
