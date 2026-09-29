# Spec 002 구현 검증 기록

## 2026-09-28 — Setup 및 Foundation (T001~T019)

### 범위

- 실행 프로필과 장애 변형의 canonical 모델
- 로컬 실행환경·LocalStack 큐 topology snapshot 및 fail-closed 설정
- 서비스 중립 adapter 경계와 결정적 테스트 fixture
- 공통 실행 세션의 lock, checkpoint, 필수 복구, restore block, seal 순서
- Spec 001 호환 runner facade와 실행 프로필 registry
- Spec 002 증적 번들의 canonical 파일, typed evidence reference, cross-Run 원본 연결 및 변조 검증
- WhyYou 개인 브랜치의 로컬 전용 reporting queue 설정 예시

### 테스트 우선 확인(RED)

Foundation 구현 전에 아래 gate를 먼저 실행했다.

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_models_spec002.py tests/contract/test_scenario_profile_v2.py tests/unit/test_execution_session.py tests/contract/test_bundle_profile_spec002.py tests/contract/test_local_environment_guard.py tests/contract/test_package_layout.py tests/integration/test_spec001_v1_regression.py
```

초기 결과는 예상대로 collection 단계에서 실패했다. 당시 빠져 있던 계약은 Spec 002 모델과
`engine.execution`, 실행 프로필 registry의 `build_profile_runner`였다. 이 실패를 구현 출발점으로
사용했다.

### Foundation gate(GREEN)

동일 명령을 구현 완료 후 다시 실행한 결과:

```text
18 passed in 3.87s
```

확인한 핵심 동작:

- 기존 `H03_MINIMAL_V1` scenario와 v1 Evidence Bundle은 변경 없이 실행·검증된다.
- 등록되지 않은 v2 profile은 Run 디렉터리를 만들기 전에 거부된다.
- 모든 fault 실행은 공통 실행 세션의 필수 restore 경로를 거친다.
- restore 실패는 동일 target+subject의 후속 fault Run을 차단한다.
- Spec 002 bundle은 profile별 canonical 파일과 `controlproof.bundle-profile.spec002.v1`을 사용한다.
- `file:`, `artifact:`, `intrinsic:` reference와 origin Run digest가 검증된다.
- 봉인 후 현재 Run 파일 또는 origin Run artifact가 변조되면 verifier가 `INVALID`를 반환한다.
- 로컬이 아닌 SQS endpoint, 외부 AI, 잘못된 receive count, main/dirty WhyYou checkout과 dirty
  ControlProof checkout은 fail-closed로 거부된다.

### 전체 회귀 및 정적 검사

```powershell
.\.venv\Scripts\ruff.exe check engine tests
.\.venv\Scripts\python.exe -m pytest -q
```

결과:

```text
All checks passed!
152 passed in 156.21s (0:02:36)
```

### 의존성 및 저장소 경계

- `boto3 1.43.103`을 프로젝트 가상환경에 설치했다.
- ControlProof 구현 브랜치: `002-h03-e03-fault-expansion`
- WhyYou 작업 브랜치: `bosung/controlproof-h03-integration`
- WhyYou `main`에는 변경하지 않았다.
- 이 단계에서는 Docker/LocalStack 실제 장애 Run을 수행하지 않았다. 실제 큐 전달·DLQ·결정 효과
  검증은 T020 이후 사용자 스토리 slice에서 수행한다.
- 실제 AWS 및 외부 AI는 실행하지 않았고 계속 `NOT_RUN` 범위다.

## 2026-09-28 — User Story 1: 재시도 소진·DLQ·최종 실패 표시 (T020~T032)

### 이번 단계에서 고정한 의미

- reporting queue는 로컬 `iep-reporting`, 최종 실패 경로는 LocalStack의
  `iep-reporting-dlq`이며 max receive count는 3, visibility timeout은 5초다.
- worker의 각 저장 전 장애 영수증은 같은 Run·session·Outbox event와 event version,
  실제 delivery attempt, `BEFORE_RESULT_DURABLE` 경계를 함께 남긴다.
- 세 번의 전달 기록만 있거나 DLQ 메시지만 있는 것으로는 H03-A8을 PASS하지 않는다. 두 자료가
  같은 원 Outbox event로 연결되어야 한다.
- DLQ 조회 성공 후 일치 건이 없는 `ABSENT`와 LocalStack 접근 자체가 실패한 `UNAVAILABLE`을
  구분한다. 전자는 FAIL 후보이고 후자는 `INCONCLUSIVE: ACCESS_LIMITED`다.
- 화면의 실패 문구만으로 H03-A9을 PASS하지 않는다. API의 최종 실패 상태와 운영자용 DLQ
  locator까지 함께 있어야 한다. API가 계속 `queued`이면 화면이 실패처럼 보여도 FAIL이다.
- 복구는 fault marker 제거와 worker health 확인을 먼저 수행한 뒤, 현재 Run에서 선택한 단일 DLQ
  메시지만 source queue로 재전송한다. 전송 실패 시 원 DLQ 메시지는 삭제하지 않는다.

### 테스트 우선 확인(RED)

구현 전에 ControlProof의 queue adapter·H03-A8/A9 judge·DLQ lineage 테스트와 WhyYou의
영수증 계약 테스트를 추가했다. 최초 실행은 `engine.adapters.whyyou.queue`,
`engine.judges.h03_dlq`가 없고 WhyYou 영수증에 `event_version`과 경계 필드가 없어서 의도대로
실패했다. 이 실패를 US1 구현 출발점으로 사용했다.

### 구현 결과

- `WhyYouQueueAdapter`가 queue/DLQ topology, 전달 시도 영수증, 일치 DLQ 메시지와 안전한
  send-before-delete redrive를 소유한다. queue URL은 digest로만 남고 receipt handle과 원문 body는
  판정 결과에 노출하지 않는다.
- WhyYou 개인 브랜치의 BEFORE hook은 부작용 전에 v2 영수증을 append+fsync한 후 기존 retry
  경로로 TimeoutError를 전달한다. local/test 이외 환경에서는 hook을 계속 거부한다.
- `H03DlqExecutor`는 환경·topology·합성 대상·baseline·fault·trigger·boundary·attempt·DLQ·API/UI를
  순서대로 관찰하며, 중간 증적 오류가 나도 marker restore를 수행한다. restore와 worker health가
  모두 성공한 경우에만 queue adapter의 redrive primitive를 호출한다.
- `H03_DLQ_V2` profile은 registry에 등록했지만, 전체 `execute`는 US2의 세 결정 경로 adapter가
  합성되기 전까지 fail-closed다. 따라서 이번 단계는 독립 US1 실행 슬라이스의 완료이며 정식 H-03
  전체 verdict나 sealed 실제 Run을 만들었다는 뜻이 아니다.

### US1 gate(GREEN)

ControlProof의 US1 및 profile/회귀 gate:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/contract/test_whyyou_queue_adapter.py tests/integration/test_h03_dlq_lineage.py tests/unit/test_judge_h03_dlq.py tests/contract/test_whyyou_browser.py tests/contract/test_whyyou_capability.py tests/contract/test_scenario_profile_v2.py tests/integration/test_spec001_v1_regression.py
```

