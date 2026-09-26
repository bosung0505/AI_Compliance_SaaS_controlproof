# ControlProof

ControlProof는 합성 데이터를 이용해 AI 서비스의 절차적 보호조치가 정상·우회·예외·장애 조건에서 실제로 작동하는지 시험하고, 판정과 재현 가능한 증적을 남기는 도구다. 첫 번째 검증 대상은 AI 면접 서비스 WhyYou다.

## 현재 개발 기준

- 제품 범위: [ControlProof × WhyYou 2주 MVP 기능 범위 V4](./docs/product/ControlProof_WhyYou_2주_MVP_기능범위_v4.md)
- 제품 정의: [MVP Product Brief](./docs/product/ControlProof_MVP_Product_Brief.md)
- 제품 결정: [MVP Decision Log](./docs/product/ControlProof_MVP_Decision_Log.md)
- 개발 원칙: [ControlProof Constitution](./.specify/memory/constitution.md)
- 현재 기능: [Spec 001 — 실행·증적 기본 모델과 H-03 최소 수직 흐름](./specs/001-execution-evidence-h03/spec.md)
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
$speckit-clarify
$speckit-plan
$speckit-tasks
$speckit-analyze
$speckit-implement
$speckit-converge
```

현재 Spec 001은 clarify, plan, tasks, analyze를 거쳐 구현 단계에 들어갔다. fake adapter 기반
H-03 수직 흐름, 봉인 증적, 검토, 무결성 확인, 재시험 계보, readiness CLI까지 구현되어 있다.

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

## H-03 실행 흐름

실제 실행 전 `.env.example`의 로컬 전용 변수들을 별도 `.env` 또는 shell에 설정한다. 운영 URL,
운영 DB, 실제 지원자 자료를 사용하면 안 된다.

```powershell
controlproof preflight H-03 --target whyyou-local --json
controlproof run H-03 --target whyyou-local --label first-h03 --json
controlproof show <RUN_ID> --json
controlproof verify <RUN_ID> --json
controlproof retest <RUN_ID> --target whyyou-local --label after-fix --json
```

- preflight가 `READY`가 아니면 Run은 만들어지지 않는다.
- target의 보호조치가 실제로 실패한 정상 시험 결과는 exit 3이다. 이는 ControlProof 구현 실패가 아니다.
- 실행 중 오류나 중단 뒤에도 restore를 먼저 수행한다.
- `RESTORE_FAILED`이면 같은 target/subject의 다음 Run이 막힌다. marker 부재와 target 안전을
  확인한 evidence 파일로만 `cleanup-confirm`할 수 있으며 force 해제는 없다.
- `verify`는 원본을 고치지 않고 hash, manifest, artifact envelope, scenario/target 연결을 검사한다.
- `retest`는 부모 bundle을 수정하지 않고 새 Run과 `retest-diff.json`을 만든다. 부모가 이미
  PASS라면 데모를 위해 결함 버전을 만들 필요가 없다.

상세 재현 절차는 [quickstart](./specs/001-execution-evidence-h03/quickstart.md), 검토 기준은
[review usability checklist](./specs/001-execution-evidence-h03/review-usability-checklist.md)를 따른다.

## 구현 구조

- `engine/`: 실행·관찰·판정 모델의 초기 spike
- `scenarios/`: H-03 초기 시나리오와 템플릿
- `seeds/`: 합성 상태 seed 초기 구현
- `tests/`: 초기 판정·seed 테스트
- `specs/`: 기능별 제품 Spec, 향후 Plan과 Tasks
- `.specify/`: Spec Kit 설정·스크립트·템플릿·Constitution
- `.agents/skills/`: Codex용 Spec Kit skills

- `engine/runner.py`: H-03 순서와 의무 restore
- `engine/evidence.py`: redaction, 원자 저장, manifest 봉인, 읽기 전용 검증
- `engine/judge.py`: H03-A1~A6와 verdict 우선순위
- `engine/presentation.py`: 비개발자 검토용 요약
- `engine/retest.py`: 부모 불변 재시험 계보와 diff
- `engine/adapters/whyyou/`: WhyYou HTTP/DB/브라우저/fault/capability 경계
- `scenarios/H-03.yaml`: 버전 고정 시나리오 정의
- `tests/`: 단위, 계약, 통합 및 합성 bundle case
