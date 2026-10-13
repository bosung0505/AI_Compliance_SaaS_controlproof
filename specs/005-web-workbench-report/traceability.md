# Spec 005 추적표 (T073)

FR-001~FR-037과 SC-001~SC-011을 작업·자동 시험·실제 검증 기록에 연결한다. 작성 2026-10-12, 기준 005 HEAD `ed1b0b1`.

## 0. 읽는 법

- **작업**: `tasks.md`가 그 요구사항을 태그로 달아 둔 작업. 태그가 없는 요구사항은 `—`이고 §5에 따로 적는다.
- **자동 시험**: 시험 함수까지 확인한 결과다. 파일명은 `tests/` 아래 경로에서 디렉터리를 줄여 적는다(`unit/test_web_badges.py` = `tests/unit/test_web_badges.py`).
- **실제 검증**: Phase 9(웹 PC 재실행, 2026-10-10~12)와 T069 웹 확인 기록. 상세는 `validation.md`.
- `tests/web/`의 화면 시험은 Playwright가 있을 때만 돌고, 없으면 skip된다(`tests/web/conftest.py`).
- 이 표는 Spec 005의 FR-001~037·SC-001~011만 다룬다. 시험 파일 주석의 FR-038 이상은 다른 Spec의 번호다.

## 1. 기능 요구사항 (FR-001~FR-037)

### 워크벤치 (FR-001~FR-007)

| FR | 요약 | 작업 | 자동 시험 | 실제 검증 |
|---|---|---|---|---|
| FR-001 | 대상·버전·정책 버전·통제 4종·시나리오 12개 표시 | T023, T026, T027, T029, T032 | `unit/test_web_readmodel_workbench.py::test_header_counts_and_groups_copy_the_catalog`, `unit/test_web_run_readability.py::test_workbench_target_commit_from_readiness`, `web/test_workbench_screen.py::test_layout_demo_band_and_no_horizontal_overflow` | T069 SC-001 PASS |
| FR-002 | 시나리오별 대상 유무·준비 상태·실행 방식·최근 결과·담당 Spec·Run 수, 통제별 묶음 | — | `unit/test_web_readmodel_workbench.py::test_header_counts_and_groups_copy_the_catalog`, `::test_readiness_common_time_and_differing_rows`, `::test_web_validation_runs_are_counted_separately`, `web/test_workbench_screen.py::test_one_common_checked_at_and_only_differing_rows_show_time` | T069 SC-001 PASS |
| FR-003 | 12개 상태는 범위표와 일치, 화면이 계산하지 않음, 어긋나면 표시 | T021, T075 | `unit/test_catalog_matrix_parity.py::test_rule1_matrix_rows_match_12_of_12`, `::test_rule2_counts_and_fixed_sentence`, `unit/test_web_readmodel_workbench.py::test_missing_official_bundle_shows_no_record_never_not_run`, `::test_mismatch_when_official_bundle_verdict_differs`, `unit/test_web_readmodel_report.py::test_counts_and_status_rows_copy_the_catalog` | T069 SC-001 PASS (12/12 일치) |
| FR-004 | 네 범주 따로 집계, 판정 불가는 중립색·reason code 배지 | — | `unit/test_web_badges.py::test_lookups_use_the_table`, `unit/test_web_readmodel_workbench.py::test_header_counts_and_groups_copy_the_catalog`, `web/test_workbench_screen.py::test_count_cards_and_neutral_inconclusive_card` | T069 SC-001 PASS (PASS 4·FAIL 0·판정 불가 4) |
| FR-005 | `NOT_RUN`/`INCONCLUSIVE`, `NO_TEST_TARGET`/`RUNNER_NOT_READY` 구분 | T022, T028 | `unit/test_web_badges.py::test_exactly_the_fifteen_spec_rows`, `::test_shape_families`, `::test_lookups_use_the_table`, `web/test_workbench_screen.py::test_runner_not_ready_and_no_test_target_badges_differ` | T069 SC-006 PASS |
| FR-006 | A-01~A-03은 부재 근거와 함께, 실행·진행률·통과 요소 없음 | — | `unit/test_catalog_matrix_parity.py::test_rule2_status_shapes`, `unit/test_web_readmodel_scenario.py::test_not_run_and_no_target_have_no_profiles_or_commands`, `web/test_workbench_screen.py::test_a_rows_have_no_run_control_or_progress`, `web/test_scenario_screen.py::test_not_run_and_no_target_have_no_run_elements` | T069 SC-006·SC-010 PASS |
| FR-007 | 실행 가능·실패·판정 불가 거르기, 재시험 필요 실패, 보고서 진입 | — | `unit/test_web_readmodel_workbench.py::test_preserved_first_failures_and_retest_needed`, `web/test_workbench_screen.py::test_filters_5_0_4`, `web/test_report_screen.py::test_report_reached_from_the_workbench` | T069 (워크벤치 화면 확인) |

