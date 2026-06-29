from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ActionRequest(BaseModel):
    account_ids: Optional[list[int]] = None
    filters: Optional[dict] = None
    username: Optional[str] = None
    target_url: str
    delay_range_ms: tuple[int, int] = (1000, 3000)
    random_order: bool = True


class DownvoteRequest(ActionRequest):
    pass


class CommentRequest(ActionRequest):
    text: str


class FollowRequest(BaseModel):
    account_ids: list[int]
    target_username: str


class JoinSubredditRequest(BaseModel):
    account_ids: list[int]
    subreddit: str


class ActionResult(BaseModel):
    account_id: int
    username: str
    success: bool
    time_ms: Optional[int] = None
    error: Optional[str] = None


class BatchActionResponse(BaseModel):
    success: bool
    total: int
    succeeded: int
    failed: int
    results: list[ActionResult]
    task_id: Optional[str] = None
