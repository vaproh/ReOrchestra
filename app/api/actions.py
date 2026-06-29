from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import hashlib
import time

from app.database import get_db, Account, ActionLog
from app.schemas.action import ActionRequest, BatchActionResponse, ActionResult
from app.schemas.common import SuccessResponse
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.post("/upvote", response_model=SuccessResponse)
async def upvote(
    request: ActionRequest,
    db: Session = Depends(get_db),
):
    from app.services.actions import ActionService

    account_ids = request.account_ids or []
    
    if request.username:
        acc = db.query(Account).filter(Account.username == request.username).first()
        if acc:
            account_ids = [acc.id]
        else:
            raise HTTPException(status_code=404, detail=f"Account not found: {request.username}")
    
    if request.filters:
        query = db.query(Account)
        if request.filters.get("status"):
            from app.models import AccountStatus
            query = query.filter(Account.status == AccountStatus[request.filters["status"]])
        if request.filters.get("type"):
            from app.models import AccountType
            query = query.filter(Account.account_type == AccountType[request.filters["type"]])
        account_ids = [a.id for a in query.all()]

    if not account_ids:
        raise HTTPException(status_code=400, detail="No accounts specified")

    accounts = db.query(Account).filter(Account.id.in_(account_ids)).all()
    if not accounts:
        raise HTTPException(status_code=404, detail="No accounts found")

    service = ActionService()
    results = []

    for account in accounts:
        dedup_hash = hashlib.sha256(f"{account.id}:{request.target_url}:upvote".encode()).hexdigest()
        existing = db.query(ActionLog).filter(ActionLog.dedup_hash == dedup_hash).first()
        if existing:
            results.append(ActionResult(account_id=account.id, username=account.username, success=False, error="Already voted"))
            continue

        try:
            start = time.time()
            res = await service.upvote_browser(
                account.username,
                account.password,
                request.target_url,
                proxy=account.proxy,
                profile_id=account.profile_id,
            )
            elapsed_ms = int((time.time() - start) * 1000)

            if res.success:
                log = ActionLog(
                    account_id=account.id,
                    target_id=request.target_url,
                    action_type="upvote",
                    action_value="1",
                    dedup_hash=dedup_hash,
                    success=True,
                )
                db.add(log)
                account.last_used = datetime.utcnow()
                db.commit()
            results.append(ActionResult(account_id=account.id, username=account.username, success=res.success, time_ms=elapsed_ms, error=res.message if not res.success else None))
        except Exception as e:
            results.append(ActionResult(account_id=account.id, username=account.username, success=False, error=str(e)))

    succeeded = len([r for r in results if r.success])
    return SuccessResponse(data={
        "total": len(results),
        "succeeded": succeeded,
        "failed": len(results) - succeeded,
        "results": [r.model_dump() for r in results],
    })


@router.post("/downvote", response_model=SuccessResponse)
async def downvote(
    request: ActionRequest,
    db: Session = Depends(get_db),
):
    from app.services.actions import ActionService

    account_ids = request.account_ids or []
    
    if request.username:
        acc = db.query(Account).filter(Account.username == request.username).first()
        if acc:
            account_ids = [acc.id]
        else:
            raise HTTPException(status_code=404, detail=f"Account not found: {request.username}")
    
    if request.filters:
        query = db.query(Account)
        if request.filters.get("status"):
            from app.models import AccountStatus
            query = query.filter(Account.status == AccountStatus[request.filters["status"]])
        if request.filters.get("type"):
            from app.models import AccountType
            query = query.filter(Account.account_type == AccountType[request.filters["type"]])
        account_ids = [a.id for a in query.all()]

    if not account_ids:
        raise HTTPException(status_code=400, detail="No accounts specified")

    accounts = db.query(Account).filter(Account.id.in_(account_ids)).all()
    if not accounts:
        raise HTTPException(status_code=404, detail="No accounts found")

    service = ActionService()
    results = []

    for account in accounts:
        dedup_hash = hashlib.sha256(f"{account.id}:{request.target_url}:downvote".encode()).hexdigest()
        existing = db.query(ActionLog).filter(ActionLog.dedup_hash == dedup_hash).first()
        if existing:
            results.append(ActionResult(account_id=account.id, username=account.username, success=False, error="Already voted"))
            continue

        try:
            start = time.time()
            res = await service.downvote_browser(
                account.username,
                account.password,
                request.target_url,
                proxy=account.proxy,
                profile_id=account.profile_id,
            )
            elapsed_ms = int((time.time() - start) * 1000)

            if res.success:
                log = ActionLog(
                    account_id=account.id,
                    target_id=request.target_url,
                    action_type="downvote",
                    action_value="-1",
                    dedup_hash=dedup_hash,
                    success=True,
                )
                db.add(log)
                account.last_used = datetime.utcnow()
                db.commit()
            results.append(ActionResult(account_id=account.id, username=account.username, success=res.success, time_ms=elapsed_ms, error=res.message if not res.success else None))
        except Exception as e:
            results.append(ActionResult(account_id=account.id, username=account.username, success=False, error=str(e)))

    succeeded = len([r for r in results if r.success])
    return SuccessResponse(data={
        "total": len(results),
        "succeeded": succeeded,
        "failed": len(results) - succeeded,
        "results": [r.model_dump() for r in results],
    })
