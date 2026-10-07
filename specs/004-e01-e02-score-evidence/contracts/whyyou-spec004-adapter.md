# Contract: WhyYou Adapter for E-01·E-02

**Target**: WhyYou local/test, 기준 `bosung/controlproof-n02-integration` `eec8f70` + 인용 모드 fixture 개인 브랜치
**Adapter ID**: `whyyou-local-spec004-v1`
**Base**: Spec 001~003 WhyYou adapter contracts

## Boundary

adapter는 WhyYou HTTP, PostgreSQL, observer root receipt를 최소 raw fact로 정규화하고 verdict를 정하지 않는다. 전체 DB
dump, 전체 로그, token, cookie, presigned/playback URL, PII, 질문·답변·자막·보고서 원문을 반환하지 않는다. 변경 주입은
Run 소유 행에만 한다.

## Spec004SeedAdapter

### `seed_lanes(run_id, lanes)`

한 transaction으로 lane마다 다음을 만든다. 실패하면 rollback하고 Run 소유 행 0건을 확인한다.

- Run 소유 직무(`status=active`, 기본 제출 요건 사본 — ID-003-09·15 규칙)
- E-01 lane: 역량 모델 버전(`published`, `published_at`, `interview_level=junior`, 유효 verification guide)과 기준
  (code, name, 표식이 맨 앞에 있는 description, weight 합 100), 직무 요건 1개
- 초대(`identity_verified`, 그 lane의 버전 ID), 지원자 프로필(합성 표식)
- 완료 면접 세션(같은 버전 ID), 기준마다 면접관 질문 turn·지원자 최종 turn·질문 근거(`target_criterion_id`)·자막 구간
  (turn 범위 안 시작/끝), 최종 녹화 자산(`final_video`, 누락 구간 없음)
- 동의·보고서·보고서 요청은 만들지 않는다

반환: lane별 ID 집합, 기준 ID·표식, `fixture_digest`. E-02 lane은 직무를 공유하고 버전은 seed하지 않는다
(`competency_model_version_id`는 호출자가 넘긴 최신 발행 버전).

### `seed_lane_after(run_id, lane, competency_model_version_id | marker_arguments)`

참조 보고서 뒤 `E01_CITATION_MATRIX`, v2 발행 뒤 `E02_SECOND_APPLICANT`를 같은 규칙으로 seed한다.

### `teardown_lanes(run_id)`

Spec 003 ID-003-12의 FK 카탈로그 방식으로 Run 소유 seed 행과 그 행에서 FK로 닿는 행(동의·상태 이력·보고서·항목·
Evidence·제품 API로 만든 버전·기준·직무 요건)만 자식부터 제거한다. 회사·회사 사용자는 시작점이 아니다. FK가 없는
outbox 사건은 합성 잔여로 남기고 ID를 기록한다. 제거 뒤 Run 소유 행 0건과 다른 직무 버전 digest 불변을 반환한다.

## ConsentAdapter

Spec 003 그대로(`read_policy`, `commit`, `read_state`). 모든 purpose를 커밋해 `ai_assessment`를 포함한다.

## ReportRequestAdapter

### `request_report(subject)`

Spec 003 평가 경로처럼 현재 회사·세션에 한정한 `report.generation_requested` outbox 사건을 결정론적 event ID·trace로
넣는다. 반환: event ID, 제출 시각.

### `read_processing(subject)`

observer receipt(`REPORT_HANDLER_ENTERED`, `REPORT_ASSESSMENT_STARTED`, `REPORT_ASSESSMENT_REFUSED`)와 보고서 존재를
안정화 읽기로 반환한다. 거부 receipt는 동의 전제 실패이며 E-01·E-02 판정이 아니다.

## ReportRecordAdapter

### `read_records(subject, phase)`

allowlist query(현재 회사·Run 소유 세션 한정):

- `reports`: report_id, version, kind, model/prompt/config_version, status, overall_score, scoring_inputs,
  summary SHA-256·길이, created_at
- `report_items`: report_item_id, criterion_id, competency_model_version_id, assessment_state, criterion_weight,
  axis_weights, axis_assessments(축·점수·인용, rationale은 SHA-256과 고정 사유 문구 일치 여부), 텍스트 필드 SHA-256
- `evidence`: evidence_id, report_item_id, criterion_id, competency_model_version_id, answer_turn_id,
  transcript_segment_id, video_start_ms/end_ms, sufficiency, generation_version, 텍스트 SHA-256
- `transcript_segments`: transcript_segment_id, turn_id, version, session_start_ms/end_ms, speaker, confidence,
  corrected_by 유무, text SHA-256·길이, 전체 컬럼 `row_digest`

조회 성공+0건은 ABSENT, query 실패는 UNAVAILABLE.

### `read_report_api(subject, phase)` / `read_timeline_api(subject, phase)`

회사 토큰으로 `GET /v1/interview-sessions/{session_id}/report`, `.../timeline`을 호출하고 data-model §7
projection을 만든다. 계약에 없는 응답 필드는 이름만 `unknown_fields`에 넣는다. playback URL은 상태만 남긴다.

## EvidenceMutationAdapter

### `remove_segment(subject, transcript_segment_id)`

