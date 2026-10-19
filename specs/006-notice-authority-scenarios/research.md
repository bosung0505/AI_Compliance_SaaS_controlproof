# Research: Spec 006 N-01·N-03·H-01·H-02

- 조사일: 2026-10-19 (Plan Phase 0)
- 대상: ControlProof `006-notice-authority-scenarios`(`fa3310c` 기준), WhyYou `33aa996`
- 방법: WhyYou는 `git show 33aa996:<경로>`·`git grep … 33aa996`으로만 읽었다. checkout 브랜치는 바꾸지 않았다. Run·DB 조회·
  서버 기동·다운로드는 하지 않았다.
- 경로 표기: `BE/` = WhyYou `backend/src/interview_evidence/`. 줄 번호는 `33aa996` 기준이다.
- 결과를 예측하는 문장은 쓰지 않는다. 아래는 소스에서 읽은 사실과 그에 따른 설계 결정이다.

## R0. Plan 중 제품 해석 질문 (열림)

| ID | 질문 | 추천 | 상태 |
|---|---|---|---|
| Q-P1 | AI 어시스턴트 답변 경로가 부르는 기본 단계 채움(`ensure_default_stages`)은 H02-A3의 "채용 단계 쓰기 도달"인가 | A: 도달로 본다 | 제품 책임자 답 대기 |
| Q-P2 | 어시스턴트에 주입된 객체가 쓰기 메서드를 갖고 있지만 부르지 않으면 H02-A3 FAIL인가 | B: FAIL 아님, 관찰·한계로 기록 | 제품 책임자 답 대기 |

근거와 선택지는 R4.3에 있다. 두 질문의 답은 `contracts/h02-write-surface-v1.md`의 금지 집합과 도달 규칙에만 영향을 주고,
모듈 구조·작업 분해는 바꾸지 않는다.

## R1. H-01 — 기본 단계 배정이 최종 단계를 배정할 수 있는가 (기준선 1절 미확인 1)

**사실**

- `HiringService.ensure_default_stages`(`BE/company_management/application/hiring_service.py` 127~160)는 포지션에 단계가 없으면
  기본 다섯 단계(보류·검토·1차 합격·최종합격·불합격, `BE/company_management/domain/hiring.py` 15~21)를 저장하고(133~147),
  `recruiting_stage_id`가 비어 있는 초대마다 `_default_stage_name(invitation.status)`로 단계를 골라
  `move_to_recruiting_stage`로 저장한다(148~159, 155). 감사 기록은 남기지 않는다.
- 상태→단계 대응(340~351): `interrupted`·`expired`·`revoked` → 보류, `completed` → 1차 합격, `reviewed`·`deleted` →
  최종합격, 나머지 → 검토. **최종합격은 배정할 수 있고 불합격은 배정하지 않는다.** 단계의 "최종" 여부는 이름으로만 정한다(312).
  마이그레이션 `backend/alembic/versions/integration/i_018_recruiting_pipeline.py` 111~115도 같은 대응이다.
- 이 함수는 채용 단계 목록·상태 조회 GET 경로와 단계 편집·이동 경로(`BE/company_management/api/company_routes.py`
  796~1078), 최종결정 경로(`BE/integration/reporting_company.py` 103~114·133), 어시스턴트 답변 경로(R4)에서 호출된다.
  회사 경로는 모두 `COMPANY_USER` 인증 뒤에만 닿는다.
- `move_applicants`(296~337)는 대상이 최종 단계이고 `require_final_report=True`일 때만 리포트 `ready`를 요구한다(321~331).
  일괄 이동 PATCH는 `True`(1008), 최종결정 POST 경로는 기본값 `False`이고 `FinalDecisionService`는 리포트 존재만 본다
  (`BE/reporting/application/final_decision_service.py` 63~65).

**결정**

