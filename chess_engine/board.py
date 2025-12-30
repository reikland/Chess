from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

Color = str  # "white" or "black"
PieceType = str  # K, Q, R, B, N, P
Square = Tuple[int, int]


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


@dataclass
class MoveState:
    move: Move
    captured: Optional[Piece]
    castling_rights: Tuple[bool, bool, bool, bool]
    en_passant_target: Optional[Square]
    moved_piece: Piece
    was_en_passant: bool = False


class Board:
    files = "abcdefgh"

    def __init__(self, setup: bool = True) -> None:
        self.board: List[List[Optional[Piece]]] = [[None for _ in range(8)] for _ in range(8)]
        self.castling_rights = (True, True, True, True) if setup else (False, False, False, False)
        self.en_passant_target: Optional[Square] = None
        self.history: List[MoveState] = []
        if setup:
            self._setup_standard()

    @staticmethod
    def in_bounds(square: Square) -> bool:
        r, c = square
        return 0 <= r < 8 and 0 <= c < 8

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
        self.en_passant_target = None
        self.history.clear()

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

    def is_square_attacked(self, square: Square, by_color: Color) -> bool:
        r, c = square
        direction = 1 if by_color == "white" else -1
        # Pawn attacks
        for dc in (-1, 1):
            pr, pc = r + direction, c + dc
            if self.in_bounds((pr, pc)):
                piece = self.get_piece((pr, pc))
                if piece and piece.color == by_color and piece.kind == "P":
                    return True
        # Knight attacks
        knight_moves = [
            (-2, -1), (-2, 1), (2, -1), (2, 1),
            (-1, -2), (-1, 2), (1, -2), (1, 2),
        ]
        for dr, dc in knight_moves:
            nr, nc = r + dr, c + dc
            if self.in_bounds((nr, nc)):
                piece = self.get_piece((nr, nc))
                if piece and piece.color == by_color and piece.kind == "N":
                    return True
        # Sliding pieces
        directions = [
            (-1, 0), (1, 0), (0, -1), (0, 1),
            (-1, -1), (-1, 1), (1, -1), (1, 1),
        ]
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            while self.in_bounds((nr, nc)):
                piece = self.get_piece((nr, nc))
                if piece:
                    if piece.color == by_color:
                        if piece.kind == "Q":
                            return True
                        if piece.kind == "R" and (dr == 0 or dc == 0):
                            return True
                        if piece.kind == "B" and dr != 0 and dc != 0:
                            return True
                    break
                nr += dr
                nc += dc
        # King attacks
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if self.in_bounds((nr, nc)):
                    piece = self.get_piece((nr, nc))
                    if piece and piece.color == by_color and piece.kind == "K":
                        return True
        return False

    def in_check(self, color: Color) -> bool:
        king_pos = self._king_position(color)
        # A missing king indicates an invalid position where the player is
        # effectively checkmated; treat it as being in check to avoid
        # continuing the game with a captured king.
        if king_pos is None:
            return True
        opponent = "black" if color == "white" else "white"
        return self.is_square_attacked(king_pos, opponent)

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
                    if diag == self.en_passant_target:
                        moves.append(Move((r, c), diag))
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
            if color == "white" and not self.in_check("white"):
                # Kingside
                if wk and not self.get_piece((7, 5)) and not self.get_piece((7, 6)):
                    if not self.is_square_attacked((7, 5), "black") and not self.is_square_attacked((7, 6), "black"):
                        moves.append(Move((7, 4), (7, 6), is_castle=True))
                if wq and not self.get_piece((7, 1)) and not self.get_piece((7, 2)) and not self.get_piece((7, 3)):
                    if not self.is_square_attacked((7, 3), "black") and not self.is_square_attacked((7, 2), "black"):
                        moves.append(Move((7, 4), (7, 2), is_castle=True))
            if color == "black" and not self.in_check("black"):
                if bk and not self.get_piece((0, 5)) and not self.get_piece((0, 6)):
                    if not self.is_square_attacked((0, 5), "white") and not self.is_square_attacked((0, 6), "white"):
                        moves.append(Move((0, 4), (0, 6), is_castle=True))
                if bq and not self.get_piece((0, 1)) and not self.get_piece((0, 2)) and not self.get_piece((0, 3)):
                    if not self.is_square_attacked((0, 3), "white") and not self.is_square_attacked((0, 2), "white"):
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
        en_passant_capture = (
            moved_piece.kind == "P"
            and self.en_passant_target == end
            and start[1] != end[1]
            and self.get_piece(end) is None
        )

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
        elif en_passant_capture:
            self.set_piece(end, moved_piece)
            self.set_piece(start, None)
            direction = -1 if moved_piece.color == "white" else 1
            captured_square = (end[0] - direction, end[1])
            captured = self.get_piece(captured_square)
            self.set_piece(captured_square, None)
        else:
            captured = self.get_piece(end)
            self.set_piece(end, moved_piece)
            self.set_piece(start, None)
        if move.promotion:
            self.set_piece(end, Piece(move.promotion, moved_piece.color))
        prev_castling = self.castling_rights
        self.castling_rights = self._update_castling_rights_after_move(move, moved_piece, captured)
        # Update en passant target
        prev_en_passant = self.en_passant_target
        self.en_passant_target = None
        if moved_piece.kind == "P" and abs(end[0] - start[0]) == 2:
            self.en_passant_target = ((start[0] + end[0]) // 2, start[1])
        state = MoveState(
            move,
            captured,
            prev_castling,
            prev_en_passant,
            moved_piece,
            en_passant_capture,
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
        # Revert en-passant target and castling rights
        self.en_passant_target = state.en_passant_target
        self.castling_rights = state.castling_rights

        en_passant_capture = state.was_en_passant

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
        elif en_passant_capture:
            self.set_piece(start, moved_piece)
            self.set_piece(end, None)
            direction = -1 if moved_piece.color == "white" else 1
            captured_square = (end[0] + direction, end[1])
            self.set_piece(captured_square, state.captured)
        else:
            self.set_piece(start, moved_piece)
            self.set_piece(end, state.captured)
        return state

    def generate_legal_moves(self, color: Color) -> List[Move]:
        moves: List[Move] = []
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece and piece.color == color:
                    for move in self._generate_pseudo_moves_for_piece((r, c), piece):
                        self.apply_move(move)
                        if not self.in_check(color):
                            moves.append(move)
                        self.undo()
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
