# Implementation Plan: E-01·E-02 점수 근거·평가 기준 보존 검증

**Branch**: `004-e01-e02-score-evidence`
**Date**: 2026-10-07
**Spec**: [spec.md](./spec.md)
**Status**: Plan 완료. 판단 보류 H-1~H-4는 2026-10-07 보성 결정으로 닫혔다(§Plan Decisions). 다음은 Tasks·Analyze.
구현·실제 Run 없음.

## Summary

Spec 004는 WhyYou 보고서 작업자가 (1) 잘못된 인용의 점수를 저장하지 않는지(E-01 우회), (2) 저장된 점수의 근거가
사라지면 조회에서 근거 부족으로 드러나는지(E-01 변경 주입), (3) 새 평가 기준 버전을 발행해도 과거 보고서의 점수·
입력·가중치·버전이 그대로이고 저장 입력으로 총점을 다시 계산할 수 있는지(E-02)를 실제 로컬 경계에서 판정한다.

ControlProof에는 두 실행 profile(`E01_CITATION_EVIDENCE_V1`, `E02_SCORING_FREEZE_V1`), scenario schema v4, 보고서 lane
seed, 보고서 기록·조회 projection, 자막 구간 제거·복원과 보조 deep probe, 제품 API 기준 버전 생성·발행, WhyYou 계산
규칙의 독립 사본, E01·E02 판정기, Spec 004 bundle profile을 추가한다. WhyYou에는 local/test 고정 모델 fixture
`spec004-report-v1`(인용 모드·기준별 점수·emission receipt)만 추가하며 별도 WhyYou 작업과 PR로 분리한다.

첫 목표는 WhyYou를 PASS로 만드는 것이 아니다. 코드상 예측 P1(조회 경로가 자막 구간을 읽지 않음)이 맞으면 E01-A3는
대상 결함 FAIL이며, 그 사실을 먼저 봉인한 뒤에만 승인된 최소 보완과 child Run으로 간다(§8).

## Technical Context

**Language/Version**: ControlProof와 WhyYou 모두 Python 3.12 이상
**Primary Dependencies**: Pydantic 2, PyYAML, HTTPX, SQLAlchemy 2, psycopg 3, boto3, pytest; WhyYou는 FastAPI와 local
worker
**Storage**: WhyYou local PostgreSQL·LocalStack, ControlProof 불변 file bundle
**Testing**: pytest 단위·계약·통합시험, Ruff; 구현 뒤 격리 샌드박스 진단과 local actual-stack Run
**Target Platform**: Windows Docker Desktop 또는 동등한 Docker 환경의 `LOCAL_EMULATED`; 실제 AWS는 `NOT_RUN`
**Project Type**: ControlProof CLI/검증 엔진 + 외부 WhyYou modular monolith/worker adapter
**Performance Goals**: preflight 뒤 각 Run 540초, bundle verify 60초, 합계 600초 이내
**Constraints**: 합성 데이터만, 외부 AI 호출 금지, WhyYou `main`·origin push 금지, 제품 코드 변경은 최초 FAIL 봉인과
승인 뒤에만, 변경 주입은 Run 소유 행에만
**Scale/Scope**: profile 2개, assertion 7개(E01 4, E02 3), 진단 관찰 1개, Evidence ID 10개, lane 6개(E-01 4, E-02 2)
**User Interface**: CLI·JSON·bundle만; 고객 웹 결과는 Spec 005
**Target Baseline**: WhyYou `bosung/controlproof-n02-integration` `eec8f706a6b8b3fb8d7c5193c7f349e9f9f93014`
(+ 인용 모드 fixture 개인 브랜치, Tasks에서 확정)

## Constitution Check

### Pre-design gate

| 원칙 | 확인 | 결과 |
|---|---|---|
| I. 판정은 증적에서만 | E01·E02 assertion마다 EV4와 raw projection 요구, 누락은 INCONCLUSIVE | PASS |
| II. 대상·준비·결과 분리 | 재계산 원본 drift·fixture 부재는 `RUNNER_NOT_READY`, fixture 출력 불일치는 실행기 결함 | PASS |
| III. 사람의 최종 결정 | 점수 임계값·채용 결정 기능 없음. 재계산은 산술 확인일 뿐 | PASS |
| IV. 시나리오/adapter 분리 | 모드·lane·assertion은 YAML, WhyYou 접점은 adapter와 capability map | PASS |
| V. 격리·결정론·복구 | 합성 lane, 결정론 fixture, 변경 주입은 Run 소유 행만, always-run 복구·teardown | PASS |
| VI. 불변 Run·재시험 | P1 FAIL도 봉인 뒤 child로만 재검증 | PASS |
| VII. 명세→증적 추적 | FR·E01/E02-A·EV4를 계약과 향후 Task에 연결 | PASS |

