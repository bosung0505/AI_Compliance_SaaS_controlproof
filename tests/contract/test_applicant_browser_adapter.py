"""T006 — applicant consent screen adapter contract (FR-010, FR-011, FR-012; Constitution quality gate).

The capture callable is injected; the real Playwright path is confirmed only by an approved actual Run.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from uuid import UUID

import pytest

from engine.adapters.base import AdapterResult, ApplicantBrowserPort
from engine.adapters.whyyou.adapter import create_whyyou_adapter
from engine.adapters.whyyou.applicant_browser import WhyYouApplicantBrowserAdapter
from engine.adapters.whyyou.n02_seed import N02CredentialStore
from engine.config import ConfigError, Settings
from engine.n01 import NOTICE_ITEMS, N01LaneRecord

RAW_TOKEN = "raw-invitation-token-0123456789abcdef0123456789"
RAW_COOKIE = "raw-session-cookie-value"
SUBJECT = {
    "run_id": "33333333-3333-4333-8333-333333333333",
    "lane_id": "mobile",
    "subject_ref": "n01-mobile",
    "invitation_id": str(UUID(int=7)),
    "applicant_id": str(UUID(int=8)),
}
VIEWPORT = {"width": 390, "height": 844}
EXPECTED = {item: [(f"{item}.text", f"{item} 고지 문구")] for item in NOTICE_ITEMS}
SCREENSHOT = b"\x89PNG\r\n\x1a\nfake-capture"


def _flags(fragment_id: str, text: str, **overrides) -> dict:
    value = {
        "fragment_id": fragment_id,
        "expected_text": text,
        "text_present": True,
        "bbox": {"x": 1.0, "y": 2.0, "width": 300.0, "height": 20.0},
        "in_viewport": True,
        "center_hit": True,
        "not_occluded": True,
        "doc_scroll_width": 390,
        "doc_client_width": 390,
        "el_scroll_width": 300,
        "el_client_width": 300,
        "no_horizontal_overflow": True,
    }
    value.update(overrides)
    return value


def _raw(**overrides) -> dict:
    value = {
        "step_reached": "ready",
        "measurement_error": None,
        "items": [
            {"item_id": item, "fragments": [_flags(fid, text) for fid, text in EXPECTED[item]]} for item in NOTICE_ITEMS
        ],
        "operations": [{"kind": "scroll", "fragment_id": "deletion.text", "scroll_y": 310}],
        "token_absent_in_dom": True,
        "screenshot_bytes": SCREENSHOT,
        "screen_policy": {"version": "2026-08-v1", "digest": "a" * 64, "policy_text": "never kept"},
        "commit_status": 201,
        "session_cookie": RAW_COOKIE,
    }
    value.update(overrides)
    return value


@pytest.fixture
def app_settings(settings) -> Settings:
    return dataclasses.replace(settings, applicant_app_url="http://127.0.0.1:5174")


@pytest.fixture
def credentials() -> N02CredentialStore:
    store = N02CredentialStore()
    store.put(f"{SUBJECT['subject_ref']}:invitation_token", RAW_TOKEN)
    return store


def _observe(adapter) -> AdapterResult:
    return adapter.observe_consent(
        subject=SUBJECT, viewport=VIEWPORT, expected_fragments=EXPECTED, display_name="합성 지원자"
    )


def test_observation_becomes_a_lane_record_without_secrets(app_settings, credentials) -> None:
    seen = []

    def capture(request):
        seen.append(request)
        return _raw()

    result = _observe(WhyYouApplicantBrowserAdapter(app_settings, credentials=credentials, capture=capture))
    assert (result.ok, result.code) == (True, "APPLICANT_CONSENT_OBSERVED")
    assert seen[0]["raw_token"] == RAW_TOKEN and seen[0]["app_url"] == "http://127.0.0.1:5174"
    record = N01LaneRecord.model_validate(result.data["record"])
    assert record.lane.value == "mobile" and record.viewport.width == 390 and record.step_reached == "ready"
    assert record.subject.subject_ref == "n01-mobile"
    assert record.capture.model_dump() == {
        "file": None, "sha256": hashlib.sha256(SCREENSHOT).hexdigest(), "bytes": len(SCREENSHOT),
    }
    assert record.token_absent_in_dom is True
    assert record.operations == ({"kind": "scroll", "fragment_id": "deletion.text", "scroll_y": 310},)
    fragment = record.items[0].fragments[0]
    assert fragment.expected_text_digest == hashlib.sha256(fragment.expected_text.encode()).hexdigest()
    assert fragment.bbox.width == 300.0 and fragment.no_horizontal_overflow
    assert result.data["screen_policy"] == {"version": "2026-08-v1", "digest": "a" * 64}
    assert result.data["commit_status"] == 201
    assert result.data["screenshot_bytes"] == SCREENSHOT


def test_session_cookie_goes_only_to_credentials_and_no_raw_secret_is_in_payload(app_settings, credentials) -> None:
    result = _observe(WhyYouApplicantBrowserAdapter(app_settings, credentials=credentials, capture=lambda _: _raw()))
    assert credentials.get(SUBJECT["subject_ref"]) == RAW_COOKIE
    serialized = json.dumps({key: value for key, value in result.data.items() if key != "screenshot_bytes"})
    assert RAW_COOKIE not in serialized and RAW_TOKEN not in serialized
    assert "session_cookie" not in result.data and "policy_text" not in serialized


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (TimeoutError("navigation"), "BROWSER_TIMEOUT"),
        (RuntimeError("browser authentication failed: 401"), "BROWSER_AUTH_FAILED"),
        (RuntimeError("browser authentication failed: 403"), "BROWSER_AUTH_FAILED"),
        (RuntimeError("net::ERR_CONNECTION_REFUSED"), "BROWSER_CAPTURE_FAILED"),
    ],
)
def test_capture_exceptions_become_sanitized_codes(app_settings, credentials, error, code) -> None:
    def capture(_request):
        raise error

    result = _observe(WhyYouApplicantBrowserAdapter(app_settings, credentials=credentials, capture=capture))
    assert (result.ok, result.code) == (False, code)
    assert RAW_TOKEN not in result.detail and dict(result.data) == {}


def test_missing_app_url_or_token_fails_before_capture(settings, app_settings) -> None:
    def capture(_request):
        raise AssertionError("capture must not run")

    store = N02CredentialStore()
    store.put(f"{SUBJECT['subject_ref']}:invitation_token", RAW_TOKEN)
    assert _observe(WhyYouApplicantBrowserAdapter(settings, credentials=store, capture=capture)).code == (
        "APPLICANT_APP_URL_MISSING"
    )
    empty = N02CredentialStore()
    assert _observe(WhyYouApplicantBrowserAdapter(app_settings, credentials=empty, capture=capture)).code == (
        "N01_INVITATION_TOKEN_MISSING"
    )


@pytest.mark.parametrize(
    ("raw", "step", "code"),
    [
        (_raw(step_reached="exchange", measurement_error="BROWSER_IDENTITY_FAILED", items=[], screenshot_bytes=b"",
              token_absent_in_dom=None, commit_status=None, screen_policy=None), "exchange", "BROWSER_IDENTITY_FAILED"),
        (_raw(step_reached="error", measurement_error="BROWSER_EXCHANGE_FAILED", items=[], screenshot_bytes=b"",
              token_absent_in_dom=None, commit_status=None, screen_policy=None, session_cookie=None),
         "error", "BROWSER_EXCHANGE_FAILED"),
        (_raw(step_reached="consent", measurement_error="BROWSER_COMMIT_FAILED", commit_status=422), "consent",
         "BROWSER_COMMIT_FAILED"),
    ],
)
def test_partial_record_is_returned_for_sealing(app_settings, credentials, raw, step, code) -> None:
    result = _observe(WhyYouApplicantBrowserAdapter(app_settings, credentials=credentials, capture=lambda _: raw))
    assert (result.ok, result.code) == (False, code)
    record = N01LaneRecord.model_validate(result.data["record"])
    assert record.step_reached == step and record.measurement_error == code
    if not raw["screenshot_bytes"]:
        assert record.capture is None


def test_settings_read_applicant_app_url_and_require_local(settings, tmp_path) -> None:
    assert settings.applicant_app_url is None
    base = {
        "WHYYOU_BASE_URL": "http://localhost:8000",
        "WHYYOU_CONSOLE_URL": "http://localhost:3000",
        "WHYYOU_DATABASE_URL": "postgresql+psycopg://local:local@localhost:5432/whyyou",
        "WHYYOU_COMPANY_TOKEN": "local-test-token",
        "WHYYOU_REPO_PATH": str(tmp_path),
        "CONTROLPROOF_FAULT_ROOT": str(tmp_path / "faults"),
        "CONTROLPROOF_MODEL_FIXTURE_ID": settings.model_fixture_id,
        "CONTROLPROOF_MODEL_FIXTURE_DIGEST": settings.model_fixture_digest,
    }
    configured = Settings.from_env(base | {"CONTROLPROOF_APPLICANT_APP_URL": "http://127.0.0.1:5174/"})
    assert configured.applicant_app_url == "http://127.0.0.1:5174"
    with pytest.raises(ConfigError):
        Settings.from_env(base | {"CONTROLPROOF_APPLICANT_APP_URL": "https://applicant.example.com"})


def test_composition_exposes_applicant_browser_port(settings) -> None:
    adapters, _client = create_whyyou_adapter(settings)
    assert isinstance(adapters.applicant_browser, WhyYouApplicantBrowserAdapter)
    assert isinstance(adapters.applicant_browser, ApplicantBrowserPort)
