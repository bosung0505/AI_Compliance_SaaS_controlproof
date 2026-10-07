# ControlProof 팀 통합 인수인계

## 1. 이 문서의 역할

이 문서는 새 팀원이 저장소의 **현재 공식 상태**, 완료된 작업, 검증 범위, 재현 방법과 다음 결정 지점을
한곳에서 이해하기 위한 단일 진입점이다. 과거의 `TEAM_HANDOFF_SPEC_001.md`를 대체하며, 프로젝트 상태를
확인할 때는 이 문서를 먼저 읽는다.

- 상태 기준일: 2026-10-08
- 현재 전달 브랜치: ControlProof `yeonwoo/004-e01-e02-score-evidence`, WhyYou `bosung/controlproof-n02-integration`(`374b122`).
  Spec 003 기반은 `003-n02-consent-order`에 보존되며 현재 기능은 Spec 004다.
  Spec 003 PR #1·WhyYou PR #5는 해당 Spec 통합 브랜치에 병합됐고, Spec 004 WhyYou PR #8도 integration에 병합됐다.
  main 병합은 사용자가 명시적으로 금지했다. 두 현재 전달 브랜치를 pull하며, 실제 Run의 source SHA는 검증 원장의 당시 값으로 유지한다.
- 이 문서가 설명하는 범위: Spec 001·002 전체, Spec 003 기록·PR 검토 보완, Spec 004 T001~T088 actual 검증
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
| Spec 003 | 구현·actual validation 기록 완료, PR 검토 보완 | T001~T093 기록 완료. child `7b59237e…`는 INCONCLUSIVE. PR 검토에서 복구 시간 오판, A7 재시도 증거 누락, H-03 동의 전제조건을 추가 보완했다(ID-003-19). 최신 자동 회귀 결과는 validation의 PR review closure 참조. Spec 전체 Complete는 아직 선언하지 않는다. |
| N-02 최초 actual Run | 봉인·검증 완료, 제품 판정 미종결 | 부모 `15cef078-ee24-4f0e-91ef-381e0f7a1cc2`: A1~A3 PASS, A4~A7 개별 FAIL, 전체 `INCONCLUSIVE` (`RESTORE_FAILED` 우선). 19개 파일 bundle `VERIFIED`는 무결성 확인이며 빠진 관찰 사실의 증명은 아니다. 원본 verdict와 bundle은 변경하지 않는다. |
| N-02 child Run (T084 attempt 3) | 봉인·검증 완료, 제품 판정 `INCONCLUSIVE` | child `7b59237e-0a96-403a-9add-28b91011e950`: A1~A4·A6 PASS, A5·A7 `INCONCLUSIVE`, 복구 `SUCCEEDED`, 차단 없음, 21개 파일 bundle `VERIFIED`, 부모 manifest 불변. 동의 전 세 경계 차단과 장애 원자성·복구는 입증됐고, 동의 뒤 처리 순서는 녹화·AI 평가만 입증됐다. 문서 분석 결과는 격리 대상이 LLM 분석을 못 해서 미입증이다. attempt 1·2(중단·INVALID/RESTORE_FAILED)는 보존된 실행기 결함 증거다. |
| Spec 004 | T001~T088 완료, 종료 gate 대기 | 최초 E-01 FAIL 봉인 → PR #8 수정 후 child `a5ad4676…` A1~A4 PASS·복구 성공·VERIFIED, D1 네 모드 관찰. E-02 최초 공식 PASS(`ce8d862`); 최신 WhyYou `374b122`은 E-02 preflight READY만 확인. 다음 T089~T097. Spec 전체 미완료. |
| Spec 005 | 계획 확정·미착수 | 웹 워크벤치·12개 시나리오 카탈로그·보고서와 웹 UX 검토를 구현·검증한다. |
| 실제 AWS | `NOT_RUN` | AWS SQS·ECS·IAM·CloudWatch·운영 네트워크는 검증하지 않았다. |
| ControlProof 웹 워크벤치 | 미구현 | 현재 결과 확인과 재현은 CLI·JSON·봉인 bundle을 사용한다. |
| 2주 MVP 전체 | 미완료 | Spec 001·002 완료를 전체 제품 또는 전체 시나리오 완료로 확대하면 안 된다. |
| 웹 결과 사용성 검토 | 미실시 | CLI 사람 시간 측정은 완료 gate에서 제외했고, 고객용 웹 결과 화면을 만든 뒤 별도 검토한다. |
| 0단계 정합성 작업 | 완료 | 12개 범위표, Spec 003 source baseline, AI 플레이북과 휴대 가능한 재현 문서를 정리했다. |
| 독립 PC 재현 | `PENDING_EXTERNAL_REPRODUCTION` | Spec 001·002 actual Run은 한 PC에서만 수행됐다. 다른 팀원의 H03_DLQ_V2 재현 전에는 독립 재현 완료로 주장하지 않는다. |
| main 통합 | 보류 | 독립 재현 gate 뒤 Spec 001·002를 포함한 현재 브랜치를 검토 가능한 PR로 통합한다. |

