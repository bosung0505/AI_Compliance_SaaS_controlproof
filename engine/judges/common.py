"""Shared reporting-effect normalization for E-03 judges."""

from __future__ import annotations

from collections.abc import Sequence

from engine.models import BusinessEffectSnapshot, Presence


def first_effect(
    snapshots: Sequence[BusinessEffectSnapshot],
) -> BusinessEffectSnapshot | None:
    return snapshots[0] if snapshots else None


def source_unavailable(snapshot: BusinessEffectSnapshot | None) -> bool:
    return snapshot is not None and snapshot.source_status is Presence.UNAVAILABLE


def durable_reporting_effects(snapshot: BusinessEffectSnapshot | None) -> dict[str, object]:
    if snapshot is None:
        return {}
    return {
        "logical_report_ids": list(snapshot.effects.get("logical_report_ids", ())),
        "projection_document_ids": list(
            snapshot.effects.get("projection_document_ids", ())
        ),
        "projection_report_ids": list(snapshot.effects.get("projection_report_ids", ())),
        "processed_keys": list(snapshot.effects.get("processed_keys", ())),
        "source_outbox_event_ids": list(
            snapshot.effects.get("source_outbox_event_ids", ())
        ),
    }


def has_durable_reporting_effect(snapshot: BusinessEffectSnapshot | None) -> bool:
    effects = durable_reporting_effects(snapshot)
    return any(
        bool(effects.get(key))
        for key in (
            "logical_report_ids",
            "projection_document_ids",
            "processed_keys",
        )
    )
