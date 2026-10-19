# Research: Spec 009 N-01·N-03

- 조사일: 2026-10-19 (Plan Phase 0). Spec 006 초안의 R5·R6·R7·R8(2026-10-19, WhyYou `33aa996` 기준)을 옮기고 ControlProof `b76af4c`,
  WhyYou `0166d9e`로 다시 확인했다.
- 방법: WhyYou는 `git show <sha>:<경로>`·`git grep … <sha>`로만 읽었다. Run·DB 조회·서버 기동·다운로드는 하지 않았다.
- 경로 표기: `BE/` = WhyYou `backend/src/interview_evidence/`, `APP/` = WhyYou `apps/applicant-interview/`. 줄 번호는 `0166d9e`
  기준이며, 이 문서가 인용하는 WhyYou 파일은 `33aa996`과 바이트가 같다(원천 기준선 머리말).
- 결과를 예측하는 문장은 쓰지 않는다. 아래는 소스에서 읽은 사실과 그에 따른 설계 결정이다.

## R0. 열린 제품 해석 질문

없다. Spec 006 초안의 Q-P1·Q-P2는 H-02 전용이었고 보성의 Spec 007이 H-02를 마감했다.

## R1. N-01 — 지원자 앱 로컬 기동과 동의 화면

**사실**

- `APP/package.json` 6~11: `dev`=`vite`. WhyYou 루트 `package.json` 10~26: `dev:applicant` = `npm run dev --workspace
  @iep/applicant-interview`. 의존성은 npm workspace라 루트 `node_modules`에 설치되고 앱 폴더에는 `node_modules`가 없다
  (연우 PC 2026-10-19 확인: 루트 `node_modules/@iep/applicant-interview` 있음).
- `APP/vite.config.ts` 7~21: `host 127.0.0.1`, `port 5174`, `strictPort`, `/v1` 프록시 대상 `http://127.0.0.1:8080` 고정, `ws: true`.
  API 기준은 `VITE_API_BASE_URL ?? ""`(`APP/src/app/routeAdapters.tsx` 44). 백엔드에 CORS가 없어(설정 주석) 같은 출처 프록시가
  필요하다. 요청은 `credentials: "include"`(81)로 쿠키를 보낸다.
- 동의 단계 진입: 화면은 항상 `exchange`에서 시작해(`APP/src/features/access/index.tsx` 215) `POST /v1/applicant/access/exchange`
  (routeAdapters 195~201, `Idempotency-Key` 동봉) → `POST /v1/applicant/identity-verifications`(202~209, `display_name`) → `GET
  /v1/applicant/consents`(211~224) → `consent` 단계(361~438)로 간다. 초대 미리보기 `POST /v1/applicant/access/preview`(156)는 토큰이
  32자 이상일 때만 부른다(index.tsx 229).
- 초대 토큰은 `HMAC-SHA256(pepper, raw)`로 `invitations.token_hash`에 저장된다(`BE/company_management/adapters/applicant_session.py`
  97~112, local pepper `b"local-development-pepper"`). 본인 확인은 표시 이름 대소문자 무시 비교다
  (`BE/company_management/application/applicant_access_service.py` 102~129). 교환 성공 시 `iep_applicant_session` 쿠키가 발급된다.
- 동의 화면 구조(index.tsx 361~438): `<section aria-label="동의 정책">` 안에 `policy.aiRole` 문단(375), `policy.recordingNotice`
  문단(378), `<dl>`의 `보관기간`/`{retentionDays}일`(382~385)과 `삭제 방법`/`{deletionMethod}`(388~391). `<form>` 안에 처리 목적
  체크박스 행 세 개(`<label>` + `<strong>{title}</strong>` + `<small>{description}</small>`, 398~423)와 제출 버튼 "동의하고 계속"
  (426~437, 세 목적을 모두 체크해야 활성). 접힘 영역은 없다. 모바일(≤600px)은 `mw-600:` 변형으로 dt·dd를 한 열로 쌓는다.
- 제출(routeAdapters 226~235): `POST /v1/applicant/consents` body `{policy_version, accepted_purposes, consent_content_digest}`,
  값은 화면이 `GET`으로 받은 `policy_version`·`content_digest`다. 성공 시 `ready` 단계.
