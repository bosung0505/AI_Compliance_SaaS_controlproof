from __future__ import annotations

import pytest

from engine.config import ConfigError, Settings


def environment(tmp_path):
    return {
        "CONTROLPROOF_TARGET_ID": "whyyou-local",
        "CONTROLPROOF_ENVIRONMENT_KIND": "LOCAL_EMULATED",
        "CONTROLPROOF_AWS_DEPLOYMENT_STATUS": "NOT_RUN",
        "CONTROLPROOF_RUN_ROOT": str(tmp_path / "runs"),
        "CONTROLPROOF_FAULT_ROOT": str(tmp_path / "faults"),
        "CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED": "true",
        "CONTROLPROOF_EXTERNAL_AI_ALLOWED": "false",
        "CONTROLPROOF_MODEL_FIXTURE_ID": "fixture",
        "CONTROLPROOF_MODEL_FIXTURE_DIGEST": "a" * 64,
        "WHYYOU_BASE_URL": "http://localhost:8080",
        "WHYYOU_CONSOLE_URL": "http://localhost:5173",
        "WHYYOU_DATABASE_URL": "postgresql+psycopg://local:local@localhost:5432/test",
        "WHYYOU_COMPANY_TOKEN": "local-token",
        "WHYYOU_REPO_PATH": str(tmp_path / "gbsa_aws"),
        "WHYYOU_AWS_ENDPOINT_URL": "http://localhost:4566",
        "WHYYOU_AWS_REGION": "ap-northeast-2",
        "WHYYOU_REPORTING_QUEUE_NAME": "iep-reporting",
        "WHYYOU_REPORTING_DLQ_NAME": "iep-reporting-dlq",
        "WHYYOU_REPORTING_MAX_RECEIVE_COUNT": "3",
        "WHYYOU_REPORTING_VISIBILITY_TIMEOUT_SECONDS": "5",
    }


def test_spec002_local_guard_accepts_only_clean_non_main_fixture(tmp_path):
    settings = Settings.from_env(environment(tmp_path))
    settings.validate_spec002_safety(
        controlproof_branch="002-h03-e03-fault-expansion",
        controlproof_dirty=False,
        whyyou_branch="bosung/controlproof-h03-integration",
        whyyou_dirty=False,
    )
    projection = settings.safe_projection()
    assert "local-token" not in str(projection)
    assert projection["aws_deployment_status"] == "NOT_RUN"


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"WHYYOU_AWS_ENDPOINT_URL": "https://sqs.ap-northeast-2.amazonaws.com"}, "local"),
        ({"CONTROLPROOF_EXTERNAL_AI_ALLOWED": "true"}, "external AI"),
        ({"WHYYOU_REPORTING_MAX_RECEIVE_COUNT": "4"}, "receive"),
    ],
)
def test_spec002_local_guard_fails_closed(tmp_path, change, message):
    env = environment(tmp_path)
    env.update(change)
    with pytest.raises(ConfigError, match=message):
        Settings.from_env(env)


def test_spec002_local_guard_rejects_main_and_dirty_checkout(tmp_path):
    settings = Settings.from_env(environment(tmp_path))
    with pytest.raises(ConfigError, match="main"):
        settings.validate_spec002_safety(repo_branch="main", repo_dirty=False)
    with pytest.raises(ConfigError, match="clean"):
        settings.validate_spec002_safety(repo_branch="feature", repo_dirty=True)
    with pytest.raises(ConfigError, match="ControlProof"):
        settings.validate_spec002_safety(
            controlproof_branch="002-h03-e03-fault-expansion",
            controlproof_dirty=True,
            whyyou_branch="bosung/controlproof-h03-integration",
            whyyou_dirty=False,
        )
