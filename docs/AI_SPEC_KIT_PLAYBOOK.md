# ControlProof AI·Spec Kit 작업 플레이북

## 1. 목적

팀원이 다른 AI 세션에서 작업을 이어도 같은 제품 의미, 같은 브랜치 안전 규칙과 같은 완료 기준을
적용하도록 하는 실행 가이드다. 현재 상태를 파악할 때는 `docs/TEAM_HANDOFF.md`, 작업 방법을 파악할
때는 이 문서를 따른다.

## 2. 새 세션의 필수 입력 순서

AI에게 구현을 요청하기 전에 다음 순서로 읽히고 실제 파일 상태를 확인한다.

1. `AGENTS.md`
2. `docs/TEAM_HANDOFF.md`
3. `docs/product/ControlProof_MVP_Scenario_Coverage_Matrix.md`
4. `docs/product/ControlProof_WhyYou_2주_MVP_기능범위_v4.md`
5. `docs/product/ControlProof_MVP_Product_Brief.md`
6. `docs/product/ControlProof_MVP_Decision_Log.md`
7. `.specify/memory/constitution.md`
8. 현재 작업 Spec의 `spec.md`, `plan.md`, `tasks.md`, `validation.md`, `traceability.md`
9. WhyYou를 다루면 그 Spec의 source baseline과 실제 checkout의 branch·commit·dirty 상태

AI가 기억이나 이전 대화만으로 현재 상태를 추정하게 하지 않는다.

## 3. 기능 Spec 한 개의 표준 사이클

| 단계 | 명령/활동 | 종료 조건 |
|---|---|---|
| 0. Source discovery | 대상 코드·API·DB·UI·시험 접점 조사 | 확인된 사실, 미확인 사항, source SHA가 문서에 있음 |
| 1. Specify | `$speckit-specify` | 사용자 이야기, 요구사항, 성공 기준, 범위 밖이 기술 중립적으로 확정 |
| 2. Clarify | `$speckit-clarify` | 팀원이 다르게 해석할 중요한 미결정 사항 0개 |
| 3. Plan | `$speckit-plan` | 실제 저장소 구조와 기술 경계, 증적·복구·보안 설계가 확정 |
| 4. Tasks | `$speckit-tasks` | 의존순서·파일·시험·문서 갱신 작업이 실행 가능한 크기로 분해 |
| 5. Analyze | `$speckit-analyze` | CRITICAL·HIGH 0개, 해석 차이를 만드는 MEDIUM 0개 |
| 6. Implement | `$speckit-implement` | Tasks 구현, 단위·계약·통합 시험 통과 |
| 7. Actual validation | 격리 WhyYou actual Run | 최초 사실, bundle, restore, source SHA와 한계 기록 |
| 8. Converge | `$speckit-converge` | Spec/Plan/Tasks/Traceability/Validation/README/인수인계가 서로 일치 |

Spec 문서 여러 개를 한꺼번에 만든 뒤 구현하는 방식이 아니다. 한 Spec의 실제 검증과 문서 수렴까지
닫고 다음 Spec으로 넘어간다.

## 4. 브랜치 규칙

- ControlProof 작업은 해당 Spec 전용 브랜치에서 한다.
- WhyYou 변경은 `bosung/controlproof-h03-integration` 또는 그로부터 분기한 개인 브랜치에서만 한다.
- WhyYou `main`에 직접 commit·push하지 않는다.
- 실제 Run 전 두 저장소의 branch, HEAD SHA와 dirty 상태를 기록한다.
- 검증한 source SHA와 문서만 바뀐 최신 HEAD를 혼동하지 않는다.
- Spec 001·002 통합은 독립 재현 gate 뒤 하나의 검토 가능한 PR로 main에 병합한다.

## 5. 완료라고 말할 수 있는 조건

다음 중 하나라도 없으면 기능 Spec은 구현 완료가 아니다.

- 승인된 요구사항과 성공 기준
- 코드와 자동시험
- 격리된 actual-stack 실행 또는 왜 실행 불가능한지에 대한 정식 상태
- assertion별 증적 연결과 bundle 무결성 확인
- fault를 썼다면 restore 확인
- 최초 FAIL을 보존한 수정 전·후 계보
- source commit, 환경 종류와 미검증 범위
- 최신 Validation, Traceability, TEAM_HANDOFF와 README

`pytest PASS`, 문서 작성 완료, 화면이 한 번 열림 중 하나만으로 완료를 주장하지 않는다.

## 6. 독립 재현 gate

Spec 001·002의 현재 actual Run은 한 PC에서 생성됐고 runtime bundle은 Git에 없다. 따라서 main 병합 전
다른 팀원이 다음 최소 gate를 수행한다.

