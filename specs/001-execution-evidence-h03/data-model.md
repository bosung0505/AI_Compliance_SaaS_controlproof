# Data Model: H-03 실행·관찰·증적·판정

**Feature**: `001-execution-evidence-h03`  
**Date**: 2026-09-24

## 모델 원칙

이 모델은 ControlProof의 실행 사실을 표현한다. WhyYou의 지원자·리포트 원본 모델을 복제하지 않고 `subject_ref`, locator와 sanitized snapshot으로 연결한다. Run 생명주기와 검증 verdict는 다른 축이며, readiness는 둘보다 앞선 별도 평가다.

```text
ScenarioDefinition 1 ── * Run 1 ── * TestSubject
                              │
                              ├── * FaultCondition
                              ├── * Observation ── * EvidenceArtifact
                              ├── * AssertionResult ── * Observation/Evidence refs
                              └── 0..1 Judgement

Run 0..1 ── parent_run_id ── * Run
Run 1 ── 1 ScenarioSnapshot
Run 1 ── 1 TargetSnapshot
```

## 공통 식별자와 시간

- `run_id`, `observation_id`, `artifact_id`: UUIDv7 권장. 정렬 가능한 고유값이어야 한다.
- `scenario_id`, `assertion_id`, `evidence_requirement_id`, `step_id`: 사람이 읽을 수 있는 안정된 문자열 ID다.
- 모든 시각은 timezone-aware UTC ISO 8601로 저장한다.
- 대상 시스템의 원본 ID는 raw PII 대신 `subject_ref`와 sanitized locator에 둔다.

## Enum

### ReadinessStatus

| 값 | 의미 |
|---|---|
| `READY` | 대상, 실행, 관찰, 복구 수단이 모두 준비됨 |
| `RUNNER_NOT_READY` | 대상은 있으나 seed/fault/browser 등 실행 수단이 없음 |
| `ACCESS_BLOCKED` | 대상은 있으나 허용된 자격으로 접근 불가 |
| `NO_TEST_TARGET` | 대상 기능 자체가 없음 |

### RunState

`PENDING`, `RUNNING`, `RESTORING`, `COMPLETED`, `ABORTED`, `RESTORE_FAILED`

### Verdict

`PASS`, `FAIL`, `INCONCLUSIVE`, `NOT_RUN`

`NOT_RUN`은 scenario listing projection에만 사용할 수 있고, `run_id`가 있는 Judgement에는 저장할 수 없다.

### InconclusiveReason

`NO_TEST_TARGET`, `ACCESS_LIMITED`, `INSUFFICIENT_EVIDENCE`, `EVIDENCE_CONFLICT`

Readiness의 `RUNNER_NOT_READY`와 `ACCESS_BLOCKED`는 verdict reason이 아니다. Run을 만들지 않고 preflight 결과로만 남긴다. 실행 중 접근이 사라진 경우에만 `ACCESS_LIMITED`를 verdict reason으로 사용한다.

### Phase

`BASELINE`, `INJECTED`, `RECOVERED`

### Presence

| 값 | 의미 |
|---|---|
| `PRESENT` | 조회 성공, 값/기록 있음 |
| `ABSENT` | 조회 성공, 값/기록 없음 |
| `UNAVAILABLE` | 조회 자체 실패 또는 접근 불가 |

### AssertionStatus

`PASS`, `FAIL`, `INCONCLUSIVE`

## Entity: ScenarioDefinition

버전 관리되는 실행 의도다. 실행할 때 전체 정의를 snapshot으로 복사한다.

| 필드 | 형식 | 규칙 |
|---|---|---|
| `scenario_id` | string | `H-03` |
| `version` | string | 내용 변경 시 증가, 예: `1.0.0` |
| `title` | string | 필수 |
| `control_intent` | string | 필수 |
| `required_capabilities` | list[string] | target 중립 capability 명칭 |
| `preconditions` | list[Precondition] | 대상 존재와 runner 준비 조건을 구분 |
| `steps` | ordered list[ScenarioStep] | `step_id` 중복 금지 |
| `assertions` | list[AssertionDefinition] | H03-A1~A6 모두 존재 |
| `required_evidence` | list[EvidenceRequirement] | EV-01~EV-09 모두 존재 |
| `timing_policy` | TimingPolicy | polling/deadline/stability 고정 |
| `restore_policy` | RestorePolicy | 장애 단계가 있으면 필수 |
| `source_requirements` | list[string] | FR/AC 추적 ID |

