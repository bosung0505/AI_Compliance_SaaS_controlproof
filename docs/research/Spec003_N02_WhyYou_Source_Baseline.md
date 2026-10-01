# Spec 003 N-02 WhyYou 소스 기준선

## 1. 목적과 조사 기준

태오 작성 자료는 존재하지 않는다. 따라서 Spec 003은 추정이나 구두 기억이 아니라 아래 WhyYou
checkout을 직접 조사한 결과를 입력으로 사용한다.

- 조사일: 2026-10-01
- 저장소: `jhkim0602/gbsa_aws`
- 브랜치: `bosung/controlproof-h03-integration`
- commit: `511ae9e2cae66b8d0ce31e8851537ed27ac6dd0c`
- 조사 성격: 명세 확정 전 source discovery. 이 문서만으로 N-02 PASS를 주장하지 않는다.

## 2. 소스에서 확인된 사실

### 2.1 지원자 화면 순서

`apps/applicant-interview/src/features/access/index.tsx`의 화면 흐름은 다음과 같다.

1. 초대 토큰 확인
2. 본인 확인
3. 서버에서 동의 정책 조회
4. 필수 목적을 모두 선택
5. 서버에 동의 기록 요청
6. 요청 성공 뒤에만 자료 제출 단계로 이동

화면은 AI의 역할, 녹화 고지, 처리 목적, 보관기간, 삭제 방법을 표시한다. UI 시험은 세 필수 목적을
모두 선택하지 않으면 계속 버튼이 비활성화되고, 동의 API 성공 뒤에만 ready 단계가 나타나는 것을
확인한다.

### 2.2 서버 정책과 동의 기록

`backend/src/interview_evidence/company_management/domain/applicant_access.py`와
`application/applicant_access_service.py`에서 다음을 확인했다.

- 필수 목적은 `document_analysis`, `recording`, `ai_assessment`다.
- 기본 정책 버전은 `2026-08-v1`이다.
- 정책 본문 전체를 canonical JSON으로 만든 SHA-256 `content_digest`가 있다.
- 서버는 제출된 목적 집합이 필수 목적과 정확히 같은지 확인한다.
- 서버는 제출된 `policy_version`과 `consent_content_digest`가 현재 정책과 같은지 확인한다.
- 성공하면 immutable 성격의 `ConsentRecord`에 정책 버전, 목적, 보관기간, 수락 시각과 본문 해시를
  저장하고 초대 상태를 `consented`로 전이한다.
- 같은 요청 트랜잭션에서 `invitation.consent_completed` Outbox 이벤트를 추가한다.
- HTTP 요청 단위 transaction middleware가 5xx 또는 예외에서 rollback하고 그 외 응답을 commit한다.

### 2.3 동의 전 자료 처리 차단

`integration/company_submission.py`는 자료 제출을 허용하기 전에 다음 둘을 모두 확인한다.

- 초대 상태가 `consented` 이상인 허용 상태인가
- 활성 동의 레코드에 `document_analysis` 목적이 있는가

`tests/integration/submission_analysis/test_consent_gate.py`는 동의 없음 또는 미동의 초대에서 upload
intent가 403이고 object storage intent가 만들어지지 않음을 검증한다. cross-module 시험은 동의 철회
뒤 추가 upload intent가 403이고 기존 한 건 외에 새 storage intent가 생기지 않음을 검증한다.

### 2.4 현재 있는 사건과 관찰점

- 동의 정책 조회: `GET /v1/applicant/consents`
- 동의 기록: `POST /v1/applicant/consents`
- 동의 완료 영속값: consent record와 invitation state change
- 동의 완료 비동기 사건: `invitation.consent_completed`
- 자료 저장 진입점: applicant submission upload-intent API
- 분석 요청 사건: `submission.analysis_requested`
- 면접·녹화 진입점: interview session API/WebSocket와 recording upload API

## 3. 아직 보장됐다고 말할 수 없는 것

다음은 코드가 없다는 단정이 아니라, 현재 조사만으로 전역 보장을 입증하지 못했다는 뜻이다.

1. `require_processing_authorization()`은 domain helper와 단위시험에는 있지만 production 경로의 모든
   분석·녹화·평가 진입점에서 공통 호출되는 구조는 아니다.
2. 자료 업로드 경계는 명시적으로 동의를 확인하지만, 분석 worker와 면접 시작 경계는 초대 상태나
   앞 단계 산출물에 의존하는 부분이 있다. 직접 event/API 우회까지 모두 막히는지는 실제 시험이 필요하다.
