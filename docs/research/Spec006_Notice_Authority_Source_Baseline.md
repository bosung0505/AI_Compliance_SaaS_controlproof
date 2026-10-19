# Spec 006 N-01·N-03·H-01·H-02 — 원천 기준선

- 조사일: 2026-10-19 (Specify 전 Source discovery, 플레이북 §3 단계 0)
- 조사 대상:
  - ControlProof `994dd3f` (`fixes-and-remaining-work`, Spec 005 웹 + 2026-10-15 UX 개편 + N-02 로컬 마감)
  - WhyYou `33aa996` (`bosung0505/gbsa_aws` `fixes-and-remaining-work`). `374b122` 위에 커밋 1개
    (`feat: finish N-02 document analysis test model integration`)만 더했다. 그 커밋이 바꾼 파일은 분석 모델 교체
    (`runtime/controlproof_model_substitute.py`, `runtime/worker.py` 분석 파이프라인 연결)와 시험·문서뿐이고,
    이 문서가 다루는 동의·최종결정·어시스턴트·작업자 처리 목록 코드는 `374b122`와 같다.
- 방법: 소스·문서 읽기만 했다. Run·DB 조회·서버 기동은 하지 않았다.
- 읽는 법: WhyYou 경로는 `backend/src/interview_evidence/` 기준 상대 경로와 줄 번호다. "확인된 사실"은 그 줄에서
  재확인할 수 있다. "미확인"은 확인 방법과 함께 적는다. 결과(PASS/FAIL)를 예측한 문장은 없다.

## 1. H-01 — `COMPANY_USER`가 아닌 주체의 최종결정 거부

### 확인된 사실

- 최종결정 API: `POST /v1/invitations/{invitation_id}/final-decisions`, operationId `recordHumanFinalDecision`
  (`reporting/api/company_routes.py` 627~630). `Authorization: Bearer`와 `Idempotency-Key`가 필요하다.
- 최종 단계로 옮기는 두 번째 쓰기 경로: `PATCH /v1/positions/{position_id}/invitations/recruiting-stage`
  (`company_management/api/company_routes.py` 986), `require_final_report=True`(1008), 검사는
  `company_management/application/hiring_service.py` 304·321.
- 주체 결정: `company_scope`(`reporting/api/company_routes.py` 385~408)는 Bearer가 없으면 401, 토큰을 못 찾으면 401을
  돌려주고, 찾으면 **항상 `ActorType.COMPANY_USER`**로 맥락을 만든다(403). HTTP로는 다른 주체 유형이 이 경로에
  들어오지 못한다.
- 주체 유형은 `COMPANY_USER`, `APPLICANT`, `SYSTEM` 세 가지다(`shared/tenant.py` 9~12). AI 어시스턴트 전용 주체 유형은 없다.
- 도메인 검사: `HumanReview`가 사람 회사 사용자가 아니면 `PermissionError("final decision requires a human company user")`를
  낸다(`reporting/domain/review.py` 107, 138). HTTP에서는 주체가 항상 `COMPANY_USER`라 이 검사에 닿지 않는다.
- 최종결정을 실제로 쓰는 호출: `reporting/application/final_decision_service.py` 82(`move_to_recruiting_stage`)·
  88(`record_recruiting_stage_decision`), `reporting/application/review_service.py` 256,
  `company_management/application/hiring_service.py` 155·332.
- 감사 기록: 성공 시 `final_decision.create`(`final_decision_service.py` 105). 거부된 시도를 기록하는 감사 항목은
  찾지 못했다. 401은 감사 호출 전에 반환된다.
- 시험용 자격 증명: 회사 토큰은 환경 변수 하나(`LOCAL_COMPANY_ACCESS_TOKEN`, 데모는 `DEMO_COMPANY_*`;
  `shared/security/local.py` 27·42·86·90). 지원자는 `iep_applicant_session` 쿠키이고, ControlProof N-02 시드가 같은
  방식으로 만든다(`seeds/n02_subjects.py` 23·95). `SYSTEM`과 AI에는 HTTP 자격 증명이 없다.

### 미확인

- `hiring_service.py` 155(기본 단계 배정)가 초대 상태에 따라 최종 단계를 배정할 수 있는지. `_default_stage_name`의
  상태→단계 대응을 읽어 확인한다.
- 거부된 호출이 `Idempotency-Key`나 파이프라인 버전에 흔적을 남기는지. DB 전후 비교로 확인한다.

## 2. H-02 — AI 어시스턴트·작업자의 쓰기 권한 표면

### 확인된 사실

- 채용 어시스턴트는 도구 호출 구조가 아니다. 저장소 전체에서 `tool_use`·`tool_choice`·`"tools"`를 찾지 못했다.
  공개 경로는 `recruiting_assistant/api.py` 216·253·285의 POST 세 개(검색, 답변, 답변 스트림)다.
- 작업자 처리 목록은 코드의 사전으로 읽을 수 있다: `runtime/worker.py` 109 `EVENT_QUEUE_ROUTING`과 같은 파일의 처리기
  대응표. 기계적으로 열거할 수 있다.
