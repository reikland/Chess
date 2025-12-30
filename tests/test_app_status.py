import tkinter as tk

import pytest

from app import ChessApp
from chess_engine.game import Game


@pytest.fixture
def app_instance():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter nécessite un affichage disponible pour ces tests.")
    root.withdraw()
    app = ChessApp(root)
    yield app
    root.destroy()


def test_illegal_move_keeps_selection_and_message(app_instance):
    app = app_instance
    size = app.square_size

    select_event = type("Event", (), {"x": 4 * size + 1, "y": 6 * size + 1})
    app.on_click(select_event)

    illegal_event = type("Event", (), {"x": 4 * size + 1, "y": 3 * size + 1})
    app.on_click(illegal_event)

    assert app.selected == (6, 4)
    assert app.status_var.get().startswith("Coup refusé : mouvement illégal")


def test_ai_status_indicator(monkeypatch, app_instance):
    app = app_instance
    app.mode_var.set("Humain vs IA")
    app.ai_color_var.set("Blanc")

    status_updates = []

    def fake_choose_move(*args, **kwargs):
        status_updates.append(app.status_var.get())
        return None

    monkeypatch.setattr("app.choose_move", fake_choose_move)

    app.play_ai_move()

    assert status_updates[0] == "L'IA réfléchit..."
    assert app.status_var.get() == "Aucun coup disponible pour l'IA."


def test_status_text_includes_repetition_draw(app_instance):
    app = app_instance
    game = Game()

    moves = [
        ("g1", "f3"),
        ("g8", "f6"),
        ("f3", "g1"),
        ("f6", "g8"),
        ("g1", "f3"),
        ("g8", "f6"),
        ("f3", "g1"),
        ("f6", "g8"),
    ]
    for start, end in moves:
        game.make_move(start, end)

    app.game = game
    app.status_var.set(app._status_text())

    assert app.status_var.get() == "Partie nulle par répétition."


def test_click_clears_selection_when_game_over(app_instance):
    app = app_instance
    game = Game()

    moves = [
        ("g1", "f3"),
        ("g8", "f6"),
        ("f3", "g1"),
        ("f6", "g8"),
        ("g1", "f3"),
        ("g8", "f6"),
        ("f3", "g1"),
        ("f6", "g8"),
    ]
    for start, end in moves:
        game.make_move(start, end)

    app.game = game
    app.selected = (0, 0)

    event = type("Event", (), {"x": 1, "y": 1})
    app.on_click(event)

    assert app.selected is None
    assert "Partie nulle" in app.status_var.get()
