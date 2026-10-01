from __future__ import annotations

import hashlib
from types import SimpleNamespace

import playwright.sync_api

import engine.adapters.whyyou.capability as capability_module
from engine.adapters.base import AdapterResult
from engine.adapters.whyyou.capability import WhyYouCapabilityProbe
from engine.adapters.whyyou.queue import QueueAccessError, QueueContractError
from engine.config import Settings
from engine.lifecycle import RestoreBlockStore
from engine.models import ReadinessStatus


class Response:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(str(self.status_code))


class Http:
    def __init__(self, paths, health=None, *, denied=False):
        self.paths = paths
        self.health = health or {}
        self.denied = denied

    def get(self, path):
        if path == "/openapi.json":
            if self.denied:
                return Response(403)
            return Response(body={"paths": {item: {} for item in self.paths}})
        if path == "/internal/controlproof/health":
            return Response(body=self.health)
        return Response()


def _settings(tmp_path):
    return Settings.from_env(
        {
            "WHYYOU_BASE_URL": "http://localhost:8000",
            "WHYYOU_CONSOLE_URL": "http://localhost:5173",
            "WHYYOU_DATABASE_URL": "postgresql+psycopg://local:local@localhost/test",
            "WHYYOU_COMPANY_TOKEN": "local-test-token",
            "WHYYOU_REPO_PATH": str(tmp_path),
            "CONTROLPROOF_RUN_ROOT": str(tmp_path / "runs"),
            "CONTROLPROOF_FAULT_ROOT": str(tmp_path / "faults"),
            "CONTROLPROOF_TEST_HOOKS_ENABLED": "true",
            "CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED": "true",
            "CONTROLPROOF_MODEL_FIXTURE_ID": "h03-report-v1",
            "CONTROLPROOF_MODEL_FIXTURE_DIGEST": (
                "ce09b95403b34e1390502c90f5c5edc518ddf65d38c8ce881617a37cac6d16b1"
            ),
        }
    )


def _client(http):
    return SimpleNamespace(http=http, capture_target_snapshot=lambda: object())


def test_route_presence_and_credential_access_are_distinct(tmp_path):
    report = "/v1/interview-sessions/{session_id}/report"
    decision = "/v1/invitations/{invitation_id}/final-decisions"
    ready = WhyYouCapabilityProbe(_settings(tmp_path), _client(Http({report, decision})))
    assert ready.target_feature_exists()
    assert ready.probe("reporting.status.read").status is ReadinessStatus.READY

    missing = WhyYouCapabilityProbe(_settings(tmp_path), _client(Http({report})))
    assert not missing.target_feature_exists()

    denied = WhyYouCapabilityProbe(
        _settings(tmp_path),
        _client(Http(set(), denied=True)),
    )
    assert denied.target_feature_exists()
    assert denied.probe("reporting.status.read").status is ReadinessStatus.ACCESS_BLOCKED


def test_n02_consent_http_capabilities_require_route_and_composed_adapter(tmp_path):
    route = "/v1/applicant/consents"
    missing_adapter = WhyYouCapabilityProbe(
        _settings(tmp_path), _client(Http({route}))
    )
    composed = WhyYouCapabilityProbe(
        _settings(tmp_path), _client(Http({route})), n02_consent=object()
    )
    assert missing_adapter.probe("consent.policy.read").status is ReadinessStatus.RUNNER_NOT_READY
    assert composed.probe("consent.policy.read").status is ReadinessStatus.READY
    assert composed.probe("consent.commit.write").status is ReadinessStatus.READY


def test_n02_consent_fault_capabilities_require_hook_adapter_and_writable_root(
    tmp_path,
) -> None:
    settings = _settings(tmp_path)
    missing = WhyYouCapabilityProbe(settings, _client(Http(set())))
    composed = WhyYouCapabilityProbe(
        settings,
        _client(Http(set())),
        n02_fault=object(),
    )
    assert (
        missing.probe("consent.fault.inject").status
        is ReadinessStatus.RUNNER_NOT_READY
    )
    for capability in (
        "consent.fault.inject",
        "consent.fault.receipt.read",
        "consent.fault.restore",
    ):
        assert composed.probe(capability).status is ReadinessStatus.READY


def test_fault_root_health_model_identity_and_restore_block(tmp_path):
    settings = _settings(tmp_path)
    health = {
        "fault_hooks_enabled": True,
        "fault_root_digest": hashlib.sha256(
            settings.fault_root.resolve().as_posix().casefold().encode("utf-8")
        ).hexdigest(),
        "model_substitute_enabled": True,
        "fixture_id": settings.model_fixture_id,
        "fixture_digest": settings.model_fixture_digest,
    }
    probe = WhyYouCapabilityProbe(settings, _client(Http(set(), health)))
    assert probe.probe("reporting.fault.inject").status is ReadinessStatus.READY
    assert probe.probe("reporting.model.deterministic").status is ReadinessStatus.READY

    blocked_run = SimpleNamespace(run_id="blocked")
    RestoreBlockStore(settings.run_root).block(
        settings.target_id,
        "candidate-01",
        blocked_run,
    )
    blocked = probe.probe("reporting.fault.restore")
    assert blocked.status is ReadinessStatus.RUNNER_NOT_READY
    assert "cleanup-confirm" in blocked.operator_action


