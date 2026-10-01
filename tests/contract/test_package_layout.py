from importlib import import_module


def test_spec002_packages_are_importable():
    assert import_module("engine.executors")
    assert import_module("engine.judges")


def test_spec003_profile_modules_are_importable():
    assert import_module("engine.executors.n02")
    assert import_module("engine.judges.n02")
