# Analysis: Spec 009 N-01·N-03 (T003)

- 작성 2026-10-19. 대상: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `tasks.md`, `contracts/*.md`,
  `checklists/requirements.md`, `docs/research/Spec009_N01_N03_WhyYou_Source_Baseline.md`.
- 교차 대상 코드(ControlProof `b76af4c`): `engine/models.py`, `engine/scenario.py`, `engine/evidence.py`, `engine/runner.py`,
  `engine/cli.py`, `engine/retest.py`, `engine/presentation.py`, `engine/h01*.py`, `engine/executors/h01.py`,
  `engine/shared_records.py`, `scripts/h01_local.py`, `scripts/n02_local.py`, `scenarios/H-01.yaml`·`N-02.yaml`,
  `tests/unit/test_catalog_matrix_parity.py`.
- 기준선 시험: `pytest tests/contract tests/unit -q` → 1037 passed, 1 skipped (구현 전).
- 결과(최초): CRITICAL 0, HIGH 1, MEDIUM 3, LOW 6.
- 결과(2026-10-19 A1 결정 반영 뒤): **CRITICAL 0, HIGH 0(A1 RESOLVED), MEDIUM 0(3건 고침), LOW 1 남음(A10 Status 문구, T014).**
- 결과(2026-10-20 T014 뒤): **CRITICAL 0, HIGH 0, MEDIUM 0, LOW 0** — A10은 spec.md·plan.md Status를 "1단계 준비 완료(2026-10-20),
  actual NOT_RUN"으로 바꿔 해소했다.
  Phase Gate(Tasks → Implement) 통과.

## 판정 요약

| ID | 등급 | 범주 | 위치 | 내용 | 처리 |
|---|---|---|---|---|---|
| A1 | HIGH | 충돌·검증 불가 gate | plan.md Compatibility, tasks.md T013, AGENTS Spec 008 절, `engine/shared_records.py` 67~81·117~119 | 공유 기록 `--verify` "그대로 통과" 요구와 T004 이후 코드 변경이 양립하지 않는다 | **RESOLVED** — 해소안 1(아래) |
| A2 | MEDIUM | 문서 불일치 | evidence-bundle-v9.md 공통 파일 표 | `environment.snapshot.json`에 미검증 범위·한계 ID를 둔다고 했으나 plan Compatibility는 환경 스냅샷 허용 집합을 바꾸지 않는다 | 고침(Spec 009 안) |
| A3 | MEDIUM | 누락 | plan.md Compatibility | 새 필드가 기존 시나리오 snapshot digest에 들어가지 않는다는 규칙이 없다 | 고침(plan에 한 줄) |
| A4 | MEDIUM | 용어 불일치 | data-model.md, research.md R3 | schema를 `v5`, 계약 파일을 `scenario-profile-v5.md`로 적음(초안 번호 잔재) | 고침(v9) |
| A5 | LOW | 모호 | scenario-profile-v9.md v9 필드 표 | `target_access` "정렬된 목록"인데 `[SCREEN, API]`는 알파벳 순이 아니다 | 고침(선언 순서) |
| A6 | LOW | 모양 불일치 | scenario-profile-v9.md vs data-model.md | `limitations`가 `{id, text}` vs `ScopeItem{id, text, follow_up?}` | 고침(같은 모양, follow_up 비움) |
| A7 | LOW | 모호 | scenario-profile-v9.md 미검증 범위 절 | 공통 한계(LOCAL_EMULATED 등)가 YAML ID인지 불명확 | 고침(YAML ID 아님, N-01 목록 비어 있음) |
| A8 | LOW | 이름 대응 | plan.md Compatibility | Run 토큰 `N03_U1_POLICY_SWAP_INJECTION` 등과 YAML ID `N03-U1` 대응이 적혀 있지 않음 | 고침(대응 한 줄) |
| A9 | LOW | 줄 번호 | research.md R3 | H-01 시나리오 검증을 `scenario.py 321~347`로 적었으나 실제 H-01 분기는 336~351(321~335는 H-02) | 고침 |
| A10 | LOW | 낡은 상태 문구 | plan.md Project Structure, spec.md·plan.md Status | `tasks.md (아직 없음)`, "Plan 작성 중"·"다음은 Tasks다" | Project Structure 고침, Status 줄은 T014에서 갱신(해소) |

## A1 (HIGH) 공유 기록 검증과 Spec 009 코드 변경의 충돌

**사실**

- `engine/shared_records.py` `display_hashes`(67~81)는 `engine/**/*.py`, `engine/web/templates/*.html`, `engine/web/static/*`,
  `catalog/*.yaml`, `scenarios/*.yaml`, `scenarios/*.json` 전부의 해시를 공유본에 고정한다. `load_snapshot`(117~119)은 현재
  저장소의 값과 다르면 `"Snapshot display code/catalog differs; select its matching code version"`으로 거부한다.
