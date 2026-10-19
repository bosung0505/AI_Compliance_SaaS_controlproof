# Implementation Plan: N-01·N-03·H-01·H-02 고지·사람 결정 권한 시나리오 실행

**Branch**: `006-notice-authority-scenarios`
**Date**: 2026-10-19
**Spec**: [spec.md](./spec.md)
**Status**: Draft. Plan 산출물 작성 완료. H-02 금지 집합의 제품 해석 질문 Q-P1·Q-P2(research R0·R4.3)가 답을 기다리고 있어
Tasks는 아직 만들지 않았다.

## Summary

카탈로그에서 `NOT_RUN`인 네 시나리오를 시나리오마다 실행 프로필 하나로 만들어 WhyYou 격리 로컬 스택(`LOCAL_EMULATED`)에서
실행하고, 기존 판정·봉인·복구·재시험 계약으로 결과를 남긴다.

- N-01 `N01_NOTICE_V1`: 지원자 앱 동의 단계를 PC 1440×900과 모바일 390×844로 열어 다섯 고지 항목의 텍스트·화면 안 위치·
  가림·가로 넘침을 측정하고, 화면·서버·저장 기록의 정책 식별값을 대조한다.
- N-03 `N03_STALE_CONSENT_V1`: 기존 동의 어댑터로 이전 정책 식별값 거부·최신 재확인 저장·과거 동의 불변을 판정한다. 교체 주입·
  근접 제출·분석 작업 정책 귀속은 미검증 범위로 표시한다("N-03 일부 실행").
- H-01 `H01_DECISION_AUTHORITY_V1`: 두 쓰기 경로(최종결정 POST, 일괄 이동 PATCH)마다 독립 합성 지원자로 정상 회사 사용자 기준
  동작과 세 거부 주체를 시도하고, DB projection으로 전후 상태·감사 기록을 비교한다.
- H-02 `H02_WRITE_SURFACE_V1`: 검사 대상 커밋의 소스를 `git show`로 읽어 Python `ast`로 어시스턴트 경로와 작업자 처리 목록을
  열거·분류하고 금지 집합 도달을 분석한다. 대상 상태를 바꾸지 않는다.

WhyYou는 바꾸지 않는다. 시험용 수단도 만들지 않는다(spec FR-023·FR-032).

## Technical Context

**Language/Version**: Python 3.12 이상(ControlProof `pyproject.toml`); WhyYou 지원자 앱은 Node·Vite(대상 쪽, 기동만)
**Primary Dependencies**: Pydantic 2, PyYAML, HTTPX, SQLAlchemy 2, psycopg 3, Jinja2, Playwright(이미 의존성) — 새 의존성 없음
**Storage**: WhyYou local PostgreSQL(하네스 compose), ControlProof 불변 file bundle(`.controlproof/runs`, 커밋 안 함)
**Testing**: pytest 단위·계약·통합·web, Ruff; 구현 뒤 승인된 actual-stack Run
**Target Platform**: Windows + Docker Desktop의 `LOCAL_EMULATED`; 실제 AWS는 `NOT_RUN`
**Project Type**: ControlProof CLI·검증 엔진·로컬 웹 워크벤치 + 외부 WhyYou adapter
**Performance Goals**: 준비된 스택에서 시나리오별 Run 540초, `verify` 60초, 합계 600초 이내(SC-009)
**Constraints**: 합성 데이터만, 외부 AI 차단, WhyYou 무변경, 실제 Run마다 연우 승인, closure 전 12/5/4/3 불변
**Scale/Scope**: 프로필 4, assertion 13(N01 3·N03 3·H01 4·H02 3), Evidence ID 10, 미검증 범위 항목 3(N03-U1~U3, 공통 AWS 별도), 한계 항목 4
**User Interface**: CLI·JSON·bundle; 결과 표시는 기존 워크벤치(`engine/web`) 한 줄 추가만
**Target Baseline**: WhyYou `bosung0505/gbsa_aws` `fixes-and-remaining-work` `33aa996`(D-024)

## Constitution Check

### Pre-design gate