### Post-design re-check

위반 없음. WhyYou 쪽 변경은 local/test 대체 모델이며 운영 경로에서 활성화될 수 없다(기존 `validate_controlproof_
test_controls` 가드 유지). 자막 구간 직접 삭제와 deep probe 쓰기는 제품 흐름이 아니라 변경 주입·진단으로 명시하고
복구를 필수로 둔다.

## Source-derived Boundary Map

| 주장 | 실제 경계 | ControlProof 입력 | 관찰 |
|---|---|---|---|
| 잘못된 인용 비우기 (E01-A1·A2) | `ReportRequestedEventHandler` → `CriterionAssessor.assess` → `verified_against` → `save_report` | 기준 설명의 인용 모드 표식 + `report.generation_requested` | fixture emission receipt, `report_items.axis_assessments`, `evidence` 행 |
| 저장 뒤 노출 (E01-D1 진단) | `_report_from_row` → `_restored_axes` → `_report_view` | Run 소유 항목 JSON 직접 쓰기 | `GET .../report` |
| 근거 제거 노출 (E01-A3·A4) | `GET /v1/company/interview-sessions/{id}/report`(자막 구간 미조회), `.../timeline`(조회) | Run 소유 자막 구간 DELETE/INSERT | 두 조회 3회, 행 digest |
| 동결 (E02-A1·A2) | `ReportGenerator`가 버전 가중치를 항목에 복사, 작업자는 세션 스냅샷의 버전을 읽음 | 제품 API 버전 생성·발행, 버전에 묶인 lane seed | `reports`, `report_items`, 조회 응답 |
| 재계산 (E02-A3) | `scoring.aggregate`, `Report.criterion_aggregate`, `_scoring_inputs`, `_scoring_breakdown_view` | 없음(읽기만) | 저장 `overall_score`·`scoring_inputs`, 조회 `overall_score`·`scoring_breakdown` |

## Execution Design

### 1. Profile과 scenario

| 항목 | E-01 | E-02 |
|---|---|---|
| profile | `E01_CITATION_EVIDENCE_V1` | `E02_SCORING_FREEZE_V1` |
| scenario 파일 | `scenarios/E-01.yaml` | `scenarios/E-02.yaml` |
| schema | `controlproof.scenario.v4` | `controlproof.scenario.v4` |
| assertion | `E01-A1`~`E01-A4` | `E02-A1`~`E02-A3` |
| 진단 관찰 | `E01-D1` | 없음 |
| evidence | EV4-01·02·03·04·05·09·10 | EV4-01·02·04·06·07·08·09·10 |
| bundle profile | `controlproof.bundle-profile.spec004.v1` | 같음 |
| 고정 모델 fixture | `spec004-report-v1` | `spec004-report-v1` |
| 시간 정책 | poll 2, 안정화 3회·4초, restore 120, Run 540, verify 60 | 같음 |

`scenario.py`에 v4 분기를 추가한다. v1·v2·v3 검증과 `N02_CANONICAL_STEPS`는 바꾸지 않는다. `lanes` 필드는 profile별
lane enum(`E01LaneId`, `E02LaneId`)을 받도록 넓히고 profile이 허용하지 않는 lane을 거부한다. CLI 허용 표에 `E-01`,
`E-02`를 추가한다.

### 2. Lane과 subject

모든 lane은 독립 합성 지원자·초대·완료 세션을 가지며 보고서 요청 전에 제품 API로 동의를 커밋한다.

| Lane | 기준 버전 출처 | 기준 구성 | 실행 | 판정 |
|---|---|---|---|---|
| `E01_REFERENCE` | Run seed(직접) | 1개, `VALID` | 보고서 생성, 이후 불변 확인 | A1(참조 불변), 다른 지원자 ID 공급 |
| `E01_CITATION_MATRIX` | Run seed(참조 보고서 뒤) | 5개: `VALID`, `EMPTY`, `NONEXISTENT`, `OTHER_APPLICANT`, `OTHER_CRITERION`→`VALID` | 보고서 생성 | A1, A2 |
| `E01_EVIDENCE_REMOVAL` | Run seed(직접) | 2개, 둘 다 `VALID` | 보고서 생성 → 기준 1 근거 자막 구간 제거 → 조회 → 복원 → 조회 | A3, A4 |
| `E01_STORAGE_PROBE` | Run seed(직접) | 1개, `VALID` | 보고서 생성 → 축 JSON 직접 쓰기 4종 → 조회 → 원복 | D1(진단) |
| `E02_FIRST_APPLICANT` | 제품 API v1(생성·발행) | 2개, 가중치 v1, 축 가중치 v1 | 보고서 생성 → 변경 전 수집 → (v2 발행·두 번째 처리 뒤) 재수집 | A1, A2, A3 |
| `E02_SECOND_APPLICANT` | 제품 API v2(생성·발행 뒤 최신 발행 버전) | 2개, 가중치 v2, 축 가중치 v2 | 보고서 생성 | A2(전제), A3 |

