# H-01 preparation data model

- `H01Case`: COMPANY_CONTROL / APPLICANT_HTTP / ANONYMOUS_HTTP / SYSTEM_BOUNDARY / AI_ASSISTANT.
- `H01Subject`: Run UUID, case, company/reviewer/stage UUID; deterministic applicant/invitation UUIDs
  in namespace `c63883d8-ec38-5f91-9c96-b16598f46db8`, names `<run>:<case>:applicant|invitation`.
  Each subject has an explicit unique reference and request UUID. No credential fields.
- `H01State`: company/invitation/report IDs, report_status, invitation_status, recruiting_stage_id,
  pipeline_row_version, full allowlisted final-review and request-related audit projections.
  Business digest excludes audit: recording a denial is permitted without changing a decision.
- `H01Observation`: subject/request identity, source boundary, response, before/after, identity and
  prerequisite checks, real denial audit/receipt presence. No raw HTTP bodies/tokens/exceptions.
- `H01Assessment`: existing PASS/FAIL/INCONCLUSIVE values with stable reason and changed fields.
- `H01PreparationResult`: observations, assessments, cleanup_succeeded and sanitized error code.
  Never a sealed Run, official verdict, live READY record or catalog result.

State comparisons first bind company/invitation to the expected subject. Unreadable/foreign states
are INCONCLUSIVE. Denied or error responses with changed owned business state are FAIL. Accepted
unauthorized requests are FAIL. Control requires one consistent review, expected stage, reviewed
status, one pipeline increment and company reviewer identity plus matching product success audit.
Missing AI or required evidence cannot PASS; cleanup failure overrides preparation acceptance.