결과:

```text
33 passed in 3.81s
```

WhyYou 개인 브랜치의 topology 및 BEFORE 영수증 gate:

```powershell
.\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/shared/test_local_queue_topology.py backend/tests/unit/runtime/test_controlproof_reporting_fault.py
```

결과:

```text
24 passed, 1 warning in 0.93s
```

정적 검사:

```powershell
.\.venv\Scripts\ruff.exe check engine tests
```

결과: `All checks passed!`

ControlProof 전체 회귀:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

결과:

```text
173 passed in 118.41s (0:01:58)
```

### 아직 실행하지 않은 것

- Docker/LocalStack 실제 queue를 이용한 최초 H03 Run은 실행하지 않았다.
- `H03-A1~A6`와 새 `H03-A7`의 전체 결정 경로 시험은 US2에서 완성한다.
- AWS 배포 리소스와 외부 AI는 계속 `NOT_RUN`이며, 이 로컬 결과를 AWS 검증 결과로 확대 해석하지
  않는다.

## 2026-09-28 — User Story 2: 리포트 없는 채용 확정의 모든 경로 차단 (T033~T041)

### 이번 단계에서 고정한 의미

- WhyYou의 채용 확정 기능은 operation 두 개지만 시험 case는 세 개다. 단일 지원자 최종 결정
  `recordHumanFinalDecision` 한 건과, 일괄 단계 이동 `moveApplicantsToRecruitingStage`의
  `최종합격`·`불합격` 두 건을 서로 독립적으로 실행한다.
- AI 점수는 어느 판정 입력에도 사용하지 않는다. H03-A7은 리포트가 없는 합성 지원자에 대해
  `COMPANY_USER`가 시도한 세 경로가 모두 명시적으로 거부되고, 단계·invitation·HumanReview·감사
  효과가 전후 동일한지만 판정한다.
- 한 경로라도 요청을 수락하거나 일부 효과를 기록하면 직접 `FAIL`이다. 반대로 대상 접근 실패,
  경로 미등록, 명시적 거부인지 확인할 수 없는 오류는 제품 안전성을 입증하지 못하므로
  `INCONCLUSIVE`다.
- case마다 같은 시작 상태를 snapshot하고 시험 후 해당 합성 지원자 범위만 reset한다. 따라서 앞선
  `최종합격` 시험이 뒤의 `불합격` 시험 결과를 오염시키지 않는다.
- adapter는 고정된 WhyYou source commit, OpenAPI operation ID와 해당 position의 최종 단계 snapshot을
  capability 증적에 묶는다. 원문 `Idempotency-Key`는 메모리의 HTTP 요청에만 쓰고 산출물에는
  SHA-256 digest만 남긴다.

### 테스트 우선 확인(RED)

구현 전에 결정 adapter, H03-A7 judge, 세 경로 통합 테스트를 먼저 추가했다. 최초 실행은 아래처럼
필수 구현이 존재하지 않아 collection 단계에서 실패했다.

```text
ModuleNotFoundError: No module named 'engine.adapters.whyyou.decisions'
ImportError: cannot import name 'judge_h03_decisions'
```

이 실패를 T036~T040 구현의 출발점으로 사용했다.

### 구현 결과

- `WhyYouDecisionAdapter`가 두 OpenAPI operation을 세 canonical path로 확장하고, 회사 사용자 actor,
  final-stage snapshot, 안정된 오류 분류, 명시적 report-required 거부와 수락/부분 기록을 구분한다.
- `WhyYouEffectAdapter`가 합성 invitation/position으로 범위를 제한해 단계와 row version, invitation
  상태, HumanReview actor, `final_decision.create` 및 batch-move 감사 identity를 최소 투영한다. 조회
  성공 후 자료가 없을 때만 `ABSENT`, 접근 실패 시 `UNAVAILABLE`을 반환한다.
- `H03DlqExecutor.collect_us2`가 각 경로에 별도 logical operation ID를 부여해 pre-effect → 결정 시도
  → post-effect → reset 순서로 실행하고, `judge_h03_decisions`가 세 경로를 하나의 H03-A7 결과로
  집계한다.
- WhyYou 제품 코드는 이 단계에서 수정하지 않았다. 특히 일괄 최종 단계 이동이 실제로 우회되는지는
  봉인된 최초 실제 Run(T081)에서 판정한 뒤, 직접 FAIL 증적이 있을 때만 T082에서 수정한다.
- US1/US2 슬라이스는 독립 검증 가능하지만 canonical H03 bundle orchestration은 아직 완성 전이다.
  그러므로 전체 `execute`뿐 아니라 CLI preflight도 `profile.h03_dlq_v2.sealed_execution`을 이유로
  `RUNNER_NOT_READY`를 반환한다. 부분 구현을 실제 H-03 완료나 PASS로 표시하지 않는다.

