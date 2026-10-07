# Data Model: E-01·E-02 점수 근거·평가 기준 보존 검증

Spec 001~003의 `Run`, `Observation`, `EvidenceArtifact`, `AssertionResult`, `Judgement`, `RetestLink`,
`TargetSnapshot`, `TargetEnvironmentSnapshot`, restore lifecycle, 차단 파일, Spec 003의 `ConsentPolicySnapshot`·
`ConsentStateSnapshot`·`ProcessingAttemptReceipt`를 유지한다. 아래 모델은 additive하게 추가한다.

## 1. ExecutionProfile

| Field | `E01_CITATION_EVIDENCE_V1` | `E02_SCORING_FREEZE_V1` |
|---|---|---|
| `scenario_id` | `E-01` | `E-02` |
| `schema_version` | `controlproof.scenario.v4` | `controlproof.scenario.v4` |
| `assertion_ids` | `E01-A1`~`E01-A4` | `E02-A1`~`E02-A3` |
| `diagnostic_ids` | `E01-D1` | 없음 |
| `evidence_ids` | EV4-01·02·03·04·05·09·10 | EV4-01·02·04·06·07·08·09·10 |
| `lanes` | `E01LaneId` 4개 | `E02LaneId` 2개 |
| `environment_kind` | `LOCAL_EMULATED` | `LOCAL_EMULATED` |
| `aws_deployment_status` | `NOT_RUN` | `NOT_RUN` |
| `requires_restore` | true | true |
| `requires_queue_policy_snapshot` | false | false |
| `allowed_model_fixtures` | `spec004-report-v1` | `spec004-report-v1` |
| `bundle_profile_contract` | `controlproof.bundle-profile.spec004.v1` | 같음 |

`Run` 검증은 Spec 003 profile policy 방식(`profile_policy(profile).validate_run(run)`)을 따른다. Spec 004 policy는
environment snapshot digest, lane manifest digest, capability digest, fixture ID·digest, `LOCAL_EMULATED`, AWS `NOT_RUN`,
미검증 범위를 요구하고 queue topology는 요구하지 않는다. E-02 policy는 `scoring_rule_source_digest`도 요구한다.

## 2. Lane enum

```text
E01LaneId: E01_REFERENCE, E01_CITATION_MATRIX, E01_EVIDENCE_REMOVAL, E01_STORAGE_PROBE
E02LaneId: E02_FIRST_APPLICANT, E02_SECOND_APPLICANT
```

## 3. ReportLane

Spec 003 `RunSubjectLane`과 같은 원칙(lane마다 독립 subject, trace namespace, seed correlation)을 따르며 보고서 입력을
기술한다.

| Field | Type | Rules |
|---|---|---|
| `lane_id` | enum | profile의 lane 중 하나 |
| `subject_ref` | string | Run 안에서 unique |
| `position_id` | UUID | E-01은 lane마다 다름, E-02는 두 lane 공유 |
| `invitation_id`, `applicant_id` | UUID | lane마다 다름 |
| `interview_session_id` | UUID | 완료 세션 fixture |
| `competency_model_version_id` | UUID | seed 시점에 묶인 버전 |
| `version_source` | enum | `RUN_SEED`(E-01), `PRODUCT_API_LATEST_PUBLISHED`(E-02) |
| `criteria` | ordered list of `LaneCriterion` | 1개 이상 |
| `fixture_rows` | map table → ID set | 세션·turn·질문 근거·자막 구간·자산 |
| `fixture_digest` | SHA-256 | fixture projection digest |
| `consent_required_purposes` | set | `ai_assessment` 포함 |
| `trace_namespace` | string | `controlproof:{run_id}:{lane_id}` |
| `seed_correlation_id` | string | teardown 연결 |

### LaneCriterion

| Field | Type | Rules |
|---|---|---|
| `criterion_id` | UUID | Run seed이면 결정론적 uuid5, 제품 API면 응답 값 |
| `code` | string | 버전 안에서 unique |
| `weight` | float | 버전 안 합 100(제품 API) |
| `citation_mode` | enum/null | E-01만: `VALID`, `EMPTY`, `NONEXISTENT`, `OTHER_APPLICANT`, `OTHER_CRITERION` |
| `mode_argument` | UUID/string/null | `NONEXISTENT`·`OTHER_APPLICANT`: 인용할 UUID, `OTHER_CRITERION`: 참조 기준 ID |
| `fixture_score` | integer/null | 판단 보류 H-2 (a)일 때 0~100 |
| `marker` | string | 기준 설명 맨 앞 표식, 계약 형식 |
| `answer_turn_id`, `question_turn_id`, `transcript_segment_id` | UUID | 이 기준에 묶인 fixture |

