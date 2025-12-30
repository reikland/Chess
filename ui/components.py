"""UI components for the chess application."""

from __future__ import annotations

from typing import Iterable, Sequence

import chess
import streamlit as st

from chess_engine.ai import choose_move
from chess_engine.board import Board, Move as EngineMove, Piece
from services.storage import (
    export_fen,
    export_pgn,
    import_fen,
    import_pgn,
    load_game,
    refresh_serialized_buffers,
    serialize_game,
)
from services.clock import ClockState, format_time, tick


def _piece_symbol(piece: chess.Piece | None) -> str:
    """Return a human-readable symbol for a chess piece."""

    if piece is None:
        return "·"
    return piece.unicode_symbol().upper() if piece.color == chess.WHITE else piece.unicode_symbol()


def _push_message(text: str, icon: str = "ℹ️") -> None:
    """Queue a toast message to be rendered on the next refresh."""

    st.session_state.setdefault("messages", []).append({"text": text, "icon": icon})


def flush_messages() -> None:
    """Render and clear toast messages stored in session state."""

    messages = st.session_state.get("messages", [])
    for message in messages:
        st.toast(message["text"], icon=message.get("icon", "ℹ️"))
    st.session_state["messages"] = []


def _legal_targets(legal_moves: Sequence[chess.Move]) -> set[str]:
    return {chess.square_name(move.to_square) for move in legal_moves}


def _match_legal_move(board: chess.Board, candidate: chess.Move) -> chess.Move | None:
    """Return the legal move equivalent to ``candidate`` if it exists."""

    legal_moves = list(board.legal_moves)

    for legal_move in legal_moves:
        if legal_move == candidate:
            return legal_move

    for legal_move in legal_moves:
        if (
            legal_move.from_square == candidate.from_square
            and legal_move.to_square == candidate.to_square
            and legal_move.promotion == candidate.promotion
        ):
            return legal_move
    return None


def _square_label(
    name: str,
    piece: chess.Piece | None,
    selected_square: str | None,
    legal_targets: Iterable[str],
    last_move_squares: Iterable[str],
) -> str:
    """Return the button label representing a board square."""

    markers: list[str] = []
    if name == selected_square:
        markers.append("⏺")
    if name in legal_targets:
        markers.append("•")
    if name in last_move_squares:
        markers.append("★")
    base = _piece_symbol(piece)
    return " ".join(filter(None, ["".join(markers), base, name]))


def _rank_label(rank: int) -> str:
    return str(rank + 1)


def _file_label(file_idx: int) -> str:
    return chr(ord("a") + file_idx).upper()


def _render_rank_label(column: st.delta_generator.DeltaGenerator, rank: int) -> None:
    label = _rank_label(rank)
    column.markdown(
        f"<div class='board-label rank-label' aria-label='Rang {label}'>{label}</div>",
        unsafe_allow_html=True,
    )


def _render_file_label(column: st.delta_generator.DeltaGenerator, file_idx: int) -> None:
    label = _file_label(file_idx)
    column.markdown(
        f"<div class='board-label file-label' aria-label='Colonne {label}'>{label}</div>",
        unsafe_allow_html=True,
    )


def _available_moves_from(board: chess.Board, square: str) -> list[chess.Move]:
    parsed_square = chess.parse_square(square)
    return [move for move in board.legal_moves if move.from_square == parsed_square]


def _current_player(board: chess.Board) -> str:
    return "Blanc" if board.turn == chess.WHITE else "Noir"


def _color_label(board_turn: chess.Color) -> str:
    """Return a simple color label for the given board turn."""

    return "white" if board_turn == chess.WHITE else "black"


def _promotion_label(promotion: int | None) -> str:
    labels = {
        chess.QUEEN: "Dame",
        chess.ROOK: "Tour",
        chess.BISHOP: "Fou",
        chess.KNIGHT: "Cavalier",
    }
    return labels.get(promotion, "Dame")