- 최종결정·채용 단계 쓰기 함수(`move_to_recruiting_stage`, `record_recruiting_stage_decision`,
  `HumanReview.recruiting_stage_decision`)의 호출 위치는 1절 목록뿐이고, `workers/`·`recruiting_assistant/`에는 없다.

### 미확인

- 어시스턴트 답변 경로가 간접적으로 쓰기 서비스를 부를 수 있는지(의존성 주입 대상). `recruiting_assistant/api.py`의
  읽기 전용 리더(`RecruitingPipelineReader`)와 주입 지점을 정적으로 따라가 확인한다.
- 정적 검사의 기준(호출 그래프 범위, 동적 디스패치 처리)은 Plan에서 정한다.

## 3. N-01 — PC·390px 모바일 동의 화면의 필수 고지

### 확인된 사실

- 지원자 앱 경로: `access/:token`(`apps/applicant-interview/src/app/featureRoutes.ts` 30). 동의 단계는
  `apps/applicant-interview/src/features/access/index.tsx`에 있다(교환 → 본인 확인 → 동의).
- 고지 문구의 원천은 백엔드 상수 `DEFAULT_CONSENT_POLICY`(`company_management/domain/applicant_access.py` 54)이고,
  `GET /v1/applicant/consents`(`company_management/api/applicant_routes.py` 274)가 `policy_version`과 `content_digest`를
  함께 돌려준다. 해시는 정규화한 JSON의 SHA-256이다(`applicant_access.py` 42~51).
- 디자인 시스템의 모바일 구간은 `max-width: 600px`(`packages/design-system/theme.css` 224)다.
- ControlProof 브라우저 어댑터는 회사 콘솔만 1440×900으로 연다(`engine/adapters/whyyou/browser.py` 50·68·105).
  지원자 앱을 여는 실행기는 없다.

### 미확인

- 동의 화면에 AI 사용·사람의 최종 결정·녹화 목적·보관기간·삭제 방법이 모두 그려지는지와 390px에서 잘리는지.
  실제 화면 확인 전에는 알 수 없다.
- 지원자 앱의 로컬 기동 방법과 포트. WhyYou `package.json` 스크립트로 확인한다.

## 4. N-03 — 정책 교체 구간의 동의 귀속

### 확인된 사실

- 낡은 정책 거부는 있다: `POST /v1/applicant/consents`(`applicant_routes.py` 305)가 받은 버전·해시가 현재 정책과 다르면
  `"consent policy version or digest is stale"`(`company_management/application/applicant_access_service.py` 147)를 내고
  422로 돌려준다(`applicant_routes.py` 331).
- **실행 중 정책을 바꿀 수단이 없다.** 정책은 코드 상수이고 서비스 생성자 기본값으로 들어간다
  (`applicant_access_service.py` 60). 관리 API나 DB 경로가 없다. 교체를 일으키려면 WhyYou 쪽 시험용 수단이 필요하다
  (Spec 003의 `runtime/controlproof_consent.py`처럼 로컬·시험 환경에서만 켜지는 방식이 선례다).
- 동의 기록에는 `policy_version`이 저장된다. 제출 승인 객체에도 `policy_version`이 실린다
  (`integration/company_submission.py` 58·74).
- 분석 작업이 어느 정책 버전으로 시작됐는지 남기는 저장 필드는 `submission_analysis/`·`workers/`에서 찾지 못했다.
  (`submission_analysis/application/authorization.py` 99의 `"2026-08-v1"`은 시험용 대역 객체의 고정값이다.)

### 미확인

- 화면에 남은 이전 정책으로 제출하는 경로(V4 §10.3 "우회")는 교체 수단 없이도 이전 해시를 직접 보내 재현할 수 있다.
  이것만으로 시나리오 목적을 충족하는지는 Clarify에서 정한다.

## 5. 재사용할 수 있는 ControlProof 부품

- 최종결정 호출: `engine/adapters/whyyou/client.py` 117 `attempt_final_decision`, `decisions.py` 106 `attempt`·
  226 `capture_reset_token`·274 `reset`(401/403을 `DECISION_ACCESS_DENIED`로 대응, 194).
- 동의: `engine/adapters/whyyou/consent.py` 83 `read_policy`·121 `commit`(`CONSENT_POLICY_MISMATCH`, 166)·201 `read_state`.
- 회사 토큰은 하나(`engine/config.py` 71·130 `WHYYOU_COMPANY_TOKEN`). 주체별 토큰을 다루는 설정은 없다.
- 시드: H-03 검토 대기 리포트 시드, N-02 지원자 쿠키 시드(`seeds/n02_subjects.py`).

## 6. 구매자·데이터 범위와의 관계 (2026-10-19 팀 방향)

팀은 공급기업과 채용기업 모두를 구매자로 보고, 받는 데이터에 따라 판정 가능한 항목이 달라진다고 정했다. 이 기준선의
네 시나리오 중 H-02는 소스 접근이 필요한 정적 검사라 공급기업 데이터가 있어야 한다. N-01·H-01·N-03은 화면·API 접근으로
시험할 수 있다. 이 구분을 Spec 006 요구사항에 넣을지는 Specify·Clarify에서 정한다.
