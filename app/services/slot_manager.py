import asyncio
import time
import logging
from typing import Optional, AsyncIterator

import requests
from sqlalchemy.orm import Session

from app.models import CamofoxSlot
from app.services.config_service import get_config

logger = logging.getLogger("slot_manager")


class SlotManager:
    _instance: Optional["SlotManager"] = None

    def __new__(cls) -> "SlotManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        self.config = get_config()
        self._semaphores: dict[int, asyncio.Semaphore] = {}
        self._slots: dict[int, CamofoxSlot] = {}
        self._lock = asyncio.Lock()
        self._starting_ports: set[int] = set()

    def get_slot_for_account(self, account_id: int, num_slots: int) -> int:
        return account_id % num_slots

    def get_semaphore(self, slot_id: int) -> asyncio.Semaphore:
        if slot_id not in self._semaphores:
            max_concurrent = self.config.get("concurrency", "max_concurrent_per_slot", default=10)
            self._semaphores[slot_id] = asyncio.Semaphore(max_concurrent)
        return self._semaphores[slot_id]

    async def slot_context(self, slot_id: int) -> AsyncIterator[None]:
        semaphore = self.get_semaphore(slot_id)
        await semaphore.acquire()
        try:
            yield
        finally:
            semaphore.release()

    async def health_check(self, port: int) -> dict:
        url = f"http://localhost:{port}/"
        try:
            resp = requests.get(url, timeout=5)
            data = resp.json()
            return {
                "connected": True,
                "data": data,
                "url": url,
            }
        except requests.exceptions.ConnectionError:
            return {"connected": False, "url": url, "error": "Connection refused"}
        except Exception as e:
            return {"connected": False, "url": url, "error": str(e)}

    async def update_slot_health(
        self,
        db: Session,
        slot_id: int,
        health_data: dict,
    ) -> None:
        slot = db.query(CamofoxSlot).filter(CamofoxSlot.id == slot_id).first()
        if not slot:
            return

        slot.last_health_check = time.time()

        if health_data.get("connected"):
            slot.status = "running"
            if "data" in health_data:
                slot.memory_mb = health_data["data"].get("memory", {}).get("rssMb")
                slot.cpu_percent = health_data["data"].get("cpu", {}).get("percent")
        else:
            slot.status = "crashed"

        db.commit()

    def calculate_num_slots(self, num_accounts: int) -> int:
        accounts_per_slot = self.config.get("concurrency", "accounts_per_slot", default=50)
        return max(1, (num_accounts + accounts_per_slot - 1) // accounts_per_slot)

    async def ensure_slots(
        self,
        db: Session,
        num_accounts: int,
        base_port: int = 9377,
    ) -> list[CamofoxSlot]:
        target_slots = self.calculate_num_slots(num_accounts)

        existing = db.query(CamofoxSlot).order_by(CamofoxSlot.port).all()

        if len(existing) >= target_slots:
            return existing[:target_slots]

        async with self._lock:
            for i in range(len(existing), target_slots):
                port = base_port + i

                existing_slot = db.query(CamofoxSlot).filter(
                    CamofoxSlot.port == port
                ).first()
                if existing_slot:
                    continue

                if port in self._starting_ports:
                    continue

                self._starting_ports.add(port)

                max_concurrent = self.config.get("concurrency", "max_concurrent_per_slot", default=10)

                slot = CamofoxSlot(
                    port=port,
                    status="stopped",
                    max_concurrent=max_concurrent,
                    current_load=0,
                )
                db.add(slot)

        db.commit()
        return db.query(CamofoxSlot).order_by(CamofoxSlot.port).all()

    def get_slot_stats(self, db: Session) -> dict:
        slots = db.query(CamofoxSlot).all()
        return {
            "total": len(slots),
            "running": sum(1 for s in slots if s.status == "running"),
            "stopped": sum(1 for s in slots if s.status == "stopped"),
            "crashed": sum(1 for s in slots if s.status == "crashed"),
            "max_concurrent_per_slot": self.config.get("concurrency", "max_concurrent_per_slot", default=10),
            "total_capacity": sum(s.max_concurrent for s in slots),
            "slots": [
                {
                    "id": s.id,
                    "port": s.port,
                    "status": s.status,
                    "max_concurrent": s.max_concurrent,
                    "current_load": s.current_load,
                    "memory_mb": s.memory_mb,
                    "cpu_percent": s.cpu_percent,
                }
                for s in slots
            ],
        }


def get_slot_manager() -> SlotManager:
    return SlotManager()
