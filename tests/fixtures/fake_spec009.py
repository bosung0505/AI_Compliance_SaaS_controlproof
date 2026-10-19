"""Fakes for the Spec 009 N-01/N-03 executors: no database, no HTTP server, no browser.

The consent adapter is the real ``WhyYouConsentAdapter`` over an ``httpx.MockTransport``; the applicant browser
is the real ``WhyYouApplicantBrowserAdapter`` with an injected capture. Both talk to one in-memory backend.
Raw invitation tokens and session cookies are recorded by ``SpyStore`` so tests can prove they never reach a
bundle file.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid5

import httpx

from engine.adapters.base import AdapterResult
from engine.adapters.whyyou.applicant_browser import WhyYouApplicantBrowserAdapter
from engine.adapters.whyyou.consent import WhyYouConsentAdapter
from engine.adapters.whyyou.n02_seed import N02CredentialStore
from engine.adapters.whyyou.spec009_cleanup import REQUIRED_RESIDUE_TABLES
from engine.models import ScenarioReadiness
from engine.scenario import SPEC009_FIXTURES
from seeds.spec009_subjects import build_spec009_seed_plan
from tests.fixtures.spec002 import environment_snapshot

FIXTURE_ID, FIXTURE_DIGEST = next(iter(SPEC009_FIXTURES.items()))
COMPANY_ID = "00000000-0000-7000-8000-000000000001"
REVIEWER_ID = "00000000-0000-7000-8000-000000000002"
_NS = UUID("0f6b9b52-7f4e-5d0b-9c1e-5a3f00000009")
_AT = datetime(2026, 10, 20, 1, tzinfo=UTC)
PNG = b"\x89PNG\r\n\x1a\n"

POLICY_BODY = {
    "policy_version": "2026-08-v1",
    "ai_role": "AI는 질문과 평가 초안을 만들지만 최종 채용 결정은 기업의 사람이 수행합니다.",
    "recording_notice": "면접 중 음성과 영상을 녹화하며 Evidence 재생 구간에 사용합니다.",
    "processing_purposes": [
        {"purpose": "document_analysis", "title": "문서 분석", "description": "제출 자료를 질문 준비에 사용합니다."},
        {"purpose": "recording", "title": "면접 녹화", "description": "영상과 음성을 저장합니다."},
        {"purpose": "ai_assessment", "title": "AI 평가 보조", "description": "최종 답변 근거로 평가 초안을 만듭니다."},
    ],
    "retention_days": 180,
    "deletion_method": "삭제 요청 또는 보관기간 만료 시 원본과 파생 데이터를 삭제합니다.",
    "required_purposes": ["ai_assessment", "document_analysis", "recording"],
}
POLICY_DIGEST = hashlib.sha256(
    json.dumps(POLICY_BODY, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
POLICY_JSON = POLICY_BODY | {"content_digest": POLICY_DIGEST}
CURRENT = {"version": POLICY_BODY["policy_version"], "digest": POLICY_DIGEST}


def spec009_settings(tmp_path: Path, **updates) -> SimpleNamespace:
    repo = tmp_path / "whyyou-repo"
    repo.mkdir(exist_ok=True)
    values = {
        "whyyou_company_id": COMPANY_ID,
        "whyyou_company_user_id": REVIEWER_ID,
        "whyyou_base_url": "http://whyyou.test",
        "whyyou_database_url": "postgresql+psycopg://local:local@localhost:5432/whyyou",
        "whyyou_repo_path": repo,
        "applicant_app_url": "http://127.0.0.1:5174",
        "external_ai_allowed": False,
        "model_substitute_enabled": True,
        "model_fixture_id": FIXTURE_ID,
        "model_fixture_digest": FIXTURE_DIGEST,
        "environment_kind": "LOCAL_EMULATED",
        "aws_deployment_status": "NOT_RUN",
    }
    values.update(updates)
    return SimpleNamespace(**values)


def spec009_target(target_snapshot):
    target = target_snapshot.model_copy(update={"model_fixture_id": FIXTURE_ID, "model_fixture_digest": FIXTURE_DIGEST})
    return type(target).model_validate(target.model_dump(exclude={"target_version"}))


def spec009_environment(target):
    return environment_snapshot(
        model_fixture_id=FIXTURE_ID,
        model_fixture_digest=FIXTURE_DIGEST,
        whyyou_commit={"commit_sha": target.git_commit_sha, "dirty": False},
    )


def ready(scenario, target) -> ScenarioReadiness:
    return ScenarioReadiness(
        scenario_id=scenario.scenario_id,
        scenario_version=scenario.version,
        target_id="whyyou-local",
        implementation_status="IMPLEMENTED",
        status="READY",
        checks=(),
        target_snapshot=target,
        target_version=target.target_version,
        model_fixture_id=FIXTURE_ID,
        model_fixture_digest=FIXTURE_DIGEST,
    )


class SpyStore(N02CredentialStore):
    """Credential store that remembers every raw value ever handed over."""

    def __init__(self) -> None:
        super().__init__()
        self.seen: set[str] = set()

    def put(self, subject_ref: str, credential: str) -> None:
        self.seen.add(credential)
        super().put(subject_ref, credential)


class FakeBackend:
    """In-memory applicant consent state shared by the HTTP handler, the seed and the browser capture."""

    def __init__(self, modes=()) -> None:
        self.modes = set(modes)
        self.tokens: dict[str, dict] = {}
        self.sessions: dict[str, dict] = {}
        self.status: dict[str, str] = {}
        self.records: dict[str, list[dict]] = {}

    def consent(self, subject: dict, version: str, digest: str, trace: str) -> dict:
        invitation = str(subject["invitation_id"])
        rows = self.records.setdefault(invitation, [])
        record = {
            "consent_record_id": str(uuid5(_NS, f"{invitation}:{len(rows)}")),
            "policy_version": version,
            "evidence_digest": digest,
            "accepted_at": (_AT + timedelta(seconds=len(rows))).isoformat(),
            "trace_id": trace,
            "transition_id": str(uuid5(_NS, f"{invitation}:{len(rows)}:transition")),
            "event_id": str(uuid5(_NS, f"{invitation}:{len(rows)}:event")),
        }
        rows.append(record)
        self.status[invitation] = "consented"
        return record

    def handler(self, request: httpx.Request) -> httpx.Response:
        cookie = request.headers.get("cookie", "").removeprefix("iep_applicant_session=")
        subject = self.sessions.get(cookie)
        if subject is None:
            return httpx.Response(401, json={"detail": "unauthorized"})
        lane = str(subject["lane_id"])
        if request.method == "GET":
            if "policy_unavailable" in self.modes and lane == "stale":
                return httpx.Response(503, json={"detail": "unavailable"})
            return httpx.Response(200, json=POLICY_JSON)
        body = json.loads(request.content)
        stale = (body["policy_version"], body["consent_content_digest"]) != (CURRENT["version"], CURRENT["digest"])
        if stale and "stale_transport" in self.modes:
            raise httpx.ConnectError("connection refused", request=request)
        if stale and "stale_accepted" not in self.modes:
            return httpx.Response(422, json={"detail": "consent policy version or digest is stale"})
        if self.status.get(str(subject["invitation_id"])) == "consented":
            return httpx.Response(422, json={"detail": "cannot transition invitation from consented to consented"})
        record = self.consent(subject, body["policy_version"], body["consent_content_digest"], request.headers["x-trace-id"])
        return httpx.Response(
            201,
            json={
                "consent_record_id": record["consent_record_id"],
                "policy_version": record["policy_version"],
                "accepted_purposes": body["accepted_purposes"],
                "retention_days": 180,
            },
        )

    def state_reader(self, subject) -> dict:
        if "state_unavailable" in self.modes:
            raise RuntimeError("database unavailable")
        invitation = str(subject["invitation_id"])
        rows = self.records.get(invitation, [])
        return {
            "source_status": "PRESENT",
            "invitation_status": self.status.get(invitation, "missing"),
            "invitation_row_version": 1 + len(rows),
            "consent_record_ids": [row["consent_record_id"] for row in rows],
            "active_consent_count": len(rows),
            "consent_policy_versions": [row["policy_version"] for row in rows],
            "consent_content_digests": [row["evidence_digest"] for row in rows],
            "accepted_purpose_sets": [POLICY_BODY["required_purposes"] for _ in rows],
            "consented_state_change_ids": [row["transition_id"] for row in rows],
            "consent_completed_event_ids": [row["event_id"] for row in rows],
            "trace_ids": [row["trace_id"] for row in rows],
        }

    def latest(self, invitation_id) -> dict | None:
        rows = self.records.get(str(invitation_id), [])
        return dict(rows[-1]) if rows else None


class FakeSpec009Seed:
    """Deterministic lanes from the real seed plan; teardown outcome is chosen by the test."""

    def __init__(self, settings, credentials, backend: FakeBackend, *, teardown: str = "SUCCEEDED") -> None:
        self.settings, self.credentials, self.backend, self.teardown = settings, credentials, backend, teardown
        self.plans: dict = {}
        self.teardowns: list[str] = []

    def seed_lanes(self, *, run_id, profile):
        if "seed_fails" in self.backend.modes:
            return AdapterResult(False, "SPEC009_SEED_WRITE_FAILED", detail="OperationalError")
        plan = build_spec009_seed_plan(
            UUID(run_id), profile=profile, company_id=UUID(COMPANY_ID), reviewer_id=UUID(REVIEWER_ID)
        )
        self.plans[run_id] = plan
        for subject in plan.subjects:
            payload = subject.subject_payload()
            invitation = str(subject.invitation_id)
            if subject.raw_invitation_token:
                self.credentials.put(f"{subject.subject_ref}:invitation_token", subject.raw_invitation_token)
                self.backend.tokens[subject.raw_invitation_token] = payload
                self.backend.status[invitation] = "invited"
            if subject.raw_session_cookie:
                self.credentials.put(subject.subject_ref, subject.raw_session_cookie)
                self.backend.sessions[subject.raw_session_cookie] = payload
                self.backend.status[invitation] = "identity_verified"
        return plan.lanes

    def subject_for(self, *, run_id, lane_id):
        return self.plans[run_id].subject_payload(lane_id)

    def display_name_for(self, *, run_id, lane_id):
        return self.plans[run_id].by_lane(lane_id).display_name

    def read_consent_facts(self, *, subject):
        if "facts_unavailable" in self.backend.modes:
            return AdapterResult(False, "SPEC009_CONSENT_FACTS_UNAVAILABLE", detail="OperationalError")
        row = self.backend.latest(subject["invitation_id"])
        record = (
            {key: row[key] for key in ("consent_record_id", "policy_version", "evidence_digest", "accepted_at")}
            if row
            else None
        )
        return AdapterResult(True, "SPEC009_CONSENT_FACTS_READ", {"record": record})

    def teardown_lanes(self, *, run_id, lanes):
        self.teardowns.append(run_id)
        plan = self.plans.get(run_id)
        if plan is None or plan.lanes != tuple(lanes):
            return AdapterResult(False, "SPEC009_SEED_NOT_OWNED")
        counts = {table: 0 for table in sorted(REQUIRED_RESIDUE_TABLES)}
        data = {"owned_residue_counts": counts, "product_rows_removed": 4, "seed_digest": plan.digest}
        if self.teardown == "ERROR":
            return AdapterResult(False, "SPEC009_TEARDOWN_FAILED", detail="OperationalError")
        if self.teardown == "RESIDUE":
            counts["audit_events"] = 1
            return AdapterResult(False, "SPEC009_RESIDUE_REMAINS", data | {"status": "FAILED"})
        self.plans.pop(run_id)
        for subject in plan.subjects:
            self.credentials.remove(f"{subject.subject_ref}:invitation_token")
            self.credentials.remove(subject.subject_ref)
        return AdapterResult(True, "SPEC009_LANES_REMOVED", data | {"status": "SUCCEEDED"})


def _flags(fragment_id: str, text: str, *, width: int, overflow: bool = False) -> dict:
    return {
        "fragment_id": fragment_id,
        "expected_text": text,
        "text_present": True,
        "bbox": {"x": 8.0, "y": 40.0, "width": float(width - 16), "height": 22.0},
        "in_viewport": True,
        "center_hit": True,
        "not_occluded": True,
        "doc_scroll_width": width + (64 if overflow else 0),
        "doc_client_width": width,
        "el_scroll_width": width - 16,
        "el_client_width": width - 16,
        "no_horizontal_overflow": not overflow,
    }


def browser_capture(backend: FakeBackend):
    """Stand-in for the Playwright path: exchange, identity, measure, capture, commit."""

    def capture(request):
        subject, lane = request["subject"], request["subject"]["lane_id"]
        if "app_unreachable" in backend.modes:
            raise RuntimeError("net::ERR_CONNECTION_REFUSED")
        backend.tokens.pop(request["raw_token"])  # exchange consumes the invitation token
        cookie = f"raw-session-{lane}-{secrets.token_hex(12)}"
        backend.sessions[cookie] = subject
        backend.status[str(subject["invitation_id"])] = "identity_verified"
        observed = {
            "step_reached": "exchange",
            "measurement_error": None,
            "items": [],
            "operations": [],
            "token_absent_in_dom": None,
            "screenshot_bytes": b"",
            # The adapter keeps only version and digest; the raw echo must never reach a bundle.
            "screen_policy": None,
            "commit_status": None,
            "session_cookie": cookie,
        }
        if "identity_failure" in backend.modes:
            return observed | {"measurement_error": "BROWSER_IDENTITY_FAILED"}
        width = request["viewport"]["width"]
        overflow_lane = "overflow_mobile" in backend.modes and lane == "mobile"
        fragments = request["fragment_builder"](POLICY_JSON)
        observed.update(
            step_reached="consent",
            screen_policy=CURRENT | {"raw_echo": request["raw_token"]},
            items=[
                {
                    "item_id": item,
                    "fragments": [
                        _flags(fid, text, width=width, overflow=overflow_lane and item == "deletion")
                        for fid, text in pairs
                    ],
                }
                for item, pairs in fragments.items()
            ],
            operations=[{"kind": "scroll", "fragment_id": "deletion.method", "scroll_y": 420}],
            token_absent_in_dom=True,
            screenshot_bytes=PNG + f"{lane}-{width}".encode(),
        )
        if "commit_failure" in backend.modes:
            return observed | {"measurement_error": "BROWSER_COMMIT_FAILED", "commit_status": 422}
        backend.consent(subject, CURRENT["version"], CURRENT["digest"], f"browser:{subject['run_id']}:{lane}")
        return observed | {"step_reached": "ready", "commit_status": 201}

    return capture


def make_spec009_adapters(tmp_path: Path, target, *, modes=(), teardown: str = "SUCCEEDED", **settings_updates):
    settings = spec009_settings(tmp_path, **settings_updates)
    backend = FakeBackend(modes)
    store = SpyStore()
    consent = WhyYouConsentAdapter(
        settings,
        http_client=httpx.Client(transport=httpx.MockTransport(backend.handler), base_url="http://whyyou.test"),
        credentials=store,
        state_reader=backend.state_reader,
    )
    adapters = SimpleNamespace(
        spec009_seed=FakeSpec009Seed(settings, store, backend, teardown=teardown),
        spec009_consent=consent,
        applicant_browser=WhyYouApplicantBrowserAdapter(settings, credentials=store, capture=browser_capture(backend)),
        environment=SimpleNamespace(capture_environment=lambda: spec009_environment(target)),
    )
    return adapters, backend, store


class FakeProbes:
    """Preflight probes with every answer chosen by the test; nothing touches git, HTTP, a DB or a browser."""

    def __init__(self, target, **overrides) -> None:
        self.target = target
        self.branch = overrides.get("branch", "009-n01-n03-notice-scenarios")
        self.dirty = overrides.get("dirty", False)
        self.python = overrides.get("python", True)
        self.target_error = overrides.get("target_error")
        self.api = {
            "/internal/controlproof/health": (
                200,
                {"controlproof": {"fixture_id": FIXTURE_ID, "fixture_digest": FIXTURE_DIGEST, "external_ai_isolated": True}},
            ),
            "/openapi.json": (200, {"paths": {"/v1/applicant/consents": {}}}),
        } | overrides.get("api", {})
        self.db_missing = set(overrides.get("db_missing", ()))
        self.app = overrides.get("app", 200)
        self.chromium = overrides.get("chromium", True)

    def git(self, repo):
        return self.branch, self.dirty

    def whyyou_python_ready(self):
        return self.python

    def capture_target(self):
        if self.target_error is not None:
            raise self.target_error
        return self.target

    def api_get(self, path):
        value = self.api[path]
        if isinstance(value, Exception):
            raise value
        return value

    def db_probe(self, table, columns):
        if table in self.db_missing:
            raise RuntimeError(f"relation {table} does not exist")

    def applicant_app_status(self, url):
        if isinstance(self.app, Exception):
            raise self.app
        return self.app

    def chromium_ready(self):
        return self.chromium