- 정책 원천: `DEFAULT_CONSENT_POLICY`(`BE/company_management/domain/applicant_access.py` 54~86): `policy_version` `2026-08-v1`,
  `ai_role`("AI는 지원자 자료를 바탕으로 질문과 평가 초안을 만들지만 최종 채용 결정은 기업의 사람이 수행합니다."),
  `recording_notice`, 목적 셋(`document_analysis` "문서 분석", `recording` "면접 녹화", `ai_assessment` "AI 평가 보조", 각각
  `description` 있음), `retention_days` 180, `deletion_method`. `content_digest`는 정규화 JSON의 SHA-256(42~51).
  `GET /v1/applicant/consents`(`BE/company_management/api/applicant_routes.py` 274~298)가 이 값과 `content_digest`를 돌려준다.
- ControlProof 브라우저 어댑터(`engine/adapters/whyyou/browser.py`)는 Playwright sync API로 회사 콘솔만 1440×900으로 연다.
  Chromium 실행 파일 존재는 `engine/adapters/whyyou/capability.py`의 브라우저 probe가 본다. 연우 PC: Python 3.12.10, playwright
  1.63.0, `ms-playwright`에 `chromium-1243`·`chromium_headless_shell-1243`.

**결정**

- 지원자 앱은 하네스 API 포트가 8080일 때만 프록시로 붙는다. `scripts/spec009_local.py`는 `--api-port 8080`을 기본으로 넘기고,
  8080이나 5174가 쓰이고 있으면 `up`을 거부한다. 앱은 WhyYou 루트에서 `npm run dev:applicant`로 하네스가 띄우고 `stop`이 내린다.
  `node_modules`가 없으면 설치하지 않고 실패한다(설치는 별도 승인).
- N-01 시드: Run마다 만든 원시 초대 토큰의 HMAC를 `invitations.token_hash`에 넣은 `invited` 합성 초대. 브라우저는
  `/access/<raw>`로 들어가 교환·본인 확인을 제품 흐름으로 진행한다. N-02 시드의 pepper·HMAC 방식(`seeds/n02_subjects.py`)을
  재사용한다. 초대 토큰은 교환 때 소비되므로 lane(`pc`·`mobile`)마다 따로 둔다.
- 다섯 항목의 기대 문구 조각은 서버가 준 정책 값에서 만든다(contracts/assertions-v9.md 표). 화면 요소 찾기는 어댑터에 두고
  판정기는 조각별 측정값만 받는다(Constitution IV).
- 화면이 받은 정책 식별값은 페이지의 `GET /v1/applicant/consents` 응답을 Playwright 응답 관찰로 읽는다. 서버 현재 값은
  ControlProof가 같은 세션 쿠키로 `read_policy`를 따로 불러 읽는다. 저장 기록은 `read_state` projection으로 읽는다.
- 캡처 PNG에는 원시 초대 토큰이 보이지 않는다(headless라 주소창 없음). 캡처 직전 DOM 텍스트에 토큰·세션 값이 없는지 확인한
  결과를 증적에 남긴다.

**대안**: `VITE_API_BASE_URL`로 하네스 포트 직접 호출 — CORS가 없어 버렸다. vite 설정 수정 — WhyYou 변경이라 범위 밖이다.
ControlProof 쪽 vite `--config` 파일로 프록시 대상을 바꾸기 — WhyYou 변경 없이 가능해 보이지만 앱 `node_modules`의 플러그인을
다른 폴더의 설정에서 불러야 해서 지금은 쓰지 않는다. 8080 충돌이 실제로 문제가 될 때 다시 본다.

## R2. N-03 — 동의 어댑터 재사용과 이전 정책 식별값

**사실**

- ControlProof `engine/adapters/whyyou/consent.py`: `read_policy`(83~119), `commit`(121~199, 낡은 정책 거부를
  `CONSENT_POLICY_STALE`(32~36) → `CONSENT_POLICY_MISMATCH`(172~176)로 대응), `read_state`(201~274, projection 276~334).
- WhyYou 거부: `applicant_access_service.py` 143~147(버전·해시 중 하나라도 다르면 `ValueError("consent policy version or digest is
  stale")`) → 422(`applicant_routes.py` 331~335). 동의 기록은 `policy_version`(153)과 `evidence_digest=consent_content_digest`(157)를
  저장한다. 동의 POST는 `Idempotency-Key`를 받고 버린다(319~327).
- 동의 기록 감사(`audit_events`)는 없다. 동의는 `consent_records`, `invitation_state_history`, outbox `invitation.consent_completed`를
  쓴다. 실행 중 정책을 바꿀 수단이 없고 분석 작업에 정책 버전이 저장되지 않는다(원천 기준선 2절).

**결정**

