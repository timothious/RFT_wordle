# RFT Wordle Demo: Implementation Report

**Prepared:** 2026-11-03  
**Updated:** 2026-11-13  
**Project state:** The repository currently has no application source code. This report defines a practical first implementation; it does not claim that a model has been trained.

## 1. Goal and recommendation

Build a small Wordle-style web app in which a language model chooses guesses, then use the game's deterministic rules to provide a reward signal for reinforcement fine-tuning (RFT). The project should demonstrate the complete loop: environment, baseline, reward, training, evaluation, and inference in the app.

**Recommended learning path:** Python game engine + FastAPI + a lightweight web UI; start with `Qwen/Qwen2.5-1.5B-Instruct` and a LoRA adapter, and use Hugging Face TRL's `GRPOTrainer` for the first RFT experiment. If suitable GPU memory is available and the initial run works, compare with `Qwen/Qwen3-4B-Instruct-2507`. Keep the model choice configurable rather than tying the app to a single checkpoint.

The smaller Qwen2.5 checkpoint is a conservative starting point for experimentation. Qwen's model cards and repository document the candidate model families and usage; actual training feasibility depends on GPU memory, sequence length, rollout batch size, and quantization. GRPO is a practical RFT method here because the game can score candidate actions automatically; it is not the only possible method.

## 2. Scope for the first demo

The first version should:

- Let a person play a standard five-letter, six-guess game.
- Offer an **AI suggestion** for the current board state.
- Keep the answer and game rules in a deterministic backend, never in the browser's model prompt or a public endpoint.
- Train/evaluate the AI on reproducible, seeded games with separate train, validation, and test answer sets.
- Compare the RFT adapter to the untouched base model and a documented non-ML solver (see §5.3).
- Display guesses, feedback, remaining guesses, and optionally a short explanation. Do not require or reward hidden chain-of-thought.

This keeps the user's experience understandable while making training results measurable. The model proposes a guess; the game engine remains authoritative for word validity and feedback.

## 3. Suggested architecture

```text
Browser UI
  ├─ New game / human guesses
  └─ Request AI suggestion
        ↓
FastAPI service
  ├─ Game API and session state
  ├─ Wordle rules and evaluator (pure Python)
  └─ Model adapter (base model or RFT LoRA)

Offline training and evaluation
  ├─ Seeded Wordle episode/state generator
  ├─ Baseline and model rollout runner
  ├─ Reward functions
  └─ TRL GRPO training → saved LoRA adapter + metrics
```

Keep game rules independent of the web and model layers so the same evaluator is used by gameplay, training, and tests. The inference service should return a structured guess, not an unrestricted action; validate it against the allowed word list before showing or submitting it.

**Suggested stack**

| Area | Initial choice |
|---|---|
| Game engine, API, training | Python, FastAPI, pytest |
| Training | PyTorch, Transformers, TRL, PEFT/LoRA |
| UI | Vite + React, or another familiar frontend framework |
| Experiment artifacts | JSONL rollout records, config files, adapter checkpoints, CSV/JSON metrics |

These are recommendations, not existing repository dependencies.

## 4. Wordle environment and model contract

Implement a pure game-state transition function:

`score_guess(answer, guess) -> [green, yellow, gray] * 5`

It must handle duplicate letters correctly. Use a two-pass algorithm: mark exact-position matches first, then allocate remaining answer-letter counts to yellow matches. Add tests for repeated letters before starting model training.

The model input should contain only information available to a player:

- Rules: five-letter guesses, six turns, accepted-guess policy.
- Previous guesses and their color feedback.
- Remaining turn count.
- A request for exactly one guess in a small JSON schema, for example `{"guess":"crane"}`.

Do not include the answer, RNG seed, future feedback, or hidden evaluator data. The API validates JSON, word length, dictionary membership, and duplicate guesses; invalid output gets a clear retry/error path and is not silently treated as a successful guess. Keep the answer server-side and exclude it from logs returned to the browser.

