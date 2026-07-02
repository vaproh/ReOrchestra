from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class AccountBase(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    email_password: Optional[str] = None
    proxy: Optional[str] = None
    account_type: str = "upvoter"


class AccountCreate(AccountBase):
    pass


class AccountImport(AccountBase):
    pass


class AccountResponse(BaseModel):
    id: int
    username: str
    status: str
    account_type: str
    karma_total: int
    email_verified: bool
    proxy: Optional[str]
    last_used: Optional[datetime]
    fail_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class AccountDetailResponse(BaseModel):
    id: int
    username: str
    password: str
    status: str
    account_type: str
    karma_total: int
    karma_post: int
    karma_comment: int
    email: Optional[str]
    email_verified: bool
    proxy: Optional[str]
    cookies_present: bool = False
    session_valid: bool = False
    session_age_hours: Optional[float] = None
    last_used: Optional[datetime]
    last_login: Optional[datetime]
    fail_count: int
    created_at: datetime
    recent_actions: list = []

    class Config:
        from_attributes = True


class AccountSessionResponse(BaseModel):
    account_id: int
    username: str
    session_valid: bool
    session_age_hours: Optional[float]
    expires_in_hours: Optional[float]
    cookies_exist: bool
    last_login: Optional[datetime]


class BatchImportRequest(BaseModel):
    accounts: list[AccountImport]
    account_type: str = "upvoter"


class BatchDeleteRequest(BaseModel):
    ids: Optional[list[int]] = None
    filters: Optional[dict] = None


class LoginRequest(BaseModel):
    account_ids: list[int]
    force: bool = False
    options: Optional[dict] = None


class BatchLoginRequest(BaseModel):
    filters: dict
    force: bool = False
    options: Optional[dict] = None