1. 행이 이 lane의 Run 소유 자막 구간인지, 다른 Evidence가 다른 lane에서 같은 행을 가리키지 않는지 확인한다.
2. 전체 컬럼 값을 프로세스 메모리에 보존하고 `pre_projection_digest`를 만든다(원문 본문은 bundle에 넣지 않음).
3. `DELETE ... WHERE company_id = :company AND transcript_segment_id = :id` → 영향 행 1을 확인 → 별도 연결로 부재 확인.

### `restore_segment(subject, injection_id)`

보존한 값으로 INSERT → 별도 연결로 `row_digest == pre_projection_digest` 확인. 실패·불일치는 `RESTORE_FAILED`.

### `write_probe_axes(subject, report_item_id, axes)` / `restore_probe_axes(subject, injection_id)`

Run 소유 항목의 `axis_assessments` JSON만 UPDATE하고 원래 JSON digest로 되돌림을 확인한다. 다른 열은 바꾸지 않는다.

## CriteriaVersionAdapter

회사 토큰 사용.

### `create_version(position_id, body, idempotency_key)`

`POST /v1/positions/{position_id}/competency-model-versions`(`Idempotency-Key`). body 고정 항목: `job_requirements` 1개 이상,
`criteria`(code, name, description(표식 포함), weight 합 100, verification_guide, required 등 대상 스키마 필수 필드),
`prohibited_topics=[]`, `interview_duration_minutes=30`, `interview_level=junior`, `axis_weights`(비우거나 다섯 축 합 100).
201이면 버전 ID·row_version을, 422면 sanitized detail 코드를 반환한다.

### `publish_version(version_id, row_version, idempotency_key)`

`POST /v1/competency-model-versions/{version_id}/publish`, `If-Match-Version`에 row_version. 200이면 status·
published_at을 반환한다.

### `read_versions(position_id)` / `latest_published(position_id)`

`GET /v1/positions/{position_id}/competency-model-versions`에서 data-model §9 projection(버전 view에 criterion ID가 없어 기준 ID는 DB 읽기 전용 조회)과, `status=published` 중
`version_number` 최대인 버전을 반환한다(WhyYou 초대 규칙과 같은 선택).

### `other_positions_digest(company)`

같은 회사의 Run 소유가 아닌 직무들의 버전·기준 projection digest(읽기 전용 DB).

## ModelEmissionAdapter

`read_emissions(run_id, criterion_ids)`: observer root의 `model/` 아래 `controlproof.spec004-model-emission.v1` receipt를
criterion ID로 필터해 반환한다. 다른 Run의 receipt는 무시한다. 형식 위반은 `UNAVAILABLE`.

## ScoringSourceAdapter

`read_blob_shas()`: WhyYou checkout에서 `git rev-parse HEAD:backend/src/interview_evidence/reporting/domain/scoring.py`,
`...report.py`를 읽어 반환한다. checkout이 dirty면 Spec 003 source gate가 먼저 막는다.

## Readiness

READY 전에 다음을 모두 확인한다.

1. 두 checkout identity·clean, WhyYou는 `main`/`master`가 아님
2. API·DB endpoint가 local allowlist, `APP_ENVIRONMENT` local/test
3. 외부 AI 차단, health의 fixture ID가 `spec004-report-v1`이고 digest가 scenario와 같음
4. observer root가 API·작업자·ControlProof에서 같음, emission receipt 디렉터리 쓰기 가능
5. 작업자 증명(Spec 003 attestation), report 작업자 동작
6. 회사 토큰으로 `/v1/me`와 버전 목록 조회 가능(E-02)
7. scoring 원본 blob SHA 일치(E-02)
8. 차단 파일 없음
9. profile capability 전부 존재

## Error mapping

| Condition | Mapping |
|---|---|
| fixture가 다름, observer root 불일치, blob drift | `RUNNER_NOT_READY` |
| DB/API 접근 불가(Run 전) | `ACCESS_BLOCKED` |
| Run 중 source 접근 상실 | `INCONCLUSIVE: ACCESS_LIMITED` |
| 동의 거부 receipt로 보고서 미생성 | `INCONCLUSIVE: PRECONDITION_NOT_MET` |
| 버전 생성·발행 422/409 | `INCONCLUSIVE: PRECONDITION_NOT_MET`(detail 코드 기록) |
| emission이 의도와 다름 | 해당 사례 `INCONCLUSIVE: FIXTURE_EMISSION_MISMATCH` |
| 저장 레코드에 잘못된 인용·점수 | E01-A1 FAIL 후보 |
| 제거 확인 뒤 보고서 조회가 지표 없이 같음 | E01-A3 FAIL 후보 |
| 복원 digest 불일치·복원 불가 | `RESTORE_FAILED`, INCONCLUSIVE, 차단 |

모든 non-READY 결과는 비어 있지 않은 `operator_action`을 반환하고 secret을 출력하지 않는다.

## Conditional product remediation

adapter는 근거 부족 표시를 구현하지 않는다. E01-A3가 대상 결함으로 봉인·분류·승인된 뒤 WhyYou 보고서 읽기 경로를
보완해도 이 계약과 lane·injection ID는 그대로이며, parent/child 비교에서 바뀌는 것은 target snapshot과 조회 결과다.
