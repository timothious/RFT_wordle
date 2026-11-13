"""Episode and one-turn rollout helpers."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Callable

from backend.app.game.engine import GameState, GameStatus, MAX_GUESSES, apply_guess
from backend.app.models.contract import build_prompt
from backend.app.game.words import pick_answer


SuggestFn = Callable[[GameState], str]


@dataclass
class EpisodeResult:
    answer: str
    won: bool
    guesses: list[str]
    invalid_actions: int
    turns: int


def run_episode(
    answer: str,
    suggest: SuggestFn,
    allowed: set[str],
    *,
    max_guesses: int = MAX_GUESSES,
) -> EpisodeResult:
    state = GameState(answer=answer)
    invalid = 0
    while state.status == GameStatus.IN_PROGRESS and len(state.guesses) < max_guesses:
        try:
            guess = suggest(state)
            apply_guess(state, guess, allowed)
        except Exception:
            invalid += 1
            # Skip failed action without mutating; avoid infinite loop
            if invalid > 3:
                break
    return EpisodeResult(
        answer=answer,
        won=state.status == GameStatus.WON,
        guesses=list(state.guesses),
        invalid_actions=invalid,
        turns=len(state.guesses),
    )


@dataclass
class TurnExample:
    prompt: str
    answer: str
    state: GameState


def build_one_turn_examples(
    answers: tuple[str, ...],
    allowed: set[str],
    *,
    seed: int,
    per_answer: int = 2,
    allowed_hash: str = "local",
) -> list[TurnExample]:
    """Create prompts from deterministic partial games (empty + one random legal opener)."""
    examples: list[TurnExample] = []
    openers = sorted(allowed)[:50]
    for i, answer in enumerate(answers):
        # empty board
        empty = GameState(answer=answer)
        examples.append(
            TurnExample(
                prompt=build_prompt(empty, allowed_hash=allowed_hash),
                answer=answer,
                state=empty,
            )
        )
        if per_answer < 2:
            continue
        opener = openers[(seed + i) % len(openers)]
        if opener == answer:
            continue
        partial = GameState(answer=answer)
        try:
            apply_guess(partial, opener, allowed)
        except Exception:
            continue
        if partial.status != GameStatus.IN_PROGRESS:
            continue
        examples.append(
            TurnExample(
                prompt=build_prompt(partial, allowed_hash=allowed_hash),
                answer=answer,
                state=deepcopy(partial),
            )
        )
    return examples


def seeded_answers(answers: tuple[str, ...], n: int, seed: int) -> list[str]:
    return [pick_answer(answers, seed=seed + i) for i in range(n)]
