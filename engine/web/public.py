"""Catalog-only presentation for public introduction pages; no bundle or readiness queries."""

from __future__ import annotations

from collections import Counter
from typing import Any


def public_view(catalog: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    entries = catalog["scenarios"]
    counts = Counter(entry["mvp_treatment"] for entry in entries)
    by_id = {entry["id"]: entry for entry in entries}
    return {
        **context,
        "total": len(entries),
        "coverage": {key: counts.get(key, 0) for key in ("EXECUTED", "NOT_RUN", "NO_TEST_TARGET")},
        "scope_sentence": " ".join(catalog["fixed_scope_sentence"].split()),
        "representatives": [by_id[key] for key in ("N-02", "H-03", "E-01") if key in by_id],
    }
