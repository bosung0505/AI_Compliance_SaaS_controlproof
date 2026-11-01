"""Catalog-only presentation for public introduction pages; no bundle or readiness queries."""

from __future__ import annotations

from collections import Counter
from typing import Any

TREATMENTS = ("EXECUTED", "NOT_RUN", "NO_TEST_TARGET")
# Order of the four controls on the introduction page (N → H → A → E, as in the supplied homepage).
DOMAIN_ORDER = ("N", "H", "A", "E")


def _domain(entries: list[dict[str, Any]], control: str) -> dict[str, Any]:
    rows = [entry for entry in entries if entry["control"] == control]
    counts = Counter(entry["mvp_treatment"] for entry in rows)
    counts = {key: counts.get(key, 0) for key in TREATMENTS}
    # A scenario that ran with a declared unverified scope (currently N-03) is shown as partial.
    partial = [
        entry["id"] for entry in rows
        if entry["mvp_treatment"] == "EXECUTED" and (entry.get("explanation") or {}).get("unverified_scope")
    ]
    parts = [
        f"{counts[key]}개 {label}"
        for key, label in (("EXECUTED", "실행"), ("NOT_RUN", "미실행"), ("NO_TEST_TARGET", "대상 기능 없음"))
        if counts[key]
    ]
    parts += [f"{scenario_id} 일부 범위" for scenario_id in partial]
    return {
        "control": control,
        "counts": counts,
        "partial": partial,
        "label": " · ".join(parts),
        "unavailable": not counts["EXECUTED"] and not counts["NOT_RUN"] and bool(counts["NO_TEST_TARGET"]),
    }


def public_view(catalog: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    entries = catalog["scenarios"]
    counts = Counter(entry["mvp_treatment"] for entry in entries)
    return {
        **context,
        "total": len(entries),
        "coverage": {key: counts.get(key, 0) for key in TREATMENTS},
        "domains": {control: _domain(entries, control) for control in DOMAIN_ORDER},
    }
