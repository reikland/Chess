"""Layout helpers for the chess Streamlit app."""

from __future__ import annotations

import streamlit as st

from ui import state
from ui.components import (
    flush_messages,
    render_board,
    render_move_controls,
    render_move_history,
    render_status_bar,
)
from ui.theme import apply_theme


def render_sidebar() -> None:
    st.sidebar.header("Options")

    preferences = st.session_state["preferences"]
    preferences["mode"] = st.sidebar.radio(
        "Mode de jeu",
        ["Humain vs Humain", "Humain vs IA"],
        index=0 if preferences.get("mode") == "Humain vs Humain" else 1,
    )
    preferences["ai_color"] = st.sidebar.selectbox(
        "Couleur de l'IA",
        ["Blanc", "Noir"],
        index=0 if preferences.get("ai_color") == "Blanc" else 1,
    )
    preferences["theme"] = st.sidebar.selectbox(
        "Thème",
        ["Classique", "Sombre"],
        index=0 if preferences.get("theme") == "Classique" else 1,
    )
    preferences["ai_depth"] = st.sidebar.slider(
        "Profondeur de recherche IA",
        min_value=1,
        max_value=20,
        value=int(preferences.get("ai_depth", 2)),
        disabled=preferences.get("mode") != "Humain vs IA",
    )
    preferences["ai_max_nodes"] = st.sidebar.number_input(
        "Noeuds maximum (IA)",
        min_value=100,
        max_value=200000,
        step=100,
        value=int(preferences.get("ai_max_nodes", 5000)),
        help="Limite dure sur le nombre de noeuds explorés par l'IA (pour accélérer la réponse).",
        disabled=preferences.get("mode") != "Humain vs IA",
    )
    preferences["timer_minutes"] = st.sidebar.number_input(
        "Temps par joueur (minutes)",
        min_value=1,
        max_value=60,
        value=int(preferences.get("timer_minutes", 10)),
    )
    preferences["show_clock"] = st.sidebar.checkbox(
        "Afficher l'horloge",
        value=bool(preferences.get("show_clock", True)),
    )
    preferences["show_move_hints"] = st.sidebar.checkbox(
        "Afficher les coups légaux pour la sélection",
        value=bool(preferences.get("show_move_hints", True)),
    )

    if preferences.get("timer_minutes") != st.session_state.get("clock_timer_minutes"):
        st.session_state["clock"] = state.init_clock_from_preferences()
        st.session_state["clock_timer_minutes"] = preferences["timer_minutes"]
        st.toast("Horloge réinitialisée avec la nouvelle durée.", icon="⏱️")

    st.sidebar.divider()
    last_ai_move = st.session_state.get("last_ai_move")
    if last_ai_move:
        st.sidebar.caption(f"Coup de l'IA : {last_ai_move}")
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
    apply_theme(st.session_state["preferences"].get("theme", "Classique"))
    render_sidebar()
    render_main_area()
