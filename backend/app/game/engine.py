"""Pure Wordle game rules and state transitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Feedback(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    GRAY = "gray"


class GameStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    WON = "won"
    LOST = "lost"


class GameErrorCode(str, Enum):
    INVALID_GUESS = "invalid_guess"
    NOT_IN_DICTIONARY = "not_in_dictionary"
    DUPLICATE_GUESS = "duplicate_guess"
    GAME_OVER = "game_over"


class GameError(Exception):
    def __init__(self, code: GameErrorCode, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


WORD_LENGTH = 5
MAX_GUESSES = 6


def score_guess(answer: str, guess: str) -> list[Feedback]:
    """Two-pass scorer: exact matches first, then yellows from remaining counts."""
    answer = answer.lower()
    guess = guess.lower()
    if len(answer) != WORD_LENGTH or len(guess) != WORD_LENGTH:
        raise ValueError("answer and guess must be 5 letters")

    result: list[Feedback | None] = [None] * WORD_LENGTH
    remaining: dict[str, int] = {}

    for i, (a, g) in enumerate(zip(answer, guess, strict=True)):
        if a == g:
            result[i] = Feedback.GREEN
        else:
            remaining[a] = remaining.get(a, 0) + 1

    for i, g in enumerate(guess):
        if result[i] is not None:
            continue
        if remaining.get(g, 0) > 0:
            result[i] = Feedback.YELLOW
            remaining[g] -= 1
        else:
            result[i] = Feedback.GRAY

    return [mark for mark in result if mark is not None]


@dataclass
class GameState:
    answer: str
    guesses: list[str] = field(default_factory=list)
    feedbacks: list[list[Feedback]] = field(default_factory=list)
    status: GameStatus = GameStatus.IN_PROGRESS

    @property
    def remaining_guesses(self) -> int:
        return MAX_GUESSES - len(self.guesses)


def public_view(state: GameState, game_id: str) -> dict:
    """Board visible to clients — never includes the answer."""
    return {
        "game_id": game_id,
        "status": state.status.value,
        "remaining_guesses": state.remaining_guesses,
        "board": [
            {
                "guess": guess,
                "feedback": [mark.value for mark in feedback],
            }
            for guess, feedback in zip(state.guesses, state.feedbacks, strict=True)
        ],
    }


def apply_guess(state: GameState, guess: str, allowed: set[str]) -> GameState:
    """Validate and apply a guess. Raises GameError without mutating on failure."""
    if state.status != GameStatus.IN_PROGRESS:
        raise GameError(GameErrorCode.GAME_OVER, "Game is finished")

    normalized = guess.strip().lower()
    if len(normalized) != WORD_LENGTH or not normalized.isalpha():
        raise GameError(GameErrorCode.INVALID_GUESS, "Guess must be exactly 5 letters")

    if normalized not in allowed:
        raise GameError(GameErrorCode.NOT_IN_DICTIONARY, "Not in word list")

    if normalized in state.guesses:
        raise GameError(GameErrorCode.DUPLICATE_GUESS, "Already used")

    feedback = score_guess(state.answer, normalized)
    state.guesses.append(normalized)
    state.feedbacks.append(feedback)

    if all(mark == Feedback.GREEN for mark in feedback):
        state.status = GameStatus.WON
    elif state.remaining_guesses == 0:
        state.status = GameStatus.LOST

    return state
