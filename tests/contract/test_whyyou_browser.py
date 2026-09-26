from __future__ import annotations

from types import SimpleNamespace

from engine.adapters.whyyou.browser import WhyYouBrowserAdapter


def _settings():
    return SimpleNamespace(whyyou_company_token="token", whyyou_console_url="http://localhost")


def test_browser_projection_is_sanitized_and_classified():
    adapter = WhyYouBrowserAdapter(
        _settings(),
        capture=lambda _subject: {
            "visible_text": "real.person@example.com 리포트 생성 실패",
            "decision_control_visible": True,
            "screenshot_bytes": b"png",
        },
    )
    result = adapter.capture_review(subject={})
    assert result.ok
    assert "real.person@example.com" not in result.data["projection"]["visible_text"]
    assert result.data["projection"]["status_class"] == "failed"
    assert result.data["projection"]["decision_control_visible"] is True
    assert result.data["screenshot_bytes"] == b"png"


def test_browser_timeout_and_auth_failure_are_distinct():
    timeout = WhyYouBrowserAdapter(
        _settings(),
        capture=lambda _subject: (_ for _ in ()).throw(TimeoutError()),
    )
    denied = WhyYouBrowserAdapter(
        _settings(),
        capture=lambda _subject: (_ for _ in ()).throw(RuntimeError("403")),
    )
    assert timeout.capture_review(subject={}).code == "BROWSER_TIMEOUT"
    assert denied.capture_review(subject={}).code == "BROWSER_AUTH_FAILED"