- H-01 합성 지원자는 `recruiting_stage_id`를 미리 채운(검토 단계) 상태로 시드해 기본 단계 채움이 시도 대상에 끼어들지 않게 한다.
- 전후 projection에 `recruiting_stages`(포지션 단위)를 넣어 기본 단계 채움의 흔적도 비교한다.
- 일괄 이동 경로 기준 동작은 리포트 `ready`가 필요하므로 H-01 시드는 Spec 004 lane 행 방식(`seeds/spec004_subjects.py`의
  ready 리포트·리뷰 행)으로 만든다. H-03 대기 리포트 시드(`seeds/h03_pending_report.py`)는 리포트를 비우므로 쓰지 않는다.

**대안**: H-03 시드 재사용 — 일괄 이동 기준 동작이 `final report is not available`로 거부돼 H01-A1을 판정할 수 없어 버렸다.

## R2. H-01 — 거부된 호출의 흔적 (기준선 1절 미확인 2)

**사실**

- 최종결정 POST(`BE/reporting/api/company_routes.py` 626~679)는 `company_scope` 의존성(385~408)이 Bearer 부재·형식 오류·
  미등록 토큰에 401을 먼저 낸다. `Idempotency-Key`는 헤더 값일 뿐(411) 의존성 단계에서 저장되지 않는다.
- 일괄 이동 PATCH(`BE/company_management/api/company_routes.py` 985~994)는 `Idempotency-Key`를 받지 않는다. 인증은
  `company_scope`(512~528)이고 401은 DB 호출 전에 반환된다(516~526).
- 지원자 쿠키 `iep_applicant_session`은 회사·리포팅·어시스턴트 경로에서 읽지 않는다. 쿠키만 보내면 Bearer 부재로 401이다.
  지원자 세션 값을 Bearer로 보내도 회사 principal 제공자가 401을 낸다(`BE/runtime/production.py` 284~289).
- 위조 Bearer는 local 모드에서 `LOCAL_COMPANY_ACCESS_TOKEN`과 상수 시간 비교 뒤 401이다(`BE/shared/security/local.py` 49~52·84~85).
- 최종결정 성공 순서(`final_decision_service.py` 54~126): 리포트 확인 → 재전송 방지 조회 → 단계 이동 → `human_reviews` 저장 →
  초대 검토 종료 → 감사 `final_decision.create`(103~115) → 재전송 방지 저장(116~121).
- **재전송 방지 저장소**: 실제 연결된 최종결정 라우터는 `idempotency=` 없이 만들어져(`BE/runtime/production.py` 509~524)
  프로세스 메모리 저장소(`BE/reporting/api/company_routes.py` 377)를 쓴다. DB 표 `command_idempotency`(`i_002` 115~122)에는
  최종결정 키가 저장되지 않는다(정적 읽기, 실행 확인 아님).
- 트랜잭션 미들웨어는 500 미만 응답을 모두 commit한다(`BE/shared/database.py` 56~74). 인증된 4xx 앞의 기본 단계 채움은 남는다.
  401은 DB 호출 전이라 해당하지 않는다.

**결정**

- 전후 projection: `invitations`(`status`, `row_version`, `recruiting_stage_id`, `pipeline_row_version`), `human_reviews`,
  `invitation_state_history`, `recruiting_stages`(포지션), `command_idempotency`(대상 회사·키), `audit_events`(대상 회사, 시도
  구간). 기존 `decisions.py` `capture_reset_token`(226~272)이 읽는 행 집합을 넓힌다.
- 최종결정 경로의 재전송 방지 기록은 DB에 없으므로 **행동 관찰**로 확인한다. 전후 비교가 끝난 뒤 정상 회사 사용자가 거부 시도에
  쓴 것과 같은 `Idempotency-Key`로 결정을 보내 응답이 새 생성인지 재생인지 기록한다. 이 관찰은 거부 지원자 상태를 바꾸므로
  H01-A3 비교 이후에만 하고 복구 대상에 넣는다. 일괄 이동 경로는 키가 없으므로 해당 없음으로 기록한다.
- 처리기가 여러 프로세스면 메모리 저장소 관찰이 무의미하므로 하네스의 API 프로세스가 하나인지 preflight에서 확인한다
  (`scripts/spec004_local.py`의 uvicorn 기동 인자).

