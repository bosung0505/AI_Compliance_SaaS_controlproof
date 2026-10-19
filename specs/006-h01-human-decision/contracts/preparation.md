# H-01 stage-1 interfaces

## Preparation manifest

`scenarios/_H-01-preparation.yaml` uses `controlproof.h01-preparation.v1` and lists all five
case IDs once. It is an opt-in preparation contract, not a registered Run scenario/profile.
`scripts.h01_prepare` only validates/prints a synthetic plan and NOT_RUN, never starts a service.

## Lifecycle / driver

The lifecycle provides `prepare(subject)`, `observe(subject)`, `attempt(subject)` and
`cleanup(subjects)`. Prepare must produce a valid scoped report through the existing product
pipeline in actual stage2. Each subject is registered for cleanup before preparation begins.
The driver observes before/after even when attempt raises, sanitizes exception types, always
cleans registered subjects and never lets a cleanup error hide an earlier error. No live binding
is supplied in stage1; automatic fake lifecycles test orchestration only.

## HTTP adapter

Dedicated httpx.Request + `send(auth=None, follow_redirects=False)`; no inherited headers,
cookies or authentication. Company bearer / applicant session cookie are selected explicitly;
anonymous has neither. The company endpoint ignores applicant cookies by design.
Only POST final-decisions is allowed. Request/trace/idempotency are derived per subject.
Body contains expected pipeline version/stage; raw response/error messages and credentials are
never returned. Response is ACCEPTED only2xx, DENIED only401/403;409/422/5xx are ERROR.
Applicant session liveness is checked through GET `/v1/applicant/consents`. Its response does not
identify the applicant, so the lifecycle must ALSO bind the session to this owned applicant through
its trusted session fixture/provider. A successful policy GET alone is not identity proof.
Bad, expired or another applicant's credential cannot satisfy the identity precondition.

## DB observer

Read-only SQLAlchemy connection, explicit company AND invitation filters for invitations/reports/
HumanReview; audit limited to matching company/request ID. No literal invented actor type;
retain actual reviewer and audit actor fields. Unknown/missing sources fail closed.

## Internal SYSTEM helper (WhyYou)

`runtime/controlproof_h01.py` is not a router or product guard. Disabled by default; require
APP_ENVIRONMENT local/test, `CONTROLPROOF_H01_PROBE_ENABLED=true`, explicitly matching company,
canonical SYSTEM_BOUNDARY applicant/invitation IDs derived from Run UUID. Caller supplies an
existing decision-service factory and real transaction context. Constructs SYSTEM context only;
denial propagates through transaction rollback before normalization. No company-user elevation,
no arbitrary actor, and no synthetic AI role. Returns safe identifiers/response/error type only.

## Stage2 binding gates

Before actual: register profile/evidence/CLI integration; clean committed sources and isolated
services; normal report lifecycle + owned cleanup; actual company/applicant identity proofs;
real SYSTEM transaction binding; actual assistant operation with a compatible fixed answer model
if required (old fixed models lack that task); refusal audit/observer facts; all final-decision
and final accept/reject batch routes coverage explicitly resolved. Missing items are readiness
gaps / INCONCLUSIVE, never hidden skips or NO_TEST_TARGET. No existing data is written in stage1.
