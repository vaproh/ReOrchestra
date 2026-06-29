import os
import json
import time
import random
import asyncio
import re
import logging
from typing import Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from app.config import get_settings
from app.services.browser import CamofoxClient

settings = get_settings()
logger = logging.getLogger("login")


def _sleep(min_s: float, max_s: float):
    time.sleep(random.uniform(min_s, max_s))


def _find_fields(snapshot: str):
    """Find input field refs from accessibility snapshot."""
    refs = {}
    for match in re.findall(r'textbox "([^"]+)" \[(e\d+)\]', snapshot):
        refs[match[0]] = match[1]
    for match in re.findall(r'passwordbox "([^"]+)" \[(e\d+)\]', snapshot):
        refs[match[0]] = match[1]
    return refs


def _find_button(snapshot: str, label: str):
    """Get button ref by label (partial match)."""
    for match in re.findall(r'button "([^"]+)" \[(e\d+)\]', snapshot):
        if label.lower() in match[0].lower():
            return match[1]
    return None


def _do_login_sync(
    username: str,
    password: str,
    session_dir: str,
) -> Tuple[bool, int]:
    client = None
    tab = None

    try:
        client = CamofoxClient()

        # Go directly to login page
        tab = client.create_tab("https://old.reddit.com/login/")
        _sleep(4, 6)

        # Step 3: Get snapshot and check if already logged in
        snapshot, _ = client.snapshot(tab)
        if "welcome back" in snapshot.lower() and "already logged in" in snapshot.lower():
            _save_session(username, session_dir, {"username": username, "logged_in": True, "url": "https://www.reddit.com/"})
            logger.info(f"login | already_logged_in | username={username}")
            return True, 1000

        refs = _find_fields(snapshot)

        # Fill "Email or username" and "Password"
        if "Email or username" in refs:
            client.type_text(tab, refs["Email or username"], username, delay=1)
        if "Password" in refs:
            client.type_text(tab, refs["Password"], password, delay=1)

        _sleep(0.5, 1)

        # Click "Log In"
        login_btn = _find_button(snapshot, "Log In")
        if login_btn:
            client.click(tab, login_btn, delay=8)

        # Step 4: Verify login succeeded
        snapshot, url = client.snapshot(tab)

        if "login" not in url.lower():
            # Login successful
            _save_session(username, session_dir, {"username": username, "logged_in": True, "url": url})
            logger.info(f"login | success | username={username}")
            return True, 5000

        logger.warning(f"login | failed | username={username} | reason=invalid_credentials")
        return False, 0

    except Exception as e:
        logger.error(f"login | error | username={username} | error={e}")
        return False, 0

    finally:
        if tab and client:
            client.close_tab(tab)


def _save_session(username: str, session_dir: str, data: dict):
    session_path = os.path.join(session_dir, f"{username}.cookies")
    with open(session_path, "w") as f:
        json.dump(data, f)


class LoginService:
    def __init__(self):
        self.session_dir = settings.session_dir
        self._executor = ThreadPoolExecutor(max_workers=4)

    async def login(
        self,
        username: str,
        password: str,
        proxy: Optional[str] = None,
        profile_id: Optional[str] = None,
        force: bool = False,
        headless: bool = False,
    ) -> Tuple[bool, int]:
        session_path = os.path.join(self.session_dir, f"{username}.cookies")

        if not force and os.path.exists(session_path):
            if self._validate_session(username):
                logger.info(f"login | session_valid | username={username}")
                return True, 0

        logger.info(f"login | attempting | username={username}")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            _do_login_sync,
            username,
            password,
            self.session_dir,
        )
        return result

    def _validate_session(self, username: str) -> bool:
        session_path = os.path.join(self.session_dir, f"{username}.cookies")
        if not os.path.exists(session_path):
            return False
        try:
            with open(session_path, "r") as f:
                data = json.load(f)
            return data.get("logged_in", False)
        except Exception:
            return False

    async def login_with_session(self, username: str) -> bool:
        return self._validate_session(username)

    def logout(self, username: str):
        session_path = os.path.join(self.session_dir, f"{username}.cookies")
        if os.path.exists(session_path):
            os.remove(session_path)
