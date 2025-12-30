import tkinter as tk

import pytest

from app import ChessApp


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