따라서 저장소의 공식 상태는 **Spec 001·002 Complete, Spec 003 actual validation 완료·converge 전,
Spec 004 T001~T088 완료·최종 품질/재현/converge 전**이다.
child 판정이 `INCONCLUSIVE`(A5·A7 문서 분석 결과 미입증)이므로 WhyYou N-02 PASS로 부르지 않는다.
T092 문서는 이번 검토 결과로 다시 동기화했다. 전달 브랜치 통합 뒤 최종 converge에서 이 한계와
검토 보완 후 실제 Run `NOT_RUN`을 명시하고 종료 범위를 확정한다. 추가 실제 시험을 하면 새 child로
봉인한다. main 통합은 별도 승인 전까지 금지한다.

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
- N-02 최종 검증과 N-01·N-03 실행기·최종 검증
- H-01, H-02 실행기와 최종 검증
- E-01, E-02 실행기와 최종 검증
- A-01~A-03의 기능 구현: 이번 MVP에서는 WhyYou에 시험 대상이 없어 `NO_TEST_TARGET`로 보고하는 범위
- 전체 시나리오 카탈로그를 한 번에 실행하는 제품 흐름
- 조직·사용자·권한 관리, 결제, 운영 배포와 상용 SaaS 운영 기능
- 실제 AWS·production 환경 검증
- 다른 팀원 PC의 Spec 002 `H03_DLQ_V2` 독립 재현과 Validation 추가
- Spec 001·002 feature branch의 PR 검토와 main 통합

### Spec 003의 현재 사실과 남은 작업

최초 Run(부모 `15cef078-ee24-4f0e-91ef-381e0f7a1cc2`, ControlProof `b92b9ada…`, WhyYou `94ad7f2c…`, manifest
`d2306f3c…`)은 불변이다. 그 FAIL은 전부 원인별로 분류됐고 결과는
[Implementation Decisions](../specs/003-n02-consent-order/implementation-decisions.md) ID-003-09~18과
[Validation](../specs/003-n02-consent-order/validation.md)의 Run·assertion ledger에 있다.

- 실행기 결함(ID-003-09~15, 17, 18): seed 값(제출 요건, 직무 상태, 평가 기준 가이드, 면접 수준, 전략 시간 예산),
  시간 정책 미적용, 장애 lane 시도 식별자 재사용, teardown FK, 요청 ID 미전달, 복구 안전과 재시도 결과의 혼합,
  AI 평가 거부 증거 계약, 동의 lane의 제품 흐름 구동. 각각 실패 시험 → 최소 수정 → 전체 회귀로 처리했다.
