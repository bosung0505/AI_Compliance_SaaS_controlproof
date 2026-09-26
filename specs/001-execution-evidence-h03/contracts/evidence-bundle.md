# Contract: Evidence Bundle v1

## 디렉터리 구조

```text
.controlproof/runs/{run_id}/
├── run.json
├── scenario.snapshot.yaml
├── target.snapshot.json
├── subjects.json
├── faults.jsonl
├── observations.jsonl
├── assertions.json
├── judgement.json
├── retest-diff.json          # 재시험일 때만
├── artifacts/
│   ├── {artifact_id}.json
│   ├── {artifact_id}.png
│   └── {artifact_id}.log
└── manifest.json
```

경로는 모두 Run root 기준 상대 경로이며 `..`, 절대 경로, symlink로 root 밖을 가리킬 수 없다.

`target.snapshot.json`은 `controlproof.target-snapshot.v1` 계약을 따르며 `target_version`과 `captured_at`을 제외한 identity fields의 canonical JSON bytes에 대한 SHA-256이 `run.json.target_version=target-snapshot:sha256:<digest>`와 일치해야 한다. Spec 001 H-03 Run bundle의 snapshot은 반드시 `git_dirty=false`, `git_diff_digest=null`이어야 한다. dirty checkout의 snapshot과 `git_diff_digest`는 `RUNNER_NOT_READY` preflight 진단으로만 반환하며 Run 디렉터리를 만들거나 bundle을 봉인하지 않는다.

## Atomicity와 durability

- JSON/manifest는 동일 디렉터리의 임시 파일에 쓰고 flush·fsync 후 atomic replace한다.
- JSONL은 record 한 줄마다 flush하며 주요 phase 경계에서 fsync한다.
- artifact는 redaction이 끝난 bytes만 임시 파일에 쓰고, hash 계산 후 최종 이름으로 이동한다.
- `manifest.json.sealed_at`이 생긴 뒤 canonical 파일 쓰기를 거부한다.

## `manifest.json`

```json
{
  "schema_version": "controlproof.bundle.v1",
  "run_id": "0199...",
  "created_at": "2026-09-24T00:00:00Z",
  "sealed_at": "2026-09-24T00:02:00Z",
  "files": [
    {
      "path": "artifacts/0199....json",
      "mime_type": "application/json",
      "size_bytes": 842,
      "sha256": "64-lowercase-hex",
      "artifact_id": "0199...",
      "redaction_profile": "controlproof-redaction-v1"
    }
  ],
  "required_evidence": {
    "EV-01": ["artifact-id"],
    "EV-02": ["artifact-id"],
    "EV-03": ["artifact-id"],
    "EV-04": ["artifact-id"],
    "EV-05": ["artifact-id"],
    "EV-06": ["artifact-id"],
    "EV-07": ["artifact-id"],
    "EV-08": ["artifact-id"],
    "EV-09": ["artifact-id"]
  },
  "bundle_digest": "sha256-of-canonical-manifest-without-bundle-digest"
}
```

`files`는 `manifest.json` 자신을 제외한 모든 canonical 파일을 포함한다. directory listing에 미등록 파일이 있으면 verify는 경고하되, 필수 파일 누락/변조만 integrity failure로 본다.

## Artifact metadata

구조화 artifact JSON은 다음 envelope를 사용한다.

```json
{
  "schema_version": "controlproof.artifact.v1",
  "artifact_id": "0199...",
  "run_id": "0199...",
  "subject_ref": "candidate-01",
  "phase": "INJECTED",
  "step_id": "attempt-final-decision",
  "attempt": 1,
  "evidence_requirement_ids": ["EV-05"],
  "artifact_type": "HTTP_EXCHANGE",
  "captured_at": "2026-09-24T00:01:00Z",
  "source_locator": {
    "method": "POST",
    "route_template": "/v1/invitations/{invitation_id}/final-decisions",
    "target_id": "whyyou-local"
  },
  "content": {
    "request": {
      "headers": {"Idempotency-Key": "[HASHED]"},
      "body": {"recruiting_stage_id": "uuid", "expected_pipeline_version": 1}
    },
    "response": {"status": 404, "body": {"detail": "[SANITIZED]"}}
  }
}
```

Authorization, cookies, tokens, DB credentials와 실제 PII는 envelope에 존재할 수 없다.

## `observations.jsonl`

한 줄에 완전한 Observation JSON 한 개를 쓴다. line 순서는 수집 순서이며 `observed_at`만으로 재정렬해 원본 순서를 바꾸지 않는다.

필수 필드:

```json
{
  "schema_version": "controlproof.observation.v1",
  "observation_id": "0199...",
  "run_id": "0199...",
  "subject_ref": "candidate-01",
  "phase": "INJECTED",
  "step_id": "observe-report-status",
  "attempt": 4,
  "key": "report.api.status",
  "presence": "PRESENT",
  "value": "queued",
  "source_type": "HTTP",
  "source_ref": "whyyou-local:GET:report",
  "observed_at": "2026-09-24T00:00:08Z",
  "artifact_ids": ["0199..."]
}
```

`ABSENT`는 조회 성공·기록 없음이며, `UNAVAILABLE`은 `error_code`를 요구한다.

## 필수 evidence mapping

| ID | 최소 artifact type |
|---|---|
| EV-01 | `STATE_SNAPSHOT` |
| EV-02 | `FAULT_RECEIPT` |
| EV-03 | matching worker trigger `FAULT_RECEIPT` + report status `HTTP_EXCHANGE`; `LOG_EXTRACT`는 선택 보조 근거 |
| EV-04 | `SCREENSHOT` + visible-text JSON |
| EV-05 | decision `HTTP_EXCHANGE` |
| EV-06 | post-attempt `STATE_SNAPSHOT` |
| EV-07 | windowed decision-history `STATE_SNAPSHOT` |
| EV-08 | restore `FAULT_RECEIPT` + worker health + recovered `STATE_SNAPSHOT` + separate report-processing recovery observation |
| EV-09 | canonical `target.snapshot.json` + scenario snapshot; 두 snapshot digest가 Run과 일치 |

EV-03은 marker 적용 명령 receipt만으로 충족되지 않으며, 현재 Run·session·trigger와 일치하는 worker trigger receipt가 필요하다. EV-04는 API artifact만으로 충족되지 않는다.

## Redaction contract

1. collector는 필요한 field만 allowlist projection한다.
2. redactor는 key와 value pattern을 모두 검사한다.
3. redactor는 저장 전에 민감값을 제거/치환한다.
4. redaction scanner가 금지 pattern을 다시 검사한다.
5. 통과한 bytes만 저장하고 hash한다.

금지 key 예: `authorization`, `cookie`, `password`, `access_token`, `refresh_token`, `token_hash`, `signed_url`. 이메일은 합성 domain이라도 display artifact에서 `subject_ref`로 대체한다.

## Verify contract

`verify`는 다음을 확인한다.

- manifest schema와 run ID
- 필수 canonical 파일 존재
- manifest의 모든 path가 root 내부
- size와 SHA-256 일치
- artifact envelope의 dimension과 manifest metadata 일치
- EV-01~EV-09 mapping 존재
- PASS Run이면 모든 mapped artifact가 VERIFIED
- scenario/target snapshot digest가 run.json과 일치
- sealed parent가 retest 뒤에도 동일 digest인지

검증은 read-only이고 manifest를 자동 고치지 않는다.
