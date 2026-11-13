"""AI / solver suggestion endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api.deps import get_app_settings, get_session_store, get_word_lists
from backend.app.api.schemas import (
    ApiError,
    GamePublicView,
    SuggestRequest,
    SuggestResponse,
)
from backend.app.config import Settings
from backend.app.game.engine import GameError, GameErrorCode, apply_guess, public_view
from backend.app.game.session import SessionStore
from backend.app.game.words import WordLists
from backend.app.models.adapter import PolicyId
from backend.app.models.registry import PolicyRegistry, get_policy_registry

router = APIRouter(tags=["suggest"])


def _http_error(code: str, message: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=ApiError(code=code, message=message).model_dump(),
    )


@router.post("/games/{game_id}/suggest", response_model=SuggestResponse)
def suggest_guess(
    game_id: str,
    body: SuggestRequest | None = None,
    words: WordLists = Depends(get_word_lists),
    sessions: SessionStore = Depends(get_session_store),
    settings: Settings = Depends(get_app_settings),
    registry: PolicyRegistry = Depends(get_policy_registry),
) -> SuggestResponse:
    payload = body or SuggestRequest()
    session = sessions.get(game_id)
    if session is None:
        raise _http_error("not_found", "Game not found", status.HTTP_404_NOT_FOUND)

    if session.state.status.value != "in_progress":
        raise _http_error("game_over", "Game is finished", status.HTTP_409_CONFLICT)

    policy: PolicyId = payload.policy or settings.model_policy  # type: ignore[assignment]
    if policy not in ("solver", "base", "rft"):
        raise _http_error("invalid_guess", f"Unknown policy: {policy}", status.HTTP_400_BAD_REQUEST)

    result = registry.suggest(
        policy,
        session.state,
        words.allowed,
        words.answers,
        words.allowed_hash,
    )

    if not result.raw_ok or not result.guess:
        return SuggestResponse(
            policy=policy,
            guess=None,
            raw_ok=False,
            error=result.error or "model_invalid_output",
            applied=False,
            board=None,
        )

    applied = False
    board: GamePublicView | None = None
    if payload.apply:
        try:
            apply_guess(session.state, result.guess, words.allowed)
            applied = True
            board = GamePublicView.model_validate(public_view(session.state, session.game_id))
        except GameError as exc:
            if exc.code == GameErrorCode.GAME_OVER:
                raise _http_error(exc.code.value, exc.message, status.HTTP_409_CONFLICT) from exc
            return SuggestResponse(
                policy=policy,
                guess=result.guess,
                raw_ok=False,
                error=exc.message,
                applied=False,
                board=None,
            )

    return SuggestResponse(
        policy=policy,
        guess=result.guess,
        raw_ok=True,
        error=None,
        applied=applied,
        board=board,
    )