**대안**: DB 표만 비교 — 최종결정 키가 DB에 없어 "기록 없음"이 무변경인지 수집 불가인지 구분할 수 없어 버렸다.

## R3. H-01 — 감사 기록 (H01-A4)

**사실**

- 감사 표 `audit_events`: `audit_event_id`, `company_id`(NOT NULL), `actor_type`, `actor_id`(NOT NULL), `action`,
  `resource_type`, `resource_id`, `result`, `occurred_at`, `request_id`, `trace_id`, `metadata`(JSON)
  (`i_002_runtime_persistence.py` 44~60, `BE/shared/persistence.py` 74~88). 실패 사유 전용 열은 없다.
- 감사 쓰기는 `TenantContext`(회사·주체)를 요구한다. 인증 실패를 기록하는 미들웨어·예외 처리기·감사 action은 소스에 없다
  (`BE/main.py` 40~57, `database.py` 57, 리포팅 not-found 처리기 762만 있음). 감사 조회 HTTP 경로도 없다.

**결정**

- H01-A4는 DB projection으로 시도 구간(`occurred_at` 시도 시작~종료, 대상 회사)의 `audit_events`를 읽는다. 시도와의 연결은
  ControlProof가 보낸 `X-Request-Id`·`X-Trace-Id`와 `request_id`·`trace_id`, 그리고 `resource_id`가 대상 지원자 관련 id인지로 한다.
- 시도별 요건(spec FR-025): 주체 구분(익명 / 인정되지 않은 자격 / 지원자 + 지원자 식별자), 시각, 대상 지원자, 실패 사유. 실패
  사유는 `result` 또는 `metadata`의 값으로 찾는다. 한 요건이라도 없으면 그 시도는 미충족이다.
- 감사 표를 읽지 못하면(접속·권한 오류) `INCONCLUSIVE`(`INSUFFICIENT_EVIDENCE`).

## R4. H-02 — 어시스턴트 주입 지점과 작업자 처리 목록 (기준선 2절 미확인)

### R4.1 어시스턴트

- 경로(`BE/recruiting_assistant/api.py`, prefix `/v1`): POST `/assistant/search`(216~251), POST `/assistant/answers`(253~283),
  POST `/assistant/answers/stream`(285~344). 모두 Bearer → `COMPANY_USER`(129~152).
- 주입 대상(`create_assistant_router` 117~126, Protocol 90~107): `principal_provider`, `company_service`, `search_service`,
  `answer_service`, `audit`, `clock`, `pipeline_reader: RecruitingPipelineReader | None`.
- 실제 연결(`BE/runtime/production.py` 525~533): `pipeline_reader=lane_a.hiring_service` — Protocol은 읽기 전용이지만 넣은
  객체는 전체 `HiringService`(`BE/company_management/api/__init__.py` 103~108)다.
- `_pipeline_answer`(198~208, 호출 371·386·390·421)는 `list_recruiting_stages`·`list_invitations`를 부르고, 둘 다
  `ensure_default_stages`를 부른다(`hiring_service.py` 123~125·162~171). R1의 기본 단계 채움으로 이어진다.
- 같은 객체는 `move_applicants`, 단계 생성·이름 변경·순서 변경·삭제, `issue_invitations`도 갖지만 `api.py`는 부르지 않는다.
- `recruiting_assistant/` 모듈은 `HiringService`를 import하지 않는다. 쓰기 능력은 런타임 주입으로만 들어온다.
- `FinalDecisionService`, `ReviewService.record_*`, `HumanReview.recruiting_stage_decision`에는 어떤 주입 객체도 닿지 않는다.

### R4.2 작업자

- `EVENT_QUEUE_ROUTING`(`BE/runtime/worker.py` 109~127): 다섯 큐, 열일곱 사건.
- 운영 처리기 대응(`create_production_worker_runtime` 883~940): 아홉 사건에 처리기 일곱 종(분석 요청·완료, 면접 완료, 미디어,
  리포트 요청, 삭제 요청·보관 만료, 수용량 둘). 나머지 사건은 "ignored"로 확인 응답한다(`BE/shared/messaging/worker.py` 262~267).
