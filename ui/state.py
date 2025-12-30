"""State initialization utilities for the Streamlit application."""

from __future__ import annotations

import chess
import streamlit as st

from services.clock import ClockState, init_clock


def _init_preferences() -> None:
    """Ensure default user preferences exist in session state."""

    if "preferences" not in st.session_state:
        st.session_state["preferences"] = {
            "theme": "Classique",
            "show_move_hints": True,
            "mode": "Humain vs Humain",
            "ai_depth": 2,
            "ai_color": "Noir",
            "timer_minutes": 10,
            "show_clock": True,
        }


def _init_game() -> None:
    """Create an empty game scaffold in session state."""

    if "game" not in st.session_state:
        st.session_state["game"] = {
            "status": "in_progress",
            "board": chess.Board(),
            "history": [],
            "undone_moves": [],
            "selected_square": None,
            "legal_moves": [],
            "last_move": None,
        }


def init_clock_from_preferences() -> ClockState:
    """Create a chess clock instance based on the configured duration."""

    preferences = st.session_state["preferences"]
    clock_state = init_clock(
        minutes=int(preferences.get("timer_minutes", 10)),
        starting_color="white",
    )
    st.session_state["clock"] = clock_state
    st.session_state["clock_timer_minutes"] = preferences.get("timer_minutes", 10)
    return clock_state


def init_session_state() -> None:
    """Initialize the Streamlit session state for the app.

    Sets up placeholders for the current game, user preferences, toast messages and the
    optional chess clock so other modules can rely on their presence.
    """

    _init_preferences()
    _init_game()

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    if "clock" not in st.session_state:
        init_clock_from_preferences()