### US2 gate(GREEN)

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/contract/test_whyyou_decision_adapter.py tests/unit/test_judge_h03_decisions.py tests/integration/test_h03_decision_paths.py
.\.venv\Scripts\ruff.exe check engine tests
```

결과:

```text
16 passed in 0.92s
All checks passed!
```

전체 ControlProof 회귀 테스트도 실행했다.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

결과:

```text
190 passed in 161.01s (0:02:41)
```

### 아직 실행하지 않은 것

- Docker/LocalStack 실제 대상에 세 결정 경로를 호출해 제품 verdict를 생성하지 않았다.
- 현재 코드 구조상 batch 경로의 우회 가능성이 보여도 이를 결과로 선판정하지 않는다. T081의 봉인된
  실제 증적 전에는 WhyYou 보호 로직을 고치지 않는다.
- 전체 H03 sealed Run과 H03-A1~A9의 canonical 증적 bundle은 US3 이후 공통 복구·증적 orchestration을
  합성하고 actual-stack gate에 도달해야 생성할 수 있다.
- AWS 및 외부 AI는 계속 `NOT_RUN`이다.

## 2026-09-28 — User Story 3: 저장 전 장애의 누락 없는 복구 (T042~T052)

### 이번 단계에서 고정한 의미

- `BEFORE_RESULT_DURABLE`은 report, assistant retrieval projection, `processed_messages`가
  저장되기 전에 발동해야 한다. 장애 영수증이 없으면 효과가 0건이어도 E03-A3을 PASS로 추정하지
  않고 `INCONCLUSIVE`로 판정한다.
- 장애 중 필수 내구 효과는 0건이어야 하지만 원 `report.generation_requested` Outbox 사건은
  보존돼야 한다. WhyYou가 생성하지 않는 별도 report-completed Outbox event는 요구하지 않는다.
- 복구 후 필수 reporting 효과는 논리 report 1건, 그 report를 가리키는 중복 없는 assistant
  projection 집합, `(reporting-worker, event_id, event_version=1)` processed key 1건과 원 Outbox 사건
  1건이다.
- 조회 성공 뒤 효과가 없거나 누락·중복·불일치한 경우는 직접 `FAIL`이고, DB·queue 접근 자체가
  실패하면 `INCONCLUSIVE: ACCESS_LIMITED`다.
- 복구는 marker 비활성·worker health를 먼저 확인한 뒤 선택된 DLQ 메시지 하나만 원문 body와
  attributes 그대로 source queue에 send하고, send 성공 뒤에만 DLQ 건을 delete한다. send 성공 후
  delete 실패도 안전 복구가 아니며 `ExecutionSession`에서 `RESTORE_FAILED`로 전이될 수 있는 false
  recovery outcome으로 보존한다.

### 테스트 우선 확인(RED)

T042~T045 테스트를 먼저 추가한 최초 실행은 collection 단계에서 다음 필수 구현이 없어 실패했다.

```text
ImportError: cannot import name 'coordinate_reporting_recovery' from 'engine.execution'
ModuleNotFoundError: No module named 'engine.judges.e03'
ModuleNotFoundError: No module named 'engine.executors.e03_before'
```

이 실패를 reporting effect adapter, 공통 복구 조정자, E-03 judge와 BEFORE executor 구현의 출발점으로
사용했다.

### 구현 결과

- `WhyYouEffectAdapter`가 합성 company·invitation·session·원 event 범위에서 report,
  `assistant_retrieval_documents`, `processed_messages`, 원 Outbox를 조회한다. ID와 projection 집합은
  정렬한 canonical 투영으로 만들기 때문에 DB 반환 순서가 달라도 같은 digest를 얻는다.
- `coordinate_reporting_recovery`가 marker 제거와 worker health → send-to-source → 영수증 append →
  DLQ delete → recovered effect polling 순서를 한 곳에서 소유한다. `ExecutionSession.recover_reporting`은
  모든 send/delete 결과를 `redrive-receipts.jsonl`에 append한다. H-03 US1/US2도 직접 queue mutation
  순서를 재구현하지 않고 같은 조정자를 사용한다.
- BEFORE boundary reader가 run, session, Outbox event, fault variant와 delivery attempt를 함께
  검증한다. marker 제거 여부는 report 생성 성공과 별개인 `probe_marker_removed`로 확인할 수 있다.
- canonical `E03_BEFORE_V2` scenario에는 E03-A1~A4/A7/A8과 EV2-01~05·09~12, 600초 전체 제한,
  180초 복구 제한, max receive 3·visibility 5초 계약을 선언했다.
- `E03BeforeExecutor.collect_us3`가 seed → BEFORE fault → trigger → 재시도/DLQ → injected effect 0건
  → marker 복구 → redrive → recovered effects를 실행하고 E03-A1~A4/A8만 독립 평가한다.
- E03-A7 사람 결정 replay는 US5의 책임으로 `pending_assertion_ids=(E03-A7,)`에 남겼다. 이 단계에서는
  `E03_BEFORE_V2`를 runner/CLI에 등록하지 않고, subset PASS를 profile verdict나 봉인 bundle로 만들지
  않는다.

### US3 subset gate(GREEN)

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/contract/test_whyyou_effect_adapter.py tests/unit/test_whyyou_queue_redrive.py tests/unit/test_judge_e03_before.py tests/integration/test_e03_before.py
.\.venv\Scripts\ruff.exe check engine tests
```

결과:

```text
13 passed in 0.86s
All checks passed!
```

공통 복구 변경이 기존 H-03과 Spec 001을 훼손하지 않는지 전체 회귀도 실행했다.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

결과:

```text
205 passed in 157.01s (0:02:37)
```

### 아직 실행하지 않은 것

- Docker/LocalStack·PostgreSQL 실제 대상에서 E-03 BEFORE Run을 만들거나 제품 verdict를 봉인하지
  않았다.
- E03-A7 같은-key 사람 결정 replay와 완전한 adapter composition은 US5에서 구현한다.
- 실제 AWS와 외부 AI는 계속 `NOT_RUN`이며 로컬 queue·DB 계약 결과를 AWS 검증으로 확대하지 않는다.

## 2026-09-29 — 최초 FAIL 근거 기반 WhyYou 보완 (T082~T084)

### 변경 허용 근거

문서 배치상 이 절이 실제 스택 절보다 먼저 보이지만, 실행 순서는 아래의 `T080 → T081`을 완료한 뒤
본 절의 `T082 → T084`였다. 즉 보완 코드가 최초 FAIL보다 먼저 들어간 것이 아니다.

보완은 최초 actual-stack bundle을 먼저 봉인한 뒤에만 수행했다. 부모 Run은 수정하지 않았다.

| Task | 직접 근거 | 부모 Run | 보완 목표 |
|---|---|---|---|
| T082 | H03-A7에서 단일 final-decision은 report 부재로 거부됐지만 batch `최종합격`·`불합격`은 수락됨 | `60b19e5a-6693-427b-bf87-039e45181cfc` | batch 최종 단계도 report-ready 보호 적용 |
| T083 | H03-A9/H03-A2에서 DLQ는 확인됐지만 제품 API가 계속 `queued` | `60b19e5a-6693-427b-bf87-039e45181cfc` | 영속 실패 projection과 API/UI terminal 상태 추가 |
| T084 | E03-A7에서 동일 key·동일 body 재전송이 동등 성공으로 재생되지 않음 | `e17e0af0-b46a-4022-93a4-a91a3247f16d` | 사람 결정 command의 exactly-once 업무 효과 구현 |

### T082 — batch 최종 단계 우회 차단

- RED에서는 report가 없는 invitation을 batch `최종합격`과 `불합격`으로 옮기는 두 요청이 모두
  성공했다.
- 회사 API가 batch 이동을 호출할 때 `require_final_report=True`를 명시하도록 했다. 서비스는 전체
  대상을 먼저 검증하므로 한 건이라도 report-ready가 아니면 어떤 pipeline row도 변경하지 않는다.
- reporting의 단일 final-decision 경로는 이미 자체 report guard를 가지므로, 내부 경계가 batch
  primitive를 사용할 때는 중복 guard를 강제하지 않는다. 이 차이는 호출부 인자로 명시해 숨은 정책
  차이를 제거했다.

### T083 — 숨은 최종 실패를 제품 상태로 공개

- 대안과 선택 이유는 `implementation-decisions.md`의 `ID-002-01`에 기록했다.
- 빈 실패 리포트를 만들거나 화면이 DLQ를 직접 읽지 않는다. 별도 `report_generation_failures`에 원
  event·session·마지막 source attempt·sanitized error code만 저장한다.
- 실제 report가 없고 terminal projection이 있을 때 API는 `failed`, `retryable=false`를 반환한다.
  회사 화면은 polling을 멈추고 리포트 실패와 결정 불가를 명시한다. 복구 후 실제 report가 생기면
  report가 실패 이력보다 우선한다.

### T084 — 사람 최종결정 멱등성

