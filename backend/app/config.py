"""Application settings."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    word_list_dir: Path = DATA_DIR
    allowed_guesses_file: str = "allowed_guesses.txt"
    answers_file: str = "answers.txt"
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    session_ttl_seconds: int = 60 * 60 * 24

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
