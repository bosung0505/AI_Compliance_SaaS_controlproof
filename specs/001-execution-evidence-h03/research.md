# Phase 0 Research: H-03 실행·증적 수직 흐름

**Feature**: `001-execution-evidence-h03`  
**Date**: 2026-09-24  
**Status**: Complete

## 조사 범위

Product Brief와 Spec 001의 제품 의미를 유지하면서 현재 WhyYou 공개 저장소에서 실제로 사용할 수 있는 reporting 경로, 회사 사용자 화면, 최종결정 경로, queue 재시도 구조를 확인했다. 아래 결정은 구현 편의를 위해 결과를 미리 정하는 것이 아니라, 실제 동작을 재현 가능하게 관찰하기 위한 기술 선택이다.

## R-01. 최초 vertical의 reporting 장애 위치

**Decision**: `report.generation_requested` 메시지를 처리하는 `ReportRequestedEventHandler` 진입점에 test-only, run/session-scoped 실패 훅을 둔다. 훅이 활성화된 세션에서는 `TimeoutError`를 발생시켜 기존 reporting queue 재시도 경로를 그대로 사용한다.

**Rationale**:

- WhyYou의 실제 reporting 흐름은 `interview.completed` → media 처리 → `report.generation_requested` → `ReportGenerator.generate()`이다.
- 공용 worker 전체를 정지하면 analysis/media/deletion까지 영향을 받아 H-03의 통제 대상을 넘는다.
- DB write 이후에 실패시키면 partial report를 만들 수 있어 “리포트 없음”이라는 전제조건이 불안정해진다.
- 핸들러 진입 실패는 report 저장 전에 발생하고 기존 worker가 이미 `TimeoutError`를 재시도 대상으로 다룬다.

**Alternatives considered**:

- **컨테이너 전체 중지**: 영향 범위가 reporting을 넘고 복구 확인이 모호하여 제외.
- **SQS 메시지 삭제/강제 DLQ**: Spec 002의 재시도·DLQ 의미를 앞당기고 최초 vertical이 복잡해져 제외.
- **리포트 테이블 삭제**: 장애가 아니라 사후 데이터 훼손이므로 제외.
- **LLM 오류 주입**: 모델 대역과 report pipeline 장애가 섞이고 결정론성이 낮아 제외.

## R-02. 장애 제어 방식

**Decision**: API가 아닌 공유 test-only 디렉터리의 JSON marker를 사용한다. marker는 `run_id`, `interview_session_id`, `fault_type`, `issued_at`, `expires_at`을 가지며 atomic rename으로 적용한다.

**Rationale**:

- API와 worker가 다른 프로세스이므로 API 프로세스의 메모리 flag는 worker에 전달되지 않는다.
- DB에 fault 테이블을 추가하면 시험 보조 기능 때문에 대상 서비스 migration이 생긴다.
- Docker bind mount marker는 구현이 작고 세션 단위로 한정할 수 있으며 삭제로 복구가 명확하다.
- TTL을 두면 ControlProof가 비정상 종료되어도 영구 장애가 되지 않는다.

**Safety gates**:

1. `CONTROLPROOF_TEST_HOOKS_ENABLED=true`
2. local/test runtime만 허용
3. allowlisted fault root 밖의 경로 거부
4. session UUID 일치
5. TTL 유효
6. production runtime에서 hook enabled면 startup 실패

## R-03. H-03의 실제 관측 지점

**Decision**: 한 사실을 여러 source로 수집하되 서로 대체하지 않는다.

| 확인할 사실 | 1차 관측 | 보조 관측 |
|---|---|---|
| fault 적용 | marker apply receipt | worker의 `CONTROLPROOF_FAULT_TRIGGERED` 로그 |
| report 미준비 | report API `202 queued` | report row 부재 제한 조회 |
| 담당자 표시 | Playwright 화면 캡처와 visible text | 2초 polling timeline |
| decision 거부 | 정상 final-decision API status/detail | human review row 부재 |
| 부분 변경 없음 | invitation status, stage, pipeline version 전후 비교 | decision history count |
| 자동결정 없음 | 관찰 창의 decision history | invitation/stage 상태 시계열 |
| 복구 | marker 부재 + report 생성 재개 | worker 처리 로그와 report status |

