"""Frontend page routes — serves Jinja2 HTML templates for the dashboard."""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import logging
import os
import jinja2

from app.database import get_db, Task, TaskStatus, Account, TaskExecutionLog

logger = logging.getLogger("frontend")
router = APIRouter()

# Build Jinja2 environment with auto_reload=False to avoid Python 3.14
# lru_cache incompatibility (unhashable dict in cache key).
_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
_jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(_TEMPLATES_DIR),
    autoescape=True,  # simple bool avoids Python 3.14 select_autoescape recursion
    auto_reload=False,
)
templates = Jinja2Templates(env=_jinja_env)



# ---------------------------------------------------------------------------
# Helper: fetch data from DB directly (avoids HTTP round-trip to self)
# ---------------------------------------------------------------------------

def _get_admin_stats(db: Session) -> dict:
    from sqlalchemy import func
    from datetime import datetime, timedelta, UTC
    from app.database import Proxy
    from app.models import TaskExecutionLog as TLog, CamofoxSlot
    from app.models import AccountStatus, AccountType

    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)

    total_accounts = db.query(func.count(Account.id)).scalar() or 0
    alive_accounts = (
        db.query(func.count(Account.id))
        .filter(Account.status.in_([AccountStatus.fresh, AccountStatus.logged_in]))
        .scalar() or 0
    )
    dead_accounts = total_accounts - alive_accounts

    by_status = {}
    for st in AccountStatus:
        by_status[st.value] = (
            db.query(func.count(Account.id)).filter(Account.status == st).scalar() or 0
        )
    by_type = {}
    for at in AccountType:
        by_type[at.value] = (
            db.query(func.count(Account.id)).filter(Account.account_type == at).scalar() or 0
        )

    total_proxies = db.query(func.count(Proxy.id)).scalar() or 0
    votes_today = db.query(func.sum(Account.votes_today)).scalar() or 0

    actions_today = (
        db.query(func.count(TLog.id)).filter(TLog.created_at >= today).scalar() or 0
    )
    actions_week = (
        db.query(func.count(TLog.id)).filter(TLog.created_at >= week_ago).scalar() or 0
    )

    return {
        "success": True,
        "data": {
            "accounts": {
                "total": total_accounts,
                "alive": alive_accounts,
                "dead": dead_accounts,
                "proxies": total_proxies,
                "votes_today": votes_today,
                "by_type": by_type,
                "by_status": by_status,
            },
            "actions": {
                "today": actions_today,
                "this_week": actions_week,
            },
        },
    }


def _get_queue_status(db: Session) -> dict:
    from app.modules.queue import QueueManager
    from app.models import AccountStatus

    manager = QueueManager.get()
    logged_in = db.query(Account).filter(Account.status == AccountStatus.logged_in).count()
    rate_limited = db.query(Account).filter(Account.status == AccountStatus.rate_limited).count()
    dead = db.query(Account).filter(Account.status == AccountStatus.dead).count()
    queued_count = db.query(Task).filter(Task.status == TaskStatus.queued).count()
    running_count = db.query(Task).filter(Task.status == TaskStatus.running).count()

    return {
        "success": True,
        "data": {
            "processing": manager.is_running(),
            "queue": {"queued": queued_count, "running": running_count},
            "accounts": {
                "total": db.query(Account).count(),
                "available": logged_in,
                "rate_limited": rate_limited,
                "dead": dead,
            },
        },
    }


def _get_health() -> dict:
    """Return a minimal health dict without hitting the real HTTP endpoint."""
    from app.config import get_settings
    settings = get_settings()
    return {
        "success": True,
        "data": {
            "status": "ok",
            "camofox": {"connected": False, "port": settings.camofox_port},
            "vnc": {"enabled": settings.vnc_enabled},
        },
    }


def _task_dict(t: Task) -> dict:
    completed = t.workers_completed or 0
    failed = t.workers_failed or 0
    return {
        "id": t.id,
        "action_type": t.action_type,
        "target_url": t.target_url,
        "workers_needed": t.workers_needed,
        "workers_completed": completed,
        "workers_failed": failed,
        "status": t.status.value if t.status else None,
        "priority": t.priority,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "started_at": t.started_at.isoformat() if t.started_at else None,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
    }


