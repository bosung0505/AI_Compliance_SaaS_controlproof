# Implementation Plan: N-02 동의·AI 처리 순서 검증

**Branch**: `003-n02-consent-order`
**Date**: 2026-10-01
**Spec**: [spec.md](./spec.md)
**Status**: Implemented; actual parent/child validation recorded; PR review fixes implemented (ID-003-19), final converge pending. Actual verdict remains INCONCLUSIVE.

## Summary

Spec 003은 WhyYou의 유효한 동의가 서버 transaction에 확정되기 전에 자료 분석, 녹화 또는 AI 평가가
시작되는지를 실제 로컬 경계에서 검증한다. ControlProof에는 `N02_CONSENT_ORDER_V1` 실행 profile,
독립 subject lane, 동의·처리 effect projection, 인과 사건 그래프, 동의 저장 실패 주입과 N02-A1~A7
판정기를 추가한다. WhyYou에는 local/test 전용 합성 seed, 동의 transaction의 저장 후·상태 전이 전
fault hook, 최소 processing-start receipt를 추가한다.

구현의 첫 목표는 WhyYou를 미리 PASS 상태로 만드는 것이 아니다. 관찰용 hook과 probe를 먼저 추가한
뒤 현재 보호조치를 actual Run으로 시험하고, 직접 위반이 있으면 FAIL bundle을 봉인한다. 제품 보호조치
수정은 그 이후에만 WhyYou 개인 브랜치에서 수행하며 child Run으로 재검증한다.

## Technical Context

**Language/Version**: ControlProof와 WhyYou 모두 Python 3.12 이상
**Primary Dependencies**: Pydantic 2, PyYAML, HTTPX, SQLAlchemy 2, psycopg 3, boto3,
pytest; WhyYou는 FastAPI와 LocalStack 기반 local worker를 추가 사용
**Storage**: WhyYou local PostgreSQL·LocalStack S3/SQS, ControlProof 불변 file bundle
**Testing**: pytest 단위·계약·통합시험, Ruff; 구현 후 local actual-stack Run과 bundle verify
**Target Platform**: Windows Docker Desktop 또는 동등한 Docker 환경의 `LOCAL_EMULATED`; 실제 AWS는
`NOT_RUN`
**Project Type**: ControlProof CLI/검증 엔진 + 외부 WhyYou modular monolith/worker adapter
**Performance Goals**: preflight 이후 N-02 한 Run과 bundle verify를 10분 이내 완료
**Constraints**: 합성 데이터만 사용, 외부 AI 호출 금지, WhyYou `main` 변경 금지, 최초 실제 FAIL 보존,
모든 fault는 local/test·Run·subject allowlist와 10분 이하 TTL 적용
**Scale/Scope**: 실행 profile 1개, assertion 7개, Evidence ID 10개, pristine/자료/녹화/평가/정상/장애·복구
lane 6개, WhyYou source version 1개
**User Interface**: CLI·JSON·bundle만 포함; PC/모바일 시각 고지는 N-01, 고객 웹 UX는 Spec 005
**Target Baseline**: WhyYou `bosung/controlproof-h03-integration` commit
`511ae9e2cae66b8d0ce31e8851537ed27ac6dd0c`

## Constitution Check

### Pre-design gate

| 원칙 | 확인 | 결과 |
|---|---|---|
| I. 판정은 증적에서만 | N02-A1~A7마다 EV3와 raw observation을 요구하고 누락은 INCONCLUSIVE | PASS |
| II. 대상·준비·결과 분리 | capability 부재, runner 미준비, 접근 차단과 실제 verdict를 분리 | PASS |
| III. 사람의 최종 결정 | 채용 결정 기능·점수 임계값을 추가하지 않음 | PASS |
| IV. 시나리오/adapter 분리 | N-02 의미는 YAML, WhyYou 접점은 adapter와 capability map에 둠 | PASS |
| V. 격리·결정론·복구 | 합성 lane, 고정 모델, test-only fault, always-run restore 사용 | PASS |
| VI. 불변 Run·재시험 | 최초 결과 봉인 후 새 child Run만 생성 | PASS |
| VII. 명세→증적 추적 | FR·N02-A·EV3를 Plan·계약·향후 Task에 연결 | PASS |

