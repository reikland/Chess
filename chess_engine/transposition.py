from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from chess_engine.board import Board, Color, Move, _iter_bits

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
    age: int = 0


class TranspositionTable:
    def __init__(self, size: int = 1 << 18, bucket_size: int = 4) -> None:
        self.size = size
        self.bucket_size = bucket_size
        self._table: list[list[TTEntry]] = [[] for _ in range(size)]
        self._counter = 0

    def _index(self, key: int) -> int:
        return key % self.size

    def probe(self, key: int) -> Optional[TTEntry]:
        bucket = self._table[self._index(key)]
        for entry in bucket:
            if entry.key == key:
                return entry
        return None

    def store(self, entry: TTEntry) -> None:
        index = self._index(entry.key)
        bucket = self._table[index]
        entry.age = self._counter
        self._counter += 1

        for idx, existing in enumerate(bucket):
            if existing.key == entry.key:
                if entry.depth >= existing.depth:
                    bucket[idx] = entry
                return

        if len(bucket) < self.bucket_size:
            bucket.append(entry)
            return

        replacement_idx = min(
            range(len(bucket)),
            key=lambda i: (bucket[i].depth, bucket[i].age),
        )
        weakest = bucket[replacement_idx]
        if entry.depth < weakest.depth:
            return
        bucket[replacement_idx] = entry


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
    piece_bitboards = getattr(board, "piece_bitboards", None)
    if piece_bitboards:
        for color, per_piece in piece_bitboards.items():
            for kind, bitboard in per_piece.items():
                for idx in _iter_bits(bitboard):
                    h ^= _PIECE_KEYS[(color, kind)][idx]
    else:
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
