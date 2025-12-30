"""Simple minimax AI with alpha-beta pruning for the chess app."""

from __future__ import annotations

from typing import Iterable, Optional

from chess_engine.board import Board, Color, Move, Piece

PieceValue = {
    "P": 1,
    "N": 3,
    "B": 3,
    "R": 5,
    "Q": 9,
    "K": 0,
}


def _material_score(board: Board) -> float:
    score = 0.0
    for r in range(8):
        for c in range(8):
            piece = board.board[r][c]
            if not piece:
                continue
            value = PieceValue.get(piece.kind, 0)
            score += value if piece.color == "white" else -value
    return score


def _mobility_score(board: Board) -> float:
    white_moves = len(board.generate_legal_moves("white"))
    black_moves = len(board.generate_legal_moves("black"))
    return 0.1 * (white_moves - black_moves)


def _captured_piece(board: Board, move: Move) -> Optional[Piece]:
    if move.is_en_passant:
        return board.get_piece((move.start[0], move.end[1]))
    return board.get_piece(move.end)


def _move_order_score(board: Board, move: Move) -> tuple[int, int]:
    captured = _captured_piece(board, move)
    mover = board.get_piece(move.start)
    captured_value = PieceValue.get(captured.kind, 0) if captured else 0
    mover_value = PieceValue.get(mover.kind, 0) if mover else 0
    capture_score = captured_value * 10 - mover_value if captured else 0
    promotion_bonus = PieceValue.get(move.promotion, 0) if move.promotion else 0
    return (1 if captured else 0, capture_score + promotion_bonus)


def evaluate_board(board: Board) -> float:
    """Evaluate the board using material balance and mobility."""

    return _material_score(board) + _mobility_score(board)


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
    max_nodes: Optional[int],
    node_counter: dict[str, int],
) -> float:
    """Extend leaf searches by only exploring forcing moves (captures/checks)."""

    node_counter["count"] += 1
    if max_nodes is not None and node_counter["count"] > max_nodes:
        base_score = evaluate_board(board)
        return base_score if maximizing_color == "white" else -base_score

    terminal = _terminal_score(board, current_color, maximizing_color)
    if terminal is not None:
        return terminal

    stand_pat = evaluate_board(board)
    stand_pat = stand_pat if maximizing_color == "white" else -stand_pat

    maximizing = current_color == maximizing_color
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
        if _captured_piece(board, move):
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
            max_nodes,
            node_counter,
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
) -> float:
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
            max_nodes,
            node_counter,
        )

    legal_moves = sorted(
        board.generate_legal_moves(current_color),
        key=lambda move: _move_order_score(board, move),
        reverse=True,
    )
    if not legal_moves:
        terminal_score = _terminal_score(board, current_color, maximizing_color)
        return terminal_score if terminal_score is not None else 0.0

    maximizing = current_color == maximizing_color
    next_color: Color = "black" if current_color == "white" else "white"

    if maximizing:
        value = float("-inf")
        for move in legal_moves:
            board.apply_move(move)
            value = max(
                value,
                _minimax(
                    board,
                    depth - 1,
                    next_color,
                    maximizing_color,
                    alpha,
                    beta,
                    max_nodes,
                    node_counter,
                ),
            )
            board.undo()
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value

    value = float("inf")
    for move in legal_moves:
        board.apply_move(move)
        value = min(
            value,
            _minimax(
                board,
                depth - 1,
                next_color,
                maximizing_color,
                alpha,
                beta,
                max_nodes,
                node_counter,
            ),
        )
        board.undo()
        beta = min(beta, value)
        if beta <= alpha:
            break
    return value


def choose_move(
    board: Board, depth: int, color: Color, max_nodes: Optional[int] = None
) -> Optional[Move]:
    """Return the best move for ``color`` using minimax with alpha-beta pruning.

    ``max_nodes`` can be provided to limit the total number of explored nodes,
    offering a deterministic cap on the AI thinking time. When the search depth
    is exhausted, a quiescence phase explores only forcing moves (captures or
    moves that give check) ordered by the capture heuristic to smooth tactical
    swings before returning an evaluation.
    """

    legal_moves = sorted(
        board.generate_legal_moves(color),
        key=lambda move: _move_order_score(board, move),
        reverse=True,
    )
    if not legal_moves:
        return None

    best_move: Optional[Move] = None
    best_score = float("-inf")
    next_color: Color = "black" if color == "white" else "white"
    node_counter = {"count": 0}

    for move in legal_moves:
        board.apply_move(move)
        score = _minimax(
            board,
            depth - 1,
            next_color,
            color,
            float("-inf"),
            float("inf"),
            max_nodes,
            node_counter,
        )
        board.undo()
        if best_move is None or score > best_score:
            best_score = score
            best_move = move

    return best_move
