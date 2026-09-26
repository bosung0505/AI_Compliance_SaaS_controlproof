import json

import pytest

from engine.evidence import redact


@pytest.mark.parametrize(
    "payload,forbidden",
    [
        ({"Authorization": "Bearer abc.def"}, "abc.def"),
        ({"cookie": "session=secret"}, "session=secret"),
        ({"access_token": "access-secret"}, "access-secret"),
        ({"refresh_token": "refresh-secret"}, "refresh-secret"),
        ({"url": "https://x.test/a?X-Amz-Signature=secret"}, "secret"),
        ({"email": "real.person@example.com"}, "real.person@example.com"),
        ({"applicant_display_name": "홍길동"}, "홍길동"),
        ({"phone": "010-1234-5678"}, "010-1234-5678"),
        ({"database_url": "postgresql://user:secret@localhost/db"}, "user:secret"),
        ({"invitation_token_hash": "raw-token-hash"}, "raw-token-hash"),
    ],
)
def test_secret_and_pii_corpus_is_redacted(payload, forbidden):
    serialized = json.dumps(redact(payload), ensure_ascii=False)
    assert forbidden not in serialized


def test_uuid_is_not_corrupted_by_phone_redaction():
    value = "ddac1816-1234-4abc-965e-3573ec751f5d"
    assert redact(value) == value
