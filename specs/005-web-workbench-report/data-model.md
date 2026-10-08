# Data Model: Spec 005 웹 워크벤치·보고서

웹이 쓰는 엔티티다. 판정과 증적은 봉인 bundle이 원천이며 웹은 복사·표시만 한다. 웹이 새로 저장하는 것은 준비 상태 확인 저장본과 수정 메모뿐이다.
필드 이름은 [contracts/web-read-model.md](./contracts/web-read-model.md)의 JSON과 같다.

## 1. CatalogEntry (카탈로그 항목) — `catalog/mvp-scenarios.yaml`

| 필드 | 형식 | 규칙 |
|---|---|---|
| `id` | 문자열 | `N-01`~`A-03` 12개, 중복 없음 |
| `control` | `N`·`H`·`E`·`A` | 통제 4종 |
| `control_label` | 문자열 | 화면 묶음 머리(예: "고지·동의 (N)") |
| `question` | 문자열 | 범위표 §3 "질문" |
| `mvp_treatment` | `EXECUTED`·`NOT_RUN`·`NO_TEST_TARGET` | 범위표 §3 "2주 MVP 처리"와 같아야 함(시험) |
| `owner_spec` | 문자열 | 범위표 §3 "담당 Spec" |
| `target_exists` | 불리언 | A-01~A-03만 거짓 |
| `profiles[]` | 목록 | 실행 프로필(`EXECUTED`만), 프로필별 시나리오 파일·명령 틀 |
| `official_status` | 객체 | `result`(`PASS`·`FAIL`·`INCONCLUSIVE`·`NOT_RUN`), `reason_code`(INCONCLUSIVE면 필수), `summary`, `validation_ref`(문서 경로·절), `records[]`(Run ID·역할 parent/child/final·manifest SHA-256 있으면) |
| `explanation` | 객체 | `intent`, `protected_object`, `policy_basis`(내부 통제 기준·V4 근거만, 법 조문 없음), `implementation_location`(사람 말), `synthetic_data`, `manual_steps`, `not_run_reason`·`follow_up_condition`(NOT_RUN), `absence_evidence`(NO_TEST_TARGET), 각 값의 `source` |

검증: 12개, 처리별 5·4·3, `NO_TEST_TARGET` 항목의 `profiles`는 비어 있음, `NOT_RUN`·`NO_TEST_TARGET` 항목의 `official_status.result`는 각각
`NOT_RUN`·`INCONCLUSIVE`(reason `NO_TEST_TARGET`).

## 2. ReadinessRecord (준비 상태 확인 저장본) — `.controlproof/web/preflight/`

| 필드 | 형식 | 규칙 |
|---|---|---|
| `scenario_id`, `execution_profile` | 문자열 | 카탈로그 프로필 중 하나 |
| `result_kind` | `READINESS`·`ERROR` | 명령줄 출력 그대로(R-010) |
| `readiness` | `READY`·`RUNNER_NOT_READY`·`ACCESS_BLOCKED`·`NO_TEST_TARGET` | `READINESS`일 때만 |
| `error_kind` | 문자열 | `ERROR`일 때만, 사용법 오류는 `USAGE` |
| `checked_at` | 시각 | 명령줄 payload 값 |
| `operator_action` | 문자열 | 준비 안 됨이면 필수, 비민감 |
| `capabilities` | 객체 | Spec 004 프로필 `{ready, required}` |
| `exit_code` | 정수 | 기록만, 해석에 쓰지 않음 |
| `stored_payload` | 객체 | 경계 redaction을 거친 원 payload |

상태: 없음 → 확인 중(서버 잠금) → 저장됨. 120초 초과는 `result_kind=ERROR`, `error_kind=UNEXPECTED`, 조치 문장 "준비 상태 확인 시간이 초과됐습니다".

## 3. RunRecordView (봉인 Run 뷰)

| 필드 | 원천 |
|---|---|
| `run_id`, `scenario_id`, `scenario_version`, `execution_profile`, `target_version`, `started_at`, `ended_at`, `run_state` | `run.json` |
| `integrity` | `VERIFIED`·`INVALID`·`UNREADABLE` (`verify_bundle`) + 문제 항목 목록 |
| `verdict`, `reason_code`, `summary`, `missing_evidence`, `unverified_scope` | `judgement.json`(VERIFIED일 때만) |
| `assertions[]` | AssertionView |
| `evidence[]` | EvidenceItem(`evidence_index`) |
| `restore` | 복구 상태·시간·예산 준수·`manual_cleanup_required` |
| `limitations[]` | projection의 한계 + 카탈로그 한계 |
| `record_origin` | `ACTUAL`(실제 root)·`DEMO`(DEMO root) |
| `record_role` | `OFFICIAL`(카탈로그 공식 Run ID와 같음)·`WEB_VALIDATION`(Spec 005 재실행)·`OTHER` |
| `parent_run_id` | `run.json` |

