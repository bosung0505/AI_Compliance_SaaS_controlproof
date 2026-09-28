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
    assert result.data["projection"]["terminal_status_class"] == "final_failed"
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


def test_browser_projection_classifies_korean_unavailable_message_as_failed():
    adapter = WhyYouBrowserAdapter(
        _settings(),
        capture=lambda _subject: {
            "visible_text": "리포트를 불러올 수 없습니다. 잠시 후 다시 시도해 주세요.",
        },
    )

    result = adapter.capture_review(subject={})

    assert result.ok
    assert result.data["projection"]["status_class"] == "failed"


def test_browser_projection_distinguishes_retrying_queued_and_ready_from_final_failure():
    expected = {
        "리포트 재시도 중": "retrying",
        "리포트 처리 중": "queued_only",
        "리포트 준비 완료": "ready",
        "리포트 생성 실패": "final_failed",
    }
    for text, terminal_status in expected.items():
        result = WhyYouBrowserAdapter(
            _settings(), capture=lambda _subject, value=text: {"visible_text": value}
        ).capture_review(subject={})
        assert result.data["projection"]["terminal_status_class"] == terminal_status
