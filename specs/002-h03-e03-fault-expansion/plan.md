# Implementation Plan: H-03·E-03 장애·재시도·DLQ 확장

**Branch**: `002-h03-e03-fault-expansion` | **Date**: 2026-09-28 | **Spec**: [spec.md](./spec.md)

**Input**: [Spec 002](./spec.md), [Spec 001](../001-execution-evidence-h03/spec.md),
[Constitution](../../.specify/memory/constitution.md), WhyYou 검증 브랜치
`bosung/controlproof-h03-integration`의 로컬 실행 계약

## Summary

Spec 001의 Run 생명주기, append-only Evidence Bundle, 판정 우선순위와 WhyYou adapter 경계를
그대로 유지하면서 다음 네 축을 확장한다.

1. 공식 target을 `whyyou-local`·`LOCAL_EMULATED`로 고정하고 실제 AWS 검증은 `NOT_RUN`으로 남긴다.
2. LocalStack `iep-reporting`의 실제 redrive 설정·전달 시도·`iep-reporting-dlq` 이동을 관찰하고,
   장애 해제 뒤 동일 domain event를 안전하게 원 queue로 되돌린다.
3. `BEFORE_RESULT_DURABLE`과 `AFTER_RESULT_DURABLE_BEFORE_COMPLETION`을 별도 Run으로 실행한다.
   후자는 DB transaction commit 후 SQS acknowledge 전의 일회성 ack-loss hook으로 만든다.
4. H-03은 API operation 2개에서 파생되는 canonical decision path ID 3개를, E-03은
   report·projection·processed marker·원 Outbox와
   단계·invitation·HumanReview·감사의 정확한 업무 효과를 판정한다.

ControlProof는 기존 Python CLI/파일 bundle 구조를 유지한다. WhyYou 변경은 개인 검증 브랜치에만
적용하며 최초 실제 FAIL bundle을 봉인하기 전에는 보호조치 코드를 수정하지 않는다. 웹 워크벤치와
실제 AWS 재배포는 이 Plan에 포함하지 않는다.

## Technical Context

**Language/Version**: ControlProof와 WhyYou 모두 Python 3.12 이상. WhyYou 회사 콘솔은 기존
React/TypeScript를 사용하되 Spec 002는 화면 신규 개발을 전제하지 않는다.

**Primary Dependencies**: 기존 Pydantic 2.x, PyYAML 6.x, HTTPX 0.27+, Playwright 1.55+,
SQLAlchemy 2.x, Psycopg 3.x에 `boto3>=1.35,<2`를 추가해 LocalStack SQS를 관찰·복구한다.
WhyYou는 기존 FastAPI, SQLAlchemy, boto3 queue adapter와 LocalStack 구성을 재사용한다.

**Storage**: ControlProof canonical 저장소는 `.controlproof/runs/{run_id}/`의 append-only bundle이다.
Spec 002는 `environment.snapshot.json`, `queue-topology.snapshot.json`, `delivery-attempts.jsonl`,
`effects.jsonl`을 추가한다. WhyYou 상태는 로컬 PostgreSQL, LocalStack SQS/DLQ와 기존 Outbox를
사용하며 ControlProof 전용 DB를 추가하지 않는다.

**Testing**: pytest 단위·계약·통합 시험, HTTPX MockTransport, boto3 Stubber 또는 LocalStack 계약 시험,
Playwright Chromium, Ruff. WhyYou는 기존 pytest와 queue topology·worker 단위 시험을 확장한다.

**Target Platform**: Windows 개발 호스트의 Python CLI와 WhyYou API/worker/company-console,
Docker Desktop의 PostgreSQL 16(pgvector), LocalStack 3.8, Mailpit. 실제 AWS는 실행 대상이 아니다.

**Project Type**: 단일 Python 검증 CLI/라이브러리 + WhyYou adapter + WhyYou 개인 브랜치의
local/test 전용 fault hook과 필요한 보호조치 보완.

