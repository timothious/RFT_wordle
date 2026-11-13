"""Tests for reward components."""

from backend.app.game.engine import GameState
from backend.training.rewards import RewardWeights, score_action


def test_reward_invalid() -> None:
    state = GameState(answer="crane")
    breakdown = score_action(state, "zzzzz", {"crane", "about"}, ("crane", "about"))
    assert breakdown.invalid < 0
    assert breakdown.total == breakdown.invalid


def test_reward_solve_dominates() -> None:
    state = GameState(answer="crane")
    weights = RewardWeights()
    breakdown = score_action(state, "crane", {"crane", "about"}, ("crane", "about"), weights)
    assert breakdown.solve == weights.solve
    assert breakdown.total >= weights.solve + weights.legal + weights.turn_cost
