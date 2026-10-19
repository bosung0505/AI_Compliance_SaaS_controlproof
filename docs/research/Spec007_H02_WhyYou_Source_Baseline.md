# H-02 source discovery — 2026-10-19

Historical stage1 discovery below. Current actual/remedy/source closure is in ../../specs/007-h02-capability-surface/actual-closure.md; initial write candidate was reproduced as FAIL, then corrected and child-tested.

Stage1 source inspection, no actual H-02 product execution. Both original workspaces remain
fixes-and-remaining-work. CP HEAD994dd3fbf6294090548e4b15b0fc0256df62d7f9 /
WhyYou HEAD33aa9967e6b69de4b3789d2009cae1d3eb798d74. Both contain intended uncommitted H-01
stage1+2 source changes; WhyYou also retains old untracked .controlproof probes. Preserve all of them.
HEAD does not describe inspected current bytes; preparation inventory adds full Python tree hashes.

## Confirmed source facts (WhyYou backend/src/interview_evidence)

- `recruiting_assistant/api.py:create_assistant_router`: POST search/answers/answers/stream;
  pipeline shortcut reads stages and invitations. Audits are appended. Company principal caller,
  no separate AI actor. POST and audit persistence are not hiring decision writes.
- `recruiting_assistant/application.py:AssistantAnswerService.answer`: search → build prompt →
  model.generate → parse answer/source IDs → return answer; no tool dispatcher seen in this method.
- `recruiting_assistant/prompt.py`: build_answer_prompt currently emits system/messages/token/temperature
  contract; answer schema has answer/source_ids. No function/tool list in this builder. This fact alone
  does not prove the entire assistant is unable to mutate hiring decisions.
- `shared/aws_clients/production.py:AwsBedrockModel.generate`: serializes model input and invokes
  model provider; response is JSON. Review downstream response handling, not model text only.
- `runtime/production.py:create_production_runtime`: real assistant search/answer/projector composition;
  reader protocol receives actual company/hiring service objects; Runtime.worker_handlers has separate
  invitation_email/media_postprocess/report_generation/privacy_deletion helpers.
- `runtime/worker.py:EVENT_QUEUE_ROUTING` and `create_production_worker_runtime` contain distinct
  routed-event and handler maps. `create_worker_runtime` intersects them per queue. A routing entry
  alone is not a handler. Real `worker.py:main` selects environment worker; in-memory parity worker
  is not sufficient to inspect the production composition.
- `shared/messaging/worker.py:MessageConsumer.consume_once`: resolves subscribed handler by event
  name; missing handlers are acknowledged as ignored. Actual runtime membership still needs stage2
  evidence. Payload-driven calls and indirect dependencies require downstream review.
- Workers perform ordinary writes: analysis state, completed-interview state, report storage/search
  projection, privacy deletion, capacity configuration. `InterviewCompletedEventHandler` advances
  invitation state ready→interviewing→completed. These are not automatically final-accept/reject.
- Actual hiring sinks: `company_management/application/hiring_service.py:move_applicants`,
  `reporting/application/final_decision_service.py:record`, `integration/reporting_company.py:
  ReportingHiringBoundary.move_to_recruiting_stage`. H-01 human guard is present in dirty current
  source. H-02 must inspect exposure even when a sink currently rejects SYSTEM.

## Stage2 gates

Enumerate/reconcile every registration including stream/shortcut/API helper/queue-only entries;
trace actual methods and model output dispatch; classify auxiliary vs hiring writes with source-bound
evidence; verify actual bound objects/consumer membership on clean frozen sources; independently
observe low-score human selection/high-score rejection. Source-only inventory is preparation and
all entries remain UNREVIEWED. No current H-02 PASS/FAIL conclusion or target remedy is made.

## Review candidates discovered before actual H-02

1. `_pipeline_answer` calls HiringService.list_recruiting_stages/list_invitations, which invoke
   ensure_default_stages. This creates missing stage rows and backfills legacy invitations with
   null recruiting_stage_id; _default_stage_name maps REVIEWED/DELETED to 최종합격. A reader name
   therefore does not prove no downstream hiring write. Stage2 must preserve/evidence legacy-null
   vs assigned controls and distinguish initialization from a decision change. H-01's already-prepared
   subjects do not cover this. Do not pre-fix or relabel old H-01 results based on discovery alone.
2. API helper privacy_deletion is lane_d.deletion_service. The bounded collector explicitly leaves
   UNRESOLVED_TARGET. Manual source chain: production constructs DeletionService and passes it into
   create_lane_d_runtime; reporting/api/company_routes.py returns LaneDRuntime.deletion_service via
   `service = deletion_service or DeletionService(active_repository)`. Actual selected object/effects
   require stage2 evidence. This is a collector limit, not a product FAIL.
3. FinalDecisionService.record does not compare applicants' score ranks in the inspected method;
   it obtains the report and records the requested stage. The low/high human control is still NOT_RUN.

Snapshot:204 Python files,161-file local import closure,42 entries, all UNREVIEWED.
Tree SHA256 fce256e1d3f8975c8dbc709522d57fedf584732bef30c6ab84bb8bc351c810f6.
Preparation BLOCKED on the one indirect privacy_deletion target; issue not suppressed for readiness.
