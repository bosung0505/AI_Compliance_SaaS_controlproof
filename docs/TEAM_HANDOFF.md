# ControlProof 팀 통합 인수인계

## 1. 이 문서의 역할

이 문서는 새 팀원이 저장소의 **현재 공식 상태**, 완료된 작업, 검증 범위, 재현 방법과 다음 결정 지점을
한곳에서 이해하기 위한 단일 진입점이다. 과거의 `TEAM_HANDOFF_SPEC_001.md`를 대체하며, 프로젝트 상태를
확인할 때는 이 문서를 먼저 읽는다.

- 상태 기준일: 2026-09-30
- ControlProof 현재 작업 브랜치: `002-h03-e03-fault-expansion`
- 이 문서가 설명하는 최종 완료 범위: Spec 001과 Spec 002
- 현재 사용자 접점: 고객용 웹 화면이 아니라 개발·검증용 `controlproof` CLI

이 문서는 상세 요구사항, 기술 계약 또는 실행 원본을 복제하지 않는다. 각 사실의 상세 근거는 아래에
연결한 Spec, Validation, Traceability와 Decision 문서가 보존한다.

## 2. 현재 공식 상태

| 구분 | 공식 상태 | 정확한 의미 |
|---|---|---|
| 제품 범위 V4 | 기준선 유지 | 2주 MVP 전체의 목표와 제외 범위를 정의한다. 구현 완료표가 아니다. |
| Constitution | Complete | 모든 기능 Spec과 구현이 따라야 할 개발·검증 원칙이 확정됐다. |
| Spec 001 | Complete | 실행·증적 기본 모델과 H-03 최소 수직 흐름을 구현하고 실제 WhyYou 로컬 스택에서 검증했다. |
| Spec 002 | Complete | H-03 DLQ 확장과 E-03 저장 전/후 장애·재시도·멱등성을 구현하고 `LOCAL_EMULATED`에서 검증했다. |
| Spec 003 | 계획 확정·미착수 | 다음 작업. N-02 동의·AI 처리 순서 수직 흐름을 명세부터 실제 검증까지 진행한다. |
| Spec 004 | 계획 확정·미착수 | E-01·E-02 점수 근거·평가 기준 보존을 구현·검증한다. |
| Spec 005 | 계획 확정·미착수 | 웹 워크벤치·12개 시나리오 카탈로그·보고서와 웹 UX 검토를 구현·검증한다. |
| 실제 AWS | `NOT_RUN` | AWS SQS·ECS·IAM·CloudWatch·운영 네트워크는 검증하지 않았다. |
| ControlProof 웹 워크벤치 | 미구현 | 현재 결과 확인과 재현은 CLI·JSON·봉인 bundle을 사용한다. |
| 2주 MVP 전체 | 미완료 | Spec 001·002 완료를 전체 제품 또는 전체 시나리오 완료로 확대하면 안 된다. |
| 웹 결과 사용성 검토 | 미실시 | CLI 사람 시간 측정은 완료 gate에서 제외했고, 고객용 웹 결과 화면을 만든 뒤 별도 검토한다. |

따라서 저장소의 공식 상태는 **“Spec 001 Complete”에서 멈춘 것이 아니라 “Spec 001과 Spec 002가
각각 Complete”**다. 단, `Complete`는 해당 Spec의 명시된 범위에만 적용된다.

## 3. 절대로 바꾸어 해석하면 안 되는 제품 원칙

1. AI 점수는 참고 정보다. 점수 임계값이 자동 합격·탈락을 결정하지 않는다.
2. 최종 채용 결정은 권한 있는 사람이 검토하고 확정한다. 더 낮은 점수의 지원자가 채용될 수 있다.
3. ControlProof의 PASS는 실행한 시나리오와 수집·검증한 증적에만 적용된다.
4. PASS는 서비스 전체의 법적 준수 인증이나 보증이 아니다.
5. 최초 FAIL은 실패한 개발 결과가 아니라 발견된 제품 사실일 수 있다. 원본을 봉인하고 수정 후 새
   child Run으로 재시험한다.
6. `LOCAL_EMULATED` 결과를 AWS 결과로 복사하거나 승격하지 않는다.
7. 실제 지원자·운영 데이터·운영 credential을 시험에 사용하지 않는다.

공식 결과의 주장 범위 문자열은 `EXECUTED_SCENARIO_AND_EVIDENCE_ONLY`다.

## 4. Spec 001에서 완료한 것

