import json
import time
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Account, AccountStatus, ActionLog
from app.services.proxy_service import ProxyService
from app.services.sticky_proxy import StickyProxyClient
from app.services.rate_limiter import RateLimiter
from app.services.burn_detector import BurnDetector


@dataclass
class SessionInfo:
    account_id: int
    username: str
    slot_id: Optional[str]
    tab_id: Optional[str]
    logged_in: bool
    session_valid: bool


class AccountService:
    def __init__(self, camofox_base_url: str = "http://localhost:9377"):
        self.camofox_base_url = camofox_base_url
        self.camofox = StickyProxyClient(camofox_base_url)
        self.proxy_service = ProxyService()
        self.rate_limiter = RateLimiter()
        self.burn_detector = BurnDetector()
        self._active_sessions: dict[int, dict] = {}

    def _get_user_id(self, account_id: int) -> str:
        return f"s_{account_id}"

    def _ensure_proxy(self, db: Session, account: Account) -> bool:
        proxy = self.proxy_service.get_proxy_for_account(db, account.id)
        if not proxy:
            proxy = self.proxy_service.assign_proxy_to_account(db, account.id)
            if not proxy:
                return False

        user_id = self._get_user_id(account.id)
        try:
            self.camofox.set_proxy(user_id, proxy.proxy_string)
            return True
        except Exception as e:
            print(f"Failed to set proxy for {account.username}: {e}")
            return False

    def login(self, db: Session, account_id: int, headless: bool = True) -> dict:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            return {"success": False, "error": "Account not found"}

        user_id = self._get_user_id(account_id)

        has_cookies = bool(account.cookies)
        session_key = f"{account.username}_session"

        try:
            if has_cookies:
                resp = self.camofox.list_users()
                if user_id in resp.get("users", []):
                    proxy_ok = self._ensure_proxy(db, account)
                    return {
                        "success": True,
                        "resumed": True,
                        "username": account.username,
                        "proxy_active": proxy_ok,
                    }

            proxy_ok = self._ensure_proxy(db, account)
            if not proxy_ok:
                return {"success": False, "error": "No proxy available"}

            session_data = {
                "userId": user_id,
                "sessionKey": session_key,
                "url": "https://www.reddit.com",
                "headless": headless,
            }

            resp = self.camofox._post("/tabs", json=session_data)
            if resp.status_code != 200:
                return {"success": False, "error": f"Tab creation failed: {resp.status_code}"}

            tab_data = resp.json()
            tab_id = tab_data.get("tabId")

            if not tab_id:
                return {"success": False, "error": "No tab ID returned"}

            time.sleep(2)

            self._active_sessions[account_id] = {
                "tab_id": tab_id,
                "user_id": user_id,
                "session_key": session_key,
                "started_at": datetime.utcnow(),
            }

            account.status = AccountStatus.logged_in
            account.session_valid = True
            account.last_login = datetime.utcnow()
            db.commit()

            return {
                "success": True,
                "resumed": False,
                "username": account.username,
                "tab_id": tab_id,
                "proxy_active": proxy_ok,
            }

        except Exception as e:
            account.consecutive_failures += 1
            account.last_failure_at = datetime.utcnow()
            db.commit()
            return {"success": False, "error": str(e)}

    def logout(self, db: Session, account_id: int) -> dict:
        session = self._active_sessions.get(account_id)
        if not session:
            return {"success": False, "error": "No active session"}

        try:
            tab_id = session["tab_id"]
            user_id = session["user_id"]
            self.camofox._delete(f"/tabs/{tab_id}?userId={user_id}")
        except Exception as e:
            pass

        if account_id in self._active_sessions:
            del self._active_sessions[account_id]

        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.status = AccountStatus.session_expired
            account.session_valid = False
            db.commit()

        return {"success": True}

    def check_session(self, db: Session, account_id: int) -> bool:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            return False

        if account.status == AccountStatus.banned:
            return False

        if account.status == AccountStatus.dead:
            return False

        if not account.session_valid:
            return False

        if account.consecutive_failures >= 3:
            return False

        user_id = self._get_user_id(account_id)
        try:
            health = self.camofox.health_check()
            return health.get("browserConnected", False)
        except:
            return False

    def get_active_tab(self, account_id: int) -> Optional[str]:
        session = self._active_sessions.get(account_id)
        return session.get("tab_id") if session else None

    def get_session_info(self, db: Session, account_id: int) -> SessionInfo:
        account = db.query(Account).filter(Account.id == account_id).first()
        session = self._active_sessions.get(account_id)

        return SessionInfo(
            account_id=account_id,
            username=account.username if account else None,
            slot_id=None,
            tab_id=session.get("tab_id") if session else None,
            logged_in=account.status == AccountStatus.logged_in if account else False,
            session_valid=account.session_valid if account else False,
        )


def get_account_service() -> AccountService:
    return AccountService()
