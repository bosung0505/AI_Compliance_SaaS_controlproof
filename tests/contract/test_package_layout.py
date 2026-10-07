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
        pytest.param("engine.adapters.whyyou.spec004_seed", marks=_red_until("T036")),
        pytest.param("engine.adapters.whyyou.report_records", marks=_red_until("T037")),
        pytest.param("engine.adapters.whyyou.model_emission", marks=_red_until("T038")),
        pytest.param("engine.executors.report_lanes", marks=_red_until("T040")),
        pytest.param("engine.executors.e01", marks=_red_until("T040")),
        pytest.param("engine.judges.e01", marks=_red_until("T041")),
        pytest.param("engine.adapters.whyyou.evidence_mutation", marks=_red_until("T047")),
        pytest.param("engine.adapters.whyyou.criteria_versions", marks=_red_until("T055")),
        pytest.param("engine.executors.e02", marks=_red_until("T057")),
        pytest.param("engine.judges.e02", marks=_red_until("T058")),
        pytest.param("seeds.spec004_subjects", marks=_red_until("T035")),
    ],
)
def test_spec004_modules_are_importable(module):
    assert import_module(module)
