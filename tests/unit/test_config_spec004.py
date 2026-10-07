"""T015 — fail-closed Spec 004 settings validation (plan §1 preflight, quickstart fixture switch)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from engine.config import ConfigError

SPEC004_DIGEST = "e15ec3790b64b2fba10e0caa9372f08c917edbbaa99ce308076952b838668b3f"


@pytest.fixture
def spec004_settings(settings):
    return replace(
        settings, model_fixture_id="spec004-report-v1", model_fixture_digest=SPEC004_DIGEST
    )


def test_spec004_settings_accept_the_spec004_fixture(spec004_settings) -> None:
    spec004_settings.validate_spec004_safety(
        whyyou_branch="yeonwoo/controlproof-e01-e02-fixture", whyyou_dirty=False
    )


@pytest.mark.parametrize(
    "updates,message",
    [
        ({"model_fixture_id": "h03-report-v1"}, "spec004-report-v1"),
        ({"model_fixture_digest": "c" * 64}, "digest"),
        ({"external_ai_allowed": True}, "external AI"),
        ({"model_substitute_enabled": False}, "external AI"),
        ({"environment_kind": "AWS"}, "LOCAL_EMULATED"),
        ({"aws_deployment_status": "DEPLOYED"}, "NOT_RUN"),
    ],
)
def test_spec004_settings_fail_closed(spec004_settings, updates, message) -> None:
    with pytest.raises(ConfigError, match=message):
        replace(spec004_settings, **updates).validate_spec004_safety(
            whyyou_branch="feature", whyyou_dirty=False
        )


@pytest.mark.parametrize("branch,dirty", [("main", False), ("master", False), ("feature", True)])
def test_spec004_settings_refuse_main_or_dirty_whyyou(spec004_settings, branch, dirty) -> None:
    with pytest.raises(ConfigError):
        spec004_settings.validate_spec004_safety(whyyou_branch=branch, whyyou_dirty=dirty)
