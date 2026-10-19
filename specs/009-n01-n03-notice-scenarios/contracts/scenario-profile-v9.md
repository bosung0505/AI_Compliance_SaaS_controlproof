# Contract: N-01·N-03 Scenario Profile v9

## Identity

| Field | N-01 | N-03 |
|---|---|---|
| `schema_version` | `controlproof.scenario.v9` | 같음 |
| `scenario_id` | `N-01` | `N-03` |
| `version` | `1.0.0` | `1.0.0` |
| `execution_profile` | `N01_NOTICE_V1` | `N03_STALE_CONSENT_V1` |
| `bundle_profile_contract` | `controlproof.bundle-profile.spec009.v1` | 같음 |
| 파일 | `scenarios/N-01.yaml` | `scenarios/N-03.yaml` |
| `target_access` | `[SCREEN, API]` | `[API]` |
| `lanes` | `[pc, mobile]` | `[stale, past]` |

v9는 이 두 프로필에만 쓴다. v1~v7 검증 규칙은 바꾸지 않는다. schema·bundle contract 번호가 Spec 번호를 따르는 것은 보성의
H-01(v6/spec006)·H-02(v7/spec007) 관례다.

## v9 필드 (v4 모양에 더하는 것)

| Field | 형식 | 규칙 |
|---|---|---|
| `target_access` | `SCREEN`·`API`·`SOURCE`의 비어 있지 않은 부분집합, `TargetAccessKind` 선언 순서(SCREEN → API → SOURCE) | 필수. 위 표 값과 정확히 같아야 한다(spec FR-005) |
| `unverified_scope_items` | `{id, text, follow_up}` 목록 | 선택. 아래 표의 ID만 허용, 프로필별 집합과 같아야 한다 |
| `limitations` | `{id, text, follow_up}` 목록(`follow_up`은 비움) | 선택. 아래 표의 ID만 허용 |

세 필드는 `ScenarioDefinition`에 기본값 빈 튜플로 들어가며 Spec 009 프로필이 아닌 정의에서는 비어 있어야 한다.
표시 문구: `SCREEN` = "화면", `API` = "API", `SOURCE` = "소스 열람". 한 줄 표기는 " + "로 잇는다(예: "화면 + API").

## Canonical assertions

```text
N-01: N01-A1, N01-A2, N01-A3
N-03: N03-A1, N03-A2, N03-A3
```

N03-A4는 없다(Clarify 답). 판정 규칙은 [assertions-v9.md](./assertions-v9.md).

## Canonical evidence

```text
EV9-01 scenario / target / environment / capability snapshot                          (both)
EV9-02 lanes, synthetic subjects (no raw tokens or cookies)                            (both)
EV9-03 N-01 PC·mobile captures, fragment measurements, operations, DOM token check     (N-01)
EV9-04 policy identifiers (screen, server, stored) and consent completion time        (N-01)
EV9-05 N-03 stale/latest identifiers, rejection response, past record before/after    (N-03)
EV9-06 restore, safe state, residue                                                   (both)
EV9-07 judgement and sealed manifest                                                  (both)
```

적용 집합 밖의 EV9를 YAML에 두면 무효다. `required_evidence` 순서는 N-01 `EV9-01~04, 06, 07`, N-03 `EV9-01, 02, 05, 06, 07`.

## Canonical steps

| 프로필 | step_id 순서 (phase) | 마지막 step |
|---|---|---|
| N-01 | `seed-invitations`(BASELINE) → `open-consent-screens`(INJECTED) → `complete-consent`(INJECTED) → `cleanup-owned-subjects`(RECOVERED) | `always_run: true` |
| N-03 | `seed-lanes`(BASELINE) → `submit-stale-consent`(INJECTED) → `reread-and-commit`(INJECTED) → `cleanup-owned-subjects`(RECOVERED) | `always_run: true` |

## 미검증 범위·한계 ID

| ID | 프로필 | 종류 | 문구 | 후속 조건 |
|---|---|---|---|---|
| N03-U1 | N-03 | unverified_scope | 실행 중 정책 교체 주입 | WhyYou 시험용 정책 교체 수단과 분석 작업 정책 귀속 저장 필드 |
| N03-U2 | N-03 | unverified_scope | 교체 시점 근접 제출 | 같음 |
| N03-U3 | N-03 | unverified_scope | 분석 작업의 정책 귀속 | 같음 |
| N03-L1 | N-03 | limitation | 이전 정책 식별값은 실제 교체 없이 만든 값 | — |

모든 프로필은 공통 한계 `LOCAL_EMULATED`·합성 데이터·외부 AI 차단과 미검증 범위 `AWS`를 가진다(spec FR-056). 공통 항목은
YAML ID가 아니라 환경 스냅샷·Run `unverified_scope`에서 나온다. 그래서 N-01 YAML의 두 목록은 비어 있다. `excluded_scope`에는
`AWS`, `외부 AI 모델 품질`, 그리고 N-01은 `동의 전 처리 차단(N-02 소유)`, N-03은 `실행 중 정책 교체·분석 작업 정책 귀속`을 둔다.

## 프로필별 규칙

| 규칙 | N-01 | N-03 |
|---|---|---|
| `restore_policy` 필수 | 예(`action: n01.owned.cleanup`) | 예(`action: n03.owned.cleanup`) |
| `allowed_model_fixtures` | `{n02-analysis-v1: 092de5950a39ba3a7255c8696ffb073cddc65cda4615237044e3d910e32f9828}` | 같음 |
| 하네스 스택 필요 | 예(+지원자 앱) | 예 |
| 금지 step 용어 | `policy swap`, `final-decision` | `viewport`, `final-decision` |

모델 fixture는 호출하지 않지만 환경 스냅샷·Run 검증이 fixture 식별을 요구하므로 하네스 값(`n02_local.py`와 같음)을 고정한다.

## Required capabilities (이름은 N-02 관례대로 점 표기, `capability.py` 등록과 같게)

- N-01: `target.version.read`, `target.environment.read`, `applicant.screen.open`, `browser.chromium.available`,
  `n01.invitations.seed`, `n01.invitations.teardown`, `consent.policy.read`, `consent.state.read`
- N-03: `target.version.read`, `target.environment.read`, `n02.subjects.seed`, `n02.subjects.teardown`, `consent.policy.read`,
  `consent.commit.write`, `consent.state.read`

`applicant.screen.open`이 실패하면 `ACCESS_BLOCKED`, `browser.chromium.available`이 실패하면 `RUNNER_NOT_READY`다(FR-004·FR-005).
외부 AI 차단·소스 clean은 기존 preflight 공통 확인이다.
