# Tasks: N-01·N-03 고지 시나리오 실행

작성 2026-10-19. 선례: `specs/006-h01-human-decision/tasks.md`(보성, 두 단계). 시험을 먼저 쓰고 코드를 쓴다. 구현 전에 Analyze를
한다. 1단계는 준비(코드·자동 시험·하네스)까지이고 actual은 `NOT_RUN`이다. 카탈로그·범위표·README 숫자(12/7/2/3)는 1단계에서
바꾸지 않는다(FR-055).

## Stage1 — preparation (authorized by D-030)

- [X] T001 Source discovery·scope in `spec.md`, `research.md`, `docs/research/Spec009_N01_N03_WhyYou_Source_Baseline.md` [FR-001~005, 010~013, 030~032].
- [X] T002 Plan·contracts·data model·checklist in `plan.md`, `contracts/*.md`, `data-model.md`, `checklists/requirements.md` [FR-001~056, SC-001~011].
- [X] T003 Analyze: spec·plan·contracts·tasks 교차 검토(CRITICAL·HIGH 0), 결과를 `analysis.md`에 기록.
- [X] T004 [US1][US2] 모델·프로필 등록 — `engine/models.py`(`N01_NOTICE_V1`, `N03_STALE_CONSENT_V1`, `SPEC009_PROFILES`, `N01LaneId`, `N03LaneId`, `TargetAccessKind`, canonical, Run 검증; 환경 스냅샷 허용 집합은 그대로), `engine/scenario.py`(v9 세 필드, 프로필별 고정), `scenarios/N-01.yaml`, `scenarios/N-03.yaml`; 시험 `tests/contract/test_scenario_spec009.py`(v9 검증, 기존 YAML 의미 불변) [FR-002, FR-005, FR-055].
- [X] T005 [US1][US2] 순수 판정 — `engine/n01.py`(조각·항목·화면 관찰 모델, `assertions_for`), `engine/n03.py`(이전 식별값 규칙, projection 비교, `assertions_for`); 시험 `tests/unit/test_n01_judge.py`, `tests/unit/test_n03_judge.py`(PASS·FAIL·INCONCLUSIVE fixture, SC-003 한 화면 한 항목 가림, SC-004 미검증 범위 조립) [FR-011, FR-012, FR-030, FR-031, FR-050].
- [X] T006 [US1] 지원자 화면 어댑터 — `engine/adapters/whyyou/applicant_browser.py`(viewport별 컨텍스트, 접근→본인 확인→동의 단계, 정책 응답 관찰, 조각 측정, 캡처, DOM 토큰 검사, 체크박스·제출), `engine/adapters/base.py` Protocol, `create_whyyou_adapter` 조립; 시험 `tests/contract/test_applicant_browser_adapter.py`(fake page로 측정 해석·접근 거부·대상 부재·일시 장애 구분) [FR-010, FR-011, FR-012].
- [X] T007 [US1] N-01 시드·정리 — `seeds/n01_subjects.py`, `engine/adapters/whyyou/n01_seed.py`(초대 토큰 HMAC, `invited` 합성 초대, lane별), 정리 어댑터 확장(초대·지원자·세션·동의·상태 이력·outbox, 잔여 0); 시험 `tests/contract/test_n01_seed.py` [FR-003, FR-052].
- [X] T008 [US2] N-03 lane 시드 — N-02 쿠키 시드 재사용(`stale`), `past` 사전 동의(`consent.commit`), 이전 식별값 생성; 시험 `tests/unit/test_n03_stale_identifier.py` [FR-003, FR-031].
- [X] T009 [US1][US2] 실행기·증적 — `engine/executors/n01.py`, `engine/executors/n03.py`(단계 순서, `LINKS`, always-run 복구), `engine/n01_evidence.py`, `engine/n03_evidence.py`(`REQUIRED_FILES`, `verify_links`, `verify_facts`), `engine/evidence.py`·`engine/runner.py`·`engine/cli.py`·`engine/retest.py` 분기, `FORBIDDEN_KEYS` 추가; 시험 `tests/integration/test_n01_executor.py`, `tests/integration/test_n03_executor.py`(fake adapter 전체 흐름, 복구 실패 → `RESTORE_FAILED`·후속 차단, child 부모 불변, verify 재판정 일치) [FR-050~053, SC-001, SC-002, SC-005, SC-006].
- [X] T010 [US1][US2] 준비 상태·capability — `engine/adapters/whyyou/capability.py`(`applicant.screen.open`, `browser.chromium.available`, `n01.invitations.*`), preflight 대조; 시험 `tests/contract/test_capability_spec009.py`(`ACCESS_BLOCKED`·`RUNNER_NOT_READY` 구분, 새 준비 상태 값 0) [FR-004, FR-005, SC-011].
- [X] T011 [US3] 워크벤치 한 줄 — `engine/presentation.py`, `engine/web/readmodel.py`, `templates/run.html`, `templates/scenario.html`(대상 접근, N-03 미검증 범위·후속 조건); 시험 `tests/web/test_spec009_display.py`(두 화면 표시, 기존 화면·공유 모드 회귀) [FR-054, SC-008, SC-011].
- [X] T012 하네스 — `scripts/spec009_local.py`(`spec004_local` 래퍼, `--api-port` 기본 8080, 8080·5174 점유 시 `up` 거부, `--with-applicant-app`으로 `npm run dev:applicant` 기동·`stop` 종료, `CONTROLPROOF_APPLICANT_APP_URL`); 시험 `tests/unit/test_spec009_local_setup.py` [FR-001].
- [X] T013 자동 gate — `ruff check`, `pytest tests -q` 전체(기존 + 신규), `tests/unit/test_catalog_matrix_parity.py` 12/7/2/3 그대로 통과, 공유 bundle 25건 각각의 `engine.shared_records.verification` 결과가 `review-data/snapshot.json` 기록과 같음(24 VERIFIED, `ce5f2750…` INVALID), `scripts.share_records --verify`는 "Snapshot display code/catalog differs; select its matching code version"으로 거부됨을 확인(plan Compatibility (a)(b)); 명령·결과를 `validation.md`에 기록(actual `NOT_RUN`) [SC-009].
- [X] T014 `traceability.md`(FR·SC·assertion·EV9·시험 파일 대응), AGENTS·TEAM_HANDOFF 1단계 상태 한 줄, Decision Log D-030 1단계 마감 후속.

