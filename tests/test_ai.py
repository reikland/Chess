from chess_engine.ai import choose_move, evaluate_board
from chess_engine.board import Board, Move, Piece


def _basic_kings(board: Board) -> None:
    board.set_piece(Board.algebraic_to_square("e1"), Piece("K", "white"))
    board.set_piece(Board.algebraic_to_square("e8"), Piece("K", "black"))


def test_material_advantage_scores_positive():
    board = Board(setup=False)
    board.clear()
    _basic_kings(board)
    board.set_piece(Board.algebraic_to_square("d1"), Piece("Q", "white"))

    assert evaluate_board(board) > 8.5


def test_mobility_boosts_advantage():
    board = Board(setup=False)
    board.clear()
    board.castling_rights = (False, False, False, False)
    # Position similar to stalemate for black
    board.set_piece(Board.algebraic_to_square("a8"), Piece("K", "black"))
    board.set_piece(Board.algebraic_to_square("c6"), Piece("K", "white"))
    board.set_piece(Board.algebraic_to_square("c7"), Piece("Q", "white"))

    assert evaluate_board(board) > 9


def test_choose_move_find_mate_in_one():
    board = Board(setup=False)
    board.clear()
    board.castling_rights = (False, False, False, False)
    board.set_piece(Board.algebraic_to_square("h8"), Piece("K", "black"))
    board.set_piece(Board.algebraic_to_square("h6"), Piece("K", "white"))
    board.set_piece(Board.algebraic_to_square("f7"), Piece("Q", "white"))

    move = choose_move(board, depth=2, color="white")
    assert move is not None
    board.apply_move(move)
    assert board.in_check("black")
    assert not board.generate_legal_moves("black")