- `FinalDecisionService`가 report guard, 단계 이동, `HumanReview`, invitation `reviewed`, 감사 기록과
  idempotency resource 연결을 하나의 transaction 경계에서 소유한다.
- 동일 `Idempotency-Key`와 동일 본문 재전송은 최초 `HumanReview`와 현재 결정을 읽어 같은 201 응답을
  반환하고 업무 효과를 추가하지 않는다.
- 같은 key로 목표 단계 또는 `expected_pipeline_version`이 다른 본문을 보내면 409로 거부한다.
  예상 버전도 최초 `HumanReview` 값에 보존해 canonical body의 일부로 비교한다.
- production 조립은 기존 SQL `command_idempotency` store를 Lane D에 전달한다. 원본 key는 응답,
  감사 metadata, ControlProof bundle에 복사하지 않는다.

### WhyYou 변경과 검증

- 저장소: `jhkim0602/gbsa_aws`
- 브랜치: `bosung/controlproof-h03-integration`
- 커밋: `511ae9e` (`fix: harden report failure and final decisions`)
- `main`에는 push하지 않았다.

검증 결과:

```text
T082~T084 + migration target: 40 passed
T084 + cross-module transaction regression: 11 passed
company-console review route: 10 passed
company-console typecheck: PASS
company-console production build: PASS
Ruff changed-file gate: PASS
Alembic heads: m_021_report_generation_failures (single head)
Migration ownership/head/downgrade/drift: PASS
```

확장 reporting 디렉터리 전체 collection은 이번 변경과 무관한 기존 test helper 불일치로 중단됐다.
현재 소스와 HEAD 모두 `InMemoryReportingRepository`를 제공하지 않지만 legacy 테스트 3개가 이를
import한다. 이번 변경과 직접 연결된 SQL repository·worker·API·UI·교차 모듈 gate는 위와 같이 모두
통과했다.

### ControlProof 판정기 보정

최초 Run의 fault receipt는 source worker 시도 `[1, 2, 3]`을 정확히 기록했지만, ControlProof가 DLQ
메시지를 읽는 관찰 행위가 `ApproximateReceiveCount`를 4로 증가시켰다. 기존 adapter는 이 값을
`last_delivery_attempt`로 저장해 H03-A8과 E03-A2를 거짓 FAIL로 만들었다.

- RED 계약 테스트에서 DLQ 관찰 count 4가 worker attempt 4로 기록되는 문제를 재현했다.
- terminal failure의 `last_delivery_attempt`는 검증된 redrive topology의 source max receive count 3으로
  고정했다.
- DLQ 자체 관찰 횟수 4는 `dlq_observation_receive_count`로 분리해 원본 관찰 사실을 버리지 않는다.
- queue adapter·DLQ lineage·redrive·H03/E03 judge 회귀 28개가 통과했다.
- ControlProof 전체 회귀 249개와 Ruff 전체 검사가 통과했다.

이 보정은 부모 bundle을 다시 쓰지 않는다. 기존 FAIL은 당시 판정 결과로 불변 보존하며, 수정된
판정기와 WhyYou target commit을 사용하는 T085 child Run에서 새 결과를 만든다.

T085 preflight 직전에는 별도의 provenance 결함도 발견했다. target snapshot이 Alembic graph를 읽지
않고 migration 파일명의 사전식 마지막 값을 head로 사용해, 실제 DB와 source graph가
`m_021_report_generation_failures`인데도 `m_003_criterion_grounded_rag`를 기록했다.

- Python AST로 각 migration의 `revision`과 `down_revision`을 읽어 graph head를 계산하도록 변경했다.
- head가 없거나 둘 이상인 unmerged graph, 중복 revision과 해석 불가능한 값을 snapshot 실패로
  처리한다. 잘못된 값을 그럴듯한 버전으로 봉인하지 않는다.
- 파일명 순서와 graph 순서가 다른 RED fixture 및 unmerged graph 검사까지 포함해 13개 target snapshot
  관련 검사가 통과했고, 실제 WhyYou head가 `m_021_report_generation_failures`로 확인됐다.

## 2026-09-29 — 부모 연결 실제 스택 재시험 (T085)

### 시험 대상과 변경 고정점

- WhyYou는 개인 브랜치 `bosung/controlproof-h03-integration`의 `511ae9e`를 사용했다. `main`에는
  push하지 않았다.
- ControlProof는 DLQ 관찰 횟수와 실제 source delivery 횟수를 분리한 `fe89c58`, Alembic graph
  head를 계산하는 `6fee737`, 사람 actor 표기를 canonical 값으로 정규화한 `dd3ec0d`를 순서대로
  사용했다.
- 모든 child Run의 target version은
  `target-snapshot:sha256:fa4e235018335ee6806a2b5812bc3f783a7690adcaf837f920af9bbd232d1a83`이며,
  snapshot의 schema head는 `m_021_report_generation_failures`다.
- 실행환경은 `LOCAL_EMULATED`이고 실제 AWS와 외부 AI는 계속 `NOT_RUN`이다.

### H03 FAIL → PASS 계보

| 구분 | Run ID | 결과 | manifest SHA-256 | bundle 검증 |
|---|---|---|---|---|
| 최초 부모 | `60b19e5a-6693-427b-bf87-039e45181cfc` | FAIL | `40602160bcc9b6c534dcd0c582ec6dc39f2c5fe8b23455ba15760494d9193fec` | VERIFIED, 33 files |
| 보완 후 child | `3ff1c0c7-7937-4d0a-996c-de4d63f4f1af` | PASS | `567f36281c23a1fa081e6a2113d5099e13d3af54f0d9cb3c919db156f683d285` | VERIFIED, 35 files |

child는 부모 Run ID와 digest를 `retest-link.json`에 연결하며 부모 bundle은 다시 쓰지 않았다.
H03-A1~A9가 모두 PASS했다. 특히 단일 final-decision과 batch `최종합격`·`불합격` 세 경로가
모두 report 부재를 이유로 거부됐고 전후 효과가 동일했다. 실제 source delivery는 `[1, 2, 3]`,
API는 `failed`, 화면 projection은 `final_failed`, 운영자 DLQ locator는 존재했다. marker·worker 복구와
선택 메시지 redrive도 완료됐다.

### E03 FAIL → 보정된 PASS 계보

| 구분 | Run ID | 결과 | manifest SHA-256 | bundle 검증 |
|---|---|---|---|---|
| 최초 부모 | `e17e0af0-b46a-4022-93a4-a91a3247f16d` | FAIL | `d72dc8a9f63cb92a4c73a3db368b8463abf802536a947c7e2b475a6092300c5f` | VERIFIED, 23 files |
| 제품 보완 후 child | `5a7f09ff-d80f-4a7d-926c-2a522ad51bbb` | FAIL(E03-A7만) | `0d6381efe7e50a87bafd60a13e91c5287dfdfcbeab01952bf867b74c4b8b1590` | VERIFIED, 25 files |
| 판정 adapter 보정 후 grandchild | `ebeed35e-5779-4480-8d3b-e246a0bb72b6` | PASS | `ca38b91edcf4018be1f09f206b6b693aa599b5eebdcb2d8bef94dd526768247c` | VERIFIED, 25 files |

