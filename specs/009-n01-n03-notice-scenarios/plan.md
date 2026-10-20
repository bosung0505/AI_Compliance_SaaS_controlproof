# Implementation Plan: N-01·N-03 고지 시나리오 실행

**Branch**: `009-n01-n03-notice-scenarios`
**Date**: 2026-10-19
**Spec**: [spec.md](./spec.md)
**Status**: 1단계 준비 완료(2026-10-20), actual NOT_RUN. Plan 산출물(Spec 006 초안의 Plan을 N-01·N-03으로 줄이고 보성 H-01·H-02
등록 방식에 맞춤)대로 1단계 구현을 마쳤다([validation.md](./validation.md)). 다음은 2단계(실제 Run) 승인이다.

## Summary

카탈로그에서 `NOT_RUN`인 두 시나리오를 시나리오마다 실행 프로필 하나로 만들어 WhyYou 격리 로컬 스택(`LOCAL_EMULATED`)에서
실행하고, 기존 판정·봉인·복구·재시험 계약으로 결과를 남긴다. 등록 방식은 보성이 H-01(Spec 006)·H-02(Spec 007)에 쓴 것과 같다:
프로필 enum·canonical·Run 검증·시나리오 검증·실행기 registry·CLI·증적 계약(`REQUIRED_FILES`·`verify_links`·`verify_facts`)·재시험
분기·검토 projection. 두 단계로 간다 — **1단계**(준비: 코드·자동 시험·하네스, actual `NOT_RUN` 유지) → **2단계**(연우 승인 뒤 실제
Run·판정·필요 시 child·closure).

- N-01 `N01_NOTICE_V1`: 지원자 앱 동의 단계를 PC 1440×900과 모바일 390×844로 열어 다섯 고지 항목의 조각별 텍스트·화면 안 위치·
  가림·가로 넘침을 측정하고, 화면·서버·저장 기록의 정책 식별값을 대조한다.
- N-03 `N03_STALE_CONSENT_V1`: 기존 동의 어댑터로 이전 정책 식별값 거부·최신 재확인 저장·과거 동의 불변을 판정한다. 교체 주입·
  근접 제출·분석 작업 정책 귀속은 미검증 범위로 표시한다("N-03 일부 실행").

WhyYou는 바꾸지 않는다. 시험용 수단도 만들지 않는다(spec FR-032). H-01·H-02는 다시 실행하지 않는다.

## Technical Context

**Language/Version**: Python 3.12 이상(ControlProof `pyproject.toml`); WhyYou 지원자 앱은 Node·Vite(대상 쪽, 기동만)
**Primary Dependencies**: Pydantic 2, PyYAML, HTTPX, SQLAlchemy 2, psycopg 3, Jinja2, Playwright(이미 의존성, 연우 PC 1.63.0) — 새 의존성 없음
**Storage**: WhyYou local PostgreSQL(하네스 compose), ControlProof 불변 file bundle(하네스 상태 루트 아래, 커밋 안 함)
**Testing**: pytest 단위·계약·통합·web, Ruff; 구현 뒤 승인된 actual-stack Run
**Target Platform**: Windows + Docker Desktop의 `LOCAL_EMULATED`; 실제 AWS는 `NOT_RUN`
**Project Type**: ControlProof CLI·검증 엔진·로컬 웹 워크벤치 + 외부 WhyYou adapter
**Performance Goals**: 준비된 스택에서 시나리오별 Run 540초, `verify` 60초, 합계 600초 이내(SC-007)
**Constraints**: 합성 데이터만, 외부 AI 차단, WhyYou 무변경, 실제 Run마다 연우 승인, closure 전 12/7/2/3 불변
**Scale/Scope**: 프로필 2, assertion 6(N01 3·N03 3), Evidence ID 7(EV9-01~07), 미검증 범위 항목 3(N03-U1~U3, 공통 AWS 별도), 한계 항목 1(N03-L1)
**User Interface**: CLI·JSON·bundle; 결과 표시는 기존 워크벤치(`engine/web`) 한 줄 추가만
**Target Baseline**: ControlProof `b76af4c`, WhyYou `bosung0505/gbsa_aws` `fixes-and-remaining-work` `0166d9e`(D-030)

## Constitution Check

### Pre-design gate

