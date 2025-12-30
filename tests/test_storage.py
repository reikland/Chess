import chess

from services.storage import (
    export_fen,
    export_pgn,
    import_fen,
    import_pgn,
    load_game,
    serialize_game,
)


def _sample_state() -> dict:
    board = chess.Board()
    history = []

    for uci in ["e2e4", "e7e5", "g1f3"]:
        move = chess.Move.from_uci(uci)
        san = board.san(move)
        player = "Blanc" if board.turn == chess.WHITE else "Noir"
        board.push(move)
        history.append(
            {
                "joueur": player,
                "coup": san,
                "uci": move.uci(),
                "numero": len(history) + 1,
            }
        )

    return {
        "status": "in_progress",
        "board": board,
        "history": history,
        "undone_moves": [],
        "selected_square": None,
        "legal_moves": [],
        "last_move": ("g1", "f3"),
    }


def test_json_round_trip_preserves_board_and_history():
    state = _sample_state()
    serialized = serialize_game(state)

    loaded = load_game(serialized)

    assert loaded["board"].fen() == state["board"].fen()
    assert loaded["history"] == state["history"]
    assert loaded["status"] == state["status"]
    assert loaded["last_move"] == state["last_move"]
    # Ensure the move stack is still usable
    loaded["board"].pop()
    assert loaded["board"].fen() != state["board"].fen()


def test_fen_import_export_round_trip():
    state = _sample_state()
    fen = export_fen(state)
    restored = import_fen(fen)

    assert restored["board"].fen() == fen
    assert restored["history"] == []


def test_pgn_import_export_round_trip():
    state = _sample_state()
    pgn_text = export_pgn(state)
    restored = import_pgn(pgn_text)

    assert restored["board"].fen() == state["board"].fen()
    assert len(restored["history"]) == len(state["history"])
    assert restored["last_move"] == state["last_move"]
