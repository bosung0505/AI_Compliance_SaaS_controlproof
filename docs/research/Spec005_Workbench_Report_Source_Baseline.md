# Spec 005 웹 워크벤치·보고서 — 원천 기준선

- 조사일: 2026-10-08 (Specify 전 Source discovery, 플레이북 §3 단계 0)
- 조사 대상: ControlProof `865b0ed61e48b908532f869d3a96f2fb10b4d4d3` (`yeonwoo/004-e01-e02-score-evidence`, Spec 004
  Complete), WhyYou `374b122e1296c0159ccd88ed4763d358973c59cb` (`bosung/controlproof-n02-integration`, PR #8)
- 방법: 소스·문서 읽기와 redaction 함수 단독 호출만 했다. Run·DB 조회·웹 서버 기동은 하지 않았다.
- 읽는 법: "확인된 사실"은 ControlProof 저장소 상대 경로와 줄 범위로 재확인할 수 있다. "위험"은 이번 Spec에서
  고치지 않고 웹 설계에 반영해야 할 사실이다. "미확인"은 확인 방법과 함께 적는다.

웹 화면이 읽을 원천은 지금 모두 ControlProof 엔진(명령줄 도구·봉인 bundle·시나리오 YAML)과 제품 문서다. WhyYou는
웹이 직접 읽는 원천이 아니다(Run을 시작할 때만 엔진을 통해 닿는다).

## 1. 확인된 사실

### 1.1 12개 시나리오와 상태 — 문서에만 있다

- 시나리오 YAML은 7개다: `scenarios/H-03.yaml`(H03_MINIMAL_V1, 프로필 미지정 시 기본), `H-03-DLQ.yaml`(H03_DLQ_V2),
  `E-03-BEFORE.yaml`·`E-03-AFTER.yaml`(E03_BEFORE_V2·E03_AFTER_V2), `N-02.yaml`(N02_CONSENT_ORDER_V1),
  `E-01.yaml`·`E-02.yaml`(E01·E02). `_TEMPLATE.yaml`은 `load_all`이 건너뛴다(`engine/scenario.py` 516~529).
  시나리오 ID 5개(H-03, E-03, N-02, E-01, E-02)에 실행 프로필 7개가 대응한다.
- `ExecutionProfile` 7개(`engine/models.py` 85~92), 실행기 등록(`engine/runner.py` 913~922, 기본 H03_MINIMAL_V1은
  881~910의 레지스트리 기본값).
- **H-01, H-02, N-01, N-03, A-01~A-03은 YAML·코드·데이터 어디에도 시나리오로 없다.** N-01·N-03은 미검증 범위 집합으로만
  나온다(`engine/models.py` 317 `SPEC003_UNVERIFIED_SCOPE`, 1296 `SPEC004_UNVERIFIED_SCOPE`, `engine/cli.py` 486,
  `engine/presentation.py` 23~26, 각 YAML의 `excluded_scope`). H-01·H-02·A-01~A-03은 코드에 문자열로도 없다.
- 12개와 "실제 실행 5·`NOT_RUN` 4·`NO_TEST_TARGET` 3"은 문서에만 있다:
  `docs/product/ControlProof_MVP_Scenario_Coverage_Matrix.md` 15~28(개수표·고정 문구), 33~46(시나리오별 행),
  48~58(상태 변경 규칙), Decision Log D-013·D-014, Product Brief §14.6, constitution 106.
- 범위표의 현재 상태(2026-10-08): H-03·E-03·E-01·E-02 완료, N-02 actual child `7b59237e…` A1~A4·A6 PASS·A5·A7
  `INCONCLUSIVE`(Spec 003 최종 converge 대기), H-01·H-02·N-01·N-03 `NOT_RUN`, A-01~A-03 `NO_TEST_TARGET`
  (`…Coverage_Matrix.md` 35~46).
- 시나리오 상세 화면에 쓸 수 있는 필드(`engine/scenario.py`): `ScenarioDefinition` 276~298(`title`, `control_intent`,
  `preconditions`, `steps`, `assertions`, `required_evidence`, `timing_policy`, `restore_policy`, `source_requirements`,
  `excluded_scope`, `allowed_model_fixtures`), `Precondition` 222~226, `ScenarioStep` 229~236(`phase`, `always_run`),
  `AssertionDefinition` 239~246(`description`, `expectation`, `fail_condition`, `required_evidence_ids`),
  `EvidenceRequirement` 249~252. 법·정책 근거는 `source_requirements`가 Spec 요구사항 ID일 뿐 법 조문 문구가 아니다.

### 1.2 명령줄 도구의 결과 형식과 종료 코드

- `SCHEMA_VERSION="controlproof.cli.v1"`, 종료 코드 0 성공·PASS, 1 사용/설정 오류, 2 준비 안 됨, 3 FAIL, 4 INCONCLUSIVE·중단,
  5 무결성 실패, 6 복구 실패(`engine/cli.py` 39~45, `_run_exit` 617~624).
- 오류 출력은 `{schema_version, command, error, detail}`, 계약 오류 코드 `PROFILE_REQUIRED`·`PROFILE_MISMATCH`·
  `SPEC004_SAFE_STATE_NOT_CONFIRMED` 등(같은 파일 59~93, 559~603, 325~396).
- `preflight`(173~185, `_readiness_payload` 469~501): `readiness`, `checks[]`(capability·status·detail·operator_action),
  `operator_action`, `implementation_status`, `target_snapshot`, `model_fixture_id/digest`, `environment_kind`,
  `aws_deployment_status`, `unverified_scope`, `claim_scope`. N-02는 `protected_paths`(504~519), Spec 004는
  `capabilities{ready,required}`, `limitations`, E-02 `scoring_rule_source{status,pinned_blobs}`(522~546).
- `run`(188~211)·`show`(214~219)·`retest`(243~312)는 같은 검토 projection(`controlproof.review.v1`)에 `command`,
  `projection_schema_version`을 붙인다. `run`은 `bundle_path`와 `timing`, `retest`는 `parent_run_id`를 더한다.
- `verify`(222~240): `bundle_status`(VERIFIED/INVALID), `checked_files`, `missing/mismatched/unregistered_files`,
  `checked_evidence_requirements`, Spec 004는 `cross_reference_errors`, `redaction_violations`, `recompute_reexecution`.
- 알려진 어긋남: argparse 사용 오류도 종료 코드 2라 "준비 안 됨"과 겹친다(argparse 기본 동작). 준비 안 됨으로 끝난 `run`의
  출력 `command`는 `"preflight"`다(474, 199~201). `show`·`verify`는 `--run-root` 기본값 `.controlproof/runs`를 쓰고
  `CONTROLPROOF_RUN_ROOT`를 읽지 않는다(151). H-03 cleanup-confirm의 안전 실패는 JSON 오류가 아니라 traceback이다
  (`engine/lifecycle.py` 161~162).

### 1.3 Run 저장 위치와 bundle 구조

- run root: `CONTROLPROOF_RUN_ROOT` 또는 `.controlproof/runs`(`engine/config.py` 118). 구조는 `<run_id>/`(bundle),
  `locks/`, `blocks/<target>--<subject>.json`, `blocks/maintenance/<run_id>.json`(`engine/lifecycle.py` 56~57, 93~98,
  124~148, 172~174). 봉인 뒤 `run.json`은 불변(65~69).
- manifest(`engine/evidence.py` `seal` 638~686): `schema_version="controlproof.bundle.v1"`, `run_id`, `files[]`
  (`path`, `mime_type`, `size_bytes`, `sha256`; artifact는 `artifact_id`, `phase`, `step_id`, `attempt`,
  `evidence_requirement_ids` 등, 600~636), `required_evidence{EV:[참조]}`, `bundle_digest`(684), Spec 002/003/004는
  `profile_contract`, `execution_profile`, 환경·lane·capability·정책/scoring 원본 digest.
- 증적 참조 형식은 `artifact:<id>`, `file:<path>`, `intrinsic:sealed-manifest`, 다른 Run의 원본 참조 dict다(415~465, 520~523).
- 프로필별 파일 집합: 공통 8개(88~97), Spec 002(101~110), Spec 003(111~141), Spec 004(145~198).
- 계보: `retest-link.json`(`RetestLink`: parent·child·changed_dimensions·reason, `engine/models.py` 2037~2048; Spec 003/004는
  `parent_bundle_digest`, `parent_judgement_sha256` 추가, `engine/retest.py` 373~374, 723~725), `retest-diff.json`
  (`controlproof.retest-diff.v1`, retest.py 157~225, 664~704). 부모·자식 검증은 Spec 003/004만(`engine/evidence.py`
  1561~1603) 하고 부모가 같은 run root에 있어야 한다. H-03/Spec 002 계보에는 같은 검증이 없다.

### 1.4 판정 모델

- `Verdict` PASS·FAIL·INCONCLUSIVE·NOT_RUN(`engine/models.py` 59~63). **`NOT_RUN`은 봉인 판정에 저장될 수 없다**
  ("NOT_RUN cannot be stored for a created Run", 2028~2029). 따라서 시나리오 단위 `NOT_RUN`은 Run 기록이 없는 상태를
  화면이 표시하는 값이지 bundle에서 읽는 값이 아니다.
- `InconclusiveReason`은 D-011의 네 코드(66~70), INCONCLUSIVE에만 필수(2030~2033). `ReadinessStatus`는 READY·
  RUNNER_NOT_READY·ACCESS_BLOCKED·NO_TEST_TARGET(40~44), `ImplementationStatus`(267~270), `RunState` 6개와
  RESTORE_FAILED 시 `manual_cleanup_required`(47~56, 1805~1806), `EnvironmentKind=LOCAL_EMULATED`·
  `AwsDeploymentStatus=NOT_RUN`(118~123).
- `AssertionResult`: `expected`, `actual`, `detail`, `reason_code`, `artifact_ids`, `observation_ids`,
  `source_requirements`(1984~2002). `Judgement`: `summary`, `missing_evidence`, `findings`, `unverified_scope`(2013~2024).
- 준비 상태 결정 순서(`engine/readiness.py` 82~104): 대상 기능 없음 → NO_TEST_TARGET, 접근 차단 → ACCESS_BLOCKED,
  구현 미완·snapshot 없음·dirty·준비 안 된 check → RUNNER_NOT_READY. 대상 기능 존재 판단은 WhyYou OpenAPI의 두 경로
  (`engine/adapters/whyyou/capability.py` 154~164)이고 OpenAPI를 못 읽으면 "있음"으로 둔다.
- 검토 projection(`engine/presentation.py` `load_bundle_summary` 39~196): verdict·reason·summary·assertion별
  expected/actual/detail/evidence(`artifact_id, path, sha256, mime_type`)·claim_scope·법적 비보증 문구·미검증 범위·
  복구 상태·parent_run_id. 상수 `CLAIM_SCOPE`(18), `NO_CERTIFICATION_NOTICE`(19~22), N-02·Spec 004 문구(23~31),
  Spec 004 `limitations`(27). 비개발자용 문장은 Spec 004 일부와 `render_human`(199~265)의 한국어 줄뿐이다.

### 1.5 redaction

- `redact()`(`engine/evidence.py` 255~276)는 키 기반([REDACTED]/[HASHED], 28~76, 293~309)과 문자열 정규식(Bearer, 이메일,
  전화, 서명 쿼리, 사용자 경로, 77~86)을 적용한다. `assert_redacted()`(279~290)는 바이트에서 Bearer·이메일·전화·사용자
  경로를 찾고 JSON 키를 검사한다(서명 쿼리는 검사하지 않음).

### 1.6 H-03·E-03 공식 결과 (2026-10-08 Clarify 때 확인, 읽기만 함)

- H-03 `H03_MINIMAL_V1`(Spec 001): 부모 `f738081a-5fb3-4f21-af22-685a12355096` FAIL(H03-A2·A3) 보존, 수정 후 child
  `e42482c9-ba84-42c6-984d-209e0f80b7d8` PASS(H03-A1~A6), bundle VERIFIED(`specs/001-execution-evidence-h03/validation.md`
  101~125, 판정 156~162).
- H-03 `H03_DLQ_V2`(Spec 002): 최종 Run `ac025c2c-b941-4c4c-b737-d3d3e61deb0b` PASS(H03-A1~A9), 복구 SUCCEEDED, VERIFIED.
  최초 FAIL 부모 `60b19e5a-6693-427b-bf87-039e45181cfc` 보존, 수정 후 child/grandchild PASS
  (`specs/002-h03-e03-fault-expansion/validation.md` 333~이후 "최종 3-profile 결과"와 "최초 FAIL 보존과 재시험").
- E-03 `E03_BEFORE_V2` 최종 Run `047fb27b-c50e-4e50-b43d-acc1c08623e9` PASS, `E03_AFTER_V2` 최종 Run
  `4e3e424e-f9ab-43c0-a4d4-7a3741f8e3f0` PASS, 둘 다 복구 SUCCEEDED·VERIFIED. 최초 FAIL 부모
  `e17e0af0-b46a-4022-93a4-a91a3247f16d` 보존(같은 절).
- 세 결과 모두 한 PC의 `LOCAL_EMULATED`이며 bundle은 Git에 없다(§3). 다른 PC 독립 재현은 `PENDING_EXTERNAL_REPRODUCTION`.

## 2. 위험 (이번 Spec에서 고치지 않음, 웹 설계 입력)

1. **절대 경로 노출**: `run`·`retest` 출력의 `bundle_path`는 절대 경로다(`engine/cli.py` 551). 출력 전 `redact()`가
   `C:\Users\<이름>` 앞부분만 `[USER_ROOT]`로 바꾸고 나머지 경로는 남긴다. 사용자 홈 밖의 run root(`D:\runs`, `/var/runs`)는
   그대로 나온다. 사람용 `show` 문장(`render_human`)은 redaction을 거치지 않는다(661).
2. **JSON 이스케이프 경로 미검출**: `USER_PATH_RE`(84~86)는 드라이브 뒤 구분자를 하나만 허용해 JSON 텍스트의
   `C:\\Users\\이름`을 잡지 못한다. 그래서 `assert_redacted`가 봉인 파일 안의 Windows 사용자 경로를 놓칠 수 있다(정규식으로
   확인, 하위 에이전트가 단독 호출로 재현). 웹이 원본 증적 파일을 보여 주거나 경로를 표시하면 이 위험이 화면으로 옮겨진다.
3. **증적 링크 누락**: projection의 `evidence_links`(`engine/presentation.py` 411~424)는 `artifact:` 참조만 해석하고
   `file:`·`intrinsic:`·다른 Run 참조는 버린다. Spec 003/004 bundle은 주로 `file:` 참조라 이 목록이 비거나 불완전할 수 있다.
   웹의 "판정 → 원본 증적" 추적은 manifest를 직접 따라가야 한다.
4. **Spec 004 retest와 정리 확인 경로 불일치**: `cleanup-confirm`은 `run_root/blocks/maintenance/`에 쓰는데
   (`engine/lifecycle.py` 126, 172), Spec 004 retest는 `run_root/maintenance/`를 찾는다(`engine/retest.py` 610).
   복구 실패한 Spec 004 부모는 정리 확인 뒤에도 재시험이 거부될 것으로 보인다(ID-004-27 코드, 미관찰). 웹에서 재시험을
   시작하게 하면 드러난다.
5. **출력 일관성**: 종료 코드 2의 이중 의미, 준비 안 됨 `run`의 `command="preflight"`, H-03 cleanup traceback(1.2).

## 3. 데이터 출처 문제

- Git에 있는 실제 bundle은 Spec 003 N-02 부모 `.controlproof/runs/15cef078-ee24-4f0e-91ef-381e0f7a1cc2/`(21개 파일,
  RESTORE_FAILED, 판정 INCONCLUSIVE)와 대응 정비 기록 `.controlproof/runs/blocks/maintenance/15cef078….json`뿐이다
  (2026-10-02 일회성 예외, AGENTS.md). 그 밖의 공식 Run(H-03, E-03, N-02 child `7b59237e…`, E-01·E-02 부모·child·
  재현 Run)은 각자 PC에만 있고 Validation의 Run ID·manifest SHA-256이 공식 기록이다(플레이북 §7).
- 이 PC의 git-ignored 로컬 bundle은 `7b59237e…`와 `e2e8e71d…` 두 개다(공유 대상 아님).
- 합성 자료는 있다: `tests/fixtures/bundles/cases.json`(`synthetic_only: true`, pass·fail·missing·conflict·aborted·
  restore_failed), `tests/fixtures/spec003.py`·`spec002.py`·`spec004.py`·`n02_review_bundle.py`, 개발 데모 생성
  `scripts/prepare_sc008_review.py`(`docs/TEAM_HANDOFF.md` 372~382).
- 따라서 웹 개발은 합성 bundle로 할 수 있으나, 웹의 actual validation에 쓸 실제 결과는 (a) 웹을 띄우는 PC에서 5개 시나리오를
  다시 실행하거나 (b) 다른 PC bundle을 가져와야 한다. (b)는 플레이북 §7상 redaction 재검증·allowlist·import verify를
  정의하는 별도 Spec이 필요하다.

## 4. 웹 원천의 현재 상태

- **웹 서버·HTTP API 없음.** ControlProof 진입점은 명령줄뿐이다(`pyproject.toml`의 `controlproof = engine.cli:main`).
  의존성에 템플릿 엔진이 있으나 엔진 코드가 import하지 않는다. `scripts/spec004_local.py` 285~290의 서버 기동은 WhyYou 대상
  서비스용이다.
- **승인된 UI 프로토타입·목업 없음.** 저장소(.venv 제외)에 HTML·CSS·JS·이미지·디자인 파일이나 Figma 링크가 없다. "목업"·
  "프로토타입"은 원칙 문장으로만 있다(Product Brief §12 641~652, V4 954). `docs/reference/skeleton/`은 옛 골격 문서 4개뿐이며
  지시가 아니다.
- 12개 카탈로그 데이터, 시나리오별 사람용 설명(보호 대상·WhyYou 구현 위치·수동 단계), 대상 기능 부재 근거(A-01~A-03)를
  담는 데이터 원천이 없다.

## 5. 미확인 — 확인 방법

| 항목 | 확인 방법 |
|---|---|
| 다른 PC Run bundle의 경로·redaction 상태 | 해당 PC에서 `verify`와 경로 스캔(이스케이프 경로 포함) |
| 위험 4(Spec 004 retest 정리 경로)의 실제 동작 | 합성 RESTORE_FAILED 부모로 cleanup-confirm 뒤 retest 시험 |
| 목업 프로토타입 승인 여부 | 제품 책임자 확인(Product Brief §12는 상세 기술 Spec 전 목업 확인을 요구) |
| 사용성 검토 참여자 확보 | 역할별(실행 담당자·검증 책임자·결과 검토자) 비작성자 섭외 가능 인원 확인 |
| A-01~A-03 기능 부재 근거 | WhyYou `374b122`에서 이의제기 관련 경로·화면이 없음을 확인한 조사 자료 작성 |
