# Spec 003 Implementation Decisions

## Status

- Implementation foundation: in progress
- Initial actual N-02 Run: `15cef078-ee24-4f0e-91ef-381e0f7a1cc2`, sealed and `VERIFIED`; overall `RESTORE_FAILED` / `INCONCLUSIVE`
- Evidence-gated product remediation: `PENDING_T080_CLASSIFICATION`; no product change. No valid
  child Run yet: T084 attempt 2 child `e2e8e71d-3ba0-402e-a914-6cf26268582b` sealed `INVALID`
  (ID-003-13)

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
| T080 | A5~A7 or runner/restore ownership | Yes | `PROPOSED` `RUNNER_OR_OBSERVER_DEFECT`; ID-003-09, file-scope approval pending |
| T081 | document analysis | Yes | `NOT_REQUIRED` proposed; parent A2 PASS (ID-003-09) |
| T082 | recording | Yes | `NOT_REQUIRED` proposed; parent A3 PASS (ID-003-09) |
| T083 | AI assessment/reporting | Yes | `NOT_REQUIRED` proposed; A4 effect was runner-created (ID-003-09) |
| T084 | child retest or parent reverify | Yes | No valid child yet: attempt 1 aborted before sealing (ID-003-11, ID-003-12); attempt 2 sealed `INVALID` (ID-003-13) |

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

### ID-003-09 — Parent A4~A7 root cause: seed defect and runner-created effect

- Date: 2026-10-04
- Task: T080 classification (+ T081~T083 branch decisions)
- Requirement/assertion: FR-026~033, N02-A2~A7, SC-010
- Status: `PROPOSED`. The classification is evidence-backed; the fix touches `seeds/n02_subjects.py`,
  which is **outside T080's listed fix files**, so it needs team approval before T080 is checked off.
- Source baseline: received ControlProof `9f61713`, WhyYou `c8e9970`; parent Run sources
  ControlProof `b92b9ad`, WhyYou `94ad7f2`
- Triggering parent Run: `15cef078-ee24-4f0e-91ef-381e0f7a1cc2` (manifest SHA-256
  `d2306f3cd6e2b15ce87d94e4844a2278c7ea3c0b3c052a2aac45e1bff8f2bc9b`, re-verified `VERIFIED`)
- Exact evidence artifacts: sealed `policy-and-consent.json` (both NORMAL_ORDER and
  CONSENT_FAULT_RECOVERY remain `identity_verified`, row_version 1, zero consent facts), empty
  `faults.jsonl`/`fault-receipts.jsonl`/`causal-*.jsonl`, `recovery.json`, `protected-effects.jsonl`;
  plus the isolated-DB diagnostic rows dated 2026-10-04 in `validation.md`.
- Root-cause class: `RUNNER_OR_OBSERVER_DEFECT` for every direct FAIL, from two runner defects.

| Defect | Cause | Affected | Status |
|---|---|---|---|
| R1 seed | `build_n02_seed_plan` wrote `submission_requirements=[]` on the position and all six invitations. WhyYou loads an invitation through `SubmissionRequirementSet`, which raises a `ValueError` subclass for an empty set; the consent route maps `ValueError` to 422. The request failed in `get_invitation`, before `save_consent()` and therefore before the consent fault hook. | A5 (normal consent never committed), A6 (fault never triggered; commit 422), A7 (`normal_retry_succeeded=false`) | Fixed on local branch `yeonwoo/003-t080-seed-requirements`; not pushed |
| R2 probe input | `protected_processing.py` inserted `report.generation_requested` itself and the parent counted it as a protected effect. | A4, A6 (`leaked_effect_ids`), A7 (`failed_zero=false` via `failure_effects`) | Already corrected for future Runs by T080-E1 (ID-003-04) |