첫 child에서는 WhyYou의 동일-key 재전송 효과가 실제로 한 세트로 유지됐지만, 감사 DB의 raw actor
`company_user`를 ControlProof가 canonical `COMPANY_USER`와 다르다고 보아 E03-A7만 FAIL했다. 이는
제품의 중복 결정 결함이 아니라 판정 adapter의 표현 정규화 결함이었다. adapter가 actor 값을 대문자
underscore 형식으로 canonicalize하고 결측값은 `UNKNOWN`으로 보존하도록 고친 뒤, 기존 child를
덮어쓰지 않고 그 child를 부모로 하는 grandchild를 새로 생성했다.

최종 grandchild에서는 E03-A1/A2/A3/A4/A7/A8이 모두 PASS했다. 첫 요청과 replay의 stage assignment,
invitation `reviewed`, HumanReview ID, final-decision audit ID가 각각 같은 한 세트였고 actor도
`COMPANY_USER`였다. 장애 중 내구 효과는 0건, 복구 후 report·projection·processed marker는 정확히
한 논리 세트였으며 delivery attempt는 `[1, 2, 3]`이었다.

### 복구·잔여 큐와 판정 해석

- H03 child와 두 E03 child/grandchild 모두 Run state는 `COMPLETED`, 수동 정리 필요 여부는
  `false`였고 실행 세션의 environment restore는 성공했다.
- 최종 확인 시 `iep-reporting`과 `iep-reporting-dlq` 모두 visible 0건, in-flight 0건이었다.
- 보조 관찰값 `report_processing_recovery`는 marker 해제 직후, DLQ redrive 전에 제품 API를 읽기
  때문에 terminal failure를 보고 `FAILED`로 남는다. redrive 뒤 실제 report는 `ready`이고 canonical
  E03-A4와 restore 판정은 PASS다. 이 보조값을 제품 복구 실패로 확대 해석하지 않는다. 이름과 수집
  시점의 혼동 가능성은 Phase 9 문서·polish 후보로 남긴다.
- 각 manifest hash는 현재 bundle 파일 자체의 SHA-256이다. `verify`는 등록 파일의 누락·불일치·미등록
  파일이 없음을 부모와 모든 자식에서 다시 확인했다.

### T085 종료 gate

```text
ControlProof full pytest: 251 passed in 122.52s
ControlProof Ruff: All checks passed!
H03 parent/child bundle: VERIFIED (33/35 files)
E03 parent/child/grandchild bundle: VERIFIED (23/25/25 files)
LocalStack source/DLQ queue: visible 0, in-flight 0
```

따라서 최초 FAIL을 불변으로 보존하고, 직접 근거로 제품과 판정 경계를 보완한 뒤 부모 연결 PASS
재시험을 남기라는 T085 요구를 충족했다. 이는 Spec 002 전체 종료가 아니라 actual-stack
FAIL→PASS 계보 단계의 종료다.

## 2026-09-29 — 실제 스택 3-profile preflight gate (T080)

### 검증 대상과 고정된 식별자

- ControlProof branch/commit: `002-h03-e03-fault-expansion` / `3c4ce1e`
- WhyYou branch/commit: `bosung/controlproof-h03-integration` / `fd3e6f62888dfcc5b07a5ad0d0df094102ae6171`
- 두 checkout 모두 clean이며 WhyYou `main`은 사용하거나 변경하지 않았다.
- target: `whyyou-local`
- environment: `LOCAL_EMULATED`
- AWS deployment: `NOT_RUN`
- target snapshot digest: `target-snapshot:sha256:fbf21a4be3961305071c2039f2042f89dbdac23abb849c2521fd75548ec83e3d`
- OpenAPI digest: `1d23e1ae973672726ed3232fd83edd25ad06cd253990548c1dada1de609b952a`
- schema migration head: `m_003_criterion_grounded_rag`
- model fixture: `h03-report-v1` / `ce09b95403b34e1390502c90f5c5edc518ddf65d38c8ce881617a37cac6d16b1`
- reporting queue contract: `iep-reporting → iep-reporting-dlq`, visibility timeout 5초,
  max receive count 3

### 사전 점검 결과

아래 세 명령을 실제 PostgreSQL·LocalStack·WhyYou API·worker·company console이 실행 중인 상태에서
각각 수행했다.

```powershell
.\.venv\Scripts\python.exe -m engine.cli preflight H-03 --profile H03_DLQ_V2 --target whyyou-local --json
.\.venv\Scripts\python.exe -m engine.cli preflight E-03 --profile E03_BEFORE_V2 --target whyyou-local --json
.\.venv\Scripts\python.exe -m engine.cli preflight E-03 --profile E03_AFTER_V2 --target whyyou-local --json
```

결과:

| profile | fault variant | readiness | AWS | cloud unverified |
|---|---|---|---|---|
| `H03_DLQ_V2` | `BEFORE_RESULT_DURABLE` | `READY` | `NOT_RUN` | SQS/ECS/IAM/CloudWatch/network |
| `E03_BEFORE_V2` | `BEFORE_RESULT_DURABLE` | `READY` | `NOT_RUN` | SQS/ECS/IAM/CloudWatch/network |
| `E03_AFTER_V2` | `AFTER_RESULT_DURABLE_BEFORE_COMPLETION` | `READY` | `NOT_RUN` | SQS/ECS/IAM/CloudWatch/network |

모든 필수 capability가 `READY`였으며, 특히 runner와 WhyYou worker가 같은 fault/receipt 디렉터리를
사용한다는 것을 절대 경로 대신 SHA-256 지문으로 비교했다. 경로와 credential은 출력·기록하지 않았다.

### preflight 중 발견하고 수정한 runner 결함

최초 점검 구현은 `fault_hooks_enabled=true`와 runner 쪽 디렉터리 쓰기만 확인해, runner와 worker가 서로
다른 fault root를 보더라도 `READY`로 판정했다. 그 결과 H-03 실행 시 marker가 worker에 보이지 않아
`BOUNDARY_RECEIPT_MISSING`으로 수집기가 중단됐다. 이 시도는 verdict나 봉인 bundle을 만들지 않았으며,
제품 FAIL로 기록하지 않았다.

- WhyYou health는 실제 경로를 공개하지 않고 정규화된 fault root의 SHA-256 지문만 반환하도록 보완했다.
- ControlProof preflight는 자신의 지문과 대상 지문이 동일한지 확인하고, 다르면 모든 fault capability를
  `RUNNER_NOT_READY`로 차단하도록 보완했다.
- 잘못 처리된 합성 시도는 공식 seed teardown으로 제거했고, 해당 합성 event의 processed marker 1개도
  정확한 event/consumer/version 키로 제거했다. 관련 queue, outbox, report, session 잔여는 0건이다.
- 보완 회귀 결과: WhyYou scoped tests `58 passed`, ControlProof capability tests `9 passed`, 양쪽 Ruff 통과.

