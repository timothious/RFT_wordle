"""Held-out episode evaluation for solver / base / rft policies."""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import yaml

from backend.app.config import get_settings
from backend.app.game.engine import GameState
from backend.app.game.words import load_word_lists
from backend.app.models.adapter import PolicyId
from backend.app.models.registry import PolicyRegistry
from backend.training.rollouts import run_episode


def _wilson_ci(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((centre - margin) / denom, (centre + margin) / denom)


def evaluate_policy(
    policy: PolicyId,
    registry: PolicyRegistry,
    answers: tuple[str, ...],
    allowed: set[str],
    allowed_hash: str,
    *,
    seed: int,
    limit: int,
) -> dict:
    subset = answers[:limit] if limit > 0 else answers
    wins = 0
    guess_sum_wins = 0
    guess_sum_all = 0
    invalid_total = 0
    latencies: list[float] = []

    for i, answer in enumerate(subset):
        def suggest(state: GameState, _answer: str = answer) -> str:
            t0 = time.perf_counter()
            result = registry.suggest(policy, state, allowed, answers, allowed_hash)
            latencies.append(time.perf_counter() - t0)
            if not result.raw_ok or not result.guess:
                raise RuntimeError(result.error or "invalid suggestion")
            return result.guess

        episode = run_episode(answer, suggest, allowed)
        guess_sum_all += episode.turns
        invalid_total += episode.invalid_actions
        if episode.won:
            wins += 1
            guess_sum_wins += episode.turns

    n = len(subset)
    lo, hi = _wilson_ci(wins, n)
    return {
        "policy": policy,
        "n": n,
        "seed": seed,
        "win_rate": wins / n if n else 0.0,
        "win_rate_ci95": [lo, hi],
        "mean_guesses_all": guess_sum_all / n if n else 0.0,
        "mean_guesses_wins": guess_sum_wins / wins if wins else None,
        "invalid_actions": invalid_total,
        "mean_latency_s": sum(latencies) / len(latencies) if latencies else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Wordle policies on held-out answers")
    parser.add_argument("--config", type=Path, default=Path("backend/configs/default.yaml"))
    parser.add_argument("--policy", type=str, default="solver", help="comma-separated: solver,base,rft")
    parser.add_argument("--limit", type=int, default=0, help="max test answers (0=all)")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    cfg = {}
    if args.config.is_file():
        cfg = yaml.safe_load(args.config.read_text()) or {}

    settings = get_settings()
    words = load_word_lists(
        str(settings.word_list_dir),
        settings.allowed_guesses_file,
        cfg.get("answers_test_file", settings.answers_test_file),
    )
    registry = PolicyRegistry(settings)
    policies = [p.strip() for p in args.policy.split(",") if p.strip()]

    results = []
    for policy in policies:
        results.append(
            evaluate_policy(
                policy,  # type: ignore[arg-type]
                registry,
                words.answers,
                words.allowed,
                words.allowed_hash,
                seed=args.seed,
                limit=args.limit,
            )
        )

    out_dir = Path(cfg.get("artifacts_dir", settings.artifacts_dir)) / "metrics"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"eval_{int(time.time())}.json"
    out_path.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")
    print(json.dumps({"results": results, "wrote": str(out_path)}, indent=2))


if __name__ == "__main__":
    main()
