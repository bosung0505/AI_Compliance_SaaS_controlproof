import json
from uuid import uuid4

from engine.adapters.whyyou.h02_live import h02_cases
from engine.adapters.whyyou.h02_review import review_record, reviews
from engine.h02 import Inventory, SourceFile, SourceRef, Surface, source_digest
from engine.models import canonical_json_bytes, sha256_bytes
from tests.unit.test_h01_actual import SETTINGS


def test_review_is_bound_to_source_bytes_surface_and_explicit_disposition(tmp_path, monkeypatch):
    source = SourceFile(path="backend/src/interview_evidence/reader.py", sha256="a" * 64)
    surface = Surface(
        id="DISPATCH_ANCHOR:main",
        kind="DISPATCH_ANCHOR",
        name="main",
        target="reader.main",
        refs=(SourceRef(**source.model_dump(), line=1, end_line=2),),
    )
    inventory = Inventory(
        sources=(source,),
        source_tree_digest=source_digest((source,)),
        surfaces=(surface,),
        issues=(),
        import_closure=(source.path,),
    )
    record = {
        "mode": "read-only-pipeline-reader",
        "effects": {surface.id: "READ_ONLY"},
        "surface_digest": sha256_bytes(canonical_json_bytes([surface.model_dump(mode="json")])),
        "review_basis": [source.model_dump()],
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps({inventory.source_tree_digest: record}), encoding="utf-8")
    monkeypatch.setattr("engine.adapters.whyyou.h02_review.REVIEWED_TREES_FILE", path)
    assert review_record(inventory) == record
    assert reviews(inventory, {})[0]["effect"] == "READ_ONLY"
    changed = inventory.model_copy(
        update={"surfaces": (surface.model_copy(update={"calls": ("hiring.move_applicants",)}),)}
    )
    assert review_record(changed) is None
    assert reviews(changed, {})[0]["effect"] == "UNKNOWN"
    record["effects"] = {}
    path.write_text(json.dumps({inventory.source_tree_digest: record}), encoding="utf-8")
    assert review_record(inventory) is None


def test_same_position_criteria_and_separate_owned_sessions_are_required_for_rank_control():
    cases = h02_cases(uuid4(), SETTINGS)
    low, high = cases[0][2], cases[1][2]
    assert low.position_id == high.position_id
    assert low.competency_model_version_id == high.competency_model_version_id
    assert low.criteria[0].criterion_id == high.criteria[0].criterion_id
    assert len({c[1].invitation_id for c in cases}) == 6
    assert len({c[2].interview_session_id for c in cases}) == 6
    assert low.applicant_id != high.applicant_id