| 원칙 | 확인 | 결과 |
|---|---|---|
| I. 판정은 증적에서만 | assertion마다 EV6 원본 요구, 측정·조회 실패는 `INCONCLUSIVE`, 텍스트 존재만으로 PASS 없음 | PASS |
| II. 대상·준비·결과 분리 | 접근 없음 `ACCESS_BLOCKED`, 실행기·Chromium·앱 미준비 `RUNNER_NOT_READY`, 대상 결함은 판정 | PASS |
| III. 사람의 최종 결정 | H-01·H-02가 직접 시험. ControlProof는 Run 소유 지원자에 기준 동작만 보내며 대신 결정하지 않음 | PASS |
| IV. 시나리오/adapter 분리 | 프로필·assertion·대상 접근은 YAML, 화면 요소 찾기·DB·소스 읽기는 adapter, 판정기는 측정값만 받음 | PASS |
| V. 격리·결정론·복구 | Run 소유 합성 지원자, 외부 AI 차단, N-01·N-03·H-01 상태 변경은 always-run 복구, H-02는 무변경 | PASS |
| VI. 불변 Run·재시험 | 기존 `retest` 계보 재사용, 최초 FAIL·INCONCLUSIVE 봉인 보존 | PASS |
| VII. 명세→증적 추적 | FR·SC·assertion·EV6 대응을 계약·Tasks·traceability에 연결 | PASS |

Constitution III의 "더 낮은 AI 점수의 지원자도 사람 판단으로 채용될 수 있어야 한다"는 Spec 006이 시험하지 않는다
(Clarify 답 4). 결과 한계로 표시하며 원칙 위반이 아니다.

### Post-design re-check

위반 없음. 기존 규칙의 프로필 한정 예외 두 개는 Complexity Tracking에 적는다: H-02의 복구·모델 fixture 생략, schema v5의
`target_access`. 둘 다 Spec 006 프로필에만 적용하고 v3·v4 검증 규칙은 바꾸지 않는다.

## Source-derived Boundary Map

| 시나리오 | 대상 접근 | WhyYou 경계(33aa996) | ControlProof 재사용 | 새로 만듦 |
|---|---|---|---|---|
| N-01 | 화면 + API | `/access/:token` 교환→본인 확인→동의, `GET/POST /v1/applicant/consents` | `consent.py` `read_policy`·`read_state`, Playwright, N-02 HMAC 시드 방식 | 지원자 화면 수집 어댑터, N-01 시드·판정기 |
| N-03 | API | `POST /v1/applicant/consents` 낡은 정책 422 | `consent.py` 전부, N-02 쿠키 시드 | N-03 시드·판정기 |
| H-01 | API | 최종결정 POST, 일괄 이동 PATCH, `audit_events` | `decisions.py` 경로 capability·`attempt`·`reset`, Spec 004 ready 리포트 행 | 주체별 클라이언트, 확장 projection, H-01 시드·판정기 |
| H-02 | 소스 열람 | `recruiting_assistant/api.py`, `runtime/worker.py`, `runtime/production.py` | 대상 스냅샷(git sha) | `ast` 표면 열거·도달 분석기, H-02 판정기 |

근거는 [research.md](./research.md) R1~R7.

## Execution Design

### 1. 프로필과 시나리오 정의

- `engine/models.py` `ExecutionProfile`에 네 값과 `SPEC006_PROFILES` 집합을 더한다. 각 `ScenarioProfile.canonical`은
  [contracts/scenario-profile-v5.md](./contracts/scenario-profile-v5.md)를 따른다.
- 시나리오 파일 `scenarios/N-01.yaml`·`N-03.yaml`·`H-01.yaml`·`H-02.yaml`, `schema_version: controlproof.scenario.v5`.
  v5 = v4 + `target_access`(필수, `SCREEN`·`API`·`SOURCE` 부분집합) + `unverified_scope_items`(선택) + `limitations`(선택).
- `target_access`는 Spec 006 네 파일에만 둔다. 기존 v3·v4 YAML은 바꾸지 않는다. 바꾸면 봉인된 Run의 시나리오 snapshot과 다른
  정의가 생긴다. 나머지 여덟 시나리오의 접근 종류 기록은 범위 밖이다(spec SC-013 범위와 같음).

### 2. 준비 상태와 대상 접근

- `engine/readiness.py`의 판정 순서는 그대로 쓴다. 접근 종류별 probe를 `engine/adapters/whyyou/capability.py`에 더한다.
  - `SCREEN`: 지원자 앱 URL(`CONTROLPROOF_APPLICANT_APP_URL`) 응답 없음 → `ACCESS_BLOCKED`. Chromium 실행 파일 부재 →
    `RUNNER_NOT_READY`(실행기 준비 문제).
  - `API`: 기존 OpenAPI·`/v1/me` probe. 401·403·연결 거부 → `ACCESS_BLOCKED`.
  - `SOURCE`: `WHYYOU_REPO_PATH`에서 `git cat-file -t <대상 커밋>`이 `commit`이 아니면 `ACCESS_BLOCKED`.
