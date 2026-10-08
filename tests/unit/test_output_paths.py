"""T004 — output-boundary path policy and the hardened user-path pattern (FR-031, FR-035, SC-007, R-009).

RED until T009/T010. v1 sealing/verify (`USER_PATH_RE`, `assert_redacted`) stays unchanged until T020 (ID-005-02); the
hardened pattern is `USER_PATH_RE_V2`, used by the output boundary and the v2 scanner.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine import cli, evidence

HOME_WIN = "C:\\Users\\alice\\Desktop\\runs\\abc"


@pytest.mark.parametrize(
    "text",
    [
        json.dumps({"p": HOME_WIN}),              # JSON-escaped: C:\\Users\\alice\\...
        HOME_WIN,                                  # single separators
        "C:/Users/alice/runs/abc",
        "/home/alice/runs/abc",
        "/Users/alice/runs/abc",
    ],
)
def test_v2_pattern_catches_user_paths(text) -> None:
    assert evidence.USER_PATH_RE_V2.search(text)


def test_v1_pattern_is_unchanged_until_t020() -> None:
    assert evidence.USER_PATH_RE.search(HOME_WIN)
    assert not evidence.USER_PATH_RE.search(json.dumps({"p": HOME_WIN}))


def test_paths_inside_the_run_root_become_run_root_relative(tmp_path) -> None:
    root = tmp_path / "runs"
    inside = root / "abc" / "run.json"
    shown = evidence.display_paths({"bundle": str(inside), "nested": [f"see {inside}"]}, run_root=root)
    assert shown["bundle"] == "<run_root>/abc/run.json"
    assert shown["nested"] == ["see <run_root>/abc/run.json"]
    assert str(tmp_path) not in json.dumps(shown)


@pytest.mark.parametrize(
    "value",
    ["D:\\runs\\abc", "C:\\Users\\alice\\x", "/var/runs/abc", "/home/alice/x", "/tmp/cp/runs/abc"],
)
def test_other_absolute_paths_become_placeholder(value, tmp_path) -> None:
    shown = evidence.display_paths({"p": value}, run_root=tmp_path / "runs")
    assert shown["p"] == "[PATH]"


@pytest.mark.parametrize(
    "value",
    ["/v1/interview-sessions/{session_id}/report", "scenarios/E-01.yaml", "<run_root>/abc", "EV4-05"],
)
def test_routes_relative_paths_and_ids_are_kept(value, tmp_path) -> None:
    assert evidence.display_paths({"p": value}, run_root=tmp_path)["p"] == value


def test_human_cli_text_goes_through_the_boundary(capsys) -> None:
    cli._emit({"detail": "x"}, as_json=False, human=f"bundle at {HOME_WIN} and /home/bob/runs/1")
    out = capsys.readouterr().out
    assert "alice" not in out and "bob" not in out
    assert "[PATH]" in out


def test_json_cli_output_has_no_absolute_path(capsys, tmp_path) -> None:
    root = tmp_path / "runs"
    cli._emit({"bundle_path": str(root / "abc"), "note": "D:\\other\\x"}, as_json=True, run_root=root)
    payload = json.loads(capsys.readouterr().out)
    assert payload["bundle_path"] == "<run_root>/abc"
    assert payload["note"] == "[PATH]"
    assert not evidence.USER_PATH_RE_V2.search(json.dumps(payload))
    assert Path(str(tmp_path)).name not in json.dumps(payload)
