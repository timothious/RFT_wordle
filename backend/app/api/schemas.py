"""Pydantic request/response models for the game API."""

from typing import Literal

from pydantic import BaseModel, Field

FeedbackLiteral = Literal["green", "yellow", "gray"]
StatusLiteral = Literal["in_progress", "won", "lost"]
PolicyLiteral = Literal["solver", "base", "rft"]


class GuessRow(BaseModel):
    guess: str
    feedback: list[FeedbackLiteral]


class GamePublicView(BaseModel):
    game_id: str
    status: StatusLiteral
    remaining_guesses: int
    board: list[GuessRow]


class CreateGameRequest(BaseModel):
    seed: int | None = None


class SubmitGuessRequest(BaseModel):
    guess: str = Field(min_length=1, max_length=16)


class SuggestRequest(BaseModel):
    policy: PolicyLiteral | None = None
    apply: bool = False


class SuggestResponse(BaseModel):
    policy: PolicyLiteral
    guess: str | None
    raw_ok: bool
    error: str | None
    applied: bool
    board: GamePublicView | None = None


class ApiError(BaseModel):
    code: str
    message: str
