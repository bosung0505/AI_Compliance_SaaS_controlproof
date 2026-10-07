"""T044 — evidence mutation adapter contract (contracts/whyyou-spec004-adapter.md "EvidenceMutationAdapter").

RED until T047 creates `engine/adapters/whyyou/evidence_mutation.py`. A small in-memory SQL double stands in for
WhyYou; the adapter writes on one connection and confirms absence/restoration on a separate one.
"""

from __future__ import annotations

import copy
from importlib import import_module
from uuid import UUID, uuid4

from engine.adapters.base import AdapterResult
from engine.models import ChangeInjection, ChangeInjectionState, E01LaneId
from seeds.spec004_subjects import e01_lanes

COMPANY = UUID("00000000-0000-7000-8000-000000000001")
FOREIGN_SEGMENT = UUID("00000000-0000-7000-8000-0000000000f1")
FOREIGN_ITEM = UUID("00000000-0000-7000-8000-0000000000f2")


class _Result:
    def __init__(self, rows=(), rowcount=0):
        self._rows = [dict(row) for row in rows]
        self.rowcount = rowcount

    def mappings(self):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class _Database:
    def __init__(self, lane, *, shared=False, corrupt_reinsert=False):
        self.segments = {}
        self.items = {}
        self.shared = shared
        self.corrupt_reinsert = corrupt_reinsert
        self.statements: list[tuple[str, str]] = []
        for criterion in lane.criteria:
            self.segments[criterion.transcript_segment_id] = {
                "company_id": COMPANY,
                "transcript_segment_id": criterion.transcript_segment_id,
                "interview_session_id": lane.interview_session_id,
                "turn_id": criterion.answer_turn_id,
                "speaker": "applicant",
                "text": "synthetic answer",
                "version": 1,
            }
        self.segments[FOREIGN_SEGMENT] = {
            "company_id": COMPANY,
            "transcript_segment_id": FOREIGN_SEGMENT,
            "interview_session_id": uuid4(),
            "turn_id": uuid4(),
            "speaker": "applicant",
            "text": "other lane",
            "version": 1,
        }
        self.item_id = uuid4()
        self.items[self.item_id] = {
            "company_id": COMPANY,
            "session": lane.interview_session_id,
            "axis_assessments": [{"axis": "correctness", "score": None, "quoted_evidence_ids": []}],
            "rationale": "kept",
        }
        self.items[FOREIGN_ITEM] = {
            "company_id": COMPANY,
            "session": uuid4(),
            "axis_assessments": [{"axis": "depth", "score": 70, "quoted_evidence_ids": []}],
            "rationale": "foreign",
        }

    def connection(self, name):
        return _Connection(self, name)


class _Connection:
    def __init__(self, database, name):
        self.db = database
        self.name = name

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, statement, params=None):
        sql = " ".join(str(statement).split())
        params = dict(params or {})
        self.db.statements.append((self.name, sql))
        db = self.db
        if sql.startswith("SELECT * FROM transcript_segments"):
            row = db.segments.get(UUID(str(params["transcript_segment_id"])))
            if row is None or (
                "session_id" in params
                and row["interview_session_id"] != UUID(str(params["session_id"]))
            ):
                return _Result()
            return _Result([row])
        if sql.startswith("SELECT count(*) AS shared FROM evidence"):
            return _Result([{"shared": 1 if db.shared else 0}])
        if sql.startswith("DELETE FROM transcript_segments"):
            removed = db.segments.pop(UUID(str(params["transcript_segment_id"])), None)
            return _Result(rowcount=1 if removed else 0)
        if sql.startswith("INSERT INTO transcript_segments"):
            row = {key: value for key, value in params.items()}
            row["transcript_segment_id"] = UUID(str(row["transcript_segment_id"]))
            if db.corrupt_reinsert:
                row["text"] = "different"
            db.segments[row["transcript_segment_id"]] = row
            return _Result(rowcount=1)
        if sql.startswith("SELECT ri.company_id, ri.axis_assessments FROM report_items"):
            item = db.items.get(UUID(str(params["report_item_id"])))
            if item is None or (
                "session_id" in params and item["session"] != UUID(str(params["session_id"]))
            ):
                return _Result()
            return _Result(
                [{"company_id": item["company_id"], "axis_assessments": item["axis_assessments"]}]
            )
        if sql.startswith("UPDATE report_items SET axis_assessments"):
            import json

            item = db.items[UUID(str(params["report_item_id"]))]
            item["axis_assessments"] = json.loads(params["axes"])
            return _Result(rowcount=1)
        raise AssertionError(f"unexpected statement: {sql}")


def _adapter(settings, database):
    module = import_module("engine.adapters.whyyou.evidence_mutation")
    return module.WhyYouEvidenceMutationAdapter(
        settings,
        transaction_factory=lambda: database.connection("write"),
        verify_factory=lambda: database.connection("verify"),
    )