- `review-data/snapshot.json`의 `display_files`에 `engine/models.py`, `engine/scenario.py`, `scenarios/H-01.yaml`이 들어 있다
  (2026-10-19 확인).
- T004는 `engine/models.py`·`engine/scenario.py`를 바꾸고 `scenarios/N-01.yaml`·`N-03.yaml`을 더한다. T005~T012도 `engine/`
  아래 파일을 만들거나 바꾼다.

**충돌**

- plan.md Compatibility: "`scripts.share_records --verify` 포함" 기존 결과가 바뀌지 않아야 한다.
- tasks.md T013: "`scripts.share_records --verify` 그대로 통과".
- 위 두 문장은 Spec 008 설계(코드 버전 고정)상 Spec 009 브랜치에서 T004 커밋 뒤에는 성립할 수 없다. 또 같은 checkout에서
  `engine.web --shared-snapshot review-data\snapshot.json`(기본 공유 모드)도 시작되지 않는다. 팀원이 이 브랜치에서 공유 기록을
  보는 흐름(D-029)이 끊긴다.
- 단위 시험(`tests/unit/test_shared_records.py`)은 임시 저장소를 쓰므로 이 충돌을 잡지 못한다. 자동 gate만으로는 드러나지 않는다.

**고르지 않은 해소안 (제품 책임자·연우 결정 필요, 다른 Spec·AGENTS 문서 변경 포함)**

1. T013 gate를 "공유본이 고정한 코드 버전(`b76af4c`)에서 `--verify` 통과 + Spec 009 브랜치에서는 거부 메시지가 정확히 'display
   code/catalog differs'"로 바꾼다. 공유본 재생성은 closure(T019)에서 Spec 008 절차로 한다. 이 브랜치의 공유 모드 열람은 별도
   worktree(`b76af4c`)에서 한다.
2. Spec 009 진행 중에도 공유 모드를 쓰려면 커밋마다 공유본을 다시 만든다. Spec 008 산출물(`review-data/`)과 D-029 기록을
   바꾸는 일이라 Spec 009 범위 밖이다.
3. `display_hashes`가 새 파일·특정 프로필 코드를 제외하게 한다. Spec 008 코드 의미 변경이라 Spec 009 범위 밖이다.

Analyze의 권고는 1이다. Spec 008 설계를 바꾸지 않고, 검증 대상이 무엇인지 문서로 분명히 할 수 있다.

**결정(2026-10-19, 연우): 해소안 1. RESOLVED.** 반영:

- plan.md Compatibility (a)~(d): 실제 gate는 `review-data/bundles` 25건 각각의 `engine.shared_records.verification` 결과가
  `snapshot.json` 기록과 같은지(24 VERIFIED, `ce5f2750…` INVALID). `--verify`와 기본 공유 웹 모드는 이 브랜치에서
  "Snapshot display code/catalog differs; select its matching code version"으로 거부되는 것이 정상이다. 새 공유본은 closure에서
  보성 검토로 만든다. 진행 중 열람은 `fixes-and-remaining-work` worktree에서 한다.
- plan.md Test Strategy 회귀, tasks.md T013(gate)·T019(공유 snapshot 재생성), quickstart.md §5(worktree 열람), AGENTS.md
  Spec 009 절 두 문장.
- 고정 시험: `tests/contract/test_scenario_digests_frozen.py`, `test_review_data_bundles_unchanged.py`(T004 전 GREEN),
  `test_shared_snapshot_rejects_changed_code.py`(T004 뒤).

## A2~A4 (MEDIUM, 고침)

- A2: 계약의 `environment.snapshot.json` 행을 "기존 환경 어댑터 캡처 그대로, 시나리오별 미검증 범위·한계 ID는
  `scenario.snapshot.yaml`과 `run.json`·`judgement.json`의 `unverified_scope`"로 고쳤다. 참고로 기존 캡처의 `unverified_scope`는
  `SPEC003_UNVERIFIED_SCOPE`(`AWS`, `N-01`, `N-03`) 또는 Spec 002 집합이다. 그래서 N-01 Run의 환경 스냅샷에도 `N-01`이 미검증으로
  찍힌다. H-01(`H-01`이 그 집합에 없음)과 달리 실행 대상 자신이 들어간다. 판정에는 영향이 없지만, 결과 화면이 환경 스냅샷의
  범위를 그대로 보이면 오해가 생긴다. T011에서 표시 원천을 Run `unverified_scope`로 정할 것(아래 "구현 메모").
