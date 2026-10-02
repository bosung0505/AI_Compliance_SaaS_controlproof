# Spec 003 Implementation Decisions

## Status

- Implementation foundation: in progress
- Initial actual N-02 Run: `15cef078-ee24-4f0e-91ef-381e0f7a1cc2`, sealed and `VERIFIED`; overall `RESTORE_FAILED` / `INCONCLUSIVE`
- Evidence-gated product remediation: `PENDING_T080_CLASSIFICATION`; no product change or child Run

This log records implementation choices that cannot be inferred from Tasks alone.
The first actual Run is sealed. A direct assertion FAIL is a preserved observation,
not by itself proof that a WhyYou product boundary accepted processing.

## Decision template

### ID-003-XX — Title

- Date:
- Task:
- Requirement/assertion:
- Status: `PROPOSED | CONFIRMED | NOT_REQUIRED`
- Source baseline:
- Triggering test or parent Run:
- Exact evidence artifact:
- Root-cause class:
  `TARGET_CONTROL_DEFECT | RUNNER_OR_OBSERVER_DEFECT | RESTORE_OPERATOR_DEFECT`
- Decision:
- Alternatives considered:
- Safety and compatibility impact:
- Regression command and result:
- Child Run / parent immutability result:

## Pre-actual implementation decisions

### ID-003-01 — Keep Spec 003 instrumentation separate from product guards

- Date: 2026-10-01
- Task: T001~T004
- Requirement/assertion: FR-026~027, FR-037~039
- Status: `CONFIRMED`
- Source baseline: ControlProof `c27f9d6`; WhyYou `511ae9e`
- Triggering test or parent Run: approved Plan and D-015/D-016; no actual Run yet
- Exact evidence artifact: `NOT_RUN`
- Decision: Add only disabled-by-default local/test configuration, deterministic
  fixtures and implementation records during Setup. Do not add analysis,
  recording or assessment consent guards before the first actual Run.
- Alternatives considered: pre-fix suspected WhyYou boundaries; rejected because
  it would destroy the first factual FAIL/PASS evidence.
- Safety and compatibility impact: no production enablement, no actual applicant
  data, no existing sealed bundle mutation.
- Regression command and result: recorded in `validation.md` after Setup checks
- Child Run / parent immutability result: `NOT_REQUIRED` before T078

### ID-003-02 — Inject the consent fault inside the request transaction

- Date: 2026-10-01
- Task: T052~T064
- Requirement/assertion: FR-026~032, N02-A6~A7, EV3-07~EV3-09
- Status: `CONFIRMED`
- Source baseline: ControlProof `c27f9d6`; WhyYou `511ae9e`; both working trees remain uncommitted
- Triggering test or parent Run: automated US3 contract and integration tests; no actual Run yet
- Exact evidence artifact: `NOT_RUN`; automated command results are recorded in `validation.md`
- Root-cause class: not applicable before the initial actual Run
- Decision: Place a disabled-by-default, local/test-only one-shot hook immediately after
  `save_consent()` and before invitation state/Outbox mutation. Bind marker and receipt to the
  current Run, lane, subject and request. Restore only owned marker/token files, verify zero
  durable consent effects, remove each temporary deep-boundary overlay, and allow same-subject
  retry only after the safe-state check passes.
- Alternatives considered: fail outside the request transaction, infer activation from a 5xx,
  or auto-delete foreign markers. Rejected because these choices cannot prove rollback, trigger
  identity or cleanup ownership.
- Safety and compatibility impact: production/default execution is a no-op. No document,
  recording or assessment product guard was added before T078. Uncertain restore records
  `RESTORE_FAILED` and blocks a later fault Run until evidence-backed `cleanup-confirm`.
- Regression command and result: ControlProof 366 passed; scoped WhyYou regression 88 passed;
  full commands and durations are in `validation.md`
- Child Run / parent immutability result: `NOT_REQUIRED` before T078

## Conditional remediation decisions

| Task | Boundary | Parent artifact required | Status |
|---|---|---|---|
| T080 | A5~A7 or runner/restore ownership | Yes | `PENDING_CLASSIFICATION`; audit below |
| T081 | document analysis | Yes | `PENDING_DECISION`; parent A2 PASS |
| T082 | recording | Yes | `PENDING_DECISION`; parent A3 PASS |
| T083 | AI assessment/reporting | Yes | `PENDING_CLASSIFICATION`; parent A4 FAIL |
| T084 | child retest or parent reverify | Yes | `NOT_RUN`; cleanup and retest gate confirmed, full preflight pending |

