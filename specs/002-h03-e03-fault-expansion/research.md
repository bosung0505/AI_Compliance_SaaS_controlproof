# Phase 0 Research: H-03·E-03 장애·재시도·DLQ 확장

**Date**: 2026-09-28  
**Target inspected**: WhyYou `bosung/controlproof-h03-integration` at
`aa0ae2b4735d0cd1f2bfb6fe2f07077b3aa4f659`  
**Note**: 이 SHA는 조사 기준선이다. 실제 Run은 매번 canonical target snapshot으로 당시 SHA를 동결한다.

## R-001 — 공식 실행환경

**Decision**: Spec 002의 유일한 공식 target은 `whyyou-local`, 환경 종류는 `LOCAL_EMULATED`다.
PostgreSQL·LocalStack·Mailpit은 Docker, API·worker·company-console은 호스트에서 실행한다. 실제 AWS는
`NOT_RUN`으로 기록한다.

**Rationale**: WhyYou AWS 리소스가 내려가 있어 현재 재현 가능한 전체 cycle은 로컬 stack뿐이다.
LocalStack SQS 결과를 AWS 운영 안정성·권한·경보 검증으로 확대하지 않으면 개발은 계속 진행할 수 있다.

**Alternatives considered**:

- AWS를 먼저 재배포: 2주 MVP 범위와 비용·운영 준비를 크게 늘리므로 제외한다.
- in-memory queue만 사용: redrive/DLQ 계약을 실제로 검증하지 못하므로 제외한다.
- local 결과를 임시 AWS PASS로 취급: 증적 범위를 왜곡하므로 금지한다.

## R-002 — 기존 엔진 확장 방식

**Decision**: Spec 001 v1 계약은 보존하고 Spec 002 scenario profile과 adapter capability를 additive하게
추가한다. 공통 lifecycle·checkpoint·evidence·restore 코드는 `ExecutionSession`으로 추출하되 v1 bundle과
`H-03.yaml`의 의미는 바꾸지 않는다.

**Rationale**: 이미 검증된 Spec 001 경로를 전면 재작성하면 회귀 위험이 커진다. 동시에 현재 runner의
H-03 하드코딩을 그대로 복제하면 Constitution의 scenario/adapter 분리 원칙을 약화한다.

**Alternatives considered**:

- runner 전면 재작성: 장기적으로 깔끔하지만 2주 MVP 위험이 크다.
- Spec 002 전용 독립 스크립트: 빠르지만 Run·증적·복구 계약이 이중화된다.
- 기존 H-03 YAML 덮어쓰기: 과거 bundle 재현성을 깨므로 제외한다.

## R-003 — LocalStack queue topology와 데모 시간

**Decision**: 공식 Spec 002 profile은 `iep-reporting` → `iep-reporting-dlq`, max receive count 3,
visibility timeout 5초를 요구한다. adapter가 실행 직전 실제 queue attribute를 읽고 일치하지 않으면
`RUNNER_NOT_READY`로 중단한다.

**Rationale**: WhyYou production 기본 reporting receive count는 12이고 retry delay는
15·45·120·300·600·900초이므로 그대로 소진하면 10분 목표를 넘는다. WhyYou는 이미
`SQS_REPORTING_MAX_RECEIVE_COUNT`와 visibility override를 지원하므로 로컬에서 같은 redrive 의미를
더 짧게 재현할 수 있다.

**Alternatives considered**:

- 기본 12회 전부 실행: 한 Run이 지나치게 길어 데모와 반복 개발에 부적합하다.
- queue 내부 값을 조작해 즉시 DLQ 이동: 실제 retry/redrive를 시험하지 않으므로 제외한다.
- retry delay 코드를 전역 변경: production 의미에 영향을 줄 수 있으므로 환경별 기존 override를 쓴다.

## R-004 — 저장 전 장애

**Decision**: `BEFORE_RESULT_DURABLE`은 현재 `ControlProofReportingFaultGuard.before_report_side_effect`
경계를 사용한다. marker를 max receive count 소진까지 유지하고 각 attempt receipt를 수집한다.

