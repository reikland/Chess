from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from chess_engine.board import Board, Color, Move

EXACT = "exact"
LOWERBOUND = "lower"
UPPERBOUND = "upper"


@dataclass
class TTEntry:
    key: int
    depth: int
    score: float
    flag: str
    best_move: Optional[Move]


class TranspositionTable:
    def __init__(self, size: int = 1 << 15) -> None:
        self.size = size
        self._table: list[Optional[TTEntry]] = [None for _ in range(size)]

    def _index(self, key: int) -> int:
        return key % self.size

    def probe(self, key: int) -> Optional[TTEntry]:
        entry = self._table[self._index(key)]
        if entry and entry.key == key:
            return entry
        return None

    def store(self, entry: TTEntry) -> None:
        index = self._index(entry.key)
        existing = self._table[index]
        if existing is None or entry.depth >= existing.depth or existing.key == entry.key:
            self._table[index] = entry


def _init_zobrist() -> tuple[dict[tuple[Color, str], list[int]], list[int], list[int], int]:
    rng = random.Random(1337)
    piece_keys: dict[tuple[Color, str], list[int]] = {}
    for color in ("white", "black"):
        for kind in ("K", "Q", "R", "B", "N", "P"):
            piece_keys[(color, kind)] = [rng.getrandbits(64) for _ in range(64)]

    castling_keys = [rng.getrandbits(64) for _ in range(4)]
    en_passant_keys = [rng.getrandbits(64) for _ in range(8)]
    side_to_move_key = rng.getrandbits(64)
    return piece_keys, castling_keys, en_passant_keys, side_to_move_key


_PIECE_KEYS, _CASTLING_KEYS, _EN_PASSANT_KEYS, _SIDE_TO_MOVE = _init_zobrist()


def zobrist_hash(board: Board, side_to_move: Color) -> int:
    """Return a deterministic Zobrist hash for ``board`` and the side to move."""

    h = 0
    for r in range(8):
        for c in range(8):
            piece = board.get_piece((r, c))
            if piece:
                h ^= _PIECE_KEYS[(piece.color, piece.kind)][r * 8 + c]

    for idx, right in enumerate(board.castling_rights):
        if right:
            h ^= _CASTLING_KEYS[idx]

    if board.en_passant_square:
        _, file = board.en_passant_square
        h ^= _EN_PASSANT_KEYS[file]

    if side_to_move == "white":
        h ^= _SIDE_TO_MOVE

    return h


def probe(
    table: TranspositionTable, key: int, depth: int, alpha: float, beta: float
) -> Optional[TTEntry]:
    entry = table.probe(key)
    if entry is None or entry.key != key or entry.depth < depth:
        return None

    if entry.flag == EXACT:
        return entry
    if entry.flag == LOWERBOUND and entry.score >= beta:
        return entry
    if entry.flag == UPPERBOUND and entry.score <= alpha:
        return entry
    return None


def store(
    table: TranspositionTable,
    key: int,
    depth: int,
    score: float,
    flag: str,
    best_move: Optional[Move],
) -> None:
    table.store(TTEntry(key, depth, score, flag, best_move))
