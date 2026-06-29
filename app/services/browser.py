import json
import time
import logging
import requests
from typing import Optional
from dataclasses import dataclass

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger("browser")


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
        logger.debug(f"browser | create_tab | url={url}")
        resp = requests.post(self._url("/tabs"), json={
            "userId": self.user_id,
            "sessionKey": self.session_key,
            "url": url,
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        logger.debug(f"browser | create_tab | tab_id={data['tabId']}")
        return Tab(
            tab_id=data["tabId"],
            user_id=self.user_id,
            session_key=self.session_key,
        )

    def navigate(self, tab: Tab, url: str, wait: float = 5.0) -> str:
        logger.debug(f"browser | navigate | tab_id={tab.tab_id} url={url}")
        resp = requests.post(
            self._url(f"/tabs/{tab.tab_id}/navigate"),
            json={"userId": tab.user_id, "url": url},
            timeout=30,
        )
        resp.raise_for_status()
        time.sleep(wait)
        result_url = resp.json().get("url", "")
        logger.debug(f"browser | navigate | tab_id={tab.tab_id} result_url={result_url}")
        return result_url

    def wait(self, tab: Tab, timeout: int = 5000, wait_network: bool = True) -> dict:
        """Wait for page readiness via POST /tabs/:tabId/wait."""
        logger.debug(f"browser | wait | tab_id={tab.tab_id} timeout={timeout}ms")
        try:
            resp = requests.post(
                self._url(f"/tabs/{tab.tab_id}/wait"),
                json={"userId": tab.user_id, "timeout": timeout, "waitForNetwork": wait_network},
                timeout=timeout / 1000 + 5,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"browser | wait | tab_id={tab.tab_id} error={e}")
            return {"ok": False, "ready": False}

    def snapshot_quick(self, tab: Tab) -> tuple[str, str]:
        """Snapshot with minimal settle (no explicit wait)."""
        logger.debug(f"browser | snapshot_quick | tab_id={tab.tab_id}")
        resp = requests.get(
            self._url(f"/tabs/{tab.tab_id}/snapshot"),
            params={"userId": tab.user_id},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        snapshot_len = len(data.get("snapshot", ""))
        logger.debug(f"browser | snapshot_quick | tab_id={tab.tab_id} snapshot_len={snapshot_len}")
        return data.get("snapshot", ""), data.get("url", "")

    def snapshot(self, tab: Tab, wait_ready: bool = True, timeout: int = 5000) -> tuple[str, str]:
        """Returns (snapshot_text, current_url). Optionally waits for page readiness first."""
        if wait_ready:
            self.wait(tab, timeout=timeout, wait_network=True)
        return self.snapshot_quick(tab)

    def type_text(self, tab: Tab, ref: str, text: str, delay: float = 0.5) -> None:
        logger.debug(f"browser | type_text | tab_id={tab.tab_id} ref={ref} text_len={len(text)}")
        resp = requests.post(
            self._url(f"/tabs/{tab.tab_id}/type"),
            json={"userId": tab.user_id, "ref": ref, "text": text},
            timeout=30,
        )
        resp.raise_for_status()
        time.sleep(delay)

    def click(self, tab: Tab, ref: str, delay: float = 2.0) -> None:
        logger.debug(f"browser | click | tab_id={tab.tab_id} ref={ref}")
        resp = requests.post(
            self._url(f"/tabs/{tab.tab_id}/click"),
            json={"userId": tab.user_id, "ref": ref},
            timeout=60,
        )
        resp.raise_for_status()
        time.sleep(delay)

    def scroll(self, tab: Tab, direction: str = "down", amount: int = 800, delay: float = 1.0) -> None:
        logger.debug(f"browser | scroll | tab_id={tab.tab_id} direction={direction} amount={amount}")
        resp = requests.post(
            self._url(f"/tabs/{tab.tab_id}/scroll"),
            json={"userId": tab.user_id, "direction": direction, "amount": amount},
            timeout=30,
        )
        resp.raise_for_status()
        time.sleep(delay)

    def close_tab(self, tab: Tab) -> None:
        logger.debug(f"browser | close_tab | tab_id={tab.tab_id}")
        try:
            requests.delete(
                self._url(f"/tabs/{tab.tab_id}"),
                params={"userId": tab.user_id},
                timeout=10,
            )
        except Exception:
            pass

    def health(self) -> dict:
        logger.debug("browser | health_check")
        resp = requests.get(self._url("/"), timeout=5)
        return resp.json()

    def set_user_proxy(self, user_id: str, proxy: str) -> dict:
        """Assign proxy to user via sticky-proxy plugin."""
        logger.debug(f"browser | set_user_proxy | user_id={user_id} proxy={proxy}")
        resp = requests.post(
            self._url(f"/users/{user_id}/proxy"),
            json={"proxy": proxy},
            timeout=10,
        )
        resp.raise_for_status()
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
