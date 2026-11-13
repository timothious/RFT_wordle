# RFT Wordle: Backend Implementation Plan

**Prepared:** 2026-11-13  
**Related:** `RFT-WORDLE-IMPLEMENTATION-REPORT.md`  
**Scope:** Backend only — game engine, FastAPI service, model inference adapter, offline training/evaluation. Frontend UI is out of scope except for the API contract it will consume.

## 1. Backend goals

Deliver a Python backend that:

1. Owns Wordle rules, word lists, and secret answer state.
2. Exposes a small HTTP API for new game, guess, game status, and AI suggestion.
3. Serves AI suggestions from a selectable policy: base model, RFT LoRA adapter, or deterministic solver.
4. Reuses the same pure game engine for live play, rewards, training rollouts, and evaluation.
5. Supports reproducible offline RFT (GRPO + LoRA) and held-out episode metrics.

Locked product decisions from the parent report:

- v1 action space = **constrained candidate selection** (`{"guess":"..."}` from a fixed allowed list).
- Train on **one-turn shaped rewards**; promote adapters only on **held-out episode win rate**.
- Answers never leave the server; prompts never include the answer or seed.

## 2. Proposed repository layout

```text
backend/
  app/
    __init__.py
    main.py                 # FastAPI app factory / lifespan
    config.py               # Settings (env / .env)
    api/
      __init__.py
      routes_game.py        # /games endpoints
      routes_suggest.py     # /games/{id}/suggest
      deps.py               # shared dependencies
      schemas.py            # Pydantic request/response models
    game/
      __init__.py
      engine.py             # score_guess, GameState, transitions
      words.py              # load lists, hashes, splits
      session.py            # in-memory (or store) session manager
    solvers/
      __init__.py
      frequency.py          # deterministic non-ML baseline
      base.py               # Solver protocol
    models/
      __init__.py
      contract.py           # prompt builder + JSON parse/validate
      adapter.py            # load base / LoRA, generate guess
      registry.py           # selectable policy ids
  training/
    __init__.py
    rewards.py              # component rewards + weights
    rollouts.py             # one-turn prompts + episode runner
    dataset.py              # seeded state generator, splits
    train_grpo.py           # TRL GRPO entrypoint
    eval_episodes.py        # held-out evaluation + metrics CSV/JSON
    hardware_gate.py        # dry-run memory/throughput check
  tests/
    test_engine.py
    test_words.py
    test_api_game.py
    test_contract.py
    test_rewards.py
    test_solver.py
  data/
    answers_train.txt
    answers_val.txt
    answers_test.txt
    allowed_guesses.txt
    LICENSE_ATTRIBUTION.md
  configs/
    default.yaml            # model id, LoRA, reward weights, seeds
    experiment_template.yaml
  artifacts/                # gitignored: adapters, metrics, JSONL
requirements.txt
```

Keep `game/` free of FastAPI and torch imports so training and tests can import the engine alone.

## 3. Core game engine (Phase 1)

### 3.1 Responsibilities

| Module | Must provide |
|---|---|
| `score_guess(answer, guess)` | Five feedback marks; duplicate-letter safe (greens first, then yellows from remaining counts) |
| `GameState` | answer (private), guesses, feedbacks, remaining turns, status (`in_progress` / `won` / `lost`) |
| `apply_guess(state, guess)` | Validate length, alphabet, dictionary membership, non-repeat; apply transition or raise typed error |
| `public_view(state)` | Board visible to client/model: guesses, colors, remaining turns, status — **no answer** |
| Word loaders | Allowed guesses + answer list; content hash; disjoint train/val/test split helpers |

### 3.2 Validation rules

Reject (do not mutate state) when:

- Guess is not exactly five letters `a–z` (normalize case server-side).
- Guess not in `allowed_guesses`.
- Guess already used in this session.
- Game already finished.

### 3.3 Tests before any model work

- Duplicate-letter cases (e.g. answer `abbey`, guess `books` / `beeps` style fixtures).
- Win on guess 1–6; loss after six wrong guesses.
- Invalid guess paths leave state unchanged.
- `public_view` never contains `answer`.
- Split helper guarantees disjoint answer sets.

**Phase 1 exit:** `pytest` green for engine + words; word-list license note present.

## 4. FastAPI service (Phase 2)

### 4.1 Runtime settings

Configurable via environment / `config.py`:

- `WORD_LIST_DIR`, answer/allowed file names
- `SESSION_TTL_SECONDS`, max concurrent sessions
- `MODEL_POLICY` default: `solver` | `base` | `rft`
- `MODEL_ID`, `MODEL_REVISION`, `LORA_ADAPTER_PATH` (optional)
- `DEVICE`, quantization flags
- CORS origins for local UI

