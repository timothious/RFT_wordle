"""Tests for prompt parse/validate contract."""

from backend.app.game.engine import GameState
from backend.app.models.contract import (
    GuessAction,
    InvalidAction,
    ParseError,
    build_prompt,
    parse_action,
    validate_action,
)


def test_parse_action_json() -> None:
    result = parse_action('Sure\n{"guess":"Crane"}\n')
    assert isinstance(result, GuessAction)
    assert result.guess == "crane"


def test_parse_action_invalid() -> None:
    assert isinstance(parse_action("no json here"), ParseError)


def test_validate_and_prompt_no_answer_leak() -> None:
    state = GameState(answer="zebra")
    prompt = build_prompt(state)
    assert "zebra" not in prompt
    assert "answer:" not in prompt.lower()

    ok = validate_action(GuessAction("about"), state, {"about", "zebra"})
    assert isinstance(ok, GuessAction)
    bad = validate_action(GuessAction("zzzzz"), state, {"about", "zebra"})
    assert isinstance(bad, InvalidAction)
