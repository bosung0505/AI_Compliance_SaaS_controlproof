# Implementation Plan: 실행·증적 기본 모델과 H-03 최소 수직 흐름

**Branch**: `001-execution-evidence-h03` | **Date**: 2026-09-24 | **Spec**: [spec.md](./spec.md)

**Input**: [Product Brief](../../docs/product/ControlProof_MVP_Product_Brief.md), [결정 기록](../../docs/product/ControlProof_MVP_Decision_Log.md), [Constitution](../../.specify/memory/constitution.md), WhyYou 공개 저장소의 현재 reporting 구현

## Summary

첫 수직 흐름은 합성 지원자 한 명에 대해 WhyYou의 `report.generation_requested` 처리만 결정론적으로 실패시키고, 리포트 미준비 상태의 화면·API 표현과 회사 사용자의 최종결정 시도, 시도 전후 상태, 자동결정 부재, 장애 해제와 복구를 한 Run으로 수집한다. ControlProof는 시나리오 실행과 WhyYou 연결을 분리한 어댑터 구조, 명시적 Run 생명주기, 차원이 완전한 Observation, 저장 전 마스킹과 SHA-256을 적용한 파일 기반 Evidence Bundle, 증적만 사용하는 판정 엔진을 제공한다.

WhyYou 현재 구현을 기준으로 한 연결 지점은 다음과 같다.

- reporting queue routing과 핸들러: `backend/src/interview_evidence/runtime/worker.py`
- 리포트 조회: `GET /v1/interview-sessions/{session_id}/report`; 리포트가 없으면 `202 {status: queued}`
- 최종결정: `POST /v1/invitations/{invitation_id}/final-decisions`; 리포트를 먼저 조회하므로 없으면 쓰기 전에 거부됨
- 담당자 화면: `apps/company-console/src/app/routeAdapters.tsx`; `202` 동안 2초 간격으로 재조회하며 현재는 생성 중 문구를 계속 표시함
- queue 재시도: reporting 이벤트는 `TimeoutError` 시 재시도되며 첫 지연은 15초, reporting max receive count는 12회임

현재 WhyYou가 H-03을 PASS한다고 가정하지 않는다. 최초 Run은 실제 동작대로 PASS·FAIL·INCONCLUSIVE 중 하나를 생성하며, WhyYou 보호조치 수정은 최초 결과가 보존된 뒤 별도 변경과 자식 Run 재시험으로 수행한다.

## Technical Context

**Language/Version**: Python 3.12; WhyYou 연결 대상은 Python/FastAPI 백엔드와 React/TypeScript 회사 콘솔

**Primary Dependencies**: Pydantic 2.x, PyYAML 6.x, HTTPX 0.27+, Jinja2 3.x, Python Playwright 1.55+, SQLAlchemy 2.x와 Psycopg 3.x(WhyYou 상태 seed·제한 조회), 표준 라이브러리 `hashlib`, `json`, `pathlib`, `uuid`, `fcntl/msvcrt` 호환 잠금

**Storage**: ControlProof는 `.controlproof/runs/{run_id}/`의 append-only JSONL 및 JSON manifest와 원본 artifact 파일을 사용한다. WhyYou 시험 데이터는 기존 PostgreSQL·SQS/LocalStack·로컬 object storage를 사용하며 운영 데이터는 사용하지 않는다.

**Testing**: pytest 단위·계약·통합 테스트, HTTPX `MockTransport`, Playwright Chromium 화면 검증, Ruff 정적 검사

**Target Platform**: Windows 개발 호스트에서 실행되는 Python CLI; Docker Compose 기반 WhyYou 로컬/격리 테스트 환경과 Linux 컨테이너

**Project Type**: 단일 Python 검증 CLI/라이브러리 + WhyYou 전용 adapter. 완성된 웹 대시보드는 Spec 001 범위 밖이다.

**Performance Goals**: 준비된 로컬 환경에서 H-03 한 Run을 복구 포함 5분 이내 완료한다. 상태 관찰은 2초 간격, 장애 구간 판정 창은 30초, 복구 완료 기한은 120초로 기본 설정하되 시나리오 버전에 고정한다.

**Constraints**: 실제 개인정보 금지, 테스트 환경에서만 장애 주입, 외부 LLM은 고정 대역, 증적 저장 전 마스킹, 장애 적용 후 항상 복구, 동일 target+subject 동시 장애 Run 금지, 필수 증적 공백 시 PASS 금지, 최초 결과 불변

**Scale/Scope**: H-03 한 시나리오, 한 WhyYou 환경, 한 합성 지원자, 한 회사 사용자, 한 reporting 장애 종류, 6개 assertion, 9종 필수 증적. 재시도 소진·DLQ·E-03 멱등성은 Spec 002로 미룬다.

