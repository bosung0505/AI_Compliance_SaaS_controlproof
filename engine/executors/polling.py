"""Shared polling helpers for asynchronous WhyYou worker evidence."""

from __future__ import annotations

import math
from typing import Any
from uuid import UUID

from engine.adapters.base import AdapterResult
from engine.models import FaultBoundaryReceipt


def poll_required_boundary(
    reader: Any,
    *,
    label: str,
    run_id: UUID,
    source_event_id: UUID,
    fault_variant: str,
    session_id: str,
    clock: Any,
    poll_seconds: float,
    deadline_seconds: float,
) -> FaultBoundaryReceipt:
    """Wait for a worker-written boundary receipt without hiding terminal errors."""

    if reader is None:
        raise RuntimeError(f"{label} boundary receipt adapter is not composed")
    iterations = max(1, math.ceil(deadline_seconds / poll_seconds))
    last_code = "BOUNDARY_RECEIPT_MISSING"
    for index in range(iterations):
        result = reader.read_boundary_receipt(
            run_id=str(run_id),
            source_event_id=str(source_event_id),
            fault_variant=fault_variant,
            session_id=session_id,
        )
        if isinstance(result, FaultBoundaryReceipt):
            return result
        if isinstance(result, AdapterResult):
            last_code = result.code
            if result.ok:
                receipt = result.data.get("receipt")
                if isinstance(receipt, FaultBoundaryReceipt):
                    return receipt
                last_code = "INVALID_BOUNDARY_RECEIPT"
        else:
            last_code = "INVALID_BOUNDARY_RECEIPT"
        if index + 1 < iterations:
            clock.sleep(poll_seconds)
    raise RuntimeError(f"{label} boundary receipt failed: {last_code}")