- A3: plan Compatibility에 "`snapshot()`은 Spec 009 프로필이 아니면 세 필드를 digest에서 뺀다"를 더했다. `verify`는 봉인된
  정의 바이트로 digest를 다시 계산하므로(`engine/evidence.py` `_verify_snapshot_links`) 기존 bundle에는 영향이 없다. 하지만
  새 Run의 digest와 `tests/contract/test_h02_source_inventory.py`의 비교가 기존 시나리오에서 바뀌지 않게 하려면 이 규칙이 필요하다.
- A4: `data-model.md` 세 줄과 `research.md` R3 두 곳의 `v5`를 `v9`로 고쳤다.

## 범위 밖 문서에서 본 것 (고치지 않음)

- AGENTS.md Spec 009 절: "Keep … `tests/unit/test_catalog_matrix_parity.py` unchanged"는 정확하다. `test_rule3`은 카탈로그
  `profiles`만 세므로(9개) `scenarios/` 파일 추가와 무관하다. 문제 없음.
- AGENTS.md Spec 008 절·`specs/008-shared-run-records/quickstart.md`: 코드가 바뀐 브랜치에서는 `--verify`가 거부된다는 안내가
  없다. A1 결정 결과에 따라 보강이 필요할 수 있다.
- `engine/scenario.py` `SPEC004_FORBIDDEN_STEP_TERMS`·N-02 금지어에 `n-01`·`n-03`·`viewport`가 있다. Spec 004·N-02 프로필에만
  걸리므로 Spec 009 YAML과 충돌하지 않는다.

## 커버리지

| 요구 | T004 | 이후 Task |
|---|---|---|
| FR-002(프로필·정의 분리) | 프로필 2개·YAML 2개 | T009 |
| FR-005(대상 접근 기록) | `target_access` 필드·고정값 | T010(ACCESS_BLOCKED), T011(표시) |
| FR-055(카탈로그 불변) | parity 시험 무변경 통과 | T013 |
| FR-010~013, 030~032, 050~054, 056 | — | T005~T012 |
| SC-001~011 | — | T005~T013, Stage2 |

FR·SC 중 Task가 없는 항목은 없다. assertion 6개, EV9 7개 모두 계약과 Task에 연결된다.

## 구현 메모 (T004 이후 참고, 등급 없음)

- Run 검증: H-01 선례는 `unverified_scope` 집합을 고정하지 않는다(N-02·Spec 004는 고정). T004는 H-01과 같이 identity만 고정하고,
  Run `unverified_scope` 고정 여부는 T009에서 plan Compatibility 튜플로 정한다.
- `timing_policy`는 계약이 값을 고정하지 않는다. H-01과 같이 YAML에 두고 검증은 하지 않는다(canonical `timing_policy={}`).

### T005·T006에서 정한 것 (계약·지시와 다르거나 지시에 없던 것)

- `N01Capture.file`은 선택 값이다. 어댑터는 `{sha256, bytes}`만 내고 봉인 파일 이름은 실행기(T009)가 붙인다.
- `BROWSER_COMMIT_FAILED`는 측정 뒤 오류로 본다. N01-A1·A2는 측정값으로 판정하고, 동의 저장 실패는 N01-A3(저장 기록 없음 →
  `INSUFFICIENT_EVIDENCE`)만 판정한다. 다른 `measurement_error`는 해당 lane을 INCONCLUSIVE로 둔다. 커밋 실패로 화면 결과까지
  가리면 A1·A2와 A3의 독립(assertions-v9.md)이 깨지기 때문이다.
- N03-A1 판정 순서: 이전 식별값 검증 → 전후 상태 읽힘 → 2xx 또는 `state_digest` 변화면 FAIL → 전송 오류 코드면 INCONCLUSIVE →
  거부 코드(`CONSENT_POLICY_MISMATCH`·`CONSENT_COMMIT_REJECTED`)면 PASS → 그 밖의 코드(`CONSENT_COMMIT_RESPONSE_INVALID` 등)는
  INCONCLUSIVE. 전송 오류여도 상태가 바뀌었으면 관찰된 변화가 있으므로 FAIL이다.
- `N03Subject`를 두고 `applicant_id`는 선택이다(N-02 쿠키 시드 subject 모양에 맞춤).
- `N02CredentialStore`의 쓰기 메서드는 `set`이 아니라 `put`이다. 어댑터는 `put(subject_ref, cookie)`를 쓴다.
- 어댑터 결과 코드: 첫 페이지 로드 시간 초과만 `BROWSER_TIMEOUT`이다. 단계 안의 시간 초과·오류는 그 단계 코드
  (`BROWSER_EXCHANGE_FAILED`·`BROWSER_IDENTITY_FAILED`·`BROWSER_CONSENT_STEP_MISSING`·`BROWSER_MEASURE_FAILED`·
  `BROWSER_COMMIT_FAILED`)로 남기고 부분 record를 돌려준다. 추가 코드: `BROWSER_SESSION_COOKIE_MISSING`,
  `N01_INVITATION_TOKEN_MISSING`, `BROWSER_RESULT_INVALID`, `BROWSER_STEP_INCOMPLETE`(오류 없이 ready에 못 간 경우).
