"""Local reproduction safety: credentials isolation, source/state and instance guards."""

import pytest

from scripts import spec004_local as local


def _state(tmp_path):
    why = tmp_path / "whyyou"
    why.mkdir()
    (why / ".env.example").write_text("APP_ENVIRONMENT=local\n", encoding="utf-8")
    return {
        "whyyou_repo": str(why),
        "root": str(tmp_path / "evidence"),
        "boot": "boot-test",
        "instance": "test",
        "pg_port": 15734,
        "aws_port": 14767,
        "api_port": 18085,
    }


@pytest.mark.parametrize("for_cp", [True, False])
def test_environment_blocks_external_ai_and_inherited_cloud_credentials(
    tmp_path, monkeypatch, for_cp
):
    for key in (
        "AWS_SESSION_TOKEN",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GCP_SERVICE_ACCOUNT_JSON",
    ):
        monkeypatch.setenv(key, "inherited-real-secret")
    values = local.environment(_state(tmp_path), for_cp=for_cp)
    assert "inherited-real-secret" not in repr(values)
    assert values["CONTROLPROOF_EXTERNAL_AI_ALLOWED"] == "false"
    assert values["CONTROLPROOF_MODEL_FIXTURE_ID"] == "spec004-report-v1"
    assert values["AWS_ENDPOINT_URL"] == "http://127.0.0.1:14767"
    assert values["DATABASE_URL"].endswith("@127.0.0.1:15734/controlproof_spec004")
    assert values["CONTROLPROOF_OBSERVER_ROOT"] == str(tmp_path / "evidence/boot-test/observers")
    if for_cp:
        assert values["WHYYOU_BASE_URL"] == "http://127.0.0.1:18085"
        assert values["WHYYOU_REPO_PATH"] == str(tmp_path / "whyyou")


@pytest.mark.parametrize("instance", ["../main", "UPPER", "x;docker", "-repro"])
def test_invalid_instance_cannot_start_resources(instance):
    with pytest.raises(SystemExit):
        local.main(["up", "--instance", instance])


def test_state_cannot_be_written_inside_source_checkout(tmp_path):
    with pytest.raises(SystemExit):
        local.main(
            ["up", "--state-root", str(local.CP / "inside"), "--whyyou-repo", str(tmp_path / "why")]
        )
    assert not (local.CP / "inside").exists()


def test_checked_git_rejects_main_and_user_env_before_startup(tmp_path, monkeypatch):
    def output(command, **_kwargs):
        return "main\n" if "--show-current" in command else "a" * 40

    monkeypatch.setattr(local.subprocess, "check_output", output)
    with pytest.raises(RuntimeError, match="never main"):
        local.checked_git(tmp_path)
    monkeypatch.setattr(
        local.subprocess,
        "check_output",
        lambda command, **kwargs: (
            "feature"
            if "--show-current" in command
            else ""
            if "--porcelain" in command
            else "a" * 40
        ),
    )
    (tmp_path / ".env").write_text("credential=synthetic")
    with pytest.raises(RuntimeError, match="without .env"):
        local.checked_git(tmp_path)


def test_process_inventory_ignores_trailing_native_diagnostic(monkeypatch):
    monkeypatch.setattr(
        local.subprocess,
        "check_output",
        lambda *args, **kwargs: (
            '[{"ProcessId": 7, "ParentProcessId": 1, "Created": "synthetic-time"}]\n'
            "ANOMALY: native diagnostic\n"
        ),
    )
    assert local.process_snapshot() == [
        {"ProcessId": 7, "ParentProcessId": 1, "Created": "synthetic-time"}
    ]


def test_incomplete_process_inventory_requires_inspection_before_stop():
    with pytest.raises(RuntimeError, match="inspect pending PID"):
        local.stop({"pending_process": {"name": "api", "pid": 7}})
