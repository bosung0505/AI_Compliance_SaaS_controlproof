# Contract: N-01·N-03·H-01·H-02 Scenario Profile v5

## Identity

| Field | N-01 | N-03 | H-01 | H-02 |
|---|---|---|---|---|
| `schema_version` | `controlproof.scenario.v5` | 같음 | 같음 | 같음 |
| `scenario_id` | `N-01` | `N-03` | `H-01` | `H-02` |
| `version` | `1.0.0` | `1.0.0` | `1.0.0` | `1.0.0` |
| `execution_profile` | `N01_NOTICE_V1` | `N03_STALE_CONSENT_V1` | `H01_DECISION_AUTHORITY_V1` | `H02_WRITE_SURFACE_V1` |
| `bundle_profile_contract` | `controlproof.bundle-profile.spec006.v1` | 같음 | 같음 | 같음 |
| 파일 | `scenarios/N-01.yaml` | `scenarios/N-03.yaml` | `scenarios/H-01.yaml` | `scenarios/H-02.yaml` |
| `target_access` | `[SCREEN, API]` | `[API]` | `[API]` | `[SOURCE]` |

v5는 이 네 프로필에만 쓴다. v1~v4 검증 규칙은 바꾸지 않는다.

## v5 필드 (v4에 더하는 것)

| Field | 형식 | 규칙 |
|---|---|---|
| `target_access` | `SCREEN`·`API`·`SOURCE`의 비어 있지 않은 부분집합, 정렬된 목록 | 필수. 위 표 값과 정확히 같아야 한다(spec FR-005) |
| `unverified_scope_items` | `{id, text, follow_up}` 목록 | 선택. 아래 표의 ID만 허용, 프로필별 집합과 같아야 한다 |
| `limitations` | `{id, text}` 목록 | 선택. 아래 표의 ID만 허용 |

표시 문구: `SCREEN` = "화면", `API` = "API", `SOURCE` = "소스 열람". 한 줄 표기는 " + "로 잇는다(예: "화면 + API").

## Canonical assertions

```text
N-01: N01-A1, N01-A2, N01-A3
N-03: N03-A1, N03-A2, N03-A3
H-01: H01-A1, H01-A2, H01-A3, H01-A4
H-02: H02-A1, H02-A2, H02-A3
```

N03-A4는 없다(Clarify 답 3). 판정 규칙은 [assertions-v6.md](./assertions-v6.md).

## Canonical evidence

```text
EV6-01 scenario / target / environment / capability / source commit snapshot       (all)
EV6-02 lanes, synthetic subjects, credential kinds (no raw values)                 (N-01, N-03, H-01)
EV6-03 N-01 PC·mobile captures, item measurements, operations                      (N-01)
EV6-04 policy identifiers (screen, server, stored) and consent completion time     (N-01)
EV6-05 N-03 stale/latest identifiers, rejection response, past record before/after (N-03)
EV6-06 H-01 path x subject requests and responses (credential raw excluded)        (H-01)
EV6-07 H-01 before/after projections, audit rows, idempotency observation          (H-01)
EV6-08 H-02 surface lists, classification, reach analysis                          (H-02)
EV6-09 state changes, restore, safe state, residue                                 (N-01, N-03, H-01)
EV6-10 judgement and sealed manifest                                               (all)
```

적용 집합 밖의 EV6를 YAML에 두면 무효다.

## Canonical lanes

| 프로필 | lanes |
|---|---|
| N-01 | `pc`, `mobile` |
| N-03 | `stale`, `past` |
| H-01 | `fd-baseline`, `fd-denied`, `bm-baseline`, `bm-denied` |
| H-02 | 없음 |

## 미검증 범위·한계 ID

| ID | 프로필 | 종류 | 문구 | 후속 조건 |
|---|---|---|---|---|
| N03-U1 | N-03 | unverified_scope | 실행 중 정책 교체 주입 | WhyYou 시험용 정책 교체 수단과 분석 작업 정책 귀속 저장 필드 |
| N03-U2 | N-03 | unverified_scope | 교체 시점 근접 제출 | 같음 |
| N03-U3 | N-03 | unverified_scope | 분석 작업의 정책 귀속 | 같음 |
| N03-L1 | N-03 | limitation | 이전 정책 식별값은 실제 교체 없이 만든 값 | — |
| H01-L1 | H-01 | limitation | `SYSTEM`·AI 어시스턴트는 HTTP 자격 증명이 없어 시도하지 않음, 쓰기 경로는 H-02 참조 | — |
| H02-L1 | H-02 | limitation | V4 §7.3 "회사 사용자가 AI 점수 순위와 독립적으로 결정"은 확인하지 않음 | — |
| H02-L2 | H-02 | limitation | 정적 검사 범위(깊이 상한, 동적 디스패치 상수 해석만) | — |

모든 프로필은 공통 한계 `LOCAL_EMULATED`·합성 데이터·외부 AI 차단과 미검증 범위 `AWS`를 가진다(spec FR-056).

## 프로필별 규칙

| 규칙 | N-01 | N-03 | H-01 | H-02 |
|---|---|---|---|---|
| `restore_policy` 필수 | 예 | 예 | 예 | **아니오**(`NONE_STATIC`만 허용) |
| `allowed_model_fixtures` 1개 이상 | 예(`n02-analysis-v1`) | 예 | 예 | **아니오**(빈 목록) |
| 하네스 스택 필요 | 예(+지원자 앱) | 예 | 예 | 아니오(WhyYou checkout만) |
| 금지 step 용어 | `policy swap`, `final-decision` | `viewport`, `final-decision` | `viewport`, `consent` | `viewport`, `consent`, `seed` |

`NONE_STATIC`은 H-02 외 프로필에서 무효다.

## Required capabilities (Plan 고정, 이름은 `capability.py` 등록과 같게)

- N-01: `applicant-app-reachable`, `browser-chromium`, `applicant-invitation-seed`, `consent-policy-read`, `consent-state-projection`, `external-ai-blocked`, `source-clean`
- N-03: `applicant-session-seed`, `consent-policy-read`, `consent-commit`, `consent-state-projection`, `external-ai-blocked`, `source-clean`
- H-01: `decision-operations`, `decision-stages`, `ready-report-seed`, `principal-clients`, `decision-state-projection`, `audit-events-read`, `single-api-process`, `external-ai-blocked`, `source-clean`
- H-02: `source-commit-readable`