- 새 준비 상태 값은 없다(spec FR-005).

### 3. N-01 실행 순서

1. 시드: lane `pc`·`mobile` 각각 Run 소유 `invited` 합성 초대(원시 초대 토큰 Run마다 생성, `token_hash` HMAC, 합성 표시 이름).
   초대 토큰은 교환 때 소비되므로 화면마다 따로 둔다.
2. 각 lane의 새 브라우저 컨텍스트에서 `/access/<raw>` → 교환 → 본인 확인(표시 이름 입력) → 동의 단계 도달.
3. 동의 단계에서 항목별 측정: 기대 문구와 일치하는 요소, 경계 상자 대 viewport, 요소 중심점의 `elementFromPoint`가 그 요소(또는
   자손)인지, 문서와 요소의 `scrollWidth > clientWidth`. 필요한 조작(세로 스크롤)을 기록하고 전체 화면 캡처를 남긴다.
4. 화면이 받은 정책 식별값은 페이지의 `GET /v1/applicant/consents` 응답을 Playwright 응답 관찰로 읽는다. 서버 현재 값은
   ControlProof가 같은 세션으로 따로 읽는다(`read_policy`, 브라우저 컨텍스트 쿠키 사용).
5. 화면에서 체크박스 선택 → "동의하고 계속". 저장 기록(`consent_records.policy_version`·`evidence_digest`)과 동의 완료 시각을
   `read_state` projection으로 읽는다.
6. 복구: Run 소유 초대·세션·동의·상태 이력·outbox 행 정리, 잔여 0 확인.

### 4. N-03 실행 순서

1. 시드: lane `stale`(동의 전 지원자, N-02 쿠키 시드), lane `past`(Run 시작 때 제품 흐름으로 동의 완료).
2. `past` 기록 전 snapshot.
3. `stale`: 현재 정책 읽기 → 이전 정책 식별값(research R6) 제출 → 동의 기록·상태·상태 이력·outbox 전후 비교.
4. `stale`: 최신 정책 다시 읽기 → 그 값으로 제출 → 저장 기록 식별값과 재조회 값 비교.
5. `past` 기록 후 snapshot과 비교.
6. 미검증 범위 항목 N03-U1~U3를 결과에 기록(판정 없음). 복구·잔여 확인.

### 5. H-01 실행 순서

1. 시드: 경로마다 기준 지원자 1명과 거부 시도 지원자 1명(lane `fd-baseline`·`fd-denied`·`bm-baseline`·`bm-denied`). 모두
   ready 리포트·검토 단계 배정 상태(research R1).
2. 기준 동작(H01-A1): 정상 회사 사용자로 `*-baseline`에 결정. 기준이 실패하면 그 경로의 A2~A4는 `INCONCLUSIVE`.
3. `*-denied` 전 snapshot(research R2 projection) → 세 주체 시도: 인증 없음 / 지원자 자격(N-02 방식 Run 소유 세션 쿠키) /
   유효하지 않은 자격(Run마다 만든 형식 맞는 위조 Bearer). 요청마다 `X-Request-Id`·`X-Trace-Id`를 붙인다. 최종결정 경로는 세
   시도에 같은 `Idempotency-Key`를 쓴다.
4. 후 snapshot → H01-A3 비교. 감사 표 조회 → H01-A4.
5. 재전송 방지 행동 관찰(최종결정 경로만, research R2): 정상 회사 사용자가 같은 키로 `fd-denied`에 결정 → 새 생성인지 재생인지
   기록. H01-A3 비교가 끝난 뒤에만 한다.
6. `SYSTEM`·AI 어시스턴트 미시도와 H-02 결과 참조(봉인된 H-02 Run이 있으면 run id만, 판정 근거 아님)를 결과 한계에 기록.
7. 복구: `decisions.py` `reset`을 넓혀 Run 소유 지원자의 결정·리뷰·감사·단계 행을 되돌리고 잔여 0 확인.

자격 증명 원문은 메모리에만 두고 봉인하지 않는다. 증적에는 주체 종류와 원문 SHA-256의 앞 12자만 남긴다.

### 6. H-02 실행 순서

