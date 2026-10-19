# Spec 007 — H-02: AI에 채용 결정 변경 기능이 연결되어 있는가

Current: **Complete — H-02 stage2 LOCAL_EMULATED actual PASS, VERIFIED19, restore SUCCEEDED, independent44-table residue0, shared browser QA complete (2026-10-19).** See [actual closure](actual-closure.md) and [validation](validation.md). Earlier stage1 scope/status below is historical, preserved as evidence of sequence.

**Branch**: fixes-and-remaining-work (user-authorized continuing branch)
**Created**: 2026-10-19
**Status**: Complete in documented LOCAL_EMULATED scope; stage1 NOT_RUN history follows.

## User stories and acceptance

1. **US1 / P1 — 빠짐없는 기능 목록**: 검증자는 AI 어시스턴트 API·모델 입출력·실제 조립과
   워커의 이벤트 라우팅·실제 handler 연결 목록을 출처와 함께 읽는다. 이름만 검색하거나
   in-memory worker만 검사해서 운영 조립을 검사했다고 주장하지 않는다.
2. **US2 / P1 — 저장과 채용 결정의 구분**: 보고서·검색색인·감사·자료 처리·면접 진행·삭제·용량
   처리는 그 자체로 채용 결정이 아니다. 최종 결정 기록 또는 채용 파이프라인 변경 가능성을
   각 연결의 실제 호출·위임 경로로 구분한다. 알 수 없는 연결은 안전하다고 추정하지 않는다.
3. **US3 / P2 — 이해할 수 있는 결과**: stage2 화면은 기능/처리 내용/채용 결과 변경 가능 여부/
   근거를 보여준다. 사람의 결정이 AI 점수 순위에 강제 종속되지 않는지도 별도 관찰한다.

## Clarified scope — 2026-10-19

- User approved the previously explained two-stage work; this turn authorizes stage1 discovery,
  specification, read-only collector preparation and automatic validation only.
- H-01 tested attempted writes/denial. H-02 inspects exposed contracts, registration and downstream
  dispatch. A present final-decision tool is a problem even when a permission guard currently denies it.
- Current assistant is search + answer JSON, not an assumed function-calling agent. HTTP POST is not
  evidence of hiring mutation. Text claiming a decision is not execution of that decision.
- Company authentication is caller identity, not a new AI role. Concrete company/hiring objects have
  broader methods than their reader protocols: stage2 must inspect usage and model-output dispatch,
  not equate type annotations with permission restrictions.
- Source inventory collection is preparation, not an official Run. No READY/catalog profile or PASS
  promotion; 12/6/3/3 stays unchanged. No WhyYou product remedy before preserved actual findings.
- No external model, new model fixture, DB request, Docker startup, product import or source execution
  is necessary for stage1. No new dependency or source checkout is needed.

## Functional requirements

- **FR-001**: Capture source HEAD, branch, dirty fact and deterministic Python tree hashes separately.
  Dirty H-01 work is preserved; HEAD alone is not the identity of these inspected bytes.
- **FR-002**: Read only the target's backend/src/interview_evidence Python files, never .env/runtime
  logs/credentials; reject symlink/reparse escapes; do not import or execute target code.
- **FR-003**: Collect assistant routes and composition, prompt keys and response fields with source
  file/line/end/hash. An absent tool list alone cannot prove no decision-changing capability.
- **FR-004**: Enumerate production worker routing, registered handlers, routing-only events and API
  runtime helper handlers separately. Resolve direct class construction and local variable aliases;
  keep unresolved/dynamic/duplicate registrations explicit and blocking preparation readiness.
- **FR-005**: Attach selected target definitions' syntactic calls and transitive local import source
  closure as review aids. They are not a whole-program call graph or an automatic security proof.
- **FR-006**: Missing anchors, syntax/read errors, unknown registrations and source drift cannot be
  silently dropped. Empty lists are not a PASS. Stable issue codes expose no exception payloads.
- **FR-007**: Preparation output always says H-02 / stage1 / NOT_RUN / no product verdict. All
  inventory entries remain UNREVIEWED; collector readiness means ready for source review only.
- **FR-008**: Define stage2 evidence classification READ_ONLY / AUXILIARY_WRITE /
  HIRING_DECISION_WRITE / UNKNOWN. UNKNOWN or incomplete coverage blocks PASS. A decision write
  exposed to assistant/worker fails even if authorization denies it. Ordinary allowed persistence
  requires specific downstream source evidence, not a name allowlist.
- **FR-009**: Stage2 records actual composition/consumer membership and output handling on frozen
  clean sources; detects source/evidence drift and preserves first FAIL before a remedy child.
- **FR-010**: Stage2 separately tests that an authorized human may select a lower-scored applicant
  and reject a higher-scored applicant; no automatic threshold or rank rule is invented.
- **FR-011**: Preserve existing profiles, bundles, source SHAs and UI styles. No new public product
  endpoint/auth role and no H-02 official execution/profile in stage1.
- **FR-012**: Converge specification, tasks, validation, traceability, handoff, matrix, README,
  product brief and decision log at the truthful stage boundary.

## Stage2 planned assertions / evidence

| Assertion | Question | Required evidence |
|---|---|---|
| H02-A1 | Are all relevant registrations accounted for? | frozen source manifest, actual API/model/worker bindings and queue/consumer reconciliation |
| H02-A2 | Can assistant input/output dispatch a hiring write? | every route incl. stream/shortcut, prompt/response contracts, concrete dependencies and downstream dispatch review |
| H02-A3 | Can subscribed worker contracts dispatch a hiring write? | routing/handlers/helper inventory, caller/event/payload boundaries and downstream read/write trace |
| H02-A4 | Are classifications complete and grounded? | source-bound per-entry review, explicit allowed persistence vs hiring mutation, unknowns block PASS |
| H02-A5 | Is the human's decision independent of score rank? | owned synthetic low/high reports, human final actions and DB/audit observations |
| H02-A6 | Are identity, integrity and restoration evidenced? | source hashes, sealed evidence, zero mutation for static check; owned cleanup for functional control |

## Success criteria

- **SC-001**: Preparation deterministically enumerates the inspected composition without executing it.
- **SC-002**: Adversarial tests catch new/duplicate/dynamic/missing registrations, malformed source,
  source drift and unresolved targets; unknown cannot look like a safe classification.
- **SC-003**: CLI emits a usable preparation inventory while preserving NOT_RUN and target bytes.
- **SC-004**: Stage1 docs agree on scope/status and stage2 gates. Whole Spec remains incomplete.
- **SC-005**: Stage2, when authorized, closes A1~A6 with immutable evidence and readable shared UI.

Out of scope: AWS IAM/runtime assurance, arbitrary third-party plugins, external AI quality,
whole-Python security proof, N-01/N-03, Spec005 full usability closure and publication/main merge.