E-01 lane은 서로 다른 Run 소유 직무·버전을 가져 기준 표식이 섞이지 않게 한다. E-02의 두 lane은 같은 Run 소유 직무를
공유해야 "같은 직무의 기준 변경"이 된다. 기준 설명 표식은 `[controlproof-spec004 mode=VALID score=71]` 형식으로 시작하고
나머지 설명은 합성 문구다(계약: [whyyou-spec004-fixture.md](./contracts/whyyou-spec004-fixture.md)).

### 3. E-01 실행 순서

1. preflight: 두 checkout clean·비 main, local endpoint, worker 증명, 고정 모델 `spec004-report-v1` health, observer root,
   재계산 원본 blob(E-02만), capability 전부.
2. scenario·target·environment·capability snapshot 고정.
3. `E01_REFERENCE`, `E01_EVIDENCE_REMOVAL`, `E01_STORAGE_PROBE`를 한 transaction으로 seed(실패 시 rollback·0건 확인).
4. 세 lane 동의 커밋(제품 API) → 보고서 요청 → 보고서 안정화 대기.
5. 참조 보고서의 Evidence ID를 읽어 `E01_CITATION_MATRIX`를 seed(기준 표식에 참조 ID·미존재 UUID 포함) → 동의 → 보고서.
6. matrix: emission receipt·저장 레코드 수집, 참조 lane 기록 재수집 → A1·A2 사실.
7. removal: 제거 전 조회(report·timeline)·기록 수집 → 기준 1 근거 자막 구간 DELETE(행 projection·digest 보존) →
   안정화 뒤 조회 → 같은 값 INSERT → 행 digest 확인 → 조회 → A3·A4 사실. 복원은 always-run.
8. storage probe: 원래 축 JSON digest 보존 → 네 종류 쓰기 → 조회 → 원래 JSON 복원·digest 확인(always-run) → D1 사실.
9. 판정·봉인·verify → teardown(always-run, Run 소유 행만).

### 4. E-02 실행 순서

1. preflight(E-01과 같음 + 재계산 원본 blob SHA 일치).
2. Run 소유 직무 seed, 두 lane의 지원자·초대는 아직 만들지 않는다.
3. 제품 API로 v1 생성(If-Match 없이 Idempotency-Key) → 발행(If-Match row_version) → 버전 목록 조회로 최신 발행 확인.
4. `E02_FIRST_APPLICANT`를 최신 발행 버전(v1)에 묶어 seed → 동의 → 보고서 → 변경 전 수집(저장 기록, 조회 응답,
   동결 입력, 재계산 1차).
5. 제품 API로 v2 생성·발행 → 변경 전·후 버전 스냅샷 수집. 이 단계가 변경 주입이며 복구는 teardown이다.
6. 최신 발행 버전을 다시 조회해 `E02_SECOND_APPLICANT`를 묶어 seed → 동의 → 보고서.
7. 첫 보고서 재수집(저장 기록·조회 응답) → 변경 전 projection과 비교, 두 번째 보고서의 버전·가중치 확인.
8. 두 보고서 각각 독립 재계산 → 세 비교 대상과 대조.
9. 판정·봉인·verify → teardown(always-run). Run 소유 직무에서 FK로 닿는 버전·기준·직무 요건·초대·세션·보고서만 제거하고
   같은 회사의 다른 직무 버전 digest가 Run 전과 같은지 확인한다.

### 5. 변경 주입과 복구

| 주입 | 적용 | 복구 | 안전 상태 증명 | 실패 시 |
|---|---|---|---|---|
| `EVIDENCE_SEGMENT_REMOVAL` | Run 소유 자막 구간 행 1개 DELETE | 같은 컬럼 값 INSERT | 행 projection digest가 제거 전과 같음 | `RESTORE_FAILED`, 차단 |
| `STORAGE_PROBE_WRITE` | Run 소유 항목 `axis_assessments` UPDATE | 원래 JSON UPDATE | 항목 projection digest가 쓰기 전과 같음 | `RESTORE_FAILED`, 차단 |
| `CRITERIA_VERSION_PUBLISH` | 제품 API 생성·발행 | teardown이 Run 소유 직무의 행 제거 | Run 소유 행 0건, 다른 직무 버전 digest 불변 | `RESTORE_FAILED`, 차단 |

변경 주입 기록은 `REQUESTED → APPLIED → RESTORING → RESTORED | RESTORE_FAILED` 생명주기를 가진다. Spec 003 ID-003-14
결정대로 복구 안전(`RESTORE_FAILED`)과 assertion 결과(A3/A4 FAIL)를 섞지 않는다. 복구 시간은 ID-003-19처럼 실제
복구 작업 시간만 restore 예산에 넣는다. 차단 파일·`cleanup-confirm`·retest 거부 규칙은 Spec 003과 같다.

### 6. 재계산 사본

`engine/judges/e02_scoring.py`는 다음을 그대로 옮긴다.

- `aggregate(entries)`: 점수 `None`은 분자·분모에서 제외, 가중치 `max(0, w)`, 합이 0이면 동일 가중치,
  `score = round(numerator / denominator)`(Python `round`), 분모 0이면 `None`.
- `weights_for(keys, weights)`: 없는 키는 1.0.
- 기준 점수: `config_version == "report-config-v2-communication-separated"`이면 `communication` 축을 뺀 축들로,
  아니면 모든 축으로 집계.
- 총점: 기준 점수를 `criterion_weight`로 집계. 의사소통 점수: `communication` 축 점수를 `criterion_weight`로 집계.

사본 상수: 원본 `backend/src/interview_evidence/reporting/domain/scoring.py` blob `61d1e615f90ff63a353f7d2062707700b94744a1`,
`backend/src/interview_evidence/reporting/domain/report.py` blob `814289681114479aeac7ea778fae78da4d35ac48`(WhyYou `eec8f70`).
preflight는 대상 checkout의 두 blob SHA를 읽어 다르면 `RUNNER_NOT_READY: SCORING_RULE_SOURCE_DRIFT`를 낸다.

비교: 정수 점수(`overall_score`, 기준 `score`, 응답 `average_score`)는 정확히 같아야 한다. 실수(`numerator`,
`denominator`, `weight`, `normalized_weight`, `contribution`)는 절대 오차 `1e-9` 이하. 사본의 단위 시험은 WhyYou
시험 벡터와 짝수 반올림 경계(x.5)를 포함한다.

### 7. 판정 규칙 요약

세부 규칙은 [scenario-profile-v4.md](./contracts/scenario-profile-v4.md)에 있다.

- E01-A1: 네 잘못된 모드 각각 emission receipt가 의도한 인용을 냈고, 저장 축이 `score=null`·인용 없음·비어 있지 않은
  `rationale`이며, 잘못된 ID가 그 기준 항목의 축 인용·Evidence 행에 없고(다른 항목·참조 보고서에 원래 있는 행은 제외),
  참조 lane 기록 digest가 불변이면 PASS. 점수나 잘못된 ID가 그 항목에 남으면 FAIL. receipt가 없거나 의도와 다르면
  INCONCLUSIVE(실행기 결함 후보).
- E01-A2: `VALID` 모드 축이 점수·인용을 갖고 인용 ID가 같은 항목의 Evidence 행이며 그 행의 기준·버전 ID가 항목과
  같으면 PASS.
- E01-A3: 제거 receipt(별도 연결의 행 부재 확인)로 제거가 실제로 일어났음을 확인한 뒤(타임라인 변화는 보조 증거),
  제거된 근거를 인용한 축·항목이 H-4 허용 지표 중 하나로 근거 부족을 드러내면 PASS. 지표가 없고 점수·인용이 제거 전과
  같거나, POST_REMOVAL 조회가 5xx거나, 근거를 인용하지 않은 항목이 바뀌면 FAIL. 제거가 확인되지 않으면 INCONCLUSIVE.
- E01-A4: 복원 행 digest가 같고 복원 뒤 보고서 projection이 제거 전과 같으면 PASS, digest는 같은데 조회가 다르면 FAIL.
  digest 불일치·복원 실패는 assertion이 아니라 `RESTORE_FAILED`다.
