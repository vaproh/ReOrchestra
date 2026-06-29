import time
import random
import asyncio
import re
from dataclasses import dataclass
from typing import Optional
from concurrent.futures import ThreadPoolExecutor


@dataclass
class ActionResult:
    success: bool
    action: str
    link: str
    message: str = ""
    screenshot_path: Optional[str] = None

    def __str__(self) -> str:
        status = "OK" if self.success else "FAIL"
        return f"[{status}] {self.action} -> {self.link}: {self.message}"


def _sleep(min_s: float, max_s: float):
    time.sleep(random.uniform(min_s, max_s))


def _get_button_ref(snapshot: str, label: str):
    """Get button ref by label (partial match)."""
    for match in re.findall(r'button "([^"]+)" \[(e\d+)\]', snapshot):
        if label.lower() in match[0].lower():
            return match[1]
    return None


class ActionService:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=4)

    async def upvote_browser(self, username: str, password: str, target_url: str, proxy=None, profile_id=None) -> ActionResult:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._vote_browser_sync,
            username,
            password,
            target_url,
            True,
        )

    async def downvote_browser(self, username: str, password: str, target_url: str, proxy=None, profile_id=None) -> ActionResult:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._vote_browser_sync,
            username,
            password,
            target_url,
            False,
        )

    def _vote_browser_sync(
        self,
        username: str,
        password: str,
        target_url: str,
        upvote: bool,
    ) -> ActionResult:
        from app.services.browser import CamofoxClient

        vote_type = "upvote" if upvote else "downvote"
        client = None
        tab = None

        try:
            client = CamofoxClient()

            # Login if needed - go directly to login page
            tab = client.create_tab("https://old.reddit.com/login/")
            _sleep(4, 6)

            snapshot, _ = client.snapshot(tab)

            # Check if already logged in
            if "welcome back" in snapshot.lower() and "already logged in" in snapshot.lower():
                # Already logged in, skip login and go to voting
                pass
            else:
                refs = _get_input_refs_from_snapshot(snapshot)
                login_btn = _get_button_ref(snapshot, "log in")

                if "username" in refs:
                    client.type_text(tab, refs["username"], username, delay=1)
                if "password" in refs:
                    client.type_text(tab, refs["password"], password, delay=1)
                _sleep(0.5, 1)

                if login_btn:
                    client.click(tab, login_btn, delay=8)

                snapshot, url = client.snapshot(tab)
                if "login" in url.lower():
                    return ActionResult(success=False, action=vote_type, link=target_url, message="Login failed")

            # Navigate to post (use old.reddit.com for faster loading)
            post_url = target_url.replace("https://www.reddit.com", "https://old.reddit.com").replace("http://www.reddit.com", "https://old.reddit.com")
            client.navigate(tab, post_url, wait=5)

            # Scroll to reveal content
            for _ in range(4):
                client.scroll(tab, "down", 800, 1)

            # Find and click upvote button
            snapshot, _ = client.snapshot(tab)

            label = "upvote" if upvote else "downvote"
            btn_ref = _get_button_ref(snapshot, label)

            if btn_ref:
                client.click(tab, btn_ref, delay=2)
                return ActionResult(success=True, action=vote_type, link=target_url, message="Vote registered")

            return ActionResult(success=False, action=vote_type, link=target_url, message="Upvote button not found")

        except Exception as e:
            return ActionResult(success=False, action=vote_type, link=target_url, message=str(e))

        finally:
            if tab and client:
                client.close_tab(tab)


def _get_input_refs_from_snapshot(snapshot: str):
    """Get input field refs from accessibility snapshot."""
    refs = {}
    for match in re.findall(r'textbox "([^"]+)" \[(e\d+)\]', snapshot):
        refs[match[0]] = match[1]
    for match in re.findall(r'passwordbox "([^"]+)" \[(e\d+)\]', snapshot):
        refs[match[0]] = match[1]
    return refs