# Contract: E-01·E-02 Scenario Profile v4

## Identity

| Field | E-01 | E-02 |
|---|---|---|
| `schema_version` | `controlproof.scenario.v4` | `controlproof.scenario.v4` |
| `scenario_id` | `E-01` | `E-02` |
| `version` | `1.0.0` | `1.0.0` |
| `execution_profile` | `E01_CITATION_EVIDENCE_V1` | `E02_SCORING_FREEZE_V1` |
| `bundle_profile_contract` | `controlproof.bundle-profile.spec004.v1` | 같음 |
| 파일 | `scenarios/E-01.yaml` | `scenarios/E-02.yaml` |

v4는 이 두 profile에만 쓴다. v1·v2·v3 검증 규칙은 바꾸지 않는다.

## Canonical assertions·diagnostics

```text
E-01: E01-A1, E01-A2, E01-A3, E01-A4      diagnostics: E01-D1
E-02: E02-A1, E02-A2, E02-A3
```

## Canonical evidence

```text
EV4-01 scenario/target/environment/fixture/capability (+ E-02 scoring rule source) snapshot
EV4-02 lanes, subjects, criteria markers, fixture descriptor
EV4-03 citation cases and model emission receipts            (E-01)
EV4-04 report records before/after                           (both)
EV4-05 report and timeline reads x3                          (E-01)
EV4-06 criteria version snapshots before/after               (E-02)
EV4-07 frozen input sets of both reports                     (E-02)
EV4-08 recompute rule copy, inputs, results                  (E-02)
EV4-09 change injections, restore, safe state                (both)
EV4-10 judgement and sealed manifest                         (both)
```

E-01 적용: EV4-01·02·03·04·05·09·10. E-02 적용: EV4-01·02·04·06·07·08·09·10. 적용 집합 밖의 EV4를 YAML에 두면 무효다.

## Canonical lanes

| Profile | Lane | 용도 |
|---|---|---|
| E-01 | `E01_REFERENCE` | 타 지원자 Evidence ID 공급, A1 참조 불변 |
| E-01 | `E01_CITATION_MATRIX` | 다섯 인용 모드, A1·A2 |
| E-01 | `E01_EVIDENCE_REMOVAL` | 근거 제거·복원, A3·A4 |
| E-01 | `E01_STORAGE_PROBE` | 저장소 직접 쓰기 진단, D1 |
| E-02 | `E02_FIRST_APPLICANT` | v1 보고서, A1·A2·A3 |
| E-02 | `E02_SECOND_APPLICANT` | v2 보고서, A2 전제·A3 |

## Required capabilities

공통:

```yaml
target.version.read: v1
target.environment.read: v1
model.fixture.read: v1
spec004.lanes.seed: v1
spec004.lanes.teardown: v1
consent.policy.read: v1
consent.commit.write: v1
consent.state.read: v1
report.generation.request: v1
report.processing.receipts.read: v1
report.records.read: v1
report.api.read: v1
```

E-01 추가:

```yaml
model.emission.read: v1
timeline.api.read: v1
evidence.segment.remove: v1
evidence.segment.restore: v1
report.axes.probe_write: v1
report.axes.probe_restore: v1
```

E-02 추가:

```yaml
criteria.version.create: v1
criteria.version.publish: v1
criteria.version.read: v1
scoring.rule.source.read: v1
```

대상 경계가 있으나 adapter·fixture·observer가 실행·관찰하지 못하면 `RUNNER_NOT_READY`, 접근이 막히면 `ACCESS_BLOCKED`.
점수 저장 HTTP 경로가 없다는 사실은 `NO_TEST_TARGET`이 아니다(작업자 경계가 실제로 있다).

## Step contract — E-01

```text
capture-environment
capture-capabilities
seed-report-lanes                 # REFERENCE, EVIDENCE_REMOVAL, STORAGE_PROBE
commit-lane-consents
request-lane-reports
capture-reference-report
seed-citation-matrix              # 참조 보고서 Evidence ID를 표식에 넣음
commit-matrix-consent
request-matrix-report
capture-citation-cases
capture-removal-baseline
apply-evidence-removal
capture-post-removal
restore-evidence-removal          always_run
verify-removal-restored           always_run
capture-post-restore
capture-probe-baseline
apply-storage-probe
capture-storage-probe-reads
restore-storage-probe             always_run
verify-storage-probe-restored     always_run
recapture-reference-report
teardown-report-lanes             always_run
```

## Step contract — E-02

