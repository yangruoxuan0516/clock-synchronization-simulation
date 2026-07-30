from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


THREE_DECIMALS = Decimal("0.001")


def round_half_up_3(value: float) -> float:
    """Round a number to 0.001 with decimal ROUND_HALF_UP semantics."""
    return float(Decimal(str(value)).quantize(THREE_DECIMALS, rounding=ROUND_HALF_UP))


def calculate_relative_offset_error(
    clock_drift_rate: float,
    e1: float,
    l2: float,
) -> float:
    value = (
        Decimal("3000") * Decimal(str(clock_drift_rate))
        + Decimal(str(e1))
        + Decimal(str(l2))
    )
    return float(value.quantize(THREE_DECIMALS, rounding=ROUND_HALF_UP))


def calculate_local_clock_offset(
    remote_relative_offset: Optional[float],
    local_relative_offset: Optional[float],
    remote_relative_offset_error: Optional[float],
    local_relative_offset_error: Optional[float],
    remote_delay: Optional[float],
    local_delay: Optional[float],
) -> Optional[float]:
    values = (
        remote_relative_offset,
        local_relative_offset,
        remote_relative_offset_error,
        local_relative_offset_error,
        remote_delay,
        local_delay,
    )
    if any(value is None for value in values):
        return None

    result = (
        Decimal(str(remote_relative_offset))
        - Decimal(str(local_relative_offset))
        + Decimal(str(remote_relative_offset_error))
        - Decimal(str(local_relative_offset_error))
        + max(Decimal(str(remote_delay)), Decimal(str(local_delay)))
    )
    return float(result)
