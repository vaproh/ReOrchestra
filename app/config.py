try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

from functools import lru_cache
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

    # ===== TIMEOUTS (seconds) =====
    timeout_camofox_tab_create: int = 15
    timeout_camofox_navigate: int = 30
    timeout_camofox_click: int = 60
    timeout_camofox_snapshot: int = 30
    timeout_camofox_type: int = 30
    timeout_camofox_scroll: int = 30
    timeout_camofox_close: int = 10
    timeout_camofox_health: int = 5
    timeout_camofox_proxy: int = 10
    timeout_sticky_proxy: int = 10
    timeout_slot_health: int = 5
    timeout_admin_health: int = 3
    action_timeout_seconds: int = 120
    post_click_wait_ms: int = 3000

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
