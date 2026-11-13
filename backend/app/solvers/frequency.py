"""Deterministic frequency / expected-reduction Wordle solver."""

from __future__ import annotations

from collections import defaultdict

from backend.app.game.engine import Feedback, GameState, score_guess

# Stable letter-frequency tie-break (ETAOIN-ish, then alphabetical fallback via sort).
LETTER_FREQ = {
    ch: weight
    for weight, ch in enumerate(
        "etaoinshrdlcumwfgypbvkjxqz"[::-1],
        start=1,
    )
}


def candidates_consistent(answers: tuple[str, ...] | list[str], state: GameState) -> list[str]:
    remaining = list(answers)
    for guess, feedback in zip(state.guesses, state.feedbacks, strict=True):
        remaining = [word for word in remaining if score_guess(word, guess) == feedback]
    return remaining


def _pattern_key(feedback: list[Feedback]) -> tuple[str, ...]:
    return tuple(mark.value for mark in feedback)


def _guess_score(guess: str, remaining: list[str]) -> tuple[float, float, str]:
    """Higher expected reduction is better; then letter freq; then lexicographic."""
    if not remaining:
        return (0.0, _freq_score(guess), guess)

    buckets: dict[tuple[str, ...], int] = defaultdict(int)
    for answer in remaining:
        buckets[_pattern_key(score_guess(answer, guess))] += 1

    total = len(remaining)
    expected_left = sum((count / total) * count for count in buckets.values())
    reduction = total - expected_left
    return (reduction, _freq_score(guess), guess)


def _freq_score(guess: str) -> float:
    return float(sum(LETTER_FREQ.get(ch, 0) for ch in set(guess)))


class FrequencySolver:
    """Pick the legal guess that most reduces the consistent answer set in expectation."""

    def suggest(self, state: GameState, allowed: set[str], answers: tuple[str, ...]) -> str:
        remaining = candidates_consistent(answers, state)
        pool = remaining if remaining else list(answers)
        legal = sorted(word for word in allowed if word not in state.guesses)
        if not legal:
            raise ValueError("No legal guesses remain")

        # Prefer scoring among still-possible answers when available; else full legal list.
        scored_pool = [word for word in legal if word in pool] or legal
        # Cap evaluation set for speed while staying deterministic via sorted order.
        eval_guesses = scored_pool if len(scored_pool) <= 300 else scored_pool[:300]

        best = max(eval_guesses, key=lambda g: _guess_score(g, remaining or pool))
        return best
