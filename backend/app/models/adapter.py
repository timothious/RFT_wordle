"""Policy adapters: solver, base LM, RFT LoRA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from backend.app.game.engine import GameState
from backend.app.models.contract import (
    GuessAction,
    InvalidAction,
    ParseError,
    build_prompt,
    parse_action,
    validate_action,
)
from backend.app.solvers.frequency import FrequencySolver

PolicyId = Literal["solver", "base", "rft"]


@dataclass
class SuggestionResult:
    policy: PolicyId
    guess: str | None
    raw_ok: bool
    error: str | None
    raw_text: str | None = None


class SolverPolicy:
    def __init__(self) -> None:
        self._solver = FrequencySolver()

    def suggest(
        self,
        state: GameState,
        allowed: set[str],
        answers: tuple[str, ...],
        *,
        allowed_hash: str = "local",
    ) -> SuggestionResult:
        try:
            guess = self._solver.suggest(state, allowed, answers)
        except ValueError as exc:
            return SuggestionResult("solver", None, False, str(exc))
        checked = validate_action(GuessAction(guess), state, allowed)
        if isinstance(checked, InvalidAction):
            return SuggestionResult("solver", None, False, checked.message)
        return SuggestionResult("solver", checked.guess, True, None)


class LanguageModelPolicy:
    """Lazy-loads Transformers model; optional PEFT LoRA for rft."""

    def __init__(
        self,
        policy_id: PolicyId,
        model_id: str,
        revision: str,
        device: str,
        adapter_path: str | None = None,
        max_new_tokens: int = 32,
    ) -> None:
        self.policy_id = policy_id
        self.model_id = model_id
        self.revision = revision
        self.device = device
        self.adapter_path = adapter_path
        self.max_new_tokens = max_new_tokens
        self._model = None
        self._tokenizer = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "PyTorch/Transformers not installed. Install requirements-ml.txt "
                "to use base/rft policies."
            ) from exc

        tokenizer = AutoTokenizer.from_pretrained(self.model_id, revision=self.revision)
        model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            revision=self.revision,
            torch_dtype=torch.float32 if self.device == "cpu" else torch.float16,
            device_map=self.device if self.device == "cuda" else None,
        )
        if self.device == "cpu":
            model = model.to("cpu")

        if self.adapter_path:
            from peft import PeftModel

            model = PeftModel.from_pretrained(model, self.adapter_path)

        model.eval()
        self._tokenizer = tokenizer
        self._model = model

    def suggest(
        self,
        state: GameState,
        allowed: set[str],
        answers: tuple[str, ...],
        *,
        allowed_hash: str = "local",
    ) -> SuggestionResult:
        del answers  # not shown to the policy
        try:
            self._ensure_loaded()
        except Exception as exc:  # noqa: BLE001 — surface load errors to API
            return SuggestionResult(self.policy_id, None, False, str(exc))

        assert self._model is not None and self._tokenizer is not None
        import torch

        # Short candidate hint keeps v1 constrained without dumping the full list.
        remaining_guesses = sorted(w for w in allowed if w not in state.guesses)[:40]
        hint = ", ".join(remaining_guesses)
        prompt = build_prompt(
            state,
            allowed_hash=allowed_hash,
            candidate_hint=hint,
        )

        messages = [{"role": "user", "content": prompt}]
        try:
            input_ids = self._tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                return_tensors="pt",
            )
        except Exception:
            encoded = self._tokenizer(prompt, return_tensors="pt")
            input_ids = encoded["input_ids"]

        input_ids = input_ids.to(self._model.device)
        with torch.no_grad():
            output = self._model.generate(
                input_ids,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        new_tokens = output[0, input_ids.shape[-1] :]
        text = self._tokenizer.decode(new_tokens, skip_special_tokens=True)

        parsed = parse_action(text)
        if isinstance(parsed, ParseError):
            return SuggestionResult(self.policy_id, None, False, parsed.message, text)

        checked = validate_action(parsed, state, allowed)
        if isinstance(checked, InvalidAction):
            return SuggestionResult(self.policy_id, None, False, checked.message, text)

        return SuggestionResult(self.policy_id, checked.guess, True, None, text)
