"""Local web server (contracts/web-http.md; R-002, R-004).

Bound to 127.0.0.1 only (there is no address option). Every request's Host must be 127.0.0.1:<port> or
localhost:<port>; state-changing requests are POST with the start-up CSRF token. The only state-changing route of US1 is
the readiness check; there is no route that starts a Run, retest or cleanup (D-018, SC-010). Every view passes the
output boundary (paths, redaction) before it is rendered or serialised.
"""

from __future__ import annotations

import json
import re
import secrets
import urllib.parse
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from engine.evidence import display_paths, redact
from engine.web import badges
from engine.web.memos import MemoRejected, MemoStore
from engine.web.preflight import PreflightBusy, PreflightRunner, ReadinessStore, UnknownProfile
from engine.web.readmodel import (
    SCHEMA_VERSION,
    EvidenceNotFound,
    IntegrityBlocked,
    RunNotFound,
    VerifyCache,
    WorkbenchReader,
    load_catalog,
)

BIND_ADDRESS = "127.0.0.1"
PACKAGE = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE.parents[1]
STATIC = PACKAGE / "static"
STATIC_TYPES = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8"}
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'",
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
}
MAX_FORM_BYTES = 8192
RETURN_TO = re.compile(r"^/(?:scenarios/[NHEA]-0\d)?$")

# (method, path pattern, handler name). Patterns are matched exactly; `{name}` is one path segment.
ROUTES = (
    ("GET", "/", "workbench_html"),
    ("GET", "/api/workbench", "workbench_json"),
    ("GET", "/runs/{run_id}", "run_html"),
    ("GET", "/api/runs/{run_id}", "run_json"),
    ("GET", "/runs/{run_id}/evidence", "evidence_html"),
    ("GET", "/report", "report_html"),
    ("GET", "/api/report", "report_json"),
    ("GET", "/demo/", "workbench_html"),
    ("GET", "/demo/api/workbench", "workbench_json"),
    ("GET", "/demo/runs/{run_id}", "run_html"),
    ("GET", "/demo/api/runs/{run_id}", "run_json"),
    ("GET", "/demo/runs/{run_id}/evidence", "evidence_html"),
    ("GET", "/demo/report", "report_html"),
    ("GET", "/demo/api/report", "report_json"),
    ("GET", "/static/{name}", "static"),
    ("GET", "/favicon.ico", "favicon"),
    ("POST", "/preflight", "preflight"),
    ("POST", "/runs/{run_id}/memos", "memo"),
)

ERRORS = {
    "USAGE": HTTPStatus.BAD_REQUEST,
    "CONTRACT": HTTPStatus.FORBIDDEN,
    "NOT_FOUND": HTTPStatus.NOT_FOUND,
    "BUSY": HTTPStatus.CONFLICT,
    "INTEGRITY": HTTPStatus.UNPROCESSABLE_ENTITY,
    "UNEXPECTED": HTTPStatus.INTERNAL_SERVER_ERROR,
}


class WebServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port: int, *, actual: WorkbenchReader, demo: WorkbenchReader, runner: Any, catalog: dict) -> None:
        super().__init__((BIND_ADDRESS, port), _Handler)
        self.csrf_token = secrets.token_urlsafe(32)
        self.readers = {"ACTUAL": actual, "DEMO": demo}
        self.runner = runner
        self.catalog = catalog
        self.profiles = {
            (entry["id"], profile["execution_profile"]) for entry in catalog["scenarios"] for profile in entry["profiles"]
        }
        self.templates = Environment(
            loader=FileSystemLoader(PACKAGE / "templates"), autoescape=select_autoescape(["html"]), trim_blocks=True,
            lstrip_blocks=True,
        )
        self.templates.filters["when"] = _when
        self.templates.filters["short_id"] = lambda value: f"{value[:8]}…" if value else ""
        self.templates.filters["size"] = _size
        self.templates.filters["mime_label"] = _mime_label

    @property
    def allowed_hosts(self) -> set[str]:
        port = self.server_address[1]
        return {f"127.0.0.1:{port}", f"localhost:{port}"}


def make_server(
    port: int = 8765,
    *,
    run_root: Path,
    demo_root: Path,
    state_dir: Path,
    catalog: dict[str, Any] | None = None,
    target: str = "whyyou-local",
    preflight_runner: Any = None,
) -> WebServer:
    """Create the server on 127.0.0.1:<port> (0 picks a free port). The caller runs `serve_forever`."""
    catalog = catalog or load_catalog()
    cache = VerifyCache()
    actual_store = ReadinessStore(Path(state_dir) / "preflight")
    memos = MemoStore(Path(state_dir) / "memos")
    demo_store = ReadinessStore(Path(demo_root).parent / "preflight")
    runner = preflight_runner or PreflightRunner(catalog, actual_store, target=target, cwd=REPO_ROOT)
    return WebServer(
        port,
        actual=WorkbenchReader(catalog, run_root, readiness=actual_store, origin="ACTUAL", cache=cache, memos=memos),
        demo=WorkbenchReader(catalog, demo_root, readiness=demo_store, origin="DEMO", cache=cache),
        runner=runner,
        catalog=catalog,
    )