### 4.1 Action space for v1 (locked decision)

**v1 uses constrained candidate selection**, not unconstrained free generation.

- At each turn, the prompt includes (or the reward validator enforces) a fixed allowed-guess list that is identical at train and test time.
- The model must return one word from that list as `{"guess":"..."}`.
- This reduces invalid outputs on a small instruction model and makes the first GRPO run measurable.
- Document the list version/hash in every experiment config.
- A later experiment may switch to unconstrained generation; treat that as a separate study, not a silent change mid-run.

## 5. RFT design

### 5.1 Credit assignment (locked decision)

Separate training objective from evaluation metrics:

| Mode | What is optimized / measured | When used |
|---|---|---|
| One-turn training | Visible board state → JSON guess; shaped per-turn reward | GRPO training updates |
| Full-episode evaluation | Complete games until solve or six guesses | Held-out reporting and promotion gate |

Do not report training reward as proof of better play. Promote an adapter only when held-out **episode win rate** (primary) improves versus the base model under identical seeds and word lists, without unacceptable regressions in invalid-action rate or latency.

### 5.2 Training example and rollout

Treat one turn's visible board state as the prompt and the generated JSON guess as the action. Create prompts from deterministic game rollouts, then generate multiple candidate actions for the same state so GRPO can compare their rewards. The evaluator applies each candidate guess to a copy of that state and scores it without exposing the answer to the policy.

For episode-level results, run full games in a separate rollout/evaluation harness: each model guess is scored by the game engine, feedback is appended to the next prompt, and the episode ends on a solve or six guesses.

### 5.3 Non-ML baseline (required comparator)

Implement a deterministic frequency / information heuristic solver as the non-ML baseline, for example:

1. Maintain the set of answers still consistent with feedback so far.
2. Score each legal guess by expected remaining-candidate reduction (or a frequency proxy if full information gain is too slow).
3. Break ties with a fixed letter-frequency table and a stable sort so results are reproducible.

Report this solver next to the base model and the RFT adapter under the same seeds. The demo succeeds even if RFT does not beat the solver, but the comparison must be visible.

### 5.4 Reward proposal and starting weights

Use machine-checkable outcomes, not a model-graded rationale. Log every component separately. Starting weights for the first experiment (tune only on validation):

| Component | Suggested weight | Notes |
|---|---|---|
| Solve (legal guess that wins) | `+5.0` | Keep dominant so info-gain cannot replace winning |
| Legal, non-repeated guess | `+0.1` | Small format/legality credit |
| Malformed / out-of-list / repeated | `-1.0` | Hard penalty; never apply as a successful state transition |
| Progress / info gain | `+0.5 × Δ` | `Δ` = normalized reduction in remaining candidate set (or expected information gain), clipped to `[0, 1]` |
| Turn cost | `-0.05` | Prefer fewer guesses when outcomes are otherwise equal |

Normalize and retune on the validation set if needed. Avoid a reward that depends only on the final win for the first experiment: GRPO groups with all-zero rewards may provide no useful preference signal. Shaped per-turn feedback is a practical bootstrap, but verify that optimizing it improves held-out episode win rate rather than merely the proxy metric.

### 5.5 Training procedure

1. Establish a no-training baseline using both the base model and the deterministic solver in §5.3.
2. Verify prompts, action parsing, reward components, and episode rollouts with fixed seeds before training.
3. Optionally do a small supervised warm-up on legal example guesses if the base model cannot reliably follow the JSON contract. Keep this clearly separate from the RFT result.
4. **Hardware gate (required before a long GRPO run):** measure peak GPU/CPU memory and tokens/sec for a short dry-run with the planned model, LoRA rank, sequence length, and rollout batch size. Abort or downscale (smaller batch, shorter context, stronger quantization, or stay on 1.5B) if the dry-run cannot complete one training step with headroom. Record hardware, driver, and measured memory in the experiment log.
5. Run TRL `GRPOTrainer` with a custom deterministic reward function and a PEFT LoRA adapter. Start with a small dataset and short run; save the exact model ID/revision, tokenizer, dataset split, seeds, TRL/PyTorch versions, and training config.
6. Evaluate the untouched base model and adapter using the same fixed held-out seeds and word lists. Compare win rate, mean guesses among wins, invalid-action rate, latency, and reward components.
7. Only promote an adapter to the app if it beats the base-model baseline on held-out episode win rate without unacceptable regressions in legality or latency.

