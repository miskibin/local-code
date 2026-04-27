from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_base_url: str = "http://localhost:11434"
    num_ctx: int = 16384
    keep_alive: int = -1
    temperature: float = 0.2
    top_p: float = 0.95
    top_k: int = 64

    app_db_url: str = "sqlite+aiosqlite:///./app.db"
    checkpoint_db_path: str = "./checkpoints.db"
    chinook_db_path: str = "./data/chinook.db"
    uploads_dir: str = "./data/uploads"
    skills_dir: str = "./data/skills"

    cors_origins: list[str] = ["http://localhost:3000"]
    log_level: str = "DEBUG"

    google_api_key: str = ""

    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"

    python_sessions_dir: str = "./data/python_sessions"
    python_sandbox_timeout: int = 30
    python_sandbox_allow_net: list[str] = [
        "cdn.jsdelivr.net",
        "pypi.org",
        "files.pythonhosted.org",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
