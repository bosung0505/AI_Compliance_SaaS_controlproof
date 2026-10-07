"""T030 — Spec 004 seed plan and WhyYou seed adapter contract.

RED until T035 (`seeds/spec004_subjects.py`) and T036 (`engine/adapters/whyyou/spec004_seed.py`).
WhyYou groups an applicant answer under a criterion only when an interviewer question turn precedes it
(`runtime/worker.py` `_criterion_answers_by_criterion`), so every criterion gets a question and an answer turn.
"""

from __future__ import annotations

from importlib import import_module
from uuid import UUID, uuid4

from engine.models import CitationMode, CriteriaVersionSnapshot, E01LaneId, E02LaneId, VersionSource
from tests.fixtures import spec004 as fx

COMPANY = UUID("00000000-0000-7000-8000-000000000001")
REVIEWER = UUID("00000000-0000-7000-8000-000000000002")
FORBIDDEN_TABLES = {"consent_records", "reports", "report_items", "evidence", "outbox_events"}


def seeds():
    return import_module("seeds.spec004_subjects")


def adapter_module():
    return import_module("engine.adapters.whyyou.spec004_seed")


class _Result:
    def __init__(self, rows=()):
        self._rows = list(rows)

    def mappings(self):
        return self

    def all(self):
        return self._rows


class _Transaction:
    def __init__(self, *, fail_at: int | None = None) -> None:
        self.fail_at = fail_at
        self.statements: list[tuple[str, dict]] = []
        self.committed = False
        self.rolled_back = False

    def __enter__(self):
        return self

    def __exit__(self, kind, _value, _traceback):
        self.committed = kind is None
        self.rolled_back = kind is not None
        return False

    def execute(self, statement, params=None):
        self.statements.append((str(statement), dict(params or {})))
        if self.fail_at == len(self.statements):
            raise RuntimeError("synthetic seed failure")
        return _Result()


def _rows(lane):
    return seeds().lane_rows(lane, company_id=COMPANY, reviewer_id=REVIEWER)


def test_e01_lanes_are_deterministic_and_isolated() -> None:
    run_id = uuid4()
    first, second = seeds().e01_lanes(run_id), seeds().e01_lanes(run_id)
    assert first == second
    assert tuple(lane.lane_id for lane in first) == (
        E01LaneId.E01_REFERENCE,
        E01LaneId.E01_EVIDENCE_REMOVAL,
        E01LaneId.E01_STORAGE_PROBE,
    )
    assert len({lane.invitation_id for lane in first}) == 3
    assert len({lane.position_id for lane in first}) == 3
    assert all(lane.version_source is VersionSource.RUN_SEED for lane in first)
    removal = first[1]
    assert [item.code for item in removal.criteria] == ["E01-REM-1-VALID", "E01-REM-2-VALID"]


def test_matrix_lane_needs_the_reference_evidence_and_an_absent_uuid() -> None:
    run_id = uuid4()
    reference = fx.uuid7_at(fx.FIXED_AT, 5)
    lane = seeds().e01_matrix_lane(run_id, reference)
    codes = [item.code for item in lane.criteria]
    assert codes == sorted(codes) == list(fx.MATRIX_CODES.values())
    by_mode = {item.citation_mode: item for item in lane.criteria}
    assert by_mode[CitationMode.OTHER_APPLICANT].mode_argument == str(reference)
    assert by_mode[CitationMode.NONEXISTENT].mode_argument == str(
        seeds().nonexistent_evidence_id(run_id)
    )
    assert by_mode[CitationMode.OTHER_CRITERION].mode_argument == str(
        by_mode[CitationMode.VALID].criterion_id
    )


def test_lane_rows_seed_question_answer_segment_and_video_but_no_consent_or_report() -> None:
    lane = seeds().e01_lanes(uuid4())[1]
    rows = _rows(lane)
    tables = [row.table for row in rows]
    assert not FORBIDDEN_TABLES & set(tables)
    for table in (
        "positions",
        "competency_model_versions",
        "evaluation_criteria",
        "invitations",
        "applicant_profiles",
        "applicant_access_sessions",
        "interview_sessions",
        "recording_assets",
    ):
        assert table in tables
    turns = [row.values for row in rows if row.table == "interview_turns"]
    segments = [row.values for row in rows if row.table == "transcript_segments"]
    assert len(turns) == 2 * len(lane.criteria) and len(segments) == len(lane.criteria)
    ordered = sorted(turns, key=lambda value: value["sequence"])
    for index, criterion in enumerate(lane.criteria):
        question, answer = ordered[2 * index], ordered[2 * index + 1]
        assert (question["speaker"], answer["speaker"]) == ("interviewer", "applicant")
        assert question["turn_id"] == criterion.question_turn_id
        assert answer["turn_id"] == criterion.answer_turn_id
        assert question["target_criterion_id"] == criterion.criterion_id
        segment = next(
            value
            for value in segments
            if value["transcript_segment_id"] == criterion.transcript_segment_id
        )
        assert segment["turn_id"] == criterion.answer_turn_id
        assert segment["session_end_ms"] > segment["session_start_ms"]
    criteria = {
        row.values["criterion_id"]: row.values for row in rows if row.table == "evaluation_criteria"
    }
    for criterion in lane.criteria:
        assert criteria[criterion.criterion_id]["description"].startswith(criterion.marker)
        assert criteria[criterion.criterion_id]["code"] == criterion.code
    assets = [row.values for row in rows if row.table == "recording_assets"]
    assert assets[0]["asset_type"] == "final_video" and assets[0]["missing_ranges"] == []
    emails = [
        row.values["applicant_email_normalized"] for row in rows if row.table == "invitations"
    ]
    assert all(value.endswith("@example.invalid") for value in emails)


