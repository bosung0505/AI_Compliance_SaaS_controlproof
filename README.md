# ControlProof

ControlProof는 합성 데이터를 이용해 AI 서비스의 절차적 보호조치가 정상·우회·예외·장애 조건에서 실제로 작동하는지 시험하고, 판정과 재현 가능한 증적을 남기는 도구다. 첫 번째 검증 대상은 AI 면접 서비스 WhyYou다.

## 현재 개발 기준

- 제품 범위: [ControlProof × WhyYou 2주 MVP 기능 범위 V4](./docs/product/ControlProof_WhyYou_2주_MVP_기능범위_v4.md)
- 시나리오 범위표: [12개 관리·5개 실행·4개 NOT_RUN·3개 NO_TEST_TARGET](./docs/product/ControlProof_MVP_Scenario_Coverage_Matrix.md)
- 제품 정의: [MVP Product Brief](./docs/product/ControlProof_MVP_Product_Brief.md)
- 제품 결정: [MVP Decision Log](./docs/product/ControlProof_MVP_Decision_Log.md)
- 개발 원칙: [ControlProof Constitution](./.specify/memory/constitution.md)
- 완료 기능: [Spec 001 — 실행·증적 기본 모델과 H-03 최소 수직 흐름](./specs/001-execution-evidence-h03/spec.md)
- 완료 명세: [Spec 002 — H-03·E-03 장애·재시도·DLQ 확장](./specs/002-h03-e03-fault-expansion/spec.md)
- Spec 002 재현 절차: [로컬 actual-stack quickstart](./specs/002-h03-e03-fault-expansion/quickstart.md)
- Spec 002 검증 기록: [자동·실제 스택 검증 결과](./specs/002-h03-e03-fault-expansion/validation.md)
- Spec 002 추적성: [요구사항→작업→테스트→구현](./specs/002-h03-e03-fault-expansion/traceability.md)
- 팀 인수인계: [현재 공식 상태·재현·검토 통합 가이드](./docs/TEAM_HANDOFF.md)
- AI 작업 플레이북: [다른 AI 세션에서도 같은 Spec Kit 사이클을 재현하는 방법](./docs/AI_SPEC_KIT_PLAYBOOK.md)
- Spec 003 소스 기준선: [WhyYou N-02 확인 사실과 미확인 사항](./docs/research/Spec003_N02_WhyYou_Source_Baseline.md)
- 작성된 기능 명세: [Spec 003 — N-02 동의·AI 처리 순서 검증](./specs/003-n02-consent-order/spec.md)
- Spec 003 기술 계획: [경계·lane·fault·인과관계·시험 설계](./specs/003-n02-consent-order/plan.md)
- Spec 003 작업 목록: [테스트 우선 구현·최초 Run·조건부 보완 순서](./specs/003-n02-consent-order/tasks.md)
- Spec 003 검증 기록: [부모·child actual Run 원장, 회귀 기록, 알려진 한계](./specs/003-n02-consent-order/validation.md)
  — child `7b59237e…`는 A1~A4·A6 PASS, A5·A7 `INCONCLUSIVE`(격리 대상의 문서 분석 결과 미입증)
- Spec 003 구현 계약: [데이터 모델](./specs/003-n02-consent-order/data-model.md),
  [계약](./specs/003-n02-consent-order/contracts/),
  [구현 후 재현 절차](./specs/003-n02-consent-order/quickstart.md)
- 도입 결정: [ADR-0001 — Spec Kit과 팀 골격 채택](./docs/decisions/0001-adopt-spec-kit-and-skeleton.md)

`docs/reference/skeleton/`은 팀원이 만든 초기 골격의 원문 보관본이다. 제품 의미가 충돌할 때는 위 문서와 Constitution을 우선한다.

## Spec Kit

이 저장소는 GitHub Spec Kit 1.0.10을 다음 구성으로 초기화했다.

- Integration: Codex skills
- Scripts: PowerShell
- Feature numbering: sequential
- Extension: Git workflow

Codex에서 프로젝트를 다시 연 뒤 `.agents/skills/`의 기능을 사용한다.

