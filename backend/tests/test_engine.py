"""Tests for Wordle scoring and state transitions."""

import pytest

from backend.app.game.engine import (
    Feedback,
    GameError,
    GameErrorCode,
    GameState,
    GameStatus,
    apply_guess,
    public_view,
    score_guess,
)


def test_score_guess_all_green() -> None:
    assert score_guess("crane", "crane") == [Feedback.GREEN] * 5


def test_score_guess_duplicate_letters() -> None:
    # answer abbey vs guess bubba — greens first, then remaining counts for yellows
    assert score_guess("abbey", "bubba") == [
        Feedback.YELLOW,
        Feedback.GRAY,
        Feedback.GREEN,
        Feedback.GRAY,
        Feedback.YELLOW,
    ]


def test_score_guess_mixed_colors() -> None:
    # plant vs train → t yellow, r gray, a green, i gray, n yellow
    assert score_guess("plant", "train") == [
        Feedback.YELLOW,
        Feedback.GRAY,
        Feedback.GREEN,
        Feedback.GRAY,
        Feedback.YELLOW,
    ]


def test_apply_guess_win_and_public_view_hides_answer() -> None:
    state = GameState(answer="crane")
    allowed = {"crane", "slate"}
    apply_guess(state, "crane", allowed)
    assert state.status == GameStatus.WON
    view = public_view(state, "g1")
    assert "answer" not in view
    assert view["status"] == "won"
    assert view["board"][0]["guess"] == "crane"


def test_apply_guess_rejects_invalid_and_keeps_state() -> None:
    state = GameState(answer="crane")
    allowed = {"crane", "slate"}
    with pytest.raises(GameError) as exc:
        apply_guess(state, "zzzzz", allowed)
    assert exc.value.code == GameErrorCode.NOT_IN_DICTIONARY
    assert state.guesses == []


def test_apply_guess_rejects_duplicate() -> None:
    state = GameState(answer="crane")
    allowed = {"crane", "slate"}
    apply_guess(state, "slate", allowed)
    with pytest.raises(GameError) as exc:
        apply_guess(state, "slate", allowed)
    assert exc.value.code == GameErrorCode.DUPLICATE_GUESS


def test_loss_after_six_guesses() -> None:
    state = GameState(answer="crane")
    guesses = ["about", "above", "abuse", "actor", "acute", "admit"]
    allowed = set(guesses) | {"crane"}
    for guess in guesses:
        apply_guess(state, guess, allowed)
    assert state.status == GameStatus.LOST
    assert state.remaining_guesses == 0