## Constitution Check

*GATE: Phase 0 시작 전과 Phase 1 설계 후 모두 통과해야 한다.*

| 원칙 | 설계상 확인 | 상태 |
|---|---|---|
| I. 판정은 증적에서만 나온다 | assertion은 Observation과 EvidenceArtifact ID를 필수로 참조하고, 무결성 또는 필수 증적 실패 시 PASS를 금지한다. | PASS |
| II. 대상·준비·결과 분리 | capability 존재, runner 준비, 접근 가능성을 Readiness에서 별도로 계산한다. 훅 부재는 `RUNNER_NOT_READY`다. | PASS |
| III. 사람의 최종 결정 권한 | ControlProof는 회사 사용자 자격으로 정상 endpoint의 거부 여부만 시험하고 결정을 대신 만들지 않는다. 점수 임계값을 사용하지 않는다. | PASS |
| IV. 시나리오/어댑터 분리 | H-03 YAML은 의도·step·assertion을, WhyYou adapter는 API·DB·브라우저·fault 연결을 소유한다. | PASS |
| V. 격리·결정론·복구 | 합성 데이터, 테스트 전용 만료형 fault marker, LLM 대역, finally 복구와 환경 lock을 사용한다. | PASS |
| VI. 불변 결과·재시험 계보 | 완료 Run 디렉터리는 봉인하고 자식 Run은 `parent_run_id`로 연결한다. | PASS |
| VII. 명세-증적 추적성 | FR/AC → scenario step/assertion → task/test → observation/evidence/verdict ID를 보존한다. | PASS |

### Phase 1 재확인

데이터 모델은 Run 상태와 Verdict를 분리하고, 계약은 저장 전 마스킹·해시, target-scoped lock, 강제 복구, 불변 bundle을 명시한다. WhyYou test hook은 기본 비활성·테스트 profile·세션 allowlist·TTL을 모두 요구한다. 설계 후 위반 사항은 없으며 Complexity Tracking 예외도 없다.

## Architectural Decisions

### 1. 동기식 오케스트레이터와 명시적 단계

Spec 001은 별도 ControlProof 작업 큐를 만들지 않는다. `RunOrchestrator`가 readiness → lock → seed → baseline → inject → effect 확인 → 화면/API 관찰 → decision 시도 → 사후 상태 → 자동결정 부재 → restore → recovered 확인 → judgement 순서로 실행한다. 각 단계 직후 관찰과 증적을 내구 저장하여 프로세스 중단 시에도 확보된 사실을 잃지 않는다.

### 2. 파일 기반 Evidence Bundle

2주 MVP의 단일 실행기에는 별도 DB보다 파일 bundle이 더 작고 내보내기·검토·불변성 확인이 쉽다. 구조화 검색이 필요한 종합 UI는 이후 index를 추가하되, canonical record는 Run 디렉터리다. 파일은 임시 경로에 저장하고 `fsync` 후 atomic rename한다. 완료 시 manifest에 전체 파일 해시를 기록하고 sealed 상태로 전환한다.

### 3. WhyYou의 결정론적 테스트 전용 장애 훅

장애는 reporting worker의 `report.generation_requested` 처리 시작점에서 특정 `interview_session_id`에만 `TimeoutError`를 발생시키는 파일 marker 방식으로 정한다. ControlProof adapter가 공유된 test-only fault root에 TTL이 있는 marker를 atomic하게 생성·삭제한다. WhyYou 훅은 다음 조건을 모두 만족할 때만 marker를 읽는다.

- `CONTROLPROOF_TEST_HOOKS_ENABLED=true`
- runtime environment가 `local` 또는 명시적 `test`
- marker의 run/session/fault type이 스키마와 allowlist에 일치
- marker가 만료되지 않음

발동 시 worker는 `CONTROLPROOF_FAULT_TRIGGERED` 구조화 로그를 남긴 뒤 기존 재시도 경로로 진입한다. production profile에서 훅 활성화 요청은 시작 단계에서 실패해야 한다. 첫 Spec은 재시도 소진과 DLQ를 기다리지 않는다.

### 4. 실제 제품 동작은 어댑터로 읽고 판정을 미리 정하지 않는다

현재 리포트 미존재 API는 `202 queued`, 콘솔은 “최종 리포트를 생성하고 있습니다.”를 계속 표시한다. H03-A2는 30초 관찰 창 안에 ready와 구별되는 상태뿐 아니라 최종 실패/장기 지연이 드러나는지도 평가한다. 단순 `queued` 반복은 원시 사실로 보존하며 Spec의 규칙대로 FAIL 여부를 계산한다.

