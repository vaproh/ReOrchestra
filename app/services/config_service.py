import os
import yaml
import json
from pathlib import Path
from typing import Any, Optional
from copy import deepcopy

BASE_DIR = Path(__file__).parent.parent.parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config" / "default.yaml"
CUSTOM_CONFIG_PATH = BASE_DIR / "config" / "custom.yaml"
PROXIES_CONFIG_PATH = BASE_DIR / "config" / "proxies.yaml"


class ConfigService:
    _instance: Optional["ConfigService"] = None
    _default_config: dict[str, Any] = {}
    _custom_config: dict[str, Any] = {}
    _proxies_config: dict[str, Any] = {}
    _runtime_overrides: dict[str, Any] = {}
    _profiles: dict[str, Any] = {}

    def __new__(cls) -> "ConfigService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_configs()
        return cls._instance

    def _load_configs(self) -> None:
        self._default_config = self._load_yaml(DEFAULT_CONFIG_PATH)
        self._custom_config = self._load_yaml(CUSTOM_CONFIG_PATH)
        self._proxies_config = self._load_yaml(PROXIES_CONFIG_PATH)
        self._profiles = self._load_profiles()

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        with open(path) as f:
            return yaml.safe_load(f) or {}

    def _load_profiles(self) -> dict[str, Any]:
        profiles_path = BASE_DIR / "profiles.json"
        if not profiles_path.exists():
            return {}
        with open(profiles_path) as f:
            return json.load(f)

    def get(self, *keys: str, default: Any = None) -> Any:
        for source in [self._runtime_overrides, self._custom_config, self._default_config]:
            value = source
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    value = None
                    break
            if value is not None:
                return value
        return default

    def get_proxies_config(self) -> dict[str, Any]:
        return deepcopy(self._proxies_config)

    def get_evomi_config(self) -> dict[str, Any]:
        return deepcopy(self._proxies_config.get("proxy", {}).get("evomi", {}))

    def get_bulk_config(self) -> dict[str, Any]:
        return deepcopy(self._proxies_config.get("proxy", {}).get("bulk", {}))

    def get_session_config(self) -> dict[str, Any]:
        return deepcopy(self._proxies_config.get("proxy", {}).get("session", {}))

    def get_profiles(self) -> dict[str, Any]:
        return deepcopy(self._profiles)

    def get_profile(self, profile_id: str) -> Optional[dict[str, Any]]:
        for p in self._profiles.get("profiles", []):
            if p.get("id") == profile_id:
                return deepcopy(p)
        return None

    def list_profile_ids(self) -> list[str]:
        return [p.get("id") for p in self._profiles.get("profiles", [])]

    def set_runtime_override(self, key_path: str, value: Any) -> None:
        keys = key_path.split(".")
        target = self._runtime_overrides
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value

    def clear_runtime_overrides(self) -> None:
        self._runtime_overrides = {}

    def reload(self) -> None:
        self._load_configs()

    def get_all(self) -> dict[str, Any]:
        result = deepcopy(self._default_config)
        self._deep_merge(result, self._custom_config)
        self._deep_merge(result, self._runtime_overrides)
        return result

    def _deep_merge(self, base: dict, overlay: dict) -> None:
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = deepcopy(value)


def get_config() -> ConfigService:
    return ConfigService()