- Isolated reproduction: WhyYou `94ad7f2` on a fresh PostgreSQL 16 + pgvector DB, production runtime
  with every AI/storage/email/principal port stubbed and no queues, exact `b92b9ad` seed for the parent
  Run ID. Both lanes' POST returned 422 with the `SubmissionRequirementSet` message. Replacing only the
  NORMAL_ORDER invitation's requirements with WhyYou `DEFAULT_SUBMISSION_REQUIREMENTS` turned the same
  POST into 201 with exactly one consent record, transition and `invitation.consent_completed` event.
  On delivered WhyYou `c8e9970` (consent route, submission-material model and migrations unchanged
  from `94ad7f2`) the corrected seed produced 201 for both lanes. This is a diagnostic in an isolated
  DB, **not** an N-02 Run, bundle or verdict; it is not `whyyou-local`.
- Decision: Seed position and invitation rows with an explicit copy of WhyYou's default requirement
  set (resume and cover letter required, three optional materials, all enabled). No WhyYou product
  file changes. The target's 422 on an invariant-violating invitation is not a consent-control
  defect: the product API cannot create such an invitation.
- Branch outcomes: T081 and T082 `NOT_REQUIRED` (parent A2/A3 PASS with 403 `CONSENT_REQUIRED` and no
  new effect). T083 `NOT_REQUIRED` (the only A4 effect was runner-created; the parent proves no target
  AI-assessment bypass). All three are re-observed by the T084 child.
- Alternatives considered: (a) map the 422 message into the E1 reason allowlist only — rejected, it
  would label the next Run without letting consent commit; (b) seed `NULL` — rejected, the column is
  `NOT NULL`; (c) change WhyYou to tolerate empty sets — rejected, product semantics change.
- Safety and compatibility impact: seed digest changes for new Runs only; the parent bundle and its
  verdict are untouched. Without R1, the T084 child would hit the identical 422, because WhyYou
  `c8e9970` did not change the consent path.
- Regression command and result: `pytest -q tests/contract/test_n02_seed_adapter.py` EXPECTED RED 1
  failed/3 passed, then 4 passed; Linux full regression 441 passed; Ruff PASS.
- Open limits: the bypass lanes' 403 PASS was observed with invalid invitations; T084 must re-observe
  A2/A3 with the corrected seed. Separately observed, not in N-02 scope: the consent POST discards
  `Idempotency-Key`, so a resend after success returns 422 instead of replaying the 201.
- Child Run / parent immutability result: no child. Parent re-verified `VERIFIED`, 19 files.

### ID-003-10 — N-02 executor did not apply the snapshot timing policy

- Date: 2026-10-04
- Task: T085 (partial); prerequisite for T084
- Requirement/assertion: SC-006, SC-008; contract `scenario-profile-v3.md` Timing policy; N02-A1~A7
- Status: `PROPOSED` (scoped tests pass; team review required before T084)
- Finding: `scenarios/N-02.yaml` freezes poll 2 s, 3 consecutive stable reads over >= 4 s, fault TTL
  600 s, restore 120 s, Run 540 s and verify 60 s, but `engine/executors/n02.py` read none of them.
  Every effect, consent-state and observer-receipt read was a single immediate read (the parent Run
  spans 0.45 s in `run.json`); the consent fault marker TTL was a hard-coded 5 minutes; the only wait
  was a hard-coded 2.0 s/0.05 s loop for AI-assessment start receipts in `protected_processing.py`.
  Consequence: "no effect" for A1~A3/A6 rested on one read taken before asynchronous workers could
  act, and the normal-order chain (A5) could miss worker start receipts. This is a
  `RUNNER_OR_OBSERVER_DEFECT` risk, not an observed target outcome; it did not cause the parent's
  FAILs (ID-003-09), but the first child Run would be the first to exercise these paths.
- Decision: `N02Executor.execute()` wraps `read_effects`, `read_state` and
  `read_processing_receipts` in `_StableReads`; `_Stabilizer` accepts a value only after
  `stability_consecutive` equal `state_digest`/receipt-id sets spanning `stability_seconds`, sleeping
  `poll_seconds` between reads, and raises `N02RunDeadlineExceeded` at `started_at +
  run_deadline_seconds`. The consent fault marker uses `fault_ttl_seconds`. Adapter failures pass
  through unchanged. Direct `collect_us*` calls (unit tests) are not wrapped.