- WhyYou 보호조치(증거 기반): T083 보고서 작업자의 `ai_assessment` 동의 확인과 거부 receipt, T082 세션 시작의
  `recording` 동의 확인. 둘 다 동의 없는 처리 시작이 실제 Run에서 관찰된 뒤에만 추가했다. T081은 `NOT_REQUIRED`.
- child `7b59237e-0a96-403a-9add-28b91011e950`(ControlProof `14f9868`, WhyYou `be81ebc`): A1~A4·A6 PASS, A5·A7 `INCONCLUSIVE`,
  복구 `SUCCEEDED`, manifest `2a0e7862…`. 녹화 경로는 장비 점검→세션→업로드→확정, AI 평가는 보고서 생성까지
  실제로 돌렸고, 문서 경로는 분석 작업자 진입까지만 도달했다(격리 대상은 외부 AI 차단).
- 알려진 한계: 문서 분석 결과는 격리 환경에서 만들 수 없다(고정 모델이 보고서 작업만 지원); 401/403은 전부
  `CONSENT_REQUIRED`로 기록된다(대상이 사유를 응답하지 않음); 복구 lane의 인과 사건은 파일로 봉인되지 않는다;
  녹화 업로드가 로컬 object store에 객체를 남긴다; H-03 pending-report seed에는 동의 행이 없어 T083이 적용된
  대상에서 H-03 보고서 요청은 거부된다(H-03 재실행 전 seed 보완 필요).

| 단계 | Task | 상태 |
|---|---|---|
| 증거 기반 분류·조건부 보완 | T080~T083 | 완료 (T081 `NOT_REQUIRED`, T082·T083 `REQUIRED`·구현) |
| 부모 연결 재시험 | T084 | 완료 (attempt 3 child 봉인·검증) |
| 종료 품질 gate | T085~T091 | 완료 (시간 정책·보안 corpus·회귀 기록·quickstart 실제 ID·추적성·조건부 요약·스캔) |
| 상태 수렴·독립 재현 | T092~T093 | T092 이 문서 묶음으로 완료, T093은 팀원 PC(연우)에서 preflight 16/16과 child Run으로 기록 |

남은 것은 PR(base `003-n02-consent-order`)과 검토, WhyYou PR #5 병합, 그리고 `$speckit-converge`의 종료 기준 확인이다.

후속 개발 순서는 다음과 같이 확정했다.

| 순서 | 기능 Spec | 포함 범위 | 종료 의미 |
|---|---|---|---|
| 1 | Spec 003 — N-02 동의·AI 처리 순서 | 경로 시드, 동의 전 우회 차단, 사건 순서·정책 증적, 필요한 WhyYou 연결·주입·복구 | N-02 actual Run과 bundle까지 완료 |
| 2 | Spec 004 — E-01·E-02 점수 근거·기준 보존 | 잘못된 인용, `scoring_inputs`·가중치·버전 snapshot, 기준 변경 후 과거 리포트 불변 | E-01·E-02 actual 검증까지 완료 |
| 3 | Spec 005 — 웹 워크벤치·보고서 | 12개 시나리오, 결과·증적·재시험 비교, A 계열 `NO_TEST_TARGET`, 미실행·미검증 범위, 웹 UX 검토 | V4 결과물 완료 기준 검증 |

기존의 “남은 WhyYou 연결과 시험 조건”은 독립 Spec으로 만들지 않는다. N-02에 필요한 capability는
Spec 003, E-01·E-02에 필요한 capability는 Spec 004 안에서 사용자 흐름과
함께 구현한다.

H-01·H-02·N-01·N-03의 실제 완주는 V4의 목표 상한이다. Spec 005에서 readiness와 `NOT_RUN`을
사실대로 표시하되, 실제 실행까지 요구하려면 별도 후속 Spec 또는 승인된 범위 변경이 필요하다.
결정 이유와 변경 전·후는 [Decision Log D-013](./product/ControlProof_MVP_Decision_Log.md)에 있다.