- 이전 정책 식별값 = 서버 현재 값의 버전에 접미사(`-stale`)를 붙이고 해시의 마지막 16진 한 자리를 바꾼 값. 두 값이 모두 현재와
  다름을 시드 검증으로 확인하고 결과 한계 N03-L1("실제 교체 없이 만든 값")을 남긴다.
- lane `stale`은 N-02 쿠키 시드(동의 전 지원자), lane `past`는 Run 시작 때 제품 흐름(`commit`)으로 동의를 완료해 둔 별도 지원자.
  `past` 전후 snapshot은 `read_state` projection의 `consent_records` 전체 열을 비교한다.
- 복구: Run 소유 지원자·초대·세션·동의·상태 이력·outbox 행을 N-02 정리 어댑터(`engine/adapters/whyyou/n02_cleanup.py`) 방식으로
  지우고 잔여 0을 확인한다.

## R3. ControlProof 재사용과 확장 지점 (`b76af4c`)

보성이 H-01·H-02(Spec 006·007)를 등록한 지점이 그대로 N-01·N-03의 확장 지점이다. 줄 번호는 `b76af4c` 기준이다.

| 지점 | 파일·위치 | H-01 선례 | N-01·N-03 |
|---|---|---|---|
| 프로필 enum | `engine/models.py` 86~87 | `H01_HUMAN_DECISION_V1` | `N01_NOTICE_V1`, `N03_STALE_CONSENT_V1` |
| canonical 프로필 | `engine/models.py` 335~341, 449~450 | `ScenarioProfile.canonical` 분기, 적용 assertion 튜플 | 같은 분기 둘 |
| Run 검증 | `engine/models.py` 1819~1834 | 로컬 source·environment identity 요구 | 같은 요구 |
| 시나리오 검증 | `engine/scenario.py` 321~347, 506 | 프로필별 fixture·capability 고정 | v5 필드(`target_access`) + 프로필별 고정 |
| 실행기 등록 | `engine/runner.py` 18~19, 916~917 | `PROFILE_REGISTRY.register` | `N01Executor`, `N03Executor` |
| CLI | `engine/cli.py` 353~354, 650~651, 669~670 | 프로필 선택지·시나리오 대응·파일 대응 | 같은 세 곳 |
| 증적 계약 | `engine/evidence.py` 251~263, 750~754, 884~888, 941~945, 1033~1035 | `engine/h01_evidence.py`의 `REQUIRED_FILES`·`verify_links`·`verify_facts` | `engine/n01_evidence.py`, `engine/n03_evidence.py` |
| 재시험 | `engine/retest.py` 81~86 | child의 clean source·부모 cleanup 확인 | 같은 분기 |
| 검토 projection | `engine/presentation.py` 85 | 프로필별 summary 보정 | `target_access`·미검증 범위·한계 추가 |
| 웹 검토 | `engine/web/h01_review.py`, `readmodel.py`, `review.py` | 시나리오별 검토 모듈 | 공통 한 줄(대상 접근)만, 새 모듈 없음 |
| 하네스 | `scripts/h01_local.py`(`spec004_local` 래퍼, `--instance`·`--state-root`) | 환경 덮어쓰기 | `scripts/spec009_local.py` + 지원자 앱 기동 |
| 카탈로그 고정 | `tests/unit/test_catalog_matrix_parity.py` | 12/7/2/3·프로필 수 | closure 전 그대로 통과해야 함 |

- `ScenarioDefinition`은 알 수 없는 키를 거부한다(`engine/scenario.py`). 대상 접근 종류 필드는 schema v5로 넣는다.
- 동의 어댑터 클라이언트는 지원자 세션 쿠키를 다루며 회사 Bearer는 N-01·N-03에 필요 없다.
- 워크벤치 표시 지점: 결과 화면 한계 줄(`engine/web/templates/run.html`, `readmodel.py` run projection), 시나리오 화면 프로필
  준비 상태 옆(`scenario.html`, `readmodel.scenario`). `engine/web/review.py`에 N-01·N-03 제목·설명이 이미 있다.

## R4. 다운로드·설치 필요 사항 (실행하지 않음)

- WhyYou 실행 checkout의 `npm install`: 연우 PC 기본 checkout에는 이미 루트 `node_modules`가 있다. 새 worktree를 쓰면 다시 필요하다.
- Playwright Chromium: 연우 PC에 `chromium-1243`·`chromium_headless_shell-1243`이 있다(playwright 1.63.0). 없으면
  `playwright install chromium`이 필요하다(별도 승인).
- Python 새 의존성: 없음.