```text
capture-environment
capture-capabilities
capture-scoring-rule-source
seed-e02-position
create-publish-v1
seed-first-applicant              # 최신 발행 버전(v1)에 묶음
commit-first-consent
request-first-report
capture-pre-change
recompute-first-report
create-publish-v2                 # 변경 주입 CRITERIA_VERSION_PUBLISH
capture-version-change
seed-second-applicant             # 최신 발행 버전(v2)에 묶음
commit-second-consent
request-second-report
capture-second-report
capture-post-change
recompute-second-report
compare-first-report
teardown-e02-position             always_run
verify-other-positions-unchanged  always_run
```

restore·teardown 단계는 예외, timeout, Ctrl+C 뒤에도 호출한다. 변경 주입이 한 번이라도 `APPLIED`면 복구 단계를 건너뛸 수
없다. always_run 단계는 `RECOVERED` phase여야 한다(기존 규칙).

## Timing policy

```yaml
poll_seconds: 2
stability_consecutive: 3
stability_seconds: 4
environment_restore_deadline_seconds: 120
run_deadline_seconds: 540
bundle_verify_deadline_seconds: 60
expected_queue: {}
```

`fault_ttl_seconds`는 두지 않는다. 보고서 대기는 Run 예산 안의 안정화 읽기로 한다. 값 변경은 scenario version 증가와
snapshot digest 변경을 요구한다.

## Assertion rules

### E01-A1 — 잘못된 인용은 작업자 검증·저장에서 비워진다

네 모드(`EMPTY`, `NONEXISTENT`, `OTHER_APPLICANT`, `OTHER_CRITERION`) 각각:

- PASS 조건(모두): emission receipt `mode_status=EMITTED`이고 `emitted_quoted_ids`가 의도와 같다(`EMPTY`는 빈 목록과 점수
  있음); 저장 축 전부 `score=null`·`quoted_evidence_ids=[]`·비어 있지 않은 `rationale`; 잘못된 ID가 **그 기준 항목**의 축
  인용과 그 항목의 `evidence` 행에 없다(`OTHER_CRITERION` ID가 같은 보고서의 VALID 항목에, `OTHER_APPLICANT` ID가 참조
  보고서에 원래 있는 것은 위반이 아니다);
  참조 lane 보고서 projection digest가 GENERATED와 최종 재수집에서 같다.
- FAIL: 저장 축에 점수가 남거나 잘못된 ID가 그 항목의 축 인용·Evidence 행에 남음, 또는 참조 lane 기록이 바뀜.
- INCONCLUSIVE: receipt 없음(`INSUFFICIENT_EVIDENCE`), receipt가 의도와 다름(`FIXTURE_EMISSION_MISMATCH`),
  `MODE_SOURCE_MISSING`, 보고서 미생성(`PRECONDITION_NOT_MET`).
- 사유 보존의 PASS 조건은 `rationale`이 비어 있지 않은 것이다. WhyYou 고정 보류 문구와 같은지
  (`rationale_is_unverified_notice`)는 기록만 하고 PASS 조건에 넣지 않는다(대상 문구 변경에 판정이 흔들리지 않게).

### E01-A2 — 유효 인용은 정상 저장된다

- PASS: `VALID` 축이 정수 점수와 비어 있지 않은 인용을 가지고, 모든 인용 ID가 같은 항목의 `evidence` 행이며, 그 행의
  `criterion_id`·`competency_model_version_id`가 항목과 같다.
- FAIL: 점수가 비워지거나 인용이 다른 항목·보고서의 행을 가리킴.
- INCONCLUSIVE: receipt·보고서 부재.

### E01-A3 — 근거 제거 뒤 점수는 근거 부족으로 노출된다

전제: `EVIDENCE_SEGMENT_REMOVAL` 적용 receipt가 행 부재를 확인하고, PRE_REMOVAL 보고서 조회가 200. POST_REMOVAL 조회의
5xx는 전제 실패가 아니라 아래 FAIL 사유다. 타임라인 차이는 보조 증거다.

허용 지표(H-4 (a), 2026-10-07 보성 승인으로 고정) — 제거된 자막 구간을 가리키는 Evidence를 인용한 각 축·항목에 대해
POST_REMOVAL 응답이 다음 중 하나를 보이면 근거 부족 노출로 본다. 네 표현 모두 PASS 지표다.

1. 그 축의 `score`가 `null`
2. 그 항목의 `average_score`가 `null`
3. 그 항목의 `assessment_state`가 `insufficient_evidence` 또는 `needs_follow_up`
4. 그 Evidence 항목에 `playable`, `available`, `transcript_available` 중 하나가 있고 `false`

