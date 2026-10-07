"""Read `spec004-report-v1` emission receipts from the shared observer root (T038).

WhyYou writes one receipt per criterion assessment under `{CONTROLPROOF_OBSERVER_ROOT}/model/` (fixture contract).
Receipts carry no Run ID, so a Run selects them by its own criterion IDs, which are Run-owned.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from engine.adapters.base import AdapterResult
from engine.config import Settings
from engine.models import ModelEmissionReceipt


class WhyYouModelEmissionAdapter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def read_emissions(
        self, *, criterion_ids: tuple[str, ...]
    ) -> tuple[ModelEmissionReceipt, ...] | AdapterResult:
        directory = self.settings.observer_root / "model"
        if not directory.exists():
            return ()
        wanted = {str(value) for value in criterion_ids}
        receipts: list[ModelEmissionReceipt] = []
        try:
            for path in sorted(directory.glob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                if str(payload.get("criterion_id")) not in wanted:
                    continue
                receipts.append(ModelEmissionReceipt.model_validate(payload))
        except (OSError, ValueError, ValidationError, AttributeError) as exc:
            return AdapterResult(False, "EMISSION_RECEIPTS_UNAVAILABLE", detail=type(exc).__name__)
        return tuple(sorted(receipts, key=lambda item: (str(item.criterion_id), item.emitted_at)))