### Post-design re-check

설계 뒤에도 위반은 없다. 심층 probe fixture는 실제 사용자 데이터나 운영 진입점을 만들지 않으며,
capability에 고정된 합성 전제조건과 probe 뒤 증분 효과를 분리한다. 이 보정은 경계가 앞 단계 산출물을
요구해도 실제 authorization을 독립 시험하기 위한 것이며 pristine 기준선 N02-A1을 대체하지 않는다.

## Source-derived Boundary Map

| 처리 종류 | 실제 요청 경계 | 실제 시작/결과 경계 | 현재 동의 확인 | Plan의 시험 방식 |
|---|---|---|---|---|
| 자료 분석 | `POST /v1/applicant/submissions/upload-intents` 및 submission 등록 | `submission.analysis_requested` → `AnalysisRequestedEventHandler` → analysis/strategy rows | upload intent 전에 `CompanySubmissionAuthorization`이 state와 `document_analysis` 동의를 확인; worker는 직접 재검사하지 않음 | pristine 자료 lane에서 API를 직접 호출하고, 별도 event capability는 등록·관찰하되 임의의 가짜 endpoint를 만들지 않음 |
| 녹화 | `POST /v1/applicant/interview-sessions`, WebSocket start, media upload-intent/confirm | interview session state와 recording chunk/asset | `SubmissionInterviewBoundary.authorize_start`는 strategy와 applicant scope를 확인하지만 현재 active `recording` 동의를 직접 확인하지 않음 | allowlisted strategy/equipment fixture가 있는 심층 probe lane에서 실제 session 생성 API를 호출하고 증분 session/recording effect를 판정 |
| AI 평가 | 실제 독립 applicant 평가 API 없음 | `report.generation_requested` → `ReportRequestedEventHandler` → report/items/projection | handler는 현재 `ai_assessment` 동의를 직접 확인하지 않음 | 독립 direct route 부재를 capability로 고정하고 완료 면접 입력 fixture가 있는 심층 probe lane에서 실제 worker event를 호출해 증분 report effect를 판정 |
| 동의 | `GET/POST /v1/applicant/consents` | consent row + invitation `consented` + `invitation.consent_completed` Outbox가 한 HTTP transaction에서 확정 | 정책 version/digest/필수 목적을 검사 | 응답 수신 뒤 독립 DB projection을 읽고 다음 처리 요청은 그 뒤에만 보냄 |

AI 평가의 worker event는 운영 코드가 실제 사용하는 비동기 계약이다. ControlProof가 전용 평가 API를
새로 만들지는 않는다. 심층 probe가 요구하는 완료 면접 fixture는 평가 lane 안에서만 사용하고 해당
fixture의 기존 recording effect를 N02-A4의 신규 결과로 세지 않는다.

## Execution Design

### 1. Profile과 scenario

- 새 profile: `N02_CONSENT_ORDER_V1`
- 새 scenario: `scenarios/N-02.yaml`
- schema: `controlproof.scenario.v3`
- assertion: `N02-A1`~`N02-A7`
- evidence: `EV3-01`~`EV3-10`
- Run deadline: 540초, bundle verify deadline: 60초. 두 값을 scenario snapshot에 함께 고정해
  Run+verify 전체 600초 목표를 지킨다.
- 일반 polling: 2초, 연속 3회 안정화·최소 4초
- fault TTL: 최대 600초, restore deadline 120초

