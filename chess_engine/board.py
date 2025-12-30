from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

Color = str  # "white" or "black"
PieceType = str  # K, Q, R, B, N, P
Square = Tuple[int, int]


def _square_index(square: Square) -> int:
    r, c = square
    return r * 8 + c


def _bit(square: Square) -> int:
    return 1 << _square_index(square)


def _in_bounds(square: Square) -> bool:
    r, c = square
    return 0 <= r < 8 and 0 <= c < 8


# Precomputed attack tables
KNIGHT_ATTACKS: List[int] = [0] * 64
KING_ATTACKS: List[int] = [0] * 64
PAWN_ATTACKS: Dict[Color, List[int]] = {"white": [0] * 64, "black": [0] * 64}
SLIDING_RAYS: List[List[List[int]]] = [[[] for _ in range(8)] for _ in range(64)]


def _precompute_attacks() -> None:
    knight_offsets = [
        (-2, -1), (-2, 1), (2, -1), (2, 1),
        (-1, -2), (-1, 2), (1, -2), (1, 2),
    ]
    king_offsets = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1), (0, 1),
        (1, -1), (1, 0), (1, 1),
    ]
    pawn_directions = {"white": 1, "black": -1}

    for r in range(8):
        for c in range(8):
            idx = _square_index((r, c))

            # Knight
            attacks = 0
            for dr, dc in knight_offsets:
                target = (r + dr, c + dc)
                if _in_bounds(target):
                    attacks |= _bit(target)
            KNIGHT_ATTACKS[idx] = attacks

            # King
            attacks = 0
            for dr, dc in king_offsets:
                target = (r + dr, c + dc)
                if _in_bounds(target):
                    attacks |= _bit(target)
            KING_ATTACKS[idx] = attacks

            # Pawns
            for color, direction in pawn_directions.items():
                attacks = 0
                for dc in (-1, 1):
                    target = (r + direction, c + dc)
                    if _in_bounds(target):
                        attacks |= _bit(target)
                PAWN_ATTACKS[color][idx] = attacks

            # Sliding rays
            directions = [
                (-1, 0), (1, 0), (0, -1), (0, 1),
                (-1, -1), (-1, 1), (1, -1), (1, 1),
            ]
            for d_idx, (dr, dc) in enumerate(directions):
                path: List[int] = []
                nr, nc = r + dr, c + dc
                while _in_bounds((nr, nc)):
                    path.append(_square_index((nr, nc)))
                    nr += dr
                    nc += dc
                SLIDING_RAYS[idx][d_idx] = path


_precompute_attacks()


@dataclass
class Piece:
    kind: PieceType
    color: Color

    def __repr__(self) -> str:
        return f"{self.color[0].upper()}{self.kind}"


@dataclass
class Move:
    start: Square
    end: Square
    promotion: Optional[PieceType] = None
    is_castle: bool = False
    is_en_passant: bool = False


@dataclass
class MoveState:
    move: Move
    captured: Optional[Piece]
    castling_rights: Tuple[bool, bool, bool, bool]
    moved_piece: Piece
    en_passant_square: Optional[Square]
    halfmove_clock: int


@dataclass
class BoardState:
    piece_bitboards: Dict[Color, Dict[PieceType, int]]
    occupancy: int
    pieces_by_index: List[Optional[Piece]]
    king_positions: Dict[Color, Optional[Square]]