- E02-A1: 첫 보고서에 동결 입력 집합이 모두 있고 항목 가중치가 v1 값과 같으면 PASS.
- E02-A2: 두 번째 보고서가 v2 버전 ID·가중치이고(전제), 첫 보고서의 저장·조회 projection이 변경 전과 같으면 PASS.
  전제가 깨지면 INCONCLUSIVE.
- E02-A3: 두 보고서 모두 재계산이 세 비교 대상과 같으면 PASS.

### 8. P1(E01-A3 FAIL) 처리 순서

Spec 003 T080~T084와 같은 구조로 미리 고정한다.

1. **봉인**: 최초 E-01 Run을 그대로 봉인·verify하고 manifest SHA-256을 `validation.md`에 기록한다. 다시 돌려 덮어쓰지
   않는다.
2. **증거 확인**: 제거 receipt(행 부재 확인), 제거 전·후 타임라인 차이, 제거 전·후 보고서 projection, 복원 결과.
3. **원인 분류** (`implementation-decisions.md` ID-004-xx):
   - 제거가 일어나지 않았거나 다른 행을 지웠으면 `RUNNER_OR_OBSERVER_DEFECT` → 실행기 실패 시험 → 최소 수정 → 회귀.
   - 복원이 실패했으면 `RESTORE_OPERATOR_DEFECT`(Run은 `RESTORE_FAILED`·차단, Spec 003 차단 절차).
   - 제거가 확인됐고 보고서 응답이 그대로면 `TARGET_CONTROL_DEFECT`.
4. **WhyYou 최소 수정 결정**: 대상 결함이면 수정 범위를 `PROPOSED`로 기록하고 보성 승인을 받는다. 후보는 보고서 읽기
   경로가 인용 Evidence의 자막 구간 존재를 확인해 응답에 근거 부족을 드러내는 것(예: Evidence 항목의 가용성 표시와 해당
   축·항목 점수의 근거 부족 처리)이며, 판정 지표는 §7·계약의 허용 목록 안에서 고른다. 허용 목록 밖 표현이 필요하면
   scenario version을 올리고 계약을 먼저 고친다.
5. **구현**: WhyYou `eec8f70`(또는 그때의 기준 브랜치 HEAD)에서 `yeonwoo/controlproof-e01-e02-…` 개인 브랜치를 따고
   실패 시험(RED) → 최소 수정 → WhyYou 관련 단위 시험 → fork push → PR. 인용 모드 fixture PR과 섞지 않는다.
6. **child**: preflight READY와 사용자 승인 뒤 `retest <e01-parent-run-id>`로 child를 만들고 parent manifest 불변을
   확인한다. A3 PASS와 A4 복원 동등성을 다시 본다.

E02 또는 다른 E01 assertion의 FAIL도 같은 순서를 따른다.

## WhyYou Local/Test Change (별도 작업·PR)

- 파일: `backend/src/interview_evidence/runtime/controlproof_model_substitute.py`,
  `backend/tests/unit/runtime/test_controlproof_model_substitute.py`
- 추가: fixture ID `spec004-report-v1`(digest = SHA-256 of `controlproof:spec004-report-v1`), 기준 설명 표식 파서, 다섯
  인용 모드, 기준별 점수(H-2), 같은 처리 호출 범위의 앞 기준 Evidence 기억(H-3, 세션·지원자를 넘지 않음), emission
  receipt. 다른 지원자 Evidence ID는 fixture가 기억하지 않고 실행기가 표식 인자로 넣는다.
- 표식이 없으면 `h03-report-v1`과 같은 출력(첫 Evidence, 72)을 낸다.
- 유지: local/test 밖 기동 거부, 외부 AI 차단 digest, `h03-report-v1` 동작·digest 불변. 제품 코드는 바꾸지 않는다.
- 분기: `eec8f70`에서 `yeonwoo/controlproof-e01-e02-fixture`, remote `fork` push, PR base
  `bosung/controlproof-n02-integration`. origin·main push 금지.
- 시험: 모드별 단위 시험 RED → 구현 → GREEN, 기존 `h03-report-v1` 시험 불변, `ruff check`.

## Adapter and Judge Design

`AdapterSet`에 additive protocol을 추가한다. adapter는 raw fact만 반환한다.