def _lane():
    return next(lane for lane in e01_lanes(uuid4()) if lane.lane_id is E01LaneId.E01_EVIDENCE_REMOVAL)


def test_segment_outside_the_lane_is_refused(settings) -> None:
    lane = _lane()
    database = _Database(lane)
    result = _adapter(settings, database).remove_segment(
        lane=lane, transcript_segment_id=str(FOREIGN_SEGMENT), injection_id=str(uuid4())
    )
    assert isinstance(result, AdapterResult) and result.code == "SEGMENT_NOT_OWNED_BY_LANE"
    assert FOREIGN_SEGMENT in database.segments
    assert not any(sql.startswith("DELETE") for _, sql in database.statements)


def test_segment_cited_by_another_lane_is_refused(settings) -> None:
    lane = _lane()
    database = _Database(lane, shared=True)
    segment = lane.criteria[0].transcript_segment_id
    result = _adapter(settings, database).remove_segment(
        lane=lane, transcript_segment_id=str(segment), injection_id=str(uuid4())
    )
    assert isinstance(result, AdapterResult) and result.code == "SEGMENT_SHARED_ACROSS_LANES"
    assert segment in database.segments


def test_remove_deletes_one_row_and_confirms_absence_separately(settings) -> None:
    lane = _lane()
    database = _Database(lane)
    segment = lane.criteria[0].transcript_segment_id
    before = copy.deepcopy(database.segments)
    injection = _adapter(settings, database).remove_segment(
        lane=lane, transcript_segment_id=str(segment), injection_id=str(uuid4())
    )
    assert isinstance(injection, ChangeInjection)
    assert injection.state is ChangeInjectionState.APPLIED
    assert injection.apply_receipt == {"affected_rows": 1, "absence_confirmed": True}
    assert segment not in database.segments
    assert {key: value for key, value in before.items() if key != segment} == database.segments
    verify = [sql for name, sql in database.statements if name == "verify"]
    assert verify and verify[-1].startswith("SELECT * FROM transcript_segments")


def test_restore_reinserts_the_same_row(settings) -> None:
    lane = _lane()
    database = _Database(lane)
    segment = lane.criteria[0].transcript_segment_id
    original = copy.deepcopy(database.segments[segment])
    adapter = _adapter(settings, database)
    injection = adapter.remove_segment(
        lane=lane, transcript_segment_id=str(segment), injection_id=str(uuid4())
    )
    restored = adapter.restore_segment(injection=injection)
    assert restored.state is ChangeInjectionState.RESTORED
    assert restored.post_restore_digest == injection.pre_projection_digest
    assert database.segments[segment] == original
    assert adapter.target_safe(injections=(restored.model_dump(mode="json"),))


def test_restore_digest_mismatch_is_restore_failed(settings) -> None:
    lane = _lane()
    database = _Database(lane, corrupt_reinsert=True)
    segment = lane.criteria[0].transcript_segment_id
    adapter = _adapter(settings, database)
    injection = adapter.remove_segment(
        lane=lane, transcript_segment_id=str(segment), injection_id=str(uuid4())
    )
    restored = adapter.restore_segment(injection=injection)
    assert restored.state is ChangeInjectionState.RESTORE_FAILED
    assert restored.failure_code == "RESTORE_DIGEST_MISMATCH"
    assert not adapter.target_safe(injections=(restored.model_dump(mode="json"),))


def test_probe_rewrites_only_the_owned_item_axes(settings) -> None:
    lane = next(lane for lane in e01_lanes(uuid4()) if lane.lane_id is E01LaneId.E01_STORAGE_PROBE)
    database = _Database(lane)
    original = copy.deepcopy(database.items)
    adapter = _adapter(settings, database)
    axes = [{"axis": "correctness", "score": 80, "quoted_evidence_ids": []}]
    refused = adapter.write_probe_axes(
        lane=lane, report_item_id=str(FOREIGN_ITEM), axes=axes, injection_id=str(uuid4())
    )
    assert isinstance(refused, AdapterResult) and refused.code == "REPORT_ITEM_NOT_OWNED_BY_LANE"
    injection = adapter.write_probe_axes(
        lane=lane, report_item_id=str(database.item_id), axes=axes, injection_id=str(uuid4())
    )
    assert injection.state is ChangeInjectionState.APPLIED
    assert database.items[database.item_id]["axis_assessments"] == axes
    assert database.items[database.item_id]["rationale"] == "kept"
    assert database.items[FOREIGN_ITEM] == original[FOREIGN_ITEM]
    restored = adapter.restore_probe_axes(injection=injection)
    assert restored.state is ChangeInjectionState.RESTORED
    assert database.items == original
    assert adapter.target_safe(injections=(restored.model_dump(mode="json"),))
