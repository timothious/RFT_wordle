"""Load splits and build HuggingFace-style prompt datasets for GRPO."""

from __future__ import annotations

from pathlib import Path

from backend.app.game.words import WordLists, load_word_lists
from backend.training.rollouts import TurnExample, build_one_turn_examples


def load_split_lists(
    word_list_dir: Path,
    allowed_file: str,
    split_file: str,
) -> WordLists:
    return load_word_lists(str(word_list_dir), allowed_file, split_file)


def prompts_for_grpo(
    words: WordLists,
    *,
    seed: int,
    per_answer: int = 2,
) -> list[dict[str, str]]:
    examples = build_one_turn_examples(
        words.answers,
        words.allowed,
        seed=seed,
        per_answer=per_answer,
        allowed_hash=words.allowed_hash,
    )
    return [{"prompt": ex.prompt} for ex in examples]


def turn_examples(
    words: WordLists,
    *,
    seed: int,
    per_answer: int = 2,
) -> list[TurnExample]:
    return build_one_turn_examples(
        words.answers,
        words.allowed,
        seed=seed,
        per_answer=per_answer,
        allowed_hash=words.allowed_hash,
    )
