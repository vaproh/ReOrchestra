from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
import os

from app.database import get_db, Account, AccountStatus, AccountType
from app.models import TaskExecutionLog
from app.schemas.account import (
    AccountResponse,
    AccountDetailResponse,
    AccountSessionResponse,
    BatchImportRequest,
    BatchDeleteRequest,
    LoginRequest,
    BatchLoginRequest,
)
from app.schemas.common import SuccessResponse
from app.config import get_settings

router = APIRouter()


def session_valid(username: str) -> tuple[bool, float | None]:
    settings = get_settings()
    session_path = os.path.join(settings.session_dir, f"{username}.cookies")
    if not os.path.exists(session_path):
        return False, None
    age_hours = (datetime.utcnow() - datetime.fromtimestamp(os.path.getmtime(session_path))).total_seconds() / 3600
    return age_hours < settings.max_session_age_hours, age_hours


@router.post("/import", response_model=SuccessResponse, status_code=201)
async def import_accounts(
    request: BatchImportRequest,
    db: Session = Depends(get_db),
):
    imported = []
    errors = []

    for acc_data in request.accounts:
        existing = db.query(Account).filter(Account.username == acc_data.username).first()
        if existing:
            errors.append({"username": acc_data.username, "error": "Username already exists"})
            continue

        account = Account(
            username=acc_data.username,
            password=acc_data.password,
            email=acc_data.email,
            email_password=acc_data.email_password,
            proxy=acc_data.proxy,
            account_type=AccountType[request.account_type],
            status=AccountStatus.fresh,
        )
        db.add(account)
        imported.append(account)

    db.commit()

    return SuccessResponse(data={
        "imported": len(imported),
        "skipped": len(errors),
        "accounts": [{"id": a.id, "username": a.username, "status": a.status.value} for a in imported],
        "errors": errors,
    })