Spec 001은 WhyYou reporting 장애 한 종류를 사용해 ControlProof의 공통 실행 뼈대를 검증했다.

1. 실행 전 capability와 대상 버전 확인
2. 합성 지원자와 pending-report 상태 생성
3. test-only reporting 장애 주입
4. worker trigger receipt를 통한 실제 장애 발동 확인
5. API·DB·회사 화면 관찰
6. 리포트 없이 최종 채용 결정 시도
7. 결정 거부, 부분 변경 부재와 자동 결정 부재 확인
8. 장애 제거와 환경 복구
9. H03-A1~A6 판정
10. EV-01~EV-09 증적 연결·redaction·SHA-256·manifest 봉인
11. bundle 변조 검증
12. 부모를 수정하지 않는 child 재시험과 target diff

주요 구현은 `engine/runner.py`, `engine/judge.py`, `engine/evidence.py`,
`engine/presentation.py`, `engine/retest.py`, `engine/adapters/whyyou/`,
`scenarios/H-03.yaml`과 관련 시험에 있다.

### Spec 001 실제 FAIL → PASS 계보

| 구분 | Run ID | 결과 | 대상 WhyYou commit | bundle/manifest digest |
|---|---|---|---|---|
| 최초 부모 | `f738081a-5fb3-4f21-af22-685a12355096` | H03-A2·A3 FAIL | `573ce0c2146b8e7e1280e430ad4445f8a373f36e` | `b5357cdfbe6ebf259d69477c381a538a066d6b98ed34a67427cc567a1cdbd70d` |
| 최종 child | `e42482c9-ba84-42c6-984d-209e0f80b7d8` | H03-A1~A6 PASS | `aa0ae2b4735d0cd1f2bfb6fe2f07077b3aa4f659` | `213f11a4f37dfb4108443d4dd122e6c75b4f96578efe671d074a8b38053baec0` |

첫 실행은 리포트 실패가 화면에서 준비 완료처럼 보일 수 있고, 결정 거부 사유가 불명확한 문제를
찾았다. WhyYou 전용 브랜치에서 리포트 부재 시 쓰기 전 `409 REPORT_NOT_AVAILABLE`을 반환하고,
장기 지연·조회 실패를 화면에 구분해 표시하도록 보완했다. child 실행 뒤에도 부모 bundle은
`VERIFIED`였고 digest가 변하지 않았다.

상세 근거와 비채택 실행은 [Spec 001 검증 기록](../specs/001-execution-evidence-h03/validation.md)에 있다.

## 5. Spec 002에서 완료한 것

Spec 002는 Spec 001의 기본 계약을 유지하면서 다음 세 profile을 실제 로컬 스택까지 확장했다.

| Profile | 검증 경계 | 핵심 질문 |
|---|---|---|
| `H03_DLQ_V2` | reporting 재시도 소진·DLQ·결정 우회 | 최종 실패가 숨지 않고 세 최종결정 경로가 모두 차단되는가 |
| `E03_BEFORE_V2` | 결과 내구 저장 전 장애 | 장애 중 부분 효과가 없고 복구 후 reporting·사람 결정 효과가 정확히 한 세트인가 |
| `E03_AFTER_V2` | DB commit 후 SQS ack 전 장애 | 재전달이 handler를 다시 실행하지 않고 duplicate-ack로 끝나는가 |

완료한 핵심 기능은 다음과 같다.

- LocalStack source queue·DLQ topology와 재시도 횟수를 snapshot하고 fail-closed preflight 수행
- 장애 marker·worker receipt·delivery attempt·terminal failure·redrive 계보 수집
- 단일 최종결정과 batch `최종합격`·`불합격` 세 경로의 report-ready 보호 확인
- Outbox 원 사건부터 처리 시도, 최종 실패, 복구, report/projection/processed marker까지 연결
- 저장 전 장애에서 부분 효과 0건 확인
- 저장 후·ack 전 장애에서 handler 재실행 없이 동일 업무 효과 한 세트 유지 확인
- 같은 `Idempotency-Key`·같은 본문을 재전송해 사람 최종결정 효과가 정확히 한 세트인지 확인
- H-03과 E-03을 독립 assertion·독립 verdict로 판정
- Spec 002 bundle의 typed reference, cross-Run origin, redaction, SHA-256와 manifest 검증
- `RESTORE_FAILED` 차단과 증적 기반 `cleanup-confirm`
- 부모를 수정하지 않는 FAIL → PASS child/grandchild 재시험

