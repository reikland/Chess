from chess_engine.ai.engine import choose_move, evaluate_board
from chess_engine.board import Board, Move, Piece
from chess_engine.transposition import EXACT, TranspositionTable, store, zobrist_hash


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


def test_lone_black_king_still_has_legal_escape():
    board = Board(setup=False)
    board.clear()
    board.castling_rights = (False, False, False, False)
    board.set_piece(Board.algebraic_to_square("h1"), Piece("K", "black"))
    board.set_piece(Board.algebraic_to_square("f2"), Piece("K", "white"))

    # The black king should be able to step to h2 in this basic endgame-like
    # setup, ensuring the AI always finds a legal move instead of reporting
    # that none exist.
    move = choose_move(board, depth=1, color="black")

    assert move is not None
    assert move.end == Board.algebraic_to_square("h2")


def test_tt_best_move_used_for_ordering_with_node_budget():
    board = Board(setup=False)
    board.clear()
    board.castling_rights = (False, False, False, False)
    _basic_kings(board)
    rook_start = Board.algebraic_to_square("h1")
    rook_target = Board.algebraic_to_square("g1")
    board.set_piece(rook_start, Piece("R", "white"))

    transposition_table = TranspositionTable()
    key = zobrist_hash(board, "white")
    best_move = Move(rook_start, rook_target)
    store(transposition_table, key, depth=1, score=0.5, flag=EXACT, best_move=best_move)

    move = choose_move(
        board, depth=2, color="white", max_nodes=1, transposition_table=transposition_table
    )

    assert move == best_move
