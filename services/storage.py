"""Utilities for saving and loading chess game state."""

from __future__ import annotations

import json
from io import StringIO
from typing import Any, Dict, List

import chess
import chess.pgn

GameState = Dict[str, Any]


def _base_game_state(board: chess.Board | None = None) -> GameState:
    return {
        "status": "in_progress",
        "board": board or chess.Board(),
        "history": [],
        "undone_moves": [],
        "selected_square": None,
        "legal_moves": [],
        "last_move": None,
    }


def serialize_game(game: GameState) -> str:
    board: chess.Board = game["board"]
    payload = {
        "initial_fen": board.starting_fen,
        "move_stack": [move.uci() for move in board.move_stack],
        "history": game.get("history", []),
        "undone_moves": [move.uci() for move in game.get("undone_moves", [])],
        "status": game.get("status", "in_progress"),
        "last_move": game.get("last_move"),
    }
    return json.dumps(payload)


def load_game(serialized: str) -> GameState:
    data = json.loads(serialized)

    board = chess.Board(data.get("initial_fen", chess.STARTING_FEN))
    for uci in data.get("move_stack", []):
        board.push(chess.Move.from_uci(uci))

    history = data.get("history", [])
    undone = [chess.Move.from_uci(uci) for uci in data.get("undone_moves", [])]

    game_state = _base_game_state(board)
    game_state["history"] = history
    game_state["undone_moves"] = undone
    game_state["status"] = data.get("status", "in_progress")
    last_move = data.get("last_move")
    game_state["last_move"] = tuple(last_move) if last_move else None
    return game_state


def export_fen(game: GameState) -> str:
    return game["board"].fen()


def import_fen(fen: str) -> GameState:
    board = chess.Board(fen)
    return _base_game_state(board)


def export_pgn(game: GameState) -> str:
    pgn_game = chess.pgn.Game.from_board(game["board"])
    exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
    return pgn_game.accept(exporter)


def import_pgn(pgn_data: str) -> GameState:
    parsed = chess.pgn.read_game(StringIO(pgn_data))
    if parsed is None:
        raise ValueError("Unable to parse PGN data")

    working_board = chess.Board()
    history: List[Dict[str, Any]] = []
    last_move: tuple[str, str] | None = None

    for idx, move in enumerate(parsed.mainline_moves(), start=1):
        san = working_board.san(move)
        player = "Blanc" if working_board.turn == chess.WHITE else "Noir"
        working_board.push(move)
        history.append(
            {
                "joueur": player,
                "coup": san,
                "uci": move.uci(),
                "numero": idx,
            }
        )
        last_move = (
            chess.square_name(move.from_square),
            chess.square_name(move.to_square),
        )

    game_state = _base_game_state(working_board)
    game_state["history"] = history
    game_state["last_move"] = last_move
    return game_state


def refresh_serialized_buffers(game: GameState, session_state: dict[str, Any]) -> None:
    session_state.setdefault("json_buffer", serialize_game(game))
    session_state.setdefault("fen_buffer", export_fen(game))
    session_state.setdefault("pgn_buffer", export_pgn(game))