### 최초 FAIL이 찾아낸 실제 문제와 보완

| 근거 | 발견 | 보완 |
|---|---|---|
| H03-A7 | 단일 결정은 막혔지만 batch `최종합격`·`불합격` 경로가 report 부재를 우회 | batch 최종 단계도 report-ready 보호 적용 |
| H03-A9 | DLQ는 존재하지만 제품 API와 화면은 계속 `queued` | `report_generation_failures` terminal projection과 API/UI `failed` 상태 추가 |
| E03-A7 | 동일 key 재전송이 동등 성공으로 재생되지 않고 중복 위험 | 사람 최종결정 command의 exactly-once 업무 효과와 body 충돌 거부 구현 |
| E03-A7 retest | 실제 효과는 한 세트였지만 `company_user`와 `COMPANY_USER` 표현 차이로 거짓 FAIL | actor canonicalization을 고치고 기존 child를 보존한 grandchild 재시험 |

WhyYou 보완은 `bosung/controlproof-h03-integration`의
`511ae9e2cae66b8d0ce31e8851537ed27ac6dd0c`에 있으며 WhyYou `main`에는 push하지 않았다.

### Spec 002 최종 실제 스택 결과

| Profile | Run ID | 결과 | Restore | `manifest.json` SHA-256 |
|---|---|---|---|---|
| `H03_DLQ_V2` | `ac025c2c-b941-4c4c-b737-d3d3e61deb0b` | H03-A1~A9 PASS | SUCCEEDED | `b4fc92b2ccbc033517d9c71f837633e069989bf1effa67b8c3a58498758e6c65` |
| `E03_BEFORE_V2` | `047fb27b-c50e-4e50-b43d-acc1c08623e9` | A1/A2/A3/A4/A7/A8 PASS | SUCCEEDED | `4ee03a350e7d61818b3f2159250dee772d002284f98b49417f2689625a881889` |
| `E03_AFTER_V2` | `4e3e424e-f9ab-43c0-a4d4-7a3741f8e3f0` | A1/A5/A6/A8 PASS | SUCCEEDED | `52b86fdb0d9a248035c46833d1a84703f61ba8ba6c8e52ea17ca2aad2eddc0b6` |

세 bundle은 모두 `VERIFIED`였고 missing, mismatched, unregistered file은 0건이었다. 최종 H-03 종료 후
source queue와 DLQ의 visible, in-flight, delayed 수도 모두 0이었다.

최초 FAIL 계보도 삭제하지 않았다.

- H-03 부모 FAIL `60b19e5a-6693-427b-bf87-039e45181cfc` → child PASS
  `3ff1c0c7-7937-4d0a-996c-de4d63f4f1af`
- E-03 부모 FAIL `e17e0af0-b46a-4022-93a4-a91a3247f16d` → 제품 보완 child FAIL → 판정기 보정
  grandchild PASS `ebeed35e-5779-4480-8d3b-e246a0bb72b6`

마지막 기록된 품질 gate는 ControlProof Ruff PASS·전체 `270 passed`, WhyYou 관련 Python
`72 passed`·Ruff PASS, company console 10 tests·typecheck·production build PASS다. 정확한 명령, 시간,
경고와 모든 실행 계보는 [Spec 002 검증 기록](../specs/002-h03-e03-fault-expansion/validation.md)을 기준으로 한다. Spec 002
작업 목록은 T001~T091 전부 완료됐으며 미완료 Task는 0개다.

## 6. 아직 완료하지 않은 것

다음 항목은 Spec 001·002 완료에 포함되지 않는다.

- ControlProof 고객용 웹 워크벤치와 결과 보고서 화면
- 웹 결과 화면을 대상으로 한 실제 사용자 이해도·사용성 검토
- N-01, N-02, N-03 실행기와 최종 검증
- H-01, H-02 실행기와 최종 검증
- E-01, E-02 실행기와 최종 검증
- A-01~A-03의 기능 구현: 이번 MVP에서는 WhyYou에 시험 대상이 없어 `NO_TEST_TARGET`로 보고하는 범위
- 전체 시나리오 카탈로그를 한 번에 실행하는 제품 흐름
- 조직·사용자·권한 관리, 결제, 운영 배포와 상용 SaaS 운영 기능
- 실제 AWS·production 환경 검증

후속 개발 순서는 다음과 같이 확정했다.

