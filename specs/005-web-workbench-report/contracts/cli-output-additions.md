# Contract: 명령줄 출력 추가·보완 (Spec 005, FR-035·FR-036)

기존 `controlproof.cli.v1` 출력에 필드를 더하고 값 형식을 다듬는다. **종료 코드 값은 바꾸지 않는다**(D-018 추가 결정 1). 키를 지우지 않는다.

## 1. `result_kind`·`error_kind` (위험 5)

모든 `--json` 출력에 `result_kind`를 더한다.

| 명령·상황 | `result_kind` |
|---|---|
| `preflight`, 준비 안 됨으로 끝난 `run`·`retest` | `READINESS` |
| `run`·`retest` 완료 | `RUN` |
| `show` | `PROJECTION` |
| `verify` | `VERIFY` |
| `cleanup-confirm` 성공 | `CLEANUP` |
| 모든 오류 | `ERROR` |

`ERROR`에는 `error_kind`를 둔다: `USAGE`(인자 해석 오류), `CONTRACT`(`CliContractError` 코드, 안전 확인 실패), `CONFIG`, `NOT_FOUND`, `RETEST`,
`INTERRUPTED`, `UNEXPECTED`. 기존 `error`·`detail` 키는 그대로다.

- 인자 해석 오류도 `--json`이 있으면 `{"schema_version":"controlproof.cli.v1","command":…,"result_kind":"ERROR","error_kind":"USAGE",…}`를
  stdout으로 내고 종료 코드는 지금처럼 2다. `--json`이 없으면 지금처럼 사용법 문장을 stderr로 낸다.
- 준비 안 됨으로 끝난 `run`·`retest`의 `command`는 각각 `"run"`·`"retest"`다(지금은 `"preflight"`). **보성 확인**(research R-010).
- H-03 `cleanup-confirm`의 안전 확인 실패는 traceback 대신 `error_kind=CONTRACT`, `error="H03_SAFE_STATE_NOT_CONFIRMED"`, 종료 코드 1.

해석 규칙(웹): `result_kind`와 `readiness`·`error_kind`로 해석하고 종료 코드는 기록만 한다.

## 2. 경로 표기 (위험 1·2)

- `run`·`retest`의 `bundle_path` 값은 `<run_root>/<run_id>` 표기다(키 유지, 절대 경로 아님). **보성 확인**(research R-009).
- 모든 출력은 마지막에 경로 정책을 거친다: run root 안 경로 → `<run_root>/…`, 그 밖의 절대 경로 → `[PATH]`. 사람용 `show` 문장도 같다.
- `USER_PATH_RE`는 드라이브 뒤 구분자 1개 이상과 JSON 이스케이프된 구분자(`\\`)를 잡는다.

## 3. run root 규칙

`run`·`retest`·`cleanup-confirm`(지금처럼 설정 경유)과 `show`·`verify`가 모두 `--run-root` > `CONTROLPROOF_RUN_ROOT` > `.controlproof/runs`를 쓴다.
**보성 확인**(research R-004; `show`·`verify`가 환경 변수를 읽게 됨).

## 4. 증적 색인 (위험 3)

`show`·`run`·`retest`의 검토 projection(`controlproof.review.v1`)에 `evidence_index`를 더한다. 기존 `evidence_links`는 유지한다.

```json
"evidence_index": {
  "files": [{"ref": "file:report-reads.jsonl", "relative_path": "<run_root>/<run_id>/report-reads.jsonl", "sha256": "…", "size_bytes": 0,
             "mime_type": "application/x-ndjson", "evidence_requirement_ids": ["EV4-05"]}],
  "by_requirement": {"EV4-05": ["file:report-reads.jsonl"]},
  "by_assertion": {"E01-A3": {"refs": ["file:report-reads.jsonl"], "missing_requirement_ids": []}},
  "unresolved_refs": []
}
```

## 5. 검사 버전과 verify (FR-036, 보성 확인 research R-012)

- 새로 봉인하는 manifest에 `redaction_profile: "controlproof.redaction.v2"`를 쓴다.
- verify는 manifest의 검사 버전으로 판정한다(표시 없음 = v1). 강화 검사(v2) 결과는 `strict_scan_findings: [{"path": "…", "rule": "…", "count": n}]`
  비차단 필드로만 더한다. 값은 쓰지 않는다.
- `scripts/scan_bundles.py --run-root <root> --out <report.json>`: 각 bundle에 v1·v2를 모두 적용한 차이 보고서(bundle ID, 파일 상대 경로, 규칙, 건수).
  bundle을 읽기만 한다.