1. 검사 대상 커밋 = 대상 스냅샷의 git sha. 소스는 `git -C <WHYYOU_REPO_PATH> show <sha>:<path>`로만 읽어 작업 트리와 무관하게 한다.
2. 표면 열거: 어시스턴트 = `recruiting_assistant/api.py` 라우터 데코레이터 경로 전부, 작업자 = `runtime/worker.py`의
   `EVENT_QUEUE_ROUTING` 키 전부 + `create_production_worker_runtime`의 처리기 대응.
3. 주입 해석·호출 그래프·금지 집합 도달 분석: [contracts/h02-write-surface-v1.md](./contracts/h02-write-surface-v1.md).
4. 항목별 분류(읽기·쓰기·처리기 없음), 바꿀 수 있는 상태, 근거 위치(경로:줄), 도달 경로를 기록한다.
5. 복구 대상 없음. 정적 검사 범위·한계(깊이 상한, 동적 디스패치 처리, V4 §7.3 제외)를 결과에 표시한다.

### 7. 판정 규칙 요약

[contracts/assertions-v6.md](./contracts/assertions-v6.md). 시나리오 전체는 기존 `judge_spec004_run` 순서(복구 실패 →
FAIL → 충돌 → 증적 부족)를 따르는 `judge_spec006_run`으로 낸다.

## Harness

- `scripts/spec006_local.py`: `scripts/n02_local.py`처럼 `spec004_local.environment`를 덮어쓰는 얇은 진입점.
  - 외부 AI 차단·모델 대체 값은 `n02_local.py`와 같다(`CONTROLPROOF_EXTERNAL_AI_ALLOWED=false`,
    `CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED=true`, fixture `n02-analysis-v1`).
  - `--api-port` 기본 8080(지원자 앱 프록시 고정 대상, research R5). 8080이 쓰이고 있으면 `up`을 거부한다.
  - `up --with-applicant-app`: API·작업자 기동 뒤 WhyYou checkout에서 `npm run dev:applicant`를 띄우고 5174 응답을 기다린다.
    `stop`이 같이 내린다. `node_modules`가 없으면 설치하지 않고 실패한다(설치는 별도 승인).
  - CLI 환경에 `CONTROLPROOF_APPLICANT_APP_URL=http://127.0.0.1:5174`를 넣는다.
- 기존 `spec004_local.py`는 바꾸지 않는 것을 원칙으로 한다. 덮어쓰기로 안 되는 지점이 나오면 기본값을 유지하는 인자만 더하고
  Spec 004 하네스 시험(`tests/unit/test_spec004_local_setup.py`)을 같이 돌린다.

## Adapter and Judge Design

| 모듈 | 내용 | 재사용·신규 |
|---|---|---|
| `engine/adapters/whyyou/applicant_browser.py` | 지원자 화면 열기·단계 진행·항목 측정·캡처·정책 응답 관찰 | 신규(`browser.py` 패턴) |
| `engine/adapters/whyyou/spec006_seed.py` + `seeds/spec006_subjects.py` | N-01 초대 토큰, N-03 lane, H-01 ready 리포트 지원자 | 신규(N-02·Spec 004 시드 함수 재사용) |
| `engine/adapters/whyyou/principals.py` | 거부 주체별 HTTP 클라이언트(회사 Bearer 미탑재) | 신규 |
| `engine/adapters/whyyou/decisions.py` | `capture_reset_token` 행 집합 확장, 주체 클라이언트 주입 | 확장 |
| `engine/adapters/whyyou/audit_records.py` | `audit_events` 시도 구간 조회 | 신규 |
| `engine/adapters/whyyou/consent.py` | 그대로 사용 | 재사용 |
| `engine/adapters/whyyou/source_surface.py` | `git show` 소스 읽기, `ast` 열거·도달 분석 | 신규 |
| `engine/adapters/whyyou/capability.py` | 접근 종류 probe 3개, API 단일 프로세스 확인 | 확장 |
| `engine/executors/n01.py`·`n03.py`·`h01.py`·`h02.py` | 시나리오 실행 순서 | 신규(`report_lanes.py` 기반) |
| `engine/judges/n01.py`·`n03.py`·`h01.py`·`h02.py` | assertion 판정 | 신규 |
| `engine/executors/spec006.py` | `judge_spec006_run`, 미검증 범위·한계 조립 | 신규 |

어댑터는 `engine/adapters/base.py`에 Protocol을 더하고 `create_whyyou_adapter`에서 조립한다. 판정기는 어댑터 결과 모델만 받는다.

