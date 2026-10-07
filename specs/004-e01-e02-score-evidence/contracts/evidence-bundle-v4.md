# Contract: Evidence Bundle Profile for Spec 004

## Compatibility

canonical bundle schema는 `controlproof.bundle.v1`을 유지하고 E-01·E-02 manifest에 profile contract를 추가한다.

```text
controlproof.bundle-profile.spec004.v1
```

Spec 001·002·003 bundle은 새 파일 없이 기존 contract로 계속 verify된다.

## Required canonical files

기존 Run/scenario/target/environment/observations/assertions/judgement/manifest 파일에 다음을 추가한다.

| 파일 | E-01 | E-02 | 내용 |
|---|---|---|---|
| `spec004-capabilities.json` | 필수 | 필수 | capability map, fixture ID·digest, 외부 AI 차단 digest |
| `spec004-lanes.json` | 필수 | 필수 | lane·subject·기준 표식(모드·인자·점수)·fixture digest |
| `citation-cases.jsonl` | 필수 | - | CitationCase |
| `model-emissions.jsonl` | 필수 | - | ModelEmissionReceipt. E-02는 `model.emission.read` capability가 없고 점수는 저장 축에서 확인한다 |
| `report-records.jsonl` | 필수 | 필수 | ReportRecordSnapshot 단계별 |
| `report-reads.jsonl` | 필수 | 필수 | ReportReadSnapshot 단계별 |
| `storage-probe.json` | 필수 | - | StorageProbeRecord(E01-D1) |
| `criteria-versions.json` | - | 필수 | CriteriaVersionSnapshot V1·V2, 다른 직무 digest |
| `frozen-inputs.json` | - | 필수 | FrozenInputSet 두 개 |
| `recompute.json` | - | 필수 | RecomputeRecord 두 개, 사본 ID·원본 blob |
| `change-injections.jsonl` | 필수 | 필수 | ChangeInjection 생명주기 |
| `recovery.json` | 필수 | 필수 | 복구 안전 사실, restore timing, teardown 결과 |

retest child에는 기존 `retest-diff.json`도 필수다.

## Evidence mapping

| EV4 | Required source |
|---|---|
| EV4-01 | `spec004-capabilities.json` + environment/scenario/target snapshot (+ E-02 `recompute.json`의 `target_source_blob_shas`) |
| EV4-02 | `spec004-lanes.json` |
| EV4-03 | `citation-cases.jsonl` + `model-emissions.jsonl` |
| EV4-04 | `report-records.jsonl` (+ E-01 `storage-probe.json`, E01-D1 진단의 쓰기 전·후 기록) |
| EV4-05 | `report-reads.jsonl`의 PRE_REMOVAL·POST_REMOVAL·POST_RESTORE (E-01) |
| EV4-06 | `criteria-versions.json` |
| EV4-07 | `frozen-inputs.json` + `report-reads.jsonl`의 PRE_CHANGE·POST_CHANGE |
| EV4-08 | `recompute.json` |
| EV4-09 | `change-injections.jsonl` + `recovery.json` |
| EV4-10 | assertion results + judgement + manifest, child면 retest diff |

한 파일이 여러 EV4를 충족할 수 있으나 manifest reference는 각 EV4에서 독립적으로 검증한다.

## Cross-reference rules

- 모든 lane/subject reference는 `spec004-lanes.json`에 있어야 한다.
- CitationCase의 `emission_receipt_id`는 `model-emissions.jsonl`에 있고 같은 `criterion_id`를 가져야 한다.
- E01-A1 PASS는 네 모드 모두 receipt가 의도와 같고 저장 축이 비었으며 참조 lane digest가 불변임을 파일에서 다시 계산해
  확인한다. 요약 boolean만으로 PASS를 복원하지 않는다.
- E01-A3·A4의 조회 snapshot은 같은 injection ID의 적용 receipt와 복원 receipt 사이·이후에 수집돼야 한다(phase와
  `captured_at` 순서).
- 자막 구간 복원은 `post_restore_digest == pre_projection_digest`가 파일에 있어야 한다.
- E02-A2 PASS는 PRE_CHANGE·POST_CHANGE projection digest를 파일에서 다시 계산해 같아야 하고, 두 번째 보고서의 버전 ID가
  V2 스냅샷과 같아야 한다.
- E02-A3 PASS는 verify가 `recompute.json`의 입력으로 사본을 다시 실행해 `computed`와 같은지 확인한다. 사본 ID가 다르면
  verify 실패.
- `RecomputeRecord.comparison_policy=CRITERION_ID_V2`이면 `scoring_inputs.criteria`와 API 기여 목록을 기준 ID로
  대응해 비교한다. 중복·누락·다른 기준 ID·필드·수치 차이는 거부하고 정수 정확성·실수 `1e-9` 허용차는 유지한다.
  필드가 없는 과거 기록은 `POSITIONAL_V1`(순서 비교)로 검증한다. 알 수 없는 정책은 verify 실패이며 과거 파일은 고치지 않는다.
- `recovery.json`은 Spec 003 ID-003-19처럼 `restore_timing`(예산과 실제 복구 작업 누적 시간)을 가진다.

## Integrity

모든 artifact는 상대 경로, SHA-256, byte size, MIME type, capture time, redaction profile을 가진다. 봉인 뒤 파일 추가·
삭제·변경은 verify 실패다. parent bundle의 manifest digest는 child retest 전후에 같아야 한다.

## Redaction

검출 시 verify 실패:

- bearer/cookie/password/access key, presigned query credential, Idempotency-Key 원값
- 지원자 이름·이메일, 질문·답변·자막 원문
- 보고서 요약·관찰·사유·불확실성·후속 질문 원문, 기준 설명 본문, 모델 prompt
- 개인 절대 경로

허용:

- 합성 UUID, 상태, 점수, 가중치, 산술 값, 버전 문자열, 상태 코드, SHA-256, 길이
- 기준 표식의 모드 이름·인자 UUID·점수
- repo-relative source locator와 blob SHA
- sanitized local endpoint host, environment kind

## Conflict rules

phase에 따른 값 변화(PRE→POST)는 충돌이 아니다. 같은 Run/lane/phase의 같은 사실을 DB projection과 API projection이
모순되게 표현할 때(예: 같은 축 점수가 다름)만 `EVIDENCE_CONFLICT`다. 단 E01-A3의 DB(Evidence 행 존재)와 API(근거 부족
지표) 차이는 설계상 서로 다른 사실이며 충돌이 아니다.

## Verification result

verify는 최소 다음을 반환한다: 확인한 파일 수, 확인한 EV4 집합, missing/mismatched/unregistered 파일, 끊긴 lane·case·
injection·recompute 참조, 재계산 재실행 결과, redaction 위반, bundle status. required fact를 읽을 수 없으면 hash가 맞더라도
assertion PASS를 복원하지 않는다.