- 측정 JS: `center_hit`은 중심점에 요소가 있는지, `not_occluded`는 그 요소가 대상 자신·자손·조상이거나 같은 `label` 안인지다.
- 조립: N-01은 별도 `N02CredentialStore`를 쓴다(`create_whyyou_adapter`의 `n01_credentials`). 같은 저장소를 쓰는 동의 어댑터
  (`read_policy`·`read_state`)와 N-01 시드는 T007·T009에서 조립한다. `Settings.safe_projection`에는 `applicant_app_url`을
  더하지 않았다(기존 projection 시험 불변).
- `CONTROLPROOF_APPLICANT_APP_URL`은 다른 URL과 같이 로컬 호스트만 허용하고 끝의 `/`를 뗀다.

### T007·T008에서 정한 것 (계약·지시와 다르거나 지시에 없던 것)

- 커밋: N-03 lane은 같은 시드 계획·어댑터 안에 있어 T007·T008을 커밋 하나로 합쳤다.
- N-03 `raw_session_cookie`도 `secrets.token_urlsafe(48)`이다. N-02의 Run 유도 문자열은 쓰지 않는다. 그래서 같은 run_id라도
  `token_hash`·`session_hash`는 빌드마다 다르다. 결정론은 ID와 `plan.digest`에 적용된다(N-02와 같이 digest는 `*_id` 열만 덮는다).
- N-03 `display_name`은 `CP-N03-{lane}-{run_id[:8]}`이다(지시는 N-01만 정함). `applicant_email_normalized`는
  `<subject_ref>@example.invalid`이다.
- `json.dumps(plan)`은 dataclass라 직접 되지 않는다. JSON 표면으로 `plan.manifest()`(run_id·profile·lanes·tables·seed_digest)를 두고,
  시험은 repr·manifest·행 값·subject payload·lane dump 어디에도 raw 값이 없는지 본다. `plan.rows`는 `repr=False`다.
- 어댑터 생성자에 키워드 `read_factory`(재계수용 별도 connection; 기본 `engine.connect`, 주입한 transaction factory만 있으면 그것)와
  `inventory`(기본 SQLAlchemy inspector)를 더했다. `display_name_for(run_id, lane_id)`도 더했다(T009에서 N-01 본인 확인 이름을
  브라우저 어댑터에 넘길 때 씀). `Spec009SeedPort`에 포함했다.
- 결과 코드: 성공 `SPEC009_LANES_REMOVED`. 더한 코드: `SPEC009_PROFILE_UNSUPPORTED`, `SPEC009_TEARDOWN_FAILED`(정리 트랜잭션 롤백),
  `SPEC009_RESIDUE_READ_FAILED`(재계수 실패), `SPEC009_RESIDUE_REMAINS`(ok=False, data.status=`FAILED`). 소유권과 credentials는
  `SUCCEEDED`일 때만 놓는다. `FAILED`면 같은 ID로 다시 정리할 수 있게 남긴다.
- 정리 알고리즘: `OWNED_COLUMNS`는 h01_live 값을 import해 `criterion_id`·`recruiting_stage_id`를 더했다(h01_live.py 불변).
  (a)는 시드 행 identity와 같은 행을 건너뛰고 (b) 시드 역순 삭제에 맡긴다. 그래서 `product_rows_removed`는 제품이 만든 행만 센다.
  (a)의 PK 삭제는 `_delete_row` 대신 PK 열로 직접 지운다. `applicant_access_tokens`의 PK `token_hash`는 `_id`로 끝나지 않아
  `_delete_row`가 identity 없음으로 실패하기 때문이다.
- residue 표 집합: `spec009_cleanup.REQUIRED_RESIDUE_TABLES`(9개) == `engine/n01.py` 필수 표이고, `engine/n03.py` 필수 표(8개,
  `applicant_access_tokens` 없음)는 그 부분집합이다. 불일치 없음. 판정 모듈은 고치지 않았다. N-03 counts에도 tokens(0)가 들어간다.
- 필수 표가 catalog에 없거나 소유 열이 없으면 0으로 보고한다(지시대로). 스키마가 바뀌어 소유 열이 사라지면 잔여가 0으로 보일 수
  있으므로 실제 Run 전 catalog 확인이 필요하다.
- 조립: `AdapterSet.spec009_seed`·`spec009_consent`를 더했다. 저장소 변수 이름은 `n01_credentials` 그대로 두고 N-03도 쓴다.