Treat TRL and model APIs as versioned dependencies; pin versions for a reproducible experiment and verify the current `GRPOTrainer` API when implementing it.

## 6. Evaluation and acceptance criteria

The game engine is the ground truth. Evaluation should be run on a held-out set large enough to report uncertainty, with results grouped by seed and answer. Keep train, validation, and test answer lists disjoint. A first milestone can use a few hundred test games; increase this before making claims about small improvements.

Report at least:

- Win rate within six guesses, with confidence interval (primary promotion metric).
- Mean guesses to solve, both among wins and across all games.
- Invalid/repeated guess rate.
- JSON parse success rate.
- Inference latency and model memory use.
- Side-by-side comparison: base checkpoint, RFT adapter, and deterministic solver under identical conditions.

**MVP acceptance:** rules and duplicate-letter tests pass; the browser can play a complete game; AI suggestions never leak the answer; invalid model outputs are surfaced; the evaluation is reproducible; and the report clearly shows whether RFT helped versus the base model. The AI need not outperform the hand-built solver for the demo to succeed, but that comparison should be visible.

## 7. Implementation roadmap

| Phase | Work | Deliverable |
|---|---|---|
| 1. Foundation | Choose and license-check word lists; implement duplicate-safe feedback, state transitions, and tests. | Tested Python game engine |
| 2. Playable app | Build FastAPI game/session endpoints and a simple UI. Keep secret state on the server. | Human-playable Wordle demo |
| 3. Baselines | Add the deterministic solver (§5.3) and base-model suggestion endpoint; create seeded evaluation. | Baseline metrics and repeatable episodes |
| 3b. Hardware gate | Dry-run GRPO memory/throughput check for the chosen model and batch settings. | Go/no-go note with measured resource use |
| 4. RFT pipeline | Add structured prompts (candidate-selection contract), reward components, GRPO + LoRA configuration, rollout logging, and checkpoints. | Reproducible training run |
| 5. Compare and integrate | Evaluate adapter on held-out games; load selected adapter behind the same model interface. | App with selectable base/RFT model |
| 6. Document results | Record hardware, model revision, software versions, data/splits, reward weights, metrics, and limitations. | Reproducible experiment report |

## 8. Risks and controls

- **Sparse or proxy reward:** Track episode wins, not just training reward; use small shaped rewards and test for proxy gaming.
- **Credit-assignment confusion:** Train on one-turn rewards; promote only on episode metrics.
- **Invalid model actions:** Validate every response; never let the model mutate game state directly. v1 candidate selection reduces this risk.
- **Answer leakage:** Keep the target and test cases out of prompts, client state, public logs, and training metadata available at inference.
- **Data leakage:** Fix and document disjoint splits; do not tune on test results.
- **Compute limits:** Begin with the 1.5B candidate, LoRA, short contexts, and a small rollout batch. Pass the hardware gate before long runs.
- **Overclaiming:** Report sample size and uncertainty. A reward increase alone is not evidence that the game-playing policy improved.
- **Word-list licensing:** Use a word list with a compatible license and include its attribution/license in the project.

## 9. References

- Hugging Face TRL [GRPO Trainer documentation](https://huggingface.co/docs/trl/grpo_trainer) — trainer concepts, configuration, and reward functions.
- Qwen [Qwen2.5-1.5B-Instruct model card](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) — small instruction model candidate.
- Qwen [Qwen3 repository](https://github.com/QwenLM/Qwen3) and [Qwen3-4B-Instruct-2507 model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507) — alternative candidate; check its current model-card requirements before use.