```text
$speckit-specify
$speckit-clarify
$speckit-plan
$speckit-tasks
$speckit-analyze
$speckit-implement
$speckit-converge
```

Spec 001과 Spec 002는 clarify, plan, tasks, analyze, implement와 actual-stack 검증을 마쳤다.
Spec 002는 로컬 WhyYou를 대상으로 H-03 재시도 소진·DLQ·결정 우회와 E-03 저장 전/후 장애,
사람 최종결정 멱등성, 봉인 증적과 불변 FAIL→PASS 재시험을 구현했다. 이는 전체 2주 MVP나
ControlProof 웹 UI가 완성됐다는 뜻이 아니며, 현재 사용자 접점은 개발·검증용 CLI다.

## 후속 Spec 로드맵

후속 순서는 [Product Brief](./docs/product/ControlProof_MVP_Product_Brief.md)와
[Decision Log D-013](./docs/product/ControlProof_MVP_Decision_Log.md)을 기준으로 한다.

| 순서 | 상태 | 범위 |
|---|---|---|
| Spec 003 | 구현·actual validation 기록 완료, PR 검토 보완 | T001~T093 기록 완료. 실제 child `7b59237e…`는 A1~A4·A6 PASS, A5·A7 INCONCLUSIVE. 2026-10-07 검토에서 복구 시간·A7 원본 증거·H-03 동의 seed 보완; 최신 회귀는 validation 참조. 최종 converge 전이며 Spec 전체 Complete 또는 실제 N-02 PASS로 선언하지 않는다. |
| Spec 004 | T001~T078 완료, 공식 Run `NOT_RUN` | Phase 8 진단 E-02 PASS, E-01 A3 FAIL(P1); 실행기 정리·비교·타임라인 seed 보완. 다음 T079 preflight. Spec 전체 미완료. |
| Spec 005 | 계획 확정·미착수 | 웹 워크벤치·12개 시나리오 카탈로그·보고서와 웹 UX 검토 |

WhyYou 연결 기반을 별도 Spec으로 먼저 만들지 않는다. 각 시나리오에 필요한 capability를 해당 Spec의
수직 흐름 안에서 구현한다. 또한 세 Spec 문서만 먼저 완성한 뒤 개발하는 방식이 아니라, Spec 003의
명세→구현→실제 검증을 닫은 뒤 Spec 004, Spec 005 순으로 같은 사이클을 반복한다.

Spec 001·002의 actual Run은 현재 한 PC에서만 수행됐다. main 통합 전 다른 팀원이 새 checkout에서
`H03_DLQ_V2` 한 건을 재현해 source SHA·manifest SHA-256·restore 결과를 Validation에 추가해야 한다.
이 외부 gate 전에는 “독립 재현 완료”라고 표현하지 않는다.

## 개발 환경

프로젝트 코드는 Python 3.12 이상을 요구한다.

```powershell
uv sync --extra dev
uv run pytest
```

로컬 보안 도구가 `uv sync`의 Python 탐색 출력을 방해하는 Windows 환경에서는 다음 방식으로 같은 개발환경을 만들 수 있다.

```powershell
python3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

## 저장소와 브랜치 안전성

Spec 002는 나란히 있는 두 저장소를 사용한다.

| 저장소 | 허용 브랜치 | 용도 |
|---|---|---|
| `AI_Compliance_SaaS_controlproof` | `yeonwoo/004-e01-e02-score-evidence` | Spec 001~003 기반(병합된 `003-n02-consent-order`)과 현재 기능 Spec 004 |
| `gbsa_aws` | `bosung/controlproof-n02-integration` | WhyYou local/test 전용 N-02 observer·fault hook; product guard 변경 전 최초 사실 시험 대상 |

WhyYou의 `main`에 ControlProof 변경을 직접 commit 또는 push하지 않는다. actual Run 전에는 두 checkout이
모두 clean이어야 하며, preflight가 commit·dirty 상태와 target snapshot을 다시 고정한다. `.env`,
credential, 원본 queue URL, receipt handle, message body와 실제 지원자 자료는 commit하거나 bundle에
복사하지 않는다.

처음 합류한 팀원은 아래를 먼저 확인한다.

```powershell
$controlProofRepo = (Resolve-Path -LiteralPath "<ControlProof-checkout>").Path
$whyYouRepo = (Resolve-Path -LiteralPath "<WhyYou-checkout>").Path