| 원칙 | 확인 | 결과 |
|---|---|---|
| I. 판정은 증적에서만 | assertion마다 EV9 원본 요구, 측정·조회 실패는 `INCONCLUSIVE`, 텍스트 존재만으로 PASS 없음 | PASS |
| II. 대상·준비·결과 분리 | 지원자 앱 접근 없음 `ACCESS_BLOCKED`, Chromium·실행기 미준비 `RUNNER_NOT_READY`, 대상 결함은 판정 | PASS |
| III. 사람의 최종 결정 | 두 시나리오는 결정 경로를 건드리지 않음. 고지 문구에 "사람의 최종 결정"이 표시되는지를 N-01이 확인 | PASS |
| IV. 시나리오/adapter 분리 | 프로필·assertion·대상 접근은 YAML, 화면 요소 찾기·DB 읽기는 adapter, 판정기는 측정값만 받음 | PASS |
| V. 격리·결정론·복구 | Run 소유 합성 지원자, 외부 AI 차단, 상태 변경은 always-run 복구 | PASS |
| VI. 불변 Run·재시험 | 기존 `retest` 계보 재사용, 최초 FAIL·INCONCLUSIVE 봉인 보존 | PASS |
| VII. 명세→증적 추적 | FR·SC·assertion·EV9 대응을 계약·Tasks·traceability에 연결 | PASS |

### Post-design re-check

위반 없음. 기존 규칙의 프로필 한정 예외 하나를 Complexity Tracking에 적는다: schema v9의 `target_access`·`unverified_scope_items`·
`limitations`. Spec 009 두 프로필에만 적용하고 v1~v7 검증 규칙은 바꾸지 않는다.

## Source-derived Boundary Map

| 시나리오 | 대상 접근 | WhyYou 경계(0166d9e) | ControlProof 재사용 | 새로 만듦 |
|---|---|---|---|---|
| N-01 | 화면 + API | `/access/:token` 교환→본인 확인→동의, `GET/POST /v1/applicant/consents` | `consent.py` `read_policy`·`read_state`, Playwright, N-02 HMAC 시드 방식, N-02 정리 | 지원자 화면 수집 어댑터, N-01 초대 시드·실행기·판정·증적 |
| N-03 | API | `POST /v1/applicant/consents` 낡은 정책 422 | `consent.py` 전부, N-02 쿠키 시드·정리 | N-03 lane 시드·실행기·판정·증적 |

근거는 [research.md](./research.md) R1~R3.

## Execution Design

### 1. 프로필과 시나리오 정의

- `engine/models.py` `ExecutionProfile`에 `N01_NOTICE_V1`·`N03_STALE_CONSENT_V1`과 `SPEC009_PROFILES` 집합을 더한다. 각
  `ScenarioProfile.canonical`은 [contracts/scenario-profile-v9.md](./contracts/scenario-profile-v9.md)를 따른다(H-01 분기와 같은
  위치, 적용 assertion·required_evidence 튜플 고정). lane enum `N01LaneId`(`pc`·`mobile`)·`N03LaneId`(`stale`·`past`)를
  `ScenarioDefinition.lanes` 유니온에 더한다.
- 시나리오 파일 `scenarios/N-01.yaml`·`N-03.yaml`, `schema_version: controlproof.scenario.v9`, `bundle_profile_contract:
  controlproof.bundle-profile.spec009.v1`. v9 = v4 모양 + `target_access`(필수, `SCREEN`·`API`·`SOURCE` 부분집합) +
  `unverified_scope_items`(선택) + `limitations`(선택). 세 필드는 `ScenarioDefinition`에 기본값 빈 튜플로 더하고, Spec 009 프로필이
  아니면 비어 있어야 한다(기존 YAML 의미 불변).
- `engine/scenario.py`의 프로필별 검증 분기(H-01 분기 모양)에 두 프로필을 더한다: schema·scenario_id·version·bundle contract·
  assertion·evidence·lanes·`target_access` 고정값, step_id 순서, 마지막 step `always_run`, `allowed_model_fixtures`
  `{n02-analysis-v1: <digest>}`, `required_capabilities` 고정.

### 2. 준비 상태와 대상 접근

- `engine/readiness.py`의 판정 순서는 그대로 쓴다. 접근 종류별 probe를 `engine/adapters/whyyou/capability.py`에 더한다.
  - `SCREEN`: 지원자 앱 URL(`CONTROLPROOF_APPLICANT_APP_URL`) 응답 없음 → `ACCESS_BLOCKED`. Chromium 실행 파일 부재 →
    `RUNNER_NOT_READY`(기존 브라우저 probe 재사용).
  - `API`: 기존 OpenAPI·동의 경로 probe. 401·403·연결 거부 → `ACCESS_BLOCKED`.