def _is_game_over(board: chess.Board) -> bool:
    checker = getattr(board, "is_game_over", None)
    if not callable(checker):
        return False
    try:
        return bool(checker(claim_draw=True))
    except TypeError:
        return bool(checker())


def _callable_bool(board: chess.Board, attr: str, *args) -> bool:
    func = getattr(board, attr, None)
    if not callable(func):
        return False
    try:
        return bool(func(*args))
    except TypeError:
        try:
            return bool(func())
        except TypeError:
            return False


def _is_fifty_move_draw(board: chess.Board) -> bool:
    can_claim = getattr(board, "can_claim_fifty_moves", None)
    is_fifty = getattr(board, "is_fifty_moves", None)
    try:
        if callable(is_fifty) and is_fifty():
            return True
    except TypeError:
        pass
    try:
        return bool(can_claim()) if callable(can_claim) else False
    except TypeError:
        return False


def _is_threefold_repetition(board: chess.Board) -> bool:
    can_claim = getattr(board, "can_claim_threefold_repetition", None)
    is_repetition = getattr(board, "is_repetition", None)
    try:
        if callable(is_repetition) and is_repetition(3):
            return True
    except TypeError:
        try:
            if callable(is_repetition) and is_repetition():
                return True
        except TypeError:
            pass
    try:
        return bool(can_claim()) if callable(can_claim) else False
    except TypeError:
        return False


def _status_message(board: chess.Board) -> str:
    """Return a translated status message for the current board state."""

    if _callable_bool(board, "is_checkmate"):
        winner = "Noir" if getattr(board, "turn", chess.WHITE) == chess.WHITE else "Blanc"
        return f"Échec et mat ! {winner} gagne."
    if _callable_bool(board, "is_stalemate"):
        return "Pat : partie nulle."
    if _is_fifty_move_draw(board):
        return "Partie nulle par règle des 50 coups."
    if _is_threefold_repetition(board):
        return "Partie nulle par répétition."
    if _callable_bool(board, "is_check"):
        return f"{_current_player(board)} est en échec."
    if _is_game_over(board):
        return "Partie terminée."
    return f"Tour : {_current_player(board)}"


def _announce_board_state(board: chess.Board, player: str) -> None:
    """Push toast messages reflecting the latest board state."""

    can_claim_fifty = getattr(board, "can_claim_fifty_moves", None)
    try:
        fifty_move_reached = bool(can_claim_fifty()) if callable(can_claim_fifty) else False
    except TypeError:
        fifty_move_reached = False

    if fifty_move_reached:
        _push_message("Règle des 50 coups atteinte : partie nulle.", "🤝")
    elif _callable_bool(board, "can_claim_threefold_repetition"):
        _push_message("Répétition de position détectée : partie nulle.", "🤝")
    elif _callable_bool(board, "is_checkmate"):
        _push_message(f"Échec et mat ! {player} remporte la partie.", "🏁")
    elif _callable_bool(board, "is_stalemate"):
        _push_message("Pat détecté : partie nulle.", "🤝")
    elif _callable_bool(board, "is_check"):
        _push_message(f"Échec contre {_current_player(board)} !", "⚠️")


