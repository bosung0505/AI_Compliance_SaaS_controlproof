"""H-02 opt-in configuration for the existing isolated portable local harness."""

import json
import subprocess

from engine.adapters.whyyou.h02_live import FIXTURE_DIGEST, FIXTURE_ID
from scripts import spec004_local as local

_base_environment = local.environment
_base_journal_command = local.journal_command


def environment(state, *, for_cp):
    values = _base_environment(state, for_cp=for_cp)
    values.update(
        CONTROLPROOF_MODEL_FIXTURE_ID=FIXTURE_ID,
        CONTROLPROOF_MODEL_FIXTURE_DIGEST=FIXTURE_DIGEST,
        CONTROLPROOF_MODEL_SUBSTITUTE_ENABLED="true",
        CONTROLPROOF_EXTERNAL_AI_ALLOWED="false",
        CONTROLPROOF_WHYYOU_PYTHON=state["whyyou_python"],
    )
    if for_cp:
        # Constructor-only synthetic credentials. Never read a real key or persist this material.
        signing = subprocess.check_output(
            [
                state["whyyou_python"],
                "-c",
                (
                    "from cryptography.hazmat.primitives import serialization; "
                    "from cryptography.hazmat.primitives.asymmetric import rsa; "
                    "print(rsa.generate_private_key(public_exponent=65537,key_size=2048).private_bytes("
                    "serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,"
                    "serialization.NoEncryption()).decode())"
                ),
            ],
            text=True,
        )
        begin, end = "-----BEGIN PRIVATE KEY-----", "-----END PRIVATE KEY-----"
        signing = begin + signing.split(begin, 1)[1].split(end, 1)[0] + end + "\n"
        values["GCP_SERVICE_ACCOUNT_JSON"] = json.dumps(
            {
                "type": "service_account",
                "project_id": "synthetic-local",
                "private_key_id": "synthetic",
                "private_key": signing,
                "client_email": "local@synthetic-local.iam.gserviceaccount.com",
                "token_uri": f"http://127.0.0.1:{state['aws_port']}/synthetic-token",
            }
        )
    return values


def main(argv=None):
    previous = local.environment
    previous_journal = local.journal_command
    try:
        local.environment = environment

        def h02_journal(*args, **kwargs):
            kwargs.setdefault("timeout", 1200)
            return _base_journal_command(*args, **kwargs)

        local.journal_command = h02_journal
        return local.main(argv)
    finally:
        local.environment = previous
        local.journal_command = previous_journal


if __name__ == "__main__":
    raise SystemExit(main())
