from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, UTC
import logging

from app.database import get_db, Proxy
from app.schemas.common import SuccessResponse
from app.schemas.proxy import (
    ProxyImportRequest,
    ProxyReplaceRequest,
    ProxyMarkDeadRequest,
)

logger = logging.getLogger("proxies")

router = APIRouter()


@router.get("", response_model=SuccessResponse)
async def list_proxies(
    status: str = Query(None, description="Filter by status: active, dead"),
    assigned: bool = Query(None, description="Filter by assigned status"),
    db: Session = Depends(get_db),
):
    query = db.query(Proxy)

    if status:
        if status not in ("active", "dead"):
            raise HTTPException(
                status_code=400, detail="Invalid status. Valid: active, dead"
            )
        query = query.filter(Proxy.status == status)
    if assigned is True:
        query = query.filter(Proxy.assigned_account_id != None)
    elif assigned is False:
        query = query.filter(Proxy.assigned_account_id == None)

    proxies = query.all()

    return SuccessResponse(
        data={
            "total": len(proxies),
            "proxies": [
                {
                    "id": p.id,
                    "proxy_string": p.proxy_string,
                    "host": p.host,
                    "port": p.port,
                    "username": p.username,
                    "proxy_type": p.proxy_type,
                    "provider": p.provider,
                    "assigned_account_id": p.assigned_account_id,
                    "status": p.status,
                    "is_active": p.is_active,
                    "fail_count": p.fail_count,
                    "last_error": p.last_error,
                    "last_used": p.last_used.isoformat() if p.last_used else None,
                    "added_at": p.added_at.isoformat() if p.added_at else None,
                }
                for p in proxies
            ],
        }
    )


@router.post("/import", response_model=SuccessResponse)
async def import_proxies(
    request: ProxyImportRequest,
    db: Session = Depends(get_db),
):
    proxy_strings = request.proxies
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

        parts = proxy_str.replace("http://", "").split(":")
        host = parts[0] if len(parts) > 0 else None
        port_str = parts[1] if len(parts) > 1 else None
        if port_str is None or not port_str.isdigit():
            logger.warning(f"Invalid port in proxy string, skipping: {proxy_str}")
            skipped += 1
            continue
        port = int(port_str)
        username = parts[2] if len(parts) > 2 else None
        password = ":".join(parts[3:]) if len(parts) > 3 and parts[3] else None

        proxy = Proxy(
            proxy_string=proxy_str,
            host=host,
            port=port,
            username=username,
            password=password,
            status="active",
            is_active=True,
        )
        db.add(proxy)
        imported += 1

    db.commit()

    logger.info("Importing %s proxies", imported)

    return SuccessResponse(
        data={
            "imported": imported,
            "skipped": skipped,
        }
    )


@router.post("/replace", response_model=SuccessResponse)
async def replace_dead_proxies(
    request: ProxyReplaceRequest,
    db: Session = Depends(get_db),
):
    new_proxy_strings = request.proxies

    dead_proxies = (
        db.query(Proxy).filter(Proxy.status == "dead").order_by(Proxy.id).all()
    )

    if not dead_proxies:
        return SuccessResponse(
            data={
                "replaced": 0,
                "skipped": 0,
                "remaining_dead": 0,
            }
        )

    replaced = 0
    skipped = 0

    for i, proxy_str in enumerate(new_proxy_strings):
        proxy_str = proxy_str.strip()
        if not proxy_str:
            skipped += 1
            continue

        if i >= len(dead_proxies):
            skipped += 1
            continue

        dead_proxy = dead_proxies[i]

        existing = db.query(Proxy).filter(Proxy.proxy_string == proxy_str).first()
        if existing:
            skipped += 1
            continue

        parts = proxy_str.replace("http://", "").split(":")
        host = parts[0] if len(parts) > 0 else None
        port_str = parts[1] if len(parts) > 1 else None
        if port_str is None or not port_str.isdigit():
            logger.warning(f"Invalid port in proxy string, skipping: {proxy_str}")
            skipped += 1
            continue
        port = int(port_str)
        username = parts[2] if len(parts) > 2 else None
        password = ":".join(parts[3:]) if len(parts) > 3 and parts[3] else None

        dead_proxy.proxy_string = proxy_str
        dead_proxy.host = host
        dead_proxy.port = port
        dead_proxy.username = username
        dead_proxy.password = password
        dead_proxy.status = "active"
        dead_proxy.is_active = True
        dead_proxy.fail_count = 0
        dead_proxy.last_error = None
        dead_proxy.last_used = datetime.now(UTC)

        replaced += 1

    db.commit()

    remaining_dead = db.query(Proxy).filter(Proxy.status == "dead").count()

    logger.info("Replace dead proxies")

    return SuccessResponse(
        data={
            "replaced": replaced,
            "skipped": skipped,
            "remaining_dead": remaining_dead,
        }
    )


@router.delete("/{proxy_id}", response_model=SuccessResponse)
async def delete_proxy(
    proxy_id: int,
    db: Session = Depends(get_db),
):
    proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")

    proxy.assigned_account_id = None
    db.delete(proxy)
    db.commit()

    logger.info("Delete proxy %s", proxy_id)

    return SuccessResponse(data={"deleted": 1})


@router.post("/mark-dead", response_model=SuccessResponse)
async def mark_proxy_dead(
    request: ProxyMarkDeadRequest,
    db: Session = Depends(get_db),
):
    proxy_id = request.proxy_id
    error_msg = request.error

    proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")

    proxy.status = "dead"
    proxy.is_active = False
    proxy.fail_count += 1
    proxy.last_error = error_msg
    proxy.assigned_account_id = None

    db.commit()

    logger.warning("Mark proxy dead: %s", proxy_id)

    return SuccessResponse(data={"success": True})
