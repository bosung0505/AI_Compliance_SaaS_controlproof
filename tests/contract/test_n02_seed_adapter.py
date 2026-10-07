from __future__ import annotations

from uuid import UUID, uuid4

from engine.adapters.base import AdapterResult
from engine.adapters.whyyou.n02_seed import WhyYouN02SeedAdapter
from engine.models import BaselineKind, N02LaneId
from seeds.n02_subjects import build_n02_seed_plan


class _EmptyResult:
    """Real connections return rows; the FK catalog query has nothing to report here."""

    def mappings(self):
        return self

    def all(self):
        return []


class _Transaction:
    def __init__(self, *, fail_at: int | None = None) -> None:
        self.fail_at = fail_at
        self.calls = 0
        self.committed = False
        self.rolled_back = False
        self.deleted_run_ids: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, kind, _value, _traceback):
        self.committed = kind is None
        self.rolled_back = kind is not None
        return False

    def execute(self, statement, params=None):
        self.calls += 1
        if self.fail_at == self.calls:
            raise RuntimeError("synthetic seed failure")
        if params and "run_id" in params:
            self.deleted_run_ids.append(str(params["run_id"]))
        return _EmptyResult()


def test_seed_plan_has_stable_isolated_six_lane_contract() -> None:
    run_id = uuid4()
    first = build_n02_seed_plan(run_id, company_id=uuid4(), reviewer_id=uuid4())
    second = build_n02_seed_plan(
        run_id, company_id=first.company_id, reviewer_id=first.reviewer_id
    )
    assert first.digest == second.digest
    assert tuple(item.lane_id for item in first.lanes) == tuple(N02LaneId)
    assert len({item.invitation_id for item in first.lanes}) == 6
    assert len({item.applicant_id for item in first.lanes}) == 6
    assert all("@" not in item.subject_ref for item in first.lanes)
    assert all(
        item.baseline_kind is BaselineKind.PRISTINE
        for item in first.lanes
        if item.lane_id
        in {
            N02LaneId.PRISTINE_BASELINE,
            N02LaneId.DOCUMENT_BYPASS,
            N02LaneId.NORMAL_ORDER,
            N02LaneId.CONSENT_FAULT_RECOVERY,
        }
    )
    recording = first.by_lane(N02LaneId.RECORDING_BOUNDARY_PROBE)
    assessment = first.by_lane(N02LaneId.ASSESSMENT_BOUNDARY_PROBE)
    assert recording.allowed_preexisting_effects == {"equipment": 1, "strategy": 1}
    assert assessment.allowed_preexisting_effects == {
        "completed_session": 1,
        "final_turn": 1,
        "final_video": 1,
    }
    assert first.pristine_effect_counts() == {
        "consent": 0,
        "document": 0,
        "recording": 0,
        "assessment": 0,
    }


def test_seed_failure_rolls_back_the_whole_six_lane_transaction(settings) -> None:
    transaction = _Transaction(fail_at=4)
    adapter = WhyYouN02SeedAdapter(settings, transaction_factory=lambda: transaction)
    result = adapter.seed_lanes(run_id=str(uuid4()))
    assert result.ok is False
    assert result.code == "N02_SEED_WRITE_FAILED"
    assert transaction.rolled_back is True
    assert adapter.active_run_ids == ()


def test_teardown_is_allowlisted_to_the_current_run(settings) -> None:
    transaction = _Transaction()
    adapter = WhyYouN02SeedAdapter(settings, transaction_factory=lambda: transaction)
    run_id = uuid4()
    lanes = adapter.seed_lanes(run_id=str(run_id))
    assert isinstance(lanes, tuple) and len(lanes) == 6
    foreign = adapter.teardown_lanes(run_id=str(uuid4()), lanes=lanes)
    assert foreign.ok is False and foreign.code == "N02_SEED_NOT_OWNED"
    removed = adapter.teardown_lanes(run_id=str(run_id), lanes=lanes)
    assert removed.ok is True
    assert all(UUID(value) == run_id for value in transaction.deleted_run_ids)


def test_seeded_positions_and_invitations_satisfy_whyyou_submission_invariant() -> None:
    """T080/ID-003-09: parent 15cef078 consent POSTs returned 422 because the seed wrote
    ``submission_requirements=[]``. WhyYou loads every invitation through
    ``SubmissionRequirementSet``, which rejects a set with no required+enabled material, so
    the consent route failed before ``save_consent()`` and before the fault hook.
    """
    plan = build_n02_seed_plan(uuid4(), company_id=uuid4(), reviewer_id=uuid4())
    seeded = [row for row in plan.rows if row.table in {"positions", "invitations"}]
    assert {row.table for row in seeded} == {"positions", "invitations"}
    for row in seeded:
        requirements = row.values["submission_requirements"]
        assert isinstance(requirements, list) and requirements, row.table
        assert any(item["required"] and item["enabled"] for item in requirements), row.table
        material_types = [item["material_type"] for item in requirements]
        assert len(material_types) == len(set(material_types)), row.table