class Board:
    files = "abcdefgh"

    def __init__(self, setup: bool = True) -> None:
        self.board: List[List[Optional[Piece]]] = [[None for _ in range(8)] for _ in range(8)]
        self.castling_rights = (True, True, True, True) if setup else (False, False, False, False)
        self.en_passant_square: Optional[Square] = None
        self.history: List[MoveState] = []
        self.halfmove_clock = 0
        if setup:
            self._setup_standard()

    @staticmethod
    def in_bounds(square: Square) -> bool:
        return _in_bounds(square)

    @classmethod
    def algebraic_to_square(cls, name: str) -> Square:
        file = cls.files.index(name[0].lower())
        rank = int(name[1])
        return 8 - rank, file

    @classmethod
    def square_to_algebraic(cls, square: Square) -> str:
        r, c = square
        return f"{cls.files[c]}{8 - r}"

    def _setup_standard(self) -> None:
        pieces = "RNBQKBNR"
        for c, k in enumerate(pieces):
            self.board[7][c] = Piece(k, "white")
            self.board[0][c] = Piece(k, "black")
        for c in range(8):
            self.board[6][c] = Piece("P", "white")
            self.board[1][c] = Piece("P", "black")

    def clear(self) -> None:
        self.board = [[None for _ in range(8)] for _ in range(8)]
        self.castling_rights = (False, False, False, False)
        self.en_passant_square = None
        self.history.clear()
        self.halfmove_clock = 0

    def get_piece(self, square: Square) -> Optional[Piece]:
        r, c = square
        return self.board[r][c]

    def set_piece(self, square: Square, piece: Optional[Piece]) -> None:
        r, c = square
        self.board[r][c] = piece

    def _ally(self, piece: Piece, color: Color) -> bool:
        return piece.color == color

    def _enemy(self, piece: Piece, color: Color) -> bool:
        return piece.color != color

    def _king_position(self, color: Color) -> Optional[Square]:
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece and piece.kind == "K" and piece.color == color:
                    return (r, c)
        return None

    def _board_state(self) -> BoardState:
        piece_bitboards: Dict[Color, Dict[PieceType, int]] = {
            "white": {"P": 0, "N": 0, "B": 0, "R": 0, "Q": 0, "K": 0},
            "black": {"P": 0, "N": 0, "B": 0, "R": 0, "Q": 0, "K": 0},
        }
        occupancy = 0
        pieces_by_index: List[Optional[Piece]] = [None] * 64
        king_positions: Dict[Color, Optional[Square]] = {"white": None, "black": None}

        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece:
                    idx = _square_index((r, c))
                    bit = 1 << idx
                    occupancy |= bit
                    piece_bitboards[piece.color][piece.kind] |= bit
                    pieces_by_index[idx] = piece
                    if piece.kind == "K":
                        king_positions[piece.color] = (r, c)

        return BoardState(piece_bitboards, occupancy, pieces_by_index, king_positions)

    def _castling_path_is_safe(self, color: Color, kingside: bool) -> bool:
        """Return whether the king can legally castle through the target files.

        Assumptions:
        - The king of ``color`` is on its original square and it is ``color`` to move.
        - ``self.castling_rights`` already reflects whether the rook and king have
          moved; this helper only validates board state and attacked squares.
        """

        if self.in_check(color):
            return False

        row = 7 if color == "white" else 0
        empty_squares = [(row, 5), (row, 6)] if kingside else [(row, 3), (row, 2)]
        target_files = [5, 6] if kingside else [3, 2]

        rook_file = 7 if kingside else 0
        rook = self.get_piece((row, rook_file))
        if not rook or rook.kind != "R" or rook.color != color:
            return False

        if any(self.get_piece(square) for square in empty_squares):
            return False

        opponent = "black" if color == "white" else "white"
        for file in target_files:
            if self.is_square_attacked((row, file), opponent):
                return False
        return True

    def _resolve_en_passant_capture(self, move: Move, moved_piece: Piece) -> Optional[Piece]:
        """Execute an en-passant capture and return the captured pawn.

        Assumptions:
        - ``move.is_en_passant`` is ``True`` and the move has already been deemed
          legal (including the presence of the en-passant target square).
        - ``moved_piece`` is the pawn performing the capture and matches
          ``move.start``.
        """

        captured_square = (move.start[0], move.end[1])
        captured = self.get_piece(captured_square)
        self.set_piece(captured_square, None)
        self.set_piece(move.end, moved_piece)
        self.set_piece(move.start, None)
        return captured

    def _move_puts_self_in_check(self, move: Move, color: Color) -> bool:
        """Return True if applying ``move`` leaves ``color`` in check.

        Assumptions:
        - It is ``color`` to move and ``move`` is a pseudo-legal move produced by
          this board (piece presence has been validated).
        - ``self.in_check`` accurately reports check, including invalid positions
          where the king is missing.
        """

        self.apply_move(move)
        state = self._board_state()
        in_check = self.in_check(color, state)
        self.undo()
        return in_check

    def _sliding_attack(self, square_idx: int, by_color: Color, state: BoardState) -> bool:
        pieces = state.piece_bitboards[by_color]
        rook_like = pieces["R"] | pieces["Q"]
        bishop_like = pieces["B"] | pieces["Q"]

        for direction_idx, ray in enumerate(SLIDING_RAYS[square_idx]):
            uses_rook = direction_idx < 4
            uses_bishop = direction_idx >= 4
            target_mask = rook_like if uses_rook else bishop_like
            if not target_mask:
                continue
            for target_idx in ray:
                target_bit = 1 << target_idx
                if not state.occupancy & target_bit:
                    continue
                piece = state.pieces_by_index[target_idx]
                if piece and piece.color == by_color:
                    if uses_rook and piece.kind in {"R", "Q"}:
                        return True
                    if uses_bishop and piece.kind in {"B", "Q"}:
                        return True
                break
        return False

    def is_square_attacked(self, square: Square, by_color: Color, state: Optional[BoardState] = None) -> bool:
        state = state or self._board_state()
        idx = _square_index(square)
        pieces = state.piece_bitboards[by_color]

        # Pawn, knight, and king attacks via precomputed masks
        if PAWN_ATTACKS[by_color][idx] & pieces["P"]:
            return True
        if KNIGHT_ATTACKS[idx] & pieces["N"]:
            return True
        if KING_ATTACKS[idx] & pieces["K"]:
            return True

        # Sliding attacks
        if self._sliding_attack(idx, by_color, state):
            return True

        return False

    def in_check(self, color: Color, state: Optional[BoardState] = None) -> bool:
        state = state or self._board_state()
        king_pos = state.king_positions.get(color)
        # A missing king indicates an invalid position where the player is
        # effectively checkmated; treat it as being in check to avoid
        # continuing the game with a captured king.
        if king_pos is None:
            return True
        opponent = "black" if color == "white" else "white"
        return self.is_square_attacked(king_pos, opponent, state)

    def _generate_pseudo_moves_for_piece(self, position: Square, piece: Piece) -> List[Move]:
        r, c = position
        moves: List[Move] = []
        color = piece.color
        if piece.kind == "P":
            direction = -1 if color == "white" else 1
            start_row = 6 if color == "white" else 1
            one_step = (r + direction, c)
            if self.in_bounds(one_step) and not self.get_piece(one_step):
                if one_step[0] in (0, 7):
                    for promo in ["Q", "R", "B", "N"]:
                        moves.append(Move((r, c), one_step, promotion=promo))
                else:
                    moves.append(Move((r, c), one_step))
                two_step = (r + 2 * direction, c)
                if r == start_row and self.in_bounds(two_step) and not self.get_piece(two_step):
                    moves.append(Move((r, c), two_step))
            for dc in (-1, 1):
                diag = (r + direction, c + dc)
                if self.in_bounds(diag):
                    target = self.get_piece(diag)
                    if target and self._enemy(target, color) and target.kind != "K":
                        if diag[0] in (0, 7):
                            for promo in ["Q", "R", "B", "N"]:
                                moves.append(Move((r, c), diag, promotion=promo))
                        else:
                            moves.append(Move((r, c), diag))
                if self.en_passant_square and diag == self.en_passant_square:
                    adjacent = (r, c + dc)
                    adjacent_piece = self.get_piece(adjacent)
                    if (
                        adjacent_piece
                        and self._enemy(adjacent_piece, color)
                        and adjacent_piece.kind == "P"
                    ):
                        moves.append(Move((r, c), diag, is_en_passant=True))
        elif piece.kind == "N":
            offsets = [
                (-2, -1), (-2, 1), (2, -1), (2, 1),
                (-1, -2), (-1, 2), (1, -2), (1, 2),
            ]
            for dr, dc in offsets:
                nr, nc = r + dr, c + dc
                if self.in_bounds((nr, nc)):
                    target = self.get_piece((nr, nc))
                    if not target or (self._enemy(target, color) and target.kind != "K"):
                        moves.append(Move((r, c), (nr, nc)))
        elif piece.kind in {"B", "R", "Q"}:
            directions = []
            if piece.kind in {"B", "Q"}:
                directions.extend([(-1, -1), (-1, 1), (1, -1), (1, 1)])
            if piece.kind in {"R", "Q"}:
                directions.extend([(-1, 0), (1, 0), (0, -1), (0, 1)])
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                while self.in_bounds((nr, nc)):
                    target = self.get_piece((nr, nc))
                    if target:
                        if self._enemy(target, color) and target.kind != "K":
                            moves.append(Move((r, c), (nr, nc)))
                        break
                    moves.append(Move((r, c), (nr, nc)))
                    nr += dr
                    nc += dc
        elif piece.kind == "K":
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if self.in_bounds((nr, nc)):
                        target = self.get_piece((nr, nc))
                        if not target or (self._enemy(target, color) and target.kind != "K"):
                            moves.append(Move((r, c), (nr, nc)))
            # Castling
            wk, wq, bk, bq = self.castling_rights
            if color == "white":
                if wk and self._castling_path_is_safe("white", kingside=True):
                    moves.append(Move((7, 4), (7, 6), is_castle=True))
                if wq:
                    path_clear = not self.get_piece((7, 1)) and not self.get_piece((7, 2)) and not self.get_piece((7, 3))
                    if path_clear and self._castling_path_is_safe("white", kingside=False):
                        moves.append(Move((7, 4), (7, 2), is_castle=True))
            if color == "black":
                if bk and self._castling_path_is_safe("black", kingside=True):
                    moves.append(Move((0, 4), (0, 6), is_castle=True))
                if bq:
                    path_clear = not self.get_piece((0, 1)) and not self.get_piece((0, 2)) and not self.get_piece((0, 3))
                    if path_clear and self._castling_path_is_safe("black", kingside=False):
                        moves.append(Move((0, 4), (0, 2), is_castle=True))
        return moves

    def _update_castling_rights_after_move(self, move: Move, moved_piece: Piece, captured: Optional[Piece]) -> Tuple[bool, bool, bool, bool]:
        wk, wq, bk, bq = self.castling_rights
        start, end = move.start, move.end
        if moved_piece.kind == "K":
            if moved_piece.color == "white":
                wk = wq = False
            else:
                bk = bq = False
        if moved_piece.kind == "R":
            if moved_piece.color == "white":
                if start == (7, 0):
                    wq = False
                if start == (7, 7):
                    wk = False
            else:
                if start == (0, 0):
                    bq = False
                if start == (0, 7):
                    bk = False
        if captured and captured.kind == "R":
            if captured.color == "white":
                if end == (7, 0):
                    wq = False
                if end == (7, 7):
                    wk = False
            else:
                if end == (0, 0):
                    bq = False
                if end == (0, 7):
                    bk = False
        return wk, wq, bk, bq

    def apply_move(self, move: Move) -> MoveState:
        start, end = move.start, move.end
        moved_piece = self.get_piece(start)
        if moved_piece is None:
            raise ValueError("No piece on start square")
        captured = None
        prev_en_passant = self.en_passant_square
        self.en_passant_square = None

        if move.is_castle:
            # Move king
            self.set_piece(end, moved_piece)
            self.set_piece(start, None)
            # Move rook
            if end[1] == 6:
                rook_start = (start[0], 7)
                rook_end = (start[0], 5)
            else:
                rook_start = (start[0], 0)
                rook_end = (start[0], 3)
            rook = self.get_piece(rook_start)
            self.set_piece(rook_end, rook)
            self.set_piece(rook_start, None)
        elif move.is_en_passant:
            captured = self._resolve_en_passant_capture(move, moved_piece)
        else:
            captured = self.get_piece(end)
            self.set_piece(end, moved_piece)
            self.set_piece(start, None)
        if move.promotion:
            self.set_piece(end, Piece(move.promotion, moved_piece.color))
        if moved_piece.kind == "P" and abs(start[0] - end[0]) == 2:
            direction = -1 if moved_piece.color == "white" else 1
            self.en_passant_square = (start[0] + direction, start[1])
        prev_castling = self.castling_rights
        self.castling_rights = self._update_castling_rights_after_move(move, moved_piece, captured)
        prev_halfmove = self.halfmove_clock
        if moved_piece.kind == "P" or captured:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1
        state = MoveState(
            move,
            captured,
            prev_castling,
            moved_piece,
            prev_en_passant,
            prev_halfmove,
        )
        self.history.append(state)
        return state

    def undo(self) -> Optional[MoveState]:
        if not self.history:
            return None
        state = self.history.pop()
        move = state.move
        start, end = move.start, move.end
        moved_piece = state.moved_piece
        self.castling_rights = state.castling_rights
        self.en_passant_square = state.en_passant_square
        self.halfmove_clock = state.halfmove_clock

        if move.is_castle:
            self.set_piece(start, moved_piece)
            self.set_piece(end, None)
            if end[1] == 6:
                rook_start = (start[0], 7)
                rook_end = (start[0], 5)
            else:
                rook_start = (start[0], 0)
                rook_end = (start[0], 3)
            rook = self.get_piece(rook_end)
            self.set_piece(rook_start, rook)
            self.set_piece(rook_end, None)
        elif move.is_en_passant:
            captured_square = (start[0], end[1])
            self.set_piece(start, moved_piece)
            self.set_piece(end, None)
            self.set_piece(captured_square, state.captured)
        else:
            self.set_piece(start, moved_piece)
            self.set_piece(end, state.captured)
        return state

    def is_fifty_move_draw(self) -> bool:
        return self.halfmove_clock >= 100

    def generate_legal_moves(self, color: Color) -> List[Move]:
        moves: List[Move] = []
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece and piece.color == color:
                    for move in self._generate_pseudo_moves_for_piece((r, c), piece):
                        if not self._move_puts_self_in_check(move, color):
                            moves.append(move)
        return moves

    def __str__(self) -> str:
        rows = []
        for r in range(8):
            row = []
            for c in range(8):
                piece = self.board[r][c]
                if not piece:
                    row.append(".")
                else:
                    symbol = piece.kind
                    if piece.color == "black":
                        symbol = symbol.lower()
                    row.append(symbol)
            rows.append(" ".join(row))
        return "\n".join(rows)

    def _castling_rights_fen(self) -> str:
        wk, wq, bk, bq = self.castling_rights
        parts = []
        if wk:
            parts.append("K")
        if wq:
            parts.append("Q")
        if bk:
            parts.append("k")
        if bq:
            parts.append("q")
        return "".join(parts) or "-"

    def position_key(self, turn: Color) -> str:
        """Serialize the current position into a lightweight FEN-like string.

        The returned string contains, in order, the piece placement, the active
        color, castling rights, and the en passant square if available. The
        halfmove clock is intentionally omitted for repetition detection.
        """

        rows = []
        for r in range(8):
            empty = 0
            row_parts: List[str] = []
            for c in range(8):
                piece = self.board[r][c]
                if piece:
                    if empty:
                        row_parts.append(str(empty))
                        empty = 0
                    symbol = piece.kind if piece.color == "white" else piece.kind.lower()
                    row_parts.append(symbol)
                else:
                    empty += 1
            if empty:
                row_parts.append(str(empty))
            rows.append("".join(row_parts))
        placement = "/".join(rows)
        active_color = "w" if turn == "white" else "b"
        castling = self._castling_rights_fen()
        en_passant = self.square_to_algebraic(self.en_passant_square) if self.en_passant_square else "-"
        return f"{placement} {active_color} {castling} {en_passant}"
