from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import requests as http_requests

from app.database import get_db, Account, Post, ActionLog, Proxy
from app.models import AccountStatus, AccountType, PostStatus
from app.schemas.common import SuccessResponse, StatsResponse
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health", response_model=SuccessResponse)
async def health_check():
    camofox_status = {"connected": False, "port": settings.camofox_port}
    try:
        r = http_requests.get(f"http://localhost:{settings.camofox_port}/", timeout=3)
        if r.ok:
            camofox_status["connected"] = True
            try:
                camofox_status.update(r.json())
            except Exception:
                pass
    except Exception:
        pass

    return SuccessResponse(data={
        "status": "ok",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "camofox": camofox_status,
        "vnc": {
            "enabled": settings.vnc_enabled,
            "port": settings.vnc_port,
            "url": f"http://localhost:{settings.vnc_port + 1}/vnc.html" if settings.vnc_enabled else None,
        },
    })


@router.get("/stats", response_model=SuccessResponse)
async def get_stats(db: Session = Depends(get_db)):
    total_accounts = db.query(func.count(Account.id)).scalar() or 0
    alive_accounts = db.query(func.count(Account.id)).filter(
        Account.status.in_([AccountStatus.fresh, AccountStatus.logged_in])
    ).scalar() or 0
    dead_accounts = total_accounts - alive_accounts

    accounts_by_type = {
        "upvoter": db.query(func.count(Account.id)).filter(Account.account_type == AccountType.upvoter).scalar() or 0,
        "main": db.query(func.count(Account.id)).filter(Account.account_type == AccountType.main).scalar() or 0,
        "both": db.query(func.count(Account.id)).filter(Account.account_type == AccountType.both).scalar() or 0,
    }

    accounts_by_status = {
        "fresh": db.query(func.count(Account.id)).filter(Account.status == AccountStatus.fresh).scalar() or 0,
        "logged_in": db.query(func.count(Account.id)).filter(Account.status == AccountStatus.logged_in).scalar() or 0,
        "session_expired": db.query(func.count(Account.id)).filter(Account.status == AccountStatus.session_expired).scalar() or 0,
        "banned": db.query(func.count(Account.id)).filter(Account.status == AccountStatus.banned).scalar() or 0,
        "dead": db.query(func.count(Account.id)).filter(Account.status == AccountStatus.dead).scalar() or 0,
    }

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    actions_today = db.query(func.count(ActionLog.id)).filter(ActionLog.created_at >= today).scalar() or 0
    actions_week = db.query(func.count(ActionLog.id)).filter(ActionLog.created_at >= week_ago).scalar() or 0
    actions_month = db.query(func.count(ActionLog.id)).filter(ActionLog.created_at >= month_ago).scalar() or 0

    actions_by_type = {
        "upvote": db.query(func.count(ActionLog.id)).filter(ActionLog.action_type == "upvote", ActionLog.created_at >= month_ago).scalar() or 0,
        "downvote": db.query(func.count(ActionLog.id)).filter(ActionLog.action_type == "downvote", ActionLog.created_at >= month_ago).scalar() or 0,
        "login": db.query(func.count(ActionLog.id)).filter(ActionLog.action_type == "login", ActionLog.created_at >= month_ago).scalar() or 0,
    }

    total_posts = db.query(func.count(Post.id)).scalar() or 0
    posted_posts = db.query(func.count(Post.id)).filter(Post.status == PostStatus.posted).scalar() or 0
    total_karma = db.query(func.sum(Post.karma_gained)).scalar() or 0

    total_proxies = db.query(func.count(Proxy.id)).scalar() or 0

    votes_today = db.query(func.sum(Account.votes_today)).scalar() or 0

    return SuccessResponse(data={
        "accounts": {
            "total": total_accounts,
            "active": alive_accounts,
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
        "posts": {
            "total": total_posts,
            "posted": posted_posts,
            "total_karma_gained": total_karma,
        },
        "slots": {
            "total": 0,
            "running": 0,
            "crashed": 0,
            "total_capacity": 0,
        },
    })