def test_e02_lane_binds_to_the_product_version_and_skips_version_rows() -> None:
    run_id = uuid4()
    position_id = seeds().e02_position_id(run_id)
    version = CriteriaVersionSnapshot.model_validate(
        fx.criteria_version("v2", position_id=str(position_id))
    )
    lane = seeds().e02_lane(run_id, E02LaneId.E02_SECOND_APPLICANT, version)
    assert lane.version_source is VersionSource.PRODUCT_API_LATEST_PUBLISHED
    assert lane.competency_model_version_id == version.competency_model_version_id
    assert [item.criterion_id for item in lane.criteria] == [
        item.criterion_id for item in version.criteria
    ]
    assert [item.fixture_score for item in lane.criteria] == [72, 74]
    tables = {row.table for row in _rows(lane)}
    assert not {"positions", "competency_model_versions", "evaluation_criteria"} & tables
    sessions = [row.values for row in _rows(lane) if row.table == "interview_sessions"]
    assert sessions[0]["competency_model_version_id"] == version.competency_model_version_id


def test_e02_version_bodies_carry_markers_scores_and_valid_totals() -> None:
    for key, expected in (("v1", [(72, 50.0), (73, 50.0)]), ("v2", [(72, 25.0), (74, 75.0)])):
        body = seeds().e02_version_body(key)
        assert [
            (item["description"].split("score=")[1].split("]")[0], item["weight"])
            for item in body["criteria"]
        ] == [(str(score), weight) for score, weight in expected]
        assert sum(item["weight"] for item in body["criteria"]) == 100
        assert body["interview_duration_minutes"] == 30
        assert len(body["job_requirements"]) >= 1
        axis = body["axis_weights"]
        assert set(axis) == set(fx.AXES) and sum(axis.values()) == 100


def test_seed_adapter_writes_one_transaction_and_keeps_credentials(settings) -> None:
    lanes = seeds().e01_lanes(uuid4())
    transaction = _Transaction()
    adapter = adapter_module().WhyYouSpec004SeedAdapter(
        settings, transaction_factory=lambda: transaction
    )
    result = adapter.seed_lanes(run_id=str(lanes[0].run_id), lanes=lanes)
    assert result.ok and transaction.committed
    inserts = [sql for sql, _ in transaction.statements if sql.startswith("INSERT")]
    assert len(inserts) == sum(len(_rows(lane)) for lane in lanes)
    assert all(adapter.credentials.get(lane.subject_ref) for lane in lanes)


def test_seed_adapter_rolls_back_the_whole_seed_on_failure(settings) -> None:
    lanes = seeds().e01_lanes(uuid4())
    transaction = _Transaction(fail_at=3)
    adapter = adapter_module().WhyYouSpec004SeedAdapter(
        settings, transaction_factory=lambda: transaction
    )
    result = adapter.seed_lanes(run_id=str(lanes[0].run_id), lanes=lanes)
    assert not result.ok and result.code == "SPEC004_SEED_WRITE_FAILED"
    assert transaction.rolled_back
    assert all(adapter.credentials.get(lane.subject_ref) is None for lane in lanes)


def test_teardown_removes_only_this_runs_rows_and_credentials(settings) -> None:
    lanes = seeds().e01_lanes(uuid4())
    transactions = []

    def factory():
        transactions.append(_Transaction())
        return transactions[-1]

    adapter = adapter_module().WhyYouSpec004SeedAdapter(settings, transaction_factory=factory)
    assert adapter.seed_lanes(run_id=str(lanes[0].run_id), lanes=lanes).ok
    other = seeds().e01_lanes(uuid4())
    refused = adapter.teardown(run_id=str(other[0].run_id), lanes=other, position_ids=())
    assert not refused.ok and refused.code == "SPEC004_SEED_NOT_OWNED"
    removed = adapter.teardown(run_id=str(lanes[0].run_id), lanes=lanes, position_ids=())
    assert removed.ok
    deletes = [sql for sql, _ in transactions[-1].statements if sql.startswith("DELETE")]
    assert len(deletes) == sum(len(_rows(lane)) for lane in lanes)
    assert all(adapter.credentials.get(lane.subject_ref) is None for lane in lanes)
