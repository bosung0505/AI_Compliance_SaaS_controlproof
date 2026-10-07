# Specification Analysis Report: Spec 004 E-01·E-02

- 실행일: 2026-10-07
- 대상: `spec.md`, `plan.md`, `tasks.md`, `research.md`, `data-model.md`, `contracts/*`, `quickstart.md`, `traceability.md`,
  `.specify/memory/constitution.md`
- 기준 commit: ControlProof `53df004` + 이번 Tasks 변경, WhyYou `eec8f70`
- 방법: `$speckit-analyze` 탐지 항목(중복, 모호, 미명세, Constitution 정합, 커버리지, 불일치). 사용자 지시에 따라 보고서를
  파일로 남기고 CRITICAL·HIGH와 해석 차이를 만드는 MEDIUM은 같은 세션에서 문서를 고쳤다.
- 확장 hook: `before_tasks`는 optional git commit이며 작업 트리가 깨끗해 실행하지 않았다. `before_analyze` hook은 없다.

## Findings

| ID | Category | Severity | Location(s) | Summary | Resolution |
|---|---|---|---|---|---|
| I1 | Inconsistency | HIGH | spec US1 AS2·FR-011, scenario-profile E01-A1, data-model CitationCase, plan §7 | 잘못된 ID가 "보고서 어디에도 없어야" PASS라고 적어 `OTHER_CRITERION` ID(같은 보고서 VALID 항목의 정상 행)·`OTHER_APPLICANT` ID(참조 보고서의 정상 행) 때문에 항상 FAIL이 되는 판정 규칙이었다 | **Fixed**: 범위를 "그 기준의 보고서 항목(축 인용과 그 항목의 Evidence 행)"으로 좁히고 다른 항목·참조 보고서의 원래 행은 위반이 아님을 다섯 곳에 명시 |
| I2 | Conflict | HIGH | spec FR-022 ↔ scenario-profile E01-A4, plan §7 | spec은 복원 뒤 행 digest가 다르면 FAIL, 계약은 같은 사실을 `RESTORE_FAILED`로 처리 | **Fixed**: digest 불일치·복원 실패 = `RESTORE_FAILED`(Spec 003 ID-003-14 분리), digest 같고 조회가 다르면 E01-A4 FAIL로 spec·plan·계약 통일 |
| I3 | Conflict | HIGH | spec US1 AS1·FR-011 ↔ scenario-profile E01-A1 | spec은 "사유 보존"을 PASS 조건으로, 계약은 PASS 조건이 아니라고 적음 | **Fixed**: PASS 조건 = 비운 축의 `rationale`이 비어 있지 않음. WhyYou 고정 보류 문구 일치는 기록만(대상 문구 변경에 판정이 흔들리지 않게). data-model에 `rationale_present` 추가 |
| I4 | Inconsistency | HIGH | evidence-bundle-v4 파일 표·EV4 매핑, scenario-profile capability 집합 | E-02가 `model-emissions.jsonl`을 필수로 요구하지만 E-02에는 `model.emission.read` capability도 EV4-03도 없음. E-01 `storage-probe.json`은 어떤 EV4에도 매핑되지 않음(verify가 미등록 파일로 판단할 수 있음) | **Fixed**: `model-emissions.jsonl`은 E-01 전용, `storage-probe.json`은 EV4-04(E-01)에 매핑 |
| M1 | Inconsistency | MEDIUM | quickstart §5 ↔ tasks Phase 8 | quickstart는 샌드박스 진단을 "선택", tasks는 최초 공식 Run의 선행 조건 | **Fixed**: 최초 공식 Run 전 필수, 팀원 재현(T097)에서는 생략 가능으로 통일 |
| M2 | Task ordering | MEDIUM | tasks T023~T025 | 같은 WhyYou 시험 파일을 고치는 세 작업에 `[P]` 표시 | **Fixed**: `[P]` 제거, 순서 실행 명시 |
| M3 | Coverage gap | MEDIUM | tasks T042 ↔ T047, scenario capability 18개 | E-01 capability 18개 중 변경 주입 4개를 조합하는 작업이 없었다(T042는 mutation adapter가 생기기 전) | **Fixed**: T042는 인용 경로 capability만, T047이 mutation capability를 조합하고 18/18 도달 시점을 명시 |
| M4 | Coverage gap (non-functional) | MEDIUM | SC-003, tasks Phase 8 | 540초 예산을 공식 Run 전에 측정하는 작업이 없었다(보고서 4~2개를 작업자가 순차 처리) | **Fixed**: T073·T075가 진단 Run 시간을 기록하고 위험이면 T078 실행기 finding으로 처리 |
| M5 | Inconsistency | MEDIUM | plan §7 E01-A3 ↔ scenario-profile E01-A3 | plan은 제거 확인에 타임라인 변화를 필수처럼 적었고 계약은 보조 증거 | **Fixed**: 제거 확인 = 별도 연결의 행 부재 receipt, 타임라인은 보조. POST_REMOVAL 5xx FAIL과 전제(PRE 200)도 계약과 일치시킴 |
| L1 | Terminology | LOW | controlproof-cli-v4 | preflight `unverified_scope`에 격리 한계를 섞음 | **Fixed**: `unverified_scope`(미실행 범위)와 `limitations`(격리 한계)를 분리 정의 |
| L2 | Stale status | LOW | spec Status | "다음 단계는 Plan" | **Fixed** |
| L3 | Underspecification | LOW | plan Project Structure | tasks가 고치는 `config.py`, `runner.py`, `judge.py`, `execution.py`, `retest.py`가 구조에 없음 | **Fixed** |
| L4 | Underspecification | LOW | data-model ReportRecordSnapshot ↔ FR-042 | 텍스트는 SHA-256과 길이를 남긴다는 FR과 달리 길이 필드 없음 | **Fixed**: `summary_length` 추가 |
| L5 | Wording | LOW | spec FR-013 | "네 종류의 잘못된 ID"에 빈 인용(ID 아님)이 포함 | **Fixed** |
| L6 | Stale wording | LOW | spec Edge Cases | 72 고정 전제의 문장이 H-2 결정 뒤에도 남음 | **Fixed** |
| L7 | Cross-document drift | LOW | `AGENTS.md`(Current next feature = Spec 003, WhyYou 통합 브랜치 이름), `docs/TEAM_HANDOFF.md`(Spec 004 "계획 확정·미착수"), `README.md` | 저장소 공통 상태 문서가 Spec 004 진행을 반영하지 않음. Spec 004 산출물 사이 불일치는 아님 | **Open** (아래 보류 O-2) |

