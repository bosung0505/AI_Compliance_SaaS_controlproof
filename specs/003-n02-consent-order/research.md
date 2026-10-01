# Research: N-02 동의·AI 처리 순서 검증

## 조사 범위

- ControlProof branch: `003-n02-consent-order`
- WhyYou baseline branch: `bosung/controlproof-h03-integration`
- WhyYou baseline commit: `511ae9e2cae66b8d0ce31e8851537ed27ac6dd0c`
- 조사일: 2026-10-01
- 목적: Plan의 기술 결정을 확정하는 source research

이 문서는 코드를 읽어 확인한 경계와 설계 결정을 기록한다. 실제 N-02 Run 결과나 WhyYou PASS를
대신하지 않는다.

## R-001. 동의 완료의 권위 원본

**Decision**: `ConsentRecord`, invitation의 `consented` 상태·state change와
`invitation.consent_completed` Outbox row가 한 HTTP transaction에서 commit된 것을 동의 완료로 본다.
Outbox가 worker에 전달된 시각은 별도 사건이다.

**Rationale**:

- `ApplicantAccessService.record_consent()`가 정책 version/digest/필수 purpose를 검사한 뒤 세 종류의
  영속 효과를 같은 request-scoped SQLAlchemy session에 쓴다.
- `RequestScopedDatabase.install_http_transaction_middleware()`는 예외 또는 5xx에서 rollback하고 그 외
  응답 전에 commit한다.
- submission authorization은 전달된 Outbox가 아니라 현재 DB consent fact를 읽는다.

**Alternatives rejected**:

- 체크박스 클릭: 서버 영속 성공을 증명하지 못한다.
- consent API handler return 시각: middleware commit보다 이르므로 단독 기준이 될 수 없다.
- Outbox delivery 시각: 권위 원본이 아니며 전달 지연을 거짓 FAIL로 만들 수 있다.

## R-002. 정상 순서의 증명 방식

**Decision**: wall-clock timestamp 비교만 사용하지 않고 request/trace ID, domain event identity,
aggregate version, client response-before-next-command 순서와 worker boundary receipt로 causal graph를 만든다.

**Rationale**: 여러 container와 DB의 시각 정밀도가 같거나 clock skew가 있어도, middleware commit 뒤
응답 → 다음 command 전송의 프로그램 순서와 Outbox/event 계보는 선후를 보존한다.

**Alternatives rejected**:

- `accepted_at < event.occurred_at`만 비교: 같은 timestamp 또는 clock skew에서 오판한다.
- 전역 sequence table 신규 도입: MVP에 불필요한 영속 스키마와 운영 영향이 생긴다.

## R-003. 자료 분석 경계

**Decision**: pristine 미동의 lane의 공식 요청 경계는 applicant upload-intent API다. API 응답과 함께
storage intent, submission, analysis request, analysis start/result, strategy effect의 0건 여부를 본다.
`submission.analysis_requested` worker entry는 capability map에 실제 downstream 경계로 기록한다.

**Rationale**: `CompanySubmissionAuthorization`이 invitation 상태와 active `document_analysis` consent를
upload intent 전에 검사하며, 현재 통합시험이 storage intent 부재까지 확인한다. 이 경계가 자료를 받을
수 있는 권한·준비 상태부터 보호한다는 Spec 정의와 일치한다.

**Alternatives rejected**:

- HTTP 403만 확인: storage/event side effect를 놓친다.
- ControlProof 전용 analysis endpoint 추가: 실제 제품에 없는 진입점을 만들어 시험한다.

## R-004. 녹화 경계

**Decision**: 실제 `createInterviewSession` API를 심층 authorization probe로 사용한다. lane에는
장비 점검과 strategy만 allowlist fixture로 두고 session/recording effect는 0건에서 시작한다.

**Rationale**: `SessionApplicationService.create_session()`은
`SubmissionInterviewBoundary.authorize_start()`를 호출하지만, 현재 boundary는 strategy·scope·partial
acknowledgement만 확인하고 active `recording` consent를 직접 읽지 않는다. 정상 사용자 흐름의 upstream
상태에만 기대는지 실제 서버 경계에서 시험해야 한다.

**Alternatives rejected**:

- upload-intent 차단으로 녹화도 PASS: 독립 호출 가능한 session API의 보호를 증명하지 못한다.
- 가짜 recording endpoint: 실제 authorization을 우회한다.
- fixture 없이 호출: strategy not found로 거부돼 consent 보호인지 구분할 수 없다.

## R-005. AI 평가 경계

**Decision**: 독립 applicant 평가 API가 없다는 사실을 capability로 고정하고, 실제
`report.generation_requested` event와 `ReportRequestedEventHandler`를 심층 probe로 사용한다. 완료 면접,
final turn과 final video는 allowlist fixture이며 report/request/processed marker는 0건에서 시작한다.

