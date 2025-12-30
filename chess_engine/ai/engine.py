"""Simple minimax AI with alpha-beta pruning for the chess app."""

from __future__ import annotations

import time

from typing import Dict, Optional, Tuple

from chess_engine.board import Board, Color, Move, Piece
from chess_engine.evaluation import PieceValue, evaluate_board as _static_evaluation
from chess_engine.transposition import (
    EXACT,
    LOWERBOUND,
    UPPERBOUND,
    TranspositionTable,
    TTEntry,
    probe as tt_probe,
    store as tt_store,
    zobrist_hash,
)

QUIESCENCE_DEPTH = 4


def _mobility_score(board: Board) -> float:
    white_moves = len(board.generate_legal_moves("white"))
    black_moves = len(board.generate_legal_moves("black"))
    return 0.1 * (white_moves - black_moves)


def _captured_piece(board: Board, move: Move) -> Optional[Piece]:
    if move.is_en_passant:
        return board.get_piece((move.start[0], move.end[1]))
    return board.get_piece(move.end)


def _move_order_score(
    board: Board,
    move: Move,
    killer_moves: Optional[Dict[int, list[Move]]] = None,
    history_scores: Optional[Dict[Tuple, int]] = None,
    depth: int = 0,
) -> tuple[int, int, int, int]:
    captured = _captured_piece(board, move)
    mover = board.get_piece(move.start)
    captured_value = PieceValue.get(captured.kind, 0) if captured else 0
    mover_value = PieceValue.get(mover.kind, 0) if mover else 0
    capture_score = captured_value * 10 - mover_value if captured else 0
    promotion_bonus = PieceValue.get(move.promotion, 0) if move.promotion else 0

    killer_bonus = 0
    if killer_moves:
        killers = killer_moves.get(depth, [])
        killer_bonus = 1 if move in killers else 0

    history_score = 0
    if history_scores is not None:
        history_key = (move.start, move.end, move.promotion)
        history_score = history_scores.get(history_key, 0)

    return (
        1 if captured else 0,
        capture_score + promotion_bonus,
        killer_bonus,
        history_score,
    )


def evaluate_board(board: Board) -> float:
    """Evaluate the board using tapered material/positional features and mobility."""

    return _static_evaluation(board) + _mobility_score(board)


def _terminal_score(board: Board, player: Color, maximizing_color: Color) -> Optional[float]:
    legal_moves = board.generate_legal_moves(player)
    if legal_moves:
        return None
    if board.in_check(player):
        return float("-inf") if player == maximizing_color else float("inf")
    return 0.0


def _quiescence(
    board: Board,
    current_color: Color,
    maximizing_color: Color,
    alpha: float,
    beta: float,
    q_depth: int,
    max_nodes: Optional[int],
    node_counter: dict[str, int],
    transposition_table: Optional[TranspositionTable],
    deadline: Optional[float],
) -> float:
    """Extend leaf searches by exploring forcing moves (captures, promotions, checks).

    ``q_depth`` limits how far the quiescence search can extend to avoid
    exponential blowups in tactical positions.
    """

    if deadline is not None and time.time() >= deadline:
        base_score = evaluate_board(board)
        return base_score if maximizing_color == "white" else -base_score

    node_counter["count"] += 1
    if max_nodes is not None and node_counter["count"] > max_nodes:
        base_score = evaluate_board(board)
        return base_score if maximizing_color == "white" else -base_score

    terminal = _terminal_score(board, current_color, maximizing_color)
    if terminal is not None:
        return terminal

    stand_pat = evaluate_board(board)
    stand_pat = stand_pat if maximizing_color == "white" else -stand_pat

    if q_depth <= 0:
        return stand_pat

    tt_entry: Optional[TTEntry] = None
    tt_key: Optional[int] = None
    if transposition_table:
        tt_key = zobrist_hash(board, current_color)
        tt_entry = tt_probe(transposition_table, tt_key, q_depth, alpha, beta)
        if tt_entry:
            return tt_entry.score

    maximizing = current_color == maximizing_color
    alpha_original, beta_original = alpha, beta
    if maximizing:
        value = stand_pat
        if value >= beta:
            return value
        alpha = max(alpha, value)
    else:
        value = stand_pat
        if value <= alpha:
            return value
        beta = min(beta, value)

    next_color: Color = "black" if current_color == "white" else "white"

    noisy_moves: list[Move] = []
    for move in board.generate_legal_moves(current_color):
        if _captured_piece(board, move) or move.promotion:
            noisy_moves.append(move)
            continue
        board.apply_move(move)
        gives_check = board.in_check(next_color)
        board.undo()
        if gives_check:
            noisy_moves.append(move)

    if not noisy_moves:
        return value

    for move in sorted(noisy_moves, key=lambda m: _move_order_score(board, m), reverse=True):
        board.apply_move(move)
        score = _quiescence(
            board,
            next_color,
            maximizing_color,
            alpha,
            beta,
            q_depth - 1,
            max_nodes,
            node_counter,
            transposition_table,
            deadline,
        )
        board.undo()
        if maximizing:
            value = max(value, score)
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        else:
            value = min(value, score)
            beta = min(beta, value)
            if beta <= alpha:
                break

    if transposition_table and tt_key is not None:
        flag = EXACT
        if value <= alpha_original:
            flag = UPPERBOUND
        elif value >= beta_original:
            flag = LOWERBOUND
        tt_store(transposition_table, tt_key, q_depth, value, flag, best_move=None)

    return value


