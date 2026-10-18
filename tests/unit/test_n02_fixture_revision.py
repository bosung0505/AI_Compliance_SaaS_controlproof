from copy import deepcopy

import pytest

from engine.models import canonical_json_bytes, sha256_bytes
from engine.n02_revision import FIXTURE_DIGEST, FIXTURE_ID, validate_fixture_revision
from engine.scenario import load


@pytest.mark.parametrize(
    "field",
    [
        "assertions",
        "steps",
        "timing_policy",
        "lanes",
        "required_evidence",
        "required_capabilities",
    ],
)
def test_fixture_revision_refuses_changed_execution_semantics_even_with_valid_digest(field):
    parent = load("scenarios/N-02.yaml").snapshot().model_dump(mode="json")
    child = load("scenarios/_N-02-analysis.yaml").snapshot().model_dump(mode="json")
    child["definition"][field] = {"changed": True}
    child["digest"] = sha256_bytes(canonical_json_bytes(child["definition"]))
    with pytest.raises(ValueError, match="execution semantics"):
        validate_fixture_revision(
            parent, child, fixture_id=FIXTURE_ID, fixture_digest=FIXTURE_DIGEST
        )


@pytest.mark.parametrize("bad", ["digest", "fixture", "version", "identity"])
def test_fixture_revision_refuses_untrusted_snapshot_or_fixture(bad):
    parent = load("scenarios/N-02.yaml").snapshot().model_dump(mode="json")
    child = deepcopy(load("scenarios/_N-02-analysis.yaml").snapshot().model_dump(mode="json"))
    digest = FIXTURE_DIGEST
    if bad == "digest":
        child["digest"] = "f" * 64
    elif bad == "fixture":
        digest = "f" * 64
    elif bad == "version":
        child["version"] = child["definition"]["version"] = "1.2.0"
        child["digest"] = sha256_bytes(canonical_json_bytes(child["definition"]))
    else:
        child["scenario_id"] = "E-01"
    with pytest.raises(ValueError):
        validate_fixture_revision(parent, child, fixture_id=FIXTURE_ID, fixture_digest=digest)
