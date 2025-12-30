"""Lightweight chess clock helpers."""

from __future__ import annotations

from dataclasses import dataclass, replace
import time
from typing import Literal

ColorLabel = Literal["white", "black"]


@dataclass
class ClockState:
    """Represents the remaining time for both players."""

    white_remaining: float
    black_remaining: float
    active_color: ColorLabel
    last_timestamp: float | None
    running: bool = True


def init_clock(minutes: int, starting_color: ColorLabel = "white") -> ClockState:
    """Return a fresh clock state with the provided duration per side."""

    seconds = max(60, minutes * 60)
    now = time.time()
    return ClockState(
        white_remaining=float(seconds),
        black_remaining=float(seconds),
        active_color=starting_color,
        last_timestamp=now,
    )


def tick(clock: ClockState, current_turn: ColorLabel, now: float | None = None) -> ClockState:
    """Update the running clock and switch focus to the current turn."""

    now = now or time.time()
    if clock.last_timestamp is None:
        return replace(clock, active_color=current_turn, last_timestamp=now)

    elapsed = max(0.0, now - clock.last_timestamp)
    white_remaining = clock.white_remaining
    black_remaining = clock.black_remaining

    if clock.running:
        if clock.active_color == "white":
            white_remaining = max(0.0, white_remaining - elapsed)
        else:
            black_remaining = max(0.0, black_remaining - elapsed)

    return ClockState(
        white_remaining=white_remaining,
        black_remaining=black_remaining,
        active_color=current_turn,
        last_timestamp=now,
        running=clock.running,
    )


def format_time(seconds: float) -> str:
    """Display remaining seconds as a MM:SS string with leading zeros."""

    seconds = max(0, int(seconds))
    minutes, remainder = divmod(seconds, 60)
    return f"{minutes:02d}:{remainder:02d}"
