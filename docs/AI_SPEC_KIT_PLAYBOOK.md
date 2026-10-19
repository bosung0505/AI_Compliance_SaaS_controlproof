# ControlProof AI·Spec Kit 작업 플레이북

2026-10-19 공유 정책 변경(D-029): 검토한 실제 실행 기록과 계보를 코드와 함께 배포해 같은 결과 화면을 제공한다.
§7이 현재 규칙이다. [설계 이유 조사·전환 준비](research/Run_Record_Sharing_Preparation.md)를 따른다.
후속 Spec008에서 공유 snapshot·기본 읽기 모드와 별도 Git clone 검증을 구현했다. 현재 방법은
[공유 기록 README](../review-data/README.md), 검증 범위는 Spec008 Validation을 따른다.

최신 checkpoint(2026-10-18): Spec003 N-02 로컬 범위 Complete. 최종 `16dbd987…`
A1~A7 PASS, VERIFIED21, 복구 성공, DB 잔여행0. 실제 소스 CP `3ea1509`/WhyYou `e64ff9d`.
이전 2026-10-08 checkpoint의 N-02 대기 상태는 이력이다. 최신 절차는 Spec003 Quickstart와
actual-closure/validation을 따른다. main·AWS·Spec005 전체 마감과 별도 PC 재현은 자동 완료되지 않는다.


## 1. 목적

팀원이 다른 AI 세션에서 작업을 이어도 같은 제품 의미, 같은 브랜치 안전 규칙과 같은 완료 기준을
적용하도록 하는 실행 가이드다. 현재 상태를 파악할 때는 `docs/TEAM_HANDOFF.md`, 작업 방법을 파악할
때는 이 문서를 따른다.

현재 checkpoint(2026-10-08): Spec 004 T001~T097 및 converge 완료(T087 NOT_REQUIRED), Complete.
E-01 최초 FAIL·D1-only FAIL을 보존한 공식 수정 child PASS; 새 checkout E-01 4030503c…와 E-02
970108fe…가 WhyYou 374b122에서 실제 PASS/SUCCEEDED/VERIFIED, 잔여행 0이다.
최종 CP full 939 PASS 한 번, WhyYou scoped 188 PASS; 이후 wrapper 이식성 수정 setup scoped 12 PASS.
상세 source·manifest·시간·명령은 [Spec 004 validation](../specs/004-e01-e02-score-evidence/validation.md)
마지막 closure를 따른다. 재현은 해당 quickstart/spec004_local.py를 사용한다. 다음 기능은 Spec 005다.
승인된 SC-006은 두 번째 clean checkout을 허용한다(ID-004-36/D-017). 다른 PC와 AWS는 미검증이며,
아래 main 통합용 독립 PC gate는 별도다. Spec 003의 INCONCLUSIVE/최종 converge 대기는 유지한다.

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
- WhyYou Spec 003·004 변경은 `bosung/controlproof-n02-integration` 또는 그로부터 분기한 개인 브랜치에서만 한다.
  Spec 001·002의 기존 통합 경로는 `bosung/controlproof-h03-integration`이다.
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

2026-10-01에는 Spec001·002 actual Run이 한 PC에 있어 다음 독립 재현 gate를 정했다.
2026-10-19 D-029에 따라 검토한 원본은 공유할 수 있지만, 파일 열람은 다른 PC에서 새로 실행한 증거가 아니다.
아래 gate와 D-019의 인정 범위는 공유 정책과 별도로 유지한다.

1. 새 checkout에서 Quickstart의 개인 절대 경로가 없는지 확인한다.
2. ControlProof와 WhyYou의 지정 브랜치·commit을 checkout한다.
3. `H03_DLQ_V2` preflight를 `READY`로 만든다.
4. 합성 데이터로 Run 한 건을 실행한다.
5. `show`와 `verify`가 성공하고 restore가 `SUCCEEDED`인지 확인한다.
6. 새 Run ID, 두 source SHA, verdict, manifest SHA-256, 실행환경과 차이를 Validation에 추가한다.

이 gate는 다른 PC에서 실제 수행하기 전까지 `PENDING_EXTERNAL_REPRODUCTION`이다. AI가 성공했다고
가정하거나 기존 Run ID를 복사해 완료 처리하면 안 된다.