**Rationale**: WhyYou의 AI score/report는 reporting worker에서 생성된다. handler는 실제 운영 event
contract를 사용하지만 현재 active `ai_assessment` consent를 직접 확인하지 않는다. fixture 전후 delta를
보면 실제 worker 경계의 새 평가 effect를 독립적으로 식별할 수 있다.

**Alternatives rejected**:

- 존재하지 않는 direct HTTP 평가 API 추가: 제품 경계를 왜곡한다.
- 미완성 session ID로 event 호출: prerequisite 오류만 확인하고 consent 통제를 시험하지 못한다.
- upload 차단을 평가 PASS로 승격: downstream side-door 위험을 놓친다.

## R-006. 심층 fixture와 pristine 기준선의 분리

**Decision**: N02-A1은 별도 pristine lane으로 검증한다. 녹화·평가 심층 probe는 fixture digest와
allowlisted pre-existing effect를 고정하고, probe 뒤 증분만 A3/A4에 사용한다.

**Rationale**: 깊은 실제 경계는 앞 단계 산출물이 없으면 consent가 아닌 prerequisite 때문에 거부된다.
동시에 그 산출물을 일반 기준선에 숨기면 “동의 전 효과 0건” 주장을 훼손한다. 두 사실을 lane과 판정
책임으로 분리해야 한다.

**Alternatives rejected**:

- 한 subject에 모든 시도 연속 실행: 앞 시도의 side effect가 뒤 판정을 오염시킨다.
- fixture effect를 무시: 무엇이 seed이고 무엇이 target effect인지 재현할 수 없다.
- 깊은 경계를 전혀 시험하지 않음: 가장 중요한 side-door를 놓친다.

동의 저장 실패 lane은 예외다. 실패 직후 zero-effect snapshot을 먼저 확보한 뒤 같은 subject에 deep
boundary 전제조건을 임시 overlay로 적용해 세 경로를 실제 시도한다. overlay는 path마다 제거하고 정상
동의 복구 전에 pristine seed digest를 회복한다. 이 순서가 아니면 transaction rollback과 경로 차단을
같은 사실처럼 섞게 된다.

## R-007. 동의 저장 실패 주입점

**Decision**: `save_consent()` 호출 직후, invitation transition과 Outbox append 전에 local/test 전용
one-shot fault를 발동한다.

**Rationale**: 첫 DB write 이후의 실패이므로 transaction rollback이 없으면 consent row만 남는 대표
부분 저장을 직접 드러낸다. 예외는 FastAPI handler의 `ValueError` 변환 대상이 아닌 전용 runtime error로
전파돼 middleware rollback과 5xx를 만든다.

**Alternatives rejected**:

- 첫 write 전 실패: 원자성을 충분히 시험하지 못한다.
- commit 후 실패: 동의가 이미 성공한 것이므로 저장 실패 원자성 시나리오의 의미와 다르다.
- DB proxy/강제 container kill: 다른 Run에 영향을 주고 정확한 boundary receipt가 어렵다.

## R-008. fault와 observer 안전성

**Decision**: 기존 reporting fault의 환경 guard 패턴을 재사용하되 consent marker namespace와 receipt
schema를 분리한다. local/test, explicit enable, Run/subject match, TTL ≤ 600초, one-shot, fsync receipt,
always-run restore를 요구한다.

**Rationale**: WhyYou에 이미 검증된 marker/receipt/production rejection 패턴이 있으며 이를 재사용하면
새 제어면을 최소화할 수 있다. consent fault와 reporting fault를 같은 marker로 섞으면 복구 대상이
불명확해진다.

**Alternatives rejected**:

- 환경변수 하나로 전역 failure 활성화: subject 격리와 복구가 불가능하다.
- 로그 문자열만 trigger 증거로 사용: rotation/수집 실패와 상관관계 손실 위험이 있다.

## R-009. 시작 관찰 receipt

**Decision**: local/test observer가 analysis handler entry, interview session create/start, recording confirm,
report handler entry의 최소 receipt를 남긴다. observer는 write path를 결정하거나 판정하지 않는다.

**Rationale**: DB 결과만으로는 “요청됨”과 “실제 handler가 시작됨”을 구분할 수 없는 경계가 있다.
trace/event ID에 연결된 boundary receipt가 FR-015~024의 요청·시작·결과 구분을 충족한다.

**Alternatives rejected**:

- 전체 worker 로그 수집: 과수집·PII·재현성 문제가 있다.
- OpenTelemetry 전체 도입: MVP 범위를 넘고 collector 의존성이 생긴다.

## R-010. 정상 one-cycle 실행

**Decision**: browser automation 없이 applicant HTTP/WebSocket와 real local worker를 사용해 정책 조회 →
동의 → 자료 → 면접/녹화 → report 생성까지 실행한다. fixed model/embedder와 합성 media만 사용한다.

