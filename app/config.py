try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

from functools import lru_cache
from typing import Literal
import os


class Settings(BaseSettings):
    # ===== PATHS =====
    proxy_file: str = "data/proxies.txt"
    database_url: str = "sqlite:///./data/reddit.db"
    session_dir: str = "data/sessions"
    log_dir: str = "data/logs"
    profiles_path: str = "profiles.json"

    # ===== CAMOFOX =====
    camofox_port: int = 9377
    camofox_dir: str = "../camofox"

    # ===== PROXY =====
    proxy_mode: str = "sticky"
    use_proxies_by_default: bool = True

    # ===== VNC =====
    vnc_enabled: bool = False
    vnc_port: int = 5999

    # ===== SESSION =====
    max_session_age_hours: int = 72

    # ===== ACTION TIMING =====
    action_delay_ms_min: int = 1000
    action_delay_ms_max: int = 3000
    batch_size_default: int = 50

    # ===== LOGGING =====
    log_level: str = "INFO"

    # ===== CAPTCHA =====
    capsolver_api_key: str | None = None
    twocaptcha_api_key: str | None = None

    # ===== MODE =====
    app_mode: Literal["production", "test"] = "production"

    # ===== TEST MODE =====
    test_server_url: str = "http://localhost:8080"
    test_server_port: int = 8080
    test_db_url: str = "sqlite:///./data/test.db"
    test_session_dir: str = "data/test_sessions"

    # ===== TUNNEL =====
    tunnel_domain: str = "vaproh.space"
    tunnel_subdomain: str = "reorchestra-test"
    tunnel_name: str = "reorchestra-test"
    tunnel_port: int = 8080

    @property
    def is_test_mode(self) -> bool:
        return self.app_mode == "test"

    @property
    def camofox_path(self) -> str:
        if os.path.isabs(self.camofox_dir):
            return self.camofox_dir
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(project_root, self.camofox_dir)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