### ScenarioStep

| 필드 | 형식 | 규칙 |
|---|---|---|
| `step_id` | string | scenario 내 유일 |
| `phase` | Phase | 필수 |
| `action` | string | adapter capability 이름 |
| `attempt_policy` | object | 최대 시도와 backoff |
| `outputs` | list[string] | 생성할 observation key |
| `evidence_requirements` | list[string] | EV ID 참조 |
| `always_run` | boolean | restore 단계는 true |

## Entity: ScenarioReadiness

Run 생성 전에 계산하는 결과다.

| 필드 | 형식 | 규칙 |
|---|---|---|
| `scenario_id` | string | 필수 |
| `scenario_version` | string | 필수 |
| `target_id` | string | 환경 식별자 |
| `status` | ReadinessStatus | 필수 |
| `checks` | list[ReadinessCheck] | capability별 결과 |
| `checked_at` | datetime | 필수 |
| `target_version` | string? | 읽을 수 있으면 필수 |
| `operator_action` | string? | READY가 아니면 해결 방법 |

`status` 집계 우선순위는 `NO_TEST_TARGET`(기능 자체 없음) → `ACCESS_BLOCKED` → `RUNNER_NOT_READY` → `READY`다. 단, fault hook만 없으면 reporting 대상은 존재하므로 반드시 `RUNNER_NOT_READY`다.

## Entity: Run

한 시나리오의 한 번 실행이다.

| 필드 | 형식 | 규칙 |
|---|---|---|
| `run_id` | UUID | 생성 후 불변 |
| `scenario_id` | string | 필수 |
| `scenario_version` | string | snapshot과 일치 |
| `scenario_digest` | sha256 | canonical snapshot hash |
| `target_id` | string | 예: `whyyou-local` |
| `target_version` | string | git SHA + dirty flag 또는 image digest |
| `state` | RunState | 전이 규칙 준수 |
| `started_at` | datetime? | RUNNING 진입 시 필수 |
| `ended_at` | datetime? | terminal state에서 필수 |
| `seed_kind` | string | `h03_pending_report_v1` |
| `fault_kind` | string | `reporting_handler_timeout_v1` |
| `parent_run_id` | UUID? | 재시험일 때 필수, 자기 자신 금지 |
| `operator_id` | string | 비식별 운영자 ref |
| `fault_ever_applied` | boolean | false→true만 허용 |
| `manual_cleanup_required` | boolean | RESTORE_FAILED면 true |
| `implementation_status` | string | `IMPLEMENTED` 등, verdict와 독립 |

### Run state transitions

```text
PENDING ──> RUNNING ──> RESTORING ──> COMPLETED
    │           │              └────> RESTORE_FAILED
    └──────────> ABORTED
                └─(fault 미적용)───> ABORTED
RESTORING ──(restore 성공, 실행 미완주)──> ABORTED
```

검증 규칙:

- `fault_ever_applied=true`이면 `RUNNING → ABORTED` 직접 전이를 금지한다.
- `COMPLETED`, `ABORTED`, `RESTORE_FAILED`은 terminal이다.
- terminal Run의 canonical 파일은 수정하지 않는다.
- `RESTORE_FAILED`는 target+subject block marker를 요구한다.

## Entity: TestSubject

| 필드 | 형식 | 규칙 |
|---|---|---|
| `subject_ref` | string | Run 내 유일, 예: `candidate-01` |
| `subject_type` | string | `synthetic_applicant` |
| `synthetic` | boolean | Spec 001에서는 반드시 true |
| `locators` | object | invitation/session/report locator; sanitized |
| `initial_state_digest` | sha256 | baseline snapshot hash |
| `seed_correlation_id` | string | teardown과 상관관계에 사용 |

## Entity: FaultCondition

