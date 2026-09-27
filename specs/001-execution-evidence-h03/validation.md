# Spec 001 구현 검증 기록

**최종 검증일**: 2026-09-27
**범위**: clean virtual environment, deterministic adapter harness, WhyYou target-side 안전 제어,
실제 WhyYou 격리 로컬 스택 H-03 실행

## 완료된 자동 검증

| 검증 | 결과 |
|---|---|
| clean venv에서 editable dev 설치 | PASS |
| Playwright Chromium 설치 및 회사 콘솔 캡처 | PASS |
| `python -m ruff check .` | PASS |
| `python -m ruff format --check .` | PASS |
| `python -m pytest -q` | PASS, 134 tests in 114.60s |
| SC-008 관련 자동 시험 | PASS, 35 tests in 49.53s |
| WhyYou ControlProof 관련 단위·통합·안전 시험 | PASS, 25 tests |
| WhyYou 회사 콘솔 전체 시험 | PASS, 142 tests in 13.44s |
| WhyYou 회사 콘솔 typecheck·Prettier 및 Python Ruff | PASS |
| `controlproof --help` | PASS, 6개 명령 노출 |
| fake H-03 EV-01~EV-09 manifest/link와 verify | PASS |
| fake FAIL→PASS child retest 후 parent verify/digest 불변 | PASS |
| delayed receipt·transient/no-stable report·delayed restore convergence | PASS |
| adversarial bundle semantic linkage verification | PASS |
| actual subject role·initial-state retest comparison | PASS |
| `run`·`show`·`retest` CLI envelope stability | PASS |
| 단계별 durable checkpoint와 중단·restore 예외 보존 | PASS |
| 한국어 리포트 불가 상태와 UUID redaction false-positive 회귀 | PASS |
| SC-008 익명 3-case package의 `show`·`verify` | PASS, 3/3 |

자동 시험과 실제 스택 시험에는 합성 지원자와 로컬 전용 회사를 사용했다. 자격 증명·개인정보·
로컬 절대 경로는 bundle과 이 문서에 기록하지 않았다.

## Clean-environment quickstart 검증

새 가상환경 `controlproof-clean-20260927-1300`을 만들고 dev extras를 새로 설치한 뒤
`quickstart.md`의 설치, 정적 검사, 전체 시험, preflight, 실제 Run, show, verify, 변조 탐지,
retest 순서를 실행했다.

- 실제 스택 seed smoke: `LIVE_SEED_SMOKE=PASS`
- canonical Run verify: `VERIFIED`, 52 files
- 원본을 복사한 tamper fixture에서 `run.json` 한 필드만 변경: `INVALID`,
  `mismatched_files=["run.json"]`, exit code 5
- 원본 canonical Run은 변조 시험 뒤에도 `VERIFIED`

따라서 clean environment에서 문서화된 주요 사용자 경로와 원본 비수정 변조 탐지가 재현됐다.

## 첫 실제 WhyYou 격리 스택 H-03 Run

| 항목 | 기록 |
|---|---|
| 시험일 | 2026-09-27 |
| Run ID | `f738081a-5fb3-4f21-af22-685a12355096` |
| 구현 상태 | `IMPLEMENTED` |
| verdict | `FAIL` |
| 증적 | EV-01~EV-09 모두 존재, missing evidence 없음 |
| 환경 복구 | `SUCCEEDED` |
| 리포트 처리 복구 | `READY` |
| bundle verify | `VERIFIED`, 52 files |
| bundle digest | `b5357cdfbe6ebf259d69477c381a538a066d6b98ed34a67427cc567a1cdbd70d` |
| model fixture | `h03-report-v1` |
| model fixture digest | `ce09b95403b34e1390502c90f5c5edc518ddf65d38c8ce881617a37cac6d16b1` |
| target source kind | `GIT_WORKTREE` |
| target git commit | `573ce0c2146b8e7e1280e430ad4445f8a373f36e` |
| target git state | clean |
| canonical target version | `target-snapshot:sha256:ebfa40a48befb8723c76f4d10bdc87172e8f0eeb2f4a4dd26831a3daa859f762` |
| OpenAPI digest | `1d23e1ae973672726ed3232fd83edd25ad06cd253990548c1dada1de609b952a` |
| DB migration head | `m_003_criterion_grounded_rag` |
| schema signature digest | `f067922766c478fe9df4b4bddd6d3b0c53cf81e324f2d8d776da773f935d8030` |

`FAIL`은 ControlProof 실행 실패가 아니라 실제 WhyYou 보호 동작에서 발견된 결과다.

- H03-A1 PASS: marker와 일치하는 worker trigger receipt가 남았다.
- H03-A2 FAIL: API는 리포트가 `queued`/부재라고 관찰했지만 담당자 UI의 상태 class는
  `ready`여서 실패 또는 장기 지연을 명확히 표시하지 않았다.
- H03-A3 FAIL: 최종 결정 요청 자체는 거부됐지만, WhyYou가 `REPORT_NOT_AVAILABLE` 같은
  대상 제공 사유 코드를 반환하지 않았다.
- H03-A4 PASS: 거부된 요청 뒤 부분 상태 변경이 없었다.
- H03-A5 PASS: 장애 관찰 구간에 자동 최종 결정이 없었다.
- H03-A6 PASS: fault marker가 제거됐고 worker와 리포트 처리가 복구됐다.

검증 범위 밖으로 명시된 항목은 retry exhaustion/DLQ, 일반 stage-move 우회,
복구 후 idempotency다. 이 항목들은 이번 verdict에 포함하지 않았다.

## WhyYou 보호조치 수정