- 새 준비 상태 값은 없다(spec FR-005). 필요 capability 이름은 계약 문서에 고정한다.

### 3. N-01 실행 순서

1. 시드: lane `pc`·`mobile` 각각 Run 소유 `invited` 합성 초대(원시 초대 토큰 Run마다 생성, `token_hash` HMAC, 합성 표시 이름).
   초대 토큰은 교환 때 소비되므로 화면마다 따로 둔다.
2. 각 lane의 새 브라우저 컨텍스트(viewport 고정)에서 `/access/<raw>` → 초대 확인 → 본인 확인(표시 이름 입력) → 동의 단계 도달.
   `GET /v1/applicant/consents` 응답을 Playwright 응답 관찰로 받아 화면 값으로 기록한다.
3. 동의 단계에서 조각별 측정(contracts/assertions-v9.md): 기대 문구를 포함하는 요소, 경계 상자 대 viewport, 요소 중심점의
   `elementFromPoint`, 문서·요소의 `scrollWidth > clientWidth`. 필요한 조작(세로 스크롤)을 기록하고 전체 화면 캡처를 남긴다.
   캡처 직전 DOM 텍스트에 원시 토큰·세션 값이 없는지 확인한다.
4. 서버 현재 값은 ControlProof가 같은 세션 쿠키로 `read_policy`를 따로 불러 읽는다.
5. 화면에서 체크박스 셋 선택 → "동의하고 계속". 저장 기록(`consent_records.policy_version`·`evidence_digest`)과 동의 완료 시각을
   `read_state` projection으로 읽는다.
6. 복구(always_run): Run 소유 초대·지원자·세션·동의·상태 이력·outbox 행 정리, 잔여 0 확인.

### 4. N-03 실행 순서

1. 시드: lane `stale`(동의 전 지원자, N-02 쿠키 시드), lane `past`(Run 시작 때 `commit`으로 동의 완료).
2. `past` 기록 전 snapshot.
3. `stale`: 현재 정책 읽기 → 이전 정책 식별값(research R2) 제출 → 동의 기록·상태·상태 이력·outbox 전후 비교.
4. `stale`: 최신 정책 다시 읽기 → 그 값으로 제출 → 저장 기록 식별값과 재조회 값 비교.
5. `past` 기록 후 snapshot과 비교.
6. 미검증 범위 항목 N03-U1~U3와 한계 N03-L1을 결과에 기록(판정 없음). 복구(always_run)·잔여 확인.

### 5. 판정 규칙 요약

[contracts/assertions-v9.md](./contracts/assertions-v9.md). 시나리오 전체는 H-01과 같이 봉인된 관찰 행에서 assertion을 다시 만드는
순수 함수(`assertions_for(rows, recovery)`)로 내고, `verify_facts`가 봉인 뒤 같은 함수로 재판정해 `assertions.json`·
`judgement.json`과 대조한다. 전체 판정 순서는 복구 실패 → FAIL → 충돌 → 증적 부족이다.

## Harness

- `scripts/spec009_local.py`: `scripts/h01_local.py`·`n02_local.py`처럼 `spec004_local.environment`를 덮어쓰는 진입점.
  - 외부 AI 차단·모델 대체 값은 `n02_local.py`와 같다(`CONTROLPROOF_EXTERNAL_AI_ALLOWED=false`,
    `CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED=true`, fixture `n02-analysis-v1`).
  - `--api-port` 기본 8080(지원자 앱 프록시 고정 대상, research R1). 8080·5174가 쓰이고 있으면 `up`을 거부한다.
  - `up --with-applicant-app`: API·작업자 기동 뒤 WhyYou 루트에서 `npm run dev:applicant`를 띄우고 5174 응답을 기다린다.
    `stop`이 같이 내린다. 루트 `node_modules`가 없으면 설치하지 않고 실패한다(설치는 별도 승인).
  - CLI 환경에 `CONTROLPROOF_APPLICANT_APP_URL=http://127.0.0.1:5174`를 넣는다.
- 기존 `spec004_local.py`는 바꾸지 않는 것을 원칙으로 한다. 덮어쓰기로 안 되는 지점이 나오면 기본값을 유지하는 인자만 더하고
  Spec 004 하네스 시험(`tests/unit/test_spec004_local_setup.py`)을 같이 돌린다.