2026-10-13 인정 기록(D-019): 연우 PC가 Spec 005 Phase 9에서 실행한 H-03 `H03_DLQ_V2` Run
`277d3f5a-766a-45ab-9f1d-28a3a30a82e6`을 **현재 통합 대상(`374b122`) 기준의 독립 PC 재현 gate 기록으로
인정한다**(제품 책임자 승인, 연우 전달). 위 1번(새 checkout)과 2번(지정 commit) 두 조건은 이 건에 대해
면제했다. 인정 범위는 다음과 같다.

- 새로 clone한 checkout이 아니라 그 PC의 기존 clean clone을 사용한 별도 PC 재현이다.
- 실행 환경: ControlProof `9856a03` dirty 0, WhyYou `bosung/controlproof-n02-integration` `374b122`
  dirty 0, `LOCAL_EMULATED`, fixture `h03-report-v1`, preflight READY 18/18.
- 결과: A1~A9 PASS, 복구 SUCCEEDED, bundle verify VERIFIED(33 files), manifest SHA-256
  `3d6b0a85d2c657e4c3bedbfb5938399b8235ada488c0616bd641a340184fbcdf`.
- 플레이북이 지정한 과거 commit과 동일 조건의 재현이 아니다. 현재 통합 대상에 대한 교차 PC 재현이다.

이 인정은 H-03 `H03_DLQ_V2` 한 건에만 적용한다. 다른 시나리오나 AWS 환경까지 독립 검증한 것으로
확대하지 않으며 AWS는 `NOT_RUN`을 유지한다. main 병합은 이 gate와 별개로 별도 승인이 남는다.
기록은 `specs/005-web-workbench-report/validation.md`의 Phase 9 절에 있다.

## 7. 증적 공유 원칙

현재 정책은 **검토한 실제 실행 원본·상세 근거·계보를 코드와 함께 공유**하는 것이다(D-029, 2026-10-19 사용자 요청).
기존 ‘실제 기록은 각 PC에만 두고 요약으로 인계’ 정책과 D-018의 기록 가져오기 보류는 이 범위에서 대체한다.

- `runs/`와 `.controlproof/` 전체 ignore는 유지한다. 검토한 파일은 별도 추적 경로의 버전 고정 snapshot으로 배포한다.
  Spec008 경로는 `review-data/bundles/<run-id>`, 고정 목록은 `review-data/snapshot.json`이다.
- 실제 개인정보, token, `.env`, 자격 증명, 원본 queue URL·receipt handle·비검토 message body와 임시 probe는 공유하지 않는다.
- 파일 허용 목록·민감정보 재검사·bundle verify를 수행하고, Run ID·부모·원래 source SHA·manifest 해시를 함께 고정한다.
  Git 파일 배포는 snapshot 목록과 파일 해시로 검증하며 archive를 만들 경우 그 SHA-256도 기록한다.
- 최초 FAIL·INCONCLUSIVE·중단 기록을 보존한다. 원본 바이트를 고치거나 누락 파일을 예시 데이터로 대체하지 않는다.
  찾지 못한 이력은 누락으로 명시한다. 공유에 부적합한 원본이 있으면 파생본 설계와 원본과의 관계를 별도로 정의한다.
- 공유 기록 조회·무결성 검증은 독립 실행과 다르다. D-019 인정 범위와 AWS `NOT_RUN`은 바뀌지 않는다.
- Spec008의 export/검증/로딩·같은 화면 확인을 사용한다. 별도 Git clone에서 원본25건·결과 API53개·근거24개를 확인했다.
  [실행 방법](../review-data/README.md)을 따른다. 공유 snapshot과 표시 코드가 다르면 시작을 거부하므로
  후속 표시 코드/카탈로그 변경 시 원본 바이트를 보존한 새 snapshot 맥락을 함께 검토·버전 관리한다.
  조사 범위에서 미확보된 N02 중간 원본 1건은 부재로 표시한다. pull이 누락된 역사 전체를 복원한다는 뜻은 아니다.

역사적 예외(2026-10-02): 사용자가 공개 Git 게시를 승인한 Spec 003 N-02 부모 Run
`15cef078-ee24-4f0e-91ef-381e0f7a1cc2`의 원본 bundle, 대응 정비 기록, WhyYou cleanup 증거 JSON만
두 기능 브랜치에 추적했다. 이 원본은 그대로 보존한다. 이후 공유는 위 D-029 정책을 따른다.
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
