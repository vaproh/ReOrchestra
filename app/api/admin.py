from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, UTC
import httpx
import logging

from app.database import get_db, Account, Proxy
from app.models import TaskExecutionLog, CamofoxSlot
from app.models import AccountStatus, AccountType
from app.schemas.common import SuccessResponse
from app.config import get_settings

logger = logging.getLogger("admin")
router = APIRouter()


@router.get("/health", response_model=SuccessResponse)
async def health_check():
    settings = get_settings()
    camofox_status = {"connected": False, "port": settings.camofox_port}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"http://localhost:{settings.camofox_port}/",
                timeout=settings.timeout_admin_health,
            )
            if r.is_success:
                camofox_status["connected"] = True
                try:
                    camofox_status.update(r.json())
                except (ValueError, KeyError) as e:
                    logger.warning(f"health | bad_json_response | error={e}")
    except httpx.ConnectError:
        logger.warning("health | camofox_unreachable | port=%s", settings.camofox_port)
    except httpx.TimeoutException:
        logger.warning("health | camofox_timeout | port=%s", settings.camofox_port)
    except Exception as e:
        logger.error("health | camofox_check_failed | error=%s", e)

    return SuccessResponse(
        data={
            "status": "ok",
            "version": "0.9.0",
            "timestamp": datetime.now(UTC).isoformat() + "Z",
            "camofox": camofox_status,
            "vnc": {
                "enabled": settings.vnc_enabled,
                "port": settings.vnc_port,
                "url": f"http://localhost:{settings.vnc_port + 1}/vnc.html"
                if settings.vnc_enabled
                else None,
            },
        }
    )


@router.get("/stats", response_model=SuccessResponse)
async def get_stats(db: Session = Depends(get_db)):
    total_accounts = db.query(func.count(Account.id)).scalar() or 0
    alive_accounts = (
        db.query(func.count(Account.id))
        .filter(Account.status.in_([AccountStatus.fresh, AccountStatus.logged_in]))
        .scalar()
        or 0
    )
    dead_accounts = total_accounts - alive_accounts

    accounts_by_type = {
        "upvoter": db.query(func.count(Account.id))
        .filter(Account.account_type == AccountType.upvoter)
        .scalar()
        or 0,
        "main": db.query(func.count(Account.id))
        .filter(Account.account_type == AccountType.main)
        .scalar()
        or 0,
        "both": db.query(func.count(Account.id))
        .filter(Account.account_type == AccountType.both)
        .scalar()
        or 0,
    }

    accounts_by_status = {
        "fresh": db.query(func.count(Account.id))
        .filter(Account.status == AccountStatus.fresh)
        .scalar()
        or 0,
        "logged_in": db.query(func.count(Account.id))
        .filter(Account.status == AccountStatus.logged_in)
        .scalar()
        or 0,
        "session_expired": db.query(func.count(Account.id))
        .filter(Account.status == AccountStatus.session_expired)
        .scalar()
        or 0,
        "rate_limited": db.query(func.count(Account.id))
        .filter(Account.status == AccountStatus.rate_limited)
        .scalar()
        or 0,
        "banned": db.query(func.count(Account.id))
        .filter(Account.status == AccountStatus.banned)
        .scalar()
        or 0,
        "dead": db.query(func.count(Account.id))
        .filter(Account.status == AccountStatus.dead)
        .scalar()
        or 0,
    }

    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    actions_today = (
        db.query(func.count(TaskExecutionLog.id))
        .filter(TaskExecutionLog.created_at >= today)
        .scalar()
        or 0
    )
    actions_week = (
        db.query(func.count(TaskExecutionLog.id))
        .filter(TaskExecutionLog.created_at >= week_ago)
        .scalar()
        or 0
    )
    actions_month = (
        db.query(func.count(TaskExecutionLog.id))
        .filter(TaskExecutionLog.created_at >= month_ago)
        .scalar()
        or 0
    )

    actions_by_type = {
        "upvote": db.query(func.count(TaskExecutionLog.id))
        .filter(
            TaskExecutionLog.action_type.in_(["upvote_post", "upvote_comment"]),
            TaskExecutionLog.created_at >= month_ago,
        )
        .scalar()
        or 0,
        "downvote": db.query(func.count(TaskExecutionLog.id))
        .filter(
            TaskExecutionLog.action_type.in_(["downvote_post", "downvote_comment"]),
            TaskExecutionLog.created_at >= month_ago,
        )
        .scalar()
        or 0,
        "login": db.query(func.count(TaskExecutionLog.id))
        .filter(
            TaskExecutionLog.action_type == "login",
            TaskExecutionLog.created_at >= month_ago,
        )
        .scalar()
        or 0,
    }

    total_proxies = db.query(func.count(Proxy.id)).scalar() or 0

    votes_today = db.query(func.sum(Account.votes_today)).scalar() or 0

    slots = db.query(CamofoxSlot).all()
    slot_stats = {
        "total": len(slots),
        "running": sum(1 for s in slots if s.status == "running"),
        "crashed": sum(1 for s in slots if s.status == "crashed"),
        "total_capacity": sum(s.max_concurrent for s in slots),
    }

    return SuccessResponse(
        data={
            "accounts": {
                "total": total_accounts,
                "alive": alive_accounts,
                "dead": dead_accounts,
                "proxies": total_proxies,
                "votes_today": votes_today,
                "by_type": accounts_by_type,
                "by_status": accounts_by_status,
            },
            "actions": {
                "today": actions_today,
                "this_week": actions_week,
                "this_month": actions_month,
                "by_type": actions_by_type,
            },
            "sessions": {
                "avg_age_hours": 0.0,
                "expiring_soon": 0,
            },
            "slots": slot_stats,
        }
    )
