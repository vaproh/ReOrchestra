from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class AccountBase(BaseModel):
    username: str = Field(..., min_length=1, max_length=20)
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

    model_config = ConfigDict(from_attributes=True)


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
    last_used: Optional[datetime]
    last_login: Optional[datetime]
    fail_count: int
    created_at: datetime
    recent_actions: list = []

    model_config = ConfigDict(from_attributes=True)


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