### ID-003-03 — First Run root-cause audit remains open

- Date: 2026-10-02
- Task: T080 (not completed)
- Requirement/assertion: FR-026~033, N02-A4~A7, SC-010
- Status: `PROPOSED`; no remediation selected
- Source baseline: ControlProof Run source `b92b9ada48e82c5290d5b6eb99883e5dcc50f0ee`; WhyYou `94ad7f2caa0083d3d029b4b7726ee9b34c48eb21`
- Triggering parent Run: `15cef078-ee24-4f0e-91ef-381e0f7a1cc2`; manifest SHA-256 `d2306f3cd6e2b15ce87d94e4844a2278c7ea3c0b3c052a2aac45e1bff8f2bc9b`

| Direct FAIL | Exact sealed parent artifacts | Supported observation and classification limit |
|---|---|---|
| A4 | `assertions.json`, `bypass-attempts.jsonl`, `protected-effects.jsonl` | `EVENT_PERSISTED` and `event:497fd25e-9939-5ccf-9118-287fd1053b25` are real Run observations. `engine/adapters/whyyou/protected_processing.py` itself inserts `report.generation_requested` into `outbox_events`, then counts that row as a protected effect. Treating this runner-created effect as proof of target acceptance is a `RUNNER_OR_OBSERVER_DEFECT`; target behavior remains unresolved. The sealed bundle does not prove successful target AI processing or establish the T083 product-guard condition. |
| A5 | `assertions.json`, `policy-and-consent.json`, empty `causal-events.jsonl` and `causal-edges.jsonl` | Normal consent is absent and the path chain is unproven. `engine/adapters/whyyou/consent.py` maps both HTTP 409 and 422 to `CONSENT_POLICY_MISMATCH` without preserving the response reason. The sealed evidence cannot distinguish target rejection from runner request/seed mismatch. Root-cause class remains unassigned. |
| A6 | `assertions.json`, `policy-and-consent.json`, empty `fault-receipts.jsonl`, `bypass-attempts.jsonl`, `protected-effects.jsonl` | The fault trigger is unproven; the consent POST is represented by the same generic 422 mapping. The `event:a3a48891-2564-57d5-bb72-913827ee2e7a` effect has the same runner-created limitation as A4. A single root-cause class for this combined FAIL is not yet supportable. |
| A7 | `assertions.json`, `recovery.json`, `run.json` | `marker_removed`, `consumed_token_removed` and `hook_inactive` are true, while `failed_request_effects_zero` and `normal_retry_succeeded` are false. `engine/executors/n02.py` derives `restore_status=FAILED` from the whole recovery journey, including protected effects and retry/order proof. This does not prove marker cleanup failed; root-cause class remains unassigned. The persistent restore block remains in force. |

The unsealed WhyYou observer receipt `.controlproof/observers/receipts/15cef078-ee24-4f0e-91ef-381e0f7a1cc2.jsonl` contains handler-entry diagnostics, but it is outside the verified bundle and cannot replace sealed target-side effect/result evidence. Source review also found that the local report model/embedder substitute is not a global external-AI circuit breaker: `runtime/worker.py` still passes `aws.model` or `aws.embedder` to other paths. This does not establish an external call in the parent Run; it is a safety constraint for any later live execution.

T080-E1 now implements the reviewed evidence correction for future Runs; it does not alter or reclassify the parent. T080 still needs a new evidence-bearing diagnostic path and a safe, independently verified environment before the unassigned parent root causes can be resolved. Do not clear the restore block, add a WhyYou product guard, or launch T084 on this preliminary audit.

### ID-003-04 — Evidence correction implemented; live retest remains blocked

- Date: 2026-10-02
- Task: T080-E1 complete; T080 and T080-E2 open
- Status: `CONFIRMED` for scoped automated evidence behavior; actual WhyYou outcome unverified
- Decision: The assessment outbox insert is `SUBMITTED` probe input and excluded from target effect delta. Only an event-linked target `REPORT_ASSESSMENT_STARTED` receipt or independent target effect can directly FAIL A4/A6. The local/test observer writes the start receipt before the first report read, after the existing fault hook. Matching receipts are sanitized into `observations.jsonl`, linked to `protected-effects.jsonl`, and verified inside a new bundle. Consent rejection evidence keeps only HTTP status, request ID and an allowlisted target reason; recovery evidence separates condition cleanup, safe state and retry result. Parent bytes and historical verdict stay unchanged.
- Regression: scoped ControlProof N-02/EV3 tests 115 PASS; scoped WhyYou reporting/ControlProof runtime tests 27 PASS; changed-file Ruff lint PASS; parent bundle reverify `VERIFIED` (19 files). Commands and limitations are in `validation.md`.
- Safety limit: WhyYou `.env` sets `AI_PROVIDER=aws` and `EMBEDDING_PROVIDER=aws` with no `BEDROCK_RUNTIME_ENDPOINT_URL`. `runtime/worker.py` still passes `aws.model` or `aws.embedder` to non-report paths and report retrieval; it also composes AWS speech dependencies. ControlProof's `CONTROLPROOF_EXTERNAL_AI_ALLOWED=false` is not a WhyYou-wide network block. There is no evidence that the parent Run made an external AI call, but T080-E2 must close this risk before any new actual Run. The persistent restore block is untouched; no product guard was added.