| 필드 | 형식 | 규칙 |
|---|---|---|
| `fault_id` | UUID | 필수 |
| `run_id` | UUID | 필수 |
| `subject_ref` | string | 필수 |
| `fault_kind` | string | `reporting_handler_timeout_v1` |
| `target_locator` | object | session ID 등, sanitized |
| `requested_at` | datetime | 필수 |
| `applied_at` | datetime? | marker 확인 시 |
| `effect_observed_at` | datetime? | worker trigger 관찰 시 |
| `expires_at` | datetime | applied 전 필수 |
| `restored_at` | datetime? | marker 제거+확인 시 |
| `apply_success` | boolean? | 시도 전 null |
| `effect_confirmed` | boolean? | 명령 성공과 별도 |
| `restore_success` | boolean? | restore 전 null |
| `actor_ref` | string | ControlProof runner ref |

`apply_success=true`만으로 H03-A1 PASS를 만들 수 없다. `effect_confirmed=true`와 관련 evidence가 모두 필요하다.

## Entity: Observation

특정 차원에서 수집한 구조화 사실이다.

| 필드 | 형식 | 규칙 |
|---|---|---|
| `observation_id` | UUID | 필수 |
| `run_id` | UUID | 필수 |
| `subject_ref` | string | 필수 |
| `phase` | Phase | 필수 |
| `step_id` | string | scenario step에 존재 |
| `attempt` | integer | 1 이상 |
| `key` | string | 예: `report.api.status` |
| `presence` | Presence | 필수 |
| `value` | JSON value? | PRESENT일 때 필수, ABSENT/UNAVAILABLE이면 null |
| `source_type` | string | `HTTP`, `BROWSER`, `DB`, `LOG`, `FAULT`, `SYSTEM` |
| `source_ref` | string | sanitized locator |
| `observed_at` | datetime | 필수 |
| `artifact_ids` | list[UUID] | 0개 이상; assertion 입력은 필요한 artifact를 별도 요구 |
| `error_code` | string? | UNAVAILABLE이면 필수 |

### Observation identity and conflict

논리 식별 차원:

```text
run_id + subject_ref + phase + step_id + attempt + key
```

다른 phase/step/attempt의 값 변화는 충돌이 아니다. 같은 차원에서 독립 source가 같은 사실을 표현해야 하는데 정규화 값이 다를 때만 conflict candidate다. `ABSENT`와 `PRESENT`의 모순도 conflict다. `UNAVAILABLE`은 충돌 값이 아니라 증적 공백이다.

## Entity: EvidenceArtifact

| 필드 | 형식 | 규칙 |
|---|---|---|
| `artifact_id` | UUID | 필수 |
| `run_id` | UUID | 필수 |
| `subject_ref` | string | 필수 |
| `phase` | Phase | 필수 |
| `step_id` | string | 필수 |
| `attempt` | integer | 1 이상 |
| `evidence_requirement_ids` | list[string] | EV-01~EV-09 중 1개 이상 |
| `artifact_type` | string | `HTTP_EXCHANGE`, `SCREENSHOT`, `STATE_SNAPSHOT`, `LOG_EXTRACT`, `FAULT_RECEIPT`, `VERSION_SNAPSHOT` |
| `relative_path` | string | Run 디렉터리 내부만 허용 |
| `source_locator` | object | sanitized |
| `captured_at` | datetime | 필수 |
| `mime_type` | string | 필수 |
| `size_bytes` | integer | 0 이상 |
| `sha256` | string | 64 lowercase hex |
| `redaction_profile` | string | 적용한 profile version |
| `integrity_status` | string | `VERIFIED`, `MISMATCH`, `MISSING` |

검증 규칙:

- relative path traversal 금지.
- hash는 redacted 저장 bytes에 대해 계산한다.
- 필수 evidence가 `VERIFIED`가 아니면 해당 assertion은 PASS할 수 없다.
- locator만 저장한 경우에도 판정 입력 정규화 추출물을 artifact로 저장한다.

## Entity: AssertionDefinition

| 필드 | 형식 | 규칙 |
|---|---|---|
| `assertion_id` | string | H03-A1~A6 |
| `description` | string | 필수 |
| `expectation` | declarative rule | engine이 지원하는 규칙 조합 |
| `fail_condition` | declarative rule? | A1/A6에는 직접 FAIL 없음 |
| `required_observation_keys` | list[string] | 필수 |
| `required_evidence_ids` | list[string] | 필수 |
| `source_requirements` | list[string] | FR/AC IDs |

