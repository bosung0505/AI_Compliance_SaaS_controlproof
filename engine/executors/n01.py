"""N-01 official execution: applicant consent screens at PC and mobile viewports, policy identifiers (Spec 009).

Steps follow plan.md §3. Expected fragments are built from the policy the screen itself received; a browser
failure still seals its partial record so the judge decides INCONCLUSIVE.
"""

from __future__ import annotations

import hashlib
from typing import Any

from engine import n01
from engine.adapters.base import AdapterResult
from engine.executors.spec009 import Spec009Executor, policy_identifier, subject_identity
from engine.models import ExecutionProfile, N01LaneId, ReadinessStatus

PROFILE = ExecutionProfile.N01_NOTICE_V1
UNVERIFIED_SCOPE = ("AWS_NOT_RUN", "EXTERNAL_MODEL_QUALITY_NOT_TESTED", "N02_PRE_CONSENT_BLOCK_NOT_RETESTED")
LINKS = {
    "EV9-01": {"environment.snapshot.json", "target.snapshot.json", "scenario.snapshot.yaml", "n01-scope.json"},
    "EV9-02": {"subjects.json", "n01-lanes.json"},
    "EV9-03": {"n01-measurements.json"},
    "EV9-04": {"n01-policy-identifiers.json"},
    "EV9-06": {"recovery.json"},
    "EV9-07": {"run.json", "assertions.json", "judgement.json"},
}


def capture_name(lane: str) -> str:
    return f"n01-{lane}-capture.png"


def lane_summary(record: dict[str, Any]) -> dict[str, Any]:
    """`n01-lanes.json` row: derived from the sealed measurement record."""
    return {
        "lane": record["lane"],
        "viewport": record["viewport"],
        "subject_ref": record["subject"]["subject_ref"],
        "step_reached": record["step_reached"],
        "measurement_error": record.get("measurement_error"),
    }


class N01Executor(Spec009Executor):
    profile = PROFILE
    tag = "N01"
    block_subject = "n01-notice"
    seed_kind = "n01-invited-token-lanes-v1"
    fault_kind = "n01-consent-screen-observation-v1"
    unverified_scope = UNVERIFIED_SCOPE
    links = LINKS
    scope_file = "n01-scope.json"
    judge = n01
    _seed_step = "seed-invitations"
    api_capabilities = ("consent.policy.read",)
    db_checks = (
        ("consent_records", "consent_record_id, policy_version, evidence_digest, accepted_at", ("consent.state.read",)),
        ("applicant_access_sessions", "session_hash", ("n01.invitations.teardown",)),
        ("invitation_state_history", "to_status", ("consent.state.read",)),
        ("applicant_access_tokens", "token_hash, consumed_at", ("n01.invitations.seed", "n01.invitations.teardown")),
        ("applicant_profiles", "applicant_id", ("n01.invitations.seed", "n01.invitations.teardown")),
    )

    def _extra_checks(self, probes, mark):
        screen = ("applicant.screen.open",)
        url = self.settings.applicant_app_url
        if not url:
            mark(screen, ReadinessStatus.ACCESS_BLOCKED, "SPEC009_APPLICANT_APP_URL_MISSING")
        else:
            try:
                status = probes.applicant_app_status(url)
            except Exception:  # noqa: BLE001 - no answer from the applicant app is an access block
                mark(screen, ReadinessStatus.ACCESS_BLOCKED, "SPEC009_APPLICANT_APP_UNREACHABLE")
            else:
                if status != 200:
                    mark(screen, ReadinessStatus.ACCESS_BLOCKED, f"SPEC009_APPLICANT_APP_UNAVAILABLE:{status}")
        try:
            chromium = probes.chromium_ready()
        except Exception:  # noqa: BLE001 - a driver that cannot start is a missing runner tool
            chromium = False
        if not chromium:
            mark(("browser.chromium.available",), ReadinessStatus.RUNNER_NOT_READY, "SPEC009_CHROMIUM_MISSING")

    def _initial_record(self, run_id, lanes):
        return {"lanes": [], "identifiers": []}

    def _observe(self, run_id, lanes, record, step, checkpoint):
        seed, consent = self.adapters.spec009_seed, self.adapters.spec009_consent
        browser = self.adapters.applicant_browser
        try:
            for lane in N01LaneId:
                subject = seed.subject_for(run_id=str(run_id), lane_id=lane)
                width, height = n01.VIEWPORTS[lane]
                try:
                    result = browser.observe_consent(
                        subject=subject,
                        viewport={"width": width, "height": height},
                        fragment_builder=n01.expected_fragments,
                        display_name=seed.display_name_for(run_id=str(run_id), lane_id=lane),
                    )
                except Exception as exc:  # noqa: BLE001 - adapter defect becomes a sealed partial record
                    result = AdapterResult(False, "BROWSER_ADAPTER_ERROR", detail=type(exc).__name__)
                step("open-consent-screens", "INJECTED", lane.value, "observe_consent", result)
                data = dict(result.data)
                lane_record = dict(data.get("record") or self._unreached(subject, lane, result.code))
                screenshot = bytes(data.get("screenshot_bytes") or b"")
                capture = lane_record.get("capture")
                if capture and screenshot and hashlib.sha256(screenshot).hexdigest() == capture["sha256"]:
                    lane_record["capture"] = {**capture, "file": capture_name(lane.value)}
                    self._captures[capture_name(lane.value)] = screenshot
                else:
                    lane_record["capture"] = None
                record["lanes"].append(lane_record)
                checkpoint(f"SCREEN_OBSERVED:{lane.value}")

                server = consent.read_policy(subject=subject)
                step("complete-consent", "INJECTED", lane.value, "read_policy", server)
                facts = seed.read_consent_facts(subject=subject)
                step("complete-consent", "INJECTED", lane.value, "read_consent_facts", facts)
                stored = facts.data.get("record") if facts.ok else None
                record["identifiers"].append(
                    {
                        "lane": lane.value,
                        "subject_ref": str(subject["subject_ref"]),
                        "screen": data.get("screen_policy"),
                        "server": policy_identifier(server),
                        "stored": {"policy_version": stored["policy_version"], "evidence_digest": stored["evidence_digest"]}
                        if stored
                        else None,
                        "consented_at": stored["accepted_at"] if stored else None,
                        "commit_status": data.get("commit_status"),
                    }
                )
                checkpoint(f"IDENTIFIERS_READ:{lane.value}")
        finally:
            close = getattr(browser, "close", None)
            if close is not None:
                close()

    @staticmethod
    def _unreached(subject, lane, code) -> dict[str, Any]:
        width, height = n01.VIEWPORTS[lane]
        return {
            "lane": lane.value,
            "viewport": {"width": width, "height": height},
            "subject": subject_identity(subject),
            "step_reached": "error",
            "capture": None,
            "token_absent_in_dom": None,
            "operations": [],
            "items": [],
            "measurement_error": code,
        }

    def _assertions(self, record, recovery):
        return n01.assertions_for(record["lanes"], record["identifiers"], recovery)

    def _documents(self, record, lanes, errors):
        return {
            "n01-lanes.json": [lane_summary(item) for item in record["lanes"]],
            "n01-measurements.json": record["lanes"],
            "n01-policy-identifiers.json": record["identifiers"],
        }

    def _links(self):
        links = super()._links()
        links["EV9-03"] |= set(self._captures)
        return links

    def _summary(self, verdict):
        return f"PC·모바일 동의 화면의 다섯 고지와 정책 식별값을 테스트했습니다. 전체 {verdict}."