### Validation

- E-01 lane의 기준 표식은 그 lane의 기준에만 있다. `E01_CITATION_MATRIX`의 `OTHER_APPLICANT` 인자는 `E01_REFERENCE`
  보고서의 실제 Evidence ID여야 하며 참조 보고서가 저장되기 전에는 matrix를 seed하지 않는다.
- `OTHER_CRITERION` 인자는 같은 lane에서 버전 순서상 앞에 있는 `VALID` 기준 ID여야 한다.
- `NONEXISTENT` 인자는 `uuid5(run namespace, "e01-nonexistent")`이며 대상 DB 어디에도 없어야 한다(seed 전 확인).
- 자막 구간은 lane마다 고유하고 다른 lane·Run과 공유하지 않는다.
- E-02 두 lane은 같은 `position_id`를 가지며 `E02_SECOND_APPLICANT`는 v2 발행 뒤에만 seed한다.

## 4. ModelEmissionReceipt

WhyYou `spec004-report-v1`이 local/test observer root에 남기는 receipt의 정규화.

| Field | Type | Rules |
|---|---|---|
| `schema_version` | const | `controlproof.spec004-model-emission.v1` |
| `receipt_id` | UUID | unique |
| `fixture_id` | const | `spec004-report-v1` |
| `criterion_id` | UUID | payload의 기준 |
| `mode` | enum | 위 다섯 모드 또는 `DEFAULT` |
| `provided_evidence_ids` | ordered UUID list | payload의 `provided_answers[].evidence_id` |
| `emitted_quoted_ids` | ordered UUID list | 모델이 낸 인용(모든 축 동일) |
| `emitted_score` | integer/null | 모델이 낸 점수 |
| `mode_status` | enum | `EMITTED`, `MODE_SOURCE_MISSING`, `MARKER_INVALID` |
| `emitted_at` | aware datetime | 필수 |

질문·답변 원문, 기준 설명 본문은 저장하지 않는다.

## 5. CitationCase

E-01 matrix와 참조 lane의 기준별 사례.

| Field | Type | Rules |
|---|---|---|
| `case_id` | string | `{lane_id}:{criterion_code}` |
| `mode` | enum | 다섯 모드 |
| `intended_quoted_ids` | ordered UUID list | 실행기가 의도한 인용 |
| `emission_receipt_id` | UUID/null | 없으면 판정 INCONCLUSIVE |
| `stored_axes` | list of `StoredAxisProjection` | 저장 레코드 |
| `stored_evidence_ids` | ordered UUID set | 그 항목의 Evidence 행 |
| `invalid_id_present` | boolean | 잘못된 ID가 축 인용·Evidence 행 어디든 남았는지 |
| `outcome` | enum | `EMPTIED`, `REJECTED`, `STORED_VALID`, `STORED_INVALID`, `NOT_PRODUCED` |

### StoredAxisProjection

`axis`, `score`(int/null), `quoted_evidence_ids`, `rationale_sha256`, `rationale_is_unverified_notice`(boolean,
WhyYou 고정 사유 문구와 같은지).

## 6. ReportRecordSnapshot

DB allowlist projection. 한 보고서·한 시점.

| Field | Type | Rules |
|---|---|---|
| `run_id`, `lane_id`, `subject_ref` | identity | 필수 |
| `phase` | enum | `GENERATED`, `PRE_REMOVAL`, `POST_REMOVAL`, `POST_RESTORE`, `PRE_PROBE`, `POST_PROBE`, `PRE_CHANGE`, `POST_CHANGE` |
| `report_id`, `report_version` | UUID, int | Run이 만든 보고서 |
| `model_version`, `prompt_version`, `config_version` | string | 원문 |
| `status` | string | ready/partial/... |
| `summary_sha256` | SHA-256 | 원문 금지 |
| `overall_score` | int/null | 저장 열 |
| `scoring_inputs` | object | 원본 JSON(숫자·ID만이므로 그대로) |
| `items` | list of `ReportItemProjection` | criterion 순 |
| `evidence` | list of `EvidenceProjection` | ID·범위·소속 ID, 관찰·사유는 SHA-256 |
| `transcript_segments` | list | ID·turn·version·시작/끝·`row_digest`, 본문은 SHA-256 |
| `source_status` | enum | PRESENT/ABSENT/UNAVAILABLE |
| `state_digest` | SHA-256 | canonical projection |