### 시나리오 상세 (FR-008~FR-012)

| FR | 요약 | 작업 | 자동 시험 | 실제 검증 |
|---|---|---|---|---|
| FR-008 | 정의 원천의 의도·전제·단계·assertion·증적·복구·시간·제외를 그대로 | T048~T051 | `unit/test_web_readmodel_scenario.py::test_definition_from_scenario_file_without_runs`, `::test_definition_from_sealed_snapshot_when_a_run_exists`, `::test_h03_and_e03_split_by_profile`, `unit/test_catalog_matrix_parity.py::test_rule3_seven_profiles_map_to_existing_scenario_files` | T069 (E-01·E-02 상세 확인) |
| FR-009 | 보호 대상·정책 근거·구현 위치·합성 데이터·수동 단계, 출처 표시, 법 조문 금지 | T021, T027 | `unit/test_catalog_matrix_parity.py::test_rule4_sources_present_and_no_legal_articles`, `unit/test_web_readmodel_scenario.py::test_legal_mapping_notice_and_explanation`, `web/test_scenario_screen.py::test_e01_shows_preconditions_and_copyable_command_without_run_button` | T069 (법 조문 비표시 확인) |
| FR-010 | `NOT_RUN`은 사유·후속 조건, `NO_TEST_TARGET`은 부재 근거·생겼을 때 처리 | T027 | `unit/test_catalog_matrix_parity.py::test_rule2_status_shapes`, `unit/test_web_readmodel_scenario.py::test_not_run_and_no_target_have_no_profiles_or_commands`, `web/test_scenario_screen.py::test_not_run_and_no_target_have_no_run_elements` | T069 SC-006 PASS |
| FR-011 | 준비 상태는 확인 시각과 함께, 막힌 항목·조치 문장, 사용법 오류와 구분 | T024, T030 | `unit/test_web_preflight.py::test_ready_record_is_stored_with_payload_checked_at`, `::test_usage_error_is_a_tool_error`, `::test_timeout_is_an_unexpected_error`, `::test_unparseable_output_is_an_unexpected_error`, `unit/test_web_readmodel_scenario.py::test_readiness_with_checked_at_and_tool_error`, `unit/test_web_readmodel_workbench.py::test_usage_error_is_a_tool_error_not_readiness`, `web/test_scenario_screen.py::test_preflight_from_detail_stores_a_new_checked_at` | Phase 9 준비 상태 확인 2건(E-02 16/16, E-01 18/18), T069 SC-010 PASS |
| FR-012 | 웹이 시작할 수 있는 동작은 준비 상태 확인뿐, 나머지는 명령 안내 | T024, T025, T030, T031 | `unit/test_web_preflight.py::test_command_is_built_from_catalog_profiles_only`, `unit/test_web_readmodel_scenario.py::test_commands_only_from_catalog_templates`, `contract/test_web_http.py::test_route_table_has_no_run_retest_or_cleanup_start`, `::test_concurrent_preflight_post_is_409`, `web/test_workbench_screen.py::test_preflight_form_is_the_only_action_and_disabled_on_demo`, `web/test_compare_screen.py::test_retest_only_as_a_command` | T069 SC-010 PASS (POST 라우트 2개뿐) |

### 실행 결과·증적 (FR-013~FR-020)

