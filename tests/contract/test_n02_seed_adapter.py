from __future__ import annotations

from uuid import UUID, uuid4

from engine.adapters.whyyou.n02_seed import WhyYouN02SeedAdapter
from engine.models import BaselineKind, N02LaneId
from seeds.n02_subjects import build_n02_seed_plan


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
