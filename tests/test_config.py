import pytest
from app.config import get_settings, Settings


def test_settings_defaults():
    settings = get_settings()
    assert settings.database_url == "sqlite:///./data/reddit.db"
    assert settings.max_session_age_hours == 72
    assert settings.action_delay_ms_min == 1000
    assert settings.action_delay_ms_max == 3000


def test_settings_env_override(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("MAX_SESSION_AGE_HOURS", "48")

    settings = get_settings()
    assert settings.database_url == "sqlite:///./test.db"
    assert settings.max_session_age_hours == 48