def _minimax(
    board: Board,
    depth: int,
    current_color: Color,
    maximizing_color: Color,
    alpha: float,
    beta: float,
    max_nodes: Optional[int],
    node_counter: dict[str, int],
    transposition_table: Optional[TranspositionTable],
    killer_moves: Dict[int, list[Move]],
    history_scores: Dict[Tuple, int],
    deadline: Optional[float],
) -> float:
    if deadline is not None and time.time() >= deadline:
        base_score = evaluate_board(board)
        return base_score if maximizing_color == "white" else -base_score

    node_counter["count"] += 1
    if max_nodes is not None and node_counter["count"] > max_nodes:
        base_score = evaluate_board(board)
        return base_score if maximizing_color == "white" else -base_score

    terminal = _terminal_score(board, current_color, maximizing_color)
    if terminal is not None:
        return terminal
    if depth == 0:
        return _quiescence(
            board,
            current_color,
            maximizing_color,
            alpha,
            beta,
            QUIESCENCE_DEPTH,
            max_nodes,
            node_counter,
            transposition_table,
            deadline,
        )

    legal_moves = sorted(
        board.generate_legal_moves(current_color),
        key=lambda move: _move_order_score(
            board,
            move,
            killer_moves=killer_moves,
            history_scores=history_scores,
            depth=depth,
        ),
        reverse=True,
    )
    if not legal_moves:
        terminal_score = _terminal_score(board, current_color, maximizing_color)
        return terminal_score if terminal_score is not None else 0.0

    maximizing = current_color == maximizing_color
    next_color: Color = "black" if current_color == "white" else "white"
    best_move_found: Optional[Move] = None

    def _apply_null_move_allowed() -> bool:
        if depth < 2:
            return False
        if board.in_check(current_color):
            return False
        non_pawn = 0
        pawns = 0
        for row in board.board:
            for piece in row:
                if piece and piece.color == current_color:
                    if piece.kind == "P":
                        pawns += 1
                    elif piece.kind != "K":
                        non_pawn += 1
        return not (non_pawn == 0 and pawns <= 4)

    def _null_move_search(beta_window: float) -> Optional[float]:
        prev_en_passant = board.en_passant_square
        prev_halfmove = board.halfmove_clock
        prev_castling = board.castling_rights

        board.en_passant_square = None
        board.halfmove_clock += 1
        reduction = 2 if depth > 5 else 1
        search_depth = max(0, depth - 1 - reduction)
        score = _minimax(
            board,
            search_depth,
            next_color,
            maximizing_color,
            beta_window - 1,
            beta_window,
            max_nodes,
            node_counter,
            transposition_table,
            killer_moves,
            history_scores,
            deadline,
        )

        board.en_passant_square = prev_en_passant
        board.halfmove_clock = prev_halfmove
        board.castling_rights = prev_castling
        return score

    if _apply_null_move_allowed():
        null_score = _null_move_search(beta)
        if maximizing and null_score is not None and null_score >= beta:
            return null_score
        if not maximizing and null_score is not None and null_score <= alpha:
            return null_score

    tt_entry: Optional[TTEntry] = None
    tt_key: Optional[int] = None
    if transposition_table:
        tt_key = zobrist_hash(board, current_color)
        tt_entry = tt_probe(transposition_table, tt_key, depth, alpha, beta)
        if tt_entry:
            return tt_entry.score

    if tt_entry and tt_entry.best_move:
        for idx, move in enumerate(legal_moves):
            if move == tt_entry.best_move:
                legal_moves.insert(0, legal_moves.pop(idx))
                break

    alpha_original, beta_original = alpha, beta

    if maximizing:
        value = float("-inf")
        for idx, move in enumerate(legal_moves):
            is_capture = _captured_piece(board, move) is not None
            is_promotion = move.promotion is not None
            board.apply_move(move)
            gives_check = board.in_check(next_color)

            reduction = 0
            if (
                depth >= 3
                and idx >= 3
                and not is_capture
                and not is_promotion
                and not gives_check
            ):
                reduction = 1 if depth < 5 else 2

            search_depth = max(0, depth - 1 - reduction)
            score = _minimax(
                board,
                search_depth,
                next_color,
                maximizing_color,
                alpha,
                beta,
                max_nodes,
                node_counter,
                transposition_table,
                killer_moves,
                history_scores,
                deadline,
            )

            if reduction and score > alpha:
                score = _minimax(
                    board,
                    depth - 1,
                    next_color,
                    maximizing_color,
                    alpha,
                    beta,
                    max_nodes,
                    node_counter,
                    transposition_table,
                    killer_moves,
                    history_scores,
                    deadline,
                )

            board.undo()
            if score > value:
                value = score
                best_move_found = move
                if not is_capture:
                    history_key = (move.start, move.end, move.promotion)
                    history_scores[history_key] = history_scores.get(history_key, 0) + depth * depth
            alpha = max(alpha, value)
            if alpha >= beta:
                if not is_capture:
                    killers = killer_moves.setdefault(depth, [])
                    if move in killers:
                        killers.remove(move)
                    killers.append(move)
                    killer_moves[depth] = killers[-2:]
                break
    else:
        value = float("inf")
        for idx, move in enumerate(legal_moves):
            is_capture = _captured_piece(board, move) is not None
            is_promotion = move.promotion is not None
            board.apply_move(move)
            gives_check = board.in_check(next_color)

            reduction = 0
            if (
                depth >= 3
                and idx >= 3
                and not is_capture
                and not is_promotion
                and not gives_check
            ):
                reduction = 1 if depth < 5 else 2

            search_depth = max(0, depth - 1 - reduction)
            score = _minimax(
                board,
                search_depth,
                next_color,
                maximizing_color,
                alpha,
                beta,
                max_nodes,
                node_counter,
                transposition_table,
                killer_moves,
                history_scores,
                deadline,
            )

            if reduction and score < beta:
                score = _minimax(
                    board,
                    depth - 1,
                    next_color,
                    maximizing_color,
                    alpha,
                    beta,
                    max_nodes,
                    node_counter,
                    transposition_table,
                    killer_moves,
                    history_scores,
                    deadline,
                )

            board.undo()
            if score < value:
                value = score
                best_move_found = move
                if not is_capture:
                    history_key = (move.start, move.end, move.promotion)
                    history_scores[history_key] = history_scores.get(history_key, 0) + depth * depth
            beta = min(beta, value)
            if beta <= alpha:
                if not is_capture:
                    killers = killer_moves.setdefault(depth, [])
                    if move in killers:
                        killers.remove(move)
                    killers.append(move)
                    killer_moves[depth] = killers[-2:]
                break

    if transposition_table and tt_key is not None:
        flag = EXACT
        if value <= alpha_original:
            flag = UPPERBOUND
        elif value >= beta_original:
            flag = LOWERBOUND
        tt_store(transposition_table, tt_key, depth, value, flag, best_move_found)
    return value


