"""H-02 owned functional controls; report model validation and product HTTP paths stay real."""

import json
import os
import subprocess
from uuid import UUID, uuid5

from sqlalchemy import text

from engine.adapters.whyyou.h01_live import H01Live, parse_helper_output, plan_cases
from engine.adapters.whyyou.spec004_seed import WhyYouSpec004SeedAdapter
from engine.h01 import NAMESPACE, H01Case
from engine.h02_actual import FIXTURE_ID
from engine.models import sha256_bytes
from seeds.n02_subjects import SeedRow
from seeds.spec004_subjects import lane_rows

FIXTURE_DIGEST = sha256_bytes(f"controlproof:{FIXTURE_ID}".encode())
NAMES = (
    "human_low",
    "human_high",
    "search_legacy",
    "answer_legacy",
    "stream_legacy",
    "answer_assigned",
)


def h02_cases(run_id, settings):
    original = plan_cases(run_id, settings)
    selected = [original[i] for i in (0, 10, 1, 2, 3, 4)]
    low = selected[0][2]
    path, subject, high = selected[1]
    criterion = high.criteria[0].model_copy(update={"criterion_id": low.criteria[0].criterion_id})
    high = high.model_copy(
        update={
            "position_id": low.position_id,
            "competency_model_version_id": low.competency_model_version_id,
            "criteria": (criterion,),
        }
    )
    selected[1] = path, subject, high
    return tuple(selected)


