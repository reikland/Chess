import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple

# Tkinter simple dialogs are used for promotion choices.
from tkinter import simpledialog

from chess_engine.ai import choose_move
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
        self.margin_x = 30
        self.margin_top = 30
        self.margin_bottom = 45

        self.game = Game()
        self.selected: Optional[Square] = None
        self.last_move: Optional[Tuple[Square, Square]] = None

        self.mode_var = tk.StringVar(value="Humain vs Humain")
        self.ai_color_var = tk.StringVar(value="Noir")
        self.ai_depth_var = tk.IntVar(value=2)
        self.ai_nodes_var = tk.IntVar(value=5000)
        self.ai_time_limit_var = tk.IntVar(value=2)

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

        ttk.Label(top, text="Mode :").grid(row=0, column=2, padx=5)
        mode_combo = ttk.Combobox(
            top,
            textvariable=self.mode_var,
            state="readonly",
            values=["Humain vs Humain", "Humain vs IA"],
            width=18,
        )
        mode_combo.grid(row=0, column=3, padx=5)
        mode_combo.bind("<<ComboboxSelected>>", lambda _: self.reset_game())

        ttk.Label(top, text="Couleur IA :").grid(row=0, column=4, padx=5)
        color_combo = ttk.Combobox(
            top,
            textvariable=self.ai_color_var,
            state="readonly",
            values=["Blanc", "Noir"],
            width=8,
        )
        color_combo.grid(row=0, column=5, padx=5)
        color_combo.bind("<<ComboboxSelected>>", lambda _: self.reset_game())

        ttk.Label(
            top,
            text="Profondeur IA (plus haut = réflexion plus longue) :",
        ).grid(row=0, column=6, padx=5)
        ttk.Spinbox(
            top,
            from_=1,
            to=20,
            textvariable=self.ai_depth_var,
            width=5,
        ).grid(row=0, column=7, padx=5)

        ttk.Label(top, text="s/coup :").grid(row=0, column=8, padx=5)
        ttk.Spinbox(
            top,
            from_=0,
            to=30,
            increment=1,
            textvariable=self.ai_time_limit_var,
            width=6,
        ).grid(row=0, column=9, padx=5)

        ttk.Label(top, text="Noeuds max :").grid(row=0, column=10, padx=5)
        ttk.Spinbox(
            top,
            from_=0,
            to=100000,
            increment=100,
            textvariable=self.ai_nodes_var,
            width=10,
        ).grid(row=0, column=11, padx=5)

        self.status_label = ttk.Label(
            top, textvariable=self.status_var, font=("Arial", 12)
        )
        self.status_label.grid(row=1, column=0, columnspan=12, pady=5)

        dark_color = "#b58863"
        self.canvas = tk.Canvas(
            self.root,
            width=self.square_size * 8 + self.margin_x * 2,
            height=self.square_size * 8 + self.margin_top + self.margin_bottom,
            highlightthickness=0,
            background=dark_color,
        )
        self.canvas.pack(padx=10, pady=10)
        self.canvas.bind("<Button-1>", self.on_click)

    def reset_game(self) -> None:
        self.game = Game()
        self.selected = None
        self.last_move = None
        self.status_var.set(self._status_text())
        self.draw_board()
        if self.mode_var.get() == "Humain vs IA" and self.ai_color_var.get() == "Blanc":
            self.root.after(50, self.play_ai_move)

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
        if status in ("draw by fifty-move rule", "partie nulle par règle des 50 coups"):
            return "Partie nulle par règle des 50 coups."
        if status in ("draw by repetition", "partie nulle par répétition"):
            return "Partie nulle par répétition."
        if "check" in status:
            return f"{turn} est en échec."
        return status

    def _choose_promotion(self, color: str) -> str | None:
        """Prompt the user for a promotion piece.

        Returning ``None`` when the input is invalid allows the caller to abort the
        move so the player can retry without forcing an unintended promotion.
        """

        choices = {"Dame": "Q", "Tour": "R", "Fou": "B", "Cavalier": "N"}
        selection = simpledialog.askstring(
            "Promotion",
            "Choisissez la pièce de promotion :",
            parent=self.root,
            initialvalue="Dame",
        )

        if selection:
            selection = selection.strip().capitalize()

        return choices.get(selection)

    def on_click(self, event: tk.Event) -> None:
        row = (event.y - self.margin_top) // self.square_size
        col = (event.x - self.margin_x) // self.square_size
        if not (0 <= row < 8 and 0 <= col < 8):
            return
        if self.game.is_over():
            self.status_var.set(self._status_text())
            self.selected = None
            self.draw_board()
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
                promotion = self._choose_promotion(moving_piece.color)
                if promotion is None:
                    self.status_var.set(
                        "Promotion annulée : entrée invalide. Choisissez une pièce."
                    )
                    self.draw_board()
                    return

        human_played = False
        move_refused = False
        try:
            move = self.game.make_move(start_alg, end_alg, promotion=promotion)
            self.last_move = (move.start, move.end)
            self.status_var.set(self._status_text())
            human_played = True
        except ValueError:
            self.status_var.set(
                "Coup refusé : mouvement illégal. Choisissez une destination valide"
                " ou sélectionnez une autre pièce."
            )
            move_refused = True
            self.selected = start
        finally:
            if not move_refused:
                self.selected = None
            self.draw_board()
            if human_played and self.mode_var.get() == "Humain vs IA":
                self.root.after(50, self.play_ai_move)

    def _ai_color(self) -> str:
        return "white" if self.ai_color_var.get() == "Blanc" else "black"

    def play_ai_move(self) -> None:
        if self.mode_var.get() != "Humain vs IA":
            return

        if self.game.is_over():
            return

        if self.game.turn != self._ai_color():
            return

        self.status_var.set("L'IA réfléchit...")
        self.draw_board()
        self.root.update_idletasks()

        max_nodes = self.ai_nodes_var.get()
        time_limit_s = self.ai_time_limit_var.get()

        max_nodes = max_nodes if max_nodes > 0 else None
        time_limit_ms = (time_limit_s * 1000) if time_limit_s > 0 else None

        if max_nodes and time_limit_ms:
            if time_limit_s >= max_nodes:
                max_nodes = None
            else:
                time_limit_ms = None

        move = choose_move(
            self.game.board,
            self.ai_depth_var.get(),
            color=self._ai_color(),
            max_nodes=max_nodes,
            time_limit_ms=time_limit_ms,
        )
        if move is None:
            self.status_var.set("Aucun coup disponible pour l'IA.")
            return

        promotion = move.promotion
        start_alg = Board.square_to_algebraic(move.start)
        end_alg = Board.square_to_algebraic(move.end)

        try:
            applied = self.game.make_move(start_alg, end_alg, promotion=promotion)
            self.last_move = (applied.start, applied.end)
            self.status_var.set(self._status_text())
        except ValueError:
            self.status_var.set("L'IA a proposé un coup invalide.")
        finally:
            self.draw_board()

    def draw_board(self) -> None:
        self.canvas.delete("all")
        light_color = "#f0d9b5"
        dark_color = "#b58863"
        highlight = "#f4f06f"
        last_move_from = "#8ecae6"
        last_move_to = "#ffb703"
        origin_x = self.margin_x
        origin_y = self.margin_top

        board_width = self.square_size * 8
        board_height = self.square_size * 8

        self.canvas.create_rectangle(
            origin_x,
            origin_y,
            origin_x + board_width,
            origin_y + board_height,
            fill=dark_color,
            outline="",
        )

        for r in range(8):
            for c in range(8):
                x1 = origin_x + c * self.square_size
                y1 = origin_y + r * self.square_size
                x2 = x1 + self.square_size
                y2 = y1 + self.square_size

                base_color = light_color if (r + c) % 2 == 0 else dark_color
                fill_color = base_color

                if self.last_move and (r, c) == self.last_move[0]:
                    fill_color = last_move_from
                if self.last_move and (r, c) == self.last_move[1]:
                    fill_color = last_move_to
                if self.selected == (r, c):
                    fill_color = highlight

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill_color, outline="")

                piece = self.game.board.get_piece((r, c))
                if piece:
                    symbol = PIECE_UNICODE[(piece.color, piece.kind)]
                    fill_color = "#111111" if piece.color == "black" else "#f6f6f6"
                    shadow_color = "#f6f6f6" if piece.color == "black" else "#111111"
                    cx = x1 + self.square_size / 2
                    cy = y1 + self.square_size / 2
                    # Shadow to increase contrast on all backgrounds
                    self.canvas.create_text(
                        cx + 1,
                        cy + 1,
                        text=symbol,
                        font=("Arial", 36, "bold"),
                        fill=shadow_color,
                    )
                    self.canvas.create_text(
                        cx,
                        cy,
                        text=symbol,
                        font=("Arial", 36, "bold"),
                        fill=fill_color,
                    )

        # Force a canvas refresh so that special pawn moves such as en-passant
        # immediately reflect on screen instead of waiting for the Tk event
        # loop to catch up with the updated board state.
        self.canvas.update_idletasks()

        label_shadow = "#111111"
        label_fill = "#f6f6f6"
        label_offset = 1
        file_labels = ["a", "b", "c", "d", "e", "f", "g", "h"]
        for r in range(8):
            rank = 8 - r
            cy = origin_y + r * self.square_size + self.square_size / 2
            x = origin_x - self.margin_x / 2
            self.canvas.create_text(
                x + label_offset,
                cy + label_offset,
                text=str(rank),
                font=("Arial", 14, "bold"),
                fill=label_shadow,
            )
            self.canvas.create_text(
                x,
                cy,
                text=str(rank),
                font=("Arial", 14, "bold"),
                fill=label_fill,
            )

        letter_y = origin_y + self.square_size * 8 + 16
        for c, file_letter in enumerate(file_labels):
            cx = origin_x + c * self.square_size + self.square_size / 2
            for y in (letter_y,):
                self.canvas.create_text(
                    cx + label_offset,
                    y + label_offset,
                    text=file_letter,
                    font=("Arial", 14, "bold"),
                    fill=label_shadow,
                )
                self.canvas.create_text(
                    cx,
                    y,
                    text=file_letter,
                    font=("Arial", 14, "bold"),
                    fill=label_fill,
                )


def main() -> None:
    root = tk.Tk()
    ChessApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
