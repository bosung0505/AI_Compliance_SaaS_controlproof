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

현재 Spec 001은 작성과 품질 검토가 끝났으므로 다음 단계는 `$speckit-clarify`다. 모호성이 없음을 확인한 뒤 `$speckit-plan`으로 이동한다.

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

## 현재 골격

- `engine/`: 실행·관찰·판정 모델의 초기 spike
- `scenarios/`: H-03 초기 시나리오와 템플릿
- `seeds/`: 합성 상태 seed 초기 구현
- `tests/`: 초기 판정·seed 테스트
- `specs/`: 기능별 제품 Spec, 향후 Plan과 Tasks
- `.specify/`: Spec Kit 설정·스크립트·템플릿·Constitution
- `.agents/skills/`: Codex용 Spec Kit skills

현재 골격의 데이터 계약은 확정본이 아니다. Spec 001의 Plan에서 readiness 분리, Observation 식별 차원, 증적 무결성, Run 생명주기와 reason code를 반영한 뒤 구현한다.