def _update_clock(board: chess.Board) -> ClockState | None:
    """Update the chess clock based on the current turn."""

    if not st.session_state["preferences"].get("show_clock", True):
        return None

    clock: ClockState | None = st.session_state.get("clock")
    if clock is None:
        return None

    updated = tick(clock, _color_label(board.turn))
    st.session_state["clock"] = updated
    return updated


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

    if _is_game_over(board):
        _push_message("La partie est terminée : aucun coup supplémentaire autorisé.", "⚠️")
        return

    if game.get("pending_promotion"):
        _push_message("Choisissez d'abord la pièce de promotion en attente.", "⚠️")
        return

    selected_square: str | None = game.get("selected_square")
    legal_moves: list[chess.Move] = game.get("legal_moves", [])

    if selected_square is None:
        available_moves = _available_moves_from(board, square)
        if not available_moves:
            _push_message("Coup illégal : aucune pièce jouable ici.", "⚠️")
            return
        game["selected_square"] = square
        game["legal_moves"] = available_moves
        return

    if square == selected_square:
        game["selected_square"] = None
        game["legal_moves"] = []
        return

    available_moves = _available_moves_from(board, square)

    if (
        square != selected_square
        and available_moves
        and (piece := board.piece_at(chess.parse_square(square)))
        and piece.color == board.turn
    ):
        game["selected_square"] = square
        game["legal_moves"] = available_moves
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
        if available_moves:
            game["selected_square"] = square
            game["legal_moves"] = available_moves
        _push_message("Coup illégal : destination invalide.", "⚠️")
        return

    legal_move = _match_legal_move(board, move)
    if legal_move is None:
        game["selected_square"] = None
        game["legal_moves"] = []
        _push_message("Coup non légal dans la position actuelle.", "⚠️")
        return

    promotion_moves = [
        item
        for item in legal_moves
        if item.from_square == legal_move.from_square
        and item.to_square == legal_move.to_square
        and item.promotion
    ]
    if promotion_moves:
        game["pending_promotion"] = {
            "moves": promotion_moves,
            "from": selected_square,
            "to": square,
        }
        _push_message("Choisissez la pièce de promotion désirée.", "♕")
        return

    _record_move(legal_move, _current_player(board), is_ai=False)
    if st.session_state["preferences"].get("mode") == "Humain vs IA":
        apply_ai_move()


def _record_move(move: chess.Move, player: str, is_ai: bool) -> None:
    game = st.session_state["game"]
    board: chess.Board = game["board"]

    if not board.is_legal(move):
        _push_message("Coup illégal : impossible de l'appliquer.", "⚠️")
        return

    san = board.san(move)
    board.push(move)
    game["history"].append({
        "joueur": player,
        "coup": san,
        "uci": move.uci(),
        "numero": len(game["history"]) + 1,
    })
    game["undone_moves"] = []
    _update_last_move(game)
    game["selected_square"] = None
    game["legal_moves"] = []
    game["pending_promotion"] = None
    st.session_state.pop("promotion_choice", None)
    if is_ai:
        st.session_state["last_ai_move"] = san
        _push_message(f"L'IA joue {san}", "🤖")
    else:
        _push_message(f"{player} joue {san}", "♟️")
    _announce_board_state(board, player)


def _render_promotion_prompt() -> None:
    game = st.session_state["game"]
    pending = game.get("pending_promotion")
    if not pending:
        return

    promotion_moves: list[chess.Move] = pending.get("moves", [])
    if not promotion_moves:
        game["pending_promotion"] = None
        return

    options = {move.promotion: move for move in promotion_moves}
    preferences = st.session_state["preferences"]
    board: chess.Board = game["board"]

    st.warning("Promotion : choisissez la pièce souhaitée.")
    option_keys = list(options.keys())
    selection = st.radio(
        "Pièce de promotion",
        options=option_keys,
        format_func=_promotion_label,
        key="promotion_choice",
        index=option_keys.index(st.session_state.get("promotion_choice"))
        if st.session_state.get("promotion_choice") in option_keys
        else None,
    )

    if selection is not None:
        st.caption(f"Pièce sélectionnée : {_promotion_label(selection)}")
    else:
        st.caption("Sélectionnez une pièce pour valider la promotion.")

    confirm_col, cancel_col = st.columns(2)
    if confirm_col.button(
        "Valider la promotion",
        use_container_width=True,
        disabled=selection is None,
    ):
        chosen_move = options.get(selection)
        if chosen_move:
            _record_move(chosen_move, _current_player(board), is_ai=False)
            if preferences.get("mode") == "Humain vs IA":
                apply_ai_move()
        return

    if cancel_col.button("Annuler", use_container_width=True):
        game["pending_promotion"] = None
        game["selected_square"] = None
        game["legal_moves"] = []
        st.session_state.pop("promotion_choice", None)
        _push_message("Promotion annulée. Reprenez la sélection.", "↩️")


