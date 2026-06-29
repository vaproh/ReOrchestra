import re
import requests
from typing import Optional


class StickyProxyClient:
    def __init__(self, camofox_base_url: str = "http://localhost:9377"):
        self.base_url = camofox_base_url.rstrip("/")

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _post(self, path: str, **kwargs) -> requests.Response:
        return requests.post(self._url(path), **kwargs)

    def _get(self, path: str, **kwargs) -> requests.Response:
        return requests.get(self._url(path), **kwargs)

    def _delete(self, path: str, **kwargs) -> requests.Response:
        return requests.delete(self._url(path), **kwargs)

    def set_proxy(self, user_id: str, proxy_string: str) -> dict:
        parsed = self.parse_proxy_string(proxy_string)
        if not parsed:
            raise ValueError(f"Invalid proxy_string format: {proxy_string}")

        resp = requests.post(
            self._url(f"/users/{user_id}/proxy"),
            json={"proxy_string": proxy_string},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def get_proxy(self, user_id: str) -> Optional[dict]:
        resp = requests.get(
            self._url(f"/users/{user_id}/proxy"),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return data if data else None

    def delete_proxy(self, user_id: str) -> dict:
        resp = requests.delete(
            self._url(f"/users/{user_id}/proxy"),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def list_users(self) -> dict:
        resp = requests.get(self._url("/users"), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def parse_proxy_string(self, proxy_string: str) -> Optional[dict]:
        # Strip protocol prefix if present
        clean = proxy_string
        if clean.startswith("http://"):
            clean = clean[7:]
        elif clean.startswith("https://"):
            clean = clean[8:]

        # Format: user:pass@gateway:port
        m = re.match(r"([^:]+):([^@]+)@([^:]+):(\d+)$", clean)
        if m:
            return {
                "server": f"http://{m.group(3)}:{m.group(4)}",
                "username": m.group(1),
                "password": m.group(2),
            }

        # Format: host:port:user:pass
        m = re.match(r"([^:]+):(\d+):([^:]+):(.+)$", clean)
        if m:
            return {
                "server": f"http://{m.group(1)}:{m.group(2)}",
                "username": m.group(3),
                "password": m.group(4),
            }

        return None

    def health_check(self) -> dict:
        resp = requests.get(self._url("/health"), timeout=5)
        resp.raise_for_status()
        return resp.json()
