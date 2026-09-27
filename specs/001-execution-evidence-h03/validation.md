# Spec 001 구현 검증 기록

**최종 검증일**: 2026-09-27
**범위**: clean virtual environment, deterministic adapter harness, WhyYou target-side 안전 제어, 실제 WhyYou 격리 로컬 스택 H-03 실행

## 완료된 자동 검증

| 검증 | 결과 |
|---|---|
| clean venv에서 editable dev 설치 | PASS |
| Playwright Chromium 설치 및 회사 콘솔 캡처 | PASS |
| `python -m ruff check .` | PASS |
| `python -m ruff format --check .` | PASS |
| `python -m pytest -q` | PASS, 131 tests in 139.22s |
| WhyYou ControlProof 관련 단위·안전 시험 | PASS, 21 tests |
| WhyYou 변경 파일 `ruff check` | PASS |
| `controlproof --help` | PASS, 6개 명령 노출 |
| fake H-03 EV-01~EV-09 manifest/link와 verify | PASS |
| fake FAIL→PASS child retest 후 parent verify/digest 불변 | PASS |
| delayed receipt·transient/no-stable report·delayed restore convergence | PASS |
| adversarial bundle semantic linkage verification | PASS |
| actual subject role·initial-state retest comparison | PASS |
| `run`·`show`·`retest` CLI envelope stability | PASS |
| 단계별 durable checkpoint와 중단·restore 예외 보존 | PASS |

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

## 실제 WhyYou 격리 스택 H-03 Run

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

## 실제 retest와 부모 bundle 불변성

canonical Run을 부모로 `repeat-verification` 재시험을 실행했다.

| 항목 | 기록 |
|---|---|
| parent Run ID | `f738081a-5fb3-4f21-af22-685a12355096` |
| child Run ID | `187a73b8-d667-424d-8a68-8ea115ace816` |
| child verdict | `FAIL` — H03-A2, H03-A3 동일 재현 |
| child bundle | `VERIFIED`, 55 files |
| child bundle digest | `47d4bd7e6119b78bbf55844140f57948c812720e3e189ce7e81ba715034b9d30` |
| retest target difference | 없음, canonical target version 동일 |
| retest model fixture difference | 없음, fixture ID/digest 동일 |
| retest 후 parent verify | `VERIFIED`, 52 files |
| retest 전·후 parent digest | 모두 `b5357cdfbe6ebf259d69477c381a538a066d6b98ed34a67427cc567a1cdbd70d` |

자식은 독립 bundle과 `parent_run_id`를 갖고, 부모 파일과 digest는 변경되지 않았다.

## 아직 완료되지 않은 외부 검증

### SC-008 비작성자 2분 검토

코드 작성에 참여하지 않은 팀원 1명이 `review-usability-checklist.md`의
PASS/FAIL/INCONCLUSIVE 세 case를 수행해야 한다. 현재 검토자, 실행 시각, 답변, 소요 시간이
없으므로 **미검증**이다. 자동 projection 테스트나 이 문서 작성자의 검토로 대신하지 않는다.

## 판정

- ControlProof 구현·clean environment·실제 스택 실행 게이트: PASS
- WhyYou H-03 제품 보호 결과: FAIL — H03-A2와 H03-A3 개선 필요
- 제품 완료 기준: **PARTIAL** — SC-008 비작성자 시험만 남음

**Checkpoint**: 구현 정상 여부와 시험 대상 WhyYou의 FAIL을 분리해 기록했고, 원본 bundle을
수정하지 않은 실제 재시험 계보까지 확인했다.