최종결정은 동일한 회사 사용자 bearer와 공개된 정상 endpoint로 시도한다. 화면에 버튼이 없어 API를 호출하더라도 권한·route·payload는 실제 정상 경로와 동일해야 하며, 별도 관리자 DB write는 금지한다. 응답 status/detail과 전후 DB/API 상태가 함께 A3/A4의 근거가 된다.

### 5. seed와 trigger 분리

H-03 seed는 리포트가 없는 completed session, final video, 최종 turn·transcript, 회사 사용자, 채용 단계까지 준비한다. `report.generation_requested` 이벤트 발행은 장애 marker가 적용된 뒤 별도 trigger step에서 수행한다. 기존 `state_seed.py`의 ready report fixture는 E 계열 기준선용으로 남기고 H-03에 재사용하지 않는다.

### 6. 판정 우선순위

직접 관찰한 보호조치 위반은 finding으로 보존한다. 다만 Run이 `ABORTED`/`RESTORE_FAILED`이거나 A1/A6을 평가할 수 없으면 전체 verdict는 `INCONCLUSIVE`이고 발견된 위험을 summary에 병기한다. 정상 완료 Run에서는 직접 FAIL이 하나라도 있으면 전체 FAIL, FAIL이 없고 필수 평가 공백이 있으면 INCONCLUSIVE, 나머지만 PASS다.

## Observation and Timing Policy

- 기본 polling 간격: 2초
- 장애 효과 확인: worker 발동 로그와 `report absent/queued`가 모두 관찰될 때 성립
- 담당자 표시 관찰 창: fault 발동 확인 시점부터 30초
- 안정화 조건: 같은 의미의 상태가 3회 연속 관찰되고 최소 4초 이상 지속
- 자동결정 부재 창: decision 거부 뒤 10초 동안 decision history와 3개 상태 필드를 2초 간격으로 관찰
- 복구 기한: marker 제거 후 120초 안에 report `ready|partial` 도달 및 worker 재처리 확인
- 원시 polling 결과: 모두 JSONL로 보존
- 판정 입력: 관찰 창의 마지막 안정 상태와 필요한 전후 비교값

이 수치는 `scenario_version`에 포함된다. 변경하면 새 scenario version으로만 적용하며 과거 Run 해석을 바꾸지 않는다.

## Project Structure

### Documentation (this feature)

```text
specs/001-execution-evidence-h03/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── controlproof-cli.md
│   ├── evidence-bundle.md
│   └── whyyou-adapter.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # $speckit-tasks 단계에서 생성
```

### Source Code (repository root)

```text
engine/
├── __init__.py
├── cli.py                   # preflight/run/show/verify/retest 명령
├── models.py                # 공통 enum·entity·식별 차원
├── lifecycle.py             # Run 상태 전이와 target lock
├── readiness.py             # capability/runner/access 평가
├── scenario.py              # YAML load·version snapshot·validation
├── runner.py                # 단계 오케스트레이션과 강제 복구
├── observations.py          # polling, 존재 상태, 안정화, 충돌 판정
├── evidence.py              # redact → persist → hash → manifest
├── judge.py                 # assertion 및 전체 verdict
└── adapters/
    ├── __init__.py
    ├── base.py              # 서비스 중립 Protocol
    └── whyyou/
        ├── __init__.py
        ├── client.py        # 회사 API·인증·버전
        ├── capability.py    # endpoint/hook/access 점검
        ├── seed.py          # H-03 pending-report fixture
        ├── fault.py         # marker apply/probe/restore
        ├── state.py         # baseline/post/recovered snapshot
        └── browser.py       # 담당자 화면 캡처와 표시문구 추출

scenarios/
└── H-03.yaml                # Spec 001 최소형으로 축소·버전 상승

seeds/
├── __init__.py
├── state_seed.py            # E 계열 ready-report fixture 유지
└── h03_pending_report.py    # H-03 전용 fixture와 teardown

tests/
├── unit/
│   ├── test_models.py
│   ├── test_lifecycle.py
│   ├── test_observations.py
│   ├── test_evidence.py
│   └── test_judge_h03.py
├── contract/
│   ├── test_scenario_contract.py
│   ├── test_bundle_contract.py
│   └── test_whyyou_adapter_contract.py
├── integration/
│   ├── test_h03_orchestration.py
│   └── test_h03_restore_failure.py
└── fixtures/
    ├── observations/
    └── whyyou/
```

WhyYou의 테스트 전용 변경은 WhyYou 저장소에서 별도 커밋으로 관리한다. ControlProof 저장소에 타 제품 코드를 복사하지 않으며, `contracts/whyyou-adapter.md`가 양쪽의 경계를 정의한다.