## Evidence and Bundle

[contracts/evidence-bundle-v5.md](./contracts/evidence-bundle-v5.md). `engine/evidence.py`에 `SPEC006_PROFILE_CONTRACT`
(`controlproof.bundle-profile.spec006.v1`)와 프로필별 필수 파일 목록을 더한다. 봉인·`verify`·redaction은 기존 함수를 쓴다.
캡처 PNG는 `write_bytes`로 넣는다. 화면에 원시 초대 토큰이 보이지 않는지는 캡처 시점 DOM 텍스트로 확인하고 결과를 증적에 남긴다.

## Workbench

- 검토 projection(`engine/presentation.py` `load_bundle_summary`)에 `target_access`·`unverified_scope_items`·`limitations`를 싣는다.
- 결과 화면 `engine/web/templates/run.html` 한계 줄(130~132) 위에 "대상 접근: 화면 + API" 한 줄, 시나리오 화면
  `scenario.html` 프로필 준비 상태(91) 옆에 같은 한 줄. 값은 `readmodel.run`(봉인 summary)·`readmodel.scenario`(YAML)에서 읽는다.
- N-03 결과 화면은 미검증 범위 세 항목과 후속 조건을 같은 한계 영역에 보인다.
- 새 화면·새 route·웹 Run 시작은 없다(D-018).

## Test Strategy

- **단위**: 판정기별 PASS·FAIL·INCONCLUSIVE 고정 fixture(SC-004·005의 FAIL fixture 포함), 항목 측정 해석, 감사 주체 요건,
  `ast` 열거·도달 분석(합성 소스 트리로 쓰기 노출·분류 불가·깊이 초과 사례).
- **계약**: 시나리오 v5 검증(필드·적용 assertion·EV 집합), 프로필 registry·CLI 대응, bundle profile spec006, adapter 계약
  (접근 성공·권한 거부·대상 부재·일시 장애 구분 — Constitution 품질 게이트).
- **통합**: fake adapter로 시나리오별 전체 흐름, 복구 실패 → `RESTORE_FAILED`·후속 차단, child 재시험 부모 불변.
- **web**: 대상 접근 한 줄과 N-03 미검증 범위 표시, 기존 화면 회귀.
- **회귀**: 기존 Spec 001~005 시험 전부. `tests/unit/test_catalog_matrix_parity.py`의 5/4/3·7 프로필 고정은 closure 전까지
  그대로 통과해야 한다(catalog `profiles`를 closure 전에 바꾸지 않음).
- **actual-stack**: 연우 승인 뒤 시나리오별 최초 Run → 판정 → 필요 시 child. [quickstart.md](./quickstart.md) 참조.

## Risks and Responses

| 위험 | 대응 |
|---|---|
| 8080 포트 충돌로 지원자 앱이 다른 API에 붙음 | `up`이 8080 사용 중이면 거부, preflight가 하네스 상태 파일의 API pid·포트와 대조 |
| 메모리 재전송 방지 저장소가 여러 프로세스에 나뉨 | preflight에서 API 프로세스 1개 확인, 아니면 `RUNNER_NOT_READY` |
| 화면 문구가 서버 정책 값과 달라 항목을 못 찾음 | 기대 문구를 서버 정책 값에서 만든다. 서버 값이 있는데 화면에서 못 찾으면 그 항목 FAIL, 브라우저 측정 자체가 실패하면 `INCONCLUSIVE`(`INSUFFICIENT_EVIDENCE`) |
| H-02 도달 분석이 동적 경로를 놓침 | 동적 디스패치는 상수 해석만, 나머지 `INCONCLUSIVE`, 깊이 상한 표시 |
| 시드가 기본 단계 채움을 일으켜 H-01 비교를 흐림 | 단계 배정한 지원자로 시드, `recruiting_stages` projection 비교 |

## Plan Decisions

- **PD-1** 실행 프로필 4개는 권장 명명 그대로.
- **PD-2** 하네스는 `spec004_local.py` 재사용 + `spec006_local.py` 진입점. API 포트 기본 8080 — 권장 설계(18085)와 다르다.
  지원자 앱 프록시 대상이 8080 고정이고 WhyYou를 바꾸지 않기 위해서다.