## Adapter and Judge Design

| 모듈 | 내용 | 재사용·신규 |
|---|---|---|
| `engine/adapters/whyyou/applicant_browser.py` | 지원자 화면 열기·단계 진행·조각 측정·캡처·정책 응답 관찰 | 신규(`browser.py` 패턴) |
| `engine/adapters/whyyou/n01_seed.py` + `seeds/n01_subjects.py` | N-01 초대 토큰 시드(HMAC) | 신규(N-02 시드 함수 재사용) |
| `engine/adapters/whyyou/consent.py` | 그대로 사용 | 재사용 |
| `engine/adapters/whyyou/n02_seed.py`·`n02_cleanup.py`·`seeds/n02_subjects.py` | N-03 lane 시드·두 시나리오 정리 | 재사용(필요하면 인자만 추가) |
| `engine/adapters/whyyou/capability.py` | 접근 종류 probe(지원자 앱·브라우저) | 확장 |
| `engine/executors/n01.py`·`n03.py` | 시나리오 실행 순서, `LINKS`(EV9→파일), `assertions_for` | 신규(`executors/h01.py` 기반) |
| `engine/n01.py`·`n03.py` | 관찰·측정 모델과 순수 판정 | 신규(`engine/h01.py` 기반) |
| `engine/n01_evidence.py`·`n03_evidence.py` | `REQUIRED_FILES`·`verify_links`·`verify_facts` | 신규(`engine/h01_evidence.py` 기반) |

어댑터는 `engine/adapters/base.py`에 Protocol을 더하고 `create_whyyou_adapter`에서 조립한다. 판정기는 어댑터 결과 모델만 받는다.
웹 검토 모듈(`engine/web/h01_review.py` 같은 것)은 만들지 않는다 — 공통 화면과 한 줄 표시만 쓴다.

## Evidence and Bundle

[contracts/evidence-bundle-v9.md](./contracts/evidence-bundle-v9.md). `engine/evidence.py`의 H-01·H-02 분기(`REQUIRED_FILES` 선택,
manifest `profile_contract`, `verify_links`·`verify_facts` 위임, 기대 contract)에 Spec 009 두 프로필을 더한다. 봉인·`verify`·
redaction은 기존 함수를 쓴다. 캡처 PNG는 `write_bytes`로 넣는다.

## Workbench

- 검토 projection(`engine/presentation.py`)에 `target_access`·`unverified_scope_items`·`limitations`를 싣는다.
- 결과 화면 `engine/web/templates/run.html` 한계 영역 위에 "대상 접근: 화면 + API" 한 줄, 시나리오 화면 `scenario.html` 프로필
  준비 상태 옆에 같은 한 줄. 값은 `readmodel.run`(봉인 summary)·`readmodel.scenario`(YAML)에서 읽는다.
- N-03 결과 화면은 미검증 범위 세 항목과 후속 조건을 같은 한계 영역에 보인다.
- 새 화면·새 route·웹 Run 시작은 없다(D-018). Spec 008 공유 모드(기본)는 봉인된 공유본만 보이므로 새 Run은 `--run-root` 로컬
  모드로 본다.

## Test Strategy

- **단위**: 판정기별 PASS·FAIL·INCONCLUSIVE 고정 fixture(SC-003의 한 화면 한 항목 가림 fixture 포함), 조각 측정 해석, 이전 식별값
  생성 규칙(버전·해시 둘 다 다름), 미검증 범위·한계 조립.
- **계약**: 시나리오 v9 검증(필드·적용 assertion·EV 집합·lanes·target_access), 프로필 registry·CLI 대응, bundle profile spec009,
  adapter 계약(접근 성공·권한 거부·대상 부재·일시 장애 구분 — Constitution 품질 게이트), `verify_facts` 재판정 일치.
- **통합**: fake adapter로 시나리오별 전체 흐름, 복구 실패 → `RESTORE_FAILED`·후속 차단, child 재시험 부모 불변.
- **web**: 대상 접근 한 줄과 N-03 미검증 범위 표시, 기존 화면 회귀(공유 모드 포함).
- **회귀**: 기존 Spec 001~008 시험 전부. `tests/unit/test_catalog_matrix_parity.py`의 12/7/2/3·프로필 수 고정은 closure 전까지
  그대로 통과해야 한다(catalog `profiles`를 closure 전에 바꾸지 않음). 기존 시나리오 13개의 snapshot digest 고정
  (`tests/contract/test_scenario_digests_frozen.py`), 공유 bundle 25건의 verification 불변
  (`tests/contract/test_review_data_bundles_unchanged.py`), 이 브랜치에서 공유본 거부 메시지
  (`tests/contract/test_shared_snapshot_rejects_changed_code.py`) — Compatibility (a)(b).