### T009·T010에서 정한 것 (계약·지시와 다르거나 지시에 없던 것)

- 구조: 두 실행기의 공통 부분(preflight·journal·정리·봉인)은 `engine/executors/spec009.py`의 `Spec009Executor`, 공통
  `verify_facts` 검사는 `engine/spec009_evidence.py`의 `verify_common`에 두었다. `n01.py`·`n03.py`(실행기·증적)는 그 위의 얇은 층이다.
  `settings`는 `adapters.spec009_seed.settings`를 지연 읽기한다(registry가 어떤 adapters로도 실행기를 만들 수 있게).
- N-03 판정 모델 확장(`engine/n03.py`): `N03StaleAttempt.current`·`submitted`, `N03LatestCommit.reread`를 선택 값으로 바꿨다. 정책을
  못 읽은 Run도 그대로 봉인하고 INCONCLUSIVE로 판정하기 위해서다. `response_class`(`2xx`/`non-2xx`)를 더했다. 동의 어댑터의 성공
  응답에는 상태 코드가 없다(`status_code`는 거부 응답에만 있음). 어댑터를 바꾸면 N-02·Spec 004 기록 모양이 바뀌므로 어댑터는 그대로
  두고, 실행기가 `ok=True`를 `2xx`로 적는다. 정확한 코드를 지어내지 않는다.
- N-03 past lane: 동의 완료 commit이 성공했을 때만 `past_before`를 기록한다. 준비 실패를 "과거 기록이 바뀜"(FAIL)으로 읽지 않고
  N03-A3 INCONCLUSIVE가 되게 하기 위해서다.
- 시드 실패: `seed_lanes`가 실패하면 증적 없이 `N0X_SEED_FAILED:<code>` RuntimeError로 끝낸다. 지시는 어댑터 실패에서 Run을 멈추지
  말라고 했지만, 시드가 없으면 판정할 subject가 없다. 시드 트랜잭션은 통째로 롤백되므로 차단도 걸지 않는다. journal은 남는다.
- 정리 결과: teardown이 `ok`이고 스스로 `SUCCEEDED`라고 할 때만 `SUCCEEDED`다. counts가 없으면 `{"unknown": 1}`. 120초를 넘기면
  `FAILED`. 차단 이름은 `n01-notice`·`n03-stale-consent`다.
- 반환: 인터페이스(run, judgement, directory)는 H-01과 같다. `verify_bundle` 결과는 `executor.verification`에 두고, VERIFIED가
  아니면 `N0X_BUNDLE_INVALID`로 실패한다.
- `observations.jsonl`: 단계별 행 `{step_id, phase, lane, action, ok, adapter_code}`. 실행기 예외는 `executor-error` 행으로 남긴다.
- 증적 연결: EV9-07은 run·assertions·judgement 파일과 `intrinsic:sealed-manifest`. N-01 캡처 PNG는 있을 때만 EV9-03에 더 연결한다
  (`LINKS` 상수에는 없음). `n03-lanes.json`은 `{lanes, past_setup(정책 읽기·commit 코드), errors}`, `n01-lanes.json`은 측정 기록에서
  만든 lane 요약이다. `n0X-scope.json`은 `{scenario_id, target_access, unverified_scope, unverified_scope_items, limitations,
  common_limitations, excluded_scope}`이고, 공통 한계 ID는 `LOCAL_EMULATED`·`SYNTHETIC_DATA`·`EXTERNAL_AI_BLOCKED`(문구는 이 구현이 정함)다.
- `verify_facts` 추가 검사: subjects의 lane 순서·Run 소유, N-03 attempt·latest subject = stale lane, lanes 파일 = 측정 기록 요약,
  identifiers의 lane·subject_ref, manifest의 PNG 집합 = 캡처 기록 집합. 불일치 파일 이름이 정해지지 않는 예외는 N-03은
  `n03-stale-attempt.json`, N-01은 `n01-measurements.json`으로 적는다.
- preflight: 검사 실패를 capability에 이렇게 붙였다. 설정 격리·`CONTROLPROOF_WHYYOU_PYTHON`·health fixture → `target.environment.read`,
  git clean·target snapshot → `target.version.read`, openapi 경로 → `consent.policy.read`(N-03은 `consent.commit.write`도),
  `consent_records`·`invitation_state_history` → `consent.state.read`, `applicant_access_sessions` → N-03 `n02.subjects.seed·teardown`
  / N-01 `n01.invitations.teardown`, `applicant_access_tokens`·`applicant_profiles` → `n01.invitations.seed·teardown`. 연결 거부·
  401·403은 ACCESS_BLOCKED, 그 밖은 RUNNER_NOT_READY. 전체 상태는 `evaluate_readiness`로 합친다(그래서 target snapshot의 dirty·
  fixture 규칙도 같이 적용된다). N-01 지원자 앱 URL 미설정도 `applicant.screen.open` ACCESS_BLOCKED다. Chromium 검사는
  `sync_playwright()`로 `executable_path`를 읽는다(드라이버 프로세스를 띄운다, 다운로드 없음). probe는 `adapters.spec009_probes`로
  바꿀 수 있고 없으면 `LocalProbes`다. N-01·N-03은 WhyYou helper를 부르지 않지만 `CONTROLPROOF_WHYYOU_PYTHON` 확인은 지시대로 넣었다.
