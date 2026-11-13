"""Shared FastAPI dependencies."""

from functools import lru_cache

from backend.app.config import Settings, get_settings
from backend.app.game.session import SessionStore
from backend.app.game.words import WordLists, load_word_lists


@lru_cache
def get_word_lists() -> WordLists:
    settings = get_settings()
    return load_word_lists(
        str(settings.word_list_dir),
        settings.allowed_guesses_file,
        settings.answers_file,
    )


@lru_cache
def get_session_store() -> SessionStore:
    settings = get_settings()
    return SessionStore(ttl_seconds=settings.session_ttl_seconds)


def get_app_settings() -> Settings:
    return get_settings()
