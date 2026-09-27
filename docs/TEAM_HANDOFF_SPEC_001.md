# 팀 인수인계: Spec 001 현황·재현·검토 가이드

## 1. 이 문서를 먼저 읽는 이유

이 저장소를 처음 받은 팀원이 “전체 MVP가 완성됐는가?”, “무엇을 실제로 시험했는가?”,
“어떤 명령부터 실행해야 하는가?”를 혼동하지 않도록 현재 상태와 재현 절차를 한곳에 정리한다.

핵심 결론은 다음과 같다.

- **완료**: Spec 001 문서와 H-03 최소 수직 흐름의 CLI 구현·자동 시험·실제 WhyYou 검증
- **미완료**: 전체 2주 MVP, ControlProof 웹 UI, N/E 계열 및 H-03 확장형, 배포형 SaaS
- **현재 사용자 접점**: 웹 화면이 아니라 개발·검증용 `controlproof` CLI
- **공식 상태**: Spec 001 `Complete`
- **사람 사용성 시험**: CLI에서 하지 않고 향후 고객용 웹 결과 화면에서 수행

따라서 “Spec 001 완료”를 “ControlProof 제품 전체 완료”로 해석하면 안 된다.

## 2. Spec 001에서 만든 것

Spec 001은 WhyYou reporting 장애 상황 하나를 사용해 ControlProof의 공통 실행 뼈대를 검증한다.

1. 실행 전 capability와 대상 버전 확인
2. 합성 지원자와 pending-report 상태 생성
3. test-only reporting 장애 주입
4. worker trigger receipt로 장애 발동 확인
5. API·DB·회사 화면 관찰
6. 리포트 없이 최종 채용 결정 시도
7. 결정 거부, 부분 변경 부재와 자동 결정 부재 확인
8. 장애 제거와 환경 복구
9. H03-A1~A6 판정
10. EV-01~EV-09 증적 연결·redaction·SHA-256·manifest 봉인
11. bundle 변조 검증
12. 부모를 수정하지 않는 child 재시험과 target diff

주요 구현은 다음 위치에 있다.

- `engine/runner.py`: H-03 실행 순서와 의무 복구
- `engine/judge.py`: H03-A1~A6와 전체 verdict
- `engine/evidence.py`: redaction, 원자 저장, manifest와 무결성 검증
- `engine/presentation.py`: `show` projection
- `engine/retest.py`: 부모 불변 child 재시험
- `engine/adapters/whyyou/`: WhyYou API·DB·브라우저·fault·capability 연결
- `scenarios/H-03.yaml`: 버전 고정 시나리오
- `tests/`: 단위·계약·통합·보안 회귀 시험

## 3. 아직 만들지 않은 것

- ControlProof 웹 대시보드와 결과 화면
- 조직·사용자·권한·결제·운영 배포 기능
- 전체 N-01~N-03, H-01~H-03, E-01~E-03 실행기
- H-03의 retry exhaustion·DLQ 검증
- E-03의 Outbox·결정 이력 멱등성 검증
- 실제 고객을 대상으로 한 결과 화면 사용성 검토

DLQ·일반 stage-move 우회·복구 후 idempotency는 Spec 001의 PASS 범위가 아니며 후속 Spec에서
다뤄야 한다.

## 4. 실제 검증에서 일어난 일

첫 실제 WhyYou Run은 제품 보호조치 문제를 찾아 `FAIL`을 냈다.

- parent Run: `f738081a-5fb3-4f21-af22-685a12355096`
- WhyYou commit: `573ce0c2146b8e7e1280e430ad4445f8a373f36e`
- 결과: H03-A2·A3 FAIL
- 원본 bundle digest: `b5357cdfbe6ebf259d69477c381a538a066d6b98ed34a67427cc567a1cdbd70d`

WhyYou 전용 브랜치에서 다음을 수정했다.

- 리포트가 없으면 최종 결정 API가 쓰기 전에 `409 REPORT_NOT_AVAILABLE` 반환
- 리포트 장기 지연·조회 실패가 회사 화면에 준비 완료처럼 보이지 않도록 표시
- 거부된 결정 시도로 채용 상태와 결정 이력을 변경하지 않음

수정 후 첫 FAIL을 부모로 새 child Run을 실행했다.

- child Run: `e42482c9-ba84-42c6-984d-209e0f80b7d8`
- WhyYou commit: `aa0ae2b4735d0cd1f2bfb6fe2f07077b3aa4f659`
- 결과: H03-A1~A6 모두 PASS
- child bundle digest: `213f11a4f37dfb4108443d4dd122e6c75b4f96578efe671d074a8b38053baec0`
- parent bundle: 재시험 후에도 `VERIFIED`, digest 불변

상세 기록과 비채택 실행은 `specs/001-execution-evidence-h03/validation.md`에 있다.

## 5. 저장소와 브랜치

### ControlProof