- 화면 어댑터: `expected_fragments` 인자를 `fragment_builder`로 바꿨다. GET 응답 본문은 측정 함수 안에서만 쓰고 반환하지 않는다. 더한
  코드 `BROWSER_POLICY_RESPONSE_MISSING`·`BROWSER_POLICY_RESPONSE_INVALID`. 조각 ID는 `ai_assist.title|description`,
  `human_final.ai_role`, `recording_purpose.notice|<purpose>.title`, `retention.label|days`, `deletion.label|method`(11개).
- N-01 실행기: 어댑터 예외는 `BROWSER_ADAPTER_ERROR`, 캡처 전 실패(`APPLICANT_APP_URL_MISSING`·`BROWSER_TIMEOUT` 등)는
  `step_reached=error` 부분 기록으로 봉인한다. 캡처 해시가 받은 바이트와 다르면 캡처를 버린다(→ INCONCLUSIVE).
- CLI: N-01·N-03도 `--profile` 필수 목록에 넣었다(H-01은 원래 없음). retest는 queue 스냅샷을 찍지 않는다. preflight payload의
  `unverified_scope`는 H-01과 같이 기존 versioned 값 그대로다(표시는 T011). retest 규칙은 H-01 분기를 같이 쓰고 메시지만 `Spec 009`.
- 실제 Run 전에 확인할 것(이번에 고치지 않음): `cleanup-confirm`에 Spec 009 차단 subject 분기가 없어 H-03 기본 분기로 간다(H-01
  차단도 같다). 실제 Playwright 경로·버튼 이름·GET 응답 관찰, `read_consent_facts` SQL, LocalProbes는 fake로만 시험했다.

### 복구 경로에서 정한 것

- 복구 로직은 `engine/spec009_recovery.py`(`check_block`·`recover`·`recount`)에 두고 `scripts/spec009_recover.py`와
  `cleanup-confirm` 분기가 같이 쓴다. 읽기 전용 재계수를 위해 `spec009_cleanup.expand_resources`(SELECT만)를 떼어 냈다.
- 결정론 ID로 다시 만든 시드 계획에서 `session_hash`·`token_hash`는 시드 때 뽑은 원시 값에서 나오므로 다시 만들 수 없다. 복구는
  이 두 열을 뺀 ID(`session_id`·`invitation_id`·`applicant_id` 등)로 시드 행을 식별·삭제한다. 그래서 `product_rows_removed`는
  teardown과 같이 제품이 만든 행만 센다.
- `check_block`은 블록 파일의 run_id와 봉인 `run.json`의 `execution_profile`을 본다. 거부 코드 `SPEC009_RECOVERY_BLOCK_MISSING`·
  `SPEC009_RECOVERY_BLOCK_MISMATCH`·`SPEC009_RECOVERY_BUNDLE_MISSING`·`SPEC009_RECOVERY_PROFILE_MISMATCH`. 스크립트는 `SUCCEEDED`면
  0, 아니면 1로 끝나고 증적 파일은 어느 쪽이든 쓴다.
- `cleanup-confirm`은 증적의 `status` 값을 믿지 않고 재계수만 본다. 증적 불일치는 `SPEC009_CLEANUP_EVIDENCE_INVALID`, 재계수가
  비었거나 0이 아니면 `SPEC009_SAFE_STATE_NOT_CONFIRMED`. 이 분기는 `create_runtime`을 부르지 않는다.

### T011·T012에서 정한 것

- T011: `engine/presentation.py`(검토 projection)는 바꾸지 않았다. 지시대로 `engine/web/readmodel.py`가 봉인
  `scenario.snapshot.yaml`의 `definition`에서 `target_access`·`unverified_scope_items`·`limitations`를 읽는다(`target_access_line`,
  `scope_item_lines`). 결과 화면은 "실행 한계" div 바로 위에 대상 접근 줄, div 안에 `<ul class="scope-items">`로 미검증 세 줄과
  한계 한 줄을 둔다. 한계 줄 형식은 "한계: …"로 정했다. `Judgement.unverified_scope` 코드값은 기존처럼 개발자 영역에만 있다.