1. 새 checkout에서 Quickstart의 개인 절대 경로가 없는지 확인한다.
2. ControlProof와 WhyYou의 지정 브랜치·commit을 checkout한다.
3. `H03_DLQ_V2` preflight를 `READY`로 만든다.
4. 합성 데이터로 Run 한 건을 실행한다.
5. `show`와 `verify`가 성공하고 restore가 `SUCCEEDED`인지 확인한다.
6. 새 Run ID, 두 source SHA, verdict, manifest SHA-256, 실행환경과 차이를 Validation에 추가한다.

이 gate는 다른 PC에서 실제 수행하기 전까지 `PENDING_EXTERNAL_REPRODUCTION`이다. AI가 성공했다고
가정하거나 기존 Run ID를 복사해 완료 처리하면 안 된다.

## 7. 증적 공유 원칙

- `runs/`와 `.controlproof/` 전체는 Git에 commit하지 않는다.
- 실제 개인정보, token, `.env`, 원본 queue URL, receipt handle, message body를 공유하지 않는다.
- 대표 bundle 공유 기능이 생기기 전에는 Validation의 Run ID, source SHA, assertion 결과와 manifest
  SHA-256이 공식 기록이다.
- 향후 공유용 export를 만들면 redaction 재검증, allowlist 파일만 포함, 새 archive SHA-256과 import
  verify 절차를 별도 Spec으로 정의한다.

2026-10-02 일회성 팀 인계 예외: 사용자가 공개 Git 게시를 승인한 Spec 003 N-02 부모 Run
`15cef078-ee24-4f0e-91ef-381e0f7a1cc2`의 원본 bundle, 대응 정비 기록, WhyYou cleanup 증거 JSON만
두 기능 브랜치에 추적한다. 그 밖의 `.controlproof/` 생성물과 이후 Run에는 위 원칙을 그대로 적용한다.
이 예외는 독립 PC Run 완료나 대상 서비스 PASS를 뜻하지 않는다. 팀원은 pull 후 원본 SHA와 bundle
`verify`를 확인한다.

## 8. AI에게 이어서 맡길 때 사용할 프롬프트

```text
현재 저장소의 AGENTS.md와 docs/AI_SPEC_KIT_PLAYBOOK.md를 먼저 전부 읽고,
docs/TEAM_HANDOFF.md에서 공식 상태를 확인해라. 현재 작업 Spec과 대상 WhyYou checkout의
branch/HEAD/dirty 상태를 실제로 검사한 뒤, 다음 미완료 단계 하나만 진행해라.
WhyYou main에는 변경을 만들지 말고, actual Run을 하지 않았다면 실행 완료라고 쓰지 마라.
작업 뒤 변경 파일, 검증 명령, 남은 외부 gate와 문서 간 상태 일치 여부를 보고해라.
```

Spec 003을 이어서 진행할 때는 여기에 다음을 추가한다.

```text
Spec 003은 T001~T093 구현·검증 기록과 PR 검토 보완(ID-003-19)이 있다. 현재 상태는
TEAM_HANDOFF와 validation의 Current status / PR review closure를 먼저 확인하라.
specs/003-n02-consent-order/의 spec.md, plan.md, tasks.md, research.md, data-model.md, contracts/와
quickstart.md를 입력으로 작업 브랜치 통합 후 최종 converge의 종료 범위를 검토하라.
현재 실제 child는 A1~A4·A6 PASS, A5·A7 INCONCLUSIVE이며 검토 보완 후 실제 Run은 NOT_RUN이다.
자동 A1~A7 PASS를 실제 WhyYou verdict로 쓰지 말고, 부모 증거를 수정하지 마라.
main 병합은 사용자가 금지했으므로 별도 승인 전 진행하지 마라.
```

2026-10-05~07 이어받기 결과(연우): T080~T093 완료. 최초 Run의 FAIL은 실행기 결함 10건과 WhyYou 보호조치
2건으로 분류됐고, child `7b59237e-0a96-403a-9add-28b91011e950`가 A1~A4·A6 PASS, A5·A7 `INCONCLUSIVE`로 봉인됐다.
실행기 수정은 모두 실패 시험 → 최소 수정 → 전체 회귀 순서였고, WhyYou 수정은 실제 Run에서 동의 없는
처리 시작이 관찰된 뒤에만 추가했다. 격리 재현(PostgreSQL+pgvector, moto, WhyYou API·작업자)으로 실행기
변경을 먼저 검증한 다음 팀원 PC에서 공식 Run을 돌렸다. 세부는 Implementation Decisions ID-003-09~18.

## 9. 문서 수렴 체크

Converge에서 최소한 다음 상태가 같아야 한다.

- Spec status와 Validation closure
- tasks 체크 상태와 실제 코드/시험
- Traceability의 requirement→test→evidence 연결
- Scenario Coverage Matrix의 현재 상태
- TEAM_HANDOFF의 공식 상태·다음 작업
- README의 로드맵·재현 링크
- Product Brief의 현재 산출물 설명
- Decision Log의 변경 이유

서로 다른 문서에 다른 “현재 상태”가 있으면 새 기능으로 넘어가지 않는다.
