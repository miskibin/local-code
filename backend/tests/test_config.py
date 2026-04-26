def test_settings_defaults_env_overrides(monkeypatch):
    monkeypatch.setenv("APP_DB_URL", "sqlite+aiosqlite:///:memory:")
    from app.config import Settings
    s = Settings()
    assert s.ollama_base_url.startswith("http")
    assert s.num_ctx == 32768
    assert s.checkpoint_db_path