12개라는 숫자의 공식 해석은 [MVP 시나리오 범위표](./product/ControlProof_MVP_Scenario_Coverage_Matrix.md)를
따른다. 현재는 12개 관리, 5개 실제 실행 목표, 4개 `NOT_RUN`, 3개 `NO_TEST_TARGET`이며 “12개 검증
완료”라고 표현하지 않는다.

## 7. 저장소와 브랜치 안전성

| 저장소 | 사용 브랜치 | 역할 |
|---|---|---|
| `bosung0505/AI_Compliance_SaaS_controlproof` | `yeonwoo/004-e01-e02-score-evidence` | Spec 001~003 기반(병합된 `003-n02-consent-order`)과 현재 기능 Spec 004 |
| `jhkim0602/gbsa_aws` | `bosung/controlproof-n02-integration` | N-02 제품 보호조치와 local/test 계측, Spec 004 고정 모델·보고서 연결·가용성 표시(PR #8) |

현재 브랜치와 원격의 일치 여부는 아래 명령으로 확인한다. Spec 002 최종 actual-stack에서 검증한
ControlProof 구현 commit은 `06f7a77`, WhyYou commit은
`511ae9e2cae66b8d0ce31e8851537ed27ac6dd0c`다. 이후 문서 commit이 추가돼도 검증 source는
Validation에 기록된 SHA로 식별한다.

2026-10-02 전달 checkpoint에서 WhyYou `bosung/controlproof-n02-integration`의 소스 변경 commit은
`7f98370d8f8b5c0513c7901ef8ecb85f0776d492`이고, 원본 cleanup 증거의 바이트 보존까지 반영한
전달 HEAD는 `c8e9970d1b873247f95928e68e93d5afdc6791ae`다. ControlProof 전달 소스는
이 인수인계를 포함해 `origin/003-n02-consent-order`에 게시된 HEAD로 식별하고, 팀원은 checkout
뒤 전체 SHA를 직접 기록한다. 두 전달 브랜치는 최초 actual Run 당시의 source SHA와 다르다. 원본
Run의 과거 source claim은 위 Validation ledger의 SHA로 계속 식별한다. 기존 로컬 WhyYou checkout에는
이번에 추적한 cleanup JSON 외의 `.controlproof/` 진단 로그·작업자 증거가 미추적 파일로 남아 있다.
이를 새 소스 commit에 넣거나 clean-source 증명으로 취급하지 않는다.

WhyYou `main`에는 ControlProof 관련 변경을 직접 commit하거나 push하지 않는다. actual Run 전에는 두
checkout 모두 clean이어야 한다. 기존 체크포인트와 원본 Run을 덮어쓰지 않는다.

```powershell
git branch --show-current
git status --short
git rev-list --left-right --count HEAD...@{upstream}
```

각 저장소 루트에서 실행한다. 마지막 명령은 upstream이 없으면 실패한다. 게시와 upstream 설정이
끝난 뒤 `0  0`이면 해당 로컬 브랜치와 추적 원격이 일치한다.

### 팀원 PC에 가져올 소스와 로컬 증거

두 저장소를 나란히 clone한다. 각 저장소에서 `git fetch origin`을 수행하고 ControlProof는
`origin/yeonwoo/004-e01-e02-score-evidence`, WhyYou는 `origin/bosung/controlproof-n02-integration`을 checkout한다.
`git branch --show-current`, `git rev-parse HEAD`, `git status --short`로 전달받은 SHA와 clean 상태를
대조한다. 파일 몇 개만 별도 pull하면 실행기·시나리오·테스트·WhyYou 계측 버전이 어긋날 수 있다.

현재 Spec 004 재현은 `specs/004-e01-e02-score-evidence/quickstart.md`와 최신 validation을 따른다.
아래 원본 전달 예외·명령은 과거 Spec 003 checkpoint이며, Spec 004 원본 Run은 포함되지 않는다.

일반 규칙상 `.env`, credential, `.controlproof/`와 Run bundle은 Git에 넣지 않는다. 다만 사용자가
2026-10-02에 **공개 Git 게시를 승인한 일회성 예외**로, 이 부모의 정확한 bundle 20개 파일과
정비 기록만 ControlProof 작업 브랜치에, cleanup 증거 JSON 하나만 WhyYou 작업 브랜치에 포함했다.
따라서 팀원은 두 브랜치를 pull하면 아래 세 경로를 별도 복사 없이 받는다.

| 저장소 | pull 뒤 확인할 원본 경로 | SHA-256 확인 |
|---|---|---|
| ControlProof | `.controlproof/runs/15cef078-ee24-4f0e-91ef-381e0f7a1cc2/` 폴더 전체 | `manifest.json`: `d2306f3cd6e2b15ce87d94e4844a2278c7ea3c0b3c052a2aac45e1bff8f2bc9b`; `verify`는 19개 증거 파일 `VERIFIED` |
| ControlProof | `.controlproof/runs/blocks/maintenance/15cef078-ee24-4f0e-91ef-381e0f7a1cc2.json` | `3180d28664f7274e8c653fb7c3b59a1342c1801c153c81485d80db7767668666` |
| WhyYou | `.controlproof/n02-cleanup-evidence-375c2f2bfcaf.json` | `406a87bc88cf2f0ec0bcff1799f7ad4b8099937e507484d11ad9e3d801649eef` |

팀원은 ControlProof 루트에서 `Get-FileHash`로 세 해시를 확인하고
`.\.venv\Scripts\python.exe -m engine.cli verify 15cef078-ee24-4f0e-91ef-381e0f7a1cc2 --json`을
실행한다. T084에는 WhyYou JSON을 `--cleanup-evidence`로 지정한다. 이후 새 Run과 진단 로그는
이 예외에 포함되지 않는다. 새 독립 N-02 Run을 수행하는 팀원은 자신의 로컬 설정과 새 Run ID를
별도로 기록한다.

## 8. 팀원이 읽을 문서 순서

처음에는 다음 순서로 읽는다.

1. 이 문서
2. 저장소 [README](../README.md)
3. 진행 중인 [Spec 003 Tasks](../specs/003-n02-consent-order/tasks.md),
   [Validation](../specs/003-n02-consent-order/validation.md),
   [Implementation Decisions](../specs/003-n02-consent-order/implementation-decisions.md)
4. 실제 재현 전 [Spec 003 Quickstart](../specs/003-n02-consent-order/quickstart.md),
   [Spec](../specs/003-n02-consent-order/spec.md)과 [Traceability](../specs/003-n02-consent-order/traceability.md)
5. [2주 MVP 기능 범위 V4](./product/ControlProof_WhyYou_2주_MVP_기능범위_v4.md)
6. [MVP 시나리오 범위표](./product/ControlProof_MVP_Scenario_Coverage_Matrix.md)
7. [AI·Spec Kit 작업 플레이북](./AI_SPEC_KIT_PLAYBOOK.md)
8. [Spec 002](../specs/002-h03-e03-fault-expansion/spec.md)
9. [Spec 002 Validation](../specs/002-h03-e03-fault-expansion/validation.md)의 최종 closure 절
10. [Spec 002 Traceability](../specs/002-h03-e03-fault-expansion/traceability.md)
11. H-03/E-03 재현할 때 [Spec 002 Quickstart](../specs/002-h03-e03-fault-expansion/quickstart.md)
12. 구현 세부가 필요할 때 [Plan](../specs/002-h03-e03-fault-expansion/plan.md),
   [Data Model](../specs/002-h03-e03-fault-expansion/data-model.md),
   [Contracts](../specs/002-h03-e03-fault-expansion/contracts/),
   [Tasks](../specs/002-h03-e03-fault-expansion/tasks.md),
   [Implementation Decisions](../specs/002-h03-e03-fault-expansion/implementation-decisions.md)
13. 기본 모델의 유래가 필요할 때 [Spec 001](../specs/001-execution-evidence-h03/spec.md),
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
| `specs/003-*` | 진행 중인 N-02 계약·작업·실제 검증 | 최신 사실은 Tasks·Validation·Implementation Decisions의 마지막 기록을 확인 |
| `validation.md` | 시간순 실행·실패·수정·최종 gate | 중간의 “미실행” 기록도 당시 사실이므로 지우지 않고 마지막 closure로 현재 상태 판단 |
| `docs/reference/skeleton/` | 팀 초기 골격 원문 보관 | 구현 기준은 아니지만 출처 추적을 위해 유지 |

## 9. 재현 수준별 시작 방법

### 팀원 PC 기본 준비

기존 [ControlProof README](../README.md)의 Python 3.12 개발환경과
WhyYou 저장소 `docs/local-development.md`의 Windows PowerShell 절에는
일반 설치·Docker 시작·API·작업자 실행·시험 명령이 있다. 팀원은 두 저장소를 같은 상위 디렉터리에
놓고 각 저장소의 예시 환경 파일로 **자신의 로컬 전용** 설정을 만든다. ControlProof는
`python3.12 -m venv .venv`와 `.\.venv\Scripts\python.exe -m pip install -e ".[dev]"`를,
WhyYou는 `scripts/local.ps1 install`, `doctor`, `up` 절차를 참고한다. PostgreSQL·LocalStack·API와
관리되는 작업자 4개의 기동 여부를 확인한다. N-02 verdict에는 company console/browser가 필수는
아니다.

WhyYou 기본 `.env.example`의 일반 AI provider 값은 외부 GCP/AWS 호출 경로를 포함한다. N-02에서는
실제 키를 채워 실행하지 말고, [Spec 003 Quickstart](../specs/003-n02-consent-order/quickstart.md)의
`LOCAL_EMULATED`, 외부 AI 차단, 고정 model/embedder 대역, loopback endpoint와 API·작업자별 동일
격리 증명을 충족해야 한다. `doctor` 통과만으로 N-02 격리나 전체 preflight `READY`를 주장하지 않는다.
원본 로컬 DB에는 미처리 outbox 325건이 있어 그 DB에 작업자를 바로 연결하지 않는다. 새로 마이그레이션한
DB와 전용 LocalStack 큐를 써서 분리한다. 이 원본 DB 수치는 2026-10-02 조사 시점의 관찰값이다.

현재 문서들은 기본 설치와 일반 시험은 안내하지만, **N-02의 깨끗한 독립 PC 전체 절차는 아직
검증 완료되지 않았다.** T088·T093에서 quickstart의 실제 명령, 로컬
설정과 독립 Run을 확인하고 발견한 portability 결함을 수정·기록해야 한다.

N-02 관련 빠른 자동 점검은 두 저장소의 개발환경을 만든 뒤 각 저장소 루트에서 실행한다.
이는 실제 WhyYou Run이나 전체 회귀를 대신하지 않는다.

```powershell
# ControlProof 저장소
& .\.venv\Scripts\python.exe -m pytest -q tests/contract/test_whyyou_capability.py tests/contract/test_cli_preflight.py tests/integration/test_n02_retest_lineage.py

# WhyYou 저장소
& .\.venv\Scripts\python.exe -m pytest -q backend/tests/integration/test_worker_delivery.py backend/tests/unit/runtime/test_controlproof_model_substitute.py backend/tests/integration/test_controlproof_fault_hook_safety.py
```

### A. ControlProof 회귀 시험

Docker와 WhyYou를 띄우지 않고 실행·판정·증적·복구 계약을 검증한다.

```powershell
cd <ControlProof 저장소 경로>
& .\.venv\Scripts\python.exe -m ruff check .
& .\.venv\Scripts\python.exe -m pytest -q
```

Spec 002 closure 기록은 Ruff PASS와 `270 passed`이고, Spec 003 Phase 6 기록은 `407 passed`다.
그 뒤 T080-E1~E4와 관련 소스가 바뀌었으므로 **현재 전체 회귀 PASS 수로 407을 재사용하지 않는다.**
Phase 7 T087에서 변경 후 전체 회귀를 다시 실행한다. 그 전에는 관련 scoped 시험만 해당 변경의
검증으로 인용한다.

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

### D. Spec 003 N-02 로컬 actual Run·child 재시험

[Spec 003 Quickstart](../specs/003-n02-consent-order/quickstart.md)를 기준으로 두 저장소의 branch,
HEAD, clean 상태와 대상 격리를 확인한다. `preflight N-02 --profile N02_CONSENT_ORDER_V1 --target whyyou-local --json`의
**전체 16개**가 `READY`인 새 결과가 있어야 Run을 시작할 수 있다.
최근 14/16 결과는 Run 허가가 아니다. 작업자별 session/PID/설정 digest 증명, API와 worker의
외부 AI 격리, 원본 DB와 분리된 큐·DB, N-02 안전 상태를 함께 확인한다. N-02 최초 부모 Run은 이미
있으므로 같은 ID를 재실행하거나 bundle을 고치지 않는다.

T084는 완료됐다. 팀원 PC에서 전체 16/16 `READY` preflight 뒤 부모 `15cef078-ee24-4f0e-91ef-381e0f7a1cc2`를 지정하고 원본
정비 증거를 `--cleanup-evidence`로 제공해 child `7b59237e-0a96-403a-9add-28b91011e950`를 실행·봉인·검증했다(명령과 실제 ID는
quickstart 7~8절). 같은 절차를 다시 밟으면 새 child가 생기며 기존 부모·child bundle은 바뀌지 않는다.
팀원 PC 특유의 환경 조정(5433 포트, `.env` 수동 로드, `/v1/me`로 회사 생성, 가짜 GCP 키, `Set-ExecutionPolicy`,
앱 제어 정책이 막은 SQLAlchemy `.pyd` 우회)은 Validation의 T093 행과 ID-003-15 기록에 있다.

## 10. 결과를 읽는 법

- `PASS`: 해당 Run에서 실행한 profile의 필수 assertion, 필요한 증적 무결성과 환경 복구가 확인됐다.
- `FAIL`: 관찰 가능한 보호조치 위반·누락·중복이 확인됐다. ControlProof 실행기 오류와 다르다.
- `INCONCLUSIVE`: 접근 제한, 증적 부족·충돌 또는 복구 불확실성 때문에 PASS/FAIL을 주장할 수 없다.
- `NOT_RUN`: 실행하지 않은 환경 또는 범위다. 실제 AWS는 현재 `NOT_RUN`이다.

`show`에서는 verdict와 이유뿐 아니라 assertion별 expected/actual, evidence path·SHA-256,
restore 상태, 실제 failure route, 누락·중복 effect, 미검증 범위와 implementation status를 확인한다.
`verify`는 원본을 고치지 않고 hash, manifest, artifact envelope, scenario/target 연결을 검사한다.

일반적으로 과거 Run bundle은 `.controlproof/`에만 있고 Git에 포함되지 않는다. 이번 N-02 부모
`15cef078-ee24-4f0e-91ef-381e0f7a1cc2`만 위 일회성 예외로 공개 작업 브랜치에 정확한 원본을
보존했다. 이 파일을 pull해 조회·검증하는 것은 팀원 PC에서 새 Run을 독립 재현한 결과가 아니다.
과거 결과의 Run ID, source SHA, manifest SHA와 assertion 결과는 Validation에도 남아 있다.

N-02 최초 부모는 개별 A4~A7 FAIL이 있어도 복구 실패가 최종 판정보다 우선해 전체
`INCONCLUSIVE`다. 이후 `cleanup-confirm`은 현재의 안전 상태를 증명할 뿐 부모의 과거 verdict를
PASS로 바꾸지 않는다. 자동 fixture PASS, API/작업자 readiness, bundle `VERIFIED`와 실제 WhyYou
제품 판정은 서로 다른 사실이다.

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

Spec 003 Implement와 actual validation(T001~T093)은 끝났고 PR #1(`d0c0e5b`)과 WhyYou PR #5(`eec8f70`)는 병합됐다.
현재 기능은 Spec 004(`yeonwoo/004-e01-e02-score-evidence`, WhyYou `bosung/controlproof-n02-integration` `374b122`)이며 아래 4번이
진행 중이다. 1~3번은 Spec 003에 남은 항목이다.

1. **PR과 검토:** `yeonwoo/003-t080-t085` → `003-n02-consent-order` PR을 만든다. 보성은 ID-003-13~18의
   `PROPOSED`/위임 판단 항목을 최종 확정하고, WhyYou PR jhkim0602/gbsa_aws#5(T083·T082)를 병합 또는 재배치한다.
   그 PR은 base 브랜치 특성상 CI가 돌지 않으므로 관리자 병합이 필요하다.
2. **converge:** README, 이 문서, 플레이북, Product Brief, 범위표와 Spec 003 상태가 일치하는지
   `$speckit-converge` 기준으로 확인한다. child 판정은 `INCONCLUSIVE`이며 PASS로 올려 적지 않는다.
3. **후속 한계 처리(선택):** 문서 분석 결과까지 입증하려면 WhyYou 고정 모델을 문서 분석·전략 생성 작업까지
   확장해야 한다(제품 코드 변경, 미승인). H-03 seed에 동의 행을 넣기 전에는 T083이 적용된 대상에서 H-03을
   재실행하지 않는다.
4. **Spec 004 (현재):** T001~T088 완료(T087 NOT_REQUIRED). WhyYou PR #8 병합 `374b122` 기준.
   - 최초 공식 E-01 `09c9d9bb…` FAIL과 D1-only child `ec0c895d…` FAIL은 보존됐다. D1 네 모드는 진단 관찰이다.
   - 수정 후 공식 child `a5ad4676-333b-44d0-8657-95ab434f3b3d`: A1~A4 PASS, 복구 SUCCEEDED, bundle VERIFIED,
     잔여 데이터 0. 자막 삭제 시 가용성 false, 복원 후 true; 저장 점수·동결 입력을 바꾸지 않았다.
   - E-02 최초 공식 `e39e62ae…` PASS(WhyYou `ce8d862`, 72/74·첫 보고서 불변). `374b122`에서 E-02 preflight
     READY/계산 소스 MATCH만 확인했고 새 E-02 actual Run은 아직 없다. AWS NOT_RUN, Spec 전체 미완료.
   - 검증 원장: Spec validation 최신 T088. T084 전체 회귀 799 PASS/구형 기대값 1 FAIL 후 해당 계약 scoped 11 PASS;
     WhyYou 수정 관련 184 PASS·ruff·타입 검사 PASS. 최종 전체 회귀 T091은 남아 있다.
   - 다음: T089 시간 예산 시험 → T090 보안 corpus → T091 전체 gate → T092 quickstart → T093/T094 추적성·조건부
     작업 확인 → T095 보안 스캔 → T096 최종 문서 수렴 → T097 두 번째 clean checkout/팀원 재현.
   - ID-004-30은 승인·구현·actual 검증 완료. ID-004-14(b) observer 확장과 D1-only child의 범용 retest 사유 문구
     한계는 기록되어 있다. 원본 bundle은 Git 전달 대상이 아니며 새 환경에서는 quickstart로 새 Run을 만든다.
   - 전달 시 두 현재 작업 브랜치를 pull하고 이 문서와 Spec validation/tasks/decisions를 읽는다. 실행 시점 source SHA와
     이후 문서 commit을 혼동하지 않는다. 연우 PC 한정 설정은 과거 인계 항목이며 현재 재현의 필수값이 아니다.

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