경로 지문을 맞춘 뒤의 첫 실행에서는 두 번째 runner 결함도 확인됐다. Outbox trigger 직후 비동기 worker가
receipt를 쓰기 전에 runner가 파일을 한 번만 읽어 `BOUNDARY_RECEIPT_MISSING`으로 종료했다. 이 시도도
verdict와 봉인 bundle을 만들기 전 중단됐으며, 합성 seed와 정확한 processed marker를 다시 제거했다.
H-03 DLQ와 E-03 BEFORE는 이제 scenario snapshot의 60초 deadline과 2초 poll 간격만 사용해 boundary
receipt를 기다린다. 지연 receipt RED 테스트를 추가한 뒤 관련 H-03/E-03 BEFORE/AFTER 통합 테스트
`16 passed`와 Ruff 통과를 확인했다.

이 결함을 보완하고 API를 최신 코드로 재기동한 뒤 위 세 preflight가 모두 `READY`가 된 결과만 T080
승인 근거로 사용한다. 실제 최초 봉인 Run은 T081에서 별도로 생성한다.

## 2026-09-29 — 실제 스택 최초 3-profile 봉인 실행 (T081)

### 실행 경계

- ControlProof branch/commit: `002-h03-e03-fault-expansion` / `d25083f`
- WhyYou branch/commit: `bosung/controlproof-h03-integration` /
  `fd3e6f62888dfcc5b07a5ad0d0df094102ae6171`
- WhyYou 보호 로직을 수정하기 전에 세 profile을 각각 새 Run으로 실행했다. WhyYou `main`은 사용하거나
  변경하지 않았다.
- 환경은 `LOCAL_EMULATED`, AWS는 `NOT_RUN`이고 외부 AI 호출은 금지한 상태다.
- 각 Run은 verdict와 관계없이 필수 restore를 수행하고 원본 bundle을 봉인했다. 이후 수정·재시험은
  반드시 새 child Run으로 남기며 아래 최초 결과를 덮어쓰지 않는다.

### 최초 실행 결과

| profile | Run ID | verdict | FAIL assertions | INCONCLUSIVE | restore | bundle verify | `manifest.json` SHA-256 |
|---|---|---|---|---|---|---|---|
| `H03_DLQ_V2` | `60b19e5a-6693-427b-bf87-039e45181cfc` | `FAIL` | `H03-A2`, `H03-A5`, `H03-A7`, `H03-A8`, `H03-A9` | 없음 | `SUCCEEDED` | `VERIFIED` (33 files) | `40602160bcc9b6c534dcd0c582ec6dc39f2c5fe8b23455ba15760494d9193fec` |
| `E03_BEFORE_V2` | `e17e0af0-b46a-4022-93a4-a91a3247f16d` | `FAIL` | `E03-A2`, `E03-A7` | 없음 | `SUCCEEDED` | `VERIFIED` (23 files) | `d72dc8a9f63cb92a4c73a3db368b8463abf802536a947c7e2b475a6092300c5f` |
| `E03_AFTER_V2` | `9251db5f-42a2-490d-93be-a155f25fef72` | `PASS` | 없음 | 없음 | `SUCCEEDED` | `VERIFIED` (19 files) | `69c289eebf47c824bf5b0d13a473df7403e88bd4301de9febc7301e14956fe28` |

세 bundle 모두 verifier가 필수 파일의 누락·digest 불일치·미등록 파일을 찾지 않았다. 실행 종료 후
source queue와 DLQ의 visible/not-visible message 수는 모두 0이었다.

### 제품에서 직접 확인된 결함

- H03-A7: 정상 단일 최종결정 API는 리포트 부재를 이유로 거부했지만, 일괄 단계 이동의 `최종합격`과
  `불합격` 경로는 모두 요청을 수락하고 상태 효과를 변경했다. 따라서 T082의 batch 보호 보완이
  필요하다.
- H03-A9 및 H03-A2: DLQ와 운영자 locator는 확인됐지만 제품 API 상태는 계속 `queued`였다. 회사 화면
  projection만 `final_failed`로 해석하는 것은 대상 시스템이 최종 실패를 영속·공개했다는 증명이
  아니므로, 실패 상태의 저장/API/UI 전달을 하나의 additive 설계로 보완해야 한다.
- E03-A7: 첫 사람 결정은 수락됐지만 동일한 `Idempotency-Key`와 동일 본문 재전송은 동등한 성공으로
  재현되지 않았고 대상 idempotency도 확인되지 않았다. 같은 논리 명령을 안정적으로 소유·재생하는
  application service가 필요하다.

### 제품 결함과 분리한 ControlProof 판정기 결함

- H03-A8과 E03-A2의 실제 fault receipt는 정확히 `[1, 2, 3]`이었고 같은 원 사건의 DLQ 건도
  `PRESENT`였다. 그러나 DLQ에서 증적을 읽는 동작 자체가 SQS `ApproximateReceiveCount`를 4로 만든
  값을 `last_delivery_attempt`로 사용해 두 assertion을 FAIL 처리했다.
- `maxReceiveCount=3`이 의미하는 것은 source worker의 처리 시도 3회다. DLQ 증적 조회 횟수는 업무 처리
  시도가 아니므로 이 값과 섞으면 안 된다. 최초 bundle의 FAIL은 불변으로 보존하고, adapter가 처리
  receipt 시계열을 terminal 처리 시도와 연결하도록 RED 테스트 후 수정한 다음 child retest에서만 새
  결과를 만든다.

### 안전 복구 확인

- 세 Run 모두 marker 비활성화와 worker health 확인을 포함한 `environment_restore=SUCCEEDED`였다.
- H-03과 E-03 BEFORE의 선택된 DLQ 메시지는 send-before-delete 순서로 source queue에 redrive됐다.
  H-03과 E-03 BEFORE의 recovery poll은 `TIMEOUT`이었지만, 후속 effect snapshot에는 reporting 효과가
  한 논리 세트로 관찰됐고 최종 queue 잔여도 0이었다. 이는 제품 assertion과 별도로 runner의 복구 완료
  관찰 조건을 후속 점검할 항목으로 남긴다.
- E-03 AFTER는 commit 후 첫 ack 생략, delivery attempt 2의 processed-message short circuit,
  `handler_skipped=true`, `acknowledged=true`, 전후 reporting effect 불변과 예상 밖 DLQ 부재를 모두
  확인해 네 assertion이 전부 PASS했다.

## 2026-09-28 — User Story 6 결정론적 봉인 실행 기반 (T072~T079)

### 이번 단계에서 고정한 의미

- E-03은 `--profile` 없이 BEFORE/AFTER를 추정하지 않는다. H-03의 profile 생략은 기존
  `H03_MINIMAL_V1` 동작으로 남겨 Spec 001 호환성을 유지한다.
- 세 v2 profile은 같은 bundle 봉인기를 사용하지만 assertion과 verdict를 합치지 않는다. 각 Run은
  선택한 profile의 assertion만 평가하고 다른 E-03 variant는 `remaining_variant_coverage`로만 표시한다.
