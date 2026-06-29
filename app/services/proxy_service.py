import os
import re
import random
import string
import secrets
from typing import Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Proxy
from app.services.config_service import get_config
from app.services.sticky_proxy import StickyProxyClient


@dataclass
class ParsedProxy:
    host: str
    port: int
    username: str
    password: str
    raw: str

    @property
    def server(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def http_url(self) -> str:
        return f"http://{self.username}:{self.password}@{self.host}:{self.port}"


def parse_proxy(raw: str) -> Optional[ParsedProxy]:
    raw = raw.strip()
    if not raw:
        return None

    match = re.match(r"https?://([^:]+):(\d+):([^:]+):(.+)$", raw)
    if match:
        return ParsedProxy(
            host=match.group(1),
            port=int(match.group(2)),
            username=match.group(3),
            password=match.group(4),
            raw=raw,
        )

    match = re.match(r"([^:]+):(\d+)$", raw)
    if match:
        return ParsedProxy(
            host=match.group(1),
            port=int(match.group(2)),
            username="",
            password="",
            raw=raw,
        )

    return None


def _generate_session_id(length: int = None) -> str:
    if length is None:
        length = random.randint(6, 10)
    chars = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


class ProxyService:
    def __init__(self):
        self.config = get_config()

    def generate_evomi_session(
        self,
        proxy_host: str,
        proxy_port: int,
        username: str,
        password: str,
        lifetime_minutes: int = None,
    ) -> str:
        evomi_cfg = self.config.get_evomi_config()
        session_cfg = self.config.get_session_config()

        if lifetime_minutes is None:
            lifetime_minutes = session_cfg.get("lifetime_minutes", 40)
        lifetime_minutes = min(lifetime_minutes, 120)

        session_id = _generate_session_id()

        proxy_string = f"http://{username}:{password}_session-{session_id}_lifetime-{lifetime_minutes}@{proxy_host}:{proxy_port}"

        return proxy_string

    def parse_bulk_proxy(self, proxy_str: str) -> Optional[dict]:
        parsed = parse_proxy(proxy_str)
        if not parsed:
            return None

        return {
            "proxy_string": proxy_str,
            "host": parsed.host,
            "port": parsed.port,
            "username": parsed.username,
            "password": parsed.password,
        }

    def import_bulk_proxies(self, db: Session, proxy_strings: list[str]) -> tuple[int, int]:
        imported = 0
        skipped = 0

        for proxy_str in proxy_strings:
            proxy_str = proxy_str.strip()
            if not proxy_str or proxy_str.startswith("#"):
                skipped += 1
                continue

            existing = db.query(Proxy).filter(Proxy.proxy_string == proxy_str).first()
            if existing:
                skipped += 1
                continue

            parsed = self.parse_bulk_proxy(proxy_str)
            if not parsed:
                skipped += 1
                continue

            proxy = Proxy(
                proxy_string=proxy_str,
                proxy_type="bulk",
                host=parsed["host"],
                port=parsed["port"],
                username=parsed.get("username", ""),
                password=parsed.get("password", ""),
                status="active",
                is_active=True,
            )
            db.add(proxy)
            imported += 1

        db.commit()
        return imported, skipped

    def assign_proxy_to_account(
        self,
        db: Session,
        account_id: int,
        proxy_type: str = "bulk",
    ) -> Optional[Proxy]:
        if proxy_type == "evomi":
            evomi_cfg = self.config.get_evomi_config()
            if not evomi_cfg.get("enabled"):
                return None

            proxy_string = self.generate_evomi_session(
                proxy_host=evomi_cfg.get("host", ""),
                proxy_port=evomi_cfg.get("port", 1000),
                username=evomi_cfg.get("username", ""),
                password=evomi_cfg.get("password", ""),
            )

            proxy = Proxy(
                proxy_string=proxy_string,
                proxy_type="evomi",
                provider="evomi",
                assigned_account_id=account_id,
                session_id=_generate_session_id(),
                status="active",
                is_active=True,
            )
            db.add(proxy)
            db.commit()
            return proxy

        existing = db.query(Proxy).filter(
            Proxy.assigned_account_id == account_id
        ).first()
        if existing:
            return existing

        available = db.query(Proxy).filter(
            Proxy.assigned_account_id == None,
            Proxy.is_active == True,
            Proxy.proxy_type == "bulk",
        ).first()

        if available:
            available.assigned_account_id = account_id
            db.commit()
            return available

        return None

    def get_proxy_for_account(self, db: Session, account_id: int) -> Optional[Proxy]:
        return db.query(Proxy).filter(
            Proxy.assigned_account_id == account_id,
            Proxy.is_active == True,
        ).first()

    def unassign_proxy(self, db: Session, account_id: int) -> bool:
        proxy = self.get_proxy_for_account(db, account_id)
        if proxy:
            proxy.assigned_account_id = None
            db.commit()
            return True
        return False

    def mark_proxy_dead(self, db: Session, proxy_id: int, error: str = None) -> None:
        proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
        if proxy:
            proxy.status = "dead"
            proxy.is_active = False
            proxy.fail_count += 1
            if error:
                proxy.last_error = error
            db.commit()

    def get_all_proxies(
        self,
        db: Session,
        assigned: bool = None,
        status: str = None,
    ) -> list[Proxy]:
        query = db.query(Proxy)

        if assigned is True:
            query = query.filter(Proxy.assigned_account_id != None)
        elif assigned is False:
            query = query.filter(Proxy.assigned_account_id == None)

        if status:
            query = query.filter(Proxy.status == status)

        return query.all()

    def push_proxy_to_camofox(self, db: Session, account_id: int) -> bool:
        proxy = self.get_proxy_for_account(db, account_id)
        if not proxy:
            return False

        user_id = f"s_{account_id}"
        client = StickyProxyClient()

        try:
            client.set_proxy(user_id, proxy.proxy_string)
            return True
        except Exception as e:
            print(f"Failed to push proxy to Camofox: {e}")
            return False


def get_proxy_service() -> ProxyService:
    return ProxyService()