### ID-003-05 — T080-E2 file scope fixed before implementation

- Date: 2026-10-02
- Task: T080-E2 scope decision only; implementation and verification pending
- Status: `SCOPE_REOPENED`; no actual WhyYou verdict or restore clearance
- Decision: Keep the existing report fixture's meaning. Add a local/test-only fail-closed contract for every AI dependency reachable from the API and active worker: AWS or GCP model/embedding, AWS Transcribe/Polly or GCP speech, and GCP Document AI OCR. A disabled provider is insufficient if a constructed dependency can still be invoked. Prove the selected providers and service-specific endpoint routing, plus the active worker's current configuration, before preflight can report READY. Missing, non-loopback, stale or mismatched proof must remain NOT_READY. This is isolation proof, not a promise that local substitutes can complete every WhyYou path or that A1~A7 will PASS.
- Source finding: `runtime/aws.py:_client_factory` does not apply `AWS_ENDPOINT_URL` to Bedrock, Transcribe or Polly; it accepts their service-specific `*_ENDPOINT_URL` keys. `runtime/worker.py` passes normal model/embedder and speech dependencies beyond report assessment. `runtime/document_ai.py` defaults OCR to a GCP endpoint; `runtime/speech.py` can select GCP providers. The API health endpoint reports only the report fixture identity. `engine/cli.py:cleanup-confirm` calls the reporting fault adapter's `target_safe`, which checks reporting markers and liveness, not the N-02 consent marker/token and durable consent state. None of these findings proves an external AI call in the sealed parent.

| Repository | Tracked implementation edits allowed for T080-E2 | Test edits allowed |
|---|---|---|
| WhyYou | `backend/src/interview_evidence/runtime/controlproof_model_substitute.py`; `backend/src/interview_evidence/runtime/worker.py` | `backend/tests/unit/runtime/test_controlproof_model_substitute.py`; `backend/tests/integration/test_worker_delivery.py` |
| ControlProof | `engine/adapters/whyyou/capability.py`; `engine/cli.py`; `engine/adapters/whyyou/consent_fault.py` | `tests/contract/test_whyyou_capability.py`; `tests/contract/test_cleanup_confirm.py`; `tests/integration/test_n02_consent_fault_restore.py` |

The WhyYou local ignored `.env` is an operational configuration input, not a tracked source edit: the later implementation may adjust only `AI_PROVIDER`, `EMBEDDING_PROVIDER`, `STT_PROVIDER`, `TTS_PROVIDER`, `BEDROCK_RUNTIME_ENDPOINT_URL`, `TRANSCRIBE_ENDPOINT_URL`, `POLLY_ENDPOINT_URL`, `GCP_DOCUMENT_AI_API_ENDPOINT`, and, if a GCP provider remains selected, its service-specific AI/speech endpoint. Do not print or commit the file or credentials. An endpoint must be independently shown to be loopback for the process that actually uses it; an unavailable local endpoint remains safe but may make functional readiness fail.

Read-only references for this scope: WhyYou `backend/src/interview_evidence/runtime/aws.py`, `generative_ai.py`, `speech.py`, `document_ai.py`, `production.py`, `.env.example`, `scripts/local.ps1`, `compose.yaml`; ControlProof `engine/config.py`, `engine/adapters/whyyou/fault.py`, `engine/adapters/whyyou/adapter.py`, `engine/adapters/whyyou/n02_seed.py`, `engine/lifecycle.py`, and the sealed parent bundle. Existing AWS/GCP factory tests and N-02 preflight/adapter contracts may be run without editing. The blocked Run and its unsealed observer receipt remain untouched.