class _Handler(BaseHTTPRequestHandler):
    server: WebServer
    server_version = "ControlProof"
    sys_version = ""

    def log_message(self, format: str, *args: Any) -> None:
        return

    # -- dispatch ------------------------------------------------------------------------------------------------
    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def _dispatch(self, method: str) -> None:
        path = urllib.parse.urlsplit(self.path).path
        # Read a POST body before any answer: replying without reading it lets the client see a reset connection.
        self._body = self._read_body() if method == "POST" else b""
        if self.headers.get("Host") not in self.server.allowed_hosts:
            self._error("CONTRACT", "HOST_NOT_ALLOWED", "허용되지 않은 Host입니다.", status=HTTPStatus.MISDIRECTED_REQUEST)
            return
        if method == "GET" and path == "/demo":
            self._redirect("/demo/", HTTPStatus.MOVED_PERMANENTLY)
            return
        for route_method, pattern, name in ROUTES:
            params = _match(pattern, path)
            if params is None:
                continue
            if route_method != method:
                continue
            try:
                getattr(self, f"_route_{name}")(path, **params)
            except Exception:  # noqa: BLE001 - never leak internals; answer with a generic error
                self._error("UNEXPECTED", "UNEXPECTED", "처리 중 오류가 났습니다.")
            return
        self._error("NOT_FOUND", "ROUTE_NOT_FOUND", "요청한 화면이 없습니다.")

    # -- routes --------------------------------------------------------------------------------------------------
    def _reader(self, path: str) -> WorkbenchReader:
        return self.server.readers["DEMO" if path.startswith("/demo/") else "ACTUAL"]

    def _route_workbench_json(self, path: str) -> None:
        reader = self._reader(path)
        self._json(HTTPStatus.OK, _boundary(reader.workbench(), reader.run_root))

    def _route_workbench_html(self, path: str) -> None:
        reader = self._reader(path)
        view = _boundary(reader.workbench(), reader.run_root)
        self._html(HTTPStatus.OK, "workbench.html", view=view, prefix="/demo" if view["demo"] else "")

    def _route_run_json(self, path: str, run_id: str) -> None:
        reader = self._reader(path)
        try:
            view = reader.run(run_id)
        except RunNotFound:
            self._error("NOT_FOUND", "RUN_NOT_FOUND", "요청한 실행 기록이 없습니다.")
            return
        self._json(HTTPStatus.OK, _boundary(view, reader.run_root))

    def _route_run_html(self, path: str, run_id: str) -> None:
        reader = self._reader(path)
        try:
            view = _boundary(reader.run(run_id), reader.run_root)
        except RunNotFound:
            self._error("NOT_FOUND", "RUN_NOT_FOUND", "요청한 실행 기록이 없습니다.")
            return
        self._html(HTTPStatus.OK, "run.html", view=view, prefix="/demo" if view["demo"] else "")

    def _route_evidence_html(self, path: str, run_id: str) -> None:
        reader = self._reader(path)
        ref = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("ref", [""])[0]
        try:
            view = _boundary(reader.evidence(run_id, ref), reader.run_root)
        except RunNotFound:
            self._error("NOT_FOUND", "RUN_NOT_FOUND", "요청한 실행 기록이 없습니다.")
            return
        except EvidenceNotFound:
            self._error("NOT_FOUND", "EVIDENCE_NOT_FOUND", "요청한 증적이 이 실행 기록에 없습니다.")
            return
        except IntegrityBlocked:
            self._error("INTEGRITY", "INTEGRITY_FAILED", "무결성 실패 기록의 증적 원본은 보이지 않습니다.")
            return
        self._html(HTTPStatus.OK, "evidence.html", view=view, prefix="/demo" if view["demo"] else "")

    def _route_report_json(self, path: str) -> None:
        reader = self._reader(path)
        self._json(HTTPStatus.OK, _boundary(reader.report(), reader.run_root))

    def _route_report_html(self, path: str) -> None:
        reader = self._reader(path)
        view = _boundary(reader.report(), reader.run_root)
        self._html(HTTPStatus.OK, "report.html", view=view, prefix="/demo" if view["demo"] else "")

    def _route_memo(self, path: str, run_id: str) -> None:
        form = self._form()
        if form is None:
            self._error("USAGE", "FORM_INVALID", "요청 형식이 올바르지 않습니다.")
            return
        if not secrets.compare_digest(form.get("csrf_token", ""), self.server.csrf_token):
            self._error("CONTRACT", "CSRF_TOKEN_MISMATCH", "요청 확인 값이 맞지 않습니다. 화면을 새로 고친 뒤 다시 시도하세요.")
            return
        reader = self.server.readers["ACTUAL"]
        try:
            reader.run(run_id)
            reader.memos.add(run_id, author=form.get("author", ""), text=form.get("text", ""))
        except RunNotFound:
            self._error("NOT_FOUND", "RUN_NOT_FOUND", "요청한 실행 기록이 없습니다.")
            return
        except MemoRejected as rejected:
            self._error("USAGE", "MEMO_REJECTED", str(rejected))
            return
        self._redirect(f"/runs/{run_id}#memos", HTTPStatus.SEE_OTHER)

    def _route_static(self, path: str, name: str) -> None:
        target = STATIC / name
        if not re.fullmatch(r"[a-z0-9_-]+\.(css|js)", name) or not target.is_file():
            self._error("NOT_FOUND", "STATIC_NOT_FOUND", "요청한 파일이 없습니다.")
            return
        self._send(HTTPStatus.OK, target.read_bytes(), STATIC_TYPES[target.suffix])

    def _route_favicon(self, path: str) -> None:
        self._send(HTTPStatus.NO_CONTENT, b"", "image/x-icon")

    def _route_preflight(self, path: str) -> None:
        form = self._form()
        if form is None:
            self._error("USAGE", "FORM_INVALID", "요청 형식이 올바르지 않습니다.")
            return
        if not secrets.compare_digest(form.get("csrf_token", ""), self.server.csrf_token):
            self._error("CONTRACT", "CSRF_TOKEN_MISMATCH", "요청 확인 값이 맞지 않습니다. 화면을 새로 고친 뒤 다시 시도하세요.")
            return
        scenario_id, profile = form.get("scenario_id", ""), form.get("execution_profile", "")
        if (scenario_id, profile) not in self.server.profiles:
            self._error("USAGE", "UNKNOWN_PROFILE", "카탈로그에 없는 시나리오·프로필입니다.")
            return
        return_to = form.get("return_to") or f"/scenarios/{scenario_id}"
        if not RETURN_TO.fullmatch(return_to):
            self._error("USAGE", "RETURN_TO_INVALID", "돌아갈 화면이 올바르지 않습니다.")
            return
        try:
            self.server.runner.check(scenario_id, profile)
        except UnknownProfile:
            self._error("USAGE", "UNKNOWN_PROFILE", "카탈로그에 없는 시나리오·프로필입니다.")
            return
        except PreflightBusy:
            self._error("BUSY", "PREFLIGHT_RUNNING", "준비 상태 확인이 이미 진행 중입니다. 끝난 뒤 다시 시도하세요.")
            return
        self._redirect(return_to, HTTPStatus.SEE_OTHER)

    # -- responses -----------------------------------------------------------------------------------------------
    def _read_body(self) -> bytes | None:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return None
        if length < 0 or length > MAX_FORM_BYTES:
            self.close_connection = True
            return None
        return self.rfile.read(length)

    def _form(self) -> dict[str, str] | None:
        if self._body is None:
            return None
        body = self._body.decode("utf-8", errors="replace")
        return {key: values[0] for key, values in urllib.parse.parse_qs(body).items()}

    def _wants_json(self) -> bool:
        path = urllib.parse.urlsplit(self.path).path
        return self.command == "POST" or path.startswith(("/api/", "/demo/api/"))

    def _error(self, kind: str, code: str, detail: str, *, status: HTTPStatus | None = None) -> None:
        status = status or ERRORS[kind]
        payload = {"schema_version": SCHEMA_VERSION, "view": "error", "error_kind": kind, "code": code, "detail": detail}
        if self._wants_json():
            self._json(status, payload)
        else:
            self._html(status, "error.html", view=payload, prefix="")

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _html(self, status: HTTPStatus, template: str, **context: Any) -> None:
        page = self.server.templates.get_template(template).render(
            badges=badges.BADGES, csrf_token=self.server.csrf_token, catalog=self.server.catalog, **context
        )
        self._send(status, page.encode("utf-8"), "text/html; charset=utf-8")

    def _redirect(self, location: str, status: HTTPStatus) -> None:
        self.send_response(status)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)


def _match(pattern: str, path: str) -> dict[str, str] | None:
    if "{" not in pattern:
        return {} if pattern == path else None
    regex = "^" + re.sub(r"\\\{(\w+)\\\}", r"(?P<\1>[^/]+)", re.escape(pattern)) + "$"
    found = re.match(regex, path)
    return found.groupdict() if found else None


def _boundary(view: dict[str, Any], run_root: Path) -> dict[str, Any]:
    """Output boundary (R-009, SC-007): run-root paths become `<run_root>/…`, other paths `[PATH]`, then redaction."""
    return redact(display_paths(view, run_root=run_root))


def _when(value: str | None) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value


def _size(value: int | None) -> str:
    if value is None:
        return "기록 없음"
    return f"{value} B" if value < 1024 else f"{value / 1024:.1f} KB"


def _mime_label(value: str | None) -> str:
    return {
        "application/x-ndjson": "기록 목록",
        "application/json": "문서",
        "image/png": "이미지",
    }.get(str(value), str(value))
