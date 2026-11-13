"""Tests for deterministic frequency solver."""

from backend.app.game.engine import GameState, apply_guess
from backend.app.solvers.frequency import FrequencySolver


def test_solver_returns_legal_non_repeat() -> None:
    answers = ("crane", "slate", "plant")
    allowed = set(answers) | {"about", "audio"}
    state = GameState(answer="crane")
    solver = FrequencySolver()
    guess = solver.suggest(state, allowed, answers)
    assert guess in allowed
    apply_guess(state, guess, allowed)
    guess2 = solver.suggest(state, allowed, answers)
    assert guess2 != guess
    assert guess2 in allowed


def test_solver_deterministic() -> None:
    answers = ("crane", "slate", "plant", "about")
    allowed = set(answers)
    state = GameState(answer="crane")
    solver = FrequencySolver()
    a = solver.suggest(state, allowed, answers)
    b = solver.suggest(state, allowed, answers)
    assert a == b