현재 코드의 “H03 minimal이 아닌 모든 profile은 Spec 002 queue profile” 가정은 profile별 정책 registry로
분리한다. N-02는 reporting DLQ 재시도 횟수를 판정하지 않으므로 Spec 002의 canonical queue timing이나
exact unverified scope를 억지로 상속하지 않는다. 공통 environment snapshot과 `LOCAL_EMULATED`/AWS
`NOT_RUN` 주장은 계속 상속한다.

### 2. Subject lane

| Lane | 기준선 종류 | 허용 fixture | 실행 | 주요 assertion |
|---|---|---|---|---|
| `pristine-baseline` | PRISTINE | 본인 확인 완료까지만 | consent/effect 0건 확인 | A1 |
| `document-bypass` | PRISTINE | 없음 | 미동의 upload-intent 직접 호출 | A2 |
| `recording-boundary-probe` | PREREQUISITE_FIXTURE | 장비 점검·strategy만, session/recording 없음 | 실제 create-session 호출 | A3 |
| `assessment-boundary-probe` | PREREQUISITE_FIXTURE | 완료 면접·final video, report/request 없음 | 실제 report event 투입 | A4 |
| `normal-order` | PRISTINE → CONSENTED | 없음 | 정책 조회·동의 확정 뒤 정상 자료→면접→평가 한 바퀴 | A5 |
| `consent-fault-recovery` | PRISTINE → FAULTED → RECOVERED | 기준선은 없음; rollback 확인 뒤 심층 경계용 임시 overlay를 적용·제거 | 동의 저장 중 실패, 세 경로 차단 확인, restore, 같은 subject 정상 재시도 | A6·A7 |

각 lane은 다른 `subject_ref`, invitation과 trace namespace를 가진다. deep probe fixture는
`fixture_kind`, `fixture_digest`, `allowed_preexisting_effects`를 EV3-01/03에 기록한다. judge는 baseline
전체 건수가 아니라 allowlist된 fixture를 뺀 증분 효과를 사용한다. fixture가 allowlist 밖 효과를 갖거나
digest가 다르면 Run 전제 실패로 종료한다.

### 3. 실행 순서

1. 두 checkout, local endpoint, DB, LocalStack, worker, fixed model, fault/observer hook을 preflight한다.
2. policy와 protected path capability snapshot을 고정한다.
3. 6개 subject lane을 한 transaction 단위로 seed하고 각각 불변 seed digest를 만든다. 한 lane이라도
   생성에 실패하면 transaction 전체를 rollback하고 남은 subject·fixture가 0건임을 확인한다.
4. pristine baseline을 확인한다. 불일치면 우회나 fault를 실행하지 않고 ABORTED/INCONCLUSIVE로 끝낸다.
5. document, recording, assessment 우회 lane을 순서대로 호출하고 호출 직후 및 안정화 뒤 effect를 읽는다.
6. normal lane은 서버 policy를 조회하고 동의 성공 응답 뒤 독립 DB commit projection을 확인한 후 실제
   자료·면접·평가 흐름을 실행한다.
7. fault lane에 marker를 적용하고 consent API를 호출한다. trigger receipt와 HTTP 5xx를 확인한 뒤
   consent/state/outbox/processing effect가 0건인지 읽는다.
8. `finally` 성격의 restore에서 marker와 consumed token을 제거하고 hook 비활성·DB 안전 상태를 확인한다.
9. 아직 미동의인 같은 fault subject로 자료 경계를 시도한다. 녹화와 평가는 각 deep probe 전제조건만
   가진 임시 overlay를 순서대로 적용해 실제 경계를 시도하고, effect delta를 읽은 뒤 overlay를 제거한다.
10. overlay가 모두 제거된 pristine 안전 상태를 다시 확인한 뒤 같은 subject로 정상 동의를 재시도하고
    동의 효과 한 세트와 정상 처리 순서를 확인한다.
11. A1~A7을 독립 판정하고 bundle을 봉인·verify한다.

