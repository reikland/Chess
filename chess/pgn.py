"""Minimal PGN helpers compatible with the local chess stub."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, TextIO

from . import Board, Move


class StringExporter:
    def __init__(self, headers: bool = True, variations: bool = False, comments: bool = False):
        self.headers = headers
        self.variations = variations
        self.comments = comments

    def __call__(self, game: "Game") -> str:
        return game.to_pgn()


@dataclass
class GameNode:
    move: Optional[Move] = None
    parent: Optional["GameNode"] = None
    children: List["GameNode"] = None

    def __post_init__(self) -> None:
        if self.children is None:
            self.children = []

    def add_variation(self, move: Move) -> "GameNode":
        node = GameNode(move=move, parent=self)
        self.children.append(node)
        return node


class Game:
    def __init__(self) -> None:
        self.root = GameNode()
        self.headers: dict[str, str] = {}

    @classmethod
    def from_board(cls, board: Board) -> "Game":
        game = cls()
        node = game.root
        for move in board.move_stack:
            node = node.add_variation(move)
        return game

    def accept(self, exporter: StringExporter) -> str:
        return exporter(self)

    def mainline_moves(self) -> Iterable[Move]:
        node = self.root
        while node.children:
            node = node.children[0]
            if node.move:
                yield node.move

    def board(self) -> Board:
        board = Board()
        for move in self.mainline_moves():
            board.push(move)
        return board

    def to_pgn(self) -> str:
        moves = list(self.mainline_moves())
        pgn_moves: List[str] = []
        for idx, move in enumerate(moves, start=1):
            if idx % 2 == 1:
                pgn_moves.append(f"{(idx + 1)//2}.")
            pgn_moves.append(move.uci())
        return " ".join(pgn_moves)


def read_game(stream: TextIO) -> Optional[Game]:
    content = stream.read().strip()
    if not content:
        return None
    tokens = content.replace("\n", " ").split()
    moves: List[str] = [tok for tok in tokens if not tok.endswith(".")]
    game = Game()
    node = game.root
    for token in moves:
        node = node.add_variation(Move.from_uci(token))
    return game