1단계 구현 메모(작업 설명과 실제 파일이 다른 곳, 상세는 `analysis.md` 구현 메모):
T007·T008은 `seeds/spec009_subjects.py`·`engine/adapters/whyyou/spec009_seed.py`·`spec009_cleanup.py` 하나로 두 프로필을 다루고
시험은 `tests/contract/test_spec009_seed_plan.py`·`test_spec009_seed_adapter.py`다. T009는 공통 `engine/executors/spec009.py`·
`engine/spec009_evidence.py` 위에 프로필별 모듈을 둔다. T010 preflight는 `capability.py`가 아니라 실행기의 preflight에 있고 시험은
`tests/contract/test_spec009_preflight.py`다. T011은 `presentation.py`를 바꾸지 않고 `readmodel.py`가 봉인 snapshot을 읽는다. T012의
지원자 앱은 npm 대신 node가 vite를 직접 띄운다. 복구 경로(`scripts/spec009_recover.py`, `cleanup-confirm` 분기)를 1단계에 더했다.

Dependencies: T003 → T004 → T005 → (T006, T007, T008 병렬) → T009 → T010 → T011 → T012 → T013 → T014. Tests precede code.
US1(N-01)·US2(N-03)는 각각 fake adapter로 독립 시험한다. 구현 중 문서 불일치를 발견하면 레포를 고치지 말고 연우에게 보고한다.

## Stage2 — actual (연우 승인 뒤, 시나리오마다 따로 승인)

- [X] T015 실행 checkout 준비(quickstart §2·§3): 두 저장소 clean 확인, 하네스 `up --with-applicant-app`, preflight `READY`.
- [X] T016 N-01 최초 Run → `verify` → 판정 기록. FAIL·INCONCLUSIVE는 보존하고 원인 분류 뒤 승인된 수정이 있으면 child만.
- [X] T016a 측정 v2 보강(`style_visible`·`not_clipped`·좁힌 `not_occluded`, 실행기 결함: 측정 누락) → N-01 child. 첫 Run `48a70f5e…`는
  v1 기록으로 보존한다.
- [X] T017 N-03 최초 Run → `verify` → 판정 기록. 같은 규칙.
- [X] T018 독립 잔여 확인(소유 데이터 0), 워크벤치 로컬 모드 확인, `validation.md`·`actual-closure.md` 기록.
- [X] T019 Closure: 카탈로그(`mvp_treatment`·`profiles`·`official_status`), 범위표 §2·§3(N-03 질문 문구·일부 실행 표기), README, Product Brief §14.6, TEAM_HANDOFF, D-030 후속, 공유 snapshot 재생성(보성 검토, 새 `snapshot_id`, bundle 불변). 보성 검토 뒤 `fixes-and-remaining-work` 통합 PR.
  - 2026-10-20 closure 메모: 워크벤치는 새 공유본으로 별도 checkout 공유 모드에서 확인했다(validation.md). 공유본 `shared-actual-20261020`은
    제안본이며 보성 검토와 `fixes-and-remaining-work` 통합 PR은 아직 남아 있다.
