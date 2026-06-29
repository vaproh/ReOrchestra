import json
import time
import requests
from typing import Optional
from dataclasses import dataclass

from app.config import get_settings

settings = get_settings()


@dataclass
class Tab:
    tab_id: str
    user_id: str
    session_key: str


class CamofoxClient:
    BASE_URL: str

    def __init__(self, base_url: str | None = None, user_id: str = "u1", session_key: str = "s1"):
        if base_url is None:
            base_url = f"http://localhost:{settings.camofox_port}"
        self.BASE_URL = base_url
        self.user_id = user_id
        self.session_key = session_key

    def _url(self, path: str) -> str:
        return f"{self.BASE_URL}{path}"

    def create_tab(self, url: str = "about:blank") -> Tab:
        resp = requests.post(self._url("/tabs"), json={
            "userId": self.user_id,
            "sessionKey": self.session_key,
            "url": url,
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return Tab(
            tab_id=data["tabId"],
            user_id=self.user_id,
            session_key=self.session_key,
        )

    def navigate(self, tab: Tab, url: str, wait: float = 5.0) -> str:
        resp = requests.post(
            self._url(f"/tabs/{tab.tab_id}/navigate"),
            json={"userId": tab.user_id, "url": url},
            timeout=30,
        )
        resp.raise_for_status()
        time.sleep(wait)
        return resp.json().get("url", "")

    def snapshot(self, tab: Tab) -> tuple[str, str]:
        """Returns (snapshot_text, current_url)"""
        resp = requests.get(
            self._url(f"/tabs/{tab.tab_id}/snapshot"),
            params={"userId": tab.user_id},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("snapshot", ""), data.get("url", "")

    def type_text(self, tab: Tab, ref: str, text: str, delay: float = 0.5) -> None:
        resp = requests.post(
            self._url(f"/tabs/{tab.tab_id}/type"),
            json={"userId": tab.user_id, "ref": ref, "text": text},
            timeout=30,
        )
        resp.raise_for_status()
        time.sleep(delay)

    def click(self, tab: Tab, ref: str, delay: float = 2.0) -> None:
        resp = requests.post(
            self._url(f"/tabs/{tab.tab_id}/click"),
            json={"userId": tab.user_id, "ref": ref},
            timeout=60,
        )
        resp.raise_for_status()
        time.sleep(delay)

    def scroll(self, tab: Tab, direction: str = "down", amount: int = 800, delay: float = 1.0) -> None:
        resp = requests.post(
            self._url(f"/tabs/{tab.tab_id}/scroll"),
            json={"userId": tab.user_id, "direction": direction, "amount": amount},
            timeout=30,
        )
        resp.raise_for_status()
        time.sleep(delay)

    def close_tab(self, tab: Tab) -> None:
        try:
            requests.delete(
                self._url(f"/tabs/{tab.tab_id}"),
                params={"userId": tab.user_id},
                timeout=10,
            )
        except Exception:
            pass

    def health(self) -> dict:
        resp = requests.get(self._url("/"), timeout=5)
        return resp.json()


# Convenience functions for backward compatibility
def create_browser_session(proxy=None, headless=False, profile_id=None):
    """Create a Camofox client (REST API-based, not Selenium).

    Proxy is configured via env vars when Camofox server starts, not per-session.
    """
    return CamofoxClient()


def close_browser(client: CamofoxClient):
    if client:
        # Just disconnect - don't kill the Camofox server
        pass


# Profile functions kept for compatibility
_profiles_cache: Optional[dict] = None


def load_profiles() -> Optional[dict]:
    global _profiles_cache
    if _profiles_cache is None:
        with open(settings.profiles_path) as f:
            _profiles_cache = json.load(f)
    return _profiles_cache


def get_profile(profile_id: str) -> Optional[dict]:
    profiles = load_profiles() or {}
    for p in profiles.get("profiles", []):
        if p["id"] == profile_id:
            return p
    return None


def list_profile_ids() -> list[str]:
    profiles = load_profiles() or {}
    return [p["id"] for p in profiles.get("profiles", [])]
