"""Isolated H-01 HTTP and read-only business-state boundaries; no role spoofing."""

import json
from http.cookies import SimpleCookie
from ipaddress import ip_address

import httpx
from sqlalchemy import text

from engine.h01 import H01Audit, H01Case, H01Review, H01State
from engine.models import canonical_json_bytes, sha256_bytes


class H01HTTPAdapter:
    def __init__(self, client: httpx.Client):
        self.client = client
        host = client.base_url.host
        try:
            loopback = ip_address(host).is_loopback
        except ValueError:
            loopback = host == "localhost"
        if not loopback or client.base_url.scheme not in {"http", "https"}:
            raise ValueError("H-01 preparation adapter requires a loopback target")

    @staticmethod
    def _credential_headers(case, credential):
        if case == H01Case.ANONYMOUS_HTTP:
            if credential is not None:
                raise ValueError("anonymous requests must have no credential")
            return {}
        if case not in {H01Case.COMPANY_CONTROL, H01Case.APPLICANT_HTTP}:
            raise ValueError("internal/assistant cases must use their actual execution boundary")
        if not credential or any(c in credential for c in "\r\n;"):
            raise ValueError("an explicit valid credential is required")
        if case == H01Case.COMPANY_CONTROL:
            return {"Authorization": "Bearer " + credential}
        cookie = SimpleCookie()
        cookie["iep_applicant_session"] = credential
        return {"Cookie": cookie.output(header="").strip()}

    def _send(self, method, path, *, headers, body=None):
        # Client.build_request()/post() would merge ambient company headers/cookies.
        request = httpx.Request(
            method,
            self.client.base_url.join(path),
            headers=headers,
            json=body,
        )
        return self.client.send(request, auth=None, follow_redirects=False)

    def applicant_session_active(self, credential):
        """Liveness only: the lifecycle must ALSO bind this session to the owned applicant."""
        headers = self._credential_headers(H01Case.APPLICANT_HTTP, credential)
        try:
            return self._send("GET", "/v1/applicant/consents", headers=headers).status_code == 200
        except httpx.HTTPError:
            return False

    def attempt(self, subject, *, expected_version, credential=None):
        subject.assert_owned()
        if type(expected_version) is not int or expected_version < 0:
            raise ValueError("invalid pipeline version")
        headers = self._credential_headers(subject.case, credential)
        headers.update(
            {
                "X-Request-ID": str(subject.request_id),
                "X-Trace-ID": f"controlproof:h01:{subject.run_id}:{subject.case}",
                "Idempotency-Key": f"controlproof:h01:{subject.request_id}",
            }
        )
        try:
            response = self._send(
                "POST",
                f"/v1/invitations/{subject.invitation_id}/final-decisions",
                headers=headers,
                body={
                    "recruiting_stage_id": str(subject.target_stage_id),
                    "expected_pipeline_version": expected_version,
                },
            )
        except httpx.HTTPError:
            return {"response": "UNAVAILABLE", "http_status": None, "request_observed": False}
        status = response.status_code
        classification = (
            "ACCEPTED" if 200 <= status < 300 else "DENIED" if status in {401, 403} else "ERROR"
        )
        return {"response": classification, "http_status": status, "request_observed": True}


class H01StateObserver:
    """Caller supplies an isolated read-only connection; all queries remain subject scoped."""

    def capture(self, connection, subject):
        subject.assert_owned()
        params = {
            "company_id": str(subject.company_id),
            "invitation_id": str(subject.invitation_id),
            "request_id": str(subject.request_id),
        }
        state = dict(
            connection.execute(
                text(
                    "SELECT i.company_id, i.invitation_id, i.status AS invitation_status, "
                    "i.recruiting_stage_id, i.pipeline_row_version, r.report_id, "
                    "r.status AS report_status FROM invitations i LEFT JOIN reports r "
                    "ON r.company_id=i.company_id AND r.invitation_id=i.invitation_id "
                    "AND r.version=(SELECT MAX(version) FROM reports "
                    "WHERE company_id=i.company_id AND invitation_id=i.invitation_id) "
                    "WHERE i.company_id=:company_id AND i.invitation_id=:invitation_id"
                ),
                params,
            )
            .mappings()
            .one()
        )
        review_params = {
            **params,
            "report_id": str(state["report_id"]) if state["report_id"] else None,
        }
        reviews = (
            connection.execute(
                text(
                    "SELECT human_review_id, company_user_id, review_type, value, reason FROM human_reviews "
                    "WHERE company_id=:company_id AND (target_id=:invitation_id OR report_id=:report_id) "
                    "ORDER BY human_review_id"
                ),
                review_params,
            )
            .mappings()
            .all()
        )
        audits = (
            connection.execute(
                text(
                    "SELECT audit_event_id, actor_type, actor_id, action, result, request_id "
                    "FROM audit_events WHERE company_id=:company_id AND request_id=:request_id "
                    "ORDER BY audit_event_id"
                ),
                params,
            )
            .mappings()
            .all()
        )
        projected = []
        for row in reviews:
            value = json.loads(row["value"]) if isinstance(row["value"], str) else row["value"]
            if not isinstance(value, dict):
                raise TypeError("unreadable review value")
            projected.append(
                H01Review(
                    review_id=row["human_review_id"],
                    company_user_id=row["company_user_id"],
                    stage_id=value.get("recruiting_stage_id"),
                    review_type=row["review_type"],
                    value_digest=sha256_bytes(canonical_json_bytes(value)),
                    reason_digest=sha256_bytes(str(row["reason"] or "").encode("utf-8")),
                )
            )
        state["reviews"] = tuple(projected)
        state["audits"] = tuple(
            H01Audit(
                audit_id=row["audit_event_id"],
                actor_type=row["actor_type"],
                actor_id=row["actor_id"],
                action=row["action"],
                result=row["result"],
                request_id=row["request_id"],
            )
            for row in audits
        )
        result = H01State(**state)
        if result.company_id != subject.company_id or result.invitation_id != subject.invitation_id:
            raise ValueError("foreign subject state")
        return result
