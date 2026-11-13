"""Prompt / parse / validate contract for model guesses (v1 candidate selection)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from backend.app.game.engine import WORD_LENGTH, GameState, public_view

_JSON_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)


@dataclass(frozen=True)
class GuessAction:
    guess: str


@dataclass(frozen=True)
class ParseError:
    message: str


@dataclass(frozen=True)
class InvalidAction:
    message: str


def build_prompt(
    state: GameState,
    *,
    game_id: str = "train",
    allowed_hash: str = "local",
    candidate_hint: str | None = None,
) -> str:
    view = public_view(state, game_id)
    board_lines = []
    for row in view["board"]:
        colors = ",".join(row["feedback"])
        board_lines.append(f"- {row['guess']} -> [{colors}]")
    board_text = "\n".join(board_lines) if board_lines else "- (no guesses yet)"

    hint = ""
    if candidate_hint:
        hint = f"\nCandidate words (choose one): {candidate_hint}\n"

    return (
        "You are playing Wordle. Rules: guess a five-letter English word. "
        "You have six turns. Reply with JSON only, exactly like "
        '{"guess":"crane"} — lowercase, no other keys, no markdown.\n'
        f"Allowed-list hash: {allowed_hash}\n"
        f"Remaining turns: {view['remaining_guesses']}\n"
        f"Board so far:\n{board_text}\n"
        f"{hint}"
        "Return one legal guess now."
    )


def parse_action(text: str) -> GuessAction | ParseError:
    raw = (text or "").strip()
    if not raw:
        return ParseError("empty model output")

    candidates = [raw]
    match = _JSON_RE.search(raw)
    if match:
        candidates.insert(0, match.group(0))

    for blob in candidates:
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        guess = data.get("guess")
        if isinstance(guess, str):
            return GuessAction(guess=guess.strip().lower())
    return ParseError("could not parse JSON guess")


def validate_action(
    action: GuessAction,
    state: GameState,
    allowed: set[str],
) -> GuessAction | InvalidAction:
    guess = action.guess.strip().lower()
    if len(guess) != WORD_LENGTH or not guess.isalpha():
        return InvalidAction("guess must be exactly 5 letters")
    if guess not in allowed:
        return InvalidAction("guess not in allowed list")
    if guess in state.guesses:
        return InvalidAction("guess already used")
    return GuessAction(guess=guess)
