"""UI components for the chess application."""

from __future__ import annotations

from typing import Iterable, Sequence

import chess
import streamlit as st


def _piece_symbol(piece: chess.Piece | None) -> str:
    if piece is None:
        return "·"
    return piece.unicode_symbol().upper() if piece.color == chess.WHITE else piece.unicode_symbol()


def _push_message(text: str, icon: str = "ℹ️") -> None:
    st.session_state.setdefault("messages", []).append({"text": text, "icon": icon})


def flush_messages() -> None:
    messages = st.session_state.get("messages", [])
    for message in messages:
        st.toast(message["text"], icon=message.get("icon", "ℹ️"))
    st.session_state["messages"] = []


def _legal_targets(legal_moves: Sequence[chess.Move]) -> set[str]:
    return {chess.square_name(move.to_square) for move in legal_moves}


def _square_label(
    name: str,
    piece: chess.Piece | None,
    selected_square: str | None,
    legal_targets: Iterable[str],
    last_move_squares: Iterable[str],
) -> str:
    markers: list[str] = []
    if name == selected_square:
        markers.append("⏺")
    if name in legal_targets:
        markers.append("•")
    if name in last_move_squares:
        markers.append("★")
    base = _piece_symbol(piece)
    return " ".join(filter(None, ["".join(markers), base, name]))


def _available_moves_from(board: chess.Board, square: str) -> list[chess.Move]:
    parsed_square = chess.parse_square(square)
    return [move for move in board.legal_moves if move.from_square == parsed_square]


def _current_player(board: chess.Board) -> str:
    return "Blanc" if board.turn == chess.WHITE else "Noir"


def _update_last_move(game: dict) -> None:
    board: chess.Board = game["board"]
    if not board.move_stack:
        game["last_move"] = None
        return
    last_move = board.move_stack[-1]
    game["last_move"] = (
        chess.square_name(last_move.from_square),
        chess.square_name(last_move.to_square),
    )


def on_square_click(square: str) -> None:
    game = st.session_state["game"]
    board: chess.Board = game["board"]

    selected_square: str | None = game.get("selected_square")
    legal_moves: list[chess.Move] = game.get("legal_moves", [])

    if selected_square is None:
        available_moves = _available_moves_from(board, square)
        if not available_moves:
            _push_message("Aucun coup légal depuis cette case.", "⚠️")
            return
        game["selected_square"] = square
        game["legal_moves"] = available_moves
        return

    if square == selected_square:
        game["selected_square"] = None
        game["legal_moves"] = []
        return

    move = next(
        (
            item
            for item in legal_moves
            if item.from_square == chess.parse_square(selected_square)
            and item.to_square == chess.parse_square(square)
        ),
        None,
    )

    if move is None:
        alternative_moves = _available_moves_from(board, square)
        if alternative_moves:
            game["selected_square"] = square
            game["legal_moves"] = alternative_moves
        _push_message("Destination invalide pour la pièce sélectionnée.", "⚠️")
        return

    san = board.san(move)
    player = _current_player(board)
    board.push(move)
    game["history"].append({
        "joueur": player,
        "coup": san,
        "uci": move.uci(),
        "numero": len(game["history"]) + 1,
    })
    game["undone_moves"] = []
    game["last_move"] = (
        chess.square_name(move.from_square),
        chess.square_name(move.to_square),
    )
    game["selected_square"] = None
    game["legal_moves"] = []


def render_board() -> None:
    game = st.session_state["game"]
    preferences = st.session_state["preferences"]
    board: chess.Board = game["board"]

    selected_square: str | None = game.get("selected_square")
    legal_moves: list[chess.Move] = game.get("legal_moves", [])
    legal_targets = _legal_targets(legal_moves)
    last_move_squares = set(game.get("last_move", []) or [])

    st.subheader("Plateau")
    for rank in reversed(range(8)):
        cols = st.columns(8)
        for file_idx in range(8):
            square = chess.square(file_idx, rank)
            name = chess.square_name(square)
            piece = board.piece_at(square)
            label = _square_label(
                name,
                piece,
                selected_square,
                legal_targets,
                last_move_squares,
            )
            if cols[file_idx].button(label, key=f"square-{name}", use_container_width=True):
                on_square_click(name)

    if preferences.get("show_move_hints", True) and legal_moves:
        moves_text = ", ".join(move.uci() for move in legal_moves)
        st.caption(f"Coups légaux depuis la sélection : {moves_text}")


def render_move_history() -> None:
    st.subheader("Historique des coups")
    history = st.session_state["game"]["history"]
    if not history:
        st.info("Aucun coup joué pour l'instant.")
        return

    st.dataframe(history, use_container_width=True, hide_index=True)


def undo_move() -> None:
    game = st.session_state["game"]
    board: chess.Board = game["board"]
    if not board.move_stack:
        _push_message("Impossible d'annuler : aucun coup joué.", "⚠️")
        return

    move = board.pop()
    game["undone_moves"].append(move)
    if game["history"]:
        game["history"].pop()
    _update_last_move(game)
    game["selected_square"] = None
    game["legal_moves"] = []
    _push_message("Coup annulé.", "↩️")


def redo_move() -> None:
    game = st.session_state["game"]
    board: chess.Board = game["board"]
    if not game["undone_moves"]:
        _push_message("Aucun coup à rejouer.", "⚠️")
        return

    move = game["undone_moves"].pop()
    san = board.san(move)
    player = _current_player(board)
    board.push(move)
    game["history"].append({
        "joueur": player,
        "coup": san,
        "uci": move.uci(),
        "numero": len(game["history"]) + 1,
    })
    game["last_move"] = (
        chess.square_name(move.from_square),
        chess.square_name(move.to_square),
    )
    game["selected_square"] = None
    game["legal_moves"] = []
    _push_message("Coup rejoué.", "↪️")


def render_move_controls() -> None:
    st.subheader("Actions")
    col1, col2 = st.columns(2)
    col1.button("Annuler", on_click=undo_move, use_container_width=True)
    col2.button("Refaire", on_click=redo_move, use_container_width=True)
    st.caption("Sélectionnez une pièce puis une destination pour jouer un coup.")


def render_status_bar() -> None:
    board: chess.Board = st.session_state["game"]["board"]
    current_player = _current_player(board)
    status = "Échec" if board.is_check() else "Tour"
    st.info(f"{status} : {current_player}")
