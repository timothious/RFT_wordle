"""Shaped per-turn reward components for GRPO."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass

from backend.app.game.engine import (
    Feedback,
    GameError,
    GameState,
    GameStatus,
    apply_guess,
)
from backend.app.solvers.frequency import candidates_consistent


@dataclass(frozen=True)
class RewardWeights:
    solve: float = 5.0
    legal: float = 0.1
    invalid: float = -1.0
    progress: float = 0.5
    turn_cost: float = -0.05


@dataclass
class RewardBreakdown:
    total: float
    solve: float = 0.0
    legal: float = 0.0
    invalid: float = 0.0
    progress: float = 0.0
    turn_cost: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


def candidate_reduction_delta(
    state: GameState,
    guess: str,
    answers: tuple[str, ...],
) -> float:
    """Normalized reduction in remaining answers after applying guess feedback."""
    before = candidates_consistent(answers, state)
    if not before:
        return 0.0
    feedback = []
    # Use true answer only inside the evaluator copy path caller already scored;
    # here we need feedback relative to the secret for training states.
    # Caller must pass a state that still has answer set server-side.
    from backend.app.game.engine import score_guess

    feedback = score_guess(state.answer, guess)
    probe = deepcopy(state)
    probe.guesses = list(state.guesses) + [guess]
    probe.feedbacks = list(state.feedbacks) + [feedback]
    after = candidates_consistent(answers, probe)
    delta = (len(before) - len(after)) / len(before)
    return max(0.0, min(1.0, delta))


def score_action(
    state: GameState,
    guess_text: str,
    allowed: set[str],
    answers: tuple[str, ...],
    weights: RewardWeights | None = None,
) -> RewardBreakdown:
    """Score one candidate action against a copy of state (answer never returned)."""
    weights = weights or RewardWeights()
    normalized = (guess_text or "").strip().lower()

    # Invalid / malformed
    try:
        probe = deepcopy(state)
        apply_guess(probe, normalized, allowed)
    except GameError:
        return RewardBreakdown(total=weights.invalid, invalid=weights.invalid)

    parts = RewardBreakdown(total=0.0)
    parts.legal = weights.legal
    parts.turn_cost = weights.turn_cost
    parts.progress = weights.progress * candidate_reduction_delta(state, normalized, answers)

    if probe.status == GameStatus.WON or all(
        mark == Feedback.GREEN for mark in probe.feedbacks[-1]
    ):
        parts.solve = weights.solve

    parts.total = parts.solve + parts.legal + parts.invalid + parts.progress + parts.turn_cost
    return parts
