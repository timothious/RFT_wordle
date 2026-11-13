"""Application settings."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    word_list_dir: Path = DATA_DIR
    allowed_guesses_file: str = "allowed_guesses.txt"
    answers_file: str = "answers.txt"
    answers_train_file: str = "answers_train.txt"
    answers_val_file: str = "answers_val.txt"
    answers_test_file: str = "answers_test.txt"
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    session_ttl_seconds: int = 60 * 60 * 24

    # Suggestion / LM
    model_policy: str = "solver"
    model_id: str = "Qwen/Qwen2.5-1.5B-Instruct"
    model_revision: str = "main"
    model_device: str = "cpu"
    lora_adapter_path: str | None = None
    enable_lm: bool = False
    max_new_tokens: int = 32

    # Reward defaults (also in configs/default.yaml for training)
    reward_solve: float = 5.0
    reward_legal: float = 0.1
    reward_invalid: float = -1.0
    reward_progress: float = 0.5
    reward_turn_cost: float = -0.05

    artifacts_dir: Path = ROOT_DIR / "backend" / "artifacts"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
