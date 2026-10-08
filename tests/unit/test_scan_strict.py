"""T005 — v2 scanner beside the unchanged v1 scanner (FR-036, R-012). RED until T011."""

from __future__ import annotations

import json

from engine import evidence

ESCAPED = json.dumps({"bundle_path": "C:\\Users\\alice\\runs\\abc"}).encode()


def test_v2_finds_escaped_windows_user_path_that_v1_misses() -> None:
    assert evidence.scan_bytes(ESCAPED, profile="v1") == {}
    assert evidence.scan_bytes(ESCAPED, profile="v2") == {"user_path": 1}


def test_v2_keeps_the_v1_rules() -> None:
    payload = json.dumps(
        {"note": "Bearer abcdefghijklmnop and someone@example.com", "access_token": "secret-value"}
    ).encode()
    v1 = evidence.scan_bytes(payload, profile="v1")
    v2 = evidence.scan_bytes(payload, profile="v2")
    assert v1 == v2
    assert {"bearer", "email", "sensitive_key"} <= set(v1)


def test_scan_never_returns_matched_values() -> None:
    findings = evidence.scan_bytes(ESCAPED, profile="v2")
    assert "alice" not in json.dumps(findings)


def test_strict_alias_matches_v2() -> None:
    assert evidence.scan_bytes_strict(ESCAPED) == evidence.scan_bytes(ESCAPED, profile="v2")


def test_assert_redacted_is_still_v1() -> None:
    evidence.assert_redacted(ESCAPED)  # v1 does not raise; switching is T020