**Rationale**: hook이 report 조회·쓰기·외부 model 호출보다 먼저 실행되므로 transaction rollback 뒤
report·projection·processed marker가 모두 없어야 한다는 assertion을 정확히 시험할 수 있다.

**Alternatives considered**:

- LLM timeout 유도: 외부 의존성과 시간 변동 때문에 결정론적이지 않다.
- DB 연결 종료: 다른 subject와 worker에도 영향을 줄 수 있다.
- worker 프로세스 강제 종료: 경계가 불명확하고 복구가 어렵다.

## R-005 — 저장 후·ack 전 장애

**Decision**: WhyYou `MessageConsumer`에 선택적 post-commit/pre-ack hook을 추가한다. hook은 reporting
event와 allowlist된 run/session에서만 일회성으로 acknowledge를 생략하고 boundary receipt를 남긴다.

**Rationale**: 현재 worker 순서는 handler → processed marker record → transaction commit → SQS ack다.
이 경계에서 ack만 잃어야 재전달이 processed marker의 duplicate-ack 경로로 들어가고, 실제
at-least-once 처리의 중복 억제를 검증할 수 있다.

**Alternatives considered**:

- report 저장 직후 handler 내부에서 예외: transaction 전체가 rollback될 수 있어 저장 전 장애가 된다.
- commit 뒤 프로세스 kill: 재현성과 cleanup이 떨어진다.
- ControlProof에서 임의 중복 event publish: commit/ack 경계 도달을 증명하지 못한다.

## R-006 — DLQ 관찰과 복구

**Decision**: ControlProof가 boto3로 LocalStack SQS attribute와 DLQ message를 직접 관찰한다. 복구는
DLQ 원본 body·message attributes를 source queue에 send한 뒤 성공했을 때만 DLQ message를 delete한다.

**Rationale**: 원 Outbox row는 이미 published이므로 DB 상태를 되돌려 재발행하는 것보다 queue의 실제
실패 payload를 redrive하는 편이 계보를 보존한다. domain `outbox_event_id`가 동일해 DB 처리 표식과도
연결할 수 있다.

**Alternatives considered**:

- LocalStack `StartMessageMoveTask`: 버전별 지원 편차가 있고 세밀한 send/delete 증적이 부족하다.
- Outbox publish status reset: 애플리케이션 데이터를 시험 도구가 수정하게 되어 제외한다.
- DLQ message 복사 후 원본 유지: 후속 Run을 오염시키므로 정상 복구가 아니다.

## R-007 — reporting 업무 효과 identity

**Decision**: reporting의 필수 효과는 logical report 1건, report ID에 대한 assistant retrieval
projection 집합, `(consumer_name,event_id,event_version)` processed marker 1건, 기존
`report.generation_requested` Outbox 원 사건이다.

**Rationale**: `ReportSearchProjector`는 deterministic document ID와 replace semantics를 사용하고,
`ProcessedMessageRow`는 세 필드 복합 PK를 가진다. 현재 report 완료 Outbox event는 생성되지 않으므로
존재하지 않는 효과를 요구하면 거짓 FAIL이 된다.

**Alternatives considered**:

- DB row 총수만 비교: 다른 report/tenant row와 섞여 원 사건을 설명하지 못한다.
- delivery 횟수를 effect 횟수로 취급: at-least-once queue에서 정상 retry를 중복으로 오판한다.
- completion Outbox 신규 구현: 대상 계약을 검증이 아니라 변경하게 되므로 제외한다.

## R-008 — H-03 decision path와 E-03 사람 결정

**Decision**: H-03은 `recordHumanFinalDecision`과 최종 단계(`최종합격`, `불합격`) 대상
`moveApplicantsToRecruitingStage`를 시험한다. E03-A7은 정상 operation만 같은 `Idempotency-Key`로
두 번 호출하고 단계·invitation·HumanReview·감사를 비교한다.

