"""Selectable suggestion policies."""

from __future__ import annotations

from functools import lru_cache

from backend.app.config import Settings, get_settings
from backend.app.game.engine import GameState
from backend.app.models.adapter import (
    LanguageModelPolicy,
    PolicyId,
    SolverPolicy,
    SuggestionResult,
)


class PolicyRegistry:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._solver = SolverPolicy()
        self._base: LanguageModelPolicy | None = None
        self._rft: LanguageModelPolicy | None = None

    def get(self, policy: PolicyId) -> SolverPolicy | LanguageModelPolicy:
        if policy == "solver":
            return self._solver
        if policy == "base":
            if self._base is None:
                self._base = LanguageModelPolicy(
                    "base",
                    self.settings.model_id,
                    self.settings.model_revision,
                    self.settings.model_device,
                    adapter_path=None,
                    max_new_tokens=self.settings.max_new_tokens,
                )
            return self._base
        if policy == "rft":
            if not self.settings.lora_adapter_path:
                raise RuntimeError("LORA_ADAPTER_PATH is not configured for rft policy")
            if self._rft is None:
                self._rft = LanguageModelPolicy(
                    "rft",
                    self.settings.model_id,
                    self.settings.model_revision,
                    self.settings.model_device,
                    adapter_path=self.settings.lora_adapter_path,
                    max_new_tokens=self.settings.max_new_tokens,
                )
            return self._rft
        raise ValueError(f"Unknown policy: {policy}")

    def suggest(
        self,
        policy: PolicyId,
        state: GameState,
        allowed: set[str],
        answers: tuple[str, ...],
        allowed_hash: str,
    ) -> SuggestionResult:
        if policy in ("base", "rft") and not self.settings.enable_lm:
            return SuggestionResult(
                policy,
                None,
                False,
                "LM policies disabled. Set ENABLE_LM=true and install requirements-ml.txt.",
            )
        try:
            adapter = self.get(policy)
        except Exception as exc:  # noqa: BLE001
            return SuggestionResult(policy, None, False, str(exc))
        return adapter.suggest(state, allowed, answers, allowed_hash=allowed_hash)


@lru_cache
def get_policy_registry() -> PolicyRegistry:
    return PolicyRegistry(get_settings())