**Performance Goals**: 공식 local fixture에서 각 장애 변형 Run은 복구 포함 10분 이내 종료한다.
`SQS_REPORTING_MAX_RECEIVE_COUNT=3`, `SQS_REPORTING_VISIBILITY_TIMEOUT_SECONDS=5`를 공식 데모
queue snapshot으로 사용한다. 실제 관찰값이 다르면 실행하지 않고 readiness 실패로 표시한다.

**Constraints**: 실제 개인정보·운영 결정·외부 AI 호출 금지, loopback/LocalStack endpoint만 허용,
한 Run에 한 시나리오·한 fault variant, target+subject lock, 장애 후 의무 복구, 최소 증적만 저장,
최초 결과 불변, LocalStack PASS의 AWS 승격 금지, WhyYou `main` 직접 변경·push 금지.

**Scale/Scope**: 한 Run에 합성 지원자 1명과 domain event 1개. H-03 DLQ Run 1종,
E-03 BEFORE Run 1종, E-03 AFTER Run 1종을 제공한다. 동시성·부하·다중 worker race 한계는 제외한다.

## Constitution Check

*GATE: Phase 0 시작 전과 Phase 1 설계 후 모두 통과해야 한다.*

| 원칙 | 설계상 확인 | 상태 |
|---|---|---|
| I. 판정은 증적에서만 나온다 | queue attribute, attempt receipt, DLQ message, DB effect snapshot과 API/browser 결과를 원본 artifact로 저장하고 필수 자료가 없으면 PASS를 금지한다. | PASS |
| II. 대상·준비·결과 분리 | LocalStack·fault hook·DB observer 준비 여부와 WhyYou verdict를 분리한다. 실제 AWS는 target 부재가 아니라 `NOT_RUN`·미검증 범위다. | PASS |
| III. 사람의 최종 결정 권한 | operation 2개·canonical path ID 3개의 거부와 사람 결정 재전송만 시험한다. AI 점수는 결정 또는 verdict 입력으로 사용하지 않는다. | PASS |
| IV. 시나리오/어댑터 분리 | fault variant·steps·assertion·evidence는 YAML v2 profile에, SQS·DB·HTTP 세부는 WhyYou adapter v2에 둔다. | PASS |
| V. 격리·결정론·복구 | 합성 대상, 고정 model/embedder, local/test hook, run/session allowlist, TTL, target lock과 finally 복구를 사용한다. | PASS |
| VI. 불변 결과·재시험 계보 | 최초 FAIL과 수정 후 PASS는 별도 bundle과 parent link를 사용한다. DLQ redrive도 원 Run 기록을 수정하지 않는다. | PASS |
| VII. 명세-증적 추적성 | FR·H03/E03 assertion → scenario step → adapter capability → artifact → test를 계약과 tasks에서 연결한다. | PASS |

### Phase 1 재확인

데이터 모델은 delivery attempt와 business effect를 분리하고, 계약은 실제 AWS 미검증 범위,
LocalStack queue topology, fault boundary와 decision path를 명시한다. 기존 v1 bundle과 H-03 v1
시나리오는 읽기 호환을 유지하며 새 v2 profile만 추가 필드를 요구한다. target 전용 변경은 local/test
guard와 개인 브랜치로 제한된다. 설계 후 Constitution 위반과 Complexity Tracking 예외는 없다.

## Architectural Decisions

### 1. Spec 001 계약을 보존하는 additive v2 확장

기존 `H-03.yaml`, v1 bundle과 `RunOrchestrator` 동작을 삭제하거나 의미 변경하지 않는다.
`ScenarioDefinition`에 `execution_profile`, `fault_variant`, 환경·효과 계약을 선택 필드로 추가하고,
v1 입력은 기존 validator와 executor가 처리한다. Spec 002 파일은 다음 profile을 사용한다.

- `H03_DLQ_V2`: H03-A1~A9
- `E03_BEFORE_V2`: E03-A1~A4·A7·A8
- `E03_AFTER_V2`: E03-A1·A5·A6·A8

두 E-03 Run을 하나의 verdict로 합치지 않는다. CLI projection은 두 변형의 coverage를 나란히 보여줄
수 있지만 각 bundle의 verdict는 독립적이다. E-03 전체를 PASS라고 표시하려면 두 변형 Run이 모두
존재하고 해당 필수 assertion이 PASS인지 별도로 확인해야 하며 MVP에서는 별도 aggregate verdict를
저장하지 않는다.

