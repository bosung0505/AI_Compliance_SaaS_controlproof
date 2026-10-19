# Contract: Spec 009 Evidence Bundle (profile `controlproof.bundle-profile.spec009.v1`)

기존 봉인·`verify`·redaction(`engine/evidence.py` `EvidenceBundleWriter`, `verify_bundle`, `redact`/`assert_redacted`)을 그대로
쓴다. 모든 파일은 SHA-256·수집 시각·MIME·크기를 가진다(Constitution). 새로 정하는 것은 프로필별 필수 파일과 EV9 연결이며,
등록 방식은 보성의 H-01(`engine/h01_evidence.py`: `REQUIRED_FILES`, `verify_links`, `verify_facts`)과 같다.

## 공통 파일 (H-01·H-02와 같은 이름)

| 파일 | EV | 내용 |
|---|---|---|
| `run.json` | EV9-07 | Run 메타(프로필, 상태, fixture 식별, 계보) |
| `scenario.snapshot.yaml` | EV9-01 | 시나리오 정의 사본·digest(`target_access` 포함) |
| `target.snapshot.json` | EV9-01 | 대상 git sha, OpenAPI digest, 마이그레이션 head |
| `environment.snapshot.json` | EV9-01 | `LOCAL_EMULATED`, 외부 AI 차단, AWS `NOT_RUN`, 미검증 범위·한계 ID, fixture 식별 |
| `subjects.json` | EV9-02 | Run 소유 합성 지원자·lane(원시 토큰·쿠키 없음) |
| `observations.jsonl` | EV9-03/05 | 단계별 관찰 행 |
| `assertions.json`, `judgement.json` | EV9-07 | assertion별 판정·사유·근거 EV 경로 |
| `recovery.json` | EV9-06 | 복구·안전 상태·잔여 확인 |
| `manifest.json` | EV9-07 | 파일 목록·해시(봉인), `profile_contract` |

## 프로필별 필수 파일

| 프로필 | 파일 | EV |
|---|---|---|
| N-01 | `n01-lanes.json`(lane별 viewport, subject_ref, step_reached) | EV9-02 |
| | `n01-pc-capture.png`, `n01-mobile-capture.png` | EV9-03 |
| | `n01-measurements.json`(lane별 다섯 항목·조각 측정, 조작, 요소 경계, DOM 토큰 검사 결과) | EV9-03 |
| | `n01-policy-identifiers.json`(lane별 화면 응답·서버·저장 기록 식별값, 동의 완료 시각, subject_ref) | EV9-04 |
| N-03 | `n03-lanes.json` | EV9-02 |
| | `n03-stale-attempt.json`(제출 값, 현재 값, 응답 상태·어댑터 코드), `n03-stale-before.json`, `n03-stale-after.json` | EV9-05 |
| | `n03-latest-commit.json`(재조회 값, 응답 상태, 저장 기록), `n03-past-before.json`, `n03-past-after.json` | EV9-05 |

`LINKS`(EV9 → 파일)는 실행기 모듈에 두고 `verify_links`가 manifest·evidence 등록과 대조한다(H-01과 같음).

## `verify_facts` (프로필별 의미 검증)

- `run.json`·`scenario.snapshot.yaml`의 프로필·digest 일치, `environment.snapshot.json`의 digest·clean 소스·fixture 일치
  (H-01과 같은 검사).
- 봉인된 관찰 파일에서 `assertions_for(...)`로 assertion을 다시 만들어 `assertions.json`·`judgement.json`과 같은지 본다.
  `recovery.json`이 정리 확인을 못 하면 verdict는 `INCONCLUSIVE`, Run 상태는 `RESTORE_FAILED`여야 한다.
- N-01: `n01-measurements.json`의 lane 수 2, 항목 5개 정확히 한 번씩, 캡처 파일 2개가 manifest에 있고 비어 있지 않음,
  `n01-policy-identifiers.json`의 lane별 세 값 존재.
- N-03: `n03-stale-attempt.json`의 제출 값이 현재 값과 버전·해시 둘 다 다름, `n03-past-before/after.json` 존재.
- 불일치는 `mismatched_files`에 `<file>:semantic-evidence`로 기록한다.

## Redaction

- 금지: 지원자 세션 쿠키·원시 초대 토큰 원문, DB URL, 실제 개인정보. 기존 `FORBIDDEN_KEYS`에 `invitation_token`,
  `raw_invitation_token`, `raw_session_cookie`를 더한다. `token_hash`·`cookie`는 이미 금지다.
- 캡처 PNG: 캡처 직전 DOM 텍스트에 원시 초대 토큰·세션 값이 없는지 확인한 결과를 `n01-measurements.json`에 남긴다. 주소창은
  headless라 없다.
- `verify`는 기존처럼 해시·manifest·redaction 스캔을 모두 확인한다(SC-002).

## Summary projection (`controlproof.review.v1`에 더하는 필드)

`target_access`(표시 문구), `unverified_scope_items`, `limitations`. 기존 프로필에서는 비어 있고 화면에 줄을 만들지 않는다.
