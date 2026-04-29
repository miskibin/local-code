from functools import lru_cache

from pydantic import field_validator
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
    decks_dir: str = "./data/decks"
    pptx_template_path: str = "./data/pptx_templates/default.pptx"

    cors_origins: list[str] = ["http://localhost:3000"]
    log_level: str = "DEBUG"

    google_api_key: str = ""

    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"

    gitlab_url: str = ""
    gitlab_token: str = ""
    gitlab_project_id: str = ""

    admin_emails: list[str] = []

    @field_validator("admin_emails", "cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [s.strip().lower() for s in v.split(",") if s.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