- `LOCAL_EMULATED` 결과의 AWS 상태는 항상 `NOT_RUN`이고, 결과의 구조화된 주장 범위는
  `EXECUTED_SCENARIO_AND_EVIDENCE_ONLY`다. 사람용 출력에는 법적 준수 전체를 인증하거나 보증하지
  않는다는 문구를 항상 포함한다.
- 재시험은 부모의 scenario/profile/fault를 상속하고 새 Run ID를 사용한다. target·environment·queue
  digest 차이를 기록하며, 부모 manifest와 원 artifact digest를 자식 bundle에서 검증한다. 부모가
  `RESTORE_FAILED`이거나 수동 정리가 필요하면 재시험을 시작하지 않는다.

### 구현 결과

- 공통 Spec 002 봉인 실행기가 H03 DLQ, E03 BEFORE, E03 AFTER slice를 canonical Run·Judgement·Evidence
  Bundle로 변환한다. 환경·queue·전달·효과·최종 실패·redrive 기록과 profile별 필수 EV/EV2 연결을
  생성한 뒤 manifest를 봉인한다.
- CLI에 `--profile` dispatch를 추가하되 outer envelope는 `controlproof.cli.v1`을 유지했다. `preflight`,
  `run`, `show`, `verify`, `retest`가 profile·fault·적용/잔여 assertion·AWS 미검증 범위를 additive하게
  출력하고 기존 exit code 0~6의 의미를 보존한다.
- 결과 projection은 실제 DLQ route, 결정 path coverage, 전달 계보, effect digest 차이, 복구 상태와
  독립 scenario/profile verdict를 노출한다. message body·receipt handle·원 DB row는 표시하지 않는다.
- 재시험 diff에 execution profile, fault, environment, queue topology를 추가하고, 부모 artifact와 bundle
  digest를 cross-Run reference로 연결했다. 부모 변조 시 자식 verify도 실패한다.

### RED와 GREEN 근거

최초 RED gate는 12건 실패했다. 기존 CLI가 `--profile`을 인식하지 않았고 세 v2 executor가
`RUNNER_NOT_READY`로 봉인 실행을 차단했으며, 결과 projection과 재시험에 v2 필드가 없었기 때문이다.

최종 T072~T075 gate:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/contract/test_cli_profiles_v2.py tests/contract/test_presentation_spec002.py tests/integration/test_spec002_retest_lineage.py tests/integration/test_spec002_verdict_matrix.py tests/integration/test_h03_decision_paths.py -q
```

결과:

```text
16 passed in 10.50s
```

ControlProof 전체 회귀와 정적 검사:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest -q
```

결과:

```text
All checks passed!
245 passed in 165.45s (0:02:45)
```

### 아직 실행하지 않은 actual-stack gate

- 이 기록은 fake adapter를 사용한 결정론적 세 profile 봉인·판정·재시험 계약 결과다.
- Docker/LocalStack·PostgreSQL·WhyYou API/worker/company console을 대상으로 하는 T080 preflight와
  T081 최초 세 Run은 깨끗한 양쪽 개인 브랜치에서 별도로 실행한다.
- 실제 최초 Run의 FAIL을 보기 전에는 T082~T084의 WhyYou 보호조치 코드를 수정하지 않는다.
- WhyYou 제품 코드는 이 단계에서 변경하지 않았다.

## 2026-09-28 — User Story 4: 저장 후 ack 전 장애와 중복 억제 (T053~T063)

### 이번 단계에서 고정한 의미

- `AFTER_RESULT_DURABLE_BEFORE_COMPLETION`은 handler와 `processed_messages` 기록이 같은 DB
  transaction으로 commit된 뒤, SQS acknowledge 직전에만 발동한다.
- 로컬·test 전용 marker는 첫 전달의 ack만 한 번 생략한다. worker는 이미 commit된 transaction을
  rollback하거나 명시적으로 retry하지 않는다. 실제 queue visibility 만료로 재전달된 메시지는 기존
  processed-message 분기에서 handler를 건너뛰고 ack한다.
- AFTER 경계 영수증 하나만으로 PASS하지 않는다. 경계 직후 reporting 효과, 재전달의 sanitized
  duplicate-ack 영수증, 재전달 종료 뒤 효과와 DLQ 부재를 서로 독립적으로 읽는다.
- commit 직후와 최종 snapshot 모두 논리 report 1건, 중복 없는 projection 집합, 원 event/version의
  processed key 1건이어야 하고 두 snapshot의 canonical digest가 같아야 한다.
- 경계가 관찰되지 않으면 E03-A1/A5/A6/A8은 제품 PASS나 FAIL로 추정하지 않고 INCONCLUSIVE다.
  경계가 관찰된 뒤 handler 생략 증적이 없거나 업무 효과가 달라지면 FAIL이다. AFTER 흐름에서 DLQ는
  기대 결과가 아니므로 일치 DLQ 건이 나타나면 E03-A1과 A8의 직접 FAIL이다.

### 구현 결과

- WhyYou 개인 브랜치에 기본값이 무동작인 `DeliveryLifecycleObserver`를 추가했다. 실제 순서는
  `handler → processed record → DB commit → AFTER hook → SQS acknowledge`로 고정됐고, hook은
  local/test에서 유효한 AFTER marker를 원자적으로 한 번 소비한 경우에만 ack를 생략한다.
- 재전달이 processed-message short circuit에 들어오면 handler를 다시 호출하지 않고 ack한 뒤,
  run·session·event·attempt·consumer와 `handler_skipped`/`acknowledged`만 담은 영수증을 append+fsync한다.
  지원자 payload나 이름·이메일은 영수증에 기록하지 않는다.
- `WhyYouFaultAdapter`는 BEFORE와 AFTER marker를 별도로 생성하고, marker 작성 결과를 경계 증적으로
  오인하지 않는다. boundary reader는 run·session·event·variant·boundary·one-shot을 검증하며,
  duplicate reader는 같은 event의 processed-branch 영수증만 수용한다.
- `E03_AFTER_V2`는 E03-A1/A5/A6/A8만 소유하고 EV2-01~04·09·10·12, 60초 boundary/duplicate
  기한과 `terminal DLQ = ABSENT`를 선언한다. BEFORE profile의 DLQ/redrive 기대를 공유하지 않는다.
- `E03AfterExecutor.collect_us4`는 환경·topology → 합성 대상 → AFTER marker → 원 event → boundary →
  commit 직후 효과 → duplicate ack → 최종 효과 → DLQ 부재 → restore 순으로 독립 실행한다.
- profile registry에는 `E03_AFTER_V2`를 전용 executor로 등록했다. 다만 Phase 8의 공통 봉인 bundle
  orchestration 전까지 CLI preflight와 `execute`는 명시적으로 `RUNNER_NOT_READY`다. US4 slice 통과를
  정식 봉인 Run 완료로 표시하지 않는다.

### US4 gate(GREEN)