**Rationale**: 현재 batch stage move는 report를 확인하지 않는 실제 우회 후보다. 반면 중간 단계 이동은
최종 채용 효과가 아니다. 정상 final-decision route는 Idempotency-Key를 받지만 현재 버리므로 최초
E03-A7 Run에서 확인 가능한 결함 후보다.

**Alternatives considered**:

- 모든 stage move를 차단 대상으로 포함: 정상 recruiting workflow까지 H-03으로 오판한다.
- UI 버튼만 시험: 직접 API 우회를 놓친다.
- 두 번째 요청을 새 key로 호출: 같은 논리 요청 재전송 시험이 아니다.

## R-009 — E-03 변형의 verdict 표현

**Decision**: BEFORE와 AFTER는 각각 scenario ID `E-03`을 가진 독립 Run과 독립 verdict다.
BEFORE는 A1~A4·A7·A8, AFTER는 A1·A5·A6·A8을 소유한다. MVP에서 별도 aggregate PASS를 저장하지
않고 두 bundle의 assertion coverage를 나란히 표시한다.

**Rationale**: 한 Run에 두 장애를 섞지 않는다는 Spec을 지키면서, 한 변형의 PASS가 다른 변형의
미실행을 가리지 않게 한다. 별도 campaign 저장 모델은 현재 사용 가치보다 복잡도가 크다.

**Alternatives considered**:

- 한 Run에서 두 fault 순차 실행: 상태와 복구 증적이 서로 오염된다.
- 하나의 E-03 verdict로 자동 병합: 원본 Run 책임과 판정 공백이 불명확해진다.
- campaign DB 추가: 파일 bundle MVP에 불필요한 저장 계층이다.

## R-010 — 환경·증적 schema 호환

**Decision**: `TargetSnapshot v1`과 `controlproof.bundle.v1` canonical 파일·봉인 규칙은 유지하고
environment/queue/effect 파일을 additive하게 추가한다. Spec 002 manifest의
`profile_contract=controlproof.bundle-profile.spec002.v1`이 EV2-01~EV2-12와 새 digest 검증을 선택한다.

**Rationale**: Spec 001의 sealed bundle과 테스트 fixture를 다시 쓰지 않고도 환경 주장 경계와 새
증적을 표현할 수 있다.

**Alternatives considered**:

- TargetSnapshot v1 필드를 필수 확장: 기존 bundle parsing을 깨뜨린다.
- bundle schema 전면 v2 교체: migration 가치보다 회귀 위험이 크다.
- 환경 정보를 사람이 읽는 README에만 기록: machine-verifiable하지 않다.

## R-011 — 외부 AI 및 cloud 접근 차단

**Decision**: preflight는 API·console·DB·SQS URL이 loopback인지, LocalStack endpoint가 명시됐는지,
고정 model/embedder fixture ID·digest가 일치하는지 확인한다. 하나라도 불명확하면 Run을 생성하지 않는다.

**Rationale**: local docs상 `AWS_ENDPOINT_URL`이 모든 AWS client를 포괄하지 않는다. 이번 scenario가
사용하는 경로를 allowlist하고 model/embedder를 dependency boundary에서 교체해야 의도치 않은 실제
cloud 호출을 피할 수 있다.

**Alternatives considered**:

- 개발자 주의에 의존: 반복 실행 시 안전장치가 아니다.
- 방화벽 전체 차단: 환경별 설정이 복잡하고 local service도 방해할 수 있다.
- 외부 model 호출 후 응답만 고정: 실제 비용·개인정보·재현성 문제를 해결하지 못한다.

## Research Closure

모든 Plan-level unknown을 위 결정으로 해소했다. `[NEEDS CLARIFICATION]`은 남지 않았으며, 구현 중
WhyYou의 새로운 최종 결정 경로나 queue 계약 변경이 발견되면 임의로 흡수하지 않고 target snapshot과
Spec 002 capability를 먼저 갱신한다.
