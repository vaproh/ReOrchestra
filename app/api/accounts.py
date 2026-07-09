from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, UTC
import logging

from app.database import get_db, Account, AccountStatus, AccountType

ACCOUNT_SORT_COLUMNS = {
    "id",
    "username",
    "status",
    "account_type",
    "karma_total",
    "karma_post",
    "karma_comment",
    "fail_count",
    "last_used",
    "last_login",
    "created_at",
}

logger = logging.getLogger("accounts")
from app.models import TaskExecutionLog
from app.schemas.account import (
    AccountResponse,
    AccountDetailResponse,
    BatchImportRequest,
    BatchDeleteRequest,
    LoginRequest,
)
from app.schemas.common import SuccessResponse

router = APIRouter()


@router.post("/import", response_model=SuccessResponse, status_code=201)
async def import_accounts(
    request: BatchImportRequest,
    db: Session = Depends(get_db),
):
    logger.info(f"Importing {len(request.accounts)} accounts")
    imported = []
    errors = []

    for acc_data in request.accounts:
        existing = (
            db.query(Account).filter(Account.username == acc_data.username).first()
        )
        if existing:
            logger.debug(f"Import skip: {acc_data.username} exists")
            errors.append(
                {"username": acc_data.username, "error": "Username already exists"}
            )
            continue

        account = Account(
            username=acc_data.username,
            password=acc_data.password,
            email=acc_data.email,
            proxy=acc_data.proxy,
            account_type=AccountType[request.account_type],
            status=AccountStatus.fresh,
        )
        db.add(account)
        imported.append(account)

    db.commit()
    db.flush()
    logger.info("Imported %s accounts, %s skipped", len(imported), len(errors))

    return SuccessResponse(
        data={
            "imported": len(imported),
            "skipped": len(errors),
            "accounts": [
                {"id": a.id, "username": a.username, "status": a.status.value}
                for a in imported
            ],
            "errors": errors,
        }
    )


@router.get("", response_model=SuccessResponse)
async def list_accounts(
    status: str | None = Query(None),
    account_type: str | None = Query(None),
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
            query = query.filter(
                Account.status.in_([AccountStatus.fresh, AccountStatus.logged_in])
            )
        else:
            try:
                query = query.filter(Account.status == AccountStatus[status])
            except KeyError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    if account_type:
        try:
            query = query.filter(Account.account_type == AccountType[account_type])
        except KeyError:
            raise HTTPException(
                status_code=400, detail=f"Invalid account type: {account_type}"
            )
    if search:
        query = query.filter(Account.username.contains(search))

    total = query.count()
    if sort not in ACCOUNT_SORT_COLUMNS:
        raise HTTPException(status_code=400, detail=f"Invalid sort column: {sort}")
    query = query.order_by(
        getattr(Account, sort).asc()
        if order == "asc"
        else getattr(Account, sort).desc()
    )
    accounts = query.offset((page - 1) * per_page).limit(per_page).all()

    return SuccessResponse(
        data={
            "total": total,
            "page": page,
            "per_page": per_page,
            "accounts": [
                AccountResponse.model_validate(a).model_dump()
                for a in accounts
            ],
        }
    )


@router.get("/{account_id}", response_model=SuccessResponse)
async def get_account(
    account_id: int,
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    recent = (
        db.query(TaskExecutionLog)
        .filter(TaskExecutionLog.account_id == account_id)
        .order_by(TaskExecutionLog.created_at.desc())
        .limit(10)
        .all()
    )

    return SuccessResponse(
        data={
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
                proxy=account.proxy,
                last_used=account.last_used,
                last_login=account.last_login,
                fail_count=account.fail_count,
                created_at=account.created_at,
                recent_actions=[
                    {
                        "action": a.action_type,
                        "target_url": a.target_url,
                        "success": a.success,
                        "created_at": a.created_at.isoformat(),
                    }
                    for a in recent
                ],
            ).model_dump(),
        }
    )


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
                try:
                    setattr(account, key, AccountStatus[value])
                except KeyError:
                    raise HTTPException(
                        status_code=400, detail=f"Invalid status: {value}"
                    )
            elif key == "account_type" and value:
                try:
                    setattr(account, key, AccountType[value])
                except KeyError:
                    raise HTTPException(
                        status_code=400, detail=f"Invalid account type: {value}"
                    )
            else:
                setattr(account, key, value)

    account.updated_at = datetime.now(UTC)
    db.commit()

    logger.info(f"Update account {account_id}: {list(updates.keys())}")

    return SuccessResponse(data=AccountResponse.model_validate(account).model_dump())


@router.delete("/{account_id}", response_model=SuccessResponse)
async def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    db.delete(account)
    db.commit()

    logger.info(f"Delete account {account_id}")

    return SuccessResponse(data={"deleted": 1})


@router.post("/batch-delete", response_model=SuccessResponse)
async def batch_delete_accounts(
    request: BatchDeleteRequest,
    db: Session = Depends(get_db),
):
    query = db.query(Account)

    if not request.ids and not request.filters:
        raise HTTPException(
            status_code=400, detail="Either 'ids' or 'filters' must be provided"
        )

    if request.ids:
        query = query.filter(Account.id.in_(request.ids))
    elif request.filters:
        if "status" in request.filters:
            try:
                query = query.filter(
                    Account.status == AccountStatus[request.filters["status"]]
                )
            except KeyError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {request.filters['status']}",
                )
        if "type" in request.filters:
            try:
                query = query.filter(
                    Account.account_type == AccountType[request.filters["type"]]
                )
            except KeyError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid account type: {request.filters['type']}",
                )

    accounts = query.all()
    for account in accounts:
        db.delete(account)

    db.commit()

    logger.info(f"Batch delete {len(accounts)}")

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

    logger.info(f"Login {len(accounts)} accounts")
    service = LoginService()
    results = []

    for account in accounts:
        try:
            success, time_ms = await service.login(
                username=account.username,
                password=account.password,
                proxy=account.proxy,
                force=request.force,
                headless=request.options.get("headless", False)
                if request.options
                else False,
            )
            if success:
                account.status = AccountStatus.logged_in
                account.last_login = datetime.now(UTC)
                db.commit()
                logger.info(f"Login success: {account.username}")
            results.append(
                {
                    "account_id": account.id,
                    "username": account.username,
                    "success": success,
                    "time_ms": time_ms,
                }
            )
        except Exception as e:
            logger.error(f"Login failed: {account.username} - {e}")
            results.append(
                {
                    "account_id": account.id,
                    "username": account.username,
                    "success": False,
                    "error": str(e),
                }
            )

    succeeded = len([r for r in results if r.get("success")])
    logger.info(f"Login complete: {succeeded}/{len(accounts)} succeeded")
    return SuccessResponse(
        data={
            "total": len(accounts),
            "logged_in": succeeded,
            "failed": len(results) - succeeded,
            "results": results,
        }
    )