- PASS: 영향 받은 모든 축·항목이 지표를 보이고, 영향 받지 않은 항목의 projection이 PRE_REMOVAL과 같다.
- FAIL: 영향 받은 축·항목이 지표 없이 PRE_REMOVAL과 같은 점수·인용을 보임(P1 예측), 또는 영향 받지 않은 항목이 바뀜, 또는
  POST_REMOVAL 조회가 5xx(`REPORT_UNREADABLE_AFTER_REMOVAL`).
- INCONCLUSIVE: 제거 미확인, PRE 조회 실패, 응답에 계약 밖 새 필드(`unknown_fields`)가 생겨 지표 판단이 모호
  (`EVIDENCE_CONFLICT`가 아니라 `INSUFFICIENT_EVIDENCE`로 두고 scenario 개정을 요구).

### E01-A4 — 근거 복원 뒤 조회가 원상 복구된다

- PASS: 복원 행 digest가 제거 전과 같고, POST_RESTORE 보고서 projection과 레코드 projection이 PRE_REMOVAL과 같다.
- FAIL: 복원은 안전(digest 일치)한데 조회가 다름.
- 복원 실패·미확인은 assertion이 아니라 Run `RESTORE_FAILED`(verdict INCONCLUSIVE)와 차단이다.

### E01-D1 — 저장소 직접 쓰기 노출 (진단)

모드별 `exposure`를 기록한다. verdict·exit code에 영향이 없다. 복원 실패는 다른 변경 주입과 같이 `RESTORE_FAILED`다.

### E02-A1 — 리포트가 동결 입력 집합을 자체 보존한다

- PASS: 첫 보고서에 `competency_model_version_id`(v1), `model_version`·`prompt_version`·`config_version`, 비어 있지 않은
  `scoring_inputs`, 모든 항목의 `criterion_weight`가 있고 항목 가중치·축 가중치가 V1 스냅샷과 같다.
- FAIL: 필드 누락이나 가중치 불일치(`missing_fields`).

### E02-A2 — 새 버전 발행 뒤 과거 리포트가 변하지 않는다

- 전제: V2 스냅샷이 `published`이고 두 번째 보고서의 버전 ID·항목 가중치·축 가중치가 V2와 같다. 깨지면 INCONCLUSIVE
  (`PRECONDITION_NOT_MET`).
- PASS: 첫 보고서의 PRE_CHANGE·POST_CHANGE 레코드 projection과 조회 projection이 각각 같다.
- FAIL: 어느 하나라도 다름.

### E02-A3 — 저장 입력으로 재계산한 총점이 저장값·조회값과 같다

두 보고서 각각, 비교 대상 다섯 개(`STORED_OVERALL_SCORE`, `SCORING_INPUTS`의 numerator·denominator·criteria[],
`API_OVERALL_SCORE`, `API_SCORING_BREAKDOWN`, `API_ITEM_AVERAGE_SCORE`)가 모두 `equal=true`면 PASS. 정수는 정확히,
실수는 절대 오차 `1e-9`. 하나라도 다르면 FAIL. 재계산 원본 blob SHA가 사본 기준과 다르면 Run 전에 `RUNNER_NOT_READY`.

## Verdict precedence

```text
RESTORE_FAILED → INCONCLUSIVE
direct violation → FAIL
same-fact source contradiction → INCONCLUSIVE:EVIDENCE_CONFLICT
required evidence unavailable / precondition not met → INCONCLUSIVE
all profile assertions PASS + bundle VERIFIED → PASS
```

## Scenario YAML 초안 — E-01

