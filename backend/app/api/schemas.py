"""Pydantic request/response models for the game API."""

from typing import Literal

from pydantic import BaseModel, Field

FeedbackLiteral = Literal["green", "yellow", "gray"]
StatusLiteral = Literal["in_progress", "won", "lost"]


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


class ApiError(BaseModel):
    code: str
    message: str