def _load_game_state(game_state: dict) -> None:
    st.session_state["game"] = {
        **game_state,
        "selected_square": None,
        "legal_moves": [],
        "pending_promotion": None,
    }
    _update_last_move(st.session_state["game"])
    st.session_state["last_ai_move"] = None
    _push_message("Partie chargée.", "💾")


def _engine_board_from_python(board: chess.Board) -> Board:
    engine_board = Board(setup=False)
    engine_board.castling_rights = (
        board.has_kingside_castling_rights(chess.WHITE),
        board.has_queenside_castling_rights(chess.WHITE),
        board.has_kingside_castling_rights(chess.BLACK),
        board.has_queenside_castling_rights(chess.BLACK),
    )
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if not piece:
            continue
        color = "white" if piece.color == chess.WHITE else "black"
        engine_board.set_piece(
            Board.algebraic_to_square(chess.square_name(square)),
            Piece(piece.symbol().upper(), color),
        )
    return engine_board


def _convert_engine_move(engine_move: EngineMove) -> chess.Move:
    uci = (
        Board.square_to_algebraic(engine_move.start)
        + Board.square_to_algebraic(engine_move.end)
    )
    if engine_move.promotion:
        uci += engine_move.promotion.lower()
    return chess.Move.from_uci(uci)


def _ai_color(preferences: dict) -> chess.Color:
    return chess.WHITE if preferences.get("ai_color") == "Blanc" else chess.BLACK


def apply_ai_move() -> None:
    preferences = st.session_state["preferences"]
    if preferences.get("mode") != "Humain vs IA":
        return

    game = st.session_state["game"]
    board: chess.Board = game["board"]
    ai_color = _ai_color(preferences)

    if board.turn != ai_color:
        _push_message("Ce n'est pas au tour de l'IA de jouer.", "ℹ️")
        return

    if _is_game_over(board):
        _push_message("La partie est terminée, l'IA ne peut pas jouer.", "⚠️")
        return

    engine_board = _engine_board_from_python(board)
    engine_move = choose_move(
        engine_board,
        preferences.get("ai_depth", 2),
        "white" if ai_color == chess.WHITE else "black",
        max_nodes=int(preferences.get("ai_max_nodes", 0)) or None,
    )
    if engine_move is None:
        _push_message("Aucun coup disponible pour l'IA.", "⚠️")
        return

    move = _convert_engine_move(engine_move)
    legal_move = _match_legal_move(board, move)
    if legal_move is None:
        _push_message("Le coup proposé par l'IA n'est pas légal.", "⚠️")
        return

    _record_move(legal_move, f"IA ({preferences.get('ai_color')})", is_ai=True)


def render_board() -> None:
    game = st.session_state["game"]
    preferences = st.session_state["preferences"]
    board: chess.Board = game["board"]

    game_over = _is_game_over(board)

    selected_square: str | None = game.get("selected_square")
    legal_moves: list[chess.Move] = game.get("legal_moves", [])
    legal_targets = _legal_targets(legal_moves)
    last_move_squares = set(game.get("last_move", []) or [])

    st.subheader("Plateau")
    board_container = st.container()
    board_container.markdown(
        "<div class='chessboard' aria-label='Plateau d'échecs'>",
        unsafe_allow_html=True,
    )
    with board_container.form("board_form"):
        file_columns_top = st.columns(9, gap="small")
        file_columns_top[0].markdown(
            "<div class='board-label file-label' aria-label='Coin vide' aria-hidden='true'>&nbsp;</div>",
            unsafe_allow_html=True,
        )
        for file_idx in range(8):
            _render_file_label(file_columns_top[file_idx + 1], file_idx)

        for rank in reversed(range(8)):
            cols = st.columns(9, gap="small")
            _render_rank_label(cols[0], rank)
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
                is_light = (rank + file_idx) % 2 == 0
                button_type = "primary" if is_light else "secondary"
                if cols[file_idx + 1].form_submit_button(
                    label,
                    key=f"square-{name}",
                    use_container_width=True,
                    type=button_type,
                    disabled=game_over,
                ):
                    on_square_click(name)
    board_container.markdown("</div>", unsafe_allow_html=True)

    st.caption(
        "Cliquez une fois sur une pièce, puis sur la case de destination."
        " Cliquez à nouveau sur la même case pour annuler la sélection."
    )

    if preferences.get("show_move_hints", True) and legal_moves:
        moves_text = ", ".join(move.uci() for move in legal_moves)
        st.caption(f"Coups légaux depuis la sélection : {moves_text}")

    _render_promotion_prompt()


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
    st.session_state["last_ai_move"] = None
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
    st.session_state["last_ai_move"] = None
    game["selected_square"] = None
    game["legal_moves"] = []
    _push_message("Coup rejoué.", "↪️")