규칙: `integrity != VERIFIED`면 `verdict`·`assertions`를 비운다. `run_state = RESTORE_FAILED`면 실행 안전 배지를 판정 배지보다 먼저 둔다.
`run_state = ABORTED`면 실행 상태 "중단(ABORTED)"을 판정보다 먼저 보이고 대상 서비스 판정으로 표시하지 않는다(봉인 판정은 그대로 함께).

## 4. AssertionView

`assertion_id`, `description`(봉인 snapshot), `expected`, `actual`, `status`(`PASS`·`FAIL`·`INCONCLUSIVE`), `reason_code`(INCONCLUSIVE만),
`detail`, `source_requirements`, `required_evidence_ids`, `evidence_refs[]`, `missing_evidence_ids[]`, `plain_meaning`(비개발자 문장, 카탈로그·
projection 문장에서 고르며 내부 이름·fixture·파일 이름 없음).

## 5. EvidenceItem

`ref`(`artifact:`·`file:`·`intrinsic:`·cross-run), `evidence_name`(사람용; `display_name` 키는 엔진 redaction이 개인 표시 이름으로 가려서 쓰지 않음, ID-005-08), `relative_path`(run root 기준, 개발자용), `mime_type`, `size_bytes`,
`sha256`, `phase`·`step_id`·`attempt`(있으면), `evidence_requirement_ids[]`, `viewable`(텍스트·256 KB 이하·경계 검사 통과).

## 6. LineageView / ComparisonView

`parent_run_id`, `child_run_id`, `parent_integrity`, `parent_unchanged`(`true`·`false`·`null`; 부모 무결성 값의 출처는 기록 형식에 따라 Spec 003·004 `retest-link.json`의 `parent_bundle_digest`,
Spec 002 child manifest의 다른 Run 원본 참조 `bundle_digest`, Spec 001 형식은 없음 → `null`과 `parent_integrity_source: "NONE_LEGACY"`), `parent_integrity_source`,
`changed_dimensions`(`retest-link.json` 그대로), `diff`(`retest-diff.json` 요약), `assertion_changes[]`(`assertion_id`, before, after,
before_evidence, after_evidence), `remaining_failures[]`. 부모 검증 실패나 digest 불일치(`false`)면 비교 대신 계보 문제를 보인다. `null`(이전 형식)은 계보 문제가 아니며 부모
자체의 무결성 결과와 함께 "부모 불변 값 기록 없음(이전 형식)"을 보인다.

## 7. ReportView

`target_and_versions`, `purpose_and_scope`, `fixed_scope_sentence`(범위표 고정 문구), `synthetic_data_notice`, `catalog_status[12]`, `counts`
(네 범주 + 판정 불가 reason code별), `scenario_expectations[]`, `major_failures[]`, `evidence_summary`, `versions`(정책·모델·프롬프트·평가기준;
fixture 이름은 개발자용), `lineages[]`, `test_only_additions[]`, `unverified_scope[]`, `limitations[]`, `ai_score_principle`, `legal_notice`,
`items_present`(R1~R13·C1~C9 표지).

## 8. FixMemo — `.controlproof/web/memos/<run_id>.jsonl`

`schema_version`(`controlproof.fix-memo.v1`), `memo_id`(UUID), `run_id`, `author`(1~80자), `created_at`, `text`(1~2000자). 추가만 가능.
저장 전 강화 스캐너 통과 필수. bundle·verify 대상 아님.

## 9. BadgeSpec — `engine/web/badges.py`

`key`, `label_ko`, `label_en`(표준 명칭), `icon`, `shape`(`round`·`square`·`filled`), `tone`, `description`. spec "승인된 화면 구조와 상태 이름" 표의
15개 행과 1:1. 템플릿은 key로만 고른다.

## 10. UsabilityReviewRecord (문서, Validation에 기록)

참여자(역할·비작성자 여부·익명 ID), 과업 3개·질문 7개별 소요 시간·정답 여부·오독 유형(치명적 여부), 사용한 화면 기록(실제 root의 Run ID),
진행자(태오)·일시. 통과 판단은 SC-008·SC-009.