- Not yet done (T085 stays open): `environment_restore_deadline_seconds` (120 s) and
  `bundle_verify_deadline_seconds` (60 s) are still not enforced by the N-02 path; the hard-coded
  2.0 s AI-assessment receipt loop remains. A deadline breach currently raises after the existing
  cleanup path instead of sealing an `INCONCLUSIVE` bundle; whether to seal it is a team decision.
- Tests: `tests/integration/test_spec003_timing.py` (6) — collection RED against the received engine
  (missing stabilizer; TTL 300 s), GREEN after. `tests/conftest.py` gives the N-02 system clock a
  virtual offset so existing tests do not sleep for real. Linux full regression 447 passed; Ruff PASS.
- Operational impact: a real N-02 Run now takes at least several stable-read windows (~4 s each) and
  stays inside the 540 s Run budget only if the local stack settles; T088 must measure it.

### ID-003-11 — Fault-lane recovery attempts reused the failure-phase identity

- Date: 2026-10-04
- Task: T084 prerequisite (runner defect found by the first T084 attempt)
- Requirement/assertion: N02-A6, N02-A7, FR-033~037
- Status: `PROPOSED`
- Triggering event: first `retest 15cef078-…` on the teammate PC (preflight 16/16 `READY`,
  ControlProof `2d1f66f`, WhyYou `c8e9970`) completed US1 and US2, then aborted in `collect_us3`
  with `N02ExecutionError: N-02 processing attempt failed: N02_ASSESSMENT_EVENT_WRITE_FAILED`.
  No bundle was sealed, so there is no verdict to preserve; the attempt and its cleanup state are
  recorded in `validation.md`.
- Root-cause class: `RUNNER_OR_OBSERVER_DEFECT`. `_attempt_id` derived request and outbox-event
  identities from (run, lane, path) only. The CONSENT_FAULT_RECOVERY lane attempts every path twice
  on the same subject (failure phase for A6, recovery for A7), so the recovery AI-assessment insert
  reused the failure-phase `outbox_event_id` and hit the primary key. The same reuse sent identical
  `Idempotency-Key` values for the document and recording paths, which WhyYou could treat as a
  replay. The parent never reached recovery (ID-003-09) and the fakes did not enforce the key, so
  this path had never executed.
- Decision: the processing adapter keeps a per-(subject, path) attempt ordinal; the first attempt
  keeps its original identity and later attempts append `attempt-N`. Runner-created AI-assessment
  inputs accumulate per lane and all are excluded from target effects; the latest one drives
  start-receipt matching. No WhyYou change.
- Tests: three contract tests in `tests/contract/test_n02_processing_adapter.py` with a fake that
  enforces the outbox primary key — EXPECTED RED 3 failed/6 passed, then 9 passed. Linux full
  regression 450 passed; Ruff PASS.
- Open limit: a failure-phase runner input left `pending` in the outbox may still be published and
  processed by the worker after consent is restored. If that produces a second recovered effect,
  A7 will show it; that is target behaviour to classify from the child evidence, not a runner fix.

### ID-003-12 — Lane teardown could never succeed after consent was committed

