"""N-03 official execution: stale policy identifier submission, re-read commit and past record (Spec 009).

Steps follow plan.md §4. The stale identifier is made without a real policy swap (N03-L1); N03-U1~U3 are carried
as unverified scope and never judged.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid5

from engine import n03
from engine.executors.spec009 import (
    Spec009Executor,
    adapter_code,
    policy_identifier,
    state_row,
    subject_identity,
)
from engine.models import ConsentPolicySnapshot, ExecutionProfile, N03LaneId

PROFILE = ExecutionProfile.N03_STALE_CONSENT_V1
UNVERIFIED_SCOPE = (
    "AWS_NOT_RUN",
    "N03_U1_POLICY_SWAP_INJECTION",
    "N03_U2_NEAR_SWAP_SUBMISSION",
    "N03_U3_ANALYSIS_POLICY_ATTRIBUTION",
)
LINKS = {
    "EV9-01": {"environment.snapshot.json", "target.snapshot.json", "scenario.snapshot.yaml", "n03-scope.json"},
    "EV9-02": {"subjects.json", "n03-lanes.json"},
    "EV9-05": {
        "n03-stale-attempt.json",
        "n03-stale-before.json",
        "n03-stale-after.json",
        "n03-latest-commit.json",
        "n03-past-before.json",
        "n03-past-after.json",
    },
    "EV9-06": {"recovery.json"},
    "EV9-07": {"run.json", "assertions.json", "judgement.json"},
}
_REQUESTS = UUID("4c7f6a2e-9b13-5e08-a0d4-2b9e6c1f0303")


def commit_facts(result) -> dict[str, Any]:
    """Status code when the adapter exposes one; ok=True without a code is recorded as class 2xx."""
    data = dict(result.data)
    status = data.get("status_code")
    status = status if type(status) is int else None
    if result.ok:
        response_class = "2xx"
    elif status is not None:
        response_class = "2xx" if 200 <= status < 300 else "non-2xx"
    else:
        response_class = None
    return {
        "response_status": status,
        "response_class": response_class,
        "adapter_code": result.code,
        "durable_state": str(data.get("durable_state") or ("COMMITTED" if result.ok else "UNKNOWN")),
    }


class N03Executor(Spec009Executor):
    profile = PROFILE
    tag = "N03"
    block_subject = "n03-stale-consent"
    seed_kind = "n03-session-lanes-v1"
    fault_kind = "n03-stale-policy-submission-v1"
    unverified_scope = UNVERIFIED_SCOPE
    links = LINKS
    scope_file = "n03-scope.json"
    judge = n03
    api_capabilities = ("consent.policy.read", "consent.commit.write")
    db_checks = (
        ("consent_records", "consent_record_id, policy_version, evidence_digest, accepted_at", ("consent.state.read",)),
        ("applicant_access_sessions", "session_hash", ("n02.subjects.seed", "n02.subjects.teardown")),
        ("invitation_state_history", "to_status", ("consent.state.read",)),
    )

    def _initial_record(self, run_id, lanes):
        seed = self.adapters.spec009_seed
        stale = subject_identity(seed.subject_for(run_id=str(run_id), lane_id=N03LaneId.STALE))
        return {
            "past_setup": {"policy": "NOT_ATTEMPTED", "commit": "NOT_ATTEMPTED"},
            "stale_attempt": {
                "subject": stale,
                "current": None,
                "submitted": None,
                "response_status": None,
                "response_class": None,
                "adapter_code": "NOT_ATTEMPTED",
                "durable_state": "NOT_ATTEMPTED",
            },
            "stale_before": None,
            "stale_after": None,
            "latest_commit": {
                "subject": stale,
                "reread": None,
                "response_status": None,
                "response_class": None,
                "adapter_code": "NOT_ATTEMPTED",
                "stored": None,
                "consent_record_id": None,
            },
            "past_before": None,
            "past_after": None,
        }

    def _observe(self, run_id, lanes, record, step, checkpoint):
        seed, consent = self.adapters.spec009_seed, self.adapters.spec009_consent
        stale = seed.subject_for(run_id=str(run_id), lane_id=N03LaneId.STALE)
        past = seed.subject_for(run_id=str(run_id), lane_id=N03LaneId.PAST)

        # (2) past: complete a consent with the current policy, then snapshot it.
        policy = consent.read_policy(subject=past)
        step("seed-lanes", "BASELINE", "past", "read_policy", policy)
        record["past_setup"]["policy"] = adapter_code(policy)
        if isinstance(policy, ConsentPolicySnapshot):
            committed = consent.commit(
                subject=past,
                policy=policy,
                request_id=str(uuid5(_REQUESTS, f"{run_id}:past:commit")),
                trace_id=f"controlproof:{run_id}:past",
            )
            step("seed-lanes", "BASELINE", "past", "commit", committed)
            record["past_setup"]["commit"] = committed.code
            if committed.ok:
                # Without a completed past consent there is no record to protect: A3 stays INCONCLUSIVE.
                state = consent.read_state(subject=past, phase="BASELINE", step_id="seed-lanes")
                step("seed-lanes", "BASELINE", "past", "read_state", state)
                record["past_before"] = state_row(state)
        checkpoint("PAST_SEEDED")

        # (3) stale: submit a previous identifier derived from the current one.
        current_policy = consent.read_policy(subject=stale)
        step("submit-stale-consent", "INJECTED", "stale", "read_policy", current_policy)
        before = consent.read_state(subject=stale, phase="BASELINE", step_id="submit-stale-consent")
        step("submit-stale-consent", "BASELINE", "stale", "read_state", before)
        record["stale_before"] = state_row(before)
        current = policy_identifier(current_policy)
        if current is not None:
            submitted = n03.stale_identifier(current)
            stale_policy = ConsentPolicySnapshot.model_validate(
                current_policy.model_dump()
                | {"policy_version": submitted["version"], "content_digest": submitted["digest"]}
            )
            result = consent.commit(
                subject=stale,
                policy=stale_policy,
                request_id=str(uuid5(_REQUESTS, f"{run_id}:stale:stale-commit")),
                trace_id=f"controlproof:{run_id}:stale",
            )
            step("submit-stale-consent", "INJECTED", "stale", "commit", result)
            record["stale_attempt"].update(current=current, submitted=submitted, **commit_facts(result))
        after = consent.read_state(subject=stale, phase="INJECTED", step_id="submit-stale-consent")
        step("submit-stale-consent", "INJECTED", "stale", "read_state", after)
        record["stale_after"] = state_row(after)
        checkpoint("STALE_SUBMITTED")

        # (4) stale: re-read the policy, commit with it and read the stored record directly.
        reread_policy = consent.read_policy(subject=stale)
        step("reread-and-commit", "INJECTED", "stale", "read_policy", reread_policy)
        reread = policy_identifier(reread_policy)
        if reread is not None:
            result = consent.commit(
                subject=stale,
                policy=reread_policy,
                request_id=str(uuid5(_REQUESTS, f"{run_id}:stale:latest-commit")),
                trace_id=f"controlproof:{run_id}:stale",
            )
            step("reread-and-commit", "INJECTED", "stale", "commit", result)
            facts = seed.read_consent_facts(subject=stale)
            step("reread-and-commit", "INJECTED", "stale", "read_consent_facts", facts)
            stored = facts.data.get("record") if facts.ok else None
            response = commit_facts(result)
            response.pop("durable_state")
            record["latest_commit"].update(
                reread=reread,
                stored={"policy_version": stored["policy_version"], "evidence_digest": stored["evidence_digest"]}
                if stored
                else None,
                consent_record_id=stored["consent_record_id"] if stored else None,
                **response,
            )

        # (5) past after.
        state = consent.read_state(subject=past, phase="INJECTED", step_id="reread-and-commit")
        step("reread-and-commit", "INJECTED", "past", "read_state", state)
        record["past_after"] = state_row(state)
        checkpoint("OBSERVED")

    def _assertions(self, record, recovery):
        return n03.assertions_for(
            record["stale_attempt"],
            record["stale_before"],
            record["stale_after"],
            record["latest_commit"],
            record["past_before"],
            record["past_after"],
            recovery,
        )

    def _documents(self, record, lanes, errors):
        return {
            "n03-lanes.json": {
                "lanes": [lane.model_dump(mode="json") for lane in lanes],
                "past_setup": record.get("past_setup"),
                "errors": errors,
            },
            "n03-stale-attempt.json": record["stale_attempt"],
            "n03-stale-before.json": record["stale_before"],
            "n03-stale-after.json": record["stale_after"],
            "n03-latest-commit.json": record["latest_commit"],
            "n03-past-before.json": record["past_before"],
            "n03-past-after.json": record["past_after"],
        }

    def _summary(self, verdict):
        return f"이전 정책 식별값 제출, 재조회 동의, 과거 동의 기록을 테스트했습니다. 전체 {verdict}."