| 순서 | 기능 Spec | 포함 범위 | 종료 의미 |
|---|---|---|---|
| 1 | Spec 003 — N-02 동의·AI 처리 순서 | 경로 시드, 동의 전 우회 차단, 사건 순서·정책 증적, 필요한 WhyYou 연결·주입·복구 | N-02 actual Run과 bundle까지 완료 |
| 2 | Spec 004 — E-01·E-02 점수 근거·기준 보존 | 잘못된 인용, `scoring_inputs`·가중치·버전 snapshot, 기준 변경 후 과거 리포트 불변 | E-01·E-02 actual 검증까지 완료 |
| 3 | Spec 005 — 웹 워크벤치·보고서 | 12개 시나리오, 결과·증적·재시험 비교, A 계열 `NO_TEST_TARGET`, 미실행·미검증 범위, 웹 UX 검토 | V4 결과물 완료 기준 검증 |

기존의 “남은 WhyYou 연결과 시험 조건”은 독립 Spec으로 만들지 않는다. N-02에 필요한 capability는
Spec 003, E-01·E-02에 필요한 capability는 Spec 004 안에서 사용자 흐름과 함께 구현한다.

H-01·H-02·N-01·N-03의 실제 완주는 V4의 목표 상한이다. Spec 005에서 readiness와 `NOT_RUN`을
사실대로 표시하되, 실제 실행까지 요구하려면 별도 후속 Spec 또는 승인된 범위 변경이 필요하다.
결정 이유와 변경 전·후는 [Decision Log D-013](./product/ControlProof_MVP_Decision_Log.md)에 있다.

## 7. 저장소와 브랜치 안전성

| 저장소 | 사용 브랜치 | 역할 |
|---|---|---|
| `bosung0505/AI_Compliance_SaaS_controlproof` | `002-h03-e03-fault-expansion` | 실행기·판정기·증적·문서 |
| `jhkim0602/gbsa_aws` | `bosung/controlproof-h03-integration` | WhyYou 로컬 시험 hook과 증적으로 확인된 보호조치 보완 |

현재 브랜치와 원격의 일치 여부는 아래 명령으로 확인한다. Spec 002 최종 actual-stack에서 검증한
ControlProof 구현 commit은 `06f7a77`, WhyYou commit은
`511ae9e2cae66b8d0ce31e8851537ed27ac6dd0c`다. 이후 문서 commit이 추가돼도 검증 source는
Validation에 기록된 SHA로 식별한다.

WhyYou `main`에는 ControlProof 관련 변경을 직접 commit하거나 push하지 않는다. actual Run 전에는 두
checkout 모두 clean이어야 한다.

```powershell
git branch --show-current
git status --short
git rev-list --left-right --count HEAD...@{upstream}
```

마지막 명령이 `0  0`이면 해당 로컬 브랜치와 추적 원격이 일치한다.

## 8. 팀원이 읽을 문서 순서

처음에는 다음 순서로 읽는다.

1. 이 문서
2. 저장소 [README](../README.md)
3. [2주 MVP 기능 범위 V4](./product/ControlProof_WhyYou_2주_MVP_기능범위_v4.md)
4. [Spec 002](../specs/002-h03-e03-fault-expansion/spec.md)
5. [Spec 002 Validation](../specs/002-h03-e03-fault-expansion/validation.md)의 최종 closure 절
6. [Spec 002 Traceability](../specs/002-h03-e03-fault-expansion/traceability.md)
7. 재현할 때 [Spec 002 Quickstart](../specs/002-h03-e03-fault-expansion/quickstart.md)
8. 구현 세부가 필요할 때 [Plan](../specs/002-h03-e03-fault-expansion/plan.md),
   [Data Model](../specs/002-h03-e03-fault-expansion/data-model.md),
   [Contracts](../specs/002-h03-e03-fault-expansion/contracts/),
   [Tasks](../specs/002-h03-e03-fault-expansion/tasks.md),
   [Implementation Decisions](../specs/002-h03-e03-fault-expansion/implementation-decisions.md)
9. 기본 모델의 유래가 필요할 때 [Spec 001](../specs/001-execution-evidence-h03/spec.md),
   [Validation](../specs/001-execution-evidence-h03/validation.md),
   [Traceability](../specs/001-execution-evidence-h03/traceability.md)

### 문서별 역할과 삭제하면 안 되는 이유

