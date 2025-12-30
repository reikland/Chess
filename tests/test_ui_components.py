import importlib
import sys
import types

import chess


class DummyBoard:
    def __init__(self) -> None:
        self.turn = chess.WHITE
        self._pieces = {
            chess.parse_square("e2"): chess.Piece("P", chess.WHITE),
            chess.parse_square("d2"): chess.Piece("P", chess.WHITE),
        }
        self._legal_moves = [
            chess.Move(chess.parse_square("e2"), chess.parse_square("e3")),
            chess.Move(chess.parse_square("e2"), chess.parse_square("e4")),
            chess.Move(chess.parse_square("d2"), chess.parse_square("d3")),
        ]
        self.move_stack = []

    @property
    def legal_moves(self):
        return list(self._legal_moves)

    def piece_at(self, idx: int):
        return self._pieces.get(idx)


def _install_streamlit_stub(monkeypatch, session_state: dict) -> types.ModuleType:
    stub = types.ModuleType("streamlit")
    stub.session_state = session_state
    stub.toast = lambda *args, **kwargs: None
    stub.caption = lambda *args, **kwargs: None
    stub.subheader = lambda *args, **kwargs: None
    stub.container = lambda *args, **kwargs: None
    stub.columns = lambda *args, **kwargs: []
    stub.form_submit_button = lambda *args, **kwargs: False
    monkeypatch.setitem(sys.modules, "streamlit", stub)
    return stub


def test_switch_piece_selection_updates_highlights(monkeypatch):
    session_state = {
        "game": {
            "board": DummyBoard(),
            "selected_square": None,
            "legal_moves": [],
            "pending_promotion": None,
            "history": [],
            "undone_moves": [],
        },
        "messages": [],
    }

    _install_streamlit_stub(monkeypatch, session_state)
    components = importlib.import_module("ui.components")
    importlib.reload(components)
    monkeypatch.setattr(components.st, "session_state", session_state)

    components.on_square_click("e2")

    assert session_state["game"]["selected_square"] == "e2"
    first_selection_moves = session_state["game"]["legal_moves"]
    assert first_selection_moves

    components.on_square_click("d2")

    assert session_state["game"]["selected_square"] == "d2"
    assert session_state["game"]["legal_moves"]
    assert session_state.get("messages") == []
