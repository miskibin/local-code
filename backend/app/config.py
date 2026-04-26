from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:e4b"
    num_ctx: int = 32768
    keep_alive: int = -1
    temperature: float = 0.2
    top_p: float = 0.95
    top_k: int = 64

    app_db_url: str = "sqlite+aiosqlite:///./app.db"
    checkpoint_db_path: str = "./checkpoints.db"

    cors_origins: list[str] = ["http://localhost:3000"]
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
