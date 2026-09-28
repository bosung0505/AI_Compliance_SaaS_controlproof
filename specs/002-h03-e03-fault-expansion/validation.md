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
- WhyYou 제품 코드는 이 단계에서 변경하지 않았다.