```yaml
schema_version: controlproof.scenario.v4
scenario_id: E-01
version: 1.0.0
execution_profile: E01_CITATION_EVIDENCE_V1
bundle_profile_contract: controlproof.bundle-profile.spec004.v1
applicable_assertion_ids: [E01-A1, E01-A2, E01-A3, E01-A4]
diagnostic_ids: [E01-D1]
lanes: [E01_REFERENCE, E01_CITATION_MATRIX, E01_EVIDENCE_REMOVAL, E01_STORAGE_PROBE]
title: 근거 인용 없는 점수 저장·노출 차단
control_intent: >-
  잘못된 인용을 담은 모델 출력이 보고서 작업자의 검증을 거쳐 점수로 저장되지 않고, 저장된 점수의 근거가
  사라지면 회사 보고서 조회가 그 점수를 근거 부족으로 드러내며, 근거가 복원되면 원래대로 돌아오는지 검증한다.
required_capabilities: {}        # 위 공통 + E-01 추가 집합과 정확히 같아야 함
preconditions:
  - {precondition_id: source-clean, kind: target, description: 두 checkout clean·비 main}
  - {precondition_id: fixture-spec004, kind: model, description: 고정 모델 spec004-report-v1 활성}
  - {precondition_id: external-ai-blocked, kind: environment, description: 외부 AI 차단 digest 일치}
steps: []                        # 위 Step contract 순서와 정확히 같아야 함
assertions: []                   # E01-A1~A4, required_evidence_ids는 아래 표
required_evidence: []            # EV4-01·02·03·04·05·09·10
timing_policy:
  poll_seconds: 2
  stability_consecutive: 3
  stability_seconds: 4
  environment_restore_deadline_seconds: 120
  run_deadline_seconds: 540
  bundle_verify_deadline_seconds: 60
  expected_queue: {}
restore_policy:
  mandatory: true
  action: restore-change-injections-and-teardown
  report_processing_result_field: change_injection_restore_status
observation_comparators: {}
source_requirements: [FR-010, FR-011, FR-012, FR-013, FR-020, FR-021, FR-022, FR-041]
allowed_model_fixtures:
  spec004-report-v1: "<sha256 of controlproof:spec004-report-v1>"
excluded_scope: [AWS, N-01, N-03, product-deletion-request, transcript-correction]
```

| Assertion | required_evidence_ids |
|---|---|
| E01-A1 | EV4-02, EV4-03, EV4-04 |
| E01-A2 | EV4-02, EV4-03, EV4-04 |
| E01-A3 | EV4-04, EV4-05, EV4-09 |
| E01-A4 | EV4-04, EV4-05, EV4-09 |

## Scenario YAML 초안 — E-02

```yaml
schema_version: controlproof.scenario.v4
scenario_id: E-02
version: 1.0.0
execution_profile: E02_SCORING_FREEZE_V1
bundle_profile_contract: controlproof.bundle-profile.spec004.v1
applicable_assertion_ids: [E02-A1, E02-A2, E02-A3]
lanes: [E02_FIRST_APPLICANT, E02_SECOND_APPLICANT]
title: 평가 입력·기준 동결과 과거 리포트 보존
control_intent: >-
  보고서가 생성 당시의 점수 입력·가중치·버전을 스스로 보존해, 새 평가 기준 버전을 발행하고 다른 지원자를
  처리한 뒤에도 과거 보고서가 바뀌지 않고 저장된 입력만으로 총점을 다시 계산할 수 있는지 검증한다.
required_capabilities: {}        # 공통 + E-02 추가 집합
preconditions:
  - {precondition_id: source-clean, kind: target, description: 두 checkout clean·비 main}
  - {precondition_id: fixture-spec004, kind: model, description: 고정 모델 spec004-report-v1 활성}
  - {precondition_id: scoring-source-pinned, kind: target, description: scoring.py·report.py blob이 사본 기준과 같음}
steps: []                        # 위 Step contract 순서
assertions: []                   # E02-A1~A3
required_evidence: []            # EV4-01·02·04·06·07·08·09·10
timing_policy: {}                # E-01과 같은 값
restore_policy:
  mandatory: true
  action: teardown-run-owned-position
  report_processing_result_field: change_injection_restore_status
observation_comparators: {}
source_requirements: [FR-030, FR-031, FR-032, FR-033, FR-034, FR-041]
allowed_model_fixtures:
  spec004-report-v1: "<sha256 of controlproof:spec004-report-v1>"
excluded_scope: [AWS, N-01, N-03, published-version-direct-update, human-review-score-change]
```

| Assertion | required_evidence_ids |
|---|---|
| E02-A1 | EV4-04, EV4-06, EV4-07 |
| E02-A2 | EV4-04, EV4-06, EV4-07, EV4-09 |
| E02-A3 | EV4-04, EV4-08 |

## Validation rules

- assertion·diagnostic·evidence·lane·capability·step 집합은 profile canonical과 정확히 같다.
- always_run 집합은 위 표시와 정확히 같다.
- `allowed_model_fixtures`는 `spec004-report-v1` 하나이며 digest는 64자리 소문자 hex다.
- E-02 YAML은 `scoring-source-pinned` 전제를 가져야 한다.
- N-01 viewport, N-03 policy invalidation, 제품 삭제 요청, 발행 버전 직접 수정 단계는 포함할 수 없다.