def choose_move(
    board: Board,
    depth: int,
    color: Color,
    max_nodes: Optional[int] = None,
    time_limit_ms: Optional[int] = None,
    transposition_table: Optional[TranspositionTable] = None,
) -> Optional[Move]:
    """Return the best move for ``color`` using minimax with alpha-beta pruning.

    ``max_nodes`` can be provided to limit the total number of explored nodes,
    offering a deterministic cap on the AI thinking time. When the search depth
    is exhausted, a quiescence phase explores only forcing moves (captures or
    moves that give check) ordered by the capture heuristic to smooth tactical
    swings before returning an evaluation.
    ``time_limit_ms`` offers a soft wallclock budget for the iterative deepening
    search, returning the best move found so far when the timer elapses.
    """

    killer_moves: Dict[int, list[Move]] = {}
    history_scores: Dict[Tuple, int] = {}

    legal_moves = sorted(
        board.generate_legal_moves(color),
        key=lambda move: _move_order_score(
            board,
            move,
            killer_moves=killer_moves,
            history_scores=history_scores,
            depth=depth,
        ),
        reverse=True,
    )
    if not legal_moves:
        return None

    if max_nodes is not None and max_nodes < len(legal_moves):
        return legal_moves[0]

    best_move: Optional[Move] = None
    best_score = float("-inf")
    next_color: Color = "black" if color == "white" else "white"
    node_counter = {"count": 0}
    transposition_table = transposition_table or TranspositionTable()

    deadline: Optional[float] = None
    if time_limit_ms is not None and time_limit_ms > 0:
        deadline = time.time() + (time_limit_ms / 1000)

    for current_depth in range(1, depth + 1):
        depth_best_move: Optional[Move] = None
        depth_best_score = float("-inf")

        legal_moves = sorted(
            legal_moves,
            key=lambda move: _move_order_score(
                board,
                move,
                killer_moves=killer_moves,
                history_scores=history_scores,
                depth=current_depth,
            ),
            reverse=True,
        )

        for move in legal_moves:
            if max_nodes is not None and node_counter["count"] >= max_nodes:
                break
            if deadline is not None and time.time() >= deadline:
                break

            board.apply_move(move)
            score = _minimax(
                board,
                current_depth - 1,
                next_color,
                color,
                float("-inf"),
                float("inf"),
                max_nodes,
                node_counter,
                transposition_table,
                killer_moves,
                history_scores,
                deadline,
            )
            board.undo()
            if depth_best_move is None or score > depth_best_score:
                depth_best_score = score
                depth_best_move = move

        if depth_best_move is not None:
            best_move = depth_best_move
            best_score = depth_best_score
            if depth_best_move in legal_moves:
                legal_moves.remove(depth_best_move)
                legal_moves.insert(0, depth_best_move)

        if max_nodes is not None and node_counter["count"] >= max_nodes:
            break
        if deadline is not None and time.time() >= deadline:
            break

    return best_move