| FR | 요약 | 작업 | 자동 시험 | 실제 검증 |
|---|---|---|---|---|
| FR-013 | 실행 ID·시나리오·프로필·대상 버전·시각·상태·판정·reason code·요약 | T002, T035, T037, T038, T041, T057 | `unit/test_web_readmodel_run.py::test_verified_run_copies_verdict_assertions_and_reason_codes`, `unit/test_web_run_readability.py::test_target_commit_short_and_hash_in_developer`, `contract/test_web_http_us2.py::test_run_json_and_html` | T069 SC-002 PASS (Run 11개) |
| FR-014 | assertion별 기대·관찰·결과·설명·근거 요구, `INCONCLUSIVE`는 reason code 필수 | T007 | `unit/test_web_readmodel_run.py::test_verified_run_copies_verdict_assertions_and_reason_codes`, `::test_inconclusive_reason_code_is_copied`, `::test_assertion_evidence_refs_and_missing_ids_come_from_the_index`, `unit/test_evidence_index.py::test_by_assertion_is_artifact_ids_union_snapshot_requirements` | T069 SC-002 PASS, Run 5(N-02) reason code 확인 |
| FR-015 | assertion → 원본 증적 이동, 증적별 이름·형식·크기·SHA-256·수집 단계, 누락 표시 | T007, T015, T036, T040, T057 | `unit/test_evidence_index.py`(6개 전부), `unit/test_web_evidence_view.py::test_text_evidence_is_shown_as_sealed`, `::test_unknown_reference_is_not_found`, `::test_run_view_marks_viewable_evidence`, `unit/test_web_readmodel_run.py::test_every_pass_or_fail_assertion_reaches_evidence_with_sha256`, `unit/test_web_run_readability.py::test_evidence_names_are_distinguishable`, `::test_every_evidence_label_comes_from_the_catalog`, `web/test_run_screen.py::test_workbench_to_result_to_evidence_in_three_clicks`, `contract/test_web_http_us2.py::test_evidence_routes` | T069 SC-003 PASS (assertion 41개 전부 증적 도달) |
| FR-016 | 판정·assertion은 봉인 기록 값만, 화면이 다시 비교해 만들지 않음 | T057 | `unit/test_web_readmodel_run.py::test_verified_run_copies_verdict_assertions_and_reason_codes`, `::test_restore_timing_is_copied_not_computed`, `unit/test_web_readmodel_workbench.py::test_mismatch_when_official_bundle_verdict_differs` | T069 SC-002 PASS (CLI `show`·`verify`와 불일치 0) |
| FR-017 | 보여 주기 전 무결성 확인, 실패하면 판정 대신 무결성 실패(ABORTED 예외 1건) | T057 | `unit/test_web_readmodel_run.py::test_id_005_01_case1~case3`, `::test_aborted_with_hash_mismatch_is_integrity_failure`, `::test_unreadable_bundle`, `unit/test_web_readmodel_workbench.py::test_changed_file_after_cached_verify_is_reverified_as_integrity_failure`, `unit/test_web_evidence_view.py::test_integrity_failed_run_blocks_evidence`, `unit/test_web_readmodel_compare.py::test_invalid_parent_is_a_lineage_problem`, `unit/test_web_run_readability.py::test_aborted_integrity_label_never_says_verified`, `::test_normal_integrity_label`, `web/test_run_screen.py::test_integrity_failure_is_not_a_fail`, `web/test_run_readability_screen.py::test_aborted_run_never_shows_verified`, `contract/test_web_http_us2.py::test_integrity_failed_run_is_200_with_failure_screen` | T069 SC-002 PASS (`e2e8e71d` INVALID 표시가 SC-002 근거) |
| FR-018 | 적용·해제 조건, 복구 결과·예산, 수동 정리, `RESTORE_FAILED`·중단은 대상 판정 아님 | T057 | `unit/test_web_readmodel_run.py::test_restore_failed_shows_safety_badge_before_verdict`, `::test_restore_timing_is_copied_not_computed`, `unit/test_web_run_readability.py::test_phase_summary_is_plain`, `::test_change_injection_kinds_are_korean`, `web/test_run_screen.py::test_restore_failure_badge_comes_before_the_verdict`, `::test_aborted_run_shows_state_first_and_missing_evidence` | Phase 9 Run 8개 모두 복구 SUCCEEDED, `manual_cleanup_required: false` |
| FR-019 | 비개발자용 먼저, 개발자용은 한 단계 더, 기본 문장에 내부 이름 금지 | T021, T057 | `unit/test_catalog_matrix_parity.py::test_rule6_plain_text_has_no_internal_fixture_or_file_names`, `unit/test_web_readmodel_report.py::test_fixed_model_names_only_in_developer_details`, `unit/test_web_run_readability.py::test_unverified_scope_in_korean_with_raw_in_developer`, `web/test_run_screen.py::test_fail_run_plain_first_developer_collapsed`, `web/test_run_readability_screen.py::test_steps_in_plain_words_ids_only_in_developer`, `::test_english_scope_and_snapshot_hash_hidden_by_default` | T069 (Run 7 FAIL 화면 확인) |
| FR-020 | 실패 규칙만 보기 | — | `web/test_run_screen.py::test_failed_only_toggle` | T069 (Run 7 화면 확인) |