Set-Location -LiteralPath $controlProofRepo
git branch --show-current
git status --short

Set-Location -LiteralPath $whyYouRepo
git branch --show-current
git status --short
```

두 placeholder는 각 팀원의 실제 checkout으로 한 번만 바꾼다. 두 저장소가 같은 부모 폴더에 있을
필요는 없다.

## 실행 프로필의 의미

| Profile | Scenario | 시험하는 경계 | 핵심 질문 |
|---|---|---|---|
| `H03_MINIMAL_V1` | H-03 | Spec 001 최소 흐름 | 기본 장애·복구·사람 최종결정 안전성이 작동하는가 |
| `H03_DLQ_V2` | H-03 | 저장 전 반복 장애와 DLQ | 실패가 숨지 않고 세 최종결정 경로가 모두 차단되는가 |
| `E03_BEFORE_V2` | E-03 | 결과 내구 저장 전 | 장애 중 부분 효과가 없고 복구 후 reporting·사람 결정 효과가 정확히 한 세트인가 |
| `E03_AFTER_V2` | E-03 | DB commit 후 SQS ack 전 | 재전달이 handler를 다시 실행하지 않고 duplicate-ack로 끝나는가 |

H-03과 E-03은 일부 증적을 공유해도 독립 verdict다. BEFORE PASS가 AFTER 미실행을 대신하지 않으며,
AI 점수는 어떤 profile에서도 자동 합격·탈락 조건이나 verdict 입력으로 사용하지 않는다.

## 실행 흐름

실제 실행 전 `.env.example`의 로컬 전용 변수들을 별도 `.env` 또는 shell에 설정한다. 운영 URL,
운영 DB, 실제 지원자 자료를 사용하면 안 된다.

```powershell
controlproof preflight H-03 --target whyyou-local --json
controlproof run H-03 --target whyyou-local --label first-h03 --json
controlproof show <RUN_ID> --json
controlproof verify <RUN_ID> --json
controlproof retest <RUN_ID> --target whyyou-local --label after-fix --json
```

Spec 002는 profile을 명시한다. E-03은 profile 생략을 허용하지 않는다.

```powershell
controlproof preflight H-03 --profile H03_DLQ_V2 --target whyyou-local --json
controlproof preflight E-03 --profile E03_BEFORE_V2 --target whyyou-local --json
controlproof preflight E-03 --profile E03_AFTER_V2 --target whyyou-local --json

