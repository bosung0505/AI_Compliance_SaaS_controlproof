"""T008 — N-03 stale policy identifier: a previous (version, digest) that differs from the current one."""

from __future__ import annotations

import re

import pytest

from engine.n03 import stale_identifier

CURRENT = {"version": "consent-policy-v3", "digest": "a" * 63 + "f"}


def test_stale_identifier_changes_both_version_and_digest() -> None:
    stale = stale_identifier(CURRENT)
    assert stale["version"] == "consent-policy-v3-stale"
    assert stale["version"] != CURRENT["version"]
    assert stale["digest"] != CURRENT["digest"]
    assert stale["digest"][:-1] == CURRENT["digest"][:-1]


@pytest.mark.parametrize("last", list("0123456789abcdef"))
def test_stale_digest_stays_64_lowercase_hex(last: str) -> None:
    current = {"version": "v1", "digest": "0" * 63 + last}
    stale = stale_identifier(current)
    assert re.fullmatch(r"[0-9a-f]{64}", stale["digest"])
    assert stale["digest"][-1] != last


def test_stale_identifier_is_deterministic() -> None:
    assert stale_identifier(CURRENT) == stale_identifier(dict(CURRENT))


@pytest.mark.parametrize(
    "current",
    [
        {"version": "v1", "digest": "A" * 64},
        {"version": "v1", "digest": "a" * 63},
        {"version": "", "digest": "a" * 64},
        {"digest": "a" * 64},
    ],
)
def test_stale_identifier_rejects_malformed_current(current: dict) -> None:
    with pytest.raises(ValueError):
        stale_identifier(current)
