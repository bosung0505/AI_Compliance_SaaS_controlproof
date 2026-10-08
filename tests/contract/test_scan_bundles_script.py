"""T005 — `scripts/scan_bundles.py` reads bundles only and reports counts, never values (FR-036, R-012). RED until T012."""

from __future__ import annotations

import hashlib
import json

from scripts import scan_bundles
from tests.fixtures import web_bundles as wb


def _digest_tree(root):
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_report_counts_v1_and_v2_per_rule_without_values(tmp_path) -> None:
    root = tmp_path / "runs"
    clean = wb.spec004_run(root, "E-02")
    leaky = root / "00000000-0000-4000-8000-0000000000aa"
    leaky.mkdir(parents=True)
    (leaky / "manifest.json").write_text(json.dumps({"run_id": leaky.name}), encoding="utf-8")
    (leaky / "notes.json").write_text(json.dumps({"p": "C:\\Users\\alice\\x"}), encoding="utf-8")
    before = _digest_tree(root)
    out = tmp_path / "report.json"

    assert scan_bundles.main(["--run-root", str(root), "--label", "local", "--out", str(out)]) == 0

    assert _digest_tree(root) == before
    report = json.loads(out.read_text(encoding="utf-8"))
    text = out.read_text(encoding="utf-8")
    assert report["schema_version"] == "controlproof.scan-report.v1"
    assert report["summary"]["bundle_count"] == 2
    assert report["summary"]["v1"].get("user_path", 0) == 0
    assert report["summary"]["v2"]["user_path"] == 1
    assert report["summary"]["newly_flagged_bundles"] == 1
    bundles = {item["run_id"]: item for item in report["roots"][0]["bundles"]}
    assert bundles[leaky.name]["files"] == [
        {"path": "notes.json", "v1": {}, "v2": {"user_path": 1}}
    ]
    assert bundles[clean.run_id]["newly_flagged"] is False
    assert report["roots"][0]["label"] == "local"
    for forbidden in ("alice", str(tmp_path), str(tmp_path).replace("\\", "\\\\")):
        assert forbidden not in text


def test_multiple_roots_and_missing_root(tmp_path) -> None:
    a = tmp_path / "a"
    wb.h03_case(a, "pass")
    out = tmp_path / "r.json"
    code = scan_bundles.main(
        ["--run-root", str(a), "--run-root", str(tmp_path / "absent"), "--out", str(out)]
    )
    assert code == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert [root["label"] for root in report["roots"]] == ["root-1", "root-2"]
    assert report["roots"][1]["status"] == "MISSING"
    assert report["summary"]["bundle_count"] == 1
