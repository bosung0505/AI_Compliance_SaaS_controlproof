"""N-02 entry point for the existing isolated local harness (explicit CLI commands only)."""

from scripts import spec004_local as local

FIXTURE_ID = "n02-analysis-v1"
FIXTURE_DIGEST = "092de5950a39ba3a7255c8696ffb073cddc65cda4615237044e3d910e32f9828"
_base_environment = local.environment


def environment(state: dict, *, for_cp: bool) -> dict[str, str]:
    values = _base_environment(state, for_cp=for_cp)
    values.update({
        "CONTROLPROOF_MODEL_FIXTURE_ID": FIXTURE_ID,
        "CONTROLPROOF_MODEL_FIXTURE_DIGEST": FIXTURE_DIGEST,
        "CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED": "true",
        "CONTROLPROOF_EXTERNAL_AI_ALLOWED": "false",
    })
    return values


def main(argv=None):
    previous = local.environment
    try:
        local.environment = environment
        return local.main(argv)
    finally:
        local.environment = previous


if __name__ == "__main__":
    raise SystemExit(main())
