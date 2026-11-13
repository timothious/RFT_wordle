"""Game play endpoints (no AI)."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api.deps import get_session_store, get_word_lists
from backend.app.api.schemas import (
    ApiError,
    CreateGameRequest,
    GamePublicView,
    SubmitGuessRequest,
)
from backend.app.game.engine import GameError, GameState, apply_guess, public_view
from backend.app.game.session import SessionStore
from backend.app.game.words import WordLists, pick_answer

router = APIRouter(tags=["games"])


def _http_error(code: str, message: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=ApiError(code=code, message=message).model_dump(),
    )


@router.post("/games", response_model=GamePublicView, status_code=status.HTTP_201_CREATED)
def create_game(
    body: CreateGameRequest | None = None,
    words: WordLists = Depends(get_word_lists),
    sessions: SessionStore = Depends(get_session_store),
) -> GamePublicView:
    payload = body or CreateGameRequest()
    answer = pick_answer(words.answers, seed=payload.seed)
    session = sessions.create(GameState(answer=answer), seed=payload.seed)
    return GamePublicView.model_validate(public_view(session.state, session.game_id))


@router.get("/games/{game_id}", response_model=GamePublicView)
def get_game(
    game_id: str,
    sessions: SessionStore = Depends(get_session_store),
) -> GamePublicView:
    session = sessions.get(game_id)
    if session is None:
        raise _http_error("not_found", "Game not found", status.HTTP_404_NOT_FOUND)
    return GamePublicView.model_validate(public_view(session.state, session.game_id))


@router.post("/games/{game_id}/guesses", response_model=GamePublicView)
def submit_guess(
    game_id: str,
    body: SubmitGuessRequest,
    words: WordLists = Depends(get_word_lists),
    sessions: SessionStore = Depends(get_session_store),
) -> GamePublicView:
    session = sessions.get(game_id)
    if session is None:
        raise _http_error("not_found", "Game not found", status.HTTP_404_NOT_FOUND)

    try:
        apply_guess(session.state, body.guess, words.allowed)
    except GameError as exc:
        status_code = (
            status.HTTP_409_CONFLICT
            if exc.code.value == "game_over"
            else status.HTTP_400_BAD_REQUEST
        )
        raise _http_error(exc.code.value, exc.message, status_code) from exc

    return GamePublicView.model_validate(public_view(session.state, session.game_id))