### 2. 공통 실행 세션 + profile executor

기존 runner의 lock, lifecycle, checkpoint, artifact writer, restore-finally와 seal 동작을
`ExecutionSession`으로 추출한다. profile executor는 YAML step 순서와 action handler registry를
사용하며 target 세부를 알지 않는다. Spec 001 executor는 기존 흐름을 보존하고 Spec 002는
`H03DlqExecutor`, `E03BeforeExecutor`, `E03AfterExecutor`를 등록한다.

WhyYou의 queue·decision·effect·fault 구현은 `engine/adapters/whyyou/adapter.py` 한 곳에서 최종
`AdapterSet`으로 조립한다. 개별 파일이 구현됐더라도 profile이 요구하는 모든 capability와 contract
version이 composition root에 등록되지 않으면 해당 profile은 READY가 아니다. 최종 조립 계약 테스트는
실제 executor 실행 전에 전체 등록 집합을 확인한다.

개발 중인 executor의 일부 assertion만 확인하기 위한 별도 runtime profile·CLI·부분 verdict는 만들지
않는다. US3 단계에서는 `E03BeforeExecutor`의 action pipeline과 E03-A1~A4/A8 judge를 단위·통합
테스트에서 직접 호출하고, canonical `E03_BEFORE_V2`는 US5에서 E03-A7과 최종 adapter composition이
완료되기 전까지 runner에 등록하지 않는다. US5 완료 작업은 composition contract를 통과한 뒤
`engine/runner.py`의 profile registry에 `E03BeforeExecutor`를 명시적으로 연결하고 실제 dispatch
계약으로 이를 검증한다. 따라서 중간 테스트 성공을 시나리오 PASS로 저장하거나 표시할 수 없다.

완전한 범용 workflow 언어나 새로운 작업 queue는 만들지 않는다. 세 executor가 공유하는 단계는
handler로 재사용하고, profile 차이는 적용 assertion·fault variant·복구 순서로만 남긴다.

### 3. 실행환경 snapshot은 target source snapshot과 분리

기존 `TargetSnapshot v1`은 git/OpenAPI/schema/model identity를 계속 소유한다. 새
`TargetEnvironmentSnapshot v1`은 `whyyou-local`, `LOCAL_EMULATED`, loopback URL, 구성요소 버전,
LocalStack endpoint, 외부 AI 차단, AWS `NOT_RUN`과 미검증 서비스 목록을 소유한다.

환경 identity digest를 `run.json`과 EV2-01에 연결한다. staging/AWS는 다른 `target_id`와 새 snapshot,
새 Run이 필요하며 local bundle을 복사해 사용할 수 없다.

### 4. LocalStack SQS adapter로 topology·DLQ·redrive를 관찰

ControlProof에 boto3 기반 `WhyYouQueueAdapter`를 추가한다. adapter는 실행 전에 queue URL과
`RedrivePolicy`, `VisibilityTimeout`, retention, DLQ ARN, 실제 `maxReceiveCount`를 읽는다.
공식 profile은 `iep-reporting`·`iep-reporting-dlq`, max receive count 3, visibility 5초와 일치할 때만
READY다. 값은 환경 snapshot에 고정되며 production 기본값 12를 시험했다고 주장하지 않는다.

전달 시도 수는 WhyYou fault receipt의 `delivery_attempt` 시계열로 판정하고 DLQ message의 domain
`outbox_event_id`와 연결한다. 복구 시 DLQ body와 message attributes를 원 queue에 먼저 publish하고,
성공 receipt를 저장한 뒤 DLQ 원본을 삭제한다. send 성공·delete 실패는 복구 불확실성으로 기록하되
WhyYou processed-message 멱등성이 중복 업무 효과를 차단하는지 계속 관찰한다.

