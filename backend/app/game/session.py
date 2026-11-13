"""In-memory game session store."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from backend.app.game.engine import GameState


@dataclass
class Session:
    game_id: str
    state: GameState
    created_at: float
    seed: int | None = None


class SessionStore:
    def __init__(self, ttl_seconds: int = 86_400) -> None:
        self._ttl_seconds = ttl_seconds
        self._sessions: dict[str, Session] = {}

    def create(self, state: GameState, seed: int | None = None) -> Session:
        self._purge_expired()
        game_id = str(uuid.uuid4())
        session = Session(game_id=game_id, state=state, created_at=time.time(), seed=seed)
        self._sessions[game_id] = session
        return session

    def get(self, game_id: str) -> Session | None:
        self._purge_expired()
        return self._sessions.get(game_id)

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [
            game_id
            for game_id, session in self._sessions.items()
            if now - session.created_at > self._ttl_seconds
        ]
        for game_id in expired:
            del self._sessions[game_id]