**Rationale**: 화면만으로 backend side effect를 증명할 수 없고, DB만으로 담당자가 무엇을 보았는지 증명할 수 없다. 독립 source는 같은 차원에서만 충돌을 판정한다.

## R-04. 현재 WhyYou 동작과 H-03 판정의 관계

**Decision**: 아래 현재 동작을 adapter mapping에 기록하되 PASS/FAIL은 실행 시 판정한다.

- `GET /v1/interview-sessions/{session_id}/report`는 report가 없으면 HTTP 202와 `status=queued`를 반환한다.
- 회사 콘솔은 202를 받는 동안 2초마다 재호출하고 “최종 리포트를 생성하고 있습니다.”를 계속 표시한다.
- `POST /v1/invitations/{invitation_id}/final-decisions`는 report를 먼저 조회하므로 report가 없으면 stage write 전에 거부된다.
- 정상 final decision route는 company bearer를 `ActorType.COMPANY_USER`로 만들고 stage, human review, invitation state를 한 transaction에서 갱신한다.

**Rationale**: H03-A2는 단순히 ready와 다르기만 한 표시가 아니라 최종 실패 또는 장기 지연이 숨겨지지 않는지를 묻는다. 따라서 30초 동안 generic queued만 반복되면 그 사실을 FAIL 후보로 남긴다. 반면 A3/A4는 실제 응답 이유와 쓰기 부작용을 별도로 평가한다.

## R-05. 상태 seed와 reporting trigger 분리

**Decision**: H-03 전용 fixture는 report/report item/evidence를 만들지 않는다. completed interview, final video, 최종 turn/transcript, invitation, recruiting stage, 회사 사용자까지만 만든다. fault 발동 준비 후 별도 단계가 `report.generation_requested` 이벤트를 발행한다.

**Rationale**:

- 기존 skeleton의 `state_seed.py`는 ready report를 생성하므로 H-03 전제와 반대다.
- seed 시점에 event까지 발행하면 worker가 fault 적용 전에 report를 만들 수 있다.
- fixture와 trigger를 분리하면 baseline을 안정적으로 수집하고 fault 경쟁 조건을 제거한다.

**Version guard**: WhyYou migration head, OpenAPI digest, 필요한 table/column signature를 preflight에 기록한다. signature가 다르면 `RUNNER_NOT_READY`로 중단하며 target FAIL을 만들지 않는다.

## R-06. ControlProof 영속화 방식

**Decision**: canonical 실행 기록은 `.controlproof/runs/{run_id}` 파일 bundle로 저장한다. 구조화 기록은 JSON/JSONL, 원본은 artifacts 하위 파일, 최상위 `manifest.json`은 모든 파일의 SHA-256과 상태를 가진다.

**Rationale**:

- Spec 001 규모에서 별도 DB는 migration, 백업, export 비용이 제품 가치보다 크다.
- Run 하나가 독립 디렉터리이면 검토·전달·tamper test가 단순하다.
- JSONL은 polling 중 매 관찰을 즉시 append·fsync할 수 있다.
- 이후 UI index가 필요해도 bundle을 source of truth로 유지할 수 있다.

**Rejected**:

- **메모리만 사용**: 중단 Run과 증적을 잃으므로 불가.
- **SQLite only**: binary screenshot/log artifact export가 추가로 필요하고 Run 단위 봉인이 덜 투명함.
- **S3/object storage 우선**: 로컬 2주 MVP에 과함. adapter로 이후 교체 가능.

## R-07. 증적 마스킹과 해시 순서

**Decision**: `collect → allowlist projection → secret/PII redaction → serialize → persist → hash stored bytes` 순서를 사용한다. 원본 시스템의 locator와 조회 조건은 별도 sanitized metadata로 남긴다.