책임 경계는 중복 구현 없이 고정한다. `WhyYouQueueAdapter`는 topology·attempt·DLQ 조회와 단일 message의
send→receipt→delete primitive만 소유한다. `ExecutionSession`은 marker 해제·worker health 확인 뒤 이
primitive를 호출하고 모든 receipt를 evidence writer에 남기며, delete 불확실성을 `RESTORE_FAILED`로
승격하고 effect adapter로 복구 결과를 polling한다. executor는 이 공통 복구 절차를 호출할 뿐 queue
mutation을 다시 구현하지 않는다.

### 5. 두 장애 의미는 서로 다른 target hook으로 만든다

`BEFORE_RESULT_DURABLE`은 기존 `before_report_side_effect` hook을 사용하고 marker를 재시도 한도
소진까지 유지한다. 각 attempt는 report side effect 전에 TimeoutError로 기존 retry 경로에 들어간다.

`AFTER_RESULT_DURABLE_BEFORE_COMPLETION`은 `MessageConsumer`의 DB commit 직후·SQS acknowledge 직전에
선택적 local/test hook을 호출한다. reporting event와 allowlist된 run/session에만 일회성으로
ack를 생략하고 boundary receipt를 남긴다. DB에는 report, assistant projection,
`processed_messages`가 이미 commit돼 있어야 한다. 재전달은 handler 진입 전 processed marker를 만나
duplicate-ack로 끝난다.

기존 marker schema는 `fault_type` 확장으로 호환을 유지한다. production·staging에서는 hook 활성화
자체가 startup 실패여야 하며 marker 생성 성공만으로 경계 도달을 인정하지 않는다.

### 6. 논리 업무 효과는 allowlist projection으로 비교

WhyYou DB 전체 dump를 수집하지 않는다. `WhyYouEffectObserver`가 다음 식별자와 건수만 조회한다.

- reporting: report ID/session, report에 속한 assistant document ID·source version 집합,
  `(consumer_name, event_id, event_version)` processed key, 원 Outbox event ID·publish status
- decision: invitation-stage assignment/version, invitation status, HumanReview ID·actor,
  `final_decision.create` audit ID·request ID

AFTER variant의 PASS는 handler 호출 횟수 1회가 아니라 위 논리 효과가 기대 건수와 일치하고
duplicate-ack receipt가 존재하는지로 판정한다. 현재 WhyYou가 만들지 않는 completion Outbox event는
조회·필수 증적·FAIL 조건 어디에도 추가하지 않는다.

### 7. H-03은 operation 2개와 canonical decision path ID 3개로 고정

operation capability는 `recordHumanFinalDecision`과 `moveApplicantsToRecruitingStage` 두 개다. 검증
case는 `FINAL_DECISION`, `BATCH_MOVE_FINAL_ACCEPT`, `BATCH_MOVE_FINAL_REJECT`의 세 path ID다. 뒤의
두 path ID는 같은 batch operation을 사용하지만 목표 단계 의미가 각각 `최종합격`과 `불합격`이므로
서로 격리해 실행·저장한다. 각 요청 전후에 같은 effect snapshot을 수집해 거부 응답뿐 아니라 부분
변경 0건을 확인한다. 중간 단계 이동은 H-03 path 목록에 넣지 않는다.

E03-A7은 복구된 report를 사용해 `recordHumanFinalDecision`만 같은 `Idempotency-Key`로 두 번 호출한다.
현재 target이 key를 버리는 사실은 최초 Run의 예상 FAIL 후보이지 ControlProof readiness 실패가 아니다.

### 8. 최초 FAIL과 target 보완의 순서를 강제

구현 완료는 WhyYou PASS와 별개다. 첫 실제 stack 실행에서는 현재 동작을 그대로 검증하고 bundle을
seal한다. H03-A7 우회, H03-A9 실패 노출, E03-A7 결정 중복 등 직접 결함이 나오면 그 Run을 보존한다.

WhyYou 보호조치 수정은 개인 브랜치의 후속 commit에서만 수행하고 parent Run을 지정한 retest로
검증한다. 일반 batch route의 최종 단계 이동은 정상 final-decision route를 사용하도록 거부하고,
Idempotency-Key 보완은 동일 key가 동일 결정 효과를 반환하도록 application service 경계에 둔다.
담당자 실패 표시처럼 새 영속 상태가 필요한 변경은 최초 Run 결과를 본 뒤 별도 product decision을
기록하고 구현한다.