`ReportItemProjection`: `report_item_id`, `criterion_id`, `competency_model_version_id`, `assessment_state`,
`criterion_weight`, `axis_weights`, `axes`(StoredAxisProjection), `observation_sha256`, `rationale_sha256`,
`uncertainty_sha256`.

## 7. ReportReadSnapshot

`GET .../report`와 `GET .../timeline` 응답의 allowlist projection.

| Field | Type | Rules |
|---|---|---|
| `phase` | enum | `ReportRecordSnapshot.phase`와 같음 |
| `request_id` | UUID | sanitized |
| `status_code` | int | 필수 |
| `report` | object/null | `overall_score`, `communication_score`, `unscored_criteria_count`, `scoring_breakdown`(숫자·ID·상태), 항목별 `average_score`·`assessment_state`·`criterion_weight`·`axis_assessments`(축·점수·인용·가중치)·`evidence`(ID·turn·segment·범위·sufficiency, 응답에 있으면 가용성 필드) |
| `timeline` | object/null | entry ID·type·범위·`technical_failure`, 본문은 SHA-256; playback URL은 저장 금지(상태만) |
| `unknown_fields` | list of string | 계약에 없는 새 응답 필드 이름(값 저장 금지) |
| `read_digest` | SHA-256 | canonical projection |

`unknown_fields`는 대상이 근거 부족 표현을 새 필드로 추가했을 때(§8 보완) 계약 밖 지표를 놓치지 않기 위한 것이다.

## 8. ChangeInjection

| Field | Type | Rules |
|---|---|---|
| `injection_id` | UUID | unique |
| `kind` | enum | `EVIDENCE_SEGMENT_REMOVAL`, `STORAGE_PROBE_WRITE`, `CRITERIA_VERSION_PUBLISH` |
| `run_id`, `lane_id`, `subject_ref` | identity | Run 소유 |
| `target_table`, `target_ids` | string, UUID set | Run 소유 행만 |
| `pre_projection_digest` | SHA-256 | 적용 전 |
| `pre_projection` | object | 복원에 쓰는 전체 컬럼 값(자막 본문은 bundle에 SHA-256만, 원문은 프로세스 메모리에만) |
| `applied_at` | aware datetime/null | |
| `apply_receipt` | object | 영향 행 수, 적용 뒤 부재·변경 확인 |
| `restore_action` | enum | `REINSERT`, `REWRITE`, `TEARDOWN` |
| `restored_at` | aware datetime/null | |
| `post_restore_digest` | SHA-256/null | `pre_projection_digest`와 같아야 함 |
| `state` | enum | `REQUESTED`, `APPLIED`, `RESTORING`, `RESTORED`, `RESTORE_FAILED` |
| `failure_code` | string/null | `RESTORE_FAILED`에 필수 |

`APPLIED`만으로 효과가 생겼다고 판정하지 않는다. `EVIDENCE_SEGMENT_REMOVAL`은 적용 뒤 행 부재 확인이, 복원 뒤 digest
일치가 있어야 한다. `CRITERIA_VERSION_PUBLISH`의 복원은 teardown이며 Run 소유 행 0건과 다른 직무 버전 digest 불변이
안전 상태다.

## 9. CriteriaVersionSnapshot

| Field | Type | Rules |
|---|---|---|
| `position_id` | UUID | Run 소유 |
| `competency_model_version_id` | UUID | |
| `version_number`, `row_version` | int | |
| `status` | enum | `draft`, `published`, `retired` |
| `published_at` | aware datetime/null | |
| `criteria` | list | `criterion_id`, `code`, `weight` |
| `axis_weights` | map | 비거나 다섯 축 모두 |
| `request_ids` | UUID set | 생성·발행 요청 |
| `snapshot_phase` | enum | `V1_PUBLISHED`, `V2_PUBLISHED` |
| `other_positions_digest` | SHA-256 | 같은 회사 다른 직무 버전 projection digest |

## 10. FrozenInputSet

첫 보고서와 두 번째 보고서의 동결 입력.

