"""Playwright observation of the WhyYou applicant consent step (Spec 009 N-01; research R1).

Only measurements, a capture digest and policy identifiers leave this module. Raw invitation tokens and the
applicant session cookie stay in the in-memory credential store; response bodies are never retained.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import urlparse

from engine.adapters.base import AdapterResult
from engine.adapters.whyyou.n02_seed import N02CredentialStore
from engine.config import Settings
from engine.n01 import MEASUREMENT_VERSION, N01LaneRecord

SESSION_COOKIE = "iep_applicant_session"
CONSENT_PATH = "/v1/applicant/consents"
SUBJECT_FIELDS = ("run_id", "lane_id", "subject_ref", "invitation_id", "applicant_id")
STEP_TIMEOUT_MS = 15_000

# One evaluation per consent screen (contracts/assertions-v9.md "읽을 수 있게 표시됨").
MEASURE_JS = """
(fragments) => {
  window.scrollTo(0, 0);
  const norm = (value) => (value || "").replace(/\\s+/g, " ").trim();
  const doc = document.documentElement;
  const operations = [];
  const elements = [document.body, ...document.body.querySelectorAll("*")];
  const measured = fragments.map(({fragment_id, expected_text}) => {
    const target = norm(expected_text);
    const holders = elements.filter((el) => norm(el.textContent).includes(target));
    const found = holders.find((el) => ![...el.children].some((child) => norm(child.textContent).includes(target)));
    if (!found) {
      return {fragment_id, expected_text, text_present: false, bbox: null, in_viewport: false, center_hit: false,
              not_occluded: false, doc_scroll_width: doc.scrollWidth, doc_client_width: doc.clientWidth,
              el_scroll_width: 0, el_client_width: 0, no_horizontal_overflow: false,
              style_visible: false, not_clipped: false, clip_ancestor: null, computed_opacity: null,
              computed_visibility: null};
    }
    const before = window.scrollY;
    found.scrollIntoView({block: "nearest"});
    if (window.scrollY !== before) operations.push({kind: "scroll", fragment_id, scroll_y: window.scrollY});
    const rect = found.getBoundingClientRect();
    const inViewport = rect.left >= 0 && rect.right <= window.innerWidth && rect.top >= 0
      && rect.bottom <= window.innerHeight;
    const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
    // v2: only the target or its descendants count; an ancestor hit is accepted only when it is the target's label.
    const related = !!hit && (hit === found || found.contains(hit)
      || (hit.tagName === "LABEL" && hit.contains(found)));
    const noOverflow = doc.scrollWidth <= doc.clientWidth && found.scrollWidth <= found.clientWidth;
    // v2 style_visible: no display:none on the element or any ancestor, own computed visibility, cumulative opacity.
    const ownStyle = getComputedStyle(found);
    let opacity = 1, displayed = true;
    for (let node = found; node && node.nodeType === 1; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (style.display === "none") displayed = false;
      opacity *= parseFloat(style.opacity);
    }
    const styleVisible = displayed && ownStyle.visibility === "visible" && opacity > 0;
    // v2 not_clipped: inside every non-visible-overflow ancestor's inner box (1px tolerance) and no own clipping.
    let clipAncestor = null;
    for (let node = found.parentElement; node && node !== doc && node !== document.body; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (style.overflowX === "visible" && style.overflowY === "visible") continue;
      const box = node.getBoundingClientRect();
      const left = box.left + node.clientLeft, top = box.top + node.clientTop;
      const right = left + node.clientWidth, bottom = top + node.clientHeight;
      if (rect.left < left - 1 || rect.top < top - 1 || rect.right > right + 1 || rect.bottom > bottom + 1) {
        const classes = typeof node.className === "string" && node.className.trim()
          ? "." + node.className.trim().split(/\\s+/).join(".") : "";
        clipAncestor = (node.tagName.toLowerCase() + classes).slice(0, 80);
        break;
      }
    }
    const ownClipped = found.scrollHeight > found.clientHeight + 1 || found.scrollWidth > found.clientWidth + 1;
    return {fragment_id, expected_text, text_present: true,
            bbox: {x: rect.x, y: rect.y, width: rect.width, height: rect.height},
            in_viewport: inViewport, center_hit: !!hit, not_occluded: related,
            doc_scroll_width: doc.scrollWidth, doc_client_width: doc.clientWidth,
            el_scroll_width: found.scrollWidth, el_client_width: found.clientWidth,
            no_horizontal_overflow: noOverflow,
            style_visible: styleVisible, not_clipped: clipAncestor === null && !ownClipped,
            clip_ancestor: clipAncestor, computed_opacity: opacity, computed_visibility: ownStyle.visibility};
  });
  return {fragments: measured, operations};
}
"""
SECRETS_ABSENT_JS = """
(secrets) => {
  const html = document.documentElement.outerHTML;
  const text = document.body.innerText;
  return secrets.every((secret) => !html.includes(secret) && !text.includes(secret));
}
"""


def measure_fragments(
    page, expected: Mapping[str, list[tuple[str, str]]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Run MEASURE_JS on the page at its current viewport; returns (items, operations) in item order."""
    order = [(item, str(fid), str(text)) for item, fragments in expected.items() for fid, text in fragments]
    measured = page.evaluate(MEASURE_JS, [{"fragment_id": fid, "expected_text": text} for _, fid, text in order])
    by_item: dict[str, list[dict[str, Any]]] = {}
    for (item, _, _), fragment in zip(order, measured["fragments"], strict=True):
        by_item.setdefault(item, []).append(fragment)
    items = [{"item_id": item, "fragments": fragments} for item, fragments in by_item.items()]
    return items, measured["operations"]