def test_fault_root_digest_mismatch_is_runner_not_ready(tmp_path):
    settings = _settings(tmp_path)
    health = {
        "fault_hooks_enabled": True,
        "fault_root_digest": "f" * 64,
    }

    result = WhyYouCapabilityProbe(settings, _client(Http(set(), health))).probe(
        "reporting.fault.inject"
    )

    assert result.status is ReadinessStatus.RUNNER_NOT_READY
    assert "does not match" in result.detail
    assert result.operator_action


def test_model_digest_mismatch_is_runner_not_ready(tmp_path):
    settings = _settings(tmp_path)
    health = {
        "fault_hooks_enabled": True,
        "model_substitute_enabled": True,
        "fixture_id": settings.model_fixture_id,
        "fixture_digest": "f" * 64,
    }
    result = WhyYouCapabilityProbe(settings, _client(Http(set(), health))).probe(
        "reporting.model.deterministic"
    )
    assert result.status is ReadinessStatus.RUNNER_NOT_READY
    assert result.operator_action


def test_schema_snapshot_database_mapping_and_chromium_are_probed(
    tmp_path,
    monkeypatch,
):
    settings = _settings(tmp_path)
    probe = WhyYouCapabilityProbe(settings, _client(Http(set())))
    assert probe.probe("target.version.read").status is ReadinessStatus.READY

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def execute(self, _statement):
            return 1

    monkeypatch.setattr(
        capability_module,
        "create_engine",
        lambda _url: SimpleNamespace(connect=lambda: Connection()),
    )
    assert probe.probe("h03.subject.seed").status is ReadinessStatus.READY
    assert (
        probe.probe("reporting.effects.read").status
        is ReadinessStatus.RUNNER_NOT_READY
    )
    effect_probe = WhyYouCapabilityProbe(
        settings,
        _client(Http(set())),
        effects=object(),
    )
    assert effect_probe.probe("reporting.effects.read").status is ReadinessStatus.READY

    executable = tmp_path / "chromium.exe"
    executable.write_bytes(b"fixture")

    class PlaywrightContext:
        def __enter__(self):
            return SimpleNamespace(chromium=SimpleNamespace(executable_path=str(executable)))

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(playwright.sync_api, "sync_playwright", PlaywrightContext)
    assert probe.probe("reporting.ui.observe").status is ReadinessStatus.READY


def test_queue_capability_distinguishes_contract_mismatch_and_access_loss(tmp_path):
    class Queue:
        def __init__(self, error=None):
            self.error = error

        def capture_topology(self):
            if self.error:
                raise self.error
            return object()

    ready = WhyYouCapabilityProbe(
        _settings(tmp_path), _client(Http(set())), queue=Queue()
    ).probe("messaging.reporting.topology.read")
    mismatch = WhyYouCapabilityProbe(
        _settings(tmp_path),
        _client(Http(set())),
        queue=Queue(QueueContractError("visibility mismatch")),
    ).probe("messaging.reporting.topology.read")
    denied = WhyYouCapabilityProbe(
        _settings(tmp_path),
        _client(Http(set())),
        queue=Queue(QueueAccessError("sanitized")),
    ).probe("messaging.reporting.topology.read")

    assert ready.status is ReadinessStatus.READY
    assert mismatch.status is ReadinessStatus.RUNNER_NOT_READY
    assert denied.status is ReadinessStatus.ACCESS_BLOCKED


def test_decision_path_capability_requires_both_pinned_operations(tmp_path):
    class Decision:
        def __init__(self, result):
            self.result = result

        def probe_operations(self):
            return self.result

    ready_probe = WhyYouCapabilityProbe(
        _settings(tmp_path),
        _client(Http(set())),
        decision=Decision(AdapterResult(True, "DECISION_OPERATIONS_READY")),
    )
    incomplete_probe = WhyYouCapabilityProbe(
        _settings(tmp_path),
        _client(Http(set())),
        decision=Decision(AdapterResult(False, "DECISION_OPERATIONS_INCOMPLETE")),
    )
    blocked_probe = WhyYouCapabilityProbe(
        _settings(tmp_path),
        _client(Http(set())),
        decision=Decision(AdapterResult(False, "DECISION_OPERATIONS_ACCESS_BLOCKED")),
    )

    for capability in ("hiring.decision_paths.read", "hiring.decision_path.attempt"):
        assert ready_probe.probe(capability).status is ReadinessStatus.READY
        assert incomplete_probe.probe(capability).status is ReadinessStatus.RUNNER_NOT_READY
        assert blocked_probe.probe(capability).status is ReadinessStatus.ACCESS_BLOCKED