controlproof run H-03 --profile H03_DLQ_V2 --target whyyou-local --label h03-local --json
controlproof run E-03 --profile E03_BEFORE_V2 --target whyyou-local --label e03-before-local --json
controlproof run E-03 --profile E03_AFTER_V2 --target whyyou-local --label e03-after-local --json
```

- preflight가 `READY`가 아니면 Run은 만들어지지 않는다.
- target의 보호조치가 실제로 실패한 정상 시험 결과는 exit 3이다. 이는 ControlProof 구현 실패가 아니다.
- 실행 중 오류나 중단 뒤에도 restore를 먼저 수행한다.
- `RESTORE_FAILED`이면 같은 target/subject의 다음 Run이 막힌다. marker 부재와 target 안전을
  확인한 evidence 파일로만 `cleanup-confirm`할 수 있으며 force 해제는 없다.
- `verify`는 원본을 고치지 않고 hash, manifest, artifact envelope, scenario/target 연결을 검사한다.
- `retest`는 부모 bundle을 수정하지 않고 새 Run과 `retest-diff.json`을 만든다. 부모가 이미
  PASS라면 데모를 위해 결함 버전을 만들 필요가 없다.

최초 actual Run의 FAIL은 시험기 실패로 덮어쓰지 않는다. 먼저 bundle을 봉인하고 `verify`한 뒤,
그 증적으로 확인된 제품 또는 판정 경계만 수정한다. 수정 후 결과는 반드시 새 child Run으로 만들고
부모 FAIL의 manifest digest와 모든 파일을 그대로 보존한다. Spec 002의 실제 H-03/E-03 계보와
manifest SHA-256은 [검증 기록](./specs/002-h03-e03-fault-expansion/validation.md)에 있다.

## 결과를 읽는 법과 주장 범위

- `PASS`: 그 Run에서 실행한 profile의 모든 필수 assertion, 증적 무결성과 환경 복구가 확인됐다.
- `FAIL`: 관찰 가능한 보호조치 위반·누락·중복이 직접 확인됐다. ControlProof 실행기 자체 실패와 다르다.
- `INCONCLUSIVE`: 접근 제한, 증적 부족·충돌 또는 복구 불확실성 때문에 제품 PASS/FAIL을 주장할 수 없다.
- `NOT_RUN`: 실행하지 않은 환경 또는 범위다. 실제 AWS는 현재 항상 `NOT_RUN`이다.

모든 결과의 정확한 주장 범위는 `EXECUTED_SCENARIO_AND_EVIDENCE_ONLY`다. ControlProof는 실행한
시나리오와 수집·검증한 증적만 보고하며, **서비스 전체의 법적 준수를 인증하거나 보증하지 않는다.**

공식 target은 `whyyou-local`, 환경은 `LOCAL_EMULATED`다. LocalStack의 SQS/DLQ PASS는 로컬 메시징
계약에만 적용된다. 실제 AWS SQS·ECS·IAM·CloudWatch·운영 네트워크를 검증한 결과가 아니며,
향후 staging/AWS를 검증하려면 별도 target ID와 새 Run을 만들어야 한다. 로컬 verdict나 bundle을
클라우드 결과로 복사·승격하지 않는다.

처음 합류한 팀원은 먼저 [팀 통합 인수인계](./docs/TEAM_HANDOFF.md)를 읽고, Spec 002는
[Spec 002 quickstart](./specs/002-h03-e03-fault-expansion/quickstart.md)를 따른다. Spec 001의 상세
실제 스택 재현 절차는 [Spec 001 quickstart](./specs/001-execution-evidence-h03/quickstart.md),
CLI 결과 검토 정책과 웹 UX 이관 결정은
[review policy](./specs/001-execution-evidence-h03/review-usability-checklist.md)를 따른다.

## 구현 구조

- `engine/`: 실행·관찰·판정·증적·재시험 엔진
- `scenarios/`: 버전 고정 H-03 시나리오와 템플릿
- `seeds/`: 합성 상태 seed 구현
- `tests/`: 단위·계약·통합·보안 회귀 테스트
- `specs/`: 기능별 Spec·Plan·Tasks·검증 기록
- `.specify/`: Spec Kit 설정·스크립트·템플릿·Constitution
- `.agents/skills/`: Codex용 Spec Kit skills

- `engine/runner.py`: profile dispatch와 Spec 001 호환 실행
- `engine/executors/`: H-03 DLQ, E-03 BEFORE/AFTER 실행과 봉인 orchestration
- `engine/evidence.py`: redaction, 원자 저장, manifest 봉인, 읽기 전용 검증
- `engine/judges/`: H03-A7~A9와 E03-A1~A8 증적 기반 판정
- `engine/judge.py`: Spec 001 H03-A1~A6와 공통 verdict 우선순위
- `engine/presentation.py`: 비개발자 검토용 요약
- `engine/retest.py`: 부모 불변 재시험 계보와 diff
- `engine/adapters/whyyou/`: WhyYou HTTP/DB/브라우저/fault/capability 경계
- `scenarios/H-03.yaml`: Spec 001 버전 고정 시나리오
- `scenarios/H-03-DLQ.yaml`, `E-03-BEFORE.yaml`, `E-03-AFTER.yaml`: Spec 002 profile snapshot
- `tests/`: 단위, 계약, 통합 및 합성 bundle case
