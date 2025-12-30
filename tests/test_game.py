from chess_engine.game import Game
from chess_engine.board import Piece, Board
import pytest


def test_fools_mate_checkmate():
    game = Game()
    game.make_move("f2", "f3")
    game.make_move("e7", "e5")
    game.make_move("g2", "g4")
    game.make_move("d8", "h4")

    assert game.is_checkmate("white")


def test_stalemate_detection():
    game = Game()
    game.board.clear()
    game.board.castling_rights = (False, False, False, False)
    # Position with black to move in stalemate
    game.board.set_piece(Board.algebraic_to_square("a8"), Piece("K", "black"))
    game.board.set_piece(Board.algebraic_to_square("c6"), Piece("K", "white"))
    game.board.set_piece(Board.algebraic_to_square("c7"), Piece("Q", "white"))
    game.turn = "black"

    assert game.is_stalemate("black")


def test_undo_restores_position():
    game = Game()
    game.make_move("e2", "e4")
    game.make_move("e7", "e5")
    game.undo()

    assert game.turn == "black"
    assert game.piece_at("e5") is None
    assert game.piece_at("e7") is not None

    game.undo()
    assert game.turn == "white"
    assert game.piece_at("e4") is None
    assert game.piece_at("e2") is not None


def test_king_capture_is_illegal():
    game = Game()
    game.board.clear()
    game.board.castling_rights = (False, False, False, False)
    game.board.set_piece(Board.algebraic_to_square("e1"), Piece("K", "white"))
    game.board.set_piece(Board.algebraic_to_square("e8"), Piece("K", "black"))
    game.board.set_piece(Board.algebraic_to_square("e7"), Piece("Q", "white"))
    game.turn = "white"

    legal_moves = game.legal_moves()
    assert all(move.end != Board.algebraic_to_square("e8") for move in legal_moves)

    with pytest.raises(ValueError):
        game.make_move("e7", "e8")


def test_fifty_move_rule_detection():
    game = Game()
    game.board.clear()
    game.board.castling_rights = (False, False, False, False)

    game.board.set_piece(Board.algebraic_to_square("a1"), Piece("K", "white"))
    game.board.set_piece(Board.algebraic_to_square("h8"), Piece("K", "black"))
    game.board.set_piece(Board.algebraic_to_square("b1"), Piece("N", "white"))
    game.board.set_piece(Board.algebraic_to_square("g8"), Piece("N", "black"))

    for _ in range(25):
        game.make_move("b1", "a3")
        game.make_move("g8", "h6")
        game.make_move("a3", "b1")
        game.make_move("h6", "g8")

    assert game.board.halfmove_clock == 100
    assert game.is_fifty_move_draw()
    assert game.game_status() == "draw by fifty-move rule"


def test_threefold_repetition_detection():
    game = Game()

    moves = [
        ("g1", "f3"),
        ("g8", "f6"),
        ("f3", "g1"),
        ("f6", "g8"),
        ("g1", "f3"),
        ("g8", "f6"),
        ("f3", "g1"),
        ("f6", "g8"),
    ]

    for start, end in moves:
        game.make_move(start, end)

    assert game.is_threefold_repetition()
    assert game.game_status() == "draw by repetition"
    assert game.is_over()
