from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from chess_engine.board import Board, Color, Piece

PieceValue: Dict[str, float] = {
    "P": 1.0,
    "N": 3.2,
    "B": 3.33,
    "R": 5.1,
    "Q": 9.0,
    "K": 0.0,
}

PHASE_WEIGHTS = {"P": 0, "N": 1, "B": 1, "R": 2, "Q": 4, "K": 0}
TOTAL_PHASE = 24  # Starting phase sum across both sides


@dataclass(frozen=True)
class EvaluationConfig:
    pawn_shield_bonus: float = 0.15
    king_open_file_penalty: float = 0.25
    king_centralization_bonus: float = 0.05
    doubled_pawn_penalty: float = 0.2
    isolated_pawn_penalty: float = 0.15
    passed_pawn_bonus: float = 0.3
    minor_centralization_bonus: float = 0.03
    development_bonus: float = 0.08
    early_castle_bonus: float = 0.25
    early_queen_penalty: float = 0.08


CONFIG = EvaluationConfig()


MIDGAME_TABLES: Dict[str, Tuple[Tuple[float, ...], ...]] = {
    "P": (
        (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        (0.05, 0.1, 0.1, -0.1, -0.1, 0.1, 0.1, 0.05),
        (0.05, -0.05, -0.05, 0.1, 0.1, -0.05, -0.05, 0.05),
        (0.0, 0.0, 0.0, 0.2, 0.2, 0.0, 0.0, 0.0),
        (0.05, 0.05, 0.1, 0.25, 0.25, 0.1, 0.05, 0.05),
        (0.1, 0.1, 0.15, 0.2, 0.2, 0.15, 0.1, 0.1),
        (0.2, 0.2, 0.2, 0.25, 0.25, 0.2, 0.2, 0.2),
        (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    ),
    "N": (
        (-0.5, -0.4, -0.3, -0.25, -0.25, -0.3, -0.4, -0.5),
        (-0.35, -0.15, 0.0, 0.1, 0.1, 0.0, -0.15, -0.35),
        (-0.25, 0.05, 0.15, 0.2, 0.2, 0.15, 0.05, -0.25),
        (-0.2, 0.05, 0.2, 0.25, 0.25, 0.2, 0.05, -0.2),
        (-0.2, 0.05, 0.2, 0.25, 0.25, 0.2, 0.05, -0.2),
        (-0.25, 0.0, 0.15, 0.2, 0.2, 0.15, 0.0, -0.25),
        (-0.35, -0.2, -0.05, 0.05, 0.05, -0.05, -0.2, -0.35),
        (-0.5, -0.35, -0.25, -0.2, -0.2, -0.25, -0.35, -0.5),
    ),
    "B": (
        (-0.2, -0.1, -0.1, -0.05, -0.05, -0.1, -0.1, -0.2),
        (-0.1, 0.0, 0.05, 0.0, 0.0, 0.05, 0.0, -0.1),
        (-0.05, 0.1, 0.15, 0.1, 0.1, 0.15, 0.1, -0.05),
        (-0.05, 0.05, 0.15, 0.2, 0.2, 0.15, 0.05, -0.05),
        (-0.05, 0.05, 0.15, 0.2, 0.2, 0.15, 0.05, -0.05),
        (-0.05, 0.05, 0.1, 0.15, 0.15, 0.1, 0.05, -0.05),
        (-0.1, 0.0, 0.05, 0.05, 0.05, 0.05, 0.0, -0.1),
        (-0.2, -0.1, -0.1, -0.05, -0.05, -0.1, -0.1, -0.2),
    ),
    "R": (
        (-0.05, 0.0, 0.05, 0.05, 0.05, 0.05, 0.0, -0.05),
        (-0.05, 0.05, 0.1, 0.15, 0.15, 0.1, 0.05, -0.05),
        (-0.05, 0.05, 0.1, 0.15, 0.15, 0.1, 0.05, -0.05),
        (-0.05, 0.05, 0.1, 0.15, 0.15, 0.1, 0.05, -0.05),
        (-0.05, 0.05, 0.1, 0.15, 0.15, 0.1, 0.05, -0.05),
        (-0.05, 0.05, 0.1, 0.15, 0.15, 0.1, 0.05, -0.05),
        (0.05, 0.1, 0.15, 0.2, 0.2, 0.15, 0.1, 0.05),
        (0.05, 0.05, 0.1, 0.15, 0.15, 0.1, 0.05, 0.05),
    ),
    "Q": (
        (-0.2, -0.1, -0.1, -0.05, -0.05, -0.1, -0.1, -0.2),
        (-0.1, 0.0, 0.05, 0.05, 0.05, 0.05, 0.0, -0.1),
        (-0.1, 0.05, 0.1, 0.1, 0.1, 0.1, 0.05, -0.1),
        (-0.05, 0.05, 0.1, 0.1, 0.1, 0.1, 0.05, -0.05),
        (-0.05, 0.05, 0.1, 0.1, 0.1, 0.1, 0.05, -0.05),
        (-0.1, 0.05, 0.1, 0.1, 0.1, 0.1, 0.05, -0.1),
        (-0.1, 0.0, 0.05, 0.05, 0.05, 0.05, 0.0, -0.1),
        (-0.2, -0.1, -0.1, -0.05, -0.05, -0.1, -0.1, -0.2),
    ),
    "K": (
        (0.2, 0.3, 0.1, 0.0, 0.0, 0.1, 0.3, 0.2),
        (0.2, 0.2, 0.0, 0.0, 0.0, 0.0, 0.2, 0.2),
        (-0.1, -0.2, -0.2, -0.2, -0.2, -0.2, -0.2, -0.1),
        (-0.2, -0.3, -0.3, -0.4, -0.4, -0.3, -0.3, -0.2),
        (-0.3, -0.4, -0.4, -0.5, -0.5, -0.4, -0.4, -0.3),
        (-0.3, -0.4, -0.4, -0.5, -0.5, -0.4, -0.4, -0.3),
        (-0.3, -0.4, -0.4, -0.5, -0.5, -0.4, -0.4, -0.3),
        (-0.3, -0.4, -0.4, -0.5, -0.5, -0.4, -0.4, -0.3),
    ),
}

ENDGAME_TABLES: Dict[str, Tuple[Tuple[float, ...], ...]] = {
    "P": tuple(reversed(MIDGAME_TABLES["P"])),
    "N": (
        (-0.4, -0.3, -0.2, -0.15, -0.15, -0.2, -0.3, -0.4),
        (-0.25, -0.05, 0.05, 0.15, 0.15, 0.05, -0.05, -0.25),
        (-0.15, 0.1, 0.2, 0.25, 0.25, 0.2, 0.1, -0.15),
        (-0.1, 0.1, 0.25, 0.3, 0.3, 0.25, 0.1, -0.1),
        (-0.1, 0.1, 0.25, 0.3, 0.3, 0.25, 0.1, -0.1),
        (-0.15, 0.05, 0.2, 0.25, 0.25, 0.2, 0.05, -0.15),
        (-0.25, -0.05, 0.05, 0.1, 0.1, 0.05, -0.05, -0.25),
        (-0.35, -0.25, -0.2, -0.15, -0.15, -0.2, -0.25, -0.35),
    ),
    "B": (
        (-0.15, -0.1, -0.05, 0.0, 0.0, -0.05, -0.1, -0.15),
        (-0.05, 0.05, 0.1, 0.15, 0.15, 0.1, 0.05, -0.05),
        (0.0, 0.1, 0.15, 0.2, 0.2, 0.15, 0.1, 0.0),
        (0.0, 0.1, 0.2, 0.25, 0.25, 0.2, 0.1, 0.0),
        (0.0, 0.1, 0.2, 0.25, 0.25, 0.2, 0.1, 0.0),
        (0.0, 0.1, 0.15, 0.2, 0.2, 0.15, 0.1, 0.0),
        (-0.05, 0.05, 0.1, 0.15, 0.15, 0.1, 0.05, -0.05),
        (-0.15, -0.1, -0.05, 0.0, 0.0, -0.05, -0.1, -0.15),
    ),
    "R": (
        (-0.05, 0.0, 0.05, 0.05, 0.05, 0.05, 0.0, -0.05),
        (0.0, 0.05, 0.1, 0.15, 0.15, 0.1, 0.05, 0.0),
        (0.05, 0.1, 0.15, 0.2, 0.2, 0.15, 0.1, 0.05),
        (0.05, 0.1, 0.15, 0.25, 0.25, 0.15, 0.1, 0.05),
        (0.05, 0.1, 0.15, 0.25, 0.25, 0.15, 0.1, 0.05),
        (0.05, 0.1, 0.15, 0.2, 0.2, 0.15, 0.1, 0.05),
        (0.0, 0.05, 0.1, 0.15, 0.15, 0.1, 0.05, 0.0),
        (-0.05, 0.0, 0.05, 0.05, 0.05, 0.05, 0.0, -0.05),
    ),
    "Q": (
        (-0.25, -0.15, -0.15, -0.1, -0.1, -0.15, -0.15, -0.25),
        (-0.15, -0.05, 0.0, 0.05, 0.05, 0.0, -0.05, -0.15),
        (-0.1, 0.0, 0.05, 0.1, 0.1, 0.05, 0.0, -0.1),
        (-0.05, 0.05, 0.1, 0.15, 0.15, 0.1, 0.05, -0.05),
        (-0.05, 0.05, 0.1, 0.15, 0.15, 0.1, 0.05, -0.05),
        (-0.1, 0.0, 0.05, 0.1, 0.1, 0.05, 0.0, -0.1),
        (-0.15, -0.05, 0.0, 0.05, 0.05, 0.0, -0.05, -0.15),
        (-0.25, -0.15, -0.15, -0.1, -0.1, -0.15, -0.15, -0.25),
    ),
    "K": (
        (-0.1, -0.05, 0.0, 0.05, 0.05, 0.0, -0.05, -0.1),
        (-0.05, 0.05, 0.1, 0.15, 0.15, 0.1, 0.05, -0.05),
        (0.0, 0.1, 0.15, 0.2, 0.2, 0.15, 0.1, 0.0),
        (0.05, 0.15, 0.2, 0.25, 0.25, 0.2, 0.15, 0.05),
        (0.1, 0.2, 0.25, 0.3, 0.3, 0.25, 0.2, 0.1),
        (0.15, 0.25, 0.3, 0.35, 0.35, 0.3, 0.25, 0.15),
        (0.15, 0.25, 0.3, 0.35, 0.35, 0.3, 0.25, 0.15),
        (0.1, 0.2, 0.25, 0.3, 0.3, 0.25, 0.2, 0.1),
    ),
}


def _mirror_row(row: int) -> int:
    return 7 - row


def _interpolate(mid_value: float, end_value: float, phase: float) -> float:
    return (phase * mid_value) + ((1 - phase) * end_value)


def _game_phase(board: Board) -> float:
    remaining_phase = 0
    for piece, _, _ in board.iter_pieces():
        remaining_phase += PHASE_WEIGHTS[piece.kind]
    return max(0.0, min(1.0, remaining_phase / TOTAL_PHASE))


def _piece_square_value(table: Tuple[Tuple[float, ...], ...], piece: Piece, row: int, col: int) -> float:
    lookup_row = row if piece.color == "white" else _mirror_row(row)
    return table[lookup_row][col]


def _material_and_position(board: Board) -> Tuple[float, float]:
    mid_score = 0.0
    end_score = 0.0
    for piece, r, c in board.iter_pieces():
        sign = 1.0 if piece.color == "white" else -1.0
        base_value = PieceValue.get(piece.kind, 0.0)
        mid_table = MIDGAME_TABLES[piece.kind]
        end_table = ENDGAME_TABLES[piece.kind]
        mid_score += sign * (base_value + _piece_square_value(mid_table, piece, r, c))
        end_score += sign * (base_value + _piece_square_value(end_table, piece, r, c))
    return mid_score, end_score


def _file_has_pawn(board: Board, file_index: int, color: Color) -> bool:
    return any(piece.kind == "P" and piece.color == color for piece, _ in board.file_pieces(file_index))


def king_safety(board: Board) -> Tuple[float, float]:
    mid_score = 0.0
    end_score = 0.0
    for color in ("white", "black"):
        king_pos = board._king_position(color)
        if king_pos is None:
            continue
        r, c = king_pos
        direction = -1 if color == "white" else 1
        shield_squares = [
            (r + direction, c + dc) for dc in (-1, 0, 1) if Board.in_bounds((r + direction, c + dc))
        ]
        shield = sum(
            1
            for square in shield_squares
            if (piece := board.get_piece(square)) and piece.kind == "P" and piece.color == color
        )
        score = shield * CONFIG.pawn_shield_bonus

        if not _file_has_pawn(board, c, color):
            score -= CONFIG.king_open_file_penalty

        center_distance = abs(3.5 - r) + abs(3.5 - c)
        centralization = (3.5 - center_distance) * CONFIG.king_centralization_bonus
        end_score += (centralization if color == "white" else -centralization)

        mid_score += score if color == "white" else -score
    return mid_score, end_score


def _pawn_files(board: Board, color: Color) -> Dict[int, list[Tuple[int, int]]]:
    files: Dict[int, list[Tuple[int, int]]] = {i: [] for i in range(8)}
    for piece, r, c in board.iter_pieces():
        if piece.kind == "P" and piece.color == color:
            files[c].append((r, c))
    return files


def pawn_structure(board: Board) -> float:
    score = 0.0
    for color_sign, color in ((1.0, "white"), (-1.0, "black")):
        files = _pawn_files(board, color)
        opponent = "black" if color == "white" else "white"
        opponent_files = _pawn_files(board, opponent)

        for file_index, pawns in files.items():
            if len(pawns) > 1:
                score -= color_sign * CONFIG.doubled_pawn_penalty * (len(pawns) - 1)

            adjacent_files = [file_index - 1, file_index + 1]
            has_neighbor = any(
                0 <= adj < 8 and files[adj] for adj in adjacent_files
            )
            if not has_neighbor:
                score -= color_sign * CONFIG.isolated_pawn_penalty

            for pawn_row, _ in pawns:
                direction = -1 if color == "white" else 1
                rows_ahead = (
                    range(pawn_row + direction, -1, direction)
                    if color == "white"
                    else range(pawn_row + direction, 8, direction)
                )
                opponent_pawns_ahead = any(
                    any(pr == pawn_row_ahead for pr, _ in opponent_files.get(f, []))
                    for pawn_row_ahead in rows_ahead
                    for f in (file_index - 1, file_index, file_index + 1)
                    if 0 <= f < 8
                )
                if not opponent_pawns_ahead:
                    score += color_sign * CONFIG.passed_pawn_bonus
    return score


def _minor_centralization(board: Board) -> float:
    score = 0.0
    for piece, r, c in board.iter_pieces():
        if piece.kind not in {"N", "B"}:
            continue
        distance = abs(3.5 - r) + abs(3.5 - c)
        centralization = (3.5 - distance) * CONFIG.minor_centralization_bonus
        score += centralization if piece.color == "white" else -centralization
    return score


def _mobility(board: Board) -> Tuple[float, float]:
    white_moves = len(board.generate_legal_moves("white"))
    black_moves = len(board.generate_legal_moves("black"))
    diff = white_moves - black_moves
    # Mobility is more valuable in the middlegame than in simplified endgames.
    return diff * 0.01, diff * 0.004


def _pawn_attacks_square(board: Board, square: Tuple[int, int], attacker: Color) -> bool:
    r, c = square
    direction = -1 if attacker == "white" else 1
    for dc in (-1, 1):
        ar, ac = r + direction, c + dc
        if Board.in_bounds((ar, ac)):
            piece = board.get_piece((ar, ac))
            if piece and piece.color == attacker and piece.kind == "P":
                return True
    return False


def _outpost_squares(board: Board) -> Tuple[float, float]:
    mid_score = 0.0
    end_score = 0.0
    for piece, r, c in board.iter_pieces():
        if piece.kind not in {"N", "B"}:
            continue

        supported_by_pawn = _pawn_attacks_square(board, (r, c), piece.color)
        enemy = "black" if piece.color == "white" else "white"
        attacked_by_enemy_pawn = _pawn_attacks_square(board, (r, c), enemy)

        if supported_by_pawn and not attacked_by_enemy_pawn:
            outpost_bonus = 0.15 if piece.kind == "N" else 0.1
            sign = 1.0 if piece.color == "white" else -1.0
            mid_score += sign * outpost_bonus
            end_score += sign * (outpost_bonus * 0.5)
    return mid_score, end_score


_START_MINOR_SQUARES = {
    "white": {(7, 1), (7, 6), (7, 2), (7, 5)},
    "black": {(0, 1), (0, 6), (0, 2), (0, 5)},
}
_CASTLED_KING_SQUARES = {(7, 6), (7, 2), (0, 6), (0, 2)}


def _development_and_castling(board: Board) -> Tuple[float, float]:
    phase = _game_phase(board)
    opening_weight = max(0.0, 1.0 - phase)
    if opening_weight == 0:
        return 0.0, 0.0

    mid_score = 0.0
    for color in ("white", "black"):
        sign = 1.0 if color == "white" else -1.0
        for square in _START_MINOR_SQUARES[color]:
            piece = board.get_piece(square)
            if not piece or piece.color != color or piece.kind not in {"N", "B"}:
                mid_score += sign * CONFIG.development_bonus * opening_weight

        king_pos = board._king_position(color)
        if king_pos in _CASTLED_KING_SQUARES:
            mid_score += sign * CONFIG.early_castle_bonus * opening_weight

        queen_home = (7, 3) if color == "white" else (0, 3)
        queen_piece = board.get_piece(queen_home)
        if queen_piece is None or queen_piece.kind != "Q" or queen_piece.color != color:
            mid_score -= sign * CONFIG.early_queen_penalty * opening_weight

    # Development matters mostly in the opening; taper off for late phases.
    return mid_score, mid_score * 0.3


def evaluate_board(board: Board) -> float:
    phase = _game_phase(board)
    mid_score, end_score = _material_and_position(board)
    king_mid, king_end = king_safety(board)
    pawn_score = pawn_structure(board)
    minor_activity = _minor_centralization(board)
    mobility_mid, mobility_end = _mobility(board)
    outpost_mid, outpost_end = _outpost_squares(board)
    dev_mid, dev_end = _development_and_castling(board)

    mid_total = (
        mid_score
        + king_mid
        + pawn_score
        + minor_activity
        + mobility_mid
        + outpost_mid
        + dev_mid
    )
    end_total = (
        end_score
        + king_end
        + pawn_score
        + minor_activity
        + mobility_end
        + outpost_end
        + dev_end
    )

    return _interpolate(mid_total, end_total, phase)