직접 위반 하나가 확인되면 전체 verdict는 FAIL이지만 나머지 안전한 lane은 계속 실행해 범위를 보여준다.
다만 baseline 손상, environment guard 실패 또는 restore 실패 뒤에는 위험한 후속 단계를 중단한다.

## Consent Completion and Causality

동의 완료 기준은 UI 클릭이나 Outbox 전달이 아니라 다음 transaction 효과의 동시 확정이다.

```text
consent_record 저장
→ invitation identity_verified → consented 전이
→ invitation_state_change 저장
→ invitation.consent_completed outbox 저장
→ HTTP middleware commit
→ client가 201 응답 수신
→ 이후 processing 요청 전송
```

WhyYou middleware가 commit 뒤에 response를 반환하므로 `consent_response_received`는 commit의 외부
관찰 가능한 상한이다. ControlProof는 201 응답 직후 별도 DB connection으로 네 효과를 읽어 commit을
확인하고, 그 확인 뒤에만 processing 요청을 보낸다. 따라서 정상 순서는 wall-clock timestamp 하나가
아니라 다음 causal edge로 증명한다.

- 같은 consent request의 trace/request ID와 consent row/state/outbox identity
- HTTP response 수신보다 뒤에 생성된 processing command receipt
- domain Outbox의 event identity·aggregate version·trace ID
- worker handler-entry receipt와 결과 row identity

시각이 같아도 이 edge가 완전하면 순서를 판정할 수 있다. edge가 끊겼거나 출처가 모순되면 PASS가 아니라
`INCONCLUSIVE: INSUFFICIENT_EVIDENCE` 또는 `EVIDENCE_CONFLICT`다. consent-completed Outbox 전달이
늦었다는 사실만으로 FAIL을 만들지 않는다.

## WhyYou Test Instrumentation

### Consent fault boundary

`ApplicantAccessService.record_consent()`의 `save_consent()` 직후, invitation 전이와 Outbox append 전에
local/test 전용 guard를 호출한다. 여기서 receipt를 fsync한 뒤 예외를 발생시키면 실제 HTTP transaction
middleware가 consent row를 포함한 요청 전체를 rollback한다. 이 지점은 첫 DB write 이후이므로 “아무
것도 쓰기 전 실패”보다 부분 저장 위험을 직접 검증한다.

marker는 `consent/{invitation_id}.json`에 두고 다음을 요구한다.

- schema/fault type 정확 일치
- Run ID, invitation ID, applicant ID 일치
- `APP_ENVIRONMENT`가 local/test
- `CONTROLPROOF_TEST_HOOKS_ENABLED=true`
- 발급·만료 시각과 최대 600초 TTL
- one-shot consumed token의 원자적 생성

### Processing observer

local/test에서만 다음 경계에 최소 receipt를 남긴다.

- consent fault trigger
- `workers/analysis/event_handler.py::AnalysisRequestedEventHandler.__call__`의 submission analysis 진입
- `interview_engine/application/session_service.py`의 `_create_session_once`, `_start_session_once`,
  `confirm_recording_upload` 성공 직후
- `runtime/worker.py::ReportRequestedEventHandler.__call__`의 reporting 진입

receipt는 Run/lane/subject, trace ID, event/request ID, boundary, observed_at만 포함하며 본문, 답변, 이메일,
점수와 credential은 포함하지 않는다. observer는 판정을 하지 않고 운영환경에서 활성화될 수 없다.
observer receipt 기록·flush가 실패해도 WhyYou product transaction은 계속되어야 하며, ControlProof는
필수 receipt 부재를 PASS가 아닌 `INCONCLUSIVE: INSUFFICIENT_EVIDENCE`로 처리한다.

### Conditional remediation gate