Start with **in-memory sessions** keyed by UUID. Optional later: Redis or SQLite. Persist nothing that would leak answers to client logs.

### 4.2 HTTP API contract

All responses that describe a board use the public view only.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/games` | Start game. Body optional: `{ "seed": int }` for reproducible answers from the **play** pool (never expose which answer). |
| `GET` | `/games/{game_id}` | Public board state. |
| `POST` | `/games/{game_id}/guesses` | Submit human guess `{ "guess": "crane" }`. |
| `POST` | `/games/{game_id}/suggest` | Ask current policy for one suggestion. Does **not** auto-submit unless `apply: true`. |
| `GET` | `/health` | Liveness; optional model-loaded flag. |

Suggested response shapes:

```json
{
  "game_id": "uuid",
  "status": "in_progress",
  "remaining_guesses": 5,
  "board": [
    { "guess": "crane", "feedback": ["gray", "yellow", "gray", "green", "gray"] }
  ]
}
```

Suggestion response:

```json
{
  "policy": "base",
  "guess": "slate",
  "raw_ok": true,
  "error": null,
  "applied": false,
  "board": { "...": "public view if applied" }
}
```

Error model: stable `code` + human `message` for `invalid_guess`, `not_in_dictionary`, `duplicate_guess`, `game_over`, `model_invalid_output`, `not_found`.

### 4.3 Security / leakage controls

- Never return `answer`, RNG internals, or full remaining-candidate sets to the browser in v1 play mode.
- Do not log answers in access logs or suggestion payloads.
- Validate model output through the same `apply_guess` / dictionary checks before any apply.
- Rate-limit `/suggest` if serving a local GPU (simple in-process token bucket is enough for demo).

### 4.4 API tests

- Full human game via TestClient.
- Invalid guesses return 4xx and unchanged board.
- Finished game rejects further guesses.
- Suggest with mock policy returns structured guess; invalid model JSON surfaces `model_invalid_output`.
- Public JSON schema snapshot does not include answer fields.

**Phase 2 exit:** Human-complete game over HTTP; secrets stay server-side.

## 5. Model contract and inference adapter (Phases 3–5)

### 5.1 Prompt contract (v1)

Prompt contents (player-visible only):

- Rules summary (5 letters, 6 turns, JSON-only reply).
- Allowed-guess policy statement (choose from list / list hash).
- Prior guesses + feedback.
- Remaining turn count.
- Output schema: exactly `{"guess":"<word>"}`.

Implementation modules:

- `contract.build_prompt(public_state, allowed_list_meta) -> str`
- `contract.parse_action(text) -> GuessAction | ParseError`
- `contract.validate_action(action, state, allowed) -> Ok | Invalid`

### 5.2 Adapter interface

```text
Policy.suggest(public_state) -> SuggestionResult
```

Implementations:

| Policy id | Behavior |
|---|---|
| `solver` | Deterministic frequency / expected-reduction heuristic |
| `base` | `Qwen/Qwen2.5-1.5B-Instruct` (configurable) with no adapter |
| `rft` | Same base + PEFT LoRA from `LORA_ADAPTER_PATH` |

Shared behavior: generate text → parse JSON → validate against allowed list and session → return structured result. Never mutate game state inside the adapter; routes decide whether to apply.

### 5.3 Deterministic solver (required baseline)

`solvers/frequency.py`:

1. Filter answer candidates consistent with feedback so far.
2. Score each legal guess by expected remaining-set reduction (or frequency proxy if too slow).
3. Stable tie-break via fixed letter frequencies + lexicographic order.

Must be pure and seeded-independent given the same board; unit-test against fixed fixtures.

### 5.4 Loading and performance

- Lazy-load model on first `/suggest` or at startup (config flag).
- Pin `MODEL_ID` + revision in config; record in health/metrics.
- Support CPU fallback for smoke tests with a stub policy in pytest.
- Keep generation short (single short JSON line); stop sequences for `}` / newline as needed.

**Phase 3 exit:** `/suggest` works with `solver` and `base`; evaluation harness can call the same policies offline.

## 6. Offline training and evaluation backend (Phases 3b–4)

These are CLI/library modules under `training/`, not required to run inside the web process.

### 6.1 Data and rollouts

- Seeded episode/state generator using train/val/test answer files.
- One-turn dataset: serialize `public_view` prompts from deterministic partial games.
- Episode runner: loop suggest → `apply_guess` → append feedback until win/loss.

### 6.2 Rewards (`training/rewards.py`)

Starting weights (from parent report); log each component:

| Component | Weight |
|---|---|
| Solve | `+5.0` |
| Legal non-repeat | `+0.1` |
| Invalid / malformed / repeat | `-1.0` |
| Progress (`Δ` candidate reduction, clipped `[0,1]`) | `+0.5 × Δ` |
| Turn cost | `-0.05` |

Reward function must use engine copies only; never expose answer to the policy model.

### 6.3 Hardware gate

`training/hardware_gate.py`:

- Load planned model + LoRA config.
- Run one tiny GRPO / generate step.
- Record peak GPU/CPU memory, step time, tokens/sec.
- Exit non-zero if step fails or memory headroom is insufficient.
- Write `artifacts/hardware_gate.json`.

### 6.4 GRPO training

`training/train_grpo.py`:

- TRL `GRPOTrainer` + PEFT LoRA.
- Custom deterministic reward callable.
- Save adapter under `artifacts/adapters/<run_id>/`.
- Write run config snapshot (model revision, seeds, reward weights, list hashes, package versions).

### 6.5 Evaluation

`training/eval_episodes.py`:

- Fixed held-out seeds and test answers.
- Metrics: win rate + CI, mean guesses (wins / all), invalid rate, JSON parse rate, latency, memory.
- Compare `base`, `rft`, `solver` side by side.
- Emit `artifacts/metrics/<run_id>.json` and `.csv`.

Promotion rule: load `rft` in the API only if held-out episode win rate beats `base` without unacceptable legality/latency regressions.

**Phase 4–5 exit:** Reproducible train + eval artifacts; API can select promoted adapter.

## 7. Dependencies and config

Pin versions in `requirements.txt` when implementing (illustrative groups):

- API: `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`
- Engine/tests: `pytest`, `httpx`
- ML: `torch`, `transformers`, `trl`, `peft`, `accelerate` (and optional bitsandbytes)
- Config/logging: `pyyaml`, `structlog` or stdlib logging

`configs/default.yaml` should include model id/revision, LoRA rank, reward weights, seeds, paths, and policy default.

## 8. Backend work breakdown (checklist)

### Phase 1 — Foundation

- [ ] Add licensed word lists + attribution file
- [ ] Implement `score_guess` + `GameState` + `apply_guess`
- [ ] Implement loaders, content hashes, disjoint splits
- [ ] Pytest: duplicates, win/loss, invalid guesses, no answer leakage in public view

### Phase 2 — Playable API

- [ ] Settings + app factory + lifespan
- [ ] Session store (in-memory)
- [ ] Routes: create game, get state, submit guess, health
- [ ] Pydantic schemas and typed error codes
- [ ] API tests with TestClient

### Phase 3 — Baselines and suggest

- [ ] Prompt/parse/validate contract
- [ ] Deterministic solver policy
- [ ] Base-model adapter (stub-friendly for CI)
- [ ] `POST /games/{id}/suggest`
- [ ] Offline episode eval against solver + base
- [ ] Record baseline metrics

### Phase 3b — Hardware gate

- [ ] Dry-run script + `artifacts/hardware_gate.json`
- [ ] Go/no-go decision documented for 1.5B + planned batch

### Phase 4 — RFT pipeline

- [ ] Reward components + unit tests
- [ ] One-turn rollout dataset builder
- [ ] `train_grpo.py` with pinned config snapshot
- [ ] JSONL logging of rollouts/rewards
- [ ] Save LoRA adapter + run metadata

### Phase 5 — Compare and integrate

- [ ] Held-out eval: base vs rft vs solver
- [ ] Promotion gate on episode win rate
- [ ] Registry loads `rft` adapter behind same suggest interface
- [ ] Config switch `MODEL_POLICY=base|rft|solver`

### Phase 6 — Backend documentation artifacts

- [ ] Experiment report fields: hardware, versions, splits, rewards, metrics, limitations
- [ ] Keep this plan + parent report in sync if decisions change

## 9. Backend acceptance criteria

The backend MVP is done when:

1. Engine tests pass, including duplicate-letter feedback.
2. A client can play a full game using only public API fields.
3. AI suggestion never returns or logs the answer.
4. Invalid model outputs are rejected with a clear error, not applied as guesses.
5. Solver and base policies produce reproducible evaluation metrics on fixed seeds.
6. After RFT, metrics show whether the adapter beat the base model on held-out episode win rate.
7. Training/eval use the same engine as the API.

Out of scope for this backend plan: React/Vite UI polish, deployment/orchestration beyond local run, and unconstrained free-generation experiments.

## 10. Suggested local run commands (target)

```bash
# API
uvicorn backend.app.main:app --reload --port 8000

# Tests
pytest backend/tests -q

# Baselines / eval
python -m backend.training.eval_episodes --config configs/default.yaml --policy base,solver

# Hardware gate
python -m backend.training.hardware_gate --config configs/default.yaml

# Train (after gate passes)
python -m backend.training.train_grpo --config configs/default.yaml
```

Exact module paths may adjust slightly during implementation; keep engine importable without starting the web server.
