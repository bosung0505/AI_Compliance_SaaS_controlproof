"""H-01 opt-in wrapper for the existing portable isolated local harness."""

from engine.adapters.whyyou.h01_live import FIXTURE_DIGEST, FIXTURE_ID
from scripts import spec004_local as local

_base_environment = local.environment


def environment(state, *, for_cp):
    values = _base_environment(state, for_cp=for_cp)
    values.update(
        CONTROLPROOF_MODEL_FIXTURE_ID=FIXTURE_ID,
        CONTROLPROOF_MODEL_FIXTURE_DIGEST=FIXTURE_DIGEST,
        CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED="true",
        CONTROLPROOF_EXTERNAL_AI_ALLOWED="false",
        CONTROLPROOF_WHYYOU_PYTHON=state["whyyou_python"],
    )
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