Post-T078 evidence correction: the initial bundle remains immutable. The direct
assessment outbox insert is a probe input; its database acknowledgement is not
the report handler's consent decision. Add an observer boundary after the
existing fault hook and before the first report read, then seal its
Run/lane/subject/event-linked receipt with the attempt and effect evidence.
Any later consent guard must execute before this start receipt. Treat handler
entry alone as diagnostic. If the authorization outcome or effect
source is unavailable, report insufficient evidence. Preserve only allowlisted
consent rejection reasons and separate restore cleanup from retry/order facts.
Use scoped RED-to-green contracts before applying any target product guard.
The evidence correction may touch the adapters, model, judge, executor, bundle
verifier and local/test observer files listed in T080-E1; it does not alter the
historical parent or authorize a child Run while the restore block remains.

instrumentation·seed·adapter는 첫 Run 전에 구현할 수 있다. 아래 제품 보호조치는 첫 actual FAIL을 봉인한
뒤에만 구현한다.

- analysis worker의 active `document_analysis` consent 재확인
- interview start의 active `recording` consent 재확인
- report generation의 active `ai_assessment` consent 재확인

첫 Run이 해당 경계를 PASS하면 방어 코드를 중복 추가하지 않는다. FAIL이면 부모 bundle digest를 기록한
후 원인을 먼저 `TARGET_CONTROL_DEFECT`, `RUNNER_OR_OBSERVER_DEFECT`, `RESTORE_OPERATOR_DEFECT` 중 하나로
분류한다. A2~A5의 대상 통제 결함은 WhyYou 개인 브랜치의 실제 경계에서 최소 guard를 보완한다. A6의
부분 동의나 A7의 중복·복구 순서 위반은 consent application/middleware와 ControlProof restore 중 실제
책임 경계를 증적으로 정한 뒤 그 경계만 보완한다. 실행기·observer 결함을 WhyYou 결함으로 고치거나,
WhyYou 직접 위반을 실행기 수정으로 숨기지 않는다. 보완 뒤 같은 profile의 child Run으로 검증한다.

## Adapter and Judge Design

ControlProof `AdapterSet`에 다음 선택 protocol을 additive하게 추가한다.

- `ConsentAdapter`: policy 읽기, 동의 제출, commit projection 읽기
- `ProtectedProcessingAdapter`: path capability, request/event attempt, effect projection
- `N02SeedAdapter`: lane별 합성 subject와 prerequisite fixture 생성·teardown
- `ConsentFaultAdapter`: marker apply, trigger receipt, restore, safe-state
- `CausalReceiptAdapter`: trace/event receipt와 causal edge 수집

adapter는 raw fact만 반환하고 PASS/FAIL을 정하지 않는다. `engine/judges/n02.py`가 path별 delta와 evidence
availability를 평가한다. N02-A2~A4에서 금지 효과가 하나라도 직접 관찰되면 FAIL이 우선하며, HTTP가
403이어도 effect projection이 UNAVAILABLE이면 PASS가 아니다.

readiness가 `READY`가 아니면 기존 공통 `operator_action` 필드에 실행 담당자가 취할 수 있는 비민감
조치를 반드시 제공한다. `ACCESS_BLOCKED`는 접근이 막힌 source와 필요한 credential/권한 범주를
구분하되 실제 credential 값은 출력하지 않는다.

`N02SeedAdapter`는 fault lane에 대해 `apply_probe_overlay(path)`와 `remove_probe_overlay(path)`도 제공한다.
overlay는 실패 직후 zero snapshot 이후에만 적용하며, 복구 동의 전 모든 overlay 제거와 원래 seed
digest 복원을 확인한다.

## Evidence and Bundle

기존 `controlproof.bundle.v1`의 manifest, SHA-256, redaction, immutable retest 계약을 유지하고
`profile_contract=controlproof.bundle-profile.spec003.v1`을 추가한다.

