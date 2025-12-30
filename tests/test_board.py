import pytest

from chess_engine.board import Board, Move, Piece


def test_initial_legal_moves_count():
    board = Board()
    moves = board.generate_legal_moves("white")
    assert len(moves) == 20


def test_en_passant_move_is_generated():
    board = Board(setup=False)
    board.clear()
    board.castling_rights = (False, False, False, False)
    # Place kings
    board.set_piece(Board.algebraic_to_square("e1"), Piece("K", "white"))
    board.set_piece(Board.algebraic_to_square("e8"), Piece("K", "black"))
    # Pawns positioned where en passant should be possible
    board.set_piece(Board.algebraic_to_square("e5"), Piece("P", "white"))
    board.set_piece(Board.algebraic_to_square("d7"), Piece("P", "black"))

    board.apply_move(
        Move(Board.algebraic_to_square("d7"), Board.algebraic_to_square("d5"))
    )
    moves = board.generate_legal_moves("white")
    assert any(
        m.start == Board.algebraic_to_square("e5")
        and m.end == Board.algebraic_to_square("d6")
        and m.is_en_passant
        for m in moves
    )


def test_en_passant_target_created_after_double_step():
    board = Board(setup=False)
    board.clear()
    board.castling_rights = (False, False, False, False)
    board.set_piece(Board.algebraic_to_square("e1"), Piece("K", "white"))
    board.set_piece(Board.algebraic_to_square("e8"), Piece("K", "black"))
    board.set_piece(Board.algebraic_to_square("e5"), Piece("P", "white"))
    board.set_piece(Board.algebraic_to_square("d7"), Piece("P", "black"))

    board.apply_move(
        Move(Board.algebraic_to_square("d7"), Board.algebraic_to_square("d5"))
    )

    assert board.en_passant_square == Board.algebraic_to_square("d6")


def test_en_passant_capture_executes_correctly():
    board = Board(setup=False)
    board.clear()
    board.castling_rights = (False, False, False, False)
    board.set_piece(Board.algebraic_to_square("e1"), Piece("K", "white"))
    board.set_piece(Board.algebraic_to_square("e8"), Piece("K", "black"))
    board.set_piece(Board.algebraic_to_square("e5"), Piece("P", "white"))
    board.set_piece(Board.algebraic_to_square("d7"), Piece("P", "black"))

    board.apply_move(
        Move(Board.algebraic_to_square("d7"), Board.algebraic_to_square("d5"))
    )
    moves = board.generate_legal_moves("white")
    ep_move = next(m for m in moves if m.is_en_passant)

    board.apply_move(ep_move)

    assert board.get_piece(Board.algebraic_to_square("d6")).color == "white"
    assert board.get_piece(Board.algebraic_to_square("d5")) is None
    assert board.en_passant_square is None


def test_en_passant_expires_after_intervening_move():
    board = Board(setup=False)
    board.clear()
    board.castling_rights = (False, False, False, False)
    board.set_piece(Board.algebraic_to_square("e1"), Piece("K", "white"))
    board.set_piece(Board.algebraic_to_square("e8"), Piece("K", "black"))
    board.set_piece(Board.algebraic_to_square("h1"), Piece("R", "white"))
    board.set_piece(Board.algebraic_to_square("e5"), Piece("P", "white"))
    board.set_piece(Board.algebraic_to_square("d7"), Piece("P", "black"))

    board.apply_move(
        Move(Board.algebraic_to_square("d7"), Board.algebraic_to_square("d5"))
    )
    assert board.en_passant_square is not None

    board.apply_move(
        Move(Board.algebraic_to_square("e1"), Board.algebraic_to_square("f1"))
    )

    assert board.en_passant_square is None
    moves = board.generate_legal_moves("white")
    assert all(not m.is_en_passant for m in moves)


def test_en_passant_does_not_allow_self_check():
    board = Board(setup=False)
    board.clear()
    board.castling_rights = (False, False, False, False)
    board.set_piece(Board.algebraic_to_square("e1"), Piece("K", "white"))
    board.set_piece(Board.algebraic_to_square("h8"), Piece("K", "black"))
    board.set_piece(Board.algebraic_to_square("e8"), Piece("R", "black"))
    board.set_piece(Board.algebraic_to_square("e5"), Piece("P", "white"))
    board.set_piece(Board.algebraic_to_square("d7"), Piece("P", "black"))

    board.apply_move(
        Move(Board.algebraic_to_square("d7"), Board.algebraic_to_square("d5"))
    )
    moves = board.generate_legal_moves("white")

    assert all(not m.is_en_passant for m in moves)


