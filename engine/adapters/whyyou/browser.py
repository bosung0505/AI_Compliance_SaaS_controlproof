"""Playwright capture of the actual WhyYou company review route."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from engine.adapters.base import AdapterResult
from engine.config import Settings
from engine.evidence import redact


class WhyYouBrowserAdapter:
    def __init__(
        self,
        settings: Settings,
        capture: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    ) -> None:
        self.settings = settings
        self._capture = capture
        self._playwright = None
        self._browser = None

    def capture_review(self, *, subject: Mapping[str, Any]) -> AdapterResult:
        try:
            raw = (
                self._capture(subject) if self._capture else self._capture_with_playwright(subject)
            )
        except TimeoutError:
            return AdapterResult(False, "BROWSER_TIMEOUT")
        except Exception as exc:  # noqa: BLE001 - adapter boundary returns a sanitized envelope
            code = (
                "BROWSER_AUTH_FAILED"
                if "401" in str(exc) or "403" in str(exc)
                else "BROWSER_CAPTURE_FAILED"
            )
            return AdapterResult(False, code, detail=type(exc).__name__)
        visible_text = str(redact(str(raw.get("visible_text", ""))))
        status_class = str(raw.get("status_class") or _classify_status(visible_text))
        projection = {
            "route": "/review/{session_id}",
            "role": str(raw.get("role", "main")),
            "visible_text": visible_text,
            "ready_content_visible": bool(raw.get("ready_content_visible", False)),
            "decision_control_visible": bool(raw.get("decision_control_visible", False)),
            "viewport": dict(raw.get("viewport", {"width": 1440, "height": 900})),
            "status_class": status_class,
        }
        return AdapterResult(
            True,
            "BROWSER_CAPTURED",
            {"projection": projection, "screenshot_bytes": raw.get("screenshot_bytes", b"")},
        )

    def _capture_with_playwright(self, subject: Mapping[str, Any]) -> Mapping[str, Any]:
        from playwright.sync_api import sync_playwright

        if self._playwright is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
        context = self._browser.new_context(
            viewport={"width": 1440, "height": 900},
            extra_http_headers={"Authorization": f"Bearer {self.settings.whyyou_company_token}"},
        )
        try:
            page = context.new_page()
            route = (
                f"{self.settings.whyyou_console_url}/review/{subject['interview_session_id']}"
                f"?invitationId={subject['invitation_id']}"
            )
            response = page.goto(route, wait_until="networkidle", timeout=15_000)
            if response and response.status in {401, 403}:
                raise RuntimeError(f"browser authentication failed: {response.status}")
            text = page.locator("body").inner_text(timeout=5_000)
            screenshot = page.screenshot(full_page=True)
            lowered = text.casefold()
            return {
                "visible_text": text,
                "ready_content_visible": any(
                    word in lowered for word in ("종합 평가", "최종 리포트", "overall score")
                )
                and not any(word in lowered for word in ("생성 중", "처리 중", "오류", "실패")),
                "decision_control_visible": page.get_by_role("button").count() > 0,
                "screenshot_bytes": screenshot,
                "viewport": {"width": 1440, "height": 900},
            }
        finally:
            context.close()

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None


def _classify_status(text: str) -> str:
    lowered = text.casefold()
    if any(word in lowered for word in ("실패", "오류", "failed", "error")):
        return "failed"
    if any(word in lowered for word in ("지연", "delayed")):
        return "delayed"
    if any(word in lowered for word in ("생성 중", "처리 중", "queued", "processing")):
        return "queued_only"
    if any(word in lowered for word in ("리포트", "report")):
        return "ready"
    return "unknown"