| Evidence | 계획된 artifact |
|---|---|
| EV3-01 | `n02-capabilities.json`, `environment.json`, scenario/target snapshot |
| EV3-02 | `policy-and-consent.json`, sanitized consent HTTP exchange |
| EV3-03 | lane별 `baseline-effects.jsonl`, fixture descriptor |
| EV3-04 | `bypass-http-exchanges.jsonl`, worker event command receipt |
| EV3-05 | `protected-effects.jsonl` 전후 snapshot과 delta |
| EV3-06 | `causal-events.jsonl`, `causal-edges.jsonl` |
| EV3-07 | consent fault marker digest와 `fault-receipts.jsonl` |
| EV3-08 | failed-consent effect snapshot |
| EV3-09 | restore receipt, recovered consent/effect snapshot |
| EV3-10 | judgement, summary, manifest, retest diff |

전체 테이블이나 로그 dump는 금지한다. row ID, 상태, event type/version, count, trace digest와 필요 최소
시각만 allowlist projection으로 수집한다.

## Test Strategy

### ControlProof automated gates

- model: lane/fixture/capability/causal edge/fault receipt validation
- scenario contract: profile, assertion, EV3, 단계, restore 정책의 canonical 집합
- adapter contract: PRESENT/ABSENT/UNAVAILABLE, 403/5xx/timeout, 최소 DB projection, secret redaction,
  non-READY `operator_action`
- judge fixtures: PASS, 각 경로 직접 FAIL, 부족 증적, 충돌, baseline invalid, restore failure
- integration: atomic six-lane seed rollback, consent-response timeout의 상태 확인 불가 판정,
  six-lane orchestration, interrupt/timeout restore, parent-child immutability
- regression: Spec 001·002 profile selection, bundle verify와 270-test 기준 동작 보존

### WhyYou automated gates

- 현재 `test_consent_gate.py`는 유지한다.
- 오래된 `cross_module/test_a_to_b.py` 전체를 N-02 gate로 복원하지 않는다. 삭제된 harness와 무관한 현재
  production wiring을 사용하는 작은 통합시험으로 교체한다.
- consent fault가 receipt 뒤 5xx와 전체 rollback을 만드는 통합시험
- local/test 밖 hook startup 거부, marker mismatch/expiry/other subject 무시 시험
- observer 저장 실패가 제품 transaction을 실패시키지 않는 통합시험
- deep boundary에서 active consent 부재를 현재 동작 그대로 포착하는 characterization 시험
- 보호조치 보완은 FAIL 봉인 뒤 expectation을 변경하거나 별도 regression으로 추가

### Actual-stack gate

1. 두 저장소 clean/non-main 및 local-only preflight
2. 최초 N-02 Run
3. bundle verify와 restore 성공
4. 직접 FAIL이면 부모 봉인 → 최소 수정 → child Run
5. 최종 Run에서 A1~A7, EV3-01~10, claim scope 확인
6. 부모와 child manifest 불변·계보 검증

CLI 출력의 사람이 읽기 쉬운 정도는 자동 projection 계약만 검사한다. 사람 대상 이해도 평가는 Spec 005
웹 결과 화면에서 수행한다.

## Project Structure

### Documentation

```text
specs/003-n02-consent-order/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── controlproof-cli-v3.md
│   ├── evidence-bundle-v3.md
│   ├── scenario-profile-v3.md
│   ├── consent-fault-observer.md
│   └── whyyou-n02-adapter.md
├── checklists/
│   └── requirements.md
├── tasks.md                    # 구현·시험·actual Run 실행 순서
├── validation.md               # 구현 중 명령·결과·Run·bundle 기록
├── traceability.md             # FR/SC/assertion/EV → task/test/artifact
└── implementation-decisions.md # 최초 Run 뒤 조건부 보완 결정
```

### ControlProof