- Date: 2026-10-04
- Task: T084 prerequisite (runner defect behind the block left by T084 attempt 1)
- Requirement/assertion: SC-006, contract `whyyou-n02-adapter.md` teardown, N02-A7
- Status: `PROPOSED` (extends the contract's "seed correlation allowlist" to rows that reference it)
- Finding: `teardown_lanes` deleted only the seed and overlay rows. WhyYou foreign keys are
  `NO ACTION`, so once a lane committed consent, `invitation_state_history`/`consent_records`
  referenced the seeded invitation and the delete failed with `ForeignKeyViolation`. Reproduced on an
  isolated PostgreSQL with the WhyYou `c8e9970` schema. Consequence: every Run that reaches a
  consented lane ends `N02_TEARDOWN_FAILED` → `RESTORE_FAILED` → block, including a fully correct
  child. This is why T084 attempt 1 left `whyyou-local--n02-consent-order.json`.
- Root-cause class: `RUNNER_OR_OBSERVER_DEFECT`.
- Decision: before deleting each seed/overlay row, `_delete_dependents` reads the PostgreSQL FK
  catalog and removes, children first, only rows reachable by foreign key from that Run's own seeded
  row. Shared rows (company, company user) are never a starting point. Rows without a foreign key
  (e.g. outbox events) stay as synthetic residue.
- Verification: isolated PostgreSQL, two seeded Runs; Run A had two consented lanes (2 consent
  records, 2 state-history rows). New teardown for A committed without error and removed A's
  invitations, consent records and history; Run B's six invitations, the company and company user
  were untouched; two outbox events remained as residue. Contract test with a fake catalog
  connection; existing fakes now return an empty catalog result. Linux full regression 451 passed
  (three consecutive runs; one earlier run showed a single failure that did not recur and was not
  captured); Ruff PASS.
- Block handling: `cleanup-confirm` requires the blocked Run's sealed bundle, which an aborted Run
  does not have, so the documented path cannot clear this block (tooling gap, recorded here). On the
  teammate PC the local target is synthetic and disposable: the operator destroys and recreates the
  WhyYou containers and volumes, archives the block file and the aborted Run's fault receipt outside
  both checkouts, and records it in `validation.md`. This must never be done on a shared target.

### ID-003-13 — Consent fault receipt could not be linked to the failed request

- Date: 2026-10-05
- Task: T084 prerequisite (runner defect found by T084 attempt 2)
- Requirement/assertion: N02-A6, EV3-07 (trigger receipt tied to the failed consent request)
- Status: `PROPOSED`
- Triggering event: second `retest 15cef078-…` on the teammate PC (preflight 16/16 `READY` at
  2026-10-05T02:28:14Z, ControlProof `c6e5619`, WhyYou `c8e9970`) ran to the end and sealed child
  `e2e8e71d-3ba0-402e-a914-6cf26268582b`. The executor's post-seal `verify_bundle` returned `INVALID`
  with the single mismatch `fault-receipts.jsonl:failed-request`, and the CLI raised
  `N02ExecutionError: N-02 sealed bundle failed verification`. The INVALID bundle is preserved
  unchanged as evidence of this defect; it is neither edited nor re-run.
- Root-cause class: `RUNNER_OR_OBSERVER_DEFECT`. The consent commit sent the runner request identity
  only as `Idempotency-Key`. WhyYou's applicant scope takes the request id from a UUID `X-Request-Id`
  header and otherwise falls back to the applicant session id, and the consent fault guard writes
  that context id into the receipt. The receipt therefore carried the session id, never the
  executor's `failed_request_id`. The parent never triggered the fault (consent POST 422,
  ID-003-09), attempt 1 aborted before sealing, and the fakes record the runner id directly, so this
  link had never been checked against WhyYou.
- Decision: the consent commit also sends `X-Request-Id` set to the runner request id (the uuid5 the
  executor already records). Processing attempts are unchanged: their receipts are linked by path
  and event id, not by request id. No WhyYou, verifier or judge change.
- Alternatives considered: relaxing the verifier link (rejected: EV3-07 must tie the trigger to the
  exact failed request); keying the WhyYou receipt to `Idempotency-Key` (rejected: a product-side
  change without a product defect).
- Open item for review (unchanged): the judge treats a receipt/request mismatch as A6
  `INCONCLUSIVE`, while `_verify_spec003_facts` treats the same fact as an `INVALID` bundle in every
  case. An honestly recorded mismatch therefore aborts after sealing instead of producing a
  verified `INCONCLUSIVE` child.
- Tests: a contract test in `tests/contract/test_n02_consent_adapter.py` whose fake applies the
  target rule (UUID `X-Request-Id`, else session id) — EXPECTED RED 1 failed/6 passed (session id
  recorded), then 7 passed. Linux full regression 452 passed; Ruff check PASS; format check
  unchanged (78 pre-existing files).