- 작업자 맥락은 `ActorType.SYSTEM`(`messaging/worker.py` 268~274).
- 동적 디스패치: 삭제 실행기 dict(`production.py` 398~403), `Runtime.worker_handlers` dict(565~582), 허용 접두사로 제한된
  `importlib`(`BE/interview_engine/application/idempotency.py` 227~235, `BE/workers/reporting/media.py` 24), capability
  `getattr` 몇 곳(`integration/privacy_deletion.py` 201, `reporting/application/public.py` 251, `production.py` 442,
  `messaging/worker.py` 181·350·378·428).
- `InterviewCompletedEventHandler`는 초대 상태를 `ready → interviewing → completed`로 옮긴다(`worker.py` 340·351). 채용 단계·
  최종결정 함수 참조는 작업자·`workers/`·수용량·메시징에서 grep으로 찾지 못했다.

### R4.3 금지 집합과 열린 질문

**확정 금지 집합(정의 위치)** — 최종결정·사람 검토 쓰기와 지원자 단계 이동:

- `FinalDecisionService.record`(`BE/reporting/application/final_decision_service.py` 54)
- `ReviewService.record_final_decision`(220), `ReviewService.record_recruiting_stage_decision`(244),
  `ReviewService.close_invitation_review`(92) (`BE/reporting/application/review_service.py`)
- `HumanReview.final_decision`(93), `HumanReview.recruiting_stage_decision`(123) (`BE/reporting/domain/review.py`)
- `Invitation.move_to_recruiting_stage`(`BE/company_management/domain/hiring.py` 208)
- `HiringService.move_applicants`(296), `ReportingHiringBoundary.move_to_recruiting_stage`(`BE/integration/reporting_company.py` 95)
- 저장 경계: 지원자 단계 열(`recruiting_stage_id`·`pipeline_row_version`)을 쓰는 `save_invitation`
  (`BE/company_management/repositories/postgres.py` 974, 994~995), `save_review`(`BE/reporting/repositories/postgres.py` 1019)

**Q-P1. 기본 단계 채움** — 어시스턴트 답변 경로는 `ensure_default_stages` → `Invitation.move_to_recruiting_stage` →
`save_invitation`에 정적으로 닿는다. 이 쓰기는 `recruiting_stage_id`가 빈 이전 초대에만 일어나고, 상태가
`reviewed`·`deleted`이면 최종합격을 배정한다.

- A(추천): 도달로 본다. spec FR-042의 "직접 또는 간접 도달"과 V4 §10.5 "문이 아예 없는가"를 글자 그대로 따른다. 사람이 아닌
  경로가 최종합격 값을 쓸 수 있다는 사실은 이유와 무관하게 쓰기 노출이다.
- B: 도달에서 뺀다. 기존 상태(사람 결정 뒤의 `reviewed`)를 기본 단계로 반영하는 이전 데이터 채움으로 보고 관찰로만 남긴다.
  `reviewed`는 사람 결정 뒤에만 생기지만, 대응표는 실제 결정이 불합격이어도 최종합격을 고른다는 점에서 B의 근거가 약하다.

**Q-P2. 주입 객체의 미사용 쓰기 메서드** — 어시스턴트가 받은 `HiringService`는 `move_applicants` 등을 갖지만 호출하지 않는다.

- A: 쓰기 메서드를 가진 객체를 받는 것 자체를 노출로 보고 FAIL로 판정한다.
- B(추천): 판정은 호출 도달로만 한다. 미사용 쓰기 메서드는 항목의 "보유 능력" 관찰과 결과 한계로 기록한다. 호출 도달은
  정적으로 결정 가능하지만 보유 기준은 서비스 주입을 쓰는 거의 모든 경로를 FAIL로 만들어 판정이 구분력을 잃는다.

**도달 분석 규칙(질문과 무관하게 확정)**