@router.get("", response_model=SuccessResponse)
async def list_accounts(
    status: str | None = Query(None),
    type: str | None = Query(None),
    search: str | None = Query(None),
    sort: str = Query("id"),
    order: str = Query("desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Account)

    if status:
        if status == "alive":
            query = query.filter(Account.status.in_([AccountStatus.fresh, AccountStatus.logged_in]))
        else:
            query = query.filter(Account.status == AccountStatus[status])
    if type:
        query = query.filter(Account.account_type == AccountType[type])
    if search:
        query = query.filter(Account.username.contains(search))

    total = query.count()
    query = query.order_by(getattr(Account, sort).asc() if order == "asc" else getattr(Account, sort).desc())
    accounts = query.offset((page - 1) * per_page).limit(per_page).all()

    return SuccessResponse(data={
        "total": total,
        "page": page,
        "per_page": per_page,
        "accounts": [
            {
                **AccountResponse.model_validate(a).model_dump(),
                "session_valid": session_valid(a.username)[0],
            }
            for a in accounts
        ],
    })


@router.get("/{account_id}", response_model=SuccessResponse)
async def get_account(
    account_id: int,
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    is_valid, age_hours = session_valid(account.username)
    recent = db.query(TaskExecutionLog).filter(
        TaskExecutionLog.account_id == account_id
    ).order_by(TaskExecutionLog.created_at.desc()).limit(10).all()

    return SuccessResponse(data={
        **AccountDetailResponse(
            id=account.id,
            username=account.username,
            password=account.password,
            status=account.status.value,
            account_type=account.account_type.value,
            karma_total=account.karma_total,
            karma_post=account.karma_post,
            karma_comment=account.karma_comment,
            email=account.email,
            email_verified=account.email_verified,
            proxy=account.proxy,
            profile_id=account.profile_id,
            cookies_present=os.path.exists(os.path.join(get_settings().session_dir, f"{account.username}.cookies")),
            session_valid=is_valid,
            session_age_hours=age_hours,
            last_used=account.last_used,
            last_login=account.last_login,
            fail_count=account.fail_count,
            created_at=account.created_at,
            recent_actions=[{"action": a.action_type, "target_url": a.target_url, "success": a.success, "created_at": a.created_at.isoformat()} for a in recent],
        ).model_dump(),
    })


@router.patch("/{account_id}", response_model=SuccessResponse)
async def update_account(
    account_id: int,
    updates: dict,
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    for key, value in updates.items():
        if hasattr(account, key):
            if key == "status" and value:
                setattr(account, key, AccountStatus[value])
            elif key == "account_type" and value:
                setattr(account, key, AccountType[value])
            else:
                setattr(account, key, value)

    account.updated_at = datetime.utcnow()
    db.commit()

    return SuccessResponse(data=AccountResponse.model_validate(account).model_dump())


@router.delete("/{account_id}", response_model=SuccessResponse)
async def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    session_path = os.path.join(get_settings().session_dir, f"{account.username}.cookies")
    if os.path.exists(session_path):
        os.remove(session_path)

    db.delete(account)
    db.commit()

    return SuccessResponse(data={"deleted": 1})


@router.post("/batch-delete", response_model=SuccessResponse)
async def batch_delete_accounts(
    request: BatchDeleteRequest,
    db: Session = Depends(get_db),
):
    query = db.query(Account)

    if request.ids:
        query = query.filter(Account.id.in_(request.ids))
    elif request.filters:
        if "status" in request.filters:
            query = query.filter(Account.status == AccountStatus[request.filters["status"]])
        if "type" in request.filters:
            query = query.filter(Account.account_type == AccountType[request.filters["type"]])

    accounts = query.all()
    for account in accounts:
        session_path = os.path.join(get_settings().session_dir, f"{account.username}.cookies")
        if os.path.exists(session_path):
            os.remove(session_path)
        db.delete(account)

    db.commit()

    return SuccessResponse(data={"deleted": len(accounts)})


@router.post("/login", response_model=SuccessResponse)
async def login_accounts(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    from app.modules.accounts.login import LoginService

    accounts = db.query(Account).filter(Account.id.in_(request.account_ids)).all()
    if not accounts:
        raise HTTPException(status_code=404, detail="No accounts found")

    service = LoginService()
    results = []

    for account in accounts:
        try:
            success, time_ms = await service.login(
                username=account.username,
                password=account.password,
                proxy=account.proxy,
                profile_id=account.profile_id,
                force=request.force,
                headless=request.options.get("headless", False) if request.options else False,
            )
            if success:
                account.status = AccountStatus.logged_in
                account.last_login = datetime.utcnow()
                db.commit()
            results.append({"account_id": account.id, "username": account.username, "success": success, "time_ms": time_ms})
        except Exception as e:
            results.append({"account_id": account.id, "username": account.username, "success": False, "error": str(e)})

    succeeded = len([r for r in results if r.get("success")])
    return SuccessResponse(data={
        "total": len(accounts),
        "logged_in": succeeded,
        "failed": len(results) - succeeded,
        "results": results,
    })


@router.post("/login/simple", response_model=SuccessResponse)
async def login_simple(
    request: dict,
    db: Session = Depends(get_db),
):
    """Login with username and password directly (no account ID needed)."""
    from app.modules.accounts.login import LoginService

    username = request.get("username")
    password = request.get("password")
    headless = request.get("headless", False)

    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")

    service = LoginService()
    success, time_ms = await service.login(
        username=username,
        password=password,
        force=True,
        headless=headless,
    )

    return SuccessResponse(data={
        "success": success,
        "username": username,
        "time_ms": time_ms,
    })


@router.post("/login/batch", response_model=SuccessResponse)
async def batch_login_accounts(
    request: BatchLoginRequest,
    db: Session = Depends(get_db),
):
    query = db.query(Account)

    if request.filters.get("status"):
        query = query.filter(Account.status == AccountStatus[request.filters["status"]])
    if request.filters.get("type"):
        query = query.filter(Account.account_type == AccountType[request.filters["type"]])

    accounts = query.all()
    if not accounts:
        raise HTTPException(status_code=404, detail="No accounts found")

    from app.modules.accounts.login import LoginService
    service = LoginService()
    results = []

    for account in accounts:
        try:
            success, time_ms = await service.login(
                username=account.username,
                password=account.password,
                proxy=account.proxy,
                profile_id=account.profile_id,
                force=request.force,
                headless=request.options.get("headless", False) if request.options else False,
            )
            if success:
                account.status = AccountStatus.logged_in
                account.last_login = datetime.utcnow()
                db.commit()
            results.append({"account_id": account.id, "username": account.username, "success": success, "time_ms": time_ms})
        except Exception as e:
            results.append({"account_id": account.id, "username": account.username, "success": False, "error": str(e)})

    succeeded = len([r for r in results if r.get("success")])
    return SuccessResponse(data={
        "total": len(accounts),
        "logged_in": succeeded,
        "failed": len(results) - succeeded,
        "results": results,
    })


@router.get("/{account_id}/session", response_model=SuccessResponse)
async def check_session(
    account_id: int,
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    is_valid, age_hours = session_valid(account.username)
    settings = get_settings()
    expires_in = max(0, settings.max_session_age_hours - age_hours) if age_hours else settings.max_session_age_hours

    return SuccessResponse(data={
        "account_id": account.id,
        "username": account.username,
        "session_valid": is_valid,
        "session_age_hours": round(age_hours, 2) if age_hours else None,
        "expires_in_hours": round(expires_in, 2),
        "cookies_exist": os.path.exists(os.path.join(settings.session_dir, f"{account.username}.cookies")),
        "last_login": account.last_login.isoformat() if account.last_login else None,
    })
