# Spec 009 N-01·N-03 — 원천 기준선

- 조사일: 2026-10-19 (Specify 전 Source discovery, 플레이북 §3 단계 0). 같은 날 Spec 006 초안용으로 조사한 내용 가운데 N-01·N-03
  부분을 옮기고 기준 커밋을 갱신했다(D-030).
- 조사 대상:
  - ControlProof `b76af4c` (`fixes-and-remaining-work`, Spec 005 웹 + UX 개편 + N-02 로컬 마감 + Spec 006 H-01 + Spec 007 H-02 +
    Spec 008 공유 기록). 이 문서가 인용하는 동의 어댑터·브라우저 어댑터·N-02 시드·설정(`engine/adapters/whyyou/consent.py`,
    `browser.py`, `capability.py`, `client.py`, `seeds/n02_subjects.py`, `engine/config.py`)은 `994dd3f`와 같다. 프로필 등록 지점
    (`engine/models.py`, `scenario.py`, `runner.py`, `cli.py`, `evidence.py`, 웹 readmodel)은 H-01·H-02 등록으로 바뀌었으므로
    줄 번호 대신 함수·심볼 이름으로 적는다.
  - WhyYou `0166d9e` (`bosung0505/gbsa_aws` `fixes-and-remaining-work`). `33aa996` 위에 커밋 2개(`4de2b08` H-01/H-02 수정,
    `0166d9e` 문서)만 더했다. 바뀐 파일은 `hiring_service.py`, `recruiting_assistant/application.py`, `runtime/controlproof_h01*`,
    `controlproof_h02_binding.py`, `controlproof_model_substitute.py`, `runtime/production.py`와 시험·문서뿐이고, 이 문서가 다루는
    동의·지원자 앱 코드는 `33aa996`·`374b122`와 같다. 아래 줄 번호는 그 파일들 기준이라 `0166d9e`에서도 그대로다.
- 방법: 소스·문서 읽기만 했다. Run·DB 조회·서버 기동은 하지 않았다.
- 읽는 법: WhyYou 경로는 `backend/src/interview_evidence/` 기준 상대 경로와 줄 번호다. "확인된 사실"은 그 줄에서
  재확인할 수 있다. "미확인"은 확인 방법과 함께 적는다. 결과(PASS/FAIL)를 예측한 문장은 없다.

## 1. N-01 — PC·390px 모바일 동의 화면의 필수 고지

### 확인된 사실

- 지원자 앱 경로: `access/:token`(`apps/applicant-interview/src/app/featureRoutes.ts` 30). 동의 단계는
  `apps/applicant-interview/src/features/access/index.tsx`에 있다(교환 → 본인 확인 → 동의).
- 화면은 항상 `exchange`에서 시작해(`features/access/index.tsx` 215) URL 초대 토큰 교환(265~268) → 본인 확인(277) → 동의
  (361~438)로 간다. 초대 토큰은 `HMAC-SHA256(pepper, raw)`로 `invitations.token_hash`에 저장된다
  (`company_management/adapters/applicant_session.py` 97~112, local pepper `b"local-development-pepper"`). 본인 확인은 표시 이름
  대소문자 무시 비교다(`company_management/application/applicant_access_service.py` 102~129).
- 동의 화면 문구 출처: `policy.aiRole`(375, AI 사용과 사람의 최종 결정), `policy.recordingNotice`(378), "보관기간" 라벨 +
  `retentionDays`(382~385), "삭제 방법" 라벨 + `deletionMethod`(388~391), 처리 목적 체크박스(398~423). 접힘 영역은 없다.
- 고지 문구의 원천은 백엔드 상수 `DEFAULT_CONSENT_POLICY`(`company_management/domain/applicant_access.py` 54~86): `policy_version`
  `2026-08-v1`, `ai_role`, `recording_notice`, 목적 셋(document_analysis·recording·ai_assessment), `retention_days` 180,
  `deletion_method`. `GET /v1/applicant/consents`(`company_management/api/applicant_routes.py` 274)가 `policy_version`과
  `content_digest`를 함께 돌려준다. 해시는 정규화한 JSON의 SHA-256이다(`applicant_access.py` 42~51).
- 지원자 앱 기동: `apps/applicant-interview/package.json` 6~11 `dev`=`vite`, 루트 `package.json` 10~26 `dev:applicant`.
  `apps/applicant-interview/vite.config.ts` 7~21: `127.0.0.1:5174`, `strictPort`, `/v1` 프록시 대상 `http://127.0.0.1:8080` 고정.
  API 기준은 `VITE_API_BASE_URL ?? ""`(`src/app/routeAdapters.tsx` 44). 백엔드에 CORS가 없어(설정 주석) 같은 출처 프록시가
  필요하다. `.env.example` 153·155: `APPLICANT_ACCESS_BASE_URL=http://localhost:5174/access`.