## Entity: AssertionResult

| 필드 | 형식 | 규칙 |
|---|---|---|
| `assertion_id` | string | 정의에 존재 |
| `subject_ref` | string | 필수 |
| `status` | AssertionStatus | 필수 |
| `expected` | JSON/text | snapshot |
| `actual` | JSON/text | 정규화된 실제 값 |
| `observation_ids` | list[UUID] | 판정 입력 |
| `artifact_ids` | list[UUID] | 판정 근거 |
| `reason_code` | InconclusiveReason? | INCONCLUSIVE이면 필수 |
| `detail` | string | 비개발자도 이해 가능한 설명 |
| `source_requirements` | list[string] | 역추적 가능 |

## Entity: Judgement

| 필드 | 형식 | 규칙 |
|---|---|---|
| `run_id` | UUID | 필수 |
| `scenario_id` | string | 필수 |
| `verdict` | `PASS|FAIL|INCONCLUSIVE` | 생성된 Run에서 NOT_RUN 금지 |
| `reason_code` | InconclusiveReason? | INCONCLUSIVE이면 필수 |
| `assertion_results` | list[AssertionResult] | H03-A1~A6 정확히 1개씩 |
| `findings` | list[Finding] | 직접 관찰 위험을 보존 |
| `missing_evidence` | list[string] | 없으면 빈 목록 |
| `unverified_scope` | list[string] | DLQ 등 명시 |
| `summary` | string | 한 문장 핵심 설명 |
| `decided_at` | datetime | terminal 전 저장 가능하나 seal 때 확정 |
| `engine_version` | string | 필수 |

### 전체 verdict 계산

1. Run이 `ABORTED` 또는 `RESTORE_FAILED` → `INCONCLUSIVE`; 앞서 발견한 FAIL finding은 유지.
2. H03-A1 또는 A6가 INCONCLUSIVE → 전체 `INCONCLUSIVE`; 보호조치 finding은 유지.
3. 정상 완료이며 A2~A5 중 FAIL 존재 → `FAIL`.
4. FAIL이 없고 assertion INCONCLUSIVE 또는 필수 evidence 공백/불일치 존재 → `INCONCLUSIVE`.
5. 6개 assertion PASS, 9종 evidence VERIFIED, Run `COMPLETED` → `PASS`.

## Entity: RetestLink

물리적으로는 child Run의 필드와 별도 diff 산출물로 표현한다.

| 필드 | 형식 | 규칙 |
|---|---|---|
| `parent_run_id` | UUID | terminal Run이어야 함 |
| `child_run_id` | UUID | parent와 다름 |
| `changed_dimensions` | object | target/scenario/config 차이 |
| `reason` | string | 재시험 사유 |
| `created_at` | datetime | 필수 |

부모 bundle은 읽기 전용으로 연다. 자식 Run은 독립 Observation/Evidence/Judgement를 가지며 부모 파일을 hard link로 공유하지 않는다.

## H-03 상태 snapshot

H03-A4/A5 비교에 사용하는 최소 상태는 다음 allowlist다.

```json
{
  "invitation_status": "completed",
  "recruiting_stage_id": "uuid-or-null",
  "pipeline_row_version": 1,
  "final_decision_count": 0,
  "latest_final_decision_actor_type": null,
  "report_presence": "ABSENT",
  "report_status": null
}
```

전체 invitation/report/human_review row를 덤프하지 않는다. 비교는 각 필드와 count에 대해 수행하고 snapshot 자체를 EV-01/EV-06/EV-07/EV-08 artifact로 저장한다.

## Bundle seal rules

Run 종료 시 다음 순서로 봉인한다.

1. 미완료 JSONL record를 flush·fsync한다.
2. 모든 artifact를 다시 hash하고 integrity status를 갱신한다.
3. assertion과 judgement를 계산한다.
4. `run.json`, `judgement.json`, `manifest.json`을 atomic write한다.
5. `manifest.json`의 `sealed_at`과 `bundle_digest`를 기록한다.
6. 이후 변경 시 verify가 mismatch를 반환한다. 원본을 고치지 않고 새 Run을 만든다.