| 문서 | 역할 | 상태 해석 |
|---|---|---|
| `TEAM_HANDOFF.md` | 현재 상태와 팀 진입점 | 항상 최신이어야 하는 단일 인수인계 |
| `README.md` | 저장소 실행·구조 요약 | 인수인계와 같은 현재 상태를 가리켜야 함 |
| V4 | 전체 MVP 범위 기준선 | 미완료 항목이 있어도 삭제하지 않음 |
| Product Brief | 사용자·제품 흐름·제품 상태 정의 | 현재 산출물 표기만 최신화하고 제품 결정은 유지 |
| Decision Log | 결정 이유와 변경 이력 | 과거 순서도 이력이므로 삭제하지 않음 |
| `specs/001-*` | 완료된 기본 계약과 최초 실제 검증 | Spec 002가 대체하지 않으므로 유지 |
| `specs/002-*` | 완료된 확장 계약·계획·작업·검증 | 현재 Spec 002의 권위 있는 기록 |
| `validation.md` | 시간순 실행·실패·수정·최종 gate | 중간의 “미실행” 기록도 당시 사실이므로 지우지 않고 마지막 closure로 현재 상태 판단 |
| `docs/reference/skeleton/` | 팀 초기 골격 원문 보관 | 구현 기준은 아니지만 출처 추적을 위해 유지 |

## 9. 재현 수준별 시작 방법

### A. ControlProof 회귀 시험

Docker와 WhyYou를 띄우지 않고 실행·판정·증적·복구 계약을 검증한다.

```powershell
cd <ControlProof 저장소 경로>
& .\.venv\Scripts\python.exe -m ruff check .
& .\.venv\Scripts\python.exe -m pytest -q
```

마지막 공식 기록은 Ruff PASS와 `270 passed`다. 현재 코드가 더 변경됐다면 절대 숫자보다 모든 시험의
PASS 여부와 새 Validation 기록을 우선한다.

### B. 합성 PASS·FAIL·INCONCLUSIVE bundle 확인

실제 지원자나 WhyYou 서버 없이 Spec 001 호환 projection을 확인할 수 있다.

```powershell
& .\.venv\Scripts\python.exe -m scripts.prepare_sc008_review --output .controlproof/team-demo-01
& .\.venv\Scripts\python.exe -m engine.cli show <RUN_ID> --run-root .controlproof/team-demo-01/runs --json
& .\.venv\Scripts\python.exe -m engine.cli verify <RUN_ID> --run-root .controlproof/team-demo-01/runs --json
```

이는 개발 데모이며 사람 시간 측정 release gate가 아니다.

### C. Spec 002 로컬 actual-stack 재현

Docker Desktop, WhyYou 로컬 설정, Playwright Chromium과 두 저장소가 필요하다. 환경변수, stack 시작,
queue 초기 상태, 세 preflight, 세 Run, bundle verify와 종료 절차는 반드시
[Spec 002 Quickstart](../specs/002-h03-e03-fault-expansion/quickstart.md)를 그대로 따른다.

핵심 실행 명령은 다음과 같다.

```powershell
controlproof preflight H-03 --profile H03_DLQ_V2 --target whyyou-local --json
controlproof preflight E-03 --profile E03_BEFORE_V2 --target whyyou-local --json
controlproof preflight E-03 --profile E03_AFTER_V2 --target whyyou-local --json

controlproof run H-03 --profile H03_DLQ_V2 --target whyyou-local --label h03-local --json
controlproof run E-03 --profile E03_BEFORE_V2 --target whyyou-local --label e03-before-local --json
controlproof run E-03 --profile E03_AFTER_V2 --target whyyou-local --label e03-after-local --json
```

세 preflight가 모두 `READY`, `LOCAL_EMULATED`, AWS `NOT_RUN`이 아니면 Run을 만들지 않는다.

## 10. 결과를 읽는 법

- `PASS`: 해당 Run에서 실행한 profile의 필수 assertion, 필요한 증적 무결성과 환경 복구가 확인됐다.
- `FAIL`: 관찰 가능한 보호조치 위반·누락·중복이 확인됐다. ControlProof 실행기 오류와 다르다.
- `INCONCLUSIVE`: 접근 제한, 증적 부족·충돌 또는 복구 불확실성 때문에 PASS/FAIL을 주장할 수 없다.
- `NOT_RUN`: 실행하지 않은 환경 또는 범위다. 실제 AWS는 현재 `NOT_RUN`이다.

`show`에서는 verdict와 이유뿐 아니라 assertion별 expected/actual, evidence path·SHA-256,
restore 상태, 실제 failure route, 누락·중복 effect, 미검증 범위와 implementation status를 확인한다.
`verify`는 원본을 고치지 않고 hash, manifest, artifact envelope, scenario/target 연결을 검사한다.