- **PD-3** N-01 viewport PC 1440×900, 모바일 390×844. 판정 근거 네 가지(텍스트·경계·가림·가로 넘침).
- **PD-4** N-01 접근→본인 확인은 N-02 쿠키 시드가 아니라 같은 HMAC 방식의 초대 토큰 시드다. 지원자 앱이 항상 토큰 교환부터
  시작하기 때문이다(research R5). 권장 설계와 다르다. N-03·H-01 지원자 자격은 N-02 쿠키 시드를 그대로 쓴다.
- **PD-5** H-01 두 경로 = 최종결정 POST(`DecisionPathId.FINAL_DECISION`), 일괄 이동 PATCH 최종합격(`BATCH_MOVE_FINAL_ACCEPT`).
- **PD-6** H-01 시드는 H-03 대기 리포트가 아니라 Spec 004 ready 리포트 행 방식(research R1).
- **PD-7** H-02 금지 집합의 확정 부분과 도달 규칙은 research R4.3. Q-P1·Q-P2는 열림.
- **PD-8** `target_access`는 Spec 006 네 YAML에만.
- **PD-9** H-01 감사 기록은 감사 표 직접 조회(감사 조회 API가 없음, research R3).

## Project Structure

### Documentation (this feature)

```text
specs/006-notice-authority-scenarios/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── scenario-profile-v5.md
│   ├── assertions-v6.md
│   ├── evidence-bundle-v5.md
│   └── h02-write-surface-v1.md
├── checklists/requirements.md
└── tasks.md            # $speckit-tasks (아직 없음)
```

### Source Code (ControlProof repository root)

```text
engine/
├── models.py                    # ExecutionProfile 4개, SPEC006_PROFILES, canonical, Run 검증, 환경 스냅샷 범위
├── scenario.py                  # schema v5, target_access, H-02 복구·fixture 예외
├── runner.py                    # registry 4개
├── cli.py                       # profile 대응·파일 대응
├── evidence.py                  # SPEC006_PROFILE_CONTRACT
├── presentation.py              # target_access, unverified_scope_items, limitations
├── retest.py                    # spec006 cleanup 확인 분기
├── adapters/base.py             # Protocol 추가
├── adapters/whyyou/{applicant_browser,principals,audit_records,source_surface,spec006_seed}.py   # 신규
├── adapters/whyyou/{decisions,capability,adapter}.py                                            # 확장
├── executors/{n01,n03,h01,h02,spec006}.py                                                       # 신규
├── judges/{n01,n03,h01,h02}.py                                                                  # 신규
└── web/{readmodel.py,templates/run.html,templates/scenario.html}                                # 한 줄 표시
scenarios/{N-01,N-03,H-01,H-02}.yaml
seeds/spec006_subjects.py
scripts/spec006_local.py
tests/{unit,contract,integration,web}/test_*spec006*.py, tests/fixtures/fake_spec006.py
```

**Structure Decision**: 기존 단일 Python 프로젝트 구조를 따른다. 새 최상위 디렉터리는 없다.

## Compatibility and Migration

- v3·v4 시나리오·bundle profile·Run 검증은 그대로다. 기존 봉인 bundle의 `verify` 결과가 바뀌지 않아야 한다(회귀 시험).
- `TargetEnvironmentSnapshot`의 미검증 범위 허용 집합(`engine/models.py` 518~522)에 Spec 006 집합을 더한다. 기존 두 집합은 그대로다.
- catalog `profiles`·`official_status`는 closure에서만 바꾼다.

## Complexity Tracking

| 예외 | 필요한 이유 | 더 단순한 대안을 버린 이유 |
|---|---|---|
| H-02 프로필만 복구 필수·모델 fixture 필수 규칙 면제(`engine/scenario.py` 452~455) | 정적 검사라 상태 변경·모델 호출이 없음 | 가짜 복구 단계를 넣으면 "복구 성공"이라는 거짓 증적이 생김 |
| scenario schema v5(`target_access`) | 알 수 없는 키를 거부하는 모델(`engine/scenario.py` 218~219) | v4에 선택 필드로 넣으면 v4 시나리오 의미가 바뀜 |

## Phase Gate

- Plan → Tasks: Q-P1·Q-P2 답을 받아 `contracts/h02-write-surface-v1.md`의 금지 집합·도달 규칙을 고정한 뒤.
- Tasks → Implement: Analyze CRITICAL·HIGH 0, 해석 차이를 만드는 MEDIUM 0.
- Implement → actual Run: 자동 gate 통과, 실행 checkout 준비(quickstart), 연우 승인.
- Closure: D-024 3항 문서 갱신, 미검증 범위 표시 확인.