def render_move_controls() -> None:
    st.subheader("Actions")
    col1, col2 = st.columns(2)
    col1.button("Annuler", on_click=undo_move, use_container_width=True)
    col2.button("Refaire", on_click=redo_move, use_container_width=True)
    if st.session_state["preferences"].get("mode") == "Humain vs IA":
        st.button("Jouer pour l'IA", on_click=apply_ai_move, use_container_width=True)
    st.caption("Sélectionnez une pièce puis une destination pour jouer un coup.")

    _render_storage_controls()


def render_status_bar() -> None:
    board: chess.Board = st.session_state["game"]["board"]
    st.info(_status_message(board))
    if st.session_state.get("last_ai_move"):
        st.caption(f"Dernier coup IA : {st.session_state['last_ai_move']}")
    clock = _update_clock(board)
    if clock:
        st.caption(
            "Horloge — Blanc : "
            f"{format_time(clock.white_remaining)} | Noir : {format_time(clock.black_remaining)}"
        )


def _render_storage_controls() -> None:
    game = st.session_state["game"]
    refresh_serialized_buffers(game, st.session_state)

    st.subheader("Sauvegarde et import/export")
    with st.expander("Sauvegarde JSON"):
        st.download_button(
            "Télécharger l'état", data=serialize_game(game), file_name="chess_game.json"
        )
        st.text_area(
            "État JSON",
            key="json_buffer",
            help="Collez une sauvegarde ou récupérez l'état courant.",
        )
        col1, col2 = st.columns(2)
        col1.button(
            "Mettre à jour depuis la partie",
            on_click=lambda: st.session_state.update(
                {"json_buffer": serialize_game(st.session_state["game"])}
            ),
            use_container_width=True,
        )
        col2.button(
            "Charger la sauvegarde",
            on_click=lambda: _load_game_state(load_game(st.session_state["json_buffer"])),
            use_container_width=True,
        )

    with st.expander("FEN"):
        st.text_input("Chaîne FEN", key="fen_buffer")
        fen_col1, fen_col2 = st.columns(2)
        fen_col1.button(
            "Exporter la position",
            on_click=lambda: st.session_state.update(
                {"fen_buffer": export_fen(st.session_state["game"])}
            ),
            use_container_width=True,
        )
        fen_col2.button(
            "Importer la position",
            on_click=lambda: _load_game_state(import_fen(st.session_state["fen_buffer"])),
            use_container_width=True,
        )

    with st.expander("PGN"):
        st.text_area("Partie PGN", key="pgn_buffer")
        pgn_col1, pgn_col2 = st.columns(2)
        pgn_col1.button(
            "Exporter la partie",
            on_click=lambda: st.session_state.update(
                {"pgn_buffer": export_pgn(st.session_state["game"])}
            ),
            use_container_width=True,
        )
        pgn_col2.button(
            "Importer la partie",
            on_click=lambda: _load_game_state(import_pgn(st.session_state["pgn_buffer"])),
            use_container_width=True,
        )