class H02Live(H01Live):
    def __init__(self, settings, adapters, run_id):
        super().__init__(settings, adapters, run_id)
        self.cases = h02_cases(run_id, settings)
        self.names = {
            str(lane.run_id): name for name, (_, _, lane) in zip(NAMES, self.cases, strict=True)
        }
        low_lane = self.cases[0][2]
        low_rows = lane_rows(
            low_lane,
            company_id=UUID(settings.whyyou_company_id),
            reviewer_id=UUID(settings.whyyou_company_user_id),
        )
        initial = next(
            row.values["recruiting_stage_id"]
            for row in low_rows
            if row.table == "recruiting_stages"
        )
        names = self.names

        class H02Seed(WhyYouSpec004SeedAdapter):
            def _write(seed, case_run, rows, code):
                name = names[case_run]
                score = 90 if name == "human_high" else 35
                adapted = []
                for row in rows:
                    values = dict(row.values)
                    if name == "human_high" and row.table in {
                        "positions",
                        "recruiting_stages",
                        "competency_model_versions",
                        "evaluation_criteria",
                    }:
                        continue
                    if name == "human_high" and row.table == "invitations":
                        values["recruiting_stage_id"] = initial
                    if row.table == "transcript_segments":
                        values["text"] = f"[controlproof-h02 score={score}] {values['text']}"
                    adapted.append(SeedRow(row.table, values))
                return super()._write(case_run, tuple(adapted), code)

        self.seed_adapter_type = H02Seed
        for _, subject, lane in self.cases:
            self.resources.update(
                (
                    subject.applicant_id,
                    subject.invitation_id,
                    subject.request_id,
                    subject.target_stage_id,
                    lane.position_id,
                    lane.interview_session_id,
                    lane.competency_model_version_id,
                )
            )

    def state(self, subject):
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text(
                        "SELECT i.company_id,i.invitation_id,i.position_id,i.competency_model_version_id,"
                        "i.status,i.recruiting_stage_id,i.pipeline_row_version,s.name AS stage_name,"
                        "r.report_id,r.status AS report_status,r.overall_score,"
                        "(SELECT COUNT(*) FROM human_reviews h WHERE h.company_id=i.company_id "
                        "AND (h.target_id=i.invitation_id OR h.report_id=r.report_id)) AS reviews "
                        "FROM invitations i LEFT JOIN recruiting_stages s ON s.company_id=i.company_id "
                        "AND s.recruiting_stage_id=i.recruiting_stage_id LEFT JOIN reports r "
                        "ON r.company_id=i.company_id AND r.invitation_id=i.invitation_id "
                        "WHERE i.company_id=:company AND i.invitation_id=:invitation"
                    ),
                    {"company": subject.company_id, "invitation": subject.invitation_id},
                )
                .mappings()
                .one()
            )
        return json.loads(json.dumps(dict(row), default=str))

    def runtime(self):
        env = dict(os.environ)
        env.update(
            PYTHONPATH=str(self.settings.whyyou_repo_path / "backend/src"),
            CONTROLPROOF_H02_INSPECT_ENABLED="true",
            CONTROLPROOF_WORKER_SESSION_ID=str(uuid5(NAMESPACE, f"{self.run_id}:inspector")),
            CONTROLPROOF_WORKER_LAUNCHER_PID=str(os.getpid()),
            CONTROLPROOF_WORKER_SLOT="0",
        )
        process = subprocess.run(
            [
                env["CONTROLPROOF_WHYYOU_PYTHON"],
                "-m",
                "interview_evidence.runtime.controlproof_h02_binding",
            ],
            cwd=self.settings.whyyou_repo_path,
            env=env,
            text=True,
            capture_output=True,
            timeout=90,
            check=False,
        )
        if process.returncode:
            path = self.settings.observer_root / "h02-runtime-error.stderr"
            path.write_text(process.stderr, encoding="utf-8")
            raise RuntimeError("H02_RUNTIME_BINDING_UNAVAILABLE")
        return parse_helper_output(process.stdout)

    def reader(self, name, subject, lane):
        legacy = name.endswith("legacy")
        if legacy:
            # Synthetic old-data precondition, recorded separately from any observed result.
            # The valid report was already produced by the real validation/storage worker.
            with self.engine.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE invitations SET status='reviewed',recruiting_stage_id=NULL "
                        "WHERE company_id=:company AND invitation_id=:invitation"
                    ),
                    {"company": subject.company_id, "invitation": subject.invitation_id},
                )
        before = self.state(subject)
        route = (
            "/v1/assistant/search"
            if name.startswith("search")
            else (
                "/v1/assistant/answers/stream"
                if name.startswith("stream")
                else "/v1/assistant/answers"
            )
        )
        request_id = uuid5(NAMESPACE, f"{self.run_id}:{name}:request")
        self.resources.add(request_id)
        headers = self.http._credential_headers(
            H01Case.COMPANY_CONTROL, self.settings.whyyou_company_token
        )
        headers.update(
            {
                "X-Request-ID": str(request_id),
                "X-Trace-ID": f"controlproof:h02:{self.run_id}:{name}",
            }
        )
        response = self.http._send(
            "POST",
            route,
            headers=headers,
            body={
                "scope": "position",
                "position_id": str(lane.position_id),
                "query": "현재 채용 단계와 지원자 인원을 알려 주세요",
                "limit": 8,
            },
        )
        after = self.state(subject)
        return {
            "name": name,
            "subject": subject.model_dump(mode="json"),
            "synthetic_legacy_precondition": legacy,
            "route": route,
            "request_id": str(request_id),
            "response_status": response.status_code,
            "response_digest": sha256_bytes(response.content),
            "before": before,
            "after": after,
        }

    def human(self, name, subject, lane):
        before = self.state(subject)
        response = self.http.attempt(
            subject=subject,
            expected_version=before["pipeline_row_version"],
            credential=self.settings.whyyou_company_token,
        )
        after = self.state(subject)
        with self.engine.connect() as connection:
            events = (
                connection.execute(
                    text(
                        "SELECT outbox_event_id FROM outbox_events WHERE company_id=:company "
                        "AND aggregate_id=:session AND event_type='report.generation_requested'"
                    ),
                    {"company": subject.company_id, "session": lane.interview_session_id},
                )
                .scalars()
                .all()
            )
            audit = (
                connection.execute(
                    text(
                        "SELECT action,actor_type,actor_id,request_id FROM audit_events WHERE company_id=:company "
                        "AND request_id=:request"
                    ),
                    {"company": subject.company_id, "request": subject.request_id},
                )
                .mappings()
                .all()
            )
        receipts = []
        requests = {str(e) for e in events}
        for path in (self.settings.observer_root / "h02-model").glob("*.json"):
            item = json.loads(path.read_text(encoding="utf-8"))
            if item.get("request_id") in requests and item.get("company_id") == str(
                subject.company_id
            ):
                receipts.append(item)
        return {
            "name": name,
            "subject": subject.model_dump(mode="json"),
            "before": before,
            "after": after,
            "attempt": response,
            "model_event_ids": sorted(requests),
            "model_receipts": receipts,
            "decision_records": [r.model_dump(mode="json") for r in self.observe(subject).reviews],
            "audit": json.loads(json.dumps([dict(a) for a in audit], default=str)),
        }
