"""GRPO + LoRA training entrypoint for Wordle one-turn actions."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import yaml

from backend.app.config import get_settings
from backend.app.game.words import load_word_lists
from backend.training.dataset import turn_examples
from backend.training.rewards import RewardWeights, score_action


def _load_cfg(path: Path) -> dict:
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Wordle policy with TRL GRPO + LoRA")
    parser.add_argument("--config", type=Path, default=Path("backend/configs/default.yaml"))
    args = parser.parse_args()
    cfg = _load_cfg(args.config)
    settings = get_settings()

    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig, TaskType
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from trl import GRPOConfig, GRPOTrainer
    except ImportError as exc:
        raise SystemExit(
            f"ML dependencies missing ({exc}). Install with: pip install -r requirements-ml.txt"
        ) from exc

    words = load_word_lists(
        str(settings.word_list_dir),
        settings.allowed_guesses_file,
        cfg.get("answers_train_file", settings.answers_train_file),
    )
    seed = int(cfg.get("seed", 42))
    examples = turn_examples(words, seed=seed, per_answer=int(cfg.get("per_answer", 2)))
    # Keep a side map from prompt -> training state for reward scoring
    prompt_to_state = {ex.prompt: ex.state for ex in examples}
    hf_ds = Dataset.from_list([{"prompt": ex.prompt} for ex in examples])

    weights = RewardWeights(
        solve=float(cfg.get("reward_solve", settings.reward_solve)),
        legal=float(cfg.get("reward_legal", settings.reward_legal)),
        invalid=float(cfg.get("reward_invalid", settings.reward_invalid)),
        progress=float(cfg.get("reward_progress", settings.reward_progress)),
        turn_cost=float(cfg.get("reward_turn_cost", settings.reward_turn_cost)),
    )

    model_id = cfg.get("model_id", settings.model_id)
    revision = cfg.get("model_revision", settings.model_revision)
    device = cfg.get("model_device", settings.model_device)

    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        revision=revision,
        torch_dtype=torch.float32 if device == "cpu" else torch.float16,
    )

    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=int(cfg.get("lora_r", 8)),
        lora_alpha=int(cfg.get("lora_alpha", 16)),
        lora_dropout=float(cfg.get("lora_dropout", 0.05)),
        target_modules=cfg.get("lora_target_modules", ["q_proj", "v_proj"]),
    )

    run_id = cfg.get("run_id", f"grpo_{int(time.time())}")
    out_dir = Path(cfg.get("artifacts_dir", settings.artifacts_dir)) / "adapters" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    def reward_funcs(completions: list[str], prompts: list[str] | None = None, **kwargs):
        del kwargs
        rewards: list[float] = []
        prompts = prompts or [""] * len(completions)
        log_rows = []
        for completion, prompt in zip(completions, prompts, strict=False):
            state = prompt_to_state.get(prompt)
            if state is None:
                rewards.append(weights.invalid)
                continue
            # completion may be chat text; reward uses parser inside score via raw guess extract
            from backend.app.models.contract import parse_action, ParseError

            parsed = parse_action(completion)
            guess = "" if isinstance(parsed, ParseError) else parsed.guess
            breakdown = score_action(state, guess, words.allowed, words.answers, weights)
            rewards.append(breakdown.total)
            log_rows.append({"prompt_head": prompt[:80], "completion": completion, **breakdown.as_dict()})
        log_path = out_dir / "reward_samples.jsonl"
        with log_path.open("a", encoding="utf-8") as fh:
            for row in log_rows:
                fh.write(json.dumps(row) + "\n")
        return rewards

    training_args = GRPOConfig(
        output_dir=str(out_dir / "trainer"),
        learning_rate=float(cfg.get("learning_rate", 1e-5)),
        per_device_train_batch_size=int(cfg.get("batch_size", 1)),
        gradient_accumulation_steps=int(cfg.get("grad_accum", 4)),
        num_train_epochs=float(cfg.get("epochs", 1)),
        logging_steps=1,
        max_completion_length=int(cfg.get("max_new_tokens", settings.max_new_tokens)),
        num_generations=int(cfg.get("num_generations", 2)),
        report_to=[],
    )

    trainer = GRPOTrainer(
        model=model,
        reward_funcs=reward_funcs,
        args=training_args,
        train_dataset=hf_ds,
        processing_class=tokenizer,
        peft_config=peft_config,
    )
    trainer.train()
    trainer.save_model(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))

    meta = {
        "run_id": run_id,
        "model_id": model_id,
        "model_revision": revision,
        "seed": seed,
        "allowed_hash": words.allowed_hash,
        "answers_hash": words.answers_hash,
        "n_prompts": len(examples),
        "reward_weights": weights.__dict__,
        "config": cfg,
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "adapter": str(out_dir)}, indent=2))


if __name__ == "__main__":
    main()