Safe-state proof must be specific to the blocked N-02 Run and subject: owned consent marker/token absent or safely restored, failed consent transaction has zero durable partial effects, no active fault hook, and target liveness. `cleanup-confirm` must reject a generic reporting-only safety result, missing subject mapping, unavailable database state or mismatched evidence. The persistent block stays active until a separate evidence-backed cleanup action. If these checks require edits outside the allowlist, a new service emulator, a product behavior change, or broader outbound-service isolation (for example MediaConvert), stop and report the needed expansion before implementing it. No child Run is authorized by this scope decision.

2026-10-02 implementation-entry audit reopened the worker-attestation scope before code changes. `scripts/run_workers.py` starts four independent `interview_evidence.worker` processes; `backend/src/interview_evidence/worker.py` writes one shared static `/tmp/iep-worker-ready` file and removes it on exit. Neither the API fixture health nor that file proves each currently active worker's AI routing. The runtime-only `worker.py` edit allowlist above cannot establish an authoritative process set or distinguish an old worker launched with a different configuration. A read-only Win32 process command-line inventory with `Get-CimInstance Win32_Process` was denied (`Access is denied`) in this workspace, so external process enumeration cannot close the gap here. A new design review must explicitly add launcher/entrypoint attestation and its tests, or another independently verifiable process isolation mechanism, before T080-E2 implementation resumes. This is a scope finding, not a newly observed external call. No test, code change, block clearance or Run followed this finding.

### ID-003-06 — Managed worker pool AI isolation gate implemented

- Date: 2026-10-02
- Task: T080-E2 isolation sub-bundle, including live API/worker proof and read-only N-02 safe-state confirmation
- Status: `CONFIRMED` for scoped behavior and isolated live proof; actual WhyYou verdict remains the sealed parent's `INCONCLUSIVE`
- Additional reviewed WhyYou scope: `scripts/run_workers.py`, `backend/src/interview_evidence/worker.py`, `backend/tests/integration/test_worker_delivery.py`, and the existing local/test health contract regression in `backend/tests/integration/test_controlproof_fault_hook_safety.py`. This is the multi-process expansion identified in ID-003-05; no product consent guard changed.
- Decision: When the fixed model control is enabled, API and worker startup require `AI_PROVIDER=aws`, `EMBEDDING_PROVIDER=aws`, disabled STT, text-only TTS, `CONTROLPROOF_EXTERNAL_AI_ALLOWED=false`, and explicit loopback endpoints for Bedrock runtime, Transcribe, Polly and GCP Document AI OCR. Unsupported GCP model/speech modes fail closed. The API health exposes only an isolation digest, not endpoint or credential values. The local launcher holds an exclusive pool lock, assigns a fresh session ID, and publishes the actual interpreter PIDs reported by one fresh attestation per worker slot. Each production worker writes its PID, launcher/session identity, matching isolation digest and heartbeat after a successful cycle. N-02 `processing.paths.read` requires matching API, launcher and every listed worker proof; a missing, stale, mismatched or extra fresh attestation is NOT_READY. A partial launch cleans up spawned children. The old static ready file is not used in this profile.
- Local configuration: four service-specific endpoint keys were added only to WhyYou's ignored `.env`, all pointing to loopback. No credential was printed or committed. A process-local readback of `controlproof_health` reported isolation enabled and a 64-character digest. These settings may cause unsupported local AI calls to fail locally; this is fail-closed isolation, not a functional substitute for every path.
- Tests: initial intended RED was 10 WhyYou AI routing cases plus one ControlProof preflight case, all failing for the missing contract. After implementation, scoped WhyYou tests and ControlProof capability/CLI tests pass; exact final commands and counts are in `validation.md`. The attempted `scripts/local.ps1 check` ran repository-wide formatting and failed on 10 existing Prettier files; it was not a configuration check and no broad reformat was made.
- Live probe: Windows venv launchers inserted wrapper Python processes; the initial manifest used wrapper PIDs, so worker proofs could not match. The launcher now derives its expected PID set from fresh slot proofs. On isolated probe `c4ae90212e32`, four live worker PIDs, the launcher PID, session ID, digest and heartbeats matched. The probe used a new database and five new queues because the existing local database held 325 pending outbox events. Probe processes, database and queues were removed; the original pending count remained 325. Scoped 51 WhyYou and 20 ControlProof tests passed. The local probe result remains under ignored `.controlproof/live-worker-probes/c4ae90212e32/result.json`; it is not a sealed N-02 bundle.
- Additional live proof: isolated probe `40ce0a1bc9e1` started an API and four workers with one shared loopback AI isolation profile, a new migrated DB and five new queues. The API health returned HTTP 200 and the same digest as the live worker/session proofs; ControlProof's `processing.paths.read` capability method returned `READY`. The probe stopped every process and removed its temporary DB/queues. This was not a full N-02 CLI preflight. A separate read-only check of the original parent's fault subject found `identity_verified`, zero consent and document effects, and no marker or consumed token; see `.controlproof/n02-safe-state-readonly-20261002.json` in WhyYou. The historical parent's `failed_request_effects_zero=false` and `RESTORE_FAILED` remain unchanged.
- Operational limit: these snapshots do not prove the absence of an uninstrumented worker at a later Run. Repeat process inventory and full preflight immediately before any child Run. `cleanup-confirm` still uses the H-03 reporting `target_safe` contract, so it must not be used to clear this N-02 block without an N-02-specific safety contract and evidence review. No block clearance, product remediation or new actual Run occurred in this sub-bundle.

