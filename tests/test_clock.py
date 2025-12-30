import math

from services.clock import format_time, init_clock, tick


def test_tick_consumes_time_for_active_color():
    clock = init_clock(minutes=1, starting_color="white")
    start_white = clock.white_remaining
    # Advance time while white is active
    updated = tick(clock, "white", now=clock.last_timestamp + 15)
    assert math.isclose(updated.white_remaining, start_white - 15, rel_tol=1e-6)

    # Switch to black's turn: white time continues ticking until the switch moment
    updated_again = tick(updated, "black", now=updated.last_timestamp + 20)
    assert math.isclose(updated_again.white_remaining, updated.white_remaining - 20, rel_tol=1e-6)
    assert math.isclose(updated_again.black_remaining, updated.black_remaining, rel_tol=1e-6)

    # Black time decreases once active
    final_state = tick(updated_again, "black", now=updated_again.last_timestamp + 10)
    assert math.isclose(final_state.black_remaining, updated_again.black_remaining - 10, rel_tol=1e-6)


def test_format_time_handles_zero_and_padding():
    assert format_time(0) == "00:00"
    assert format_time(9) == "00:09"
    assert format_time(125) == "02:05"