- 원격: `https://github.com/bosung0505/AI_Compliance_SaaS_controlproof.git`
- 작업 브랜치: `001-execution-evidence-h03`
- `main`이 아니라 이 브랜치를 받아야 Spec 001 최신 상태를 볼 수 있다.

```powershell
git clone https://github.com/bosung0505/AI_Compliance_SaaS_controlproof.git
cd AI_Compliance_SaaS_controlproof
git switch 001-execution-evidence-h03
git pull --ff-only origin 001-execution-evidence-h03
git status --short --branch
git rev-list --left-right --count HEAD...origin/001-execution-evidence-h03
```

마지막 명령이 `0  0`이면 로컬과 원격 브랜치가 일치한다. `git status`에는 수정 파일이 없어야 한다.

### WhyYou

- 원격: `https://github.com/jhkim0602/gbsa_aws.git`
- 작업 브랜치: `bosung/controlproof-h03-integration`
- 검증 커밋: `aa0ae2b4735d0cd1f2bfb6fe2f07077b3aa4f659`
- WhyYou `main`에는 이 작업을 push하지 않았다.

```powershell
git clone https://github.com/jhkim0602/gbsa_aws.git
cd gbsa_aws
git switch bosung/controlproof-h03-integration
git pull --ff-only origin bosung/controlproof-h03-integration
git rev-parse HEAD
```

마지막 출력이 위 검증 커밋과 같아야 이 문서에 기록된 실제 PASS 대상과 일치한다.

## 6. 단계 A: ControlProof만 빠르게 검증

이 단계는 Docker와 WhyYou 실행 없이 가능하다. fake adapter를 사용하지만 실행·판정·증적·복구·
재시험 계약 전체를 검증한다.

```powershell
cd <ControlProof 저장소 경로>
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
& .\.venv\Scripts\python.exe -m ruff check .
& .\.venv\Scripts\python.exe -m ruff format --check .
& .\.venv\Scripts\python.exe -m pytest -q
```

현재 기준 기대 결과는 다음과 같다.

- Ruff check PASS
- Ruff format PASS
- pytest `134 passed`

개별 핵심 시험만 보려면 다음을 실행한다.

```powershell
& .\.venv\Scripts\python.exe -m pytest -q `
  tests/integration/test_h03_orchestration.py `
  tests/integration/test_h03_bundle_links.py `
  tests/integration/test_h03_retest_lineage.py `
  tests/contract/test_cli_review.py
```

## 7. 단계 B: 합성 결과를 직접 조회

실제 지원자나 WhyYou 서버 없이 PASS·FAIL·INCONCLUSIVE bundle을 새로 만들 수 있다.
출력 디렉터리는 비어 있는 새 경로를 사용한다.

```powershell
& .\.venv\Scripts\python.exe -m scripts.prepare_sc008_review `
  --output .controlproof/team-demo-01
```

생성된 `reviewer-runs.json`의 Run ID 하나를 사용한다.

```powershell
& .\.venv\Scripts\python.exe -m engine.cli show <RUN_ID> `
  --run-root .controlproof/team-demo-01/runs --json

& .\.venv\Scripts\python.exe -m engine.cli verify <RUN_ID> `
  --run-root .controlproof/team-demo-01/runs --json
```

확인할 사항:

- `verdict`, `summary`, `failed_assertions`, `inconclusive_assertions`
- assertion별 `expected`, `actual`, `evidence.path`, `evidence.sha256`
- `environment_restore_status`, `report_processing_recovery`
- `unverified_scope`, `implementation_status`
- verify 결과가 `VERIFIED`

이 package는 개발 데모이며 사람 시간 측정 release gate가 아니다.

## 8. 단계 C: WhyYou 변경 자체를 검증

WhyYou 저장소에서 먼저 의존성을 설치한다. 기본 절차는 WhyYou의
`docs/local-development.md`를 따른다.

```powershell
cd <WhyYou 저장소 경로>
npm ci
uv sync --frozen
```

ControlProof 관련 backend 회귀 시험:

```powershell
uv run pytest -q `
  backend/tests/unit/runtime/test_controlproof_reporting_fault.py `
  backend/tests/unit/runtime/test_controlproof_model_substitute.py `
  backend/tests/integration/test_controlproof_fault_hook_safety.py `
  backend/tests/integration/reporting/test_recruiting_stage_decision.py
