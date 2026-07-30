from __future__ import annotations

from timesync_sim.logic import (
    choose_cm_after_timeout,
    choose_initial_cm,
    evaluate_time_integrity,
)


def test_initial_election_chooses_smallest_seen_cm() -> None:
    assert choose_initial_cm(8, {8, 3, 5}) == 3


def test_failover_keeps_available_current_cm() -> None:
    assert choose_cm_after_timeout(5, {3: 9500, 5: 9000}, 10000) == 5


def test_failover_chooses_smallest_available_cm() -> None:
    assert choose_cm_after_timeout(5, {3: 9500, 5: 7000, 8: 9800}, 10000) == 3


def test_integrity_dmax_zero_passes() -> None:
    trace = evaluate_time_integrity(0, 12.0, 4, 3, 999)
    assert trace.accepted


def test_integrity_unknown_offset_passes() -> None:
    trace = evaluate_time_integrity(50, None, 4, 3, 999)
    assert trace.accepted


def test_integrity_counter_mismatch_discards() -> None:
    trace = evaluate_time_integrity(50, 12.0, 4, 3, 10)
    assert not trace.accepted


def test_integrity_age_interval_is_strict() -> None:
    assert evaluate_time_integrity(50, 12.0, 4, 4, 1).accepted
    assert evaluate_time_integrity(50, 12.0, 4, 4, 49).accepted
    assert not evaluate_time_integrity(50, 12.0, 4, 4, 0).accepted
    assert not evaluate_time_integrity(50, 12.0, 4, 4, 50).accepted
