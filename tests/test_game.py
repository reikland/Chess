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
