from pydantic import BaseModel
from typing import Any, Optional


class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None
    timestamp: str


class SuccessResponse(BaseModel):
    success: bool = True
    data: Any


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str
    version: str = "0.9.0"


class StatsAccounts(BaseModel):
    total: int
    alive: int
    dead: int
    by_type: dict
    by_status: dict


class StatsActions(BaseModel):
    today: int
    this_week: int
    this_month: int
    by_type: dict


class StatsSessions(BaseModel):
    avg_age_hours: float
    expiring_soon: int


class StatsResponse(BaseModel):
    accounts: StatsAccounts
    actions: StatsActions
    sessions: StatsSessions
