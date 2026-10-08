# Contract: 웹 read model (`controlproof.web.v1`)

화면과 JSON 응답이 같은 뷰를 쓴다. 모든 값은 봉인 bundle·카탈로그·준비 상태 저장본에서 복사하며 웹이 판정을 계산하지 않는다. 모든 응답은
출력 경계 redaction(경로는 `<run_root>/…` 또는 `[PATH]`)을 거친다. 엔티티 정의는 [data-model.md](../data-model.md).

공통 머리:

```json
{
  "schema_version": "controlproof.web.v1",
  "view": "workbench",
  "generated_at": "2026-10-08T10:12:00+00:00",
  "environment_kind": "LOCAL_EMULATED",
  "aws_deployment_status": "NOT_RUN",
  "claim_scope": "EXECUTED_SCENARIO_AND_EVIDENCE_ONLY",
  "data_origin": "ACTUAL",
  "demo": false
}
```

`data_origin`이 `DEMO`면 `demo: true`이고 HTML은 상단 `DEMO DATA` 띠를 고정한다. 한 응답에 ACTUAL과 DEMO 기록을 섞지 않는다.

## view = workbench

```json
{
  "target": {"name": "WhyYou", "target_version": "<canonical target version 또는 null>"},
  "readiness_checked_at": "2026-10-08T10:12:00+00:00",
  "counts": {
    "PASS": 4, "FAIL": 0, "NOT_RUN": 4,
    "INCONCLUSIVE": {"total": 4, "by_reason": {"INSUFFICIENT_EVIDENCE": 1, "NO_TEST_TARGET": 3, "ACCESS_LIMITED": 0, "EVIDENCE_CONFLICT": 0}}
  },
  "groups": [
    {"control": "N", "control_label": "고지·동의 (N)", "scenarios": [
      {"id": "N-02", "question": "…", "target_exists": true,
       "readiness": {"value": "READY", "badge": "ready", "checked_at": "2026-10-08T09:05:00+00:00", "differs_from_common": true},
       "mvp_treatment": "EXECUTED",
       "official": {"result": "INCONCLUSIVE", "reason_code": "INSUFFICIENT_EVIDENCE", "badge": "insufficient_evidence", "note": "A5·A7"},
       "records_on_this_pc": {"official_present": false, "web_validation_runs": 1},
       "mismatch": null}
    ]}
  ],
  "retest_needed": [],
  "preserved_first_failures": [{"scenario_id": "E-01", "parent_run_id": "…", "child_run_id": "…"}]
}
```

- `counts`는 `groups`의 `official.result`·`reason_code`를 센 값이다(판정 생성 아님). 네 범주와 reason code 합이 같아야 한다.
- `readiness.differs_from_common`이 참인 줄만 HTML에서 확인 시각을 표시한다(FR-002).
- `mismatch`는 실제 root의 공식 Run 판정이 카탈로그 공식 상태와 다를 때 `{run_id, bundle_verdict, catalog_result}`.

## view = scenario

```json
{
  "id": "E-01", "mvp_treatment": "EXECUTED", "target_exists": true,
  "definition": {"source": "sealed_snapshot|scenario_file", "version": "1.0.0", "intent": "…", "preconditions": [], "steps": [],
                 "assertions": [{"assertion_id": "E01-A1", "description": "…", "expectation": {}, "required_evidence_ids": []}],
                 "required_evidence": [], "restore_policy": {}, "excluded_scope": []},
  "explanation": {"protected_object": "…", "policy_basis": "…", "legal_mapping_notice": "법 조문 대응은 표시하지 않음(법적 준수 비보증)",
                  "implementation_location": "…", "synthetic_data": "…", "manual_steps": []},
  "profiles": [{"execution_profile": "E01_CITATION_EVIDENCE_V1", "readiness": {}, "run_command": "…", "retest_command": "…",
                "preconditions_for_run": ["READY", "잠금 없음", "차단 없음", "사람 승인"]}],
  "previous_runs": [{"run_id": "…", "verdict": "FAIL", "integrity": "VERIFIED", "record_role": "WEB_VALIDATION"}]
}
```

`NOT_RUN` 항목은 `profiles=[]`, `explanation.not_run_reason`·`follow_up_condition`; `NO_TEST_TARGET` 항목은 `profiles=[]`, `explanation.absence_evidence`.
두 경우 모두 실행 명령 필드가 없다.

## view = run

```json
{
  "run": {"run_id": "…", "scenario_id": "E-01", "execution_profile": "…", "target_version": "…", "run_state": "COMPLETED",
          "started_at": "…", "ended_at": "…", "record_origin": "ACTUAL", "record_role": "WEB_VALIDATION", "parent_run_id": null},
  "integrity": {"status": "VERIFIED", "problems": []},
  "verdict": {"value": "FAIL", "reason_code": null, "summary": "…", "plain_meaning": "…", "impact": "…"},
  "steps": [{"phase": "BASELINE", "step_id": "…", "label": "…", "always_run": false}],
  "conditions": [{"kind": "APPLIED|RELEASED", "label": "…"}],
  "assertions": [{"assertion_id": "E01-A3", "status": "FAIL", "reason_code": null, "expected": {}, "actual": {}, "detail": "…",
                  "plain_meaning": "…", "evidence_refs": ["file:report-reads.jsonl"], "missing_evidence_ids": []}],
  "evidence": [{"ref": "file:report-reads.jsonl", "display_name": "회사 화면 리포트 조회", "relative_path": "<run_root>/<run_id>/report-reads.jsonl",
                "mime_type": "application/x-ndjson", "size_bytes": 12345, "sha256": "…", "phase": null, "evidence_requirement_ids": ["EV4-05"],
                "viewable": true}],
  "restore": {"status": "SUCCEEDED", "seconds": 0.2, "deadline_seconds": 120, "manual_cleanup_required": false},
  "limitations": ["FIXTURE_INTERVIEW_INPUT", "EXTERNAL_AI_BLOCKED", "FIXED_MODEL_SUBSTITUTE"],
  "memos": [{"memo_id": "…", "author": "…", "created_at": "…", "text": "…"}],
  "developer": {"fixture_id": "…", "files": ["…"]}
}
```

- `integrity.status != VERIFIED`면 `verdict`·`assertions`·`evidence`는 `null`이고 `integrity.problems`만 채운다.
- `relative_path`와 `developer`는 HTML에서 "개발자용 원본 정보" 안에만 그린다(FR-019).

## view = compare

```json
{
  "parent": {"run_id": "…", "verdict": "FAIL", "target_version": "…", "integrity": "VERIFIED"},
  "child": {"run_id": "…", "verdict": "PASS", "target_version": "…", "integrity": "VERIFIED"},
  "parent_unchanged": true,
  "changed_dimensions": {"scenario": false, "target_paths": ["git_commit_sha"], "environment": false, "model_fixture": false},
  "fix_description": {"text": "…", "source": "memo|validation"},
  "assertion_changes": [{"assertion_id": "E01-A3", "before": "FAIL", "after": "PASS", "before_evidence": ["…"], "after_evidence": ["…"]}],
  "remaining_failures": []
}
```

`parent_unchanged=false`이거나 부모가 VERIFIED가 아니면 `lineage_problem`만 채우고 비교 항목은 `null`.

## view = report

ReportView 필드([data-model.md](../data-model.md) §7)와 `items_present`: `{"R1": true, …, "R13": true, "C1": true, …, "C9": true}`.
`fixed_scope_sentence`는 범위표 고정 문구와 글자가 같다.
