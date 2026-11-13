"""Word-list loading and answer selection."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class WordLists:
    allowed: set[str]
    answers: tuple[str, ...]
    allowed_hash: str
    answers_hash: str


def _read_words(path: Path) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(f"Word list not found: {path}")
    words: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        word = line.strip().lower()
        if not word or word.startswith("#"):
            continue
        if len(word) != 5 or not word.isalpha():
            raise ValueError(f"Invalid word in {path.name}: {word!r}")
        words.append(word)
    if not words:
        raise ValueError(f"Word list is empty: {path}")
    return words


def _content_hash(words: list[str]) -> str:
    payload = "\n".join(words).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


@lru_cache
def load_word_lists(word_list_dir: str, allowed_file: str, answers_file: str) -> WordLists:
    base = Path(word_list_dir)
    allowed_words = _read_words(base / allowed_file)
    answer_words = _read_words(base / answers_file)

    allowed_set = set(allowed_words)
    missing = [word for word in answer_words if word not in allowed_set]
    if missing:
        raise ValueError(f"Answers missing from allowed list: {missing[:5]}")

    return WordLists(
        allowed=allowed_set,
        answers=tuple(answer_words),
        allowed_hash=_content_hash(allowed_words),
        answers_hash=_content_hash(answer_words),
    )


def pick_answer(answers: tuple[str, ...], seed: int | None = None) -> str:
    if not answers:
        raise ValueError("No answers available")
    rng = random.Random(seed)
    return rng.choice(answers)
