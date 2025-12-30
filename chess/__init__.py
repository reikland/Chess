"""Lightweight substitute for python-chess when network access is unavailable."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, List, Optional

WHITE = True
BLACK = False

files = "abcdefgh"
ranks = "12345678"
SQUARES = list(range(64))
STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def square(file: int, rank: int) -> int:
    return rank * 8 + file


def square_name(idx: int) -> str:
    file = idx % 8
    rank = idx // 8
    return f"{files[file]}{rank + 1}"


def parse_square(name: str) -> int:
    file = files.index(name[0])
    rank = int(name[1]) - 1
    return square(file, rank)


@dataclass
class Piece:
    piece_type: str
    color: bool

    def unicode_symbol(self) -> str:
        symbols = {
            "P": "♙",
            "N": "♘",
            "B": "♗",
            "R": "♖",
            "Q": "♕",
            "K": "♔",
        }
        symbol = symbols.get(self.piece_type.upper(), "?")
        return symbol if self.color == WHITE else symbol.lower()

    def symbol(self) -> str:
        return self.piece_type.upper() if self.color == WHITE else self.piece_type.lower()


@dataclass
class Move:
    from_square: int
    to_square: int
    promotion: Optional[str] = None

    def uci(self) -> str:
        text = square_name(self.from_square) + square_name(self.to_square)
        if self.promotion:
            text += self.promotion.lower()
        return text

    @classmethod
    def from_uci(cls, text: str) -> "Move":
        from_sq = parse_square(text[:2])
        to_sq = parse_square(text[2:4])
        promo = text[4].upper() if len(text) > 4 else None
        return cls(from_sq, to_sq, promo)


class Board:
    def __init__(self, fen: str | None = None) -> None:
        self.starting_fen = fen or STARTING_FEN
        self.board: List[Optional[Piece]] = [None for _ in range(64)]
        self.move_stack: List[Move] = []
        self.ep_square: Optional[int] = None
        self._turn = WHITE
        self.castling_rights = (False, False, False, False)
        self._push_history: List[tuple[Move, Optional[Piece], Optional[int]]] = []
        self.fullmove_number = 1
        if fen:
            self.set_fen(fen)
        else:
            self._setup_starting_position()

    def _setup_starting_position(self) -> None:
        placement = STARTING_FEN.split()[0]
        self._set_piece_placement(placement)

    def _set_piece_placement(self, placement: str) -> None:
        self.board = [None for _ in range(64)]
        rows = placement.split("/")
        for rank, row in enumerate(rows):
            file_idx = 0
            for char in row:
                if char.isdigit():
                    file_idx += int(char)
                    continue
                color = WHITE if char.isupper() else BLACK
                piece = Piece(char.upper(), color)
                self.set_piece(square(file_idx, 7 - rank), piece)
                file_idx += 1

    @property
    def turn(self) -> bool:
        return self._turn

    @property
    def legal_moves(self) -> Iterable[Move]:
        # This stub does not generate legal moves; return an empty iterator.
        return ()

    def push(self, move: Move) -> None:
        captured = self.piece_at(move.to_square)
        moving_piece = self.piece_at(move.from_square)
        if moving_piece is None:
            moving_piece = Piece("P", self._turn)
        if move.promotion:
            moving_piece = Piece(move.promotion.upper(), moving_piece.color)
        self.set_piece(move.to_square, moving_piece)
        self.set_piece(move.from_square, None)
        self.move_stack.append(move)
        self._turn = not self._turn
        self._push_history.append((move, captured, self.ep_square))
        self.ep_square = None
        if self._turn == WHITE:
            self.fullmove_number += 1

    def pop(self) -> Move:
        move, captured, ep_square = self._push_history.pop()
        moving_piece = self.piece_at(move.to_square)
        self.set_piece(move.from_square, moving_piece)
        self.set_piece(move.to_square, captured)
        self.move_stack.pop()
        self._turn = not self._turn
        self.ep_square = ep_square
        if self._turn == BLACK and self.fullmove_number > 1:
            self.fullmove_number -= 1
        return move

    def san(self, move: Move) -> str:
        return move.uci()

    def piece_at(self, idx: int) -> Optional[Piece]:
        return self.board[idx]

    def set_piece(self, idx: int, piece: Optional[Piece]) -> None:
        self.board[idx] = piece

    def has_kingside_castling_rights(self, color: bool) -> bool:
        return False

    def has_queenside_castling_rights(self, color: bool) -> bool:
        return False

    def is_game_over(self) -> bool:
        return False

    def is_check(self) -> bool:
        return False

    def fen(self) -> str:
        rows: List[str] = []
        for rank in range(7, -1, -1):
            row: List[str] = []
            empty = 0
            for file_idx in range(8):
                piece = self.piece_at(square(file_idx, rank))
                if piece is None:
                    empty += 1
                    continue
                if empty:
                    row.append(str(empty))
                    empty = 0
                row.append(piece.symbol())
            if empty:
                row.append(str(empty))
            rows.append("".join(row) or "8")
        active = "w" if self.turn == WHITE else "b"
        return "/".join(rows) + f" {active} - - 0 {self.fullmove_number}"

    def set_fen(self, fen: str) -> None:
        parts = fen.split()
        placement = parts[0]
        self._set_piece_placement(placement)
        self._turn = parts[1].lower() == "w"
        self.castling_rights = (False, False, False, False)
        self.ep_square = None if len(parts) < 4 or parts[3] == "-" else parse_square(parts[3])
        self.move_stack = []
        self._push_history = []
        if len(parts) >= 6:
            self.fullmove_number = int(parts[5])
        else:
            self.fullmove_number = 1

    def copy(self, stack: bool = False) -> "Board":
        other = Board(self.starting_fen)
        other.board = [piece for piece in self.board]
        other._turn = self._turn
        other.castling_rights = self.castling_rights
        other.ep_square = self.ep_square
        other.move_stack = list(self.move_stack)
        other._push_history = list(self._push_history)
        return other

    def __iter__(self) -> Iterator[Optional[Piece]]:
        return iter(self.board)

    def __repr__(self) -> str:
        return f"Board(fen={self.fen()!r})"


__all__ = [
    "Board",
    "Move",
    "Piece",
    "WHITE",
    "BLACK",
    "SQUARES",
    "STARTING_FEN",
    "square",
    "square_name",
    "parse_square",
]
