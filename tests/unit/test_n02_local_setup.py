from scripts import n02_local, spec004_local


def test_n02_wrapper_changes_only_the_model_identity(monkeypatch):
    baseline = {"CONTROLPROOF_MODEL_FIXTURE_ID": "spec004-report-v1", "DATABASE_URL": "local-db"}
    monkeypatch.setattr(n02_local, "_base_environment", lambda *args, **kwargs: dict(baseline))
    result = n02_local.environment({}, for_cp=True)
    assert result["DATABASE_URL"] == baseline["DATABASE_URL"]
    assert result["CONTROLPROOF_MODEL_FIXTURE_ID"] == "n02-analysis-v1"
    assert result["CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED"] == "true"
    assert result["CONTROLPROOF_EXTERNAL_AI_ALLOWED"] == "false"
    assert baseline["CONTROLPROOF_MODEL_FIXTURE_ID"] == "spec004-report-v1"


def test_n02_main_restores_shared_harness_after_dispatch(monkeypatch):
    original = spec004_local.environment
    seen = []
    monkeypatch.setattr(spec004_local, "main", lambda argv: seen.append(spec004_local.environment) or 0)
    assert n02_local.main(["status"]) == 0
    assert seen == [n02_local.environment]
    assert spec004_local.environment is original