첫 실제 FAIL을 수정 이력으로 보존한 뒤, WhyYou 전용 브랜치
`bosung/controlproof-h03-integration`의 커밋
`aa0ae2b4735d0cd1f2bfb6fe2f07077b3aa4f659`에서 다음을 보완했다.

- 최종 리포트가 없으면 최종 결정 API가 쓰기 작업 전에 `409`와
  `REPORT_NOT_AVAILABLE`을 반환한다.
- 리포트가 계속 `queued`이면 회사 화면이 장기 지연을 알리고, 조회 오류이면 실패 상태를
  명시한다. 어느 경우에도 준비된 리포트처럼 표시하지 않는다.
- backend 통합 시험과 company-console UI 회귀 시험을 먼저 실패시킨 뒤 구현했고, 전체
  company-console 142개 시험과 typecheck가 통과했다.

ControlProof에서도 화면의 `data-report-state`를 우선 읽고, “리포트를 불러올 수 없습니다”를
실패로 분류하도록 browser adapter와 계약 시험을 보강했다.

## 실제 FAIL → PASS retest와 부모 bundle 불변성

첫 canonical FAIL Run을 부모로 수정 전 재현과 수정 후 재시험을 각각 새 child bundle로
실행했다. 수정 전 `repeat-verification` Run
`187a73b8-d667-424d-8a68-8ea115ace816`은 H03-A2·A3 FAIL을 동일하게 재현했다.
최종 채택한 수정 후 결과는 아래와 같다.

| 항목 | 기록 |
|---|---|
| parent Run ID | `f738081a-5fb3-4f21-af22-685a12355096` |
| final child Run ID | `e42482c9-ba84-42c6-984d-209e0f80b7d8` |
| child verdict | `PASS` — H03-A1~A6 모두 PASS |
| child bundle | `VERIFIED`, 53 files |
| child bundle digest | `213f11a4f37dfb4108443d4dd122e6c75b4f96578efe671d074a8b38053baec0` |
| retest target difference | WhyYou `git_commit_sha`만 변경 |
| child target git commit | `aa0ae2b4735d0cd1f2bfb6fe2f07077b3aa4f659` |
| child canonical target version | `target-snapshot:sha256:302cfcbf60c46f658a0d747903ec6d04f12f2f5ccbc30ff670e810733560d17d` |
| scenario difference | 없음, version/digest 동일 |
| retest model fixture difference | 없음, fixture ID/digest 동일 |
| retest 후 parent verify | `VERIFIED`, 52 files |
| retest 전·후 parent digest | 모두 `b5357cdfbe6ebf259d69477c381a538a066d6b98ed34a67427cc567a1cdbd70d` |

최종 child는 리포트 부재/실패 표시, 명시적 결정 거부, 무부작용, 자동 결정 부재, 환경 복구를
모두 증명한다. 자식은 독립 bundle과 `parent_run_id`를 갖고, 부모 파일과 digest는 변경되지 않았다.

### 재시험 중 비채택 실행

| Run ID | 결과 | 비채택 이유 |
|---|---|---|
| `906301c2-8a60-4f6d-8a24-ec2b16ac5644` | `INCONCLUSIVE`, `ABORTED` | 회사 콘솔 개발 서버 미기동으로 브라우저 증적 수집 실패 |
| `675ca918-c1df-4d9e-ab68-a6353103a480` | `FAIL`, A2 | 화면은 실패를 표시했으나 ControlProof가 한국어 불가 문구를 `ready`로 오분류 |
| `69ea137e-ff8f-46ff-89de-43a624b4fc2f` | `PASS` | CLI target ID 오타로 원본과 대상 식별자가 달라 종료 증적으로 채택하지 않음 |

세 bundle은 실패·중단 이력을 감추지 않기 위해 그대로 보존했고, 최종 판정에는 정확한 대상 ID로
다시 실행한 canonical child만 사용했다.

## SC-008 변경 결정과 검증

제품 책임자 결정으로 CLI 비작성자 120초 시간 측정을 Spec 001 완료 gate에서 제외했다. 실제로
측정하지 않은 시간을 통과한 것으로 간주하지 않으며, 사람 대상 이해도 검토는 고객용 웹 결과
화면 구현 후 별도 UX Spec에서 수행한다.

Spec 001의 SC-008은 다음 자동 검증으로 대체했다.

- canonical PASS·FAIL·INCONCLUSIVE projection 생성
- verdict, 핵심 이유, 실패·판정 불가 assertion 확인
- assertion별 증적 상대 경로·SHA-256 연결 확인
- 환경 복구, 리포트 처리 복구와 미검증 범위 확인
- 세 합성 bundle의 `show` exit 0과 `verify=VERIFIED`
- 관련 자동 시험 35개와 전체 시험 134개 PASS

`scripts/prepare_sc008_review.py`와 합성 세 verdict package는 선택적 개발 데모로 유지하지만
사람 시간 측정 release gate로 사용하지 않는다. 결정 근거는 Decision Log D-012와
`review-usability-checklist.md`에 남겼다.

## 판정

- ControlProof 구현·clean environment·실제 스택 실행 게이트: PASS
- WhyYou H-03 제품 보호 결과: PASS — 원본 FAIL을 보존한 별도 child retest에서 A1~A6 확인
- 기술 구현 완료 기준: **COMPLETE**
- Spec 001 공식 종료 상태: **COMPLETE**

**Checkpoint**: 실제 FAIL을 수정 전 이력으로 보존하고, 제품 수정 커밋과 연결된 PASS child,
원본 bundle 불변성과 CLI projection 계약까지 검증했다. 사람 사용성 평가는 현재 CLI가 아니라
후속 웹 결과 화면을 대상으로 수행한다.