# ---------------------------------------------------------------------------
# HTMX partial: queue status pill (used in base.html sidebar)
# ---------------------------------------------------------------------------

@router.get("/htmx/queue-status", response_class=HTMLResponse)
async def htmx_queue_status(request: Request, db: Session = Depends(get_db)):
    qs = _get_queue_status(db)
    processing = qs["data"]["processing"]
    if processing:
        html = '''<div id="queue-status-pill" hx-get="/htmx/queue-status" hx-trigger="every 15s" hx-swap="outerHTML"
                        class="flex items-center gap-2 px-3 py-2 rounded-lg bg-green-900/30 border border-green-800/30 transition-colors">
                    <div class="w-2 h-2 rounded-full bg-green-400 animate-pulse"></div>
                    <span class="text-green-400 text-xs font-medium">Queue Running</span>
                  </div>'''
    else:
        html = '''<div id="queue-status-pill" hx-get="/htmx/queue-status" hx-trigger="every 15s" hx-swap="outerHTML"
                        class="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-900/20 border border-red-800/20 transition-colors">
                    <div class="w-2 h-2 rounded-full bg-red-400"></div>
                    <span class="text-red-400 text-xs font-medium">Queue Stopped</span>
                  </div>'''
    return HTMLResponse(html)


# ---------------------------------------------------------------------------
# HTMX partial: stats section (auto-refreshed every 30s from dashboard)
# ---------------------------------------------------------------------------

@router.get("/htmx/stats", response_class=HTMLResponse)
async def htmx_stats(request: Request, db: Session = Depends(get_db)):
    stats = _get_admin_stats(db)
    qs = _get_queue_status(db)
    return templates.TemplateResponse(
        request,
        "partials/stats_cards.html",
        {"stats": stats, "queue_status": qs},
    )


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@router.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(url="/dashboard")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    stats = _get_admin_stats(db)
    queue_status = _get_queue_status(db)
    health_data = _get_health()

    tasks_q = (
        db.query(Task)
        .order_by(Task.created_at.desc())
        .limit(10)
        .all()
    )
    recent_tasks = {"success": True, "data": {"tasks": [_task_dict(t) for t in tasks_q]}}

    return templates.TemplateResponse(
        request,
        "pages/dashboard.html",
        {
            "active_page": "dashboard",
            "stats": stats,
            "queue_status": queue_status,
            "health_data": health_data,
            "recent_tasks": recent_tasks,
        },
    )


