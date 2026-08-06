from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set

from .constants import CM_UNAVAILABLE_MS, LOCAL_CLOCK_OFFSET_EXPIRY_MS
from .math_utils import calculate_local_clock_offset
from .models import ClockOffsetListMessage


@dataclass(frozen=True)
class IntegrityStep:
    key: str
    text: str
    passed: Optional[bool]


@dataclass(frozen=True)
class IntegrityTrace:
    accepted: bool
    steps: List[IntegrityStep]
    reason: str


def choose_initial_cm(first_cm_es_id: int, request_cm_ids: Iterable[int]) -> int:
    candidates: Set[int] = set(request_cm_ids)
    if candidates:
        return min(candidates)
    return first_cm_es_id


def choose_cm_after_timeout(
    current_cm_es_id: Optional[int],
    last_clock_list_ms: Dict[int, int],
    now_ms: int,
) -> Optional[int]:
    if current_cm_es_id is not None:
        last = last_clock_list_ms.get(current_cm_es_id)
        if last is not None and now_ms - last < CM_UNAVAILABLE_MS:
            return current_cm_es_id

    available = sorted(
        cm_es_id
        for cm_es_id, last in last_clock_list_ms.items()
        if now_ms - last < CM_UNAVAILABLE_MS
    )
    if available:
        return available[0]
    return current_cm_es_id


def local_clock_offsets_are_stale(
    last_update_ms: Optional[int],
    now_ms: int,
) -> bool:
    """Return True only after offsets have gone over 1000 ms without update."""
    return (
        last_update_ms is not None
        and now_ms - last_update_ms > LOCAL_CLOCK_OFFSET_EXPIRY_MS
    )


def compute_local_offsets_from_list(
    clock_list: ClockOffsetListMessage,
    local_ca_es_id: int,
    relative_offset_delays: Dict[int, float],
) -> Dict[int, Optional[float]]:
    local_entry = clock_list.entry_for(local_ca_es_id)
    results: Dict[int, Optional[float]] = {}
    for remote_entry in clock_list.entries:
        if remote_entry.ca_es_id == local_ca_es_id:
            continue
        if local_entry is None:
            results[remote_entry.ca_es_id] = None
            continue
        results[remote_entry.ca_es_id] = calculate_local_clock_offset(
            remote_relative_offset=remote_entry.relative_offset,
            local_relative_offset=local_entry.relative_offset,
            remote_relative_offset_error=remote_entry.relative_offset_error,
            local_relative_offset_error=local_entry.relative_offset_error,
            remote_delay=relative_offset_delays.get(remote_entry.ca_es_id),
            local_delay=relative_offset_delays.get(local_ca_es_id),
        )
    return results


def evaluate_time_integrity(
    dmax: float,
    local_clock_offset: Optional[float],
    message_reset_counter: int,
    list_reset_counter: Optional[int],
    transmission_latency: int,
) -> IntegrityTrace:
    steps: List[IntegrityStep] = []

    dmax_zero = dmax == 0
    steps.append(IntegrityStep("dmax_zero", f"Dmax == 0 ({dmax})", dmax_zero))
    if dmax_zero:
        steps.append(IntegrityStep("result_pass", "PASS", True))
        return IntegrityTrace(True, steps, "Dmax is 0")

    offset_unknown = local_clock_offset is None
    steps.append(
        IntegrityStep(
            "offset_unknown",
            f"local_clock_offset is Unknown ({local_clock_offset})",
            offset_unknown,
        )
    )
    if offset_unknown:
        steps.append(IntegrityStep("result_pass", "PASS", True))
        return IntegrityTrace(True, steps, "local_clock_offset is Unknown")

    counters_equal = (
        list_reset_counter is not None
        and message_reset_counter == list_reset_counter
    )
    steps.append(
        IntegrityStep(
            "counter_equal",
            "message reset_counter == current clock_offset_list reset_counter "
            f"({message_reset_counter} vs {list_reset_counter})",
            counters_equal,
        )
    )
    if not counters_equal:
        steps.append(IntegrityStep("result_discard", "DISCARD", False))
        return IntegrityTrace(False, steps, "reset_counter mismatch or unavailable")

    age_valid = 0 < transmission_latency < dmax
    steps.append(
        IntegrityStep(
            "age_valid",
            f"0 < age < Dmax ({transmission_latency} < {dmax})",
            age_valid,
        )
    )
    if age_valid:
        steps.append(IntegrityStep("result_pass", "PASS", True))
        return IntegrityTrace(True, steps, "age is inside the permitted interval")

    steps.append(IntegrityStep("result_discard", "DISCARD", False))
    return IntegrityTrace(False, steps, "age is outside the permitted interval")