- 시나리오 화면의 "프로필 준비 상태" 줄은 카탈로그 `profiles`가 있어야 나온다. N-01·N-03은 closure 전이라 `profiles`가 비어
  그 블록이 없으므로, 대상 접근 줄은 공식 검증 이력 줄 바로 아래에 둔다. 값은 프로필 정의에 있으면 그것을, 없으면 CLI의
  프로필→파일 대응(`_profile_scenario_path`)으로 `scenarios/N-01.yaml`·`N-03.yaml`을 읽는다.
- T012: `start_applicant_app`은 기본 `start`를 감싼 래퍼에서 ready 뒤에 부른다. `processes["applicant_app"]`에 기본 하네스와 같은
  `{ProcessId, ParentProcessId, Created}`를 기록해 기존 `stop`이 생성 시각을 다시 확인하고 내린다(`spec004_local.py` 무수정).
  `pending_process` 기록도 같다. 60초 안에 200이 없으면 `SPEC009_APPLICANT_APP_NOT_READY`로 실패하되 PID는 남겨 `stop`이 내린다.
  포트 거부 코드는 `SPEC009_PORT_IN_USE:<port>`이고 `up`에서만, API 포트(기본 8080)와 5174 중 하나라도 쓰이면 거부한다.
  `--with-applicant-app`은 `up` 밖에서 쓰면 사용 오류다. 지원자 앱 환경은 `environment(state, for_cp=False)`를 쓴다.

## Run 뒤 음성 대조 (2026-10-20, 측정 로직 무수정)

`tests/integration/test_applicant_measure_real.py`: WhyYou 동의 단계 모양의 정적 HTML을 실제 Chromium(Playwright 번들)에서
`measure_fragments`(=`MEASURE_JS`, 동작 불변으로 모듈 함수로 꺼냄)로 측정했다. 조각은 `engine.n01.expected_fragments(고정 정책)`.

| # | 경우 | 화면 | 기대 | 실제 거짓 플래그 | 결과 |
|---|---|---|---|---|---|
| 1 | 변형 없음 | PC·모바일 | 전부 참 | 없음 | 기준 맞음 |
| 2 | 보관기간 dd 위 `position:fixed` 불투명 div | PC | not_occluded 거짓 | `retention.days`: not_occluded | 잡음 |
| 3 | 삭제 방법 dd `white-space:nowrap` 긴 문구 | 모바일 | no_horizontal_overflow 거짓 | `deletion.method`: in_viewport·not_occluded·no_horizontal_overflow, 나머지 10조각: no_horizontal_overflow(문서 전체 넘침) | 잡음 |
| 4 | ai_role 문단 `position:absolute; left:-3000px` | PC·모바일 | in_viewport 거짓 | `human_final.ai_role`: in_viewport·not_occluded | 잡음 |
| 5 | 삭제 방법 dd `visibility:hidden` | PC·모바일 | 어느 플래그든 거짓 | 없음(전부 참) | **못 잡음**(strict xfail) |
| 6 | recording_notice 문단 `opacity:0` | PC·모바일 | 어느 플래그든 거짓 | 없음(전부 참) | **못 잡음**(strict xfail) |
| 7 | recording_notice를 `height:1.2em; overflow:hidden` 부모로 감쌈 | 모바일 | 어느 플래그든 거짓 | 없음(전부 참) | **못 잡음**(strict xfail) |
| 8 | recording_notice `-webkit-line-clamp:1` | 모바일 | 어느 플래그든 거짓 | 없음(전부 참) | **못 잡음**(strict xfail) |
| 9 | ai_role 문단 삭제 | PC·모바일 | text_present 거짓 | `human_final.ai_role`: 네 플래그 모두 | 잡음 |

못 잡은 원인으로 보이는 코드(`engine/adapters/whyyou/applicant_browser.py` `MEASURE_JS`):
- 5: 49~50줄 `related`가 `hit.contains(found)`(조상 hit)를 허용한다. `visibility:hidden` 요소는 `elementFromPoint`가 건너뛰어
  부모를 돌려주므로 가림 없음으로 판정된다.
- 6: 계산된 스타일(`opacity`·`visibility`·`color`)을 보지 않는다.
- 7: 45~46줄 `in_viewport`가 요소 자신의 경계 상자만 보고 조상의 `overflow` 잘림을 보지 않는다.
- 8: 51줄 `noOverflow`가 가로(`scrollWidth`)만 보고 세로 잘림(`scrollHeight > clientHeight`)을 보지 않는다.

보강안(구현하지 않음): `getComputedStyle`로 `visibility`·`opacity`(조상 누적 포함)를 검사하는 플래그를 더하고, 조상 hit 허용을 label 안으로만
좁힌다. 조상 중 `overflow`가 `visible`이 아닌 요소의 경계와 교차 영역이 요소 경계보다 작은지, 요소의 `scrollHeight > clientHeight`인지를
보는 세로 잘림 검사를 더한다. 이번 실제 Run(`48a70f5e…`) 판정에는 손대지 않는다.