- **actual-stack**: 연우 승인 뒤 시나리오별 최초 Run → 판정 → 필요 시 child. [quickstart.md](./quickstart.md) 참조.

## Risks and Responses

| 위험 | 대응 |
|---|---|
| 8080 포트 충돌로 지원자 앱이 다른 API에 붙음 | `up`이 8080·5174 사용 중이면 거부, preflight가 하네스 상태 파일의 API pid·포트와 대조 |
| 화면 문구가 서버 정책 값과 달라 조각을 못 찾음 | 기대 문구를 서버 정책 값에서 만든다. 서버 값이 있는데 화면에서 못 찾으면 그 항목 FAIL, 브라우저 측정 자체가 실패하면 `INCONCLUSIVE`(`INSUFFICIENT_EVIDENCE`) |
| 지원자 앱 미기동을 대상 결함으로 오인 | `ACCESS_BLOCKED`(앱 응답 없음)와 `RUNNER_NOT_READY`(Chromium 없음)를 preflight에서 구분 |
| 초대 토큰이 캡처·DOM에 남음 | 캡처 직전 DOM 텍스트 검사 결과를 증적에 남기고 redaction 금지 키에 `invitation_token` 추가 |
| N-02 정리 어댑터가 N-01 초대 행을 모르고 남김 | 정리 대상 행 집합을 lane 종류별로 명시하고 잔여 0을 독립 조회로 확인 |

## Plan Decisions

- **PD-1** 실행 프로필 2개는 초안 명명 그대로(`N01_NOTICE_V1`, `N03_STALE_CONSENT_V1`). schema·bundle contract 번호는 보성 관례대로
  Spec 번호를 따른다(`controlproof.scenario.v9`, `controlproof.bundle-profile.spec009.v1`), 증적 ID는 EV9-xx.
- **PD-2** 하네스는 `spec004_local.py` 재사용 + `spec009_local.py` 진입점(`--instance`·`--state-root` 방식). API 포트 기본 8080 —
  Spec 004 기본값(18085)과 다르다. 지원자 앱 프록시 대상이 8080 고정이고 WhyYou를 바꾸지 않기 위해서다.
- **PD-3** N-01 viewport PC 1440×900, 모바일 390×844. 판정 근거 네 가지(텍스트·경계·가림·가로 넘침), 항목은 조각 전부 표시될 때만.
- **PD-4** N-01 접근→본인 확인은 N-02 쿠키 시드가 아니라 같은 HMAC 방식의 초대 토큰 시드다. 지원자 앱이 항상 토큰 교환부터
  시작하기 때문이다(research R1). N-03 지원자 자격은 N-02 쿠키 시드를 그대로 쓴다.
- **PD-5** 판정은 H-01처럼 봉인 행에서 재구성 가능한 순수 함수로 두고 `verify_facts`가 재판정한다.
- **PD-6** `target_access`는 Spec 009 두 YAML에만. 기존 열 시나리오는 빈 값으로 두고 화면에도 줄을 만들지 않는다.
- **PD-7** 두 단계: 1단계 코드·자동 시험·하네스까지(actual `NOT_RUN`, 카탈로그 불변), 2단계 연우 승인 뒤 실제 Run·closure.

## Project Structure

### Documentation (this feature)

```text
specs/009-n01-n03-notice-scenarios/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── scenario-profile-v9.md
│   ├── assertions-v9.md
│   └── evidence-bundle-v9.md
├── checklists/requirements.md
├── tasks.md
└── analysis.md         # T003 Analyze
```

### Source Code (ControlProof repository root)

