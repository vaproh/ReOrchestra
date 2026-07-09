import time
import logging
import requests
from typing import Optional
from dataclasses import dataclass

from app.config import get_settings

logger = logging.getLogger("browser")


@dataclass
class Tab:
    tab_id: str
    user_id: str
    session_key: str


class CamofoxClient:
    BASE_URL: str

    def __init__(
        self, base_url: str | None = None, user_id: str = "u1", session_key: str = "s1"
    ):
        settings = get_settings()
        if base_url is None:
            base_url = f"http://localhost:{settings.camofox_port}"
        self.BASE_URL = base_url
        self.user_id = user_id
        self.session_key = session_key
        self._settings = settings

    def _url(self, path: str) -> str:
        return f"{self.BASE_URL}{path}"

    def create_tab(self, url: str = "about:blank") -> Tab:
        logger.debug(f"create_tab url={url}", extra={"url": url})
        resp = requests.post(
            self._url("/tabs"),
            json={
                "userId": self.user_id,
                "sessionKey": self.session_key,
                "url": url,
            },
            timeout=self._settings.timeout_camofox_tab_create,
        )
        resp.raise_for_status()
        data = resp.json()
        tab_id = data["tabId"]
        logger.debug(f"create_tab tab_id={tab_id}", extra={"tab_id": tab_id})
        return Tab(
            tab_id=tab_id,
            user_id=self.user_id,
            session_key=self.session_key,
        )

    def wait(self, tab: Tab, timeout: int = 5000, wait_network: bool = True) -> dict:
        """Wait for page readiness via POST /tabs/:tabId/wait."""
        logger.debug(
            f"wait tab={tab.tab_id} timeout={timeout}ms",
            extra={"tab_id": tab.tab_id, "timeout": timeout},
        )
        try:
            resp = requests.post(
                self._url(f"/tabs/{tab.tab_id}/wait"),
                json={
                    "userId": tab.user_id,
                    "timeout": timeout,
                    "waitForNetwork": wait_network,
                },
                timeout=timeout / 1000 + 5,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(
                f"Browser error: {e}", extra={"error": str(e)}, exc_info=True
            )
            return {"ok": False, "ready": False}

    def snapshot_quick(self, tab: Tab) -> tuple[str, str]:
        """Snapshot with minimal settle (no explicit wait)."""
        logger.debug(f"browser | snapshot_quick | tab_id={tab.tab_id}")
        resp = requests.get(
            self._url(f"/tabs/{tab.tab_id}/snapshot"),
            params={"userId": tab.user_id},
            timeout=self._settings.timeout_camofox_snapshot,
        )
        resp.raise_for_status()
        data = resp.json()
        snapshot_len = len(data.get("snapshot", ""))
        logger.debug(
            f"browser | snapshot_quick | tab_id={tab.tab_id} snapshot_len={snapshot_len}"
        )
        return data.get("snapshot", ""), data.get("url", "")

    def type_text(self, tab: Tab, ref: str, text: str, delay: float = 0.5) -> None:
        logger.debug(
            f"browser | type_text | tab_id={tab.tab_id} ref={ref} text_len={len(text)}"
        )
        resp = requests.post(
            self._url(f"/tabs/{tab.tab_id}/type"),
            json={"userId": tab.user_id, "ref": ref, "text": text},
            timeout=self._settings.timeout_camofox_type,
        )
        resp.raise_for_status()
        time.sleep(delay)

    def click(self, tab: Tab, ref: str, delay: float = 2.0) -> None:
        logger.debug(
            f"click tab={tab.tab_id} ref={ref}",
            extra={"tab_id": tab.tab_id, "ref": ref},
        )
        resp = requests.post(
            self._url(f"/tabs/{tab.tab_id}/click"),
            json={"userId": tab.user_id, "ref": ref},
            timeout=self._settings.timeout_camofox_click,
        )
        resp.raise_for_status()
        time.sleep(delay)

    def close_tab(self, tab: Tab) -> None:
        logger.debug(f"close_tab tab={tab.tab_id}", extra={"tab_id": tab.tab_id})
        try:
            requests.delete(
                self._url(f"/tabs/{tab.tab_id}"),
                params={"userId": tab.user_id},
                timeout=self._settings.timeout_camofox_close,
            )
        except requests.exceptions.RequestException as e:
            logger.warning(
                f"Browser error: {e}", extra={"error": str(e)}, exc_info=True
            )

    def set_user_proxy(self, user_id: str, proxy: str) -> dict:
        """Assign proxy to user via sticky-proxy plugin."""
        logger.debug(f"browser | set_user_proxy | user_id={user_id} proxy={proxy}")
        resp = requests.post(
            self._url(f"/users/{user_id}/proxy"),
            json={"proxy_string": proxy},
            timeout=self._settings.timeout_camofox_proxy,
        )
        resp.raise_for_status()
        return resp.json()