**Structure Decision**: 기존 skeleton의 `engine`, `scenarios`, `seeds`를 유지하면서 `engine/adapters/whyyou`를 추가한다. 현재 코드의 잘못된 충돌 key, readiness 오분류, 부족한 Run lifecycle은 호환 shim으로 감추지 않고 공통 모델에서 먼저 교정한다. Spec 001에는 웹 프론트엔드를 추가하지 않는다.

## Requirement-to-Component Traceability

| 요구사항 묶음 | 주요 구현 | 계약/시험 |
|---|---|---|
| FR-001~006 | `scenario.py`, `readiness.py`, capability adapter | scenario/adapter contract tests |
| FR-007~014 | `models.py`, `lifecycle.py`, `runner.py` | lifecycle unit, CLI contract |
| FR-015~020 | `fault.py`, target lock, restore guard | fault adapter contract, restore-failure integration |
| FR-021~026 | `observations.py`, dimension-complete model | observation/conflict unit tests |
| FR-027~034 | WhyYou API/browser/state adapters | H-03 orchestration integration |
| FR-035~041 | `evidence.py`, bundle manifest | evidence-bundle contract, tamper tests |
| FR-042~050 | `judge.py` | normal/fail/missing/conflict/abort fixtures |
| FR-051~054 | `retest`, sealed parent bundle | retest lineage tests |

## Implementation Sequence

1. 공통 enum/entity와 lifecycle/observation identity를 고치고 기존 테스트를 새 계약으로 전환한다.
2. Evidence Bundle writer와 마스킹·해시·검증을 만든다.
3. H-03 YAML을 6개 assertion/9종 evidence/복구 단계에 맞게 교체한다.
4. WhyYou capability/state/seed adapter를 구현하고 read-only contract tests를 통과시킨다.
5. WhyYou 저장소에 test-only reporting fault hook을 별도 커밋으로 추가하고 production-disable test를 만든다.
6. `RunOrchestrator`와 CLI를 연결해 fake adapter E2E를 먼저 통과시킨다.
7. 격리된 WhyYou 로컬 스택에서 최초 H-03 Run을 수행하고 원본 결과를 봉인한다.
8. 실제 FAIL이 확인되고 수정이 승인된 경우에만 WhyYou 보호조치를 수정하고 자식 Run으로 재시험한다.

## Migration and Compatibility

- 기존 `Verdict` 네 값은 유지하되 `NOT_RUN`을 생성된 Run verdict로 저장하지 못하게 검증한다.
- `Observation`에는 `subject_ref`, `phase`, `step_id`, `attempt`, `presence`, `source_ref`를 필수 추가한다. 기존 fixture는 명시적인 값으로 이행한다.
- `Run`에는 lifecycle, started/ended, scenario/target snapshot, parent 관계, restore 상태를 추가한다.
- 기존 H-03 YAML은 제품 의미와 맞지 않으므로 version을 올려 전면 교체한다. 과거 sample YAML은 reference로만 남기거나 삭제하지 않고 git history로 보존한다.
- `state_seed.py`의 ready-report 데이터는 H-03에 사용하지 않는다. H-03 전용 pending fixture를 추가한다.
- `.controlproof/`은 실행 산출물이므로 gitignore하고, 예시 bundle만 비식별 fixture로 커밋한다.

## Risks and Mitigations

| 위험 | 대응 |
|---|---|
| test hook이 운영에서 활성화됨 | profile+env+allowlist+TTL 4중 gate, production startup rejection, 계약 테스트 |
| marker가 남아 후속 Run에 영향 | finally restore, expiry, target lock, restore 실패 차단 파일 |
| 화면과 API가 다른 사실을 말함 | 동일 차원의 독립 source로 수집하고 conflict 또는 assertion FAIL을 명시 |
| 202 polling이 무한 지속 | 30초 deadline과 raw timeline 보존, timeout을 성공으로 취급하지 않음 |
| direct DB seed가 WhyYou schema와 어긋남 | WhyYou version/OpenAPI/migration hash preflight, adapter contract fixture, 실패 시 `RUNNER_NOT_READY` |
| 최종결정 거부 뒤 일부 상태 변경 | 세 필드와 decision history를 같은 전후 snapshot으로 비교 |
| 증적에 bearer/이메일이 남음 | allowlist projection, header/body redactor, 저장 전 검증, raw response 직접 write 금지 |
| WhyYou 업데이트로 endpoint/status가 바뀜 | adapter mapping에 target version을 연결하고 contract failure를 target FAIL로 오판하지 않음 |

## Complexity Tracking

Constitution 위반이나 예외 승인 항목이 없어 별도 복잡성 예외는 없다.
