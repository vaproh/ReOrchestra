import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Account, ActionLog, Proxy
from app.models import AccountStatus
from app.services.config_service import get_config

logger = logging.getLogger("burn_detector")


class BurnDetector:
    def __init__(self):
        self.config = get_config()

    def record_result(
        self,
        db: Session,
        account: Account,
        success: bool,
        error: Optional[str] = None,
        http_status: Optional[int] = None,
    ) -> None:
        if success:
            account.consecutive_failures = 0
            db.commit()
            return

        account.consecutive_failures += 1
        account.last_failure_at = datetime.utcnow()

        consecutive_limit = self.config.get(
            "burn_detection", "consecutive_failures", default=5
        )

        if account.consecutive_failures >= consecutive_limit:
            self._handle_burn_detection(db, account, error or "unknown")

        if http_status == 429:
            self._handle_rate_limit(db, account)

        if http_status in (401, 403) or error in ("401", "403", "banned"):
            self._handle_potential_ban(db, account, error or "http_error")

        db.commit()

    def _handle_burn_detection(
        self,
        db: Session,
        account: Account,
        error: str,
    ) -> None:
        account.status = AccountStatus.dead
        account.dead_reason = error
        logger.warning(
            f"Account {account.username} marked dead: {error} "
            f"(consecutive_failures={account.consecutive_failures})"
        )

    def _handle_rate_limit(self, db: Session, account: Account) -> None:
        backoff_hours = self.config.get(
            "burn_detection", "rate_limit_backoff_hours", default=24
        )
        logger.warning(
            f"Account {account.username} rate limited, backing off for {backoff_hours}h"
        )

    def _handle_potential_ban(
        self,
        db: Session,
        account: Account,
        error: str,
    ) -> None:
        account.status = AccountStatus.banned
        account.dead_reason = f"ban_detected:{error}"
        logger.warning(f"Account {account.username} banned: {error}")

    def check_success_rate(
        self,
        db: Session,
        account: Account,
        window_days: int = 7,
    ) -> float:
        cutoff = datetime.utcnow() - timedelta(days=window_days)

        total = db.query(ActionLog).filter(
            ActionLog.account_id == account.id,
            ActionLog.created_at >= cutoff,
        ).count()

        if total == 0:
            return 1.0

        successful = db.query(ActionLog).filter(
            ActionLog.account_id == account.id,
            ActionLog.created_at >= cutoff,
            ActionLog.success == True,
        ).count()

        return successful / total if total > 0 else 0.0

    def mark_if_dead(
        self,
        db: Session,
        account: Account,
    ) -> bool:
        threshold = self.config.get(
            "burn_detection", "success_rate_threshold", default=0.8
        )
        max_fails = self.config.get("account_limits", "max_fail_count", default=10)

        if account.fail_count >= max_fails:
            account.status = AccountStatus.dead
            account.dead_reason = "max_failures"
            db.commit()
            return True

        success_rate = self.check_success_rate(db, account)
        if success_rate < threshold:
            account.status = AccountStatus.dead
            account.dead_reason = f"low_success_rate:{success_rate:.2f}"
            db.commit()
            logger.warning(
                f"Account {account.username} marked dead: "
                f"success_rate={success_rate:.2%} < {threshold:.2%}"
            )
            return True

        return False

    def should_retry(
        self,
        db: Session,
        account: Account,
    ) -> tuple[bool, Optional[str]]:
        if account.status == AccountStatus.dead:
            return False, "account_dead"

        backoff_hours = self.config.get(
            "burn_detection", "rate_limit_backoff_hours", default=24
        )

        if account.last_failure_at:
            hours_since_failure = (
                datetime.utcnow() - account.last_failure_at
            ).total_seconds() / 3600

            if hours_since_failure < backoff_hours:
                remaining = backoff_hours - hours_since_failure
                return False, f"backoff_remaining:{remaining:.1f}h"

        return True, None

    def get_account_health(
        self,
        db: Session,
        account: Account,
    ) -> dict:
        success_rate = self.check_success_rate(db, account)
        should_retry, retry_reason = self.should_retry(db, account)

        return {
            "username": account.username,
            "status": account.status.value,
            "consecutive_failures": account.consecutive_failures,
            "fail_count": account.fail_count,
            "success_rate_7d": round(success_rate, 3),
            "should_retry": should_retry,
            "retry_reason": retry_reason,
            "last_failure_at": (
                account.last_failure_at.isoformat()
                if account.last_failure_at else None
            ),
        }


def get_burn_detector() -> BurnDetector:
    return BurnDetector()
