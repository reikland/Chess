import math

import pytest

from chess_engine.board import Move
from chess_engine.transposition import (
    EXACT,
    LOWERBOUND,
    UPPERBOUND,
    TranspositionTable,
    probe,
    store,
)


def test_store_and_probe_exact_entry():
    table = TranspositionTable(size=8, bucket_size=2)
    key = 42
    move = Move((0, 0), (0, 1))

    store(table, key, depth=3, score=1.5, flag=EXACT, best_move=move)
    hit = probe(table, key, depth=2, alpha=-math.inf, beta=math.inf)

    assert hit is not None
    assert hit.score == pytest.approx(1.5)
    assert hit.best_move == move


def test_collision_prefers_deeper_entry():
    table = TranspositionTable(size=1, bucket_size=1)
    primary_key = 1
    colliding_key = 1 + table.size  # Same index as ``primary_key``

    store(table, primary_key, depth=4, score=2.0, flag=EXACT, best_move=None)
    store(table, colliding_key, depth=2, score=-1.0, flag=EXACT, best_move=None)

    hit_primary = probe(table, primary_key, depth=1, alpha=-math.inf, beta=math.inf)
    hit_collision = probe(table, colliding_key, depth=1, alpha=-math.inf, beta=math.inf)

    assert hit_primary is not None
    assert hit_primary.score == pytest.approx(2.0)
    assert hit_collision is None


def test_update_replaces_shallower_entry():
    table = TranspositionTable(size=4, bucket_size=2)
    key = 99

    store(table, key, depth=1, score=0.5, flag=LOWERBOUND, best_move=None)
    store(table, key, depth=3, score=-0.75, flag=EXACT, best_move=None)

    hit = probe(table, key, depth=2, alpha=-2.0, beta=2.0)
    assert hit is not None
    assert hit.flag == EXACT
    assert hit.score == pytest.approx(-0.75)


def test_probe_obeys_bounds_and_depth():
    table = TranspositionTable(size=8)
    key = 7

    store(table, key, depth=2, score=5.0, flag=LOWERBOUND, best_move=None)

    # Depth requirement not met
    assert probe(table, key, depth=3, alpha=0.0, beta=10.0) is None
    # Bound not tight enough
    assert probe(table, key, depth=2, alpha=4.0, beta=10.0) is None
    # Cutoff triggered
    hit = probe(table, key, depth=2, alpha=0.0, beta=4.5)
    assert hit is not None
    assert hit.score == pytest.approx(5.0)
