from __future__ import annotations

from timesync_sim.math_utils import (
    calculate_local_clock_offset,
    calculate_relative_offset_error,
    round_half_up_3,
)


def test_round_half_up_3() -> None:
    assert round_half_up_3(1.2345) == 1.235
    assert round_half_up_3(1.2344) == 1.234


def test_relative_offset_error_formula() -> None:
    result = calculate_relative_offset_error(
        clock_drift_rate=0.00001,
        e1=0.1,
        l2=0.25,
    )
    assert result == 0.38


def test_local_clock_offset_formula() -> None:
    result = calculate_local_clock_offset(
        remote_relative_offset=220.0,
        local_relative_offset=200.0,
        remote_relative_offset_error=0.66,
        local_relative_offset_error=0.38,
        remote_delay=2.0,
        local_delay=1.5,
    )
    assert result == 23.04


def test_local_clock_offset_unknown_propagates() -> None:
    assert (
        calculate_local_clock_offset(
            remote_relative_offset=None,
            local_relative_offset=200.0,
            remote_relative_offset_error=0.66,
            local_relative_offset_error=0.38,
            remote_delay=2.0,
            local_delay=1.5,
        )
        is None
    )
