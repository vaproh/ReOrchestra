import time
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models import Account, TaskExecutionLog
from app.modules.shared.config import get_config


class RateLimiter:
    def __init__(self):
        self.config = get_config()

    def check(self, account: Account, db: Session) -> Tuple[bool, str]:
        if account.status.value in ("dead", "banned"):
            return False, f"account_{account.status.value}"

        max_votes_per_day = self.config.get("rate_limits", "max_votes_per_day", default=15)
        max_votes_per_week = self.config.get("rate_limits", "max_votes_per_week", default=100)
        min_seconds_between = self.config.get("rate_limits", "min_seconds_between_votes", default=120)

        if account.votes_today >= max_votes_per_day:
            return False, "daily_limit_reached"

        if account.votes_this_week >= max_votes_per_week:
            return False, "weekly_limit_reached"

        if account.last_vote_at:
            seconds_since = (datetime.utcnow() - account.last_vote_at).total_seconds()
            if seconds_since < min_seconds_between:
                return False, "cooldown_active"

        if not self._is_within_active_hours(account):
            return False, "outside_active_hours"

        if self._vote_ratio_too_high(account, db):
            return False, "vote_only_ratio_exceeded"

        return True, ""

    def _is_within_active_hours(self, account: Account) -> bool:
        now = datetime.utcnow()
        current_hour = now.hour
        return account.active_hours_start <= current_hour <= account.active_hours_end

    def _vote_ratio_too_high(self, account: Account, db: Session) -> bool:
        max_vote_ratio = self.config.get("rate_limits", "max_vote_only_ratio", default=0.3)

        week_ago = datetime.utcnow() - timedelta(days=7)
        total_actions = db.query(TaskExecutionLog).filter(
            TaskExecutionLog.account_id == account.id,
            TaskExecutionLog.created_at >= week_ago,
        ).count()

        if total_actions == 0:
            return False

        vote_actions = db.query(TaskExecutionLog).filter(
            TaskExecutionLog.account_id == account.id,
            TaskExecutionLog.action_type.in_([
                "upvote_post", "downvote_post",
                "upvote_comment", "downvote_comment",
            ]),
            TaskExecutionLog.created_at >= week_ago,
        ).count()

        vote_ratio = vote_actions / total_actions if total_actions > 0 else 0
        return vote_ratio > max_vote_ratio

    def record_vote(self, account: Account, db: Session) -> None:
        now = datetime.utcnow()

        if self._should_reset_daily(account, now):
            account.votes_today = 0

        if self._should_reset_weekly(account, now):
            account.votes_this_week = 0

        account.votes_today += 1
        account.votes_this_week += 1
        account.last_vote_at = now

        db.commit()

    def _should_reset_daily(self, account: Account, now: datetime) -> bool:
        if account.last_vote_at is None:
            return True
        return (now - account.last_vote_at).total_seconds() >= 86400

    def _should_reset_weekly(self, account: Account, now: datetime) -> bool:
        if account.last_vote_at is None:
            return True
        return (now - account.last_vote_at).total_seconds() >= 604800

    def get_stats(self, account: Account) -> dict:
        return {
            "votes_today": account.votes_today,
            "votes_this_week": account.votes_this_week,
            "last_vote_at": account.last_vote_at.isoformat() if account.last_vote_at else None,
            "active_hours": f"{account.active_hours_start}-{account.active_hours_end}",
        }


def get_rate_limiter() -> RateLimiter:
    return RateLimiter()