### 재시험 비교 (FR-021~FR-024)

| FR | 요약 | 작업 | 자동 시험 | 실제 검증 |
|---|---|---|---|---|
| FR-021 | 부모·child·grandchild 연결, 각 Run 판정은 그 기록 그대로 | T053~T056 | `unit/test_web_readmodel_compare.py::test_spec004_lineage_from_retest_link`, `::test_grandchild_lineage_lists_all_generations`, `::test_not_a_retest_or_unknown_is_not_found`, `web/test_compare_screen.py::test_two_runs_side_by_side_parent_unchanged`, `::test_compare_reached_from_run_and_report` | T069 SC-005 PASS (`86cd0010` FAIL → `7f25b475` PASS) |
| FR-022 | assertion별 이전·이후 결과·증적·변화, 남은 실패, 변경 차원 | — | `unit/test_web_readmodel_compare.py::test_spec004_lineage_from_retest_link`, `::test_remaining_failures`, `web/test_compare_screen.py::test_two_runs_side_by_side_parent_unchanged` | T069 SC-005 PASS (A3만 FAIL→PASS), Run 8 retest-diff 1필드 |
| FR-023 | 부모 불변을 재시험 기록의 부모 무결성 값으로 확인, 다르면 계보 문제 | — | `unit/test_web_readmodel_compare.py::test_spec002_lineage_from_cross_run_reference`, `::test_spec001_lineage_is_legacy_not_a_problem`, `::test_changed_parent_digest_is_a_lineage_problem`, `::test_invalid_parent_is_a_lineage_problem` | Run 8 뒤 부모 manifest `fe5ac508…`·digest `75c10fe6…`·파일 해시 목록 `3ed62134…` 불변, 재verify VERIFIED |
| FR-024 | 수정 메모는 봉인 기록 밖, 작성자·시각·대상 Run, 판정·증적 불변 | T036, T039, T040 | `unit/test_web_memos.py`(7개 전부), `web/test_run_screen.py::test_memo_form_is_separate_from_the_sealed_record`, `contract/test_web_http_us2.py::test_memo_post_writes_only_under_web_memos`, `::test_memo_post_rejections` | T069 SC-010 (메모 경로는 실행 동작 아님) |

### 결과 보고서 (FR-025~FR-029)

| FR | 요약 | 작업 | 자동 시험 | 실제 검증 |
|---|---|---|---|---|
| FR-025 | V4 §8.7 항목 22개를 한 화면에 | T043~T046 | `unit/test_web_readmodel_report.py::test_all_22_items_present`, `::test_test_only_additions_are_marked_as_test_means`, `::test_failures_lineages_and_expectations`, `web/test_report_screen.py::test_22_item_markers_visible`, `contract/test_web_http_us2.py::test_report_routes` | T069 SC-004 PASS (R1~R13·C1~C9 22/22) |
| FR-026 | 주장 범위 한정, 법적 준수 비보증 문장, 미검증 범위, `LOCAL_EMULATED` 구분 | — | `unit/test_web_readmodel_report.py::test_limits_and_unverified_scope` | T069 SC-004 PASS |
| FR-027 | AI 점수는 참고, 최종 결정은 권한 있는 사람 | — | `unit/test_web_readmodel_report.py::test_ai_score_principle_and_human_decision_location` | T069 SC-004 PASS |
| FR-028 | 범위 문구는 범위표 고정 문구와 같은 뜻, "12개 PASS" 금지 | — | `unit/test_web_readmodel_report.py::test_fixed_sentence_is_the_matrix_quote`, `::test_forbidden_phrases_absent`, `unit/test_catalog_matrix_parity.py::test_rule2_counts_and_fixed_sentence`, `web/test_report_screen.py::test_22_item_markers_visible` | T069 SC-004 PASS |
| FR-029 | Run마다 그 Run이 기록한 한계를 보고서에 | — | `unit/test_web_readmodel_report.py::test_limits_and_unverified_scope`, `::test_fixed_model_names_only_in_developer_details` | T069 SC-004 PASS |