**Rationale**: N-02의 핵심은 server order이고 PC/모바일 visual visibility는 N-01이다. 브라우저를
필수화하면 viewport concern을 섞고 실행 시간을 늘린다. 실제 API와 worker는 server guarantee를 직접
검증한다.

**Alternatives rejected**:

- UI screenshot을 N-02 PASS 조건으로 추가: N-01과 중복된다.
- DB seed로 정상 결과까지 건너뜀: 정상 causal order를 증명할 수 없다.

## R-011. 오래된 cross-module 시험

**Decision**: `cross_module/test_a_to_b.py` 전체 복원을 Spec 003 선행조건으로 삼지 않는다. 현재 production
wiring과 repository를 사용하는 작은 N-02 통합시험으로 대체하고 기존 파일은 별도 legacy harness 문제로
남긴다.

**Rationale**: WhyYou `pyproject.toml`도 삭제된 harness 때문에 unit 외 suite 일부가 collection되지 않는
상태를 명시한다. 오래된 대형 시험 복원은 N-02보다 넓은 리팩터링이 될 수 있다.

**Verification**: 2026-10-01 baseline checkout에서
`.venv\\Scripts\\python.exe -m pytest backend/tests/integration/cross_module/test_a_to_b.py -q`를 실행했으며,
`InMemoryCompanyRepository` import 부재로 collection error 1건이 재현됐다. 이는 N-02 assertion 실패가
아니라 legacy test harness 상태다.

**Alternatives rejected**:

- legacy harness 전체 복구: 범위와 일정 위험이 크다.
- 기존 fake authorization 시험만 신뢰: 실제 module boundary와 transaction wiring을 검증하지 못한다.

## R-012. profile/schema 확장

**Decision**: `N02_CONSENT_ORDER_V1`와 `controlproof.scenario.v3`를 추가하고 profile별 validation policy를
registry로 분리한다. bundle 본체는 v1을 유지하고 Spec 003 profile contract만 additive하게 추가한다.

**Rationale**: 현재 model은 H03 minimal 외 모든 profile에 Spec 002 queue/fault 필드를 강제한다. N-02는
queue DLQ profile이 아니므로 기존 조건문에 예외를 계속 추가하기보다 profile policy를 명시해야 한다.

**Alternatives rejected**:

- H03/E03 profile 중 하나 재사용: assertion과 evidence 의미가 다르다.
- bundle major version 변경: 기존 sealed Run 호환성을 불필요하게 깨뜨린다.

## R-013. 최초 FAIL 이후 보완

**Decision**: 첫 actual Run 전에는 observer/fault/seed/adapter만 추가한다. analysis, recording,
AI-assessment consent guard는 해당 경계의 FAIL bundle을 봉인한 뒤에만 수정한다.

**Rationale**: Constitution은 실제 실패를 먼저 보존하도록 요구한다. source review만으로 예상 결함을
미리 고치면 ControlProof가 그 결함을 실제로 탐지했다는 증거를 잃는다.

**Alternatives rejected**:

- source review 뒤 즉시 세 guard 추가: FAIL→PASS 계보가 사라진다.
- 모든 경계를 무조건 수정: 중복 방어와 unintended behavior 위험이 있다.

## R-014. DB migration과 웹 UI

**Decision**: 기본 구현은 WhyYou DB migration과 ControlProof 웹 UI를 추가하지 않는다. 기존 row의
allowlist projection과 file bundle을 사용한다.

**Rationale**: 필요한 consent/state/outbox/submission/session/report identity가 이미 존재한다. 고객 웹
결과는 Spec 005 범위다.

**Alternatives rejected**:

- N-02 전용 audit table: 실제 제품 동작보다 시험용 영속 상태를 늘린다.
- 임시 dashboard: CLI 계약과 증적 완성보다 앞서 UI를 중복 구현한다.

## Resolved Planning Questions

| Planning Gate 질문 | 결론 |
|---|---|
| 분석 요청·시작·결과 경계 | upload intent/submission Outbox/analysis handler receipt/analysis·strategy rows |
| 녹화 요청·시작·결과 경계 | create-session/WS start/recording upload-confirm/session·chunk·asset rows |
| 평가 요청·시작·결과 경계 | report event/report handler receipt/report·item·projection rows |
| 직접 우회 | 자료는 pristine API, 녹화·평가는 digest가 고정된 deep probe fixture + 실제 boundary |
| fault 지점 | consent row save 후 invitation transition·Outbox 전 |
| 공통 상관관계 | request/trace ID, event ID/version, aggregate version, client program order |
| 최소 증적 | policy/consent/state/outbox + 경로별 request/receipt/effect delta |
| legacy 시험 | 전체 복원 대신 현재 wiring의 작은 N-02 통합시험 |
| 기존 Spec 호환 | profile policy registry와 additive bundle contract로 v1/v2 보존 |

Plan 단계의 `NEEDS CLARIFICATION`은 0개다.
