import os

os.environ.setdefault("APP_DB_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("CHECKPOINT_DB_PATH", ":memory:")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("OLLAMA_MODEL", "gemma4:e4b")
