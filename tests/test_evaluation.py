from chess_engine.board import Board, Piece
from chess_engine.evaluation import evaluate_board, king_safety, pawn_structure


def board_from_fen(fen: str) -> Board:
    board = Board(setup=False)
    board.clear()
    placement = fen.split()[0]
    rows = placement.split("/")
    for r, row in enumerate(rows):
        c = 0
        for char in row:
            if char.isdigit():
                c += int(char)
                continue
            color = "white" if char.isupper() else "black"
            board.set_piece((r, c), Piece(char.upper(), color))
            c += 1
    board.castling_rights = (False, False, False, False)
    return board


def test_knight_prefers_central_square_over_corner():
    centered = board_from_fen("8/8/8/3N4/8/8/8/4k2K w - - 0 1")
    corner = board_from_fen("N7/8/8/8/8/8/8/4k2K w - - 0 1")

    assert evaluate_board(centered) > evaluate_board(corner)


def test_pawn_shield_boosts_king_safety():
    sheltered = board_from_fen("4k3/8/8/8/8/8/5PPP/6K1 w - - 0 1")
    exposed = board_from_fen("4k3/8/8/8/8/8/8/6K1 w - - 0 1")

    sheltered_mid, _ = king_safety(sheltered)
    exposed_mid, _ = king_safety(exposed)

    assert sheltered_mid > exposed_mid
    assert evaluate_board(sheltered) > evaluate_board(exposed)


def test_passed_pawn_beats_doubled_isolated_structure():
    doubled = board_from_fen("4k3/2p5/8/8/8/2P5/2P5/4K3 w - - 0 1")
    passed = board_from_fen("4k3/8/4P3/8/8/8/8/4K3 w - - 0 1")

    assert pawn_structure(doubled) < 0
    assert pawn_structure(passed) > 0
    assert evaluate_board(passed) > evaluate_board(doubled)
