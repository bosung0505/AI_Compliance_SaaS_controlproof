from importlib import import_module


def test_spec002_packages_are_importable():
    assert import_module("engine.executors")
    assert import_module("engine.judges")
