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