- 시작점: 어시스턴트 공개 경로 처리 함수 세 개, 작업자 운영 처리기 대응표의 처리기 `handle` 메서드.
- 주입 해석: Protocol 주석이 아니라 실제 연결 모듈(`BE/runtime/production.py`)의 생성 인자로 구체 클래스를 정한다. 연결을
  정적으로 읽지 못하면 그 항목은 `INCONCLUSIVE`.
- 깊이: 같은 저장소 안의 함수·메서드 호출을 금지 집합이나 외부 라이브러리에 닿을 때까지 따라간다. 상한 12단계, 상한에서 끊기면
  `INCONCLUSIVE`.
- 동적 디스패치: dict 등록·`getattr`·`importlib`가 시작점에서 닿는 경로에 있으면, 키·이름이 상수로 정해지는 경우만 해석하고
  아니면 그 항목은 `INCONCLUSIVE`.

## R5. N-01 — 지원자 앱 로컬 기동과 동의 화면 (기준선 3절 미확인)

**사실**

- `apps/applicant-interview/package.json` 6~11: `dev`=`vite`. 루트 `package.json` 10~26: `dev:applicant`.
- `apps/applicant-interview/vite.config.ts` 7~21: `127.0.0.1:5174`, `strictPort`, `/v1` 프록시 대상 `http://127.0.0.1:8080` 고정.
  API 기준은 `VITE_API_BASE_URL ?? ""`(`src/app/routeAdapters.tsx` 44). 백엔드에 CORS가 없어(설정 주석) 같은 출처 프록시가 필요하다.
- `.env.example` 153·155: `APPLICANT_ACCESS_BASE_URL=http://localhost:5174/access`, 포트 5174.
- 동의 단계 진입: 화면은 항상 `exchange`에서 시작해(`features/access/index.tsx` 215) URL 초대 토큰 교환(265~268) → 본인 확인
  (277) → 동의(361~438). 초대 토큰은 `HMAC-SHA256(pepper, raw)`로 `invitations.token_hash`에 저장된다
  (`BE/company_management/adapters/applicant_session.py` 97~112, local pepper `b"local-development-pepper"`). 본인 확인은 표시
  이름 대소문자 무시 비교다(`applicant_access_service.py` 102~129).
- 동의 화면 문구 출처: `policy.aiRole`(375, AI 사용과 사람의 최종 결정), `policy.recordingNotice`(378), "보관기간" 라벨 +
  `retentionDays`(382~385), "삭제 방법" 라벨 + `deletionMethod`(388~391), 처리 목적 체크박스(398~423). 접힘 영역은 없다.
- `DEFAULT_CONSENT_POLICY`(`BE/company_management/domain/applicant_access.py` 54~86): `policy_version` `2026-08-v1`,
  `ai_role`, `recording_notice`, 목적 셋(document_analysis·recording·ai_assessment), `retention_days` 180, `deletion_method`.

**결정**

- 지원자 앱은 하네스 API 포트가 8080일 때만 프록시로 붙는다. `scripts/spec006_local.py`는 `--api-port 8080`을 기본으로 넘기고,
  포트가 쓰이고 있으면 기동을 거부한다. 앱은 `npm run dev:applicant`(WhyYou 쪽 `node_modules` 필요)로 하네스가 띄운다.
- N-01 시드: Run마다 만든 원시 초대 토큰의 HMAC를 `invitations.token_hash`에 넣은 `invited` 합성 초대. 브라우저는
  `/access/<raw>`로 들어가 교환·본인 확인을 제품 흐름으로 진행한다. N-02 시드의 pepper·HMAC 방식(`seeds/n02_subjects.py` 23·93~99)을 재사용한다.
- 다섯 항목의 기대 문구는 서버가 준 정책 값에서 만든다: AI 평가 보조 = `ai_role`의 AI 부분 + `ai_assessment` 목적, 사람의 최종
  결정 = `ai_role`의 사람 결정 부분, 녹화·처리 목적 = `recording_notice` + 처리 목적, 보관기간 = 라벨 + `retention_days`, 삭제
  방법 = 라벨 + `deletion_method`. 화면 요소 찾기(텍스트 일치)는 어댑터 설정에 두고 판정기는 요소별 측정값만 받는다
  (Constitution IV).