### 데이터 출처와 안전 (FR-030~FR-033)

| FR | 요약 | 작업 | 자동 시험 | 실제 검증 |
|---|---|---|---|---|
| FR-030 | 판정·증적의 출처 표시, 합성 기록에 `DEMO DATA` | T023, T031, T033, T062~T068 | `unit/test_web_readmodel_run.py::test_record_origin_and_role`, `unit/test_web_readmodel_workbench.py::test_demo_and_actual_never_share_a_view`, `::test_missing_official_bundle_shows_no_record_never_not_run`, `::test_web_validation_runs_are_counted_separately`, `unit/test_web_readmodel_report.py::test_demo_report_never_mixes_into_actual`, `unit/test_catalog_matrix_parity.py::test_rule5_official_run_ids_appear_in_their_validation_document`, `contract/test_web_http.py::test_workbench_json_schema_and_boundary`, `web/test_report_screen.py::test_demo_report_never_mixes_into_actual_counts` | T069 SC-011 PASS (실제 `data_origin ACTUAL`, DEMO 표시 0건) |
| FR-031 | 절대 경로·토큰·자격 증명·개인정보·원문 금지, 출력 전 검사 | T004, T009, T025, T031, T036, T058 | `unit/test_output_paths.py`(6개), `unit/test_scan_strict.py::test_scan_never_returns_matched_values`, `unit/test_web_evidence_view.py::test_binary_evidence_is_not_shown`, `::test_text_failing_the_strict_scan_is_not_shown`, `unit/test_web_memos.py::test_strict_scan_runs_before_write`, `unit/test_web_preflight.py::test_stored_payload_goes_through_the_output_boundary`, `integration/test_web_response_redaction.py`(2개), `contract/test_web_http.py::test_html_pages_have_no_absolute_paths`, `contract/test_web_http_us2.py::test_evidence_names_survive_the_output_boundary`, `::test_no_view_field_is_masked_by_the_boundary` | T069 SC-007 PASS (파일 115개 검사, 위반 0) |
| FR-032 | 웹은 읽기만, 수정·삭제 없음 | T001 | `unit/test_web_memos.py::test_bundle_and_verify_result_unchanged` | T069 (Run 폴더 11개 확인 전후 동일, git status 비어 있음) |
| FR-033 | 합성 데이터·로컬 시험 환경만, 실제 지원자 데이터 미연결 | — | **전용 시험 없음** (§5 참고) | Phase 9 전 Run `environment_kind LOCAL_EMULATED`, fixture만 사용, 외부 AI 끔 |

### 사용성 검토·위험 보완 (FR-034~FR-037)

| FR | 요약 | 작업 | 자동 시험 | 실제 검증 |
|---|---|---|---|---|
| FR-034 | 역할별 사용성 검토 수행·기록(표본 6명, 과업 3개, 질문 7개) | T070, T071 | 해당 없음(사람 대상) | T070 완료(`usability/review-kit.md`), **T071 태오 대기** |
| FR-035 | 위험 1·2·3·5의 출력 불일치는 실패 시험 먼저, 종료 코드 불변 | T004, T006, T010, T013, T014, T018 | `contract/test_cli_output_additions.py`(6개 전부), `unit/test_output_paths.py::test_human_cli_text_goes_through_the_boundary`, `::test_json_cli_output_has_no_absolute_path`, `unit/test_scan_strict.py::test_v2_finds_escaped_windows_user_path_that_v1_misses`, `unit/test_web_preflight.py::test_exit_code_is_stored_but_not_interpreted`, `::test_usage_error_is_a_tool_error` | Phase 9 Run 8개 CLI 종료 코드 기대와 일치(Run 5 exit 4, Run 7 exit 3) |
| FR-036 | 검사 강화 전 기존 bundle 먼저 검사해 차이 기록, 봉인 파일 불변 | T005, T008, T011, T012, T016, T017, T019, T020 | `contract/test_scan_bundles_script.py`(2개), `contract/test_verify_redaction_profile.py`(7개 전부), `unit/test_scan_strict.py`(4개), `unit/test_output_paths.py::test_v1_pattern_is_unchanged_until_t020` | T016 완료, **T019 보성 PC 검사 대기**. Phase 9 신규 bundle 전부 `redaction_profile controlproof.redaction.v2` |
| FR-037 | 위험 4는 이 Spec 밖 별도 보완, actual validation 전 완료 | T061 | 해당 없음(Spec 005 범위 밖; `integration/test_spec004_retest_cleanup_path.py`는 Spec 004 소속) | T061 완료 2026-10-12, merge `25417ad`(004 tip `9f480d5`) |

