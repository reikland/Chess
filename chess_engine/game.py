from __future__ import annotations

from collections import Counter
from typing import List, Optional

from .board import Board, Move, Piece


class Game:
    def __init__(self) -> None:
        self.board = Board()
        self.turn: str = "white"
        self.move_stack: List[Move] = []
        self.position_counts: Counter[str] = Counter()
        self._record_position()

    def _switch_turn(self) -> None:
        self.turn = "black" if self.turn == "white" else "white"

    def _position_key(self) -> str:
        return self.board.position_key(self.turn)

    def _record_position(self) -> None:
        self.position_counts[self._position_key()] += 1

    def _decrement_position(self) -> None:
        key = self._position_key()
        if key in self.position_counts:
            self.position_counts[key] -= 1
            if self.position_counts[key] <= 0:
                del self.position_counts[key]

    def legal_moves(self) -> List[Move]:
        return self.board.generate_legal_moves(self.turn)

    def make_move(self, start: str, end: str, promotion: Optional[str] = None) -> Move:
        move_start = self.board.algebraic_to_square(start)
        move_end = self.board.algebraic_to_square(end)
        legal = self.legal_moves()
        candidate = None
        for mv in legal:
            if (
                mv.start == move_start
                and mv.end == move_end
                and mv.promotion == promotion
                and not mv.is_en_passant
            ):
                candidate = mv
                break
            if (
                mv.start == move_start
                and mv.end == move_end
                and mv.promotion
                and promotion is None
                and not mv.is_en_passant
            ):
                # default to queen promotion when not specified
                if mv.promotion == "Q":
                    candidate = mv
                    break
            if mv.start == move_start and mv.end == move_end and mv.is_en_passant:
                candidate = mv
                break
        if candidate is None:
            raise ValueError("Illegal move")
        # Update promotion piece if specified
        if candidate.promotion and promotion:
            candidate.promotion = promotion
        self.board.apply_move(candidate)
        self.move_stack.append(candidate)
        self._switch_turn()
        self._record_position()
        return candidate

    def undo(self) -> None:
        if not self.move_stack:
            return
        self._decrement_position()
        self.board.undo()
        self.move_stack.pop()
        self._switch_turn()

    def in_check(self, color: Optional[str] = None) -> bool:
        target = color or self.turn
        return self.board.in_check(target)

    def is_checkmate(self, color: Optional[str] = None) -> bool:
        target = color or self.turn
        if not self.board.in_check(target):
            return False
        return len(self.board.generate_legal_moves(target)) == 0

    def is_stalemate(self, color: Optional[str] = None) -> bool:
        target = color or self.turn
        if self.board.in_check(target):
            return False
        return len(self.board.generate_legal_moves(target)) == 0

    def is_over(self) -> bool:
        """Return True when the current player has no legal moves."""

        return (
            self.is_checkmate(self.turn)
            or self.is_stalemate(self.turn)
            or self.is_fifty_move_draw()
            or self.is_threefold_repetition()
        )

    def game_status(self) -> str:
        if self.is_checkmate(self.turn):
            return f"{self.turn} in checkmate"
        if self.is_stalemate(self.turn):
            return "stalemate"
        if self.is_fifty_move_draw():
            return "draw by fifty-move rule"
        if self.is_threefold_repetition():
            return "draw by repetition"
        if self.in_check(self.turn):
            return f"{self.turn} in check"
        return "ongoing"

    def piece_at(self, square: str) -> Optional[Piece]:
        return self.board.get_piece(self.board.algebraic_to_square(square))

    def is_fifty_move_draw(self) -> bool:
        return self.board.is_fifty_move_draw()

    def is_threefold_repetition(self) -> bool:
        return self.position_counts[self._position_key()] >= 3