**Rationale**: raw bearer, email, token, 전체 payload가 디스크에 한 번이라도 쓰이면 “저장 전에 제거” 조건을 위반한다. 해시는 실제 보존되는 redacted bytes에 대해 계산해야 나중에 검증 가능하다.

**Required redaction**:

- `Authorization`, cookie, access/refresh token, signed URL query
- 실제 email/name/phone 형태
- DB password와 connection URL credential
- WhyYou invitation token/hash

합성 식별자는 허용하지만 display에는 `subject_ref`를 우선 사용한다.

## R-08. Run concurrency와 복구

**Decision**: `target_id + subject_ref` 기준의 host file lock을 Run 시작부터 복구 완료까지 유지한다. 장애 적용 성공 여부와 무관하게 marker 생성 시도 이후는 `finally`에서 restore를 호출한다. restore 성공을 확인하지 못하면 `RESTORE_FAILED`와 block marker를 저장한다.

**Rationale**: 같은 세션에 두 Run이 marker를 적용·삭제하면 한 Run의 복구가 다른 Run의 fault를 풀 수 있다. 단일 host MVP에는 파일 잠금이 충분하며, 이후 분산 실행 시 lease 저장소로 대체한다.

## R-09. 비동기 관찰 정책

**Decision**: 2초 polling, 같은 상태 3회 연속 및 최소 4초를 안정화로 본다. H-03 fault 표시 창은 30초, 자동결정 부재 창은 10초, 복구는 120초다. 모든 원시 표본을 저장하고 판정에는 마지막 안정 상태를 사용한다.

**Rationale**:

- WhyYou 콘솔 자체가 2초 polling을 사용하므로 backend와 화면을 같은 시간 해상도로 비교할 수 있다.
- reporting 최초 retry delay가 15초이므로 30초 창은 fault 발동과 반복 상태를 둘 다 확인한다.
- marker 해제 뒤 다음 retry와 report 생성을 포함해도 120초면 전체 5분 목표 안에 든다.

## R-10. CLI 우선, 웹 UI 후속

**Decision**: Spec 001의 operator interface는 `preflight`, `run`, `show`, `verify`, `retest` CLI다. 화면 증적은 WhyYou 회사 콘솔을 Playwright로 캡처하지만 ControlProof 자체의 네 화면은 만들지 않는다.

**Rationale**: 먼저 검증해야 할 제품 가치는 실행·복구·증적·판정의 정확성이다. 파일 bundle과 JSON 출력은 후속 ControlProof UI의 안정된 계약이 된다.

## R-11. 추가 의존성

**Decision**:

- `playwright`: 담당자 화면의 실제 표시와 screenshot 수집
- `sqlalchemy`, `psycopg[binary]`: WhyYou fixture 및 최소 상태 조회
- HTTP mocking은 새 패키지 대신 HTTPX `MockTransport` 사용
- host lock은 별도 패키지 없이 Windows `msvcrt`와 POSIX `fcntl`을 얇게 추상화

**Rationale**: 실행 경로에 꼭 필요한 의존성만 추가한다. 브라우저 설치는 quickstart에서 명시하며 브라우저가 없으면 `RUNNER_NOT_READY`다.

## R-12. 대상 수정과 검증 도구의 저장소 경계

**Decision**: WhyYou hook과 향후 보호조치 수정은 WhyYou 저장소의 별도 commit/PR로 관리한다. ControlProof 저장소에는 adapter와 계약, target commit SHA만 보존한다.

**Rationale**: target 코드 복사본을 ControlProof 안에 두면 어떤 버전을 실제 시험했는지 모호해진다. target 수정 전 Run과 수정 후 Run의 `target_version`이 달라야 FAIL→PASS 계보가 설명된다.

## 미결정 사항

Phase 0에서 구현을 막는 미결정 사항은 없다. 다음 항목은 제품 선택이 아니라 구현 중 target mapping으로 확정한다.

- WhyYou 로컬 PostgreSQL 접속 환경변수 이름
- Docker shared fault root의 호스트 절대 경로
- 로컬 회사 사용자 bearer 획득 방식

세 값은 adapter config로 외부화하며 의미나 판정 규칙을 바꾸지 않는다.
