try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

from functools import lru_cache


class Settings(BaseSettings):
    proxy_file: str = "data/proxies.txt"
    database_url: str = "sqlite:///./data/reddit.db"
    session_dir: str = "data/sessions"
    log_dir: str = "data/logs"
    profiles_path: str = "profiles.json"
    max_session_age_hours: int = 72
    action_delay_ms_min: int = 1000
    action_delay_ms_max: int = 3000
    batch_size_default: int = 50
    log_level: str = "INFO"
    camofox_port: int = 9377
    capsolver_api_key: str | None = None
    twocaptcha_api_key: str | None = None
    use_proxies_by_default: bool = True
    proxy_mode: str = "sticky"
    vnc_enabled: bool = False
    vnc_port: int = 5999

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