- 디자인 시스템의 모바일 구간은 `max-width: 600px`(`packages/design-system/theme.css` 224)다.
- ControlProof 브라우저 어댑터는 회사 콘솔만 1440×900으로 연다(`engine/adapters/whyyou/browser.py` 50·68·105). 지원자 앱을
  여는 실행기는 없다. Chromium 실행 파일 존재는 `engine/adapters/whyyou/capability.py`의 브라우저 probe가 본다.

### 미확인

- 동의 화면에 AI 사용·사람의 최종 결정·녹화 목적·보관기간·삭제 방법이 모두 그려지는지와 390px에서 잘리는지.
  실제 화면 확인 전에는 알 수 없다(이것이 N-01 판정 대상이다).
- 프록시 대상 포트 8080을 바꾸지 않고 하네스 API를 다른 포트에 띄울 수 있는지(vite `--config`로 ControlProof 쪽 설정 파일을
  넘기는 방법). Plan에서 정한다.

## 2. N-03 — 정책 교체 구간의 동의 귀속

### 확인된 사실

- 낡은 정책 거부는 있다: `POST /v1/applicant/consents`(`applicant_routes.py` 305)가 받은 버전·해시가 현재 정책과 다르면
  `"consent policy version or digest is stale"`(`applicant_access_service.py` 143~147, 버전·해시 중 하나라도 다르면)을 내고
  422로 돌려준다(`applicant_routes.py` 331). 동의 POST는 `Idempotency-Key`를 받고 버린다(319).
- **실행 중 정책을 바꿀 수단이 없다.** 정책은 코드 상수이고 서비스 생성자 기본값으로 들어간다
  (`applicant_access_service.py` 60). 관리 API나 DB 경로가 없다. 교체를 일으키려면 WhyYou 쪽 시험용 수단이 필요하다
  (Spec 003의 `runtime/controlproof_consent.py`처럼 로컬·시험 환경에서만 켜지는 방식이 선례다).
- 동의 기록에는 `policy_version`이 저장된다. 제출된 내용 해시도 동의 기록의 `evidence_digest`로 저장된다
  (`applicant_access_service.py` 153·157). 제출 승인 객체에도 `policy_version`이 실린다(`integration/company_submission.py` 58·74).
- 동의는 `consent_records`, `invitation_state_history`, outbox `invitation.consent_completed`를 쓴다. 동의 기록 감사(`audit_events`)는
  없다.
- 분석 작업이 어느 정책 버전으로 시작됐는지 남기는 저장 필드는 `submission_analysis/`·`workers/`에서 찾지 못했다.
  (`submission_analysis/application/authorization.py` 99의 `"2026-08-v1"`은 시험용 대역 객체의 고정값이다.)

### 미확인

- 없음. 화면에 남은 이전 정책으로 제출하는 경로(V4 §10.3 "우회")는 교체 수단 없이도 이전 해시를 직접 보내 재현할 수 있고,
  Clarify에서 이것만 판정 대상(N03-A1~A3)으로 정했다.

## 3. 재사용할 수 있는 ControlProof 부품

- 동의: `engine/adapters/whyyou/consent.py` `read_policy`(83~119)·`commit`(121~199, 낡은 정책 거부를 `CONSENT_POLICY_STALE`
  (32~36) → `CONSENT_POLICY_MISMATCH`(172~176)로 대응)·`read_state`(201~274, projection 276~334).
- 시드: N-02 지원자 쿠키 시드(`seeds/n02_subjects.py` 23·93~99, pepper·HMAC)와 정리(`engine/adapters/whyyou/n02_cleanup.py`).
- 브라우저: Playwright sync API(`browser.py` 61~70), `playwright>=1.55`는 이미 의존성이다.
- 하네스: `scripts/spec004_local.py`(합성 DB·큐·고정 모델 API/작업자 기동, 프런트엔드는 띄우지 않음, 콘솔 URL 고정),
  `scripts/n02_local.py`(환경 덮어쓰기 진입점), `scripts/h01_local.py`·`h02_local.py`(보성, `--instance`·`--state-root` 방식).
- 프로필 등록 선례: 보성의 H-01(`H01_HUMAN_DECISION_V1`, `scenarios/H-01.yaml`, `engine/h01*.py`, `engine/executors/h01.py`,
  `engine/web/h01_review.py`)과 H-02. N-01·N-03도 같은 지점을 같은 모양으로 확장한다(Plan).

## 4. 구매자·데이터 범위와의 관계 (2026-10-19 팀 방향)

팀은 공급기업과 채용기업 모두를 구매자로 보고, 받는 데이터에 따라 판정 가능한 항목이 달라진다고 정했다. N-01은 화면·API 접근,
N-03은 API 접근으로 시험할 수 있어 두 구매자 모두 대상이 된다. 이 구분은 Spec 009 FR-005(대상 접근 종류)로 들어갔다.