3. 동의 완료 Outbox 전달 지연이 downstream 처리를 막아야 하는지, durable consent record가 즉시
   권위 원본인지 아직 Spec으로 확정하지 않았다. 현재 소스상 자료 제출 authorization은 DB의 동의
   레코드를 직접 읽으므로 Outbox 지연 자체를 곧바로 처리 위반으로 판정하면 안 된다.
4. 동의 저장 중 어느 DB write가 실패했을 때 consent record, invitation state, Outbox가 모두 rollback되는지
   실제 fault injection으로 확인하지 않았다.
5. 동의 API 성공 응답 시각, Outbox 생성 시각, 분석 요청 시각, 실제 worker 시작 시각을 하나의 trace로
   비교할 ControlProof adapter와 증적 계약은 아직 없다.
6. 녹화와 AI 평가를 동의 전 직접 호출하는 합성 우회 경로, 안전한 test-only 주입점과 복구 절차가 아직
   확정되지 않았다.

## 4. Spec 003에 넘기는 초기 제품 결정

1. N-02의 기준 사건은 브라우저 체크박스 클릭이 아니라 **서버 transaction이 성공해 durable consent
   record와 `consented` 상태가 commit된 시점**으로 한다.
2. Outbox 전달은 동의 완료의 유일한 진실 원본으로 간주하지 않는다. 다만 Outbox 누락·지연이 후속
   처리나 증적 연결에 미치는 영향은 별도 관찰한다.
3. 최소 우회 경로는 자료 업로드, 분석 요청/worker 시작, 면접·녹화 시작, AI 평가 시작으로 나눈다.
   경로가 실제로 존재하지 않으면 `NO_TEST_TARGET`로 뭉개지 않고 해당 capability의 부재를 기록한다.
4. 각 경로는 동의 전 시도에서 HTTP 거부만 보는 것이 아니라 DB row, object intent, Outbox/event,
   worker receipt, 녹화 asset과 평가 결과가 생기지 않았는지 확인한다.
5. 정상 경로에서는 `consent_committed_at < processing_requested_at <= processing_started_at`을 증명한다.
   같은 시각 해상도 때문에 순서를 판단할 수 없으면 PASS가 아니라 `INSUFFICIENT_EVIDENCE`다.
6. 동의 저장 실패를 주입하면 부분 저장 없이 rollback되어야 하며, 복구 후 같은 합성 지원자로 정상
   동의를 다시 수행할 수 있어야 한다.
7. 실제 첫 Run이 보호조치 결함을 찾으면 FAIL bundle을 먼저 봉인하고 WhyYou 개인 브랜치에서만 수정한
   뒤 child Run으로 재시험한다.

## 5. Spec 003 명세 전에 답해야 할 질문

- 어떤 endpoint/event를 “분석 요청”과 “실제 분석 시작”의 공식 경계로 볼 것인가?
- 면접 세션·녹화·AI 평가 각각에 직접 우회가 가능한 test route가 있는가, 없으면 안전한 local-only
  probe를 어디에 둘 것인가?
- consent transaction의 저장 전·중·commit 후 어느 지점에 fault를 주입해야 부분 저장을 가장 잘
  검증하는가?
- 정상·장애·복구 Run에서 반드시 수집할 최소 DB table, API response, Outbox row, worker receipt와
  화면 증적은 무엇인가?
- 오래된 policy version/digest는 N-02의 보조 assertion으로만 둘 것인가, N-03과 중복되지 않게 어떻게
  경계를 나눌 것인가?

이 질문은 `$speckit-clarify`와 Plan 단계에서 확정한다. 답이 정해지기 전 구현을 시작하지 않는다.

## 6. 0단계 회귀 확인 결과

2026-10-01에 위 고정 commit에서 다음 최소 회귀를 실행했다.

| 확인 | 결과 | 해석 |
|---|---|---|
| consent policy 단위시험 + 동의 없는 submission 차단 통합시험 | `5 passed` | 정책 digest·목적별 동의 domain과 upload-intent 이전 차단은 현재 시험과 일치 |
| 지원자 동의 화면 journey | `2 passed` | 필수 문구·세 목적·전부 선택 전 버튼 비활성·동의 성공 뒤 진행이 현재 UI 시험과 일치 |
| `cross_module/test_a_to_b.py` 포함 실행 | collection error | 삭제·이동된 `InMemoryCompanyRepository`를 아직 import해 cross-module 시험 파일이 현재 코드와 불일치 |

마지막 collection error는 N-02 보호조치 FAIL 판정이 아니다. 다만 과거 cross-module 시험을 근거로
동의 철회까지 검증됐다고 자동 주장할 수 없다는 뜻이다. Spec 003 Plan에서 현행 repository fixture로
시험을 복구하거나, 같은 경계를 새 통합시험으로 대체하는 작업을 명시해야 한다.
