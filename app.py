import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple

from chess_engine.board import Board
from chess_engine.game import Game

Square = Tuple[int, int]


PIECE_UNICODE = {
    ("white", "K"): "♔",
    ("white", "Q"): "♕",
    ("white", "R"): "♖",
    ("white", "B"): "♗",
    ("white", "N"): "♘",
    ("white", "P"): "♙",
    ("black", "K"): "♚",
    ("black", "Q"): "♛",
    ("black", "R"): "♜",
    ("black", "B"): "♝",
    ("black", "N"): "♞",
    ("black", "P"): "♟",
}


class ChessApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Échecs Tkinter")
        self.square_size = 80

        self.game = Game()
        self.selected: Optional[Square] = None
        self.last_move: Optional[Tuple[Square, Square]] = None

        self.status_var = tk.StringVar(value=self._status_text())

        self._build_ui()
        self.draw_board()

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=10)
        top.pack()

        btn_reset = ttk.Button(top, text="Nouvelle partie", command=self.reset_game)
        btn_reset.grid(row=0, column=0, padx=5)

        btn_undo = ttk.Button(top, text="Annuler", command=self.undo_move)
        btn_undo.grid(row=0, column=1, padx=5)

        self.status_label = ttk.Label(top, textvariable=self.status_var, font=("Arial", 12))
        self.status_label.grid(row=0, column=2, padx=10)

        self.canvas = tk.Canvas(
            self.root,
            width=self.square_size * 8,
            height=self.square_size * 8,
            highlightthickness=0,
        )
        self.canvas.pack(padx=10, pady=10)
        self.canvas.bind("<Button-1>", self.on_click)

    def reset_game(self) -> None:
        self.game = Game()
        self.selected = None
        self.last_move = None
        self.status_var.set(self._status_text())
        self.draw_board()

    def undo_move(self) -> None:
        self.game.undo()
        self.selected = None
        if self.game.move_stack:
            last = self.game.move_stack[-1]
            self.last_move = (last.start, last.end)
        else:
            self.last_move = None
        self.status_var.set(self._status_text())
        self.draw_board()

    def _status_text(self) -> str:
        status = self.game.game_status()
        turn = "Blanc" if self.game.turn == "white" else "Noir"
        if status == "ongoing":
            return f"Au tour de {turn}. Sélectionnez une pièce à déplacer."
        if "checkmate" in status:
            winner = "Noir" if self.game.turn == "white" else "Blanc"
            return f"Échec et mat ! {winner} gagne."
        if status == "stalemate":
            return "Pat. Partie nulle."
        if "check" in status:
            return f"{turn} est en échec."
        return status

    def on_click(self, event: tk.Event) -> None:
        row = event.y // self.square_size
        col = event.x // self.square_size
        if not (0 <= row < 8 and 0 <= col < 8):
            return
        clicked = (int(row), int(col))

        piece = self.game.board.get_piece(clicked)
        if self.selected is None:
            if piece and piece.color == self.game.turn:
                self.selected = clicked
                self.status_var.set("Choisissez la case de destination.")
            else:
                self.status_var.set("Sélectionnez une pièce de votre couleur.")
            self.draw_board()
            return

        start = self.selected
        end = clicked
        if start == end:
            self.selected = None
            self.status_var.set(self._status_text())
            self.draw_board()
            return

        start_alg = Board.square_to_algebraic(start)
        end_alg = Board.square_to_algebraic(end)

        moving_piece = self.game.board.get_piece(start)
        promotion: Optional[str] = None
        if moving_piece and moving_piece.kind == "P":
            if (moving_piece.color == "white" and end[0] == 0) or (
                moving_piece.color == "black" and end[0] == 7
            ):
                promotion = "Q"

        try:
            move = self.game.make_move(start_alg, end_alg, promotion=promotion)
            self.last_move = (move.start, move.end)
            self.status_var.set(self._status_text())
        except ValueError:
            self.status_var.set("Coup illégal. Réessayez.")
        finally:
            self.selected = None
            self.draw_board()

    def draw_board(self) -> None:
        self.canvas.delete("all")
        light_color = "#f0d9b5"
        dark_color = "#b58863"
        highlight = "#f4f06f"
        last_move_color = "#9dd9d2"

        for r in range(8):
            for c in range(8):
                x1 = c * self.square_size
                y1 = r * self.square_size
                x2 = x1 + self.square_size
                y2 = y1 + self.square_size

                base_color = light_color if (r + c) % 2 == 0 else dark_color
                fill_color = base_color

                if self.last_move and ((r, c) == self.last_move[0] or (r, c) == self.last_move[1]):
                    fill_color = last_move_color
                if self.selected == (r, c):
                    fill_color = highlight

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill_color, outline="")

                piece = self.game.board.get_piece((r, c))
                if piece:
                    symbol = PIECE_UNICODE[(piece.color, piece.kind)]
                    self.canvas.create_text(
                        x1 + self.square_size / 2,
                        y1 + self.square_size / 2,
                        text=symbol,
                        font=("Arial", 36),
                    )


def main() -> None:
    root = tk.Tk()
    ChessApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
