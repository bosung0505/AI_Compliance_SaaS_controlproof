import httpx
import pytest

from engine.adapters.whyyou.h01 import H01HTTPAdapter, H01StateObserver
from engine.h01 import H01Case
from tests.unit.test_h01_preparation import subjects


@pytest.mark.parametrize("case", [H01Case.ANONYMOUS_HTTP, H01Case.APPLICANT_HTTP])
def test_default_company_auth_cookies_and_headers_cannot_contaminate(case):
    captured = []

    def respond(request):
        captured.append(request)
        return httpx.Response(401, json={"detail": "private body must not escape"})

    with httpx.Client(
        base_url="http://127.0.0.1:18086",
        transport=httpx.MockTransport(respond),
        auth=("ambient-user", "ambient-password"),
        headers={"Authorization": "Bearer COMPANY-SECRET", "X-Actor-Type": "company_user"},
        cookies={"iep_applicant_session": "OTHER-SESSION", "company": "COMPANY-COOKIE"},
    ) as client:
        subject = next(s for s in subjects() if s.case == case)
        result = H01HTTPAdapter(client).attempt(
            subject,
            expected_version=4,
            credential="OWN-SESSION" if case == H01Case.APPLICANT_HTTP else None,
        )
    request = captured[0]
    assert "authorization" not in request.headers and "x-actor-type" not in request.headers
    assert "COMPANY" not in str(request.headers) and "OTHER" not in str(request.headers)
    assert request.headers.get("cookie") == (
        "iep_applicant_session=OWN-SESSION" if case == H01Case.APPLICANT_HTTP else None
    )
    assert result["response"] == "DENIED" and "private" not in str(result)


def test_invalid_or_missing_credentials_and_internal_roles_never_issue_http_request():
    called = []
    with httpx.Client(
        base_url="http://127.0.0.1", transport=httpx.MockTransport(lambda r: called.append(r))
    ) as client:
        adapter = H01HTTPAdapter(client)
        for case in H01Case:
            subject = next(s for s in subjects() if s.case == case)
            if case == H01Case.ANONYMOUS_HTTP:
                continue
            with pytest.raises(ValueError):
                adapter.attempt(subject, expected_version=4)
    assert called == []


@pytest.mark.parametrize(
    "status,response",
    [(201, "ACCEPTED"), (403, "DENIED"), (409, "ERROR"), (422, "ERROR"), (500, "ERROR")],
)
def test_conflicts_invalid_requests_and_server_errors_are_not_permission_denials(status, response):
    with httpx.Client(
        base_url="http://127.0.0.1", transport=httpx.MockTransport(lambda r: httpx.Response(status))
    ) as client:
        subject = next(s for s in subjects() if s.case == H01Case.ANONYMOUS_HTTP)
        assert H01HTTPAdapter(client).attempt(subject, expected_version=4)["response"] == response


def test_applicant_active_session_probe_uses_actual_cookie_boundary_only():
    seen = []

    def reply(request):
        seen.append(request)
        return httpx.Response(200)

    with httpx.Client(base_url="http://127.0.0.1", transport=httpx.MockTransport(reply)) as client:
        assert H01HTTPAdapter(client).applicant_session_active("OWN-SESSION") is True
    assert seen[0].url.path == "/v1/applicant/consents"
    assert seen[0].headers["cookie"] == "iep_applicant_session=OWN-SESSION"


def test_remote_base_url_is_refused():
    with httpx.Client(base_url="https://example.com") as client, pytest.raises(ValueError):
        H01HTTPAdapter(client)