## 2. 성공 기준 (SC-001~SC-011)

| SC | 요약 | 작업 | 자동 시험 | 실제 검증 기록 | 상태 |
|---|---|---|---|---|---|
| SC-001 | 12개 상태가 범위표와 12/12 일치 | T021, T023, T026, T034, T069 | `unit/test_catalog_matrix_parity.py::test_rule1_matrix_rows_match_12_of_12`, `unit/test_web_readmodel_workbench.py::test_header_counts_and_groups_copy_the_catalog`, `::test_no_pass_badge_on_not_run_no_target_or_inconclusive_rows`, `web/test_workbench_screen.py::test_no_pass_badge_on_not_run_or_inconclusive_rows` | T069: 12/12 일치, 집계 PASS 4·FAIL 0·판정 불가 4 | **PASS** |
| SC-002 | 웹 판정·assertion·reason code·무결성이 CLI와 일치 | T002, T035, T037, T042 | `unit/test_web_readmodel_run.py::test_verified_run_copies_verdict_assertions_and_reason_codes`, `::test_inconclusive_reason_code_is_copied`, `::test_restore_failed_shows_safety_badge_before_verdict` | T069: Run 11개 전부 불일치 0, `e2e8e71d` INVALID 표시 | **PASS** |
| SC-003 | assertion → 증적 SHA-256까지 3번 이하 이동 | T007, T037, T042 | `unit/test_evidence_index.py`(3개), `unit/test_web_readmodel_run.py::test_every_pass_or_fail_assertion_reaches_evidence_with_sha256`, `web/test_run_screen.py::test_workbench_to_result_to_evidence_in_three_clicks` | T069: 이 세션 8개 Run의 PASS·FAIL assertion 41개 전부 도달 | **PASS** |
| SC-004 | 보고서 22개 항목 전부 표시 | T043, T044, T047 | `unit/test_web_readmodel_report.py::test_all_22_items_present`, `web/test_report_screen.py::test_22_item_markers_visible` | T069: R1~R13·C1~C9 22/22 true | **PASS** |
| SC-005 | 재시험 비교에서 부모 판정 유지·assertion 변화·부모 불변 | T002, T053, T054, T057, T067, T068 | `unit/test_web_readmodel_compare.py::test_spec004_lineage_from_retest_link`, `web/test_compare_screen.py::test_two_runs_side_by_side_parent_unchanged` | T069: `/compare/7f25b475…` 부모 FAIL 유지, A3만 FAIL→PASS, 부모 불변 표시 | **PASS** |
| SC-006 | 12개 행 모두 상태 구분 표시 | T022, T026, T034 | `unit/test_web_badges.py::test_shape_families`, `::test_lookups_use_the_table`, `web/test_workbench_screen.py::test_runner_not_ready_and_no_test_target_badges_differ` | T069: `NOT_RUN` 4개·`NO_TEST_TARGET` 3개 구분 확인 | **PASS** |
| SC-007 | 응답에 민감정보·절대 경로 0건 | T004, T058, T060, T069 | `integration/test_web_response_redaction.py`(2개), `unit/test_output_paths.py::test_v2_pattern_catches_user_paths`, `::test_json_cli_output_has_no_absolute_path`, `unit/test_scan_strict.py::test_scan_never_returns_matched_values`, `unit/test_web_memos.py::test_strict_scan_runs_before_write` | T069: GET 응답 111개 + 저장 파일 4개 = 115개 검사, 위반 0 | **PASS** |
| SC-008 | 비작성자 6명, 질문마다 5명 이상 정답·3분 이내, 치명적 오독 0건 | T070, T071, T072 | 해당 없음(사람 대상) | T070 키트 완료. **T071 미실시** | **대기** |
| SC-009 | 6명 중 5명 이상이 미검증 범위를 범위표와 같이 답 | T070, T071, T072 | 해당 없음(사람 대상) | T070 키트에 정답 기준 포함(4개 미실행·3개 대상 없음·AWS 미검증). **T071 미실시** | **대기** |
| SC-010 | 웹에서 시작 가능한 동작은 준비 상태 확인뿐 | T006, T024, T025, T034, T049, T052, T069 | `contract/test_web_http.py::test_route_table_has_no_run_retest_or_cleanup_start`, `unit/test_web_preflight.py::test_command_is_built_from_catalog_profiles_only`, `web/test_workbench_screen.py::test_preflight_form_is_the_only_action_and_disabled_on_demo`, `web/test_compare_screen.py::test_retest_only_as_a_command`, `contract/test_cli_output_additions.py::test_preflight_and_not_ready_run_and_retest` | T069: form action·POST 라우트 둘뿐, Run·재시험·정리 시작 경로 0건 | **PASS** |
| SC-011 | DEMO와 실제 기록이 섞이지 않음 | T003, T023, T033, T044, T060, T062, T069 | `unit/test_web_readmodel_workbench.py::test_demo_and_actual_never_share_a_view`, `unit/test_web_readmodel_report.py::test_demo_report_never_mixes_into_actual`, `web/test_report_screen.py::test_demo_report_never_mixes_into_actual_counts` | T069: 실제는 `ACTUAL`·`demo false`·DEMO 표시 0건, `/demo/`는 `DEMO` | **PASS** |