```text
engine/
├── models.py                    # ExecutionProfile 2개, SPEC009_PROFILES, N01LaneId·N03LaneId, TargetAccessKind, canonical, Run 검증
├── scenario.py                  # schema v9, target_access·unverified_scope_items·limitations, 프로필별 고정
├── runner.py                    # registry 2개
├── cli.py                       # profile 대응·파일 대응
├── evidence.py                  # spec009 contract 분기
├── presentation.py              # target_access, unverified_scope_items, limitations
├── retest.py                    # spec009 child 조건 분기
├── n01.py / n03.py              # 관찰 모델·순수 판정                                  # 신규
├── n01_evidence.py / n03_evidence.py                                                   # 신규
├── adapters/base.py             # Protocol 추가
├── adapters/whyyou/{applicant_browser,n01_seed}.py                                     # 신규
├── adapters/whyyou/{capability,adapter}.py                                             # 확장
├── executors/{n01,n03}.py                                                              # 신규
└── web/{readmodel.py,templates/run.html,templates/scenario.html}                       # 한 줄 표시
scenarios/{N-01,N-03}.yaml
seeds/n01_subjects.py
scripts/spec009_local.py
tests/{unit,contract,integration,web}/test_*n01*.py, test_*n03*.py, test_*spec009*.py, tests/fixtures/fake_spec009.py
```

**Structure Decision**: 기존 단일 Python 프로젝트 구조를 따른다. 새 최상위 디렉터리는 없다.

## Compatibility and Migration

- v1~v7 시나리오·bundle profile·Run 검증은 그대로다. 공유 기록과의 관계(analysis A1, 해소안 1):
  - (a) `review-data/bundles`의 25건 각각에 대해 `engine.shared_records.verification(bundle_dir)` 결과가
    `review-data/snapshot.json`의 해당 `record["verification"]`과 같아야 한다(24건 VERIFIED, `ce5f2750…` INVALID 그대로).
    이것이 실제 회귀 gate다.
  - (b) `scripts.share_records --verify`와 기본 공유 웹 모드는 `display_files`가 `b76af4c` 코드에 고정돼 있어 이 브랜치에서는
    `"Snapshot display code/catalog differs; select its matching code version"`으로 거부되는 것이 정상이다. gate는 이 메시지를
    확인한다.
  - (c) 새 공유본(새 `snapshot_id`, 원본 bundle 바이트·판정 불변, 재봉인 없음)은 Spec 009 closure에서 보성 검토로 만든다.
  - (d) 진행 중 공유 기록 열람은 `fixes-and-remaining-work` worktree에서 한다(quickstart §5).
- 환경 스냅샷은 H-01·H-02처럼 기존 환경 어댑터 캡처(`SPEC002_UNVERIFIED_SCOPE`, AWS 구성 요소)를 그대로 쓴다. 시나리오별 미검증
  범위는 Run·Judgement의 `unverified_scope` 튜플에만 둔다(N-01: `AWS_NOT_RUN`, `EXTERNAL_MODEL_QUALITY_NOT_TESTED`,
  `N02_PRE_CONSENT_BLOCK_NOT_RETESTED`; N-03: `AWS_NOT_RUN`, `N03_U1_POLICY_SWAP_INJECTION`, `N03_U2_NEAR_SWAP_SUBMISSION`,
  `N03_U3_ANALYSIS_POLICY_ATTRIBUTION`). `TargetEnvironmentSnapshot`의 허용 집합은 바꾸지 않는다. Run 토큰
  `N03_U1_*`~`N03_U3_*`는 YAML `unverified_scope_items`의 `N03-U1`~`N03-U3`와 같은 항목이다(표시 문구·후속 조건은 YAML 값).
- `ScenarioDefinition.snapshot()`은 Spec 009 프로필이 아니면 `target_access`·`unverified_scope_items`·`limitations`를 digest
  대상에서 뺀다(Spec 004의 `diagnostic_ids` 처리와 같음). 기존 시나리오 snapshot digest가 바이트 단위로 같아야 한다.
- catalog `profiles`·`official_status`는 closure에서만 바꾼다.

## Complexity Tracking

| 예외 | 필요한 이유 | 더 단순한 대안을 버린 이유 |
|---|---|---|
| scenario schema v9(`target_access` 등 세 필드) | 알 수 없는 키를 거부하는 모델(`ScenarioModel`) | v4에 선택 필드로 넣으면 v4 시나리오 의미가 바뀜 |

## Phase Gate

- Plan → Tasks: 이 문서 승인(연우).
- Tasks → Implement: Analyze CRITICAL·HIGH 0, 해석 차이를 만드는 MEDIUM 0.
- Implement → actual Run: 자동 gate 통과(기존 시험 + 신규), 실행 checkout 준비(quickstart), 연우 승인.
- Closure: D-030 3항 문서 갱신, 미검증 범위 표시 확인, 보성 검토 뒤 `fixes-and-remaining-work` 통합.