Constitution의 대표 FAIL→수정→PASS 품질 게이트는 선택사항이 아니다. 세 최초 실제 Run에서 직접
FAIL이 하나라도 나오면 Spec 002 완료 전에 최소 한 건을 개인 브랜치에서 보완하고 원 FAIL을 부모로
지정한 PASS retest를 만든다. 유일한 FAIL이 새 영속 상태·API·UI를 요구하면 별도 product decision과
후속 구현·PASS retest가 끝날 때까지 Spec 002를 완료 처리하지 않는다. 세 Run이 모두 PASS라면 결함을
인위적으로 만들지 않고 Spec 001의 승인된 대표 FAIL→PASS bundle 쌍을 다시 verify해 완료 기록에
연결한다.

### 9. 판정과 증적 호환성

Spec 002 judge는 assertion별 필요한 observation·artifact가 없으면 INCONCLUSIVE, 직접 누락·중복·우회가
관찰되면 FAIL, 모든 필수 사실과 restore가 확인될 때만 PASS를 낸다. delivery attempt 여러 건은
중복 업무 효과가 아니다. source별 조회 성공+0건과 조회 실패를 구분한다.

Bundle은 `controlproof.bundle.v1`의 canonical 파일과 봉인 규칙을 유지하고 additive 파일만 추가한다.
Spec 002 manifest는 `profile_contract=controlproof.bundle-profile.spec002.v1`로 추가 검증 규칙을
선택한다. v1 verify는 기존 bundle을 계속 읽고, Spec 002 profile verify는 EV2-01~EV2-12와 환경
digest·effect identity를 추가 확인한다.

CLI JSON과 사람이 읽는 결과에는 `claim_scope=EXECUTED_SCENARIO_AND_EVIDENCE_ONLY`와 실제
`unverified_scope`를 함께 표시한다. 사람이 읽는 결과와 팀 안내 문서는 “이 결과는 실행된 시나리오와
확보한 증적에 한정되며 법적 준수 전체를 인증하거나 보증하지 않는다”는 주장 경계를 명시해야 한다.
presentation contract는 이 필드와 문구가 누락되거나 전체 준수·인증·보증으로 오해되는 표현이 들어가면
실패해야 한다.

## Observation and Timing Policy

- 공식 local queue: max receive count 3, visibility timeout 5초
- 일반 polling: 2초
- BEFORE retry/DLQ 관찰 기한: 360초
- AFTER commit/ack 경계 및 duplicate-ack 관찰 기한: 60초
- 담당자 상태 안정화: 3회 연속, 최소 4초
- 사람 결정 재전송 간격: 최초 응답 직후 1회, 같은 `Idempotency-Key`
- 환경 복구·DLQ redrive·report 생성 기한: 180초
- 한 변형 전체 deadline: 600초
- 모든 수치는 scenario snapshot에 포함하며 변경 시 scenario version을 올린다.

## Project Structure

### Documentation (this feature)

```text
specs/002-h03-e03-fault-expansion/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── validation.md               # 단계별 test/Run/restore/완료 gate 기록
├── traceability.md             # FR·SC·assertion·evidence → task/test/구현 매핑
├── implementation-decisions.md # 실제 FAIL 뒤 조건부 WhyYou 보완 결정 기록
├── contracts/
│   ├── controlproof-cli-v2.md
│   ├── evidence-bundle-v2.md
│   ├── scenario-profile-v2.md
│   └── whyyou-adapter-v2.md
├── checklists/
│   └── requirements.md
└── tasks.md                    # $speckit-tasks에서 생성
```

### ControlProof source (this repository)