@router.get("/accounts", response_class=HTMLResponse)
async def accounts_page(
    request: Request,
    db: Session = Depends(get_db),
    status: str = Query(None),
    search: str = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    from app.models import AccountStatus

    q = db.query(Account)
    if status:
        try:
            q = q.filter(Account.status == AccountStatus(status))
        except ValueError:
            pass
    if search:
        q = q.filter(Account.username.ilike(f"%{search}%"))

    total = q.count()
    accs = q.order_by(Account.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    def acc_dict(a: Account) -> dict:
        return {
            "id": a.id,
            "username": a.username,
            "email": a.email,
            "status": a.status.value if a.status else "fresh",
            "account_type": a.account_type.value if a.account_type else None,
            "karma_total": a.karma_total,
            "votes_today": a.votes_today,
            "votes_week": a.votes_week,
            "last_used": a.last_used.isoformat() if a.last_used else None,
            "last_login": a.last_login.isoformat() if a.last_login else None,
        }

    accounts_data = {
        "success": True,
        "data": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "accounts": [acc_dict(a) for a in accs],
        },
    }

    return templates.TemplateResponse(
        request,
        "pages/accounts.html",
        {
            "active_page": "accounts",
            "accounts_data": accounts_data,
            "current_status": status or "",
            "search_query": search or "",
            "page": page,
        },
    )


@router.get("/tasks", response_class=HTMLResponse)
async def tasks_page(
    request: Request,
    db: Session = Depends(get_db),
    status: str = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    q = db.query(Task)
    if status:
        try:
            q = q.filter(Task.status == TaskStatus(status))
        except ValueError:
            pass

    total = q.count()
    tasks = q.order_by(Task.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    tasks_data = {
        "success": True,
        "data": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "tasks": [_task_dict(t) for t in tasks],
        },
    }

    return templates.TemplateResponse(
        request,
        "pages/tasks.html",
        {
            "active_page": "tasks",
            "tasks_data": tasks_data,
            "current_status": status or "",
            "page": page,
        },
    )


@router.get("/tasks/{task_id}", response_class=HTMLResponse)
async def task_detail_page(
    request: Request,
    task_id: int,
    db: Session = Depends(get_db),
):
    task_obj = db.query(Task).filter(Task.id == task_id).first()
    if not task_obj:
        return HTMLResponse("<h1>Task not found</h1>", status_code=404)

    task = _task_dict(task_obj)

    # Fetch logs with account username join
    logs_raw = (
        db.query(TaskExecutionLog, Account.username)
        .outerjoin(Account, TaskExecutionLog.account_id == Account.id)
        .filter(TaskExecutionLog.task_id == task_id)
        .order_by(TaskExecutionLog.created_at.desc())
        .limit(100)
        .all()
    )
    logs = [
        {
            "id": log.id,
            "account_id": log.account_id,
            "username": username,
            "success": log.success,
            "outcome": log.outcome,
            "error": log.error,
            "attempts": log.attempts,
            "duration_ms": log.duration_ms,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log, username in logs_raw
    ]

    return templates.TemplateResponse(
        request,
        "pages/task_detail.html",
        {
            "active_page": "tasks",
            "task": task,
            "logs": logs,
        },
    )


@router.get("/proxies", response_class=HTMLResponse)
async def proxies_page(
    request: Request,
    db: Session = Depends(get_db),
    status: str = Query(None),
    page: int = Query(1, ge=1),
):
    from app.database import Proxy

    q = db.query(Proxy)
    if status and status in ("active", "dead"):
        q = q.filter(Proxy.status == status)

    proxies = q.order_by(Proxy.id.asc()).all()

    def proxy_dict(p: Proxy) -> dict:
        return {
            "id": p.id,
            "proxy_string": p.proxy_string,
            "host": p.host,
            "port": p.port,
            "username": p.username,
            "proxy_type": p.proxy_type,
            "provider": p.provider,
            "status": p.status,
            "is_active": p.is_active,
            "fail_count": p.fail_count,
            "last_error": p.last_error,
            "last_used": p.last_used.isoformat() if p.last_used else None,
        }

    proxies_data = {
        "success": True,
        "data": {
            "total": len(proxies),
            "proxies": [proxy_dict(p) for p in proxies],
        },
    }

    return templates.TemplateResponse(
        request,
        "pages/proxies.html",
        {
            "active_page": "proxies",
            "proxies_data": proxies_data,
            "current_status": status or "",
            "page": page,
        },
    )


@router.get("/system", response_class=HTMLResponse)
async def system_page(request: Request, db: Session = Depends(get_db)):
    from app.api.admin import health_check
    import platform
    import os
    import psutil
    
    # Get camofox and general health status
    health_resp = await health_check()
    health_data = health_resp.data
    
    # Get db, proxy, and queue stats
    stats_data = _get_admin_stats(db)["data"]
    
    # Distro info
    try:
        os_info = platform.freedesktop_os_release()
        distro_name = os_info.get("NAME", platform.system())
        distro_version = os_info.get("VERSION", platform.release())
    except (AttributeError, FileNotFoundError, OSError):
        distro_name = platform.system()
        distro_version = platform.release()

    # Memory
    mem = psutil.virtual_memory()
    # Disk (check the partition where the app resides instead of root)
    disk = psutil.disk_usage(os.path.abspath('.'))
    
    # CPU Load
    cpu_cores = psutil.cpu_count(logical=True)
    try:
        load = os.getloadavg()
        load_str = f"{load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}"
        # Estimate CPU usage from 1-minute load average (clamped to 100%)
        cpu_percent = min(round((load[0] / cpu_cores) * 100, 1), 100.0)
    except AttributeError:
        load_str = "N/A"
        cpu_percent = psutil.cpu_percent(interval=None)
        
    host_info = {
        "os": distro_name,
        "release": distro_version,
        "cpu_cores": cpu_cores,
        "cpu_percent": cpu_percent,
        "load": load_str,
        "ram": {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "percent": disk.percent
        }
    }
    
    return templates.TemplateResponse(
        request,
        "pages/system.html",
        {
            "active_page": "system",
            "health": health_data,
            "stats": stats_data,
            "host": host_info,
        },
    )