def test_undo_restores_en_passant_state():
    board = Board(setup=False)
    board.clear()
    board.castling_rights = (False, False, False, False)
    board.set_piece(Board.algebraic_to_square("e1"), Piece("K", "white"))
    board.set_piece(Board.algebraic_to_square("e8"), Piece("K", "black"))
    board.set_piece(Board.algebraic_to_square("e5"), Piece("P", "white"))
    board.set_piece(Board.algebraic_to_square("d7"), Piece("P", "black"))

    board.apply_move(
        Move(Board.algebraic_to_square("d7"), Board.algebraic_to_square("d5"))
    )
    ep_square = board.en_passant_square

    ep_move = next(m for m in board.generate_legal_moves("white") if m.is_en_passant)
    board.apply_move(ep_move)
    board.undo()

    assert board.en_passant_square == ep_square
    assert board.get_piece(Board.algebraic_to_square("d5")).color == "black"


def test_pawn_can_double_step_on_first_move():
    board = Board(setup=False)
    board.clear()
    board.castling_rights = (False, False, False, False)
    board.set_piece(Board.algebraic_to_square("h1"), Piece("K", "white"))
    board.set_piece(Board.algebraic_to_square("h8"), Piece("K", "black"))
    board.set_piece(Board.algebraic_to_square("e2"), Piece("P", "white"))
    board.set_piece(Board.algebraic_to_square("d4"), Piece("P", "black"))

    moves = board.generate_legal_moves("white")
    assert any(
        m.start == Board.algebraic_to_square("e2")
        and m.end == Board.algebraic_to_square("e4")
        for m in moves
    )


def test_pawn_controls_square_for_check_detection():
    board = Board(setup=False)
    board.clear()
    board.castling_rights = (False, False, False, False)
    board.set_piece(Board.algebraic_to_square("h1"), Piece("K", "white"))
    board.set_piece(Board.algebraic_to_square("d6"), Piece("K", "black"))
    board.set_piece(Board.algebraic_to_square("e5"), Piece("P", "white"))

    assert board.in_check("black")


def test_castling_moves_present():
    board = Board(setup=False)
    board.clear()
    # Place kings and rooks
    board.set_piece(Board.algebraic_to_square("e1"), Piece("K", "white"))
    board.set_piece(Board.algebraic_to_square("a1"), Piece("R", "white"))
    board.set_piece(Board.algebraic_to_square("h1"), Piece("R", "white"))
    board.set_piece(Board.algebraic_to_square("e8"), Piece("K", "black"))
    board.castling_rights = (True, True, False, False)

    moves = board.generate_legal_moves("white")
    assert any(m.is_castle and m.end == Board.algebraic_to_square("g1") for m in moves)
    assert any(m.is_castle and m.end == Board.algebraic_to_square("c1") for m in moves)


@pytest.mark.parametrize("promotion_piece", ["Q", "R", "B", "N"])
def test_pawn_promotion(promotion_piece):
    board = Board(setup=False)
    board.clear()
    board.castling_rights = (False, False, False, False)
    board.set_piece(Board.algebraic_to_square("a7"), Piece("P", "white"))
    board.set_piece(Board.algebraic_to_square("h8"), Piece("K", "black"))
    board.set_piece(Board.algebraic_to_square("h1"), Piece("K", "white"))

    moves = board.generate_legal_moves("white")
    promo_moves = [m for m in moves if m.promotion == promotion_piece]
    assert any(m.end == Board.algebraic_to_square("a8") for m in promo_moves)

    move = promo_moves[0]
    board.apply_move(move)
    promoted_piece = board.get_piece(Board.algebraic_to_square("a8"))
    assert promoted_piece.kind == promotion_piece
    assert promoted_piece.color == "white"


def test_missing_king_counts_as_check():
    board = Board(setup=False)
    board.clear()
    board.castling_rights = (False, False, False, False)
    board.set_piece(Board.algebraic_to_square("e8"), Piece("K", "black"))

    assert board.in_check("white")
