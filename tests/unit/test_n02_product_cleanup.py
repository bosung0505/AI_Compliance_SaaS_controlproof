from uuid import uuid4

import pytest

from seeds.n02_subjects import build_n02_seed_plan


def test_cleanup_refuses_mixed_run_lanes_before_any_sql():
    from engine.adapters.whyyou.n02_cleanup import delete_product_rows

    plan = build_n02_seed_plan(uuid4(), company_id=uuid4(), reviewer_id=uuid4())
    foreign = plan.lanes[0].model_copy(update={"run_id": uuid4()})
    with pytest.raises(ValueError, match="owned"):
        delete_product_rows(object(), company_id=plan.company_id, lanes=(foreign, *plan.lanes[1:]))


def test_cleanup_queries_always_scope_company_and_owned_subjects(monkeypatch):
    from engine.adapters.whyyou import n02_cleanup

    plan = build_n02_seed_plan(uuid4(), company_id=uuid4(), reviewer_id=uuid4())
    calls = []

    class Result:
        def mappings(self):
            return self

        def all(self):
            return []

    class Connection:
        def execute(self, statement, params):
            calls.append((str(statement), params))
            return Result()

    assert (
        n02_cleanup.delete_product_rows(Connection(), company_id=plan.company_id, lanes=plan.lanes)
        == 0
    )
    assert calls
    owned = {lane.invitation_id for lane in plan.lanes} | {lane.applicant_id for lane in plan.lanes}
    for sql, params in calls:
        assert params.get("company_id") == plan.company_id
        assert "WHERE" in sql and "company_id" in sql
        if "subject_id" in params:
            assert params["subject_id"] in owned
        if "trace" in params:
            assert params["trace"] == f"controlproof:{plan.run_id}:%"