**대안**: `VITE_API_BASE_URL`로 18085 직접 호출 — CORS가 없어 버렸다. vite 설정 수정 — WhyYou 변경이라 범위 밖이다.

## R6. N-03 — 동의 어댑터 재사용과 이전 정책 식별값

- ControlProof `engine/adapters/whyyou/consent.py`: `read_policy`(83~119), `commit`(121~199, 낡은 정책 거부를
  `CONSENT_POLICY_STALE`(32~36) → `CONSENT_POLICY_MISMATCH`(172~176)로 대응), `read_state`(201~274, projection 276~334).
- WhyYou 거부: `applicant_access_service.py` 143~147(버전·해시 중 하나라도 다르면) → 422(`applicant_routes.py` 331). 동의 기록은 `policy_version`(153)과
  `evidence_digest=consent_content_digest`(157)를 저장한다. 동의 POST는 `Idempotency-Key`를 받고 버린다(319).
- 동의 기록 감사(`audit_events`)는 없다. 동의는 `consent_records`, `invitation_state_history`, outbox `invitation.consent_completed`를 쓴다.

**결정**: 이전 정책 식별값 = 서버 현재 값의 버전에 접미사를 붙이고 해시의 마지막 16진 한 자리를 바꾼 값(두 값 모두 현재와 다름을
기록). 결과 한계에 "실제 교체 없이 만든 값"을 남긴다. 과거 동의용 합성 지원자는 Run 시작 때 제품 흐름(POST)으로 동의를 완료해 둔다.

## R7. ControlProof 재사용과 확장 지점

- 프로필 하드코딩 지점: `engine/models.py` 85~92(enum)·330~457(canonical)·518~522(환경 스냅샷 범위)·1807~1872(Run 검증),
  `engine/scenario.py` 301~460(시나리오 검증, 복구 필수 452~453, 모델 fixture 필수 454~455), `engine/runner.py` 913~922,
  `engine/cli.py` 633~672, `engine/evidence.py` 113~265, `tests/unit/test_catalog_matrix_parity.py`(69: 5/4/3, 89: 7 프로필).
- `ScenarioDefinition`은 알 수 없는 키를 거부한다(`engine/scenario.py` 218~219). 대상 접근 종류 필드는 모델 변경이 필요하다.
- 결정 어댑터 클라이언트는 회사 Bearer를 고정으로 싣는다(`engine/adapters/whyyou/client.py` 32~37). `attempt`는 회사 사용자
  불일치를 `COMPANY_ACTOR_MISMATCH`로 막는다(`decisions.py` 114~115). 거부 주체용 별도 클라이언트가 필요하다.
- 브라우저 어댑터는 Playwright sync API(`browser.py` 61~70)이고 `playwright>=1.55`는 이미 의존성이며 `.venv`에 있다. Chromium
  실행 파일 존재는 `capability.py` 487~501이 본다.
- 하네스 `scripts/spec004_local.py`는 API·작업자만 띄우고 프런트엔드는 띄우지 않는다(279~306, 콘솔 URL 145 고정).
  `scripts/n02_local.py`는 환경을 덮어쓰는 31줄 진입점이다.
- 워크벤치 표시 지점: 결과 화면 한계 줄 `engine/web/templates/run.html` 130~132(`readmodel.py` 474~487), 시나리오 화면
  `scenario.html` 28·91(`readmodel.scenario` 634~680). `engine/web/review.py` 14~17·27~30에 네 시나리오 제목·설명이 이미 있다.

## R8. 다운로드·설치 필요 사항 (실행하지 않음)

- WhyYou 실행 checkout의 `npm install`(지원자 앱 `node_modules`). 실제 Run 준비 때 별도 승인.
- Playwright Chromium: `capability.py` 487~501 probe로 확인한다. 없으면 `playwright install chromium`이 필요하다(별도 승인).
- Python 새 의존성: 없음(`ast`·`subprocess`는 표준 라이브러리).
