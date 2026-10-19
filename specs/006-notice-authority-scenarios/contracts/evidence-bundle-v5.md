# Contract: Spec 006 Evidence Bundle (profile `controlproof.bundle-profile.spec006.v1`)

기존 봉인·`verify`·redaction(`engine/evidence.py` `EvidenceBundleWriter`, `verify_bundle`, `redact`/`assert_redacted`)을 그대로
쓴다. 모든 파일은 SHA-256·수집 시각·MIME·크기를 가진다(Constitution). 새로 정하는 것은 프로필별 필수 파일과 EV6 연결이다.

## 공통 파일

| 경로 | EV | 내용 |
|---|---|---|
| `snapshot/scenario.json` | EV6-01 | 시나리오 정의 사본·digest, `target_access` |
| `snapshot/target.json` | EV6-01 | 대상 git sha, OpenAPI digest(스택 프로필), 마이그레이션 head |
| `snapshot/environment.json` | EV6-01 | `LOCAL_EMULATED`, 외부 AI 차단, AWS `NOT_RUN`, 미검증 범위·한계 ID |
| `snapshot/capabilities.json` | EV6-01 | probe 결과, 준비 상태 |
| `judgement.json` | EV6-10 | assertion별 판정·사유·근거 EV 경로 |
| `manifest.json` | EV6-10 | 파일 목록·해시(봉인) |

## 프로필별 필수 파일

| 프로필 | 파일 | EV |
|---|---|---|
| N-01 | `lanes.json` | EV6-02 |
| | `n01/{pc,mobile}/capture.png`, `n01/{pc,mobile}/items.json`(항목별 네 측정·조작·요소 경계) | EV6-03 |
| | `n01/policy_identifiers.json`(화면 응답·서버·저장 기록, 동의 완료 시각, lane별 subject_ref) | EV6-04 |
| | `restore.json` | EV6-09 |
| N-03 | `lanes.json` | EV6-02 |
| | `n03/stale_attempt.json`(제출 값, 응답 상태·코드), `n03/stale_before.json`, `n03/stale_after.json`, `n03/latest_commit.json`, `n03/past_before.json`, `n03/past_after.json` | EV6-05 |
| | `restore.json` | EV6-09 |
| H-01 | `lanes.json`(주체 종류, 자격 원문 해시 앞 12자) | EV6-02 |
| | `h01/attempts.jsonl`(경로·주체·요청 메타·응답 상태 코드·`X-Request-Id`, 본문 판정 안 함) | EV6-06 |
| | `h01/before.json`, `h01/after.json`, `h01/audit_rows.json`, `h01/idempotency_probe.json` | EV6-07 |
| | `restore.json` | EV6-09 |
| H-02 | `h02/surface.json`([h02-write-surface-v1.md](./h02-write-surface-v1.md) 결과 형식) | EV6-08 |

H-02는 `restore.json`을 갖지 않는다. 대신 `snapshot/environment.json`에 `restore: NONE_STATIC`을 둔다.

## Redaction

- 금지: 회사 Bearer·위조 Bearer·지원자 세션 쿠키·원시 초대 토큰 원문, DB URL, 실제 개인정보. 기존 `FORBIDDEN_KEYS`에
  `invitation_token`, `raw_session_cookie`, `forged_bearer`를 더한다.
- 캡처 PNG: 캡처 직전 DOM 텍스트에 원시 초대 토큰·세션 값이 없는지 확인한 결과를 `items.json`에 남긴다. 주소창은 headless라 없다.
- `verify`는 기존처럼 해시·manifest·redaction 스캔을 모두 확인한다(SC-002).

## Summary projection (`controlproof.review.v1`에 더하는 필드)

`target_access`(표시 문구), `unverified_scope_items`, `limitations`, `h02_reference`(H-01만, 참조용 run id 또는 없음).