### ID-003-07 — N-02 cleanup confirmation and remaining retest gate

- Date: 2026-10-02
- Task: T080-E3 complete; T080-E4 review open
- Decision: `cleanup-confirm` now routes the `n02-consent-order` block through the immutable, VERIFIED parent bundle and its unique `CONSENT_FAULT_RECOVERY` subject. It requires fresh matching evidence and a new read-only target probe: no active marker/token, invitation still `identity_verified`, no active or historical consent facts or invitation events, and no document effects. H-03 cleanup retains its existing route. Invalid/stale/mismatched evidence or unavailable target facts fail closed.
- Actual maintenance: the original local target passed the N-02 probe. The operator evidence SHA-256 is `406a87bc88cf2f0ec0bcff1799f7ad4b8099937e507484d11ad9e3d801649eef`; `cleanup-confirm` wrote a matching maintenance record for parent `15cef078-ee24-4f0e-91ef-381e0f7a1cc2` and removed only its N-02 restore block. Parent bundle re-verification remained VERIFIED (19 files). Its `RESTORE_FAILED`/`INCONCLUSIVE` result was not rewritten. Scoped 24 tests passed after intended RED; no full regression or new actual Run.
- Remaining gate: the current full preflight is `RUNNER_NOT_READY` with API stopped and processing observer disabled. Independently, `prepare_retest` still rejects any parent whose immutable state is `RESTORE_FAILED` or `manual_cleanup_required`, before it can inspect the new maintenance record. A read-only call reproduced that refusal. T080-E4 must specify and test how a verified N-02 cleanup record permits a child while an unresolved block, absent/mismatched record, or H-03/E-03 restore failure still refuses. This changes retest gate scope in `engine/retest.py`; no implementation was started in this bundle.

### ID-003-08 — Evidence-backed N-02 retest gate

- Date: 2026-10-02
- Task: T080-E4 complete; actual child Run remains `NOT_RUN`
- Decision: Only the N-02 profile may prepare a child from a `RESTORE_FAILED` parent after a matching `cleanup-confirm` record. `prepare_retest` first verifies the immutable parent bundle, then requires the exact parent/target/subject maintenance record, original cleanup evidence bytes with a matching SHA-256 and N-02 fault-lane safe-state facts, a valid confirmation time, and no new restore block. The CLI accepts `--cleanup-evidence` for this case. A future child link carries the cleanup confirmation reference; the parent's historical state and bundle are never rewritten. H-03/E-03 retain the unconditional restore-failed refusal.
- Evidence: seven intended RED cases before the new parameter existed; after implementation 23 scoped related tests plus one H-03 maintenance refusal test passed, changed-file Ruff and whitespace checks passed. A read-only call against parent `15cef078-ee24-4f0e-91ef-381e0f7a1cc2` and its original maintenance/evidence returned a valid preparation record with unchanged parent manifest bytes and evidence SHA-256 `406a87bc88cf2f0ec0bcff1799f7ad4b8099937e507484d11ad9e3d801649eef`. No child Run or full regression was executed.
- Limit: the original cleanup evidence is an ignored local artifact and must be retained for a later retest; a maintenance record alone cannot substitute for it. A later isolated full preflight started the API and four workers against a fresh DB/five queues, and 14/16 checks were READY. The two source/environment checks correctly remained `RUNNER_NOT_READY` because the WhyYou tracked checkout is dirty. The original DB's 325 pending outbox events were not processed; temporary infrastructure and processes were removed. The preflight transcript and separate interpretation are under ignored WhyYou `.controlproof/full-preflight-probes/48f0b3bf82a2/`. A clean-source full READY preflight and T080 root-cause classification remain open.