def test_state_observer_scopes_queries_and_uses_real_audit_identity():
    subject = subjects()[0]
    queries = []

    class Result:
        def __init__(self, rows):
            self.rows = rows

        def mappings(self):
            return self

        def one(self):
            return self.rows[0]

        def all(self):
            return self.rows

    class Connection:
        def execute(self, query, params):
            sql = str(query)
            queries.append((sql, params))
            if "FROM invitations" in sql:
                return Result(
                    [
                        {
                            "company_id": str(subject.company_id),
                            "invitation_id": str(subject.invitation_id),
                            "invitation_status": "completed",
                            "recruiting_stage_id": str(subject.target_stage_id),
                            "pipeline_row_version": 4,
                            "report_id": "00000000-0000-0000-0000-000000000020",
                            "report_status": "ready",
                        }
                    ]
                )
            return Result([])

    result = H01StateObserver().capture(Connection(), subject)
    assert result.invitation_id == subject.invitation_id
    for sql, params in queries:
        assert "company_id" in sql and params["company_id"] == str(subject.company_id)
        assert "DELETE" not in sql and "UPDATE" not in sql
        assert "SELECT 'company_user'" not in sql


def test_actual_sql_observer_selects_latest_report_and_excludes_other_tenant():
    import json

    from sqlalchemy import create_engine, text

    subject = subjects()[0]
    own, foreign = str(subject.company_id), "00000000-0000-0000-0000-000000000099"
    invitation = str(subject.invitation_id)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for ddl in [
            "CREATE TABLE invitations (company_id TEXT, invitation_id TEXT, status TEXT, recruiting_stage_id TEXT, pipeline_row_version INTEGER)",
            "CREATE TABLE reports (company_id TEXT, invitation_id TEXT, report_id TEXT, status TEXT, version INTEGER)",
            "CREATE TABLE human_reviews (company_id TEXT, report_id TEXT, target_id TEXT, human_review_id TEXT, company_user_id TEXT, review_type TEXT, value TEXT, reason TEXT)",
            "CREATE TABLE audit_events (company_id TEXT, audit_event_id TEXT, actor_type TEXT, actor_id TEXT, action TEXT, result TEXT, request_id TEXT)",
        ]:
            connection.execute(text(ddl))
        for company in (own, foreign):
            connection.execute(
                text("INSERT INTO invitations VALUES (:company,:invitation,:status,:stage,4)"),
                {
                    "company": company,
                    "invitation": invitation,
                    "status": "completed",
                    "stage": str(subject.target_stage_id),
                },
            )
            for version in (1, 2):
                connection.execute(
                    text(
                        "INSERT INTO reports VALUES (:company,:invitation,:report,:status,:version)"
                    ),
                    {
                        "company": company,
                        "invitation": invitation,
                        "report": f"00000000-0000-0000-0000-00000000000{version + 3}",
                        "status": "ready",
                        "version": version,
                    },
                )
            connection.execute(
                text(
                    "INSERT INTO human_reviews VALUES (:company,:report,:invitation,:review,:user,:kind,:value,:reason)"
                ),
                {
                    "company": company,
                    "report": "00000000-0000-0000-0000-000000000005",
                    "invitation": invitation,
                    "review": "00000000-0000-0000-0000-000000000006",
                    "user": str(subject.reviewer_id),
                    "kind": "final_decision",
                    "value": json.dumps(
                        {
                            "recruiting_stage_id": str(subject.target_stage_id),
                            "internal_note": "private-value",
                        }
                    ),
                    "reason": "private-reason",
                },
            )
            connection.execute(
                text(
                    "INSERT INTO audit_events VALUES (:company,:audit,:actor,:user,:action,:result,:request)"
                ),
                {
                    "company": company,
                    "audit": "00000000-0000-0000-0000-000000000007",
                    "actor": "system",
                    "user": str(subject.reviewer_id),
                    "action": "final_decision.denied",
                    "result": "denied",
                    "request": str(subject.request_id),
                },
            )
        snapshot = H01StateObserver().capture(connection, subject)
        assert str(snapshot.report_id).endswith("005")
        assert len(snapshot.reviews) == len(snapshot.audits) == 1
        assert snapshot.audits[0].actor_type == "system"
        assert "private" not in snapshot.model_dump_json()
    engine.dispose()
