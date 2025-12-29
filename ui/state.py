import chess
import streamlit as st


def init_session_state() -> None:
    """Initialize the Streamlit session state for the app.

    Sets up placeholders for the current game and user preferences so other
    modules can rely on their presence.
    """
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

    if "preferences" not in st.session_state:
        st.session_state["preferences"] = {
            "theme": "Classique",
            "show_move_hints": True,
            "mode": "Humain vs Humain",
            "ai_depth": 2,
            "timer_minutes": 10,
        }

    if "messages" not in st.session_state:
        st.session_state["messages"] = []