| Field | Type | Rules |
|---|---|---|
| `report_id` | UUID | |
| `competency_model_version_id` | UUID | 항목에서 |
| `model_version`, `prompt_version`, `config_version` | string | |
| `criterion_weights` | map criterion_id → float | 항목 `criterion_weight` |
| `axis_weights` | map criterion_id → map | 항목 `axis_weights` |
| `scoring_inputs_present` | boolean | 비어 있지 않음 |
| `missing_fields` | list | FR-030 |
| `matches_version_snapshot` | boolean | 가중치가 묶인 버전 스냅샷과 같음 |

## 11. RecomputeRecord

| Field | Type | Rules |
|---|---|---|
| `report_id` | UUID | |
| `rule_copy_id` | const | `controlproof.whyyou-scoring-copy.v1` |
| `rule_source` | list | `{path, blob_sha}` 두 개(scoring.py, report.py) |
| `target_source_blob_shas` | list | preflight에서 읽은 값 |
| `inputs` | object | 항목별 축 점수·가중치·`config_version` |
| `computed` | object | 기준별 score/numerator/denominator, 총점 score/numerator/denominator/contributions/exclusions, 의사소통 점수 |
| `comparisons` | list of `RecomputeComparison` | |
| `tolerance` | float | `1e-9` |

`RecomputeComparison`: `target`(`STORED_OVERALL_SCORE`, `SCORING_INPUTS`, `API_OVERALL_SCORE`, `API_SCORING_BREAKDOWN`,
`API_ITEM_AVERAGE_SCORE`), `field_path`, `expected`, `observed`, `equal`.

## 12. StorageProbeRecord (E01-D1)

| Field | Type | Rules |
|---|---|---|
| `report_item_id` | UUID | `E01_STORAGE_PROBE` lane |
| `written_axes` | list | 모드별 축(축·점수·인용) |
| `injection_id` | UUID | `STORAGE_PROBE_WRITE` |
| `read_after_write` | `ReportReadSnapshot` ref | |
| `exposure` | list | 모드별 `SHOWN_AS_WRITTEN`, `AXIS_DROPPED`, `SCORE_HIDDEN`, `READ_ERROR` |

진단 관찰이며 assertion 결과에 들어가지 않는다.

## 13. Assertion and Verdict Rules

| Assertion | Required model facts |
|---|---|
| E01-A1 | 네 잘못된 모드의 CitationCase(emission receipt 포함) + 참조 lane GENERATED/최종 ReportRecordSnapshot digest |
| E01-A2 | VALID CitationCase + Evidence 소속 ID |
| E01-A3 | EVIDENCE_SEGMENT_REMOVAL 적용 receipt + PRE_REMOVAL/POST_REMOVAL ReportReadSnapshot(report·timeline) |
| E01-A4 | 같은 injection의 RESTORED + POST_RESTORE ReportReadSnapshot·ReportRecordSnapshot |
| E02-A1 | 첫 보고서 FrozenInputSet + V1 CriteriaVersionSnapshot |
| E02-A2 | PRE_CHANGE/POST_CHANGE 첫 보고서 Record·Read + 두 번째 FrozenInputSet + V2 스냅샷 |
| E02-A3 | 두 보고서 RecomputeRecord |

Aggregation order(Spec 003과 같음):

1. 변경 주입 복구가 안전하지 않으면 Run은 `RESTORE_FAILED`, verdict는 INCONCLUSIVE.
2. 직접 위반이 관찰된 assertion은 FAIL이며 하나라도 있으면 전체 FAIL이고 다른 assertion을 숨기지 않는다.
3. 직접 FAIL이 없고 필수 source가 UNAVAILABLE이거나 전제가 깨지면 INCONCLUSIVE(`INSUFFICIENT_EVIDENCE`,
   `PRECONDITION_NOT_MET`, `FIXTURE_EMISSION_MISMATCH`).
4. 같은 사실을 서로 다른 source가 모순되게 표현하면 `EVIDENCE_CONFLICT`.
5. profile의 assertion이 모두 PASS이고 bundle이 VERIFIED일 때만 전체 PASS.

## 14. Data Retention and Redaction

포함 가능: UUID, 상태, 점수, 가중치, 숫자 산술 값, 버전 문자열, 상태 코드, SHA-256, 길이, 합성 fixture 종류·digest,
기준 표식의 모드 이름.

포함 금지: 지원자 이름·이메일, 질문·답변·자막 원문, 보고서 요약·관찰·사유·후속 질문 원문, 기준 설명 본문, cookie·
token·password·presigned URL·Idempotency-Key 원값, 전체 DB 행·로그·모델 prompt, 개인 절대 경로.
