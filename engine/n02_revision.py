"""Narrow compatibility contract for the opt-in N-02 analysis fixture revision."""

from typing import Any

from engine.models import ScenarioSnapshot, canonical_json_bytes, sha256_bytes

FIXTURE_ID = "n02-analysis-v1"
FIXTURE_DIGEST = "092de5950a39ba3a7255c8696ffb073cddc65cda4615237044e3d910e32f9828"
LEGACY_FIXTURE = {
    "h03-report-v1": "ce09b95403b34e1390502c90f5c5edc518ddf65d38c8ce881617a37cac6d16b1"
}


def validate_fixture_revision(
    parent: dict[str, Any], child: dict[str, Any], *, fixture_id: str, fixture_digest: str
) -> None:
    """Permit only the documented fixture change; all execution semantics stay identical."""
    before, after = ScenarioSnapshot.model_validate(parent), ScenarioSnapshot.model_validate(child)
    for snapshot in (before, after):
        if (
            snapshot.digest != sha256_bytes(canonical_json_bytes(snapshot.definition))
            or snapshot.scenario_id != "N-02"
            or snapshot.definition.get("scenario_id") != snapshot.scenario_id
            or snapshot.definition.get("version") != snapshot.version
        ):
            raise ValueError("invalid fixture-only scenario snapshot")
    if (
        (before.version, after.version) != ("1.0.0", "1.1.0")
        or before.definition.get("allowed_model_fixtures") != LEGACY_FIXTURE
        or after.definition.get("allowed_model_fixtures") != {FIXTURE_ID: FIXTURE_DIGEST}
        or (fixture_id, fixture_digest) != (FIXTURE_ID, FIXTURE_DIGEST)
    ):
        raise ValueError("unsupported fixture-only scenario revision")
    ignored = {"version", "allowed_model_fixtures"}
    if {key: value for key, value in before.definition.items() if key not in ignored} != {
        key: value for key, value in after.definition.items() if key not in ignored
    }:
        raise ValueError("fixture-only revision cannot change execution semantics")
