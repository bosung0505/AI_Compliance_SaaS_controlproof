# H-01 source baseline — 2026-10-18

Historical stage1 discovery snapshot; at that time no actual H-01 request, mutation or verdict. Current stage2 completion/source/remedy records are in ../../specs/006-h01-human-decision/actual-closure.md and validation.md. Initial source observations below are preserved, not current assertions about corrected code.

| Repository | Branch | HEAD | Initial status |
|---|---|---|---|
| ControlProof | fixes-and-remaining-work | 994dd3fbf6294090548e4b15b0fc0256df62d7f9 | clean |
| WhyYou | fixes-and-remaining-work | 33aa9967e6b69de4b3789d2009cae1d3eb798d74 | tracked clean; existing untracked runtime probes preserved |

## Confirmed source facts

- `reporting/api/company_routes.py` exposes POST `/v1/invitations/{id}/final-decisions` and
  constructs COMPANY_USER context only after the company principal provider validates a bearer.
- `shared/tenant.py` has COMPANY_USER, APPLICANT and SYSTEM; no AI actor type exists.
- `recruiting_assistant/api.py` also authenticates the company user. Its caller identity is not
  the same claim as the assistant being authorized to execute final decisions.
- `reporting/domain/review.py` rejects non-COMPANY_USER for final/recruiting-stage decisions.
- `FinalDecisionService.record` checks report presence, moves the recruiting stage, records
  HumanReview, marks reviewed, writes audit and idempotency. Guard failure may occur after a
  stage move; the real transaction rollback and post-request state must be observed.
- `shared/database.py` commits responses below500 and rolls back exceptions/server failures.
  A helper must catch denial outside the transaction, never swallow it before rollback.
- `tests/integration/reporting/test_human_only_decision.py` uses an in-memory reporting
  repository. Its SYSTEM denial is useful automatic evidence, not an actual-stack verdict.
- CP `WhyYouDecisionAdapter` drives final decision and final accept/reject batch moves using
  company credentials; a different company_user_id is refused by the adapter. Changing a
  subject field would test the adapter guard rather than WhyYou actor authorization.
- CP `WhyYouStateAdapter`'s historical actor label is a literal company_user in SQL. It is
  unsuitable as independent proof of the actual actor; H-01 collects stored reviewer/audit identity.
- Existing fixed models support analysis/report tasks, not the recruiting assistant answer task.
  Stage 1 must not label an unsupported answer task as a successful AI authorization test.

## Decisions for preparation

1. Isolated httpx.Request objects prevent ambient company bearer/auth/cookies from contaminating
   applicant/anonymous calls. Applicant identity must first succeed on its own product endpoint.
2. SYSTEM internal helper invokes the actual supplied FinalDecisionService in a transaction,
   disabled unless explicitly local/test and bound to canonical Run/case-owned subject IDs.
   It adds no API endpoint, role, product guard or application composition changes.
3. Preparation driver uses an explicit lifecycle protocol for normal report preparation and
   cleanup. Actual DB provisioning, official profile/bundle wiring and real assistant binding are
   stage2 tasks; missing AI observation blocks overall PASS.
4. Observe company/invitation-scoped pipeline state, HumanReview details and request-linked
   audit facts. Never derive an actor from the desired scenario outcome.
5. Existing H-03 accept/reject batch routes remain an explicit actual-stage coverage decision;
   stage1 preparation targets the final-decisions operation only and cannot claim all write routes.

No external research or new technology selection is needed; existing Python/httpx/SQLAlchemy/
Pydantic contracts are reused. These are source facts and preparation decisions, not proof that
any unauthorized actor was actually stopped in the running WhyYou service.

## Subsequent stage1 findings

The historical in-memory H-01 test could not collect because that repository implementation
had already been removed. The test is now restored to current SQL persistence with SQLite,
SYSTEM/APPLICANT roles and zero-review assertion; no product boundary was changed.
Actual caller credentials use a company Bearer and an applicant session cookie, not an
applicant Bearer. Policy GET proves session liveness only; stage2 must also prove owned
applicant/session binding. Current preparation leaves those live bindings explicitly pending.
