from types import SimpleNamespace

import pytest

from engine.web import __main__ as entry


@pytest.mark.parametrize("mode", ["default", "shared", "local", "environment"])
def test_viewer_mode_selection(monkeypatch, tmp_path, mode):
    monkeypatch.delenv("CONTROLPROOF_RUN_ROOT", raising=False)
    snapshot_path = tmp_path / "snapshot.json"
    monkeypatch.setattr(entry, "DEFAULT_SNAPSHOT", snapshot_path)
    selected = {}
    frozen = {"snapshot_id": "frozen"}
    monkeypatch.setattr(entry, "load_snapshot", lambda path: frozen)

    def make_server(port, **kwargs):
        selected.update(kwargs)
        return SimpleNamespace(
            server_address=("127.0.0.1", 8766),
            serve_forever=lambda: None,
            server_close=lambda: None,
        )

    monkeypatch.setattr(entry, "make_server", make_server)
    args = []
    if mode == "shared":
        args = ["--shared-snapshot", str(snapshot_path)]
    elif mode == "local":
        args = ["--run-root", str(tmp_path / "local")]
    elif mode == "environment":
        monkeypatch.setenv("CONTROLPROOF_RUN_ROOT", str(tmp_path / "local"))
    assert entry.main(args) == 0
    assert bool(selected["shared_snapshot"]) == (mode in {"shared", "default"})
    assert selected["run_root"] == tmp_path / (
        "bundles" if mode in {"shared", "default"} else "local"
    )


def test_explicit_shared_root_cannot_be_overridden_by_local_environment(monkeypatch):
    monkeypatch.setenv("CONTROLPROOF_RUN_ROOT", "other")
    with pytest.raises(SystemExit):
        entry.main(["--shared-snapshot", "review-data/snapshot.json"])