class _StepFailed(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class WhyYouApplicantBrowserAdapter:
    def __init__(
        self,
        settings: Settings,
        *,
        credentials: N02CredentialStore,
        capture: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    ) -> None:
        self.settings = settings
        self.credentials = credentials
        self._capture = capture
        self._playwright = None
        self._browser = None

    def observe_consent(
        self,
        *,
        subject: Mapping[str, Any],
        viewport: Mapping[str, int],
        fragment_builder: Callable[[Mapping[str, Any]], Mapping[str, list[tuple[str, str]]]],
        display_name: str,
    ) -> AdapterResult:
        """``fragment_builder`` turns the observed consent-policy GET body into expected fragments."""
        app_url = self.settings.applicant_app_url
        if not app_url:
            return AdapterResult(False, "APPLICANT_APP_URL_MISSING")
        subject_ref = str(subject["subject_ref"])
        raw_token = self.credentials.get(f"{subject_ref}:invitation_token")
        if raw_token is None:
            return AdapterResult(False, "N01_INVITATION_TOKEN_MISSING")
        request = {
            "subject": {name: str(subject[name]) for name in SUBJECT_FIELDS},
            "viewport": {"width": int(viewport["width"]), "height": int(viewport["height"])},
            "fragment_builder": fragment_builder,
            "display_name": display_name,
            "raw_token": raw_token,
            "app_url": app_url,
        }
        try:
            raw = self._capture(request) if self._capture else self._capture_with_playwright(request)
        except TimeoutError:
            return AdapterResult(False, "BROWSER_TIMEOUT")
        except Exception as exc:  # noqa: BLE001 - adapter boundary returns a sanitized envelope
            code = (
                "BROWSER_AUTH_FAILED"
                if "401" in str(exc) or "403" in str(exc)
                else "BROWSER_CAPTURE_FAILED"
            )
            return AdapterResult(False, code, detail=type(exc).__name__)
        cookie = raw.get("session_cookie")
        if cookie:
            self.credentials.put(subject_ref, str(cookie))
        screenshot = bytes(raw.get("screenshot_bytes") or b"")
        try:
            record = N01LaneRecord.model_validate(
                {
                    "lane": request["subject"]["lane_id"],
                    "viewport": request["viewport"],
                    "subject": request["subject"],
                    "step_reached": raw.get("step_reached", "error"),
                    "capture": {"sha256": hashlib.sha256(screenshot).hexdigest(), "bytes": len(screenshot)}
                    if screenshot
                    else None,
                    "token_absent_in_dom": raw.get("token_absent_in_dom"),
                    "operations": list(raw.get("operations", ())),
                    "items": [
                        {
                            "item_id": item["item_id"],
                            "fragments": [
                                {
                                    **fragment,
                                    "expected_text_digest": hashlib.sha256(
                                        str(fragment["expected_text"]).encode()
                                    ).hexdigest(),
                                }
                                for fragment in item["fragments"]
                            ],
                        }
                        for item in raw.get("items", ())
                    ],
                    "measurement_error": raw.get("measurement_error"),
                    "measurement_version": raw.get("measurement_version"),
                }
            )
        except (KeyError, TypeError, ValueError) as exc:
            return AdapterResult(False, "BROWSER_RESULT_INVALID", detail=type(exc).__name__)
        policy = raw.get("screen_policy")
        data = {
            "record": record.model_dump(mode="json"),
            "screenshot_bytes": screenshot,
            "screen_policy": {"version": str(policy["version"]), "digest": str(policy["digest"])}
            if policy
            else None,
            "commit_status": raw.get("commit_status"),
        }
        if record.measurement_error or record.step_reached != "ready":
            return AdapterResult(False, record.measurement_error or "BROWSER_STEP_INCOMPLETE", data)
        return AdapterResult(True, "APPLICANT_CONSENT_OBSERVED", data)

    def _capture_with_playwright(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright

        if self._playwright is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
        mobile = request["subject"]["lane_id"] == "mobile"
        options: dict[str, Any] = {"viewport": dict(request["viewport"]), "locale": "ko-KR"}
        if mobile:
            options.update(is_mobile=True, has_touch=True, device_scale_factor=2)
        context = self._browser.new_context(**options)
        observed: dict[str, Any] = {
            "step_reached": "error",
            "measurement_error": None,
            "items": [],
            "operations": [],
            "token_absent_in_dom": None,
            "screenshot_bytes": b"",
            "screen_policy": None,
            "commit_status": None,
            "session_cookie": None,
            "measurement_version": MEASUREMENT_VERSION,
        }
        policy_body: dict[str, Any] = {}

        def on_response(response) -> None:
            try:
                if urlparse(response.url).path != CONSENT_PATH:
                    return
                if response.request.method == "GET" and response.ok:
                    body = response.json()
                    observed["screen_policy"] = {
                        "version": str(body["policy_version"]),
                        "digest": str(body["content_digest"]),
                    }
                    # Kept only in this closure to build the expected fragments; never returned.
                    policy_body.clear()
                    policy_body.update(body)
                elif response.request.method == "POST":
                    observed["commit_status"] = response.status
            except Exception:  # noqa: BLE001 - an unreadable response leaves screen_policy empty
                return

        def session_cookie() -> str | None:
            return next(
                (item["value"] for item in context.cookies() if item["name"] == SESSION_COOKIE), None
            )

        try:
            page = context.new_page()
            page.on("response", on_response)
            try:
                response = page.goto(
                    f"{request['app_url']}/access/{request['raw_token']}",
                    wait_until="networkidle",
                    timeout=STEP_TIMEOUT_MS,
                )
            except PlaywrightTimeoutError as exc:
                raise TimeoutError("applicant app did not load") from exc
            if response and response.status in {401, 403}:
                raise RuntimeError(f"browser authentication failed: {response.status}")
            stage = "BROWSER_EXCHANGE_FAILED"
            try:
                page.get_by_role("button", name="내용을 확인하고 계속").click(timeout=STEP_TIMEOUT_MS)
                identity = page.locator('input[autocomplete="name"]')
                identity.wait_for(state="visible", timeout=STEP_TIMEOUT_MS)
                if session_cookie() is None:
                    raise _StepFailed("BROWSER_SESSION_COOKIE_MISSING")
                observed["step_reached"] = "exchange"
                stage = "BROWSER_IDENTITY_FAILED"
                identity.fill(request["display_name"])
                page.get_by_role("button", name="본인 확인 완료").click(timeout=STEP_TIMEOUT_MS)
                observed["step_reached"] = "identity"
                stage = "BROWSER_CONSENT_STEP_MISSING"
                page.locator('section[aria-label="동의 정책"]').wait_for(
                    state="visible", timeout=STEP_TIMEOUT_MS
                )
                observed["step_reached"] = "consent"
                if not policy_body:
                    raise _StepFailed("BROWSER_POLICY_RESPONSE_MISSING")
                try:
                    expected = request["fragment_builder"](dict(policy_body))
                except (KeyError, TypeError, ValueError) as exc:
                    raise _StepFailed("BROWSER_POLICY_RESPONSE_INVALID") from exc
                stage = "BROWSER_MEASURE_FAILED"
                observed["items"], observed["operations"] = measure_fragments(page, expected)
                secrets = [value for value in (request["raw_token"], session_cookie()) if value]
                observed["token_absent_in_dom"] = bool(page.evaluate(SECRETS_ABSENT_JS, secrets))
                observed["screenshot_bytes"] = page.screenshot(full_page=True)
                stage = "BROWSER_COMMIT_FAILED"
                for checkbox in page.locator("input[type=checkbox]").all():
                    checkbox.check(timeout=STEP_TIMEOUT_MS)
                with page.expect_response(
                    lambda item: urlparse(item.url).path == CONSENT_PATH
                    and item.request.method == "POST",
                    timeout=STEP_TIMEOUT_MS,
                ) as commit:
                    page.get_by_role("button", name="동의하고 계속").click(timeout=STEP_TIMEOUT_MS)
                observed["commit_status"] = commit.value.status
                page.get_by_role("status").filter(has_text="ACCESS VERIFIED").wait_for(
                    state="visible", timeout=STEP_TIMEOUT_MS
                )
                observed["step_reached"] = "ready"
            except _StepFailed as failure:
                observed["measurement_error"] = failure.code
            except Exception:  # noqa: BLE001 - keep the partial record; the stage names the failed step
                observed["measurement_error"] = stage
            observed["session_cookie"] = session_cookie()
            return observed
        finally:
            context.close()

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None