### 원인 분류와 측정 v2 결정 (2026-10-20)

- 분류: **실행기 결함(측정 누락)**. 대상(WhyYou) 동작이나 복구 운영의 문제가 아니다. 첫 실제 Run `48a70f5e…`의 캡처에는 네
  상황이 보이지 않았고 그 판정(PASS)은 v1 기록으로 봉인된 그대로 보존한다(덮어쓰지 않음).
- 결정: `MEASURE_JS`를 v2로 바꾸고 lane 기록에 `measurement_version`을 둔다. `engine/n01.py`는 기록의 버전으로 규칙을 고른다
  (없음·1 → v1 네 조건, 코드 경로·출력 모양 불변 / 2 → v2 여섯 조건 / 그 밖 → INCONCLUSIVE). `verify_facts`가 같은 함수로
  재판정하므로 v1 봉인 bundle은 새 코드에서도 같은 결과다. 새 코드로 두 실제 Run(`48a70f5e…` 15 files, `f27b68e8…` 17 files)을
  다시 verify해 둘 다 VERIFIED·mismatch 0을 확인했다.
- v2 음성 대조 결과(실제 Chromium, `test_applicant_measure_real.py`, xfail 0):

| # | 경우 | 화면 | v2 거짓 플래그 |
|---|---|---|---|
| 1 | 변형 없음 | PC·모바일 | 없음(여섯 플래그 모두 참) |
| 2 | 보관기간 위 fixed 불투명 div | PC | `retention.days` not_occluded |
| 3 | 삭제 방법 nowrap 긴 문구 | 모바일 | `deletion.method` in_viewport·not_occluded·no_horizontal_overflow, 나머지 10조각 no_horizontal_overflow |
| 4 | ai_role `left:-3000px` | PC·모바일 | `human_final.ai_role` in_viewport·not_occluded |
| 5 | 삭제 방법 `visibility:hidden` | PC·모바일 | `deletion.method` not_occluded·style_visible |
| 6 | recording_notice `opacity:0` | PC·모바일 | `recording_purpose.notice` style_visible |
| 7 | recording_notice 부모 1.2em `overflow:hidden` | 모바일 | `recording_purpose.notice` not_occluded·not_clipped(`clip_ancestor` = `div`) |
| 8 | recording_notice line-clamp 1 | 모바일 | `recording_purpose.notice` not_clipped |
| 9 | ai_role 문단 삭제 | PC·모바일 | `human_final.ai_role` 여섯 플래그 모두 |

- 새 v1 기록(가짜 어댑터)은 v2 전용 필드를 null로 직렬화하지만, 실제 첫 Run 기록에는 그 키가 없다. 모델은 둘 다 v1로 읽는다.
- 실제 화면(WhyYou 동의 단계)에서 v2 여섯 조건이 어떻게 나오는지는 N-01 child Run에서 처음 확인된다.

## 보성에게 알릴 것

1. `cleanup-confirm`에서 H-01 차단 subject(`h01-human-decision`)는 전용 분기가 없어 H-03 기본 분기(`fault.target_safe`)로 간다.
   Spec 009는 전용 분기를 더했고 H-01 쪽은 고치지 않았다.
2. 이 브랜치에서는 `scripts.share_records --verify`와 기본 공유 웹 모드가 "Snapshot display code/catalog differs"로 거부된다
   (snapshot이 `b76af4c` 코드를 고정). 공유 bundle 25건의 verification은 그대로이며, 새 공유본은 closure에서 재생성해야 한다.
3. `engine/models.py` `ConsentStateSnapshot.lane_id` 타입을 `N02LaneId | N01LaneId | N03LaneId`로 넓혔다(T005). N-02 값의
   직렬화는 바뀌지 않으며 기존 bundle 25건 verification과 digest 고정 시험이 그대로 통과한다.
4. 구현 중 본 다른 Spec 문서 불일치: T003 때 적은 Spec 008 quickstart·AGENTS Spec 008 절의 "코드가 바뀐 브랜치에서 `--verify`
   거부" 안내 누락 외에 새로 본 것은 없다. 관련 코드 관찰 하나: CLI preflight 출력의 `unverified_scope`는 versioned 프로필(H-01
   포함)에 Spec 002 AWS 목록을 그대로 보인다(Spec 009는 고치지 않음).

## Gate

CRITICAL 0, HIGH 0(A1 RESOLVED). 해석 차이를 만드는 MEDIUM은 모두 Spec 009 안에서 고쳐 0이다. T004로 진행한다.