판정 요약: SC-001~007, SC-010, SC-011 **PASS**(T069, 2026-10-12). SC-008·SC-009는 T071 뒤 T072에서 판정한다.

## 3. Run ID 대조 (Phase 9, 웹 검증 기록)

공식 Run이 아니라 Spec 005 웹 검증 기록이다(D-018 추가 결정 3). 각 시나리오의 공식 상태는 그 Spec의 Validation을 따른다.

| # | 시나리오·프로필 | 대상 | Run ID | 결과 | 공식 대조 |
|---|---|---|---|---|---|
| 1 | H-03 `H03_DLQ_V2` | `374b122` | `277d3f5a` | PASS A1~A9 | 독립 재현 gate **후보**(보성 결정 대기) |
| 2 | H-03 `H03_MINIMAL_V1` | `374b122` | `1d573850` | PASS A1~A6 | `e42482c9`와 같은 모양 |
| 3 | E-03 `E03_BEFORE_V2` | `374b122` | `fd48f7ff` | PASS 6규칙 | `047fb27b`와 같은 모양 |
| 4 | E-03 `E03_AFTER_V2` | `374b122` | `064afdb0` | PASS A1·A5·A6·A8 | `4e3e424e`와 같은 모양 |
| 5 | N-02 `N02_CONSENT_ORDER_V1` | `374b122` | `1767fb73` | INCONCLUSIVE (A5·A7 INSUFFICIENT_EVIDENCE) | `7b59237e`와 같은 모양 |
| 6 | E-02 `E02_SCORING_FREEZE_V1` | `374b122` | `4a404c73` | PASS A1~A3 | `e39e62ae`와 같은 모양 |
| 7 | E-01 부모 | `ce8d862` worktree | `86cd0010` | FAIL A3만 | `09c9d9bb`와 다섯 항목 일치 |
| 8 | E-01 재시험 | `374b122` | `7f25b475` | PASS A1~A4 | `a5ad4676`와 같은 모양 |

공통: 8개 모두 ControlProof `9856a03` dirty 0, 복구 SUCCEEDED, verify VERIFIED, `redaction_profile controlproof.redaction.v2`.
run root에는 이전 Run 3개(`15cef078`, `e2e8e71d`, `7b59237e`)를 합쳐 11개가 있다. `e2e8e71d`는 봉인 뒤 변경된 기록이라 INVALID로 나오며 SC-002 근거로 쓴다.

## 4. 미검증 범위

- **AWS**: `NOT_RUN`. 모든 Run은 `LOCAL_EMULATED`에서 했다. `LOCAL_EMULATED`는 AWS가 아니다.
- **다른 PC 재현**: H-03 DLQ Run 1(`277d3f5a`)이 **현재 통합 대상(`374b122`) 기준 독립 PC 재현 gate로 인정됐다**(D-019, 2026-10-13).
  기존 clean clone을 쓴 별도 PC 재현이고, 플레이북 §6 지정 commit과 동일 조건의 재현은 아니다. 이 한 건에만 적용하며 다른 시나리오나 AWS로
  확대하지 않는다. main 병합은 별도 승인이 남는다.
