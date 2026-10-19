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
| A10 | LOW | 낡은 상태 문구 | plan.md Project Structure, spec.md·plan.md Status | `tasks.md (아직 없음)`, "Plan 작성 중"·"다음은 Tasks다" | Project Structure만 고침. Status 줄은 Converge(T014)에서 갱신 |

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

## Gate

CRITICAL 0, HIGH 0(A1 RESOLVED). 해석 차이를 만드는 MEDIUM은 모두 Spec 009 안에서 고쳐 0이다. T004로 진행한다.
