"""Layout helpers for the chess Streamlit app."""

import streamlit as st

from ui import state
from ui.components import (
    flush_messages,
    render_board,
    render_move_controls,
    render_move_history,
    render_status_bar,
)


def render_sidebar() -> None:
    st.sidebar.header("Options")

    preferences = st.session_state["preferences"]
    preferences["mode"] = st.sidebar.radio(
        "Mode de jeu",
        ["Humain vs Humain", "Humain vs IA"],
        index=0 if preferences.get("mode") == "Humain vs Humain" else 1,
    )
    preferences["theme"] = st.sidebar.selectbox(
        "Thème",
        ["Classique", "Sombre"],
        index=0 if preferences.get("theme") == "Classique" else 1,
    )
    preferences["ai_depth"] = st.sidebar.slider(
        "Profondeur de recherche IA",
        min_value=1,
        max_value=6,
        value=int(preferences.get("ai_depth", 2)),
        disabled=preferences.get("mode") != "Humain vs IA",
    )
    preferences["timer_minutes"] = st.sidebar.number_input(
        "Temps par joueur (minutes)",
        min_value=1,
        max_value=60,
        value=int(preferences.get("timer_minutes", 10)),
    )
    preferences["show_move_hints"] = st.sidebar.checkbox(
        "Afficher les coups légaux pour la sélection",
        value=bool(preferences.get("show_move_hints", True)),
    )

    st.sidebar.divider()
    st.sidebar.caption("Choisissez un thème et un mode pour personnaliser votre partie.")


def render_main_area() -> None:
    st.title("Chess Application")
    st.caption("Plateau interactif avec historique et actions de partie.")

    flush_messages()

    main_col, side_col = st.columns([3, 2])
    with main_col:
        render_status_bar()
        render_board()
        render_move_controls()

    with side_col:
        render_move_history()


def render_app() -> None:
    state.init_session_state()
    render_sidebar()
    render_main_area()
