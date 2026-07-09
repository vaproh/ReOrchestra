try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pydantic import ConfigDict

from functools import lru_cache
import os


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    # ===== PATHS =====
    database_url: str = "sqlite:///./data/reddit.db"
    log_dir: str = "data/logs"

    # ===== CAMOFOX =====
    camofox_port: int = 9377
    camofox_dir: str = "../camofox"

    # ===== PROXY =====
    proxy_mode: str = "sticky"
    use_proxies_by_default: bool = True

    # ===== VNC =====
    vnc_enabled: bool = False
    vnc_port: int = 5999

    # ===== ACTION TIMING =====
    action_delay_ms_min: int = 1000
    action_delay_ms_max: int = 3000
    batch_size_default: int = 50

    # ===== QUEUE =====
    max_concurrent_per_task: int = 1

    # ===== LOGGING =====
    log_level: str = "INFO"

    # ===== CORS =====
    cors_allowed_origins: str = "*"

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

    @property
    def cors_origins(self) -> list[str]:
        if not self.cors_allowed_origins:
            return ["*"]
        origins = [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]
        return origins if origins else ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
