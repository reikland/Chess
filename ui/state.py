import streamlit as st


def init_session_state() -> None:
    """Initialize the Streamlit session state for the app.

    Sets up placeholders for the current game and user preferences so other
    modules can rely on their presence.
    """
    if "game" not in st.session_state:
        st.session_state["game"] = {
            "status": "not_started",
            "history": [],
        }

    if "preferences" not in st.session_state:
        st.session_state["preferences"] = {
            "theme": "classic",
            "show_move_hints": True,
        }