- **`NOT_RUN` 4개**(H-01, H-02, N-01, N-03): 이번 실행 범위 밖.
- **`NO_TEST_TARGET` 3개**(A-01~A-03): WhyYou에 대상 기능이 없다. ControlProof는 새 기능을 만들지 않는다.
- **사용성 검토**: T071 미실시. SC-008·SC-009 미판정.
- **T019**: 보성 PC 기존 bundle 검사 미수신.

## 5. 자동 시험이 없는 요구사항

| FR/SC | 왜 없는가 | 대신 무엇으로 확인하는가 |
|---|---|---|
| FR-033 | 전용 시험 없음. 합성 데이터·실제 지원자 데이터 미연결은 환경 설정과 운영 규칙의 성질이다 | 간접: `unit/test_web_readmodel_workbench.py`·`web/test_workbench_screen.py`가 `environment_kind LOCAL_EMULATED`를 단정하고, FR-030 계열 시험이 합성 기록만 쓴다. Phase 9 전 Run이 fixture만 사용하고 외부 AI를 끈 기록 |
| FR-034 | 사람 대상 검토다 | T070 키트, T071 실시, T072 판정 |
| FR-037 | Spec 005 범위 밖의 별도 보완이다 | T061 수동 게이트(완료, merge `25417ad`) |
| SC-008 | 사람 대상 | T071 결과 → T072 판정 |
| SC-009 | 사람 대상 | T071 결과 → T072 판정 |

## 6. FR/SC에 대응하지 않는 시험

계약서·research 결정·가정에만 근거가 있고 FR-001~037·SC-001~011에는 대응 조항이 없는 시험이다. 삭제 대상이 아니라 근거 출처가 다른 항목이다.

| 시험 | 근거 |
|---|---|
| `contract/test_web_http.py::test_bind_address_is_fixed_to_loopback`, `::test_foreign_host_is_421`, `::test_localhost_host_is_accepted`, `::test_post_without_or_with_wrong_token_is_403`, `::test_security_headers_on_every_response`, `::test_not_found_is_json_error` | R-002 로컬 보안 경계, `contracts/web-http.md` |
| `contract/test_cli_output_additions.py::test_show_and_verify_follow_the_run_root_rule` | R-004 run root 우선순위 |
| `unit/test_web_preflight.py::test_second_concurrent_request_is_rejected` | R-007 동시 1건 제한 |
| `unit/test_web_evidence_view.py::test_large_text_is_not_shown` | R-009(e) 256KB 상한 |
| `unit/test_web_memos.py::test_lengths_are_enforced`, `::test_limits_are_inclusive` | A-6 메모 길이 |
| `integration/test_web_performance.py::test_workbench_and_run_screens_within_two_seconds` | A-8 화면 전환 2초 |
| `unit/test_web_readmodel_workbench.py::test_changed_file_after_cached_verify_is_reverified_as_integrity_failure` | R-006 verify 캐시 (FR-017과 공동) |
| `unit/test_web_run_readability.py`·`web/test_run_readability_screen.py` 전체 | ID-005-09 결과 화면 가독성 보정 |
| `unit/test_web_readmodel_run.py` 전체 | ID-005-01 무결성 표시 순서 |

Spec 005 산출물이 아닌 기존 시험: `unit/test_redaction_security.py`(Spec 002~004 봉인·writer redaction), `contract/test_cli_preflight.py`(Spec 001), `contract/test_cleanup_confirm_spec004.py`(Spec 004), `integration/test_spec004_retest_cleanup_path.py`(PR #2, Spec 004). Spec 005에서는 회귀 기준선으로만 쓴다.

## 7. 작성 중 발견한 문서 불일치

레포를 고치지 않고 적어 둔다. Phase 11 converge에서 처리한다.

- `tasks.md`에 `tests/contract/test_web_http_us2.py` 경로가 없다. T036/T040 산출물인데(파일 docstring과 커밋 `b6f194f`) 작업 줄에 파일명이 적혀 있지 않다.
- `tasks.md`의 FR 태그가 13개 요구사항에 없다: FR-002, FR-004, FR-006, FR-007, FR-016(T057에만), FR-020, FR-022, FR-023, FR-026, FR-027, FR-028, FR-029, FR-033. 자동 시험은 있으므로 구현 누락이 아니라 태그 누락이다. 이 표의 "작업" 열 `—`가 그것이다.
- `tasks.md:255`의 "PR #2가 004에 병합되면 004를 다시 합친다"는 T061 완료(`25417ad`) 전 시점 문구다.