```text
engine/
├── cli.py                      # v2 profile dispatch와 결과 projection
├── config.py                   # LocalStack·queue·환경 guard 설정
├── models.py                   # 환경·queue·attempt·effect·fault variant 모델
├── scenario.py                 # v1 호환 + v2 profile validation
├── execution.py                # 공통 lifecycle/checkpoint/restore/seal session
├── runner.py                   # Spec 001 호환 facade와 profile dispatch
├── judge.py                    # 기존 H03-A1~A6 유지
├── executors/
│   ├── __init__.py
│   ├── h03_dlq.py
│   ├── e03_before.py
│   └── e03_after.py
├── judges/
│   ├── __init__.py
│   ├── common.py
│   ├── h03_dlq.py
│   └── e03.py
└── adapters/
    ├── base.py                 # queue·decision·effect protocol 추가
    └── whyyou/
        ├── adapter.py
        ├── capability.py
        ├── queue.py            # LocalStack topology/DLQ/redrive
        ├── decisions.py        # H-03 operation 2개/path ID 3개와 E-03 replay
        ├── effects.py          # 최소 DB projection
        ├── fault.py            # 두 marker variant·receipt·restore
        └── state.py

scenarios/
├── H-03.yaml                   # Spec 001 v1, 변경 없음
├── H-03-DLQ.yaml
├── E-03-BEFORE.yaml
└── E-03-AFTER.yaml

tests/
├── unit/                       # model, judge, effect identity, restore
├── contract/                   # scenario v2, adapter v2, bundle v2, CLI
├── integration/                # H03-DLQ, E03 BEFORE/AFTER, FAIL→PASS lineage
└── fixtures/                   # queue receipts, effect snapshots, bundles
```

### WhyYou source (sibling repo, personal branch only)

```text
backend/src/interview_evidence/
├── runtime/controlproof_faults.py
├── runtime/controlproof_model_substitute.py
├── runtime/worker.py
├── shared/messaging/worker.py
├── reporting/
│   ├── api/company_routes.py
│   └── application/final_decision_service.py
└── company_management/
    ├── api/company_routes.py
    └── application/hiring_service.py

backend/tests/
├── unit/shared/test_local_queue_topology.py
├── unit/runtime/test_controlproof_reporting_fault.py
├── unit/runtime/test_controlproof_model_substitute.py
├── integration/test_worker_delivery.py
└── integration/test_controlproof_fault_hook_safety.py
```

**Structure Decision**: ControlProof 공통 엔진에는 서비스 중립 model/protocol/judge만 추가하고,
LocalStack·WhyYou DB/API 이름은 `engine/adapters/whyyou`에 둔다. WhyYou 코드는
`bosung/controlproof-h03-integration` 계열 개인 브랜치에서만 변경하며 `main`에 직접 push하지 않는다.

## Requirement-to-Component Traceability

| 요구사항·assertion | 주요 구현 | 계약·시험 |
|---|---|---|
| FR-081~087, SC-013~014 | 환경 snapshot, endpoint guard, presentation | environment contract, preflight tests |
| FR-011~030, FR-088, H03-A8~A9, E03-A1~A2 | queue adapter, attempt observer, DLQ record | adapter contract, LocalStack integration |
| FR-031~040, FR-091, H03-A7 | decision adapter, operation 2개·path ID 3개 effect diff | decision contract, bypass fixture |
| FR-041~050, FR-089~093, E03-A3~A6 | fault variant, effect observer, E03 judge | boundary/duplicate contract tests |
| FR-051~055, FR-094~095, E03-A7 | decision replay와 effect snapshot | Idempotency-Key integration |
| FR-056~065, EV2-01~12 | bundle v2, redaction, digest, verify | bundle contract/tamper tests |
| FR-066~080, FR-096, E03-A8, SC-015 | common execution session, restore, retest, completion gate | lifecycle and FAIL→PASS tests |

## Implementation Sequence for Tasks

1. v1 회귀 baseline과 v2 scenario/model 계약
2. 환경 snapshot·LocalStack queue preflight
3. delivery/DLQ observer와 safe redrive
4. BEFORE variant와 H-03 DLQ executor/judge
5. AFTER commit-before-ack WhyYou hook과 E-03 executor/judge
6. decision path·effect observer와 E03-A7 replay
7. bundle/CLI projection·verify·retest 확장
8. 실제 stack 최초 Run 봉인
9. 확인된 WhyYou 결함만 개인 브랜치에서 보완
10. parent-linked retest와 문서화

## Complexity Tracking

Constitution 위반 또는 예외 없음.