def test_seeded_criterion_verification_guide_satisfies_whyyou_model() -> None:
    """ID-003-15: T084 attempt 2 consented lanes got 403 on upload intents because WhyYou
    could not load the seeded competency model version: ``CriterionVerificationGuide``
    rejected ``{}`` and ``InterviewLevel`` rejected ``"standard"``. Submission authorization
    maps that ValueError to 403 and the report worker failed after
    ``REPORT_ASSESSMENT_STARTED``. Bounds and values mirror the target model.
    """
    plan = build_n02_seed_plan(uuid4(), company_id=uuid4(), reviewer_id=uuid4())
    positions = [row for row in plan.rows if row.table == "positions"]
    assert positions
    for row in positions:
        # WhyYou PositionStatus is draft|active|closed; "open" made every position read fail.
        assert row.values["status"] == "active"
    from seeds.n02_subjects import build_probe_overlay_rows

    for lane in plan.lanes:
        definition = plan.by_lane(lane.lane_id)
        for row in build_probe_overlay_rows(
            definition, plan.company_id, plan.competency_model_version_id, plan.criterion_id,
            include_assessment=True,
        ):
            if row.table == "interview_strategies":
                # WhyYou InterviewStrategy requires time_budget.total_seconds > 0.
                assert row.values["time_budget"].get("total_seconds", 0) > 0
    versions = [row for row in plan.rows if row.table == "competency_model_versions"]
    assert versions
    for row in versions:
        assert row.values["interview_level"] in {"entry", "junior", "senior"}
    criteria = [row for row in plan.rows if row.table == "evaluation_criteria"]
    assert criteria
    for row in criteria:
        guide = row.values["verification_guide"]
        for name, low, high in (
            ("observable_dimensions", 1, 12),
            ("strong_answer_signals", 1, 12),
            ("weak_answer_signals", 1, 12),
            ("follow_up_directions", 1, 8),
        ):
            values = guide.get(name)
            assert isinstance(values, list) and low <= len(values) <= high, name
            assert all(isinstance(item, str) and item.strip() for item in values), name
        assert isinstance(guide.get("max_follow_ups"), int) and 0 <= guide["max_follow_ups"] <= 3
        assert isinstance(guide.get("time_budget_seconds"), int)
        assert 60 <= guide["time_budget_seconds"] <= 1800


class _CatalogConnection:
    """Fake connection: answers the FK catalog query and child selects, records deletes."""

    def __init__(self, references, children):
        self.references, self.children, self.statements = references, children, []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql.split()[0], sql, dict(params or {})))
        if "pg_constraint" in sql:
            rows = self.references.get(params["parent"], [])
        elif sql.startswith("SELECT * FROM"):
            table = sql.split()[3].strip('"')
            rows = [row for row in self.children.get(table, []) if params["k0"] in row.values()]
        else:
            rows = []

        class _Result:
            def mappings(self_inner):
                return self_inner

            def all(self_inner):
                return rows

        return _Result()


def test_teardown_removes_target_rows_that_reference_this_runs_seed_first() -> None:
    """ID-003-12: after consent commits, invitation_state_history references the seeded
    invitation (NO ACTION FK), so deleting the seed alone failed and every complete Run would
    end RESTORE_FAILED. Dependents reachable from this Run's seed rows go first; a foreign key
    whose referenced columns are not in the seed row is skipped."""
    from engine.adapters.whyyou.n02_seed import _delete_dependents

    company, invitation = uuid4(), uuid4()
    connection = _CatalogConnection(
        references={
            "invitations": [
                {"child_table": "invitation_state_history",
                 "child_columns": ["invitation_id", "company_id"],
                 "parent_columns": ["invitation_id", "company_id"]},
                {"child_table": "unrelated", "child_columns": ["x"], "parent_columns": ["not_seeded"]},
            ],
        },
        children={"invitation_state_history": [{"invitation_id": invitation, "company_id": company}]},
    )
    _delete_dependents(
        connection, "invitations", {"invitation_id": invitation, "company_id": company}
    )

    deletes = [sql for verb, sql, _ in connection.statements if verb == "DELETE"]
    assert deletes == [
        'DELETE FROM "invitation_state_history" WHERE "invitation_id" = :k0 AND "company_id" = :k1'
    ]
    assert not any('"unrelated"' in sql for _, sql, _ in connection.statements)