CRITICAL 0, HIGH 4(모두 수정), MEDIUM 5(모두 수정), LOW 7(6 수정, 1 보류).

## Constitution Alignment

위반 없음.

- I(증적): 모든 assertion이 EV4와 raw projection을 요구하고 누락·불일치는 INCONCLUSIVE다.
- II(대상·준비·결과 분리): fixture 불일치·scoring 원본 drift는 `RUNNER_NOT_READY`, emission 불일치는 실행기 결함
  INCONCLUSIVE, 점수 저장 HTTP 부재는 `NO_TEST_TARGET`이 아님을 명시했다.
- III(사람 결정): 점수 임계값·자동 결정 없음. 재계산은 산술 확인이다.
- V(격리·복구): 변경 주입은 Run 소유 행만, always-run 복구, `RESTORE_FAILED` 차단, 외부 AI 금지.
- VI(불변·계보): 최초 Run 봉인 뒤 분류·승인·child(T080~T088). 진단 Run과 공식 Run 분리.
- VII(추적): traceability 초안이 FR·SC·assertion·EV4를 task·test·구현에 연결한다.

## Coverage Summary

| 구분 | 수 | Task 있음 | 비고 |
|---|---:|---:|---|
| Functional Requirements (FR-001~004, 010~013, 020~022, 030~034, 040~043, 050~052) | 23 | 23 | traceability.md |
| Success Criteria (SC-001~007) | 7 | 7 | SC-006은 actual·재현 작업 |
| Assertions (E01-A1~A4, E02-A1~A3) + 진단 E01-D1 | 8 | 8 | |
| Evidence (EV4-01~10) | 10 | 10 | |

Unmapped tasks: 없음. T022(브랜치 생성)·T029(PR)는 Dependencies 절에 매핑된다.

## Metrics

- Total requirements (FR+SC): 30
- Total tasks: 97 (T001~T097), WhyYou 작업 8개(T022~T029) + 조건부 WhyYou 제품 보완 2개(T086, T087)
- Coverage: 100% (requirements with ≥1 task)
- Ambiguity count: 0 (I1·I3·M5 수정 뒤)
- Duplication count: 0
- Critical issues: 0
- Unresolved placeholders: quickstart의 `<e01-run-id>` 등은 실제 Run 전 의도된 자리표시자(T092에서 교체)

## Open Items (보류)

| ID | 질문 | 선택지 | 추천 |
|---|---|---|---|
| O-1 | 공식 Run(Phase 9)의 WhyYou 기준 | (a) fixture PR(T029)을 Phase 8 전에 `bosung/controlproof-n02-integration`에 병합하고 그 HEAD로 실행 (b) Spec 003처럼 개인 브랜치 head로 실행 | (a). 공식 기준 브랜치와 Run의 source SHA가 일치한다 |
| O-2 | 저장소 공통 상태 문서(L7) 갱신 시점 | (a) Implement 전에 `AGENTS.md`·`TEAM_HANDOFF.md`·`README.md`의 현재 기능·브랜치 문장만 문서 전용 커밋으로 갱신 (b) T096 종료 동기화 때 한꺼번에 | (a). 새 AI 세션이 `AGENTS.md`를 먼저 읽으므로 Spec 003을 현재 기능으로 오해하지 않게 한다 |

두 항목 모두 Spec 004 산출물 사이의 해석 차이는 아니며 Implement 시작을 막지 않는다(O-1은 Phase 8 전까지 결정).

## Next Actions

- CRITICAL·HIGH·해석 차이를 만드는 MEDIUM이 0건이므로 `$speckit-implement`로 넘어갈 수 있다.
- 첫 Implement 세션은 Phase 1(T001~T004) → Phase 2 시험(T005~T011)부터 시작한다. WhyYou Phase 3(T022~)은 병렬로 시작할
  수 있다.