| Protocol | 책임 | 재사용 |
|---|---|---|
| `Spec004SeedAdapter` | lane seed(직무·초대·세션·turn·질문 근거·자막 구간·자산), E-01 직접 버전 seed, teardown | `n02_seed.py`의 `_insert_row`, FK 카탈로그 teardown(ID-003-12) |
| `ConsentAdapter` | 정책 조회·동의 커밋·상태 읽기 | Spec 003 그대로 |
| `ReportRequestAdapter` | `report.generation_requested` outbox 투입, 처리 receipt 읽기 | `protected_processing.py` 평가 경로 |
| `ReportRecordAdapter` | `reports`·`report_items`·`evidence`·`transcript_segments` allowlist projection, 회사 보고서·타임라인 조회 | `client.py` 회사 토큰 |
| `EvidenceMutationAdapter` | 자막 구간 DELETE/INSERT, 축 JSON 쓰기/원복, digest 확인 | 신규 |
| `CriteriaVersionAdapter` | 제품 API 버전 생성·발행·목록, 버전 스냅샷 | 신규(회사 토큰) |
| `ModelEmissionAdapter` | fixture emission receipt 읽기 | observer root 읽기 패턴 |
| `ScoringSourceAdapter` | 대상 checkout의 scoring 원본 blob SHA 읽기 | `client.py` git 읽기 |

판정기: `engine/judges/e01.py`, `engine/judges/e02.py`, 사본 `engine/judges/e02_scoring.py`. 실행기:
`engine/executors/e01.py`, `engine/executors/e02.py`, 공통 lane·안정화·보고서 대기는 `engine/executors/report_lanes.py`.
안정화 읽기는 Spec 003 `_StableReads`를 재사용한다.

## Evidence and Bundle

`controlproof.bundle.v1` manifest·SHA-256·redaction·immutable retest 계약을 유지하고
`profile_contract=controlproof.bundle-profile.spec004.v1`을 추가한다. 파일과 EV4 대응은
[evidence-bundle-v4.md](./contracts/evidence-bundle-v4.md)에 있다. 보고서 요약·관찰·사유·질문·답변 원문은 저장하지
않고 SHA-256과 길이만 저장한다.

## Spec 003 재사용과 신규 범위

| 구분 | 재사용 | 신규 |
|---|---|---|
| 준비 | preflight 골격, 소스 clean·비 main, local endpoint, 작업자 증명, 외부 AI 차단 | fixture ID 확인, 재계산 원본 blob, Spec 004 capability |
| seed | `_insert_row`, FK 카탈로그 teardown, 합성 정책 | 보고서 lane(다기준 turn·질문 근거·자막 구간), 기준 표식, 제품 API 버전 |
| 처리 | 동의 adapter, 평가 경로 outbox 투입, 처리 receipt, 안정화 읽기 | 보고서 안정화 조건 |
| 변경 주입 | 생명주기·차단·`cleanup-confirm`·restore 예산 규칙 | 자막 구간 제거·복원, 축 JSON 쓰기·원복, 버전 발행 |
| 판정 | 공통 verdict 우선순위, 사유 코드 모델 | E01·E02 판정기, 재계산 사본 |
| 증적 | manifest·redaction·retest diff | Spec 004 파일·교차 참조 |
| CLI | 명령·exit code·envelope | profile 2개, projection 필드 |

## Test Strategy

### ControlProof 자동 gate

- model: profile·lane enum·변경 주입 생명주기·재계산 기록 검증
- scenario contract: v4 분기, profile별 assertion·evidence·lane·step canonical 집합, v1~v3 회귀
- adapter contract: seed rollback, 기준 표식 생성, 제품 API 버전 생성·발행(If-Match·422), 자막 구간 DELETE/INSERT와
  digest, 축 JSON 원복, emission receipt 읽기, redaction
- judge fixture: E01 모드별 PASS·FAIL·INCONCLUSIVE, A3 지표별 PASS와 P1 FAIL, E02 전제 실패, 재계산 불일치
- 재계산 사본: WhyYou 시험 벡터, 0 가중치 합, 없는 축 키, 의사소통 분리, x.5 짝수 반올림
- integration: fake 대상 위 E-01·E-02 Run 끝까지, 복구 실패 → `RESTORE_FAILED`·차단, parent-child 불변
- regression: Spec 001·002·003 전체(`pytest -q`), Ruff

### WhyYou 자동 gate

- `test_controlproof_model_substitute.py`: 다섯 모드·기준별 점수·표식 없음 = h03 동작·emission receipt·local/test 밖 거부
- 기존 reporting 단위 시험(`test_criterion_assessment.py` 등) 불변

### 격리 샌드박스 진단 (공식 Run 전)

