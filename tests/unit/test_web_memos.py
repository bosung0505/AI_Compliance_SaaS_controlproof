"""T036 — fix memos outside the sealed record (FR-024, R-008). RED until T039.

`.controlproof/web/memos/<run_id>.jsonl`, append only, `controlproof.fix-memo.v1`, author 1~80 characters, text 1~2000
characters, strict scan before write. Bundle files and the verify result never change.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from engine.evidence import verify_bundle
from engine.web import memos
from tests.fixtures import web_bundles as wb


def _tree(root):
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_add_and_list(tmp_path) -> None:
    store = memos.MemoStore(tmp_path / "memos")
    run_id = "00000000-0000-4000-8000-000000000001"
    memo = store.add(run_id, author=" 연우 ", text="리포트 조회가 제거된 근거를 확인 불가로 보이도록 수정 요청")
    assert memo["schema_version"] == "controlproof.fix-memo.v1"
    assert (memo["run_id"], memo["author"]) == (run_id, "연우")
    assert memo["memo_id"] and memo["created_at"]
    lines = (tmp_path / "memos" / f"{run_id}.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line) for line in lines] == [memo]
    assert store.list(run_id) == [memo]
    assert store.list("00000000-0000-4000-8000-000000000002") == []


def test_append_only(tmp_path) -> None:
    store = memos.MemoStore(tmp_path / "memos")
    run_id = "00000000-0000-4000-8000-000000000001"
    first = store.add(run_id, author="a", text="one")
    before = (tmp_path / "memos" / f"{run_id}.jsonl").read_text(encoding="utf-8")
    store.add(run_id, author="b", text="two")
    after = (tmp_path / "memos" / f"{run_id}.jsonl").read_text(encoding="utf-8")
    assert after.startswith(before)
    assert [item["text"] for item in store.list(run_id)] == ["one", "two"]
    assert store.list(run_id)[0] == first
    assert not any(hasattr(store, name) for name in ("update", "delete", "remove", "edit"))


@pytest.mark.parametrize(
    "author,text",
    [("", "x"), ("   ", "x"), ("a" * 81, "x"), ("a", ""), ("a", "   "), ("a", "x" * 2001)],
)
def test_lengths_are_enforced(tmp_path, author, text) -> None:
    store = memos.MemoStore(tmp_path / "memos")
    with pytest.raises(memos.MemoRejected):
        store.add("00000000-0000-4000-8000-000000000001", author=author, text=text)
    assert not (tmp_path / "memos").exists() or not any((tmp_path / "memos").iterdir())


def test_limits_are_inclusive(tmp_path) -> None:
    store = memos.MemoStore(tmp_path / "memos")
    memo = store.add("00000000-0000-4000-8000-000000000001", author="a" * 80, text="x" * 2000)
    assert len(memo["author"]) == 80 and len(memo["text"]) == 2000


@pytest.mark.parametrize(
    "text", ["see C:\\Users\\alice\\repo", "mail someone@example.com", "Bearer abcdefghijklmnop", "/home/bob/x"]
)
def test_strict_scan_runs_before_write(tmp_path, text) -> None:
    store = memos.MemoStore(tmp_path / "memos")
    with pytest.raises(memos.MemoRejected) as rejected:
        store.add("00000000-0000-4000-8000-000000000001", author="a", text=text)
    assert "alice" not in str(rejected.value) and "someone" not in str(rejected.value)
    assert not (tmp_path / "memos").exists() or not any((tmp_path / "memos").iterdir())


@pytest.mark.parametrize("run_id", ["../x", "not-a-uuid", "00000000-0000-4000-8000-000000000001/../a"])
def test_run_id_must_be_a_uuid(tmp_path, run_id) -> None:
    with pytest.raises(memos.MemoRejected):
        memos.MemoStore(tmp_path / "memos").add(run_id, author="a", text="x")


def test_bundle_and_verify_result_unchanged(tmp_path) -> None:
    root = tmp_path / "runs"
    built = wb.spec004_run(root, "E-01")
    before_tree = _tree(root)
    before = {key: value for key, value in verify_bundle(built.bundle).items() if key != "verified_at"}
    memos.MemoStore(tmp_path / "web" / "memos").add(built.run_id, author="a", text="수정 요청")
    assert _tree(root) == before_tree
    after = {key: value for key, value in verify_bundle(built.bundle).items() if key != "verified_at"}
    assert after == before
    assert not list(built.bundle.rglob("*memo*"))
