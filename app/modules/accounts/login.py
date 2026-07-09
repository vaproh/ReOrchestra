import os
import time
import random
import asyncio
import re
import logging
from typing import Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from app.config import get_settings
from app.modules.executor.browser import CamofoxClient
from app.models import get_db, Account

logger = logging.getLogger("login")


def _sleep(min_s: float, max_s: float):
    time.sleep(random.uniform(min_s, max_s))


def _find_fields(snapshot: str):
    refs = {}
    for match in re.findall(r'textbox "([^"]+)" \[(e\d+)\]', snapshot):
        refs[match[0]] = match[1]
    for match in re.findall(r'passwordbox "([^"]+)" \[(e\d+)\]', snapshot):
        refs[match[0]] = match[1]
    return refs


def _find_button(snapshot: str, label: str):
    for match in re.findall(r'button "([^"]+)" \[(e\d+)\]', snapshot):
        if label.lower() in match[0].lower():
            return match[1]
    return None


def _do_login_sync(
    username: str,
    password: str,
    proxy: Optional[str],
    user_id: str,
) -> Tuple[bool, int]:
    client = None
    tab = None
    start_time = time.time()

    try:
        client = CamofoxClient(user_id=user_id, session_key=f"login_{username}")

        if proxy:
            client.set_user_proxy(user_id, proxy)

        tab = client.create_tab("https://old.reddit.com/login/")
        client.wait(tab)

        snapshot, _ = client.snapshot_quick(tab)
        if (
            "welcome back" in snapshot.lower()
            and "already logged in" in snapshot.lower()
        ):
            logger.debug(f"Session valid: {username}", extra={"username": username})
            return True, 1000

        refs = _find_fields(snapshot)

        if "Email or username" in refs:
            client.type_text(tab, refs["Email or username"], username, delay=1)
        if "Password" in refs:
            client.type_text(tab, refs["Password"], password, delay=1)

        _sleep(0.5, 1)

        login_btn = _find_button(snapshot, "Log In")
        if login_btn:
            client.click(tab, login_btn, delay=8)

        snapshot, url = client.snapshot_quick(tab)

        if "login" not in url.lower():
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.info(
                f"Login success: {username} ({elapsed_ms}ms)",
                extra={"username": username, "ms": elapsed_ms},
            )
            return True, 5000

        logger.warning(
            f"Login failed: {username} - invalid_credentials",
            extra={"username": username, "reason": "invalid_credentials"},
        )
        return False, 0

    except Exception as e:
        logger.error(
            f"Login error: {username} - {e}",
            extra={"username": username, "error": str(e)},
            exc_info=True,
        )
        return False, 0

    finally:
        if tab and client:
            client.close_tab(tab)


class LoginService:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=4)

    async def login(
        self,
        username: str,
        password: str,
        proxy: Optional[str] = None,
        force: bool = False,
        headless: bool = False,
    ) -> Tuple[bool, int]:
        has_proxy = proxy is not None

        logger.info(
            f"Login attempt: {username}",
            extra={"username": username, "has_proxy": has_proxy},
        )

        account_id = None
        db = next(get_db())
        try:
            account = db.query(Account).filter(Account.username == username).first()
            if account:
                account_id = account.id
        finally:
            db.close()

        if not account_id:
            logger.error(f"login | account_not_found | username={username}")
            return False, 0

        user_id = f"s_{account_id}"
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            _do_login_sync,
            username,
            password,
            proxy,
            user_id,
        )
        return result