Spec 003 ID-003-18 환경(PostgreSQL 16+pgvector, moto S3/SQS, WhyYou API·작업자, AI 엔드포인트 loopback, 새 fixture)에서
[research.md](./research.md)의 SD-1~SD-5를 실행한다. 진단 Run은 공식 결과가 아니며 `validation.md`에 진단으로만
기록한다. 실행기 결함이 나오면 실패 시험 → 최소 수정 → 회귀 순서로 고친다. WhyYou 제품 결함 후보(P1)는 고치지 않고
공식 Run에서 처음 봉인한다.

### Actual-stack gate

1. 두 저장소 clean·비 main, preflight READY(사용자 승인)
2. 최초 E-01 Run, 최초 E-02 Run
3. 각 bundle verify와 복구 SUCCEEDED
4. FAIL이면 §8 순서
5. A1~A4·A1~A3, EV4, 한계 표시 확인
6. 부모·child manifest 불변·계보 확인

## Risks and Responses

| 위험 | 대응 |
|---|---|
| 인용 모드 fixture 결함이 대상 결함처럼 보임 | emission receipt를 봉인하고 의도와 다르면 실행기 결함 |
| 앞 기준 Evidence 기억이 프로세스 재시작·재전달에 의존 | 기억은 같은 처리 호출 범위로 한정, 없으면 receipt에 `MODE_SOURCE_MISSING`, 그 사례는 INCONCLUSIVE |
| 보고서 생성이 job requirement 평가·임베딩 때문에 늦거나 실패 | Spec 003 fixture와 같은 요건 수, fixed embedder, 안정화 대기, 실패는 전제 실패 |
| 제품 API 버전 생성의 검증(가중치 합 100, 요건 1개 이상, 30분 고정) | 계약에 body 고정, 422는 `RUNNER_NOT_READY`가 아닌 Run 전제 실패로 기록 |
| 같은 회사의 다른 직무 오염 | Run 소유 직무만 사용, teardown 전후 다른 직무 버전 digest 비교 |
| 자막 구간 재삽입이 원래와 다른 값 | 삭제 전 전체 컬럼 projection을 봉인하고 digest로 확인, 다르면 `RESTORE_FAILED` |
| WhyYou scoring 원본 변경으로 사본이 낡음 | blob SHA 고정, 다르면 `RUNNER_NOT_READY` |
| 다른 scenario(H-03·N-02)와 fixture ID 충돌 | 프로세스별 fixture는 하나, quickstart에 재기동 절차, preflight가 fixture ID를 확인 |
| P1 FAIL 뒤 서둘러 수정 | §8 순서와 Constitution VI, 봉인 전 수정 금지 |

## Plan Decisions (2026-10-07, 보성 결정)

| ID | 질문 | 결정 | 반영 위치 |
|---|---|---|---|
| H-1 | E-02 두 번째 지원자를 어떻게 새 버전에 묶나 | (a) v2 발행 뒤 제품 API(`GET .../competency-model-versions`)로 읽은 최신 발행 버전에 seed로 묶는다. 제품 초대 API는 쓰지 않는다 | §4, adapter 계약 `latest_published` |
| H-2 | fixture가 기준별 점수를 줄지 | (a) 표식 `score=NN`으로 기준별 점수를 다르게 준다. 값은 아래 표처럼 x.5 짝수 반올림이 두 방향으로 실측되게 고른다 | §2·§6, fixture 계약 |
| H-3 | 타 기준 인용 모드를 어떻게 만드나 | (a) 같은 처리 호출 안에서 앞 기준에 받은 Evidence ID를 기억하는 모드를 local/test 대체물 안에만 둔다. 기억은 세션·지원자를 넘지 않는다. **다른 지원자 Evidence ID는 fixture 기억으로 만들지 않고** 실행기가 다른 lane의 실제 Evidence ID를 표식 인자로 넣는다 | fixture 계약 OTHER_CRITERION memory |
| H-4 | E01-A3 PASS 지표 | (a) 허용 목록을 지금 고정한다: 축 `score=null`, 항목 `average_score=null`, 항목 상태 `insufficient_evidence`·`needs_follow_up`, Evidence 가용성 필드(`playable`·`available`·`transcript_available`)=false. 네 표현 모두 PASS 지표다. 대상 수정이 이 밖의 표현을 쓰면 그때 scenario version을 올린다 | scenario 계약 E01-A3 |

### E-02 점수 표식 값 (H-2)

| 버전 | 기준 A (score, weight) | 기준 B (score, weight) | numerator | 총점 `round` | 반올림 방향 |
|---|---|---|---|---|---|
| v1 | 72, 50 | 73, 50 | 0.5·72 + 0.5·73 = 72.5 | 72 | 짝수로 내림(half-up이면 73) |
| v2 | 72, 25 | 74, 75 | 0.25·72 + 0.75·74 = 73.5 | 74 | 짝수로 올림 |

모든 축에 같은 점수를 주므로 기준 점수는 표식 값과 같고, 정규화 가중치(0.5·0.25·0.75)와 곱이 이진 부동소수에서 정확해
경계값이 흔들리지 않는다. 축 가중치는 v1 균등(각 20), v2 비균등(합 100)으로 둔다. 의사소통 점수도 같은 기준 가중치로
집계되므로 v1 72, v2 74가 된다.

## Project Structure

### Documentation

```text
specs/004-e01-e02-score-evidence/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    ├── scenario-profile-v4.md
    ├── evidence-bundle-v4.md
    ├── controlproof-cli-v4.md
    ├── whyyou-spec004-adapter.md
    └── whyyou-spec004-fixture.md
```

Tasks 단계에서 `tasks.md`, 구현 중 `validation.md`, `traceability.md`, `implementation-decisions.md`를 만든다.

### ControlProof

```text
engine/
├── cli.py                      # E-01/E-02 profile 선택·projection
├── models.py                   # profile, lane enum, 변경 주입·재계산 기록
├── scenario.py                 # scenario v4 검증
├── evidence.py                 # Spec 004 bundle profile·교차 참조
├── presentation.py             # 모드·제거·재계산 설명, 한계 표시
├── config.py                   # fixture ID·observer root·scoring blob pin 설정
├── runner.py                   # profile policy·executor 등록
├── judge.py                    # E01·E02 판정기 등록
├── execution.py                # Spec 004 차단·cleanup-confirm 주체(필요한 곳만)
├── retest.py                   # E-01/E-02 child 계보
├── executors/
│   ├── report_lanes.py         # 공통 lane·보고서 대기
│   ├── e01.py
│   └── e02.py
├── judges/
│   ├── e01.py
│   ├── e02.py
│   └── e02_scoring.py          # WhyYou 계산 규칙 사본
└── adapters/whyyou/
    ├── spec004_seed.py
    ├── report_records.py
    ├── evidence_mutation.py
    ├── criteria_versions.py
    └── model_emission.py

seeds/
└── spec004_subjects.py

scenarios/
├── E-01.yaml
└── E-02.yaml

tests/
├── unit/                       # 사본·판정기·모델
├── contract/                   # profile·adapter·CLI·bundle
└── integration/                # fake 대상 E-01/E-02 Run, 복구 실패, retest
```

### WhyYou personal branch (local/test only)

```text
backend/src/interview_evidence/runtime/controlproof_model_substitute.py
backend/tests/unit/runtime/test_controlproof_model_substitute.py
```

**Structure Decision**: 두 저장소와 기존 엔진을 유지한다. E-01·E-02 orchestration·판정은 새 모듈로 분리하고
`runner.py`에는 profile 등록만 둔다. WhyYou 변경은 local/test 대체 모델 파일 하나와 그 시험뿐이다.

## Compatibility and Migration

- WhyYou DB migration·제품 코드 변경 없음. ControlProof는 기존 행을 allowlist projection으로 읽는다.
- scenario v1/v2/v3, bundle profile Spec 001/002/003, 기존 봉인 bundle은 그대로 읽고 검증한다.
- `.env.example`에 Spec 004 설정(fixture ID 등)을 additive하게 추가하고 실제 secret은 넣지 않는다.
- WhyYou `h03-report-v1` 동작과 digest를 바꾸지 않는다.

## Complexity Tracking

Constitution 위반 예외는 없다. E-01 lane이 4개인 이유는 참조 지원자(타 지원자 ID 공급과 불변 확인), 인용 모드
matrix, 근거 제거, 진단 쓰기가 서로의 보고서를 오염시키지 않게 하기 위해서다.

## Phase Gate

Plan 산출물(plan, research, data-model, contracts, quickstart)을 작성했고 H-1~H-4 결정을 반영했다. Tasks(`tasks.md`,
T001~T097)와 Analyze(`checklists/analysis.md`: CRITICAL 0, HIGH 4·MEDIUM 5 모두 수정)를 2026-10-07에 마쳤다. 다음 단계는
`$speckit-implement`이며 Phase 1(T001)부터 시작한다. Tasks에서 WhyYou fixture 작업을 ControlProof 작업과 분리한다. Analyze에서 CRITICAL·HIGH와
해석 차이를 만드는 MEDIUM이 0건일 때만 구현한다.
