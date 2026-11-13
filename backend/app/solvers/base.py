"""Solver protocol."""

from __future__ import annotations

from typing import Protocol

from backend.app.game.engine import GameState


class Solver(Protocol):
    def suggest(self, state: GameState, allowed: set[str], answers: tuple[str, ...]) -> str:
        """Return one legal guess for the visible board state."""