WhyYou 개인 브랜치의 worker 순서·one-shot ack 생략·재전달 short circuit·fsync 영수증 gate:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/integration/test_worker_delivery.py tests/unit/runtime/test_controlproof_reporting_fault.py -q
..\.venv\Scripts\python.exe -m ruff check .
```

결과:

```text
32 passed, 1 warning in 7.49s
All checks passed!
```

ControlProof AFTER adapter·judge·profile integration gate:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/contract/test_whyyou_after_commit_fault.py tests/unit/test_judge_e03_after.py tests/integration/test_e03_after.py -q
```

결과:

```text
13 passed in 0.86s
```

ControlProof 전체 회귀와 정적 검사:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
```

결과:

```text
218 passed in 145.84s (0:02:25)
All checks passed!
```

### 검증 제한과 아직 실행하지 않은 것

- WhyYou 저장소의 전체 legacy test collection은 이번 변경 파일에 도달하기 전에, 현재 브랜치에서
  이미 제거된 여러 `InMemory*` test helper와 `runtime.local_*` 모듈을 참조하는 44개 import 오류로
  중단된다. 이번 변경 범위의 32개 테스트와 저장소 전체 Ruff는 통과했지만, 이 기존 test-suite
  정합성 문제는 별도 정리가 필요하다.
- Docker/LocalStack·PostgreSQL 실제 대상에서 visibility timeout을 기다리는 최초 AFTER Run이나 봉인된
  제품 verdict는 아직 만들지 않았다. 이는 Phase 8 actual-stack gate의 책임이다.
- 실제 AWS와 외부 AI는 계속 `NOT_RUN`이며, 로컬 one-shot hook은 production/staging에서 활성화가
  거부된다.
- WhyYou 변경은 `bosung/controlproof-h03-integration` 개인 브랜치에만 있으며 main에는 반영하지 않았다.

## 2026-09-28 — User Story 5: 같은 결정 재전송과 최종 효과 검증 (T064~T071)

### 이번 단계에서 고정한 의미

- 같은 결정인지는 서버가 매번 새로 돌려주는 응답 ID가 아니라 `초대 건 + 목표 단계 +
  Idempotency-Key digest + canonical request-body digest`로 식별한다. 원본 Idempotency-Key는 HTTP
  요청 헤더에만 사용하며 ControlProof 결과·로그·bundle에는 저장하지 않는다.
- 첫 요청의 처리는 완료됐지만 응답만 유실될 수 있다. 이 경우에도 동일 key·동일 body 재전송을 같은
  논리 결정으로 연결하며, 첫 응답이 없다는 이유만으로 곧바로 FAIL 또는 PASS로 추정하지 않는다.
- HTTP 응답이 동일하다는 사실만으로 WhyYou의 중복 억제를 인정하지 않는다. 첫 요청 뒤와 재전송 뒤의
  허용 목록 DB 효과를 각각 읽어 비교하고, 정확히 한 번의 단계 배정·reviewed 상태·사람 검토·
  final-decision audit가 유지돼야 E03-A7이 PASS다.
- 최종 결정을 만든 주체는 `COMPANY_USER`여야 한다. AI 점수와 후보자 개인정보는 이 판단에 사용하지
  않으며 effect projection에도 포함하지 않는다.
- key 또는 canonical body가 바뀌면 다른 논리 요청이므로 replay 동등성을 주장하지 않는다. 대상이 key를
  무시해 중복 row를 만들거나 상태가 달라지면 E03-A7은 FAIL이다.

### 구현 결과

- `WhyYouDecisionAdapter`가 요청 전에 canonical body와 digest, 안정적인 logical-decision ID를 만들도록
  확장됐다. 첫 응답 유실도 sanitized identity와 함께 보존하며, 동일 요청 비교기는 대상 시스템의
  idempotency 성공을 응답만 보고 주장하지 않는다.
- `WhyYouEffectAdapter`는 final-decision에 한정된 actor와 request ID를 별도로 투영한다. 실제 DB에서
  회사 사용자 연결이 없으면 `COMPANY_USER`로 가정하지 않고 `UNKNOWN`으로 남긴다.
- E03-A7 judge는 요청 identity와 재전송 수락 여부뿐 아니라 첫 요청·재전송 뒤의 allowlisted effect
  집합을 비교한다. 단계 배정, reviewed 상태, HumanReview, final-decision audit가 각각 정확히 한 번이고
  모두 사람이 만든 결정일 때만 PASS한다. 효과를 읽을 수 없으면 FAIL을 추측하지 않고 INCONCLUSIVE다.
- `E03_BEFORE_V2` 수집 흐름은 기존 A1/A2/A3/A4/A8에 A7을 연결했다. reporting 복구가 확인된 뒤에만
  같은 사람 결정을 두 번 전송하고, 두 시점의 DB 효과를 독립적으로 읽는다. 최종 assertion 순서는
  `A1 → A2 → A3 → A4 → A7 → A8`로 고정했다.
- profile registry에 `E03_BEFORE_V2` 전용 executor를 등록했고 전체 v2 adapter composition에
  `hiring.final_decision.replay:v1`을 추가했다. 단, Phase 8의 공통 봉인 bundle orchestration 전까지
  CLI preflight와 `execute`는 계속 `RUNNER_NOT_READY`이며 slice 수집 결과를 정식 Run 완료로 오인하지
  않는다.

### RED와 GREEN 근거

최초 RED gate에서는 아직 존재하지 않던 replay 비교기와 E03-A7 judge import에서 collection이 실패했다.
이는 새 테스트가 기존 구현을 우연히 통과하지 않았다는 근거다.

최종 User Story 5 gate:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/contract/test_whyyou_decision_replay.py tests/contract/test_whyyou_adapter_v2_composition.py tests/contract/test_profile_registry_v2.py tests/unit/test_judge_e03_decision.py tests/integration/test_e03_decision_replay.py tests/integration/test_e03_before.py -q
```

결과:

```text
15 passed in 1.89s
```

ControlProof 전체 회귀와 정적 검사:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
```

결과:

```text
232 passed in 156.87s (0:02:36)
All checks passed!
```

### 검증 제한과 다음 단계 경계

- 이번 단계는 ControlProof의 재전송·효과 비교 능력을 구현한 것이며 WhyYou 제품 코드는 변경하지
  않았다. 실제 WhyYou가 Idempotency-Key를 무시한다면 최초 봉인 Run은 그 사실을 FAIL로 보존해야 한다.
- 제품 결함 수정은 실패 증적을 먼저 확보하는 Phase 8의 T084 이후에만 허용된다. 테스트를 통과시키기
  위해 사전에 WhyYou 동작을 바꾸지 않는다.
- Docker/LocalStack·PostgreSQL 대상의 정식 E03 BEFORE Run, bundle 검증, verdict 봉인은 아직 실행하지
  않았다. 이는 T072~T085에서 공통 runner·bundle을 완성한 뒤 수행한다.
- 실제 AWS와 외부 AI는 계속 `NOT_RUN`이며 로컬 queue·DB 계약 결과를 AWS 검증으로 확대하지 않는다.