```text
engine/
├── cli.py                      # N-02 profile selection/projection
├── config.py                   # profile별 safety policy
├── models.py                   # lane, path, consent, causality 모델
├── scenario.py                 # scenario v3 validation
├── evidence.py                 # Spec 003 bundle profile
├── presentation.py             # path·순서·한계 설명
├── executors/
│   └── n02.py                  # six-lane orchestration
├── judges/
│   └── n02.py                  # N02-A1~A7
└── adapters/
    ├── base.py                 # N-02 protocol
    └── whyyou/
        ├── n02_seed.py
        ├── consent.py
        ├── protected_processing.py
        ├── consent_fault.py
        └── causality.py

seeds/
└── n02_subjects.py

scenarios/
└── N-02.yaml

tests/
├── unit/                       # judge/model/fault lifecycle
├── contract/                   # profile/adapter/CLI/bundle
├── integration/                # six lanes, restore, retest
└── fixtures/                   # canonical PASS/FAIL/INCONCLUSIVE facts
```

### WhyYou personal branch

```text
backend/src/interview_evidence/
├── company_management/application/applicant_access_service.py
├── interview_engine/application/session_service.py  # create/start/recording observer
├── interview_engine/api/__init__.py                  # observer port composition
├── integration/company_submission.py
├── integration/submission_interview.py
├── shared/database.py                    # A6 rollback 결함일 때만 조건부 보완
├── runtime/controlproof_consent.py       # fault + observer, local/test only
├── runtime/production.py                 # guarded wiring/health
├── runtime/worker.py                     # analysis/report handler receipts
└── workers/analysis/event_handler.py    # 분석 worker 실재 경계/조건부 guard

backend/tests/
├── integration/                          # current production wiring N-02 tests
└── unit/                                 # marker/guard/observer safety
```

**Structure Decision**: 기존 두 저장소와 Spec 001·002 엔진을 유지한다. N-02 전용 orchestration과 judge는
새 모듈로 분리하고 `runner.py`에는 profile 등록만 둔다. WhyYou 변경은 `main`이 아닌
`bosung/controlproof-h03-integration`에서 이어지는 개인 feature branch에만 적용한다.

## Compatibility and Migration

- DB migration은 기본 계획에 없다. N-02 증적은 기존 WhyYou row와 ControlProof file bundle을 읽는다.
- 새 영속 table은 actual Run이 기존 allowlist projection으로 불가능하다고 확인된 경우에만 별도 결정한다.
- scenario v1/v2와 bundle profile Spec 001/002를 계속 읽고 실행한다.
- `Run` validation은 profile registry 기반으로 바꿔 N-02 추가가 Spec 002 queue 필드를 강제하지 않게 한다.
- `.env.example`에는 N-02 marker/observer 설정을 additive하게 추가하고 실제 secret은 저장하지 않는다.
- 기존 sealed bundle은 재작성하지 않는다.

## Complexity Tracking

Constitution 위반 예외는 없다. lane이 6개인 이유는 서로 다른 경계의 상태 오염을 막고 저장 실패 복구만
같은 subject로 증명하기 위해서다. 심층 fixture는 제품 경로를 가짜로 만드는 대안보다 실제 authorization
경계를 직접 시험하며, fixture와 증분 효과를 분리해 판정 오염을 막는다.

## Phase Gate

Plan과 Tasks 단계는 완료됐다. `$speckit-analyze`에서 발견한 HIGH 5건·MEDIUM 7건을 반영하고
재분석에서 CRITICAL·HIGH·팀 해석 차이를 만드는 MEDIUM 0건을 확인했다. 다음 단계는
`$speckit-implement`이며 아래 순서로 구현한다.

1. 공통 model/profile 계약
2. WhyYou 관찰·fault·seed 인프라
3. adapter와 effect projection
4. N-02 executor/judge/bundle/CLI
5. 자동시험과 analyze
6. 최초 actual Run 및 봉인
7. FAIL이 확인된 경계만 조건부 보완
8. child Run, validation, traceability, converge

CRITICAL·HIGH 및 팀 해석 차이를 만드는 MEDIUM이 재분석에서 0건일 때만 위 구현 파일을 수정한다.
