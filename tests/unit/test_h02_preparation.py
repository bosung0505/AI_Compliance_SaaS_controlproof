from copy import deepcopy

import pytest
import yaml
from pydantic import ValidationError

from engine.h02 import Inventory, PreparationError, load_preparation


@pytest.mark.parametrize(
    "change",
    [
        {"stage": 2},
        {"actual_status": "PASS"},
        {"schema": "other"},
        {"planned_assertions": []},
        {"planned_effects": ["READ_ONLY"]},
        {"extra": True},
    ],
)
def test_manifest_cannot_promote_or_drop_required_scope(tmp_path, change):
    original = load_preparation()
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.safe_dump({**original, **change}), encoding="utf-8")
    with pytest.raises(PreparationError, match="PREPARATION_MANIFEST_INVALID"):
        load_preparation(path)


def test_duplicate_manifest_key_is_invalid(tmp_path):
    data = load_preparation()
    path = tmp_path / "duplicate.yaml"
    path.write_text(yaml.safe_dump(data) + "\nstage: 1\n", encoding="utf-8")
    with pytest.raises(PreparationError):
        load_preparation(path)


def test_inventory_rejects_promoted_or_unbound_evidence():
    from engine.h02 import SourceFile, SourceRef, Surface, source_digest

    source = SourceFile(path="backend/src/interview_evidence/a.py", sha256="a" * 64)
    ref = SourceRef(**source.model_dump(), line=1, end_line=2)
    # A deliberately blocked miniature preparation is valid, never a product verdict.
    from engine.h02 import Issue

    inventory = Inventory(
        sources=(source,),
        source_tree_digest=source_digest((source,)),
        surfaces=(Surface(id="one", kind="DISPATCH_ANCHOR", name="a", target="a", refs=(ref,)),),
        issues=(Issue(code="MISSING_ANCHOR"),),
        import_closure=(source.path,),
    )
    data = inventory.model_dump(mode="json")
    for field, value in [
        ("actual_status", "PASS"),
        ("product_verdict", "PASS"),
        ("source_tree_digest", "b" * 64),
        ("import_closure", ["missing.py"]),
    ]:
        with pytest.raises(ValidationError):
            Inventory.model_validate({**data, field: value})
    for field, value in [
        ("review_status", "READ_ONLY"),
        ("refs", [{**ref.model_dump(), "sha256": "b" * 64}]),
    ]:
        changed = deepcopy(data)
        changed["surfaces"][0][field] = value
        with pytest.raises(ValidationError):
            Inventory.model_validate(changed)
    assert inventory.preparation_status == "BLOCKED"
