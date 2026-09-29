# Spec 002 구현 결정 기록

## ID-002-01 — reporting 최종 실패를 제품 상태로 공개한다 (T083)

### 결정 근거

최초 `H03_DLQ_V2` Run `60b19e5a-6693-427b-bf87-039e45181cfc`에서 동일 Outbox 사건의
처리 시도 3회와 LocalStack DLQ 보존은 확인됐다. 그러나
`GET /v1/interview-sessions/{session_id}/report`는 계속 `queued`를 반환했다. 회사 화면은 이 API만
읽으므로 인프라 DLQ를 직접 보지 못하며, 담당자는 영구 실패와 아직 처리 중인 상태를 구분할 수 없다.

### 검토한 대안

1. **화면 또는 ControlProof가 DLQ를 직접 읽어 실패로 추정**
   - 채택하지 않는다. 회사 사용자에게 인프라 권한을 노출하고, 제품 API에는 여전히 실패 상태가 없어
     다른 클라이언트와 화면이 서로 다른 사실을 말하게 된다.
2. **빈 `Report(status=failed)`를 기존 `reports`에 저장**
   - 채택하지 않는다. `Report`는 AI 원본과 점수·근거의 불변 기록이다. 생성되지 않은 리포트를 원본처럼
     저장하면 리포트 불변성과 실패 이력을 섞고, 기존 조회 모델에 가짜 summary·model version을
     채워야 한다.
3. **별도 `report_generation_failures` terminal projection을 저장하고 API/UI가 읽음**
   - 채택한다. source event와 session에 연결된 최소 실패 사실만 별도 보존하고, 리포트가 없을 때 API가
     `failed`, `retryable=false`를 반환한다. 회사 화면은 polling을 중단하고 명시적 최종 실패를 표시한다.
     이후 redrive로 실제 리포트가 만들어지면 리포트 조회를 우선하므로 정상 결과가 표시되며, 실패
     이력은 사후 설명을 위해 남는다.

### 선택한 동작

- reporting worker가 설정된 마지막 source 처리 시도에서 retryable 오류를 받으면 transaction rollback
  뒤 terminal projection을 별도 transaction으로 upsert한다.
- 저장 필드는 `company_id`, `interview_session_id`, `source_event_id`, `last_delivery_attempt`, 안정된
  `error_code`, `failed_at`만 허용한다. 지원자 이름, 이메일, message body, receipt handle, raw exception은
  저장하지 않는다.
- API는 준비된 실제 report를 가장 먼저 반환한다. report가 없고 terminal projection이 있으면 HTTP 200과
  `{status: "failed", retryable: false, message: ...}`를 반환한다. 둘 다 없을 때만 기존 HTTP 202
  `queued`를 유지한다.
- 회사 화면은 `failed`를 terminal 상태로 취급해 재호출 timer를 만들지 않고, 리포트 생성 실패와 최종
  채용 결정을 진행할 수 없다는 안내를 표시한다.

### 대상 파일

- `backend/alembic/versions/integration/i_021_report_generation_failures.py`
- `backend/src/interview_evidence/reporting/domain/failure.py`
- `backend/src/interview_evidence/reporting/repositories/postgres.py`
- `backend/src/interview_evidence/reporting/application/failure_service.py`
- `backend/src/interview_evidence/shared/messaging/worker.py`
- `backend/src/interview_evidence/runtime/worker.py`
- `backend/src/interview_evidence/reporting/api/company_routes.py`
- `apps/company-console/src/app/routeAdapters.tsx`
- `backend/tests/integration/reporting/test_report_failure_visibility.py`
- `backend/tests/integration/test_worker_delivery.py`
- `apps/company-console/src/app/__tests__/reviewRoute.test.tsx`

### 완료 조건

- 마지막 처리 시도 전에는 failure projection이 생기지 않는다.
- 마지막 처리 시도에는 같은 session/source event의 projection이 한 건만 남는다.
- 제품 API와 회사 화면이 `queued`와 `failed`를 구분한다.
- 원본 FAIL bundle은 수정하지 않고, 구현 후 H-03 parent-linked retest에서 H03-A9를 다시 판정한다.

### 구현 결과

- WhyYou 개인 브랜치 `bosung/controlproof-h03-integration`의 커밋 `511ae9e`에 구현했다.
- `report_generation_failures` migration과 tenant-scoped repository를 추가하고, reporting worker가
  마지막 source 처리 시도에서만 sanitized terminal projection을 upsert하도록 연결했다.
- API는 실제 report를 우선하고, report가 없을 때 terminal projection이 있으면 `failed`와
  `retryable=false`를 반환한다. 회사 화면은 이를 terminal 상태로 표시하고 polling을 종료한다.
- worker·API·UI 단위/통합 검사와 migration ownership·head·downgrade·drift 검사를 통과했다.
- 이 구현만으로 H03-A9를 PASS로 간주하지 않는다. T085의 parent-linked actual-stack Run이 제품 API,
  화면, 운영자 locator를 다시 함께 관찰해야 한다.
