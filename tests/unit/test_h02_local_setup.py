import json

from scripts import h02_local


def test_cp_inspector_gets_only_ephemeral_local_constructor_credentials(monkeypatch):
    monkeypatch.setattr(h02_local, "_base_environment", lambda *a, **kw: {})
    monkeypatch.setattr(
        h02_local.subprocess,
        "check_output",
        lambda *a, **kw: (
            "diagnostic\n-----BEGIN PRIVATE KEY-----\nsynthetic\n-----END PRIVATE KEY-----\n"
        ),
    )
    state = {"whyyou_python": "test-python", "aws_port": 14771}
    values = h02_local.environment(state, for_cp=True)
    credentials = json.loads(values["GCP_SERVICE_ACCOUNT_JSON"])
    assert credentials["token_uri"] == "http://127.0.0.1:14771/synthetic-token"
    assert credentials["project_id"] == "synthetic-local"
    assert credentials["private_key"].startswith("-----BEGIN PRIVATE KEY-----")
    assert "diagnostic" not in credentials["private_key"]
    assert "GCP_SERVICE_ACCOUNT_JSON" not in h02_local.environment(state, for_cp=False)
