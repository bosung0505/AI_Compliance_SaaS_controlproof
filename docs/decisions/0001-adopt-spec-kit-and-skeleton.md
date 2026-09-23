# ADR-0001. Spec Kit과 팀 골격을 ControlProof 개발 기준으로 채택

- 상태: Accepted
- 결정일: 2026-09-24
- 대상 저장소: `bosung0505/AI_Compliance_SaaS_controlproof`

## 배경

2주 MVP는 제품 범위 문서만으로 바로 구현하면 시나리오 의미, 증적 모델과 실제 WhyYou 연결 방식이 동시에 바뀔 위험이 있다. 팀원이 만든 `controlproof-skeleton_1`에는 scenario-as-data, 판정 엔진, 상태 seed와 테스트의 유용한 출발점이 있지만 현재 스키마와 H-03 정의를 제품 계약으로 확정하기에는 다음 문제가 있다.

- 실행기 미준비와 대상 기능 부재가 섞일 수 있다.
- Observation이 시험 대상·구간·단계·재시도를 구분하지 못한다.
- 시간에 따른 정상 상태 변화가 증적 충돌로 오인될 수 있다.
- 문서와 코드의 판정 불가 reason code가 다르다.
- H-03이 최소 수직 흐름과 DLQ·멱등성 확장을 한 번에 포함한다.

## 결정

1. GitHub 저장소 `bosung0505/AI_Compliance_SaaS_controlproof`를 ControlProof MVP의 실제 개발 저장소로 사용한다.
2. 팀 골격의 `engine`, `scenarios`, `seeds`, `tests`와 프로젝트 설정은 구현 spike로 가져온다.
3. 초기 골격 문서는 `docs/reference/skeleton/`에 원문으로 보존한다. 루트 제품 계약으로 사용하지 않는다.
4. V4, Product Brief와 Decision Log는 `docs/product/`의 기준 문서로 사용한다.
5. GitHub Spec Kit 1.0.10을 Codex skills, PowerShell scripts와 Git workflow extension 구성으로 초기화한다.
6. 확정된 Constitution은 `.specify/memory/constitution.md`, 기능 Spec은 `specs/`에서 관리한다.
7. 기능 단위로 `clarify → plan → tasks → analyze → implement → converge`를 진행한다.
8. 첫 기능 단위는 `001-execution-evidence-h03`이며, Spec 001의 Plan이 승인되기 전에는 골격의 데이터 계약을 확정하지 않는다.

## 이유

- 이미 작성한 제품 결정을 버리지 않고 공식 Spec Kit 흐름에 연결할 수 있다.
- 팀 골격의 재사용 가능한 코드를 보존하면서 잘못된 계약이 확산되는 것을 막는다.
- H-03 최소 흐름을 먼저 완주해 Run·Observation·Evidence·Verdict 구조를 실제 연결 위에서 검증할 수 있다.
- Git extension을 통해 각 Spec 단계의 변경을 독립적으로 검토하고 되돌릴 수 있다.

## 결과와 영향

- 루트 `README.md`, `docs/product/`, Constitution과 `specs/`가 현재 개발 기준이다.
- `docs/reference/skeleton/`과 기존 `scenarios/H-03.yaml`은 참고 및 마이그레이션 대상이다.
- 다음 작업은 Spec 001의 clarification이며, 그 다음에 기술 Plan을 작성한다.
- Spec 002는 Spec 001의 기반 계약과 최소 수직 흐름을 검증한 뒤 진행한다.
- Python 프로젝트가 요구하는 3.12 이상 환경은 `uv`로 관리한다.
- 초기 골격은 Python 패키지 탐색 범위를 명시하지 않아 `specs`와 `scenarios`까지 패키지로 오인했다. 프로젝트 동작은 바꾸지 않고 배포 패키지를 `engine`과 `seeds`로 제한한다.
- `.specify/`와 `.agents/`는 Spec Kit이 관리하는 도구 코드이므로 프로젝트 Ruff 검사에서 제외하고, ControlProof 애플리케이션 코드와 테스트만 팀의 정적 검사 대상으로 둔다.

## 검토한 대안

### 골격을 폐기하고 새로 작성

판정 엔진과 테스트 자산을 잃고 2주 범위에서 불필요한 재작성 비용이 발생하므로 채택하지 않았다.

### 모든 Spec을 먼저 작성한 뒤 일괄 구현

Spec 002 이후가 Spec 001의 실행·증적 계약에 의존하므로 초기 가정이 바뀔 때 문서 전체를 다시 수정할 가능성이 크다. 기능별 수직 흐름을 반복하는 방식을 선택했다.

### 문서 폴더에서 계속 수동으로 Spec Kit 형식을 모방

실제 templates, scripts, Codex skills와 Git hooks가 없어 팀이 같은 절차를 재현할 수 없으므로 채택하지 않았다.