class _RecordingTransaction(_Transaction):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[tuple[str, dict]] = []

    def execute(self, statement, params=None):
        text = str(statement)
        if text.lstrip().upper().startswith("INSERT INTO"):
            self.rows.append((text.split()[2], dict(params or {})))
        return super().execute(statement, params)


def test_processing_prerequisites_fit_the_consented_product_flow(settings) -> None:
    """ID-003-18: recording needs only a ready strategy (the equipment check is real), the
    assessment attaches turns to the one real session, probe lanes get nothing."""
    transaction = _RecordingTransaction()
    adapter = WhyYouN02SeedAdapter(settings, transaction_factory=lambda: transaction)
    run_id = uuid4()
    lanes = adapter.seed_lanes(run_id=str(run_id))
    assert not isinstance(lanes, AdapterResult)
    subject = adapter.subject_for(run_id=str(run_id), lane_id=N02LaneId.NORMAL_ORDER)
    transaction.rows.clear()

    recording = adapter.apply_processing_prerequisites(subject=subject, path_id="RECORDING")
    assert recording.ok and [table for table, _ in transaction.rows] == ["interview_strategies"]
    assert recording.data["fixture_effect_ids"] == (f"strategy:{subject['strategy_id']}",)

    session_id = str(uuid4())
    transaction.rows.clear()
    assessment = adapter.apply_processing_prerequisites(
        subject=subject, path_id="AI_ASSESSMENT", interview_session_id=session_id
    )
    assert assessment.ok
    tables = sorted(table for table, _ in transaction.rows)
    assert tables == ["interview_turns", "recording_assets", "transcript_segments"]
    assert all(str(values["interview_session_id"]) == session_id for _, values in transaction.rows)
    assert any(item.startswith("asset:") for item in assessment.data["fixture_effect_ids"])

    assert adapter.apply_processing_prerequisites(
        subject=subject, path_id="AI_ASSESSMENT", interview_session_id=session_id
    ).code == (
        "N02_PREREQUISITES_ALREADY_APPLIED"
    )
    probe = adapter.subject_for(run_id=str(run_id), lane_id=N02LaneId.RECORDING_BOUNDARY_PROBE)
    assert adapter.apply_processing_prerequisites(subject=probe, path_id="RECORDING").code == (
        "N02_PREREQUISITE_LANE_MISMATCH"
    )
    assert adapter.apply_processing_prerequisites(
        subject=subject, path_id="DOCUMENT_ANALYSIS"
    ).code == "N02_PREREQUISITES_NOT_REQUIRED"


class _TargetSessionTransaction(_RecordingTransaction):
    """The target already holds a session for the invitation (it accepted an unconsented
    recording request); the FK catalog and other reads stay empty."""

    def __init__(self, session_id) -> None:
        super().__init__()
        self.session_id = session_id

    def execute(self, statement, params=None):
        if "FROM interview_sessions" in str(statement):
            session_id = self.session_id

            class _Rows:
                def mappings(self):
                    return self

                def all(self):
                    return [{"interview_session_id": session_id}]

            return _Rows()
        return super().execute(statement, params)


def test_assessment_overlay_attaches_to_a_session_the_target_already_created(settings) -> None:
    """ID-003-18: when the target accepted an unconsented session, the fault-lane assessment
    fixture attaches its turns to that session instead of aborting the Run on a conflict."""
    leaked = uuid4()
    transaction = _TargetSessionTransaction(leaked)
    adapter = WhyYouN02SeedAdapter(settings, transaction_factory=lambda: transaction)
    run_id = uuid4()
    assert not isinstance(adapter.seed_lanes(run_id=str(run_id)), AdapterResult)
    subject = adapter.subject_for(run_id=str(run_id), lane_id=N02LaneId.CONSENT_FAULT_RECOVERY)
    transaction.rows.clear()
    result = adapter.apply_probe_overlay(subject=subject, path_id="AI_ASSESSMENT")
    assert result.ok and result.code == "N02_PROBE_OVERLAY_APPLIED_ON_TARGET_SESSION"
    assert result.data["interview_session_id"] == str(leaked)
    tables = [table for table, _ in transaction.rows]
    assert "interview_sessions" not in tables and "interview_turns" in tables
    assert all(
        str(values["interview_session_id"]) == str(leaked)
        for table, values in transaction.rows
        if "interview_session_id" in values
    )
