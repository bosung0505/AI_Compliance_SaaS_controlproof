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