과거 Run bundle은 `.controlproof/`에 있고 Git에 포함되지 않는다. 팀원이 pull만으로 같은 과거 Run ID를
조회할 수는 없지만, 코드·시나리오·fixture·자동 시험은 재현할 수 있다. 과거 결과의 Run ID, source SHA,
manifest SHA와 assertion 결과는 Validation에 남아 있다.

## 11. 코드·설계 검토 체크리스트

팀원은 테스트가 초록색인지뿐 아니라 다음을 검토한다.

1. AI 점수를 자동 합격·탈락 조건이나 ControlProof verdict 입력으로 사용하지 않는가?
2. 최종 결정 actor가 권한 있는 `COMPANY_USER`이고, AI·worker가 자동 확정하지 않는가?
3. 장애 명령 성공이 아니라 worker/boundary receipt로 실제 장애 발동을 증명하는가?
4. API·화면·DB·queue 관찰을 구분하고 충돌이나 미관찰을 숨기지 않는가?
5. source 재시도와 ControlProof의 DLQ 관찰 횟수를 혼동하지 않는가?
6. 결정 거부 뒤 부분 상태 변경과 자동 결정 부재를 별도로 확인하는가?
7. BEFORE와 AFTER가 각자 책임지는 assertion과 증적을 독립 판정하는가?
8. 복구 실패를 PASS/FAIL로 만들지 않고 후속 장애 실행을 차단하는가?
9. 최초 FAIL을 덮어쓰지 않고 child/grandchild Run으로 수정 결과를 연결하는가?
10. redaction·SHA-256·manifest·origin reference 검증이 assertion까지 연결되는가?
11. test hook과 고정 모델 대역이 production-like 환경에서 활성화되지 못하는가?
12. `LOCAL_EMULATED` 결과와 AWS `NOT_RUN`이 모든 결과와 설명에서 구분되는가?

의견은 Spec의 FR/SC ID, H03-A/E03-A/EV ID 또는 Task ID에 연결해 남긴다.

## 12. 다음 작업 순서

현재 다음 작업은 Spec 003이다. 아래 순서를 건너뛰지 않는다.

1. Product Brief와 D-013을 입력으로 Spec 003의 `spec.md`를 작성한다.
2. N-02의 경계·증적·완료 조건을 clarify한다.
3. WhyYou의 동의·분석 경로를 확인하고 기술 Plan을 작성한다.
4. Tasks와 traceability를 만든 뒤 analyze에서 모순·누락을 제거한다.
5. Spec 003 범위만 구현하고 `whyyou-local` actual Run과 bundle을 검증한다.
6. 필요하면 최초 FAIL을 보존한 child 재시험을 만들고 converge로 Spec 003을 닫는다.
7. 같은 전체 사이클로 Spec 004를 완료한 뒤 Spec 005로 넘어간다.

Spec 003~005 문서를 모두 먼저 작성한 뒤 개발을 시작하는 것이 아니다. 각 Spec은 명세·구현·실제
검증을 포함하는 독립 수직 흐름이며, 하나를 완료한 뒤 다음으로 진행한다. Spec 005까지 완료되면
V4 체크리스트를 다시 대조해 2주 MVP 최종 완료 여부를 판정한다.

## 13. 문서 유지 규칙

앞으로 기능 Spec을 닫을 때는 같은 변경 묶음에서 반드시 다음을 수행한다.

1. 해당 `spec.md`의 Status를 갱신한다.
2. `validation.md`에 최종 source SHA, 시험 결과, 한계와 종료 판정을 기록한다.
3. `tasks.md`와 `traceability.md`의 미완료·누락을 확인한다.
4. 이 통합 인수인계의 공식 상태, 완료 범위, 미완료 범위와 읽기 순서를 갱신한다.
5. `README.md`가 이 문서와 동일한 상태를 가리키는지 확인한다.
6. Product Brief의 “현재 산출물/후속 작업”이 과거 상태로 남지 않았는지 확인한다.
7. 중간 실패와 과거 결정은 삭제하지 않고 최종 closure가 무엇인지 명시한다.

현재 상태를 바꾸는 설명을 새 문서에 따로 추가해서는 안 된다. **현재 상태는 이 문서와 README,
각 Spec의 Status 및 최종 Validation closure가 서로 일치해야 한다.**