```

회사 콘솔 시험과 typecheck:

```powershell
npm test --workspace @iep/company-console -- --run
npm run typecheck --workspace @iep/company-console
```

현재 기준 기대 결과:

- ControlProof 관련 backend: 25 tests PASS
- company-console: 142 tests PASS
- company-console typecheck PASS

`uv`가 이 Windows 환경에서 동작하지 않으면 WhyYou의 `docs/local-development.md`에 기록된
`.venv` 우회 절차를 사용한다. 기존 WhyYou 전체 시험에는 이 작업과 무관한 선행 harness 제거
문제가 문서화돼 있으므로, 대상 시험과 전체 저장소 문제를 구분한다.

## 9. 단계 D: 실제 WhyYou 로컬 스택 H-03 재실행

이 단계에는 Docker Desktop, 두 저장소, Playwright Chromium, 로컬 전용 회사 계정과 DB 접속값이
필요하다. 실제 지원자와 운영 환경은 사용하지 않는다.

WhyYou의 `.env.example`을 바탕으로 로컬 `.env`를 만들고 다음 test-only 값을 명시적으로 켠다.

```text
CONTROLPROOF_TEST_HOOKS_ENABLED=true
CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED=true
CONTROLPROOF_MODEL_FIXTURE_ID=h03-report-v1
CONTROLPROOF_FAULT_ROOT=<두 프로세스가 공유하는 로컬 경로>
```

WhyYou에서 터미널을 나눠 실행한다.

```powershell
.\scripts\local.ps1 up
.\scripts\local.ps1 api
.\scripts\local.ps1 worker
.\scripts\local.ps1 company
```

ControlProof 터미널에는 `.env.example`과
`specs/001-execution-evidence-h03/quickstart.md`의 변수를 로컬 값으로 설정한다. 그 후:

```powershell
python -m engine.cli preflight H-03 --target whyyou-local --json
python -m engine.cli run H-03 --target whyyou-local --label team-review --json
python -m engine.cli show <새 RUN_ID> --json
python -m engine.cli verify <새 RUN_ID> --json
```

preflight가 `READY`가 아니면 실제 Run을 강행하지 않는다. 끝난 뒤 WhyYou에서 다음으로 정리한다.

```powershell
.\scripts\local.ps1 down
```

## 10. pull만으로 동일한 결과를 볼 수 있는가

구분해서 이해해야 한다.

- **자동 시험 재현**: 가능하다. 코드·시나리오·fixtures·테스트가 Git에 있다.
- **합성 PASS/FAIL/INCONCLUSIVE 생성**: 가능하다. 단계 B 명령으로 새 bundle을 만든다.
- **실제 WhyYou H-03 재실행**: 두 저장소와 로컬 자격 증명·Docker가 있으면 가능하다.
- **과거 Run ID를 그대로 `show`**: 불가능하다. `.controlproof/` runtime bundle은 크기·민감정보·
  환경 종속성을 이유로 Git에서 제외한다.
- **과거 결과 검토**: `validation.md`의 Run ID, target commit, bundle digest, assertion 결과와
  원본 불변 검증 기록으로 가능하다.

새로 실행하면 Run UUID, 수집 시각, 합성 subject ID와 artifact hash는 달라질 수 있다. 중요한 것은
같은 시나리오·target commit·fixture에서 assertion 의미와 verdict가 재현되는지다.

## 11. 팀 코드·설계 검토 포인트

팀원은 단순히 테스트가 초록색인지뿐 아니라 다음을 검토한다.

1. H03-A1~A6가 “AI 점수로 자동 합격·탈락”을 전제하지 않고 인간 최종결정 구조를 지키는가?
2. 장애 명령 성공이 아니라 worker receipt로 실제 장애 발동을 증명하는가?
3. API·화면·DB 관찰을 구분하고 서로 충돌하면 숨기지 않는가?
4. 최종 결정 거부 뒤 부분 상태 변경과 자동 결정 부재를 별도로 확인하는가?
5. 복구 실패가 PASS/FAIL로 잘못 표시되지 않고 `INCONCLUSIVE`와 후속 실행 차단으로 이어지는가?
6. EV-01~EV-09가 assertion에 연결되고 redaction·SHA-256·manifest 검증을 거치는가?
7. 첫 FAIL을 덮어쓰지 않고 수정 후 child Run으로 PASS를 연결하는가?
8. DLQ·일반 우회·멱등성처럼 아직 검증하지 않은 범위가 명시되는가?
9. test hook과 고정 모델 대역이 운영에서 활성화되지 못하도록 방어하는가?
10. WhyYou `main`이 아니라 전용 브랜치에서 변경됐는가?

의견은 `spec.md`의 요구사항 ID, `tasks.md`의 Task ID 또는 H03-A/EV ID에 연결해 남기면
다른 팀원이 같은 의미로 이해하기 쉽다.

## 12. 문서 읽기 순서

처음에는 다음 순서만 읽으면 된다.

1. 이 문서
2. `README.md`
3. `specs/001-execution-evidence-h03/spec.md`
4. `specs/001-execution-evidence-h03/validation.md`
5. `specs/001-execution-evidence-h03/traceability.md`
6. 실제 재현이 필요할 때 `specs/001-execution-evidence-h03/quickstart.md`
7. 구현 세부를 볼 때 `plan.md`, `data-model.md`, `contracts/`, `tasks.md`

전체 2주 MVP의 범위는 `docs/product/ControlProof_WhyYou_2주_MVP_기능범위_v4.md`, 제품의 결정과
용어는 `docs/product/ControlProof_MVP_Product_Brief.md`와
`docs/product/ControlProof_MVP_Decision_Log.md`를 기준으로 한다.
