from pathlib import Path

import pytest

from engine.adapters.whyyou.client import TargetSnapshotCaptureError, _migration_head


def _revision(root: Path, filename: str, revision: str, down_revision: str | None) -> None:
    versions = root / "backend" / "alembic" / "versions"
    versions.mkdir(parents=True, exist_ok=True)
    (versions / filename).write_text(
        f"revision: str = {revision!r}\ndown_revision: str | None = {down_revision!r}\n",
        encoding="utf-8",
    )


def test_migration_head_uses_graph_not_lexicographic_filename_order(tmp_path: Path) -> None:
    _revision(tmp_path, "z_ancestor.py", "ancestor", None)
    _revision(tmp_path, "a_actual_head.py", "actual_head", "ancestor")

    assert _migration_head(tmp_path) == "actual_head"


def test_migration_head_rejects_an_unmerged_graph(tmp_path: Path) -> None:
    _revision(tmp_path, "a.py", "head_a", None)
    _revision(tmp_path, "b.py", "head_b", None)

    with pytest.raises(TargetSnapshotCaptureError, match="exactly one head"):
        _migration_head(tmp_path)
