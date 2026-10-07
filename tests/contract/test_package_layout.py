from importlib import import_module

import pytest


def _red_until(task: str):
    return pytest.mark.xfail(
        strict=True, raises=ImportError, reason=f"RED until {task} creates the module"
    )


def test_spec002_packages_are_importable():
    assert import_module("engine.executors")
    assert import_module("engine.judges")


def test_spec003_profile_modules_are_importable():
    assert import_module("engine.executors.n02")
    assert import_module("engine.judges.n02")


# T011 (Spec 004): plan.md Project Structure. Each module is RED until the task that creates it.
@pytest.mark.parametrize(
    "module",
    [
        "engine.judges.e02_scoring",
        "engine.adapters.whyyou.spec004_seed",
        "engine.adapters.whyyou.report_records",
        "engine.adapters.whyyou.model_emission",
        "engine.executors.report_lanes",
        "engine.executors.e01",
        "engine.judges.e01",
        "engine.adapters.whyyou.evidence_mutation",
        pytest.param("engine.adapters.whyyou.criteria_versions", marks=_red_until("T055")),
        pytest.param("engine.executors.e02", marks=_red_until("T057")),
        pytest.param("engine.judges.e02", marks=_red_until("T058")),
        "seeds.spec004_subjects",
    ],
)
def test_spec004_modules_are_importable(module):
    assert import_module(module)
