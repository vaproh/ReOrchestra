"""Unit tests for RateLimiter."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session

from app.services.rate_limiter import RateLimiter
from app.models import Account, AccountStatus, TaskActionLog, Worker


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.rate_limiter = RateLimiter()
        self.mock_db = Mock(spec=Session)

    def _create_mock_account(self, **kwargs):
        """Create a mock account with default values."""
        account = Mock(spec=Account)
        account.id = kwargs.get('id', 1)
        account.status = kwargs.get('status', AccountStatus.logged_in)
        account.votes_today = kwargs.get('votes_today', 0)
        account.votes_this_week = kwargs.get('votes_this_week', 0)
        account.last_vote_at = kwargs.get('last_vote_at', None)
        account.active_hours_start = kwargs.get('active_hours_start', 0)
        account.active_hours_end = kwargs.get('active_hours_end', 23)
        return account

    def test_check_allows_fresh_account(self):
        """Test that a fresh account with no votes is allowed."""
        account = self._create_mock_account()
        # Mock the vote ratio check to return False
        self.mock_db.query.return_value.join.return_value.filter.return_value.count.return_value = 0
        allowed, reason = self.rate_limiter.check(account, self.mock_db)
        assert allowed is True
        assert reason == ""

    def test_check_rejects_dead_account(self):
        """Test that a dead account is rejected."""
        account = self._create_mock_account(status=AccountStatus.dead)
        allowed, reason = self.rate_limiter.check(account, self.mock_db)
        assert allowed is False
        assert "dead" in reason.lower()

    def test_check_rejects_banned_account(self):
        """Test that a banned account is rejected."""
        account = self._create_mock_account(status=AccountStatus.banned)
        allowed, reason = self.rate_limiter.check(account, self.mock_db)
        assert allowed is False
        assert "banned" in reason.lower()

    def test_check_rejects_daily_limit_exceeded(self):
        """Test that account exceeding daily limit is rejected."""
        account = self._create_mock_account(votes_today=15)
        # Mock config to return 15 as max_votes_per_day
        self.rate_limiter.config = Mock()
        self.rate_limiter.config.get.return_value = 15
        allowed, reason = self.rate_limiter.check(account, self.mock_db)
        assert allowed is False
        assert "daily" in reason.lower()

    def test_check_rejects_weekly_limit_exceeded(self):
        """Test that account exceeding weekly limit is rejected."""
        account = self._create_mock_account(votes_this_week=100)
        # Mock config to return 100 as max_votes_per_week
        self.rate_limiter.config = Mock()
        self.rate_limiter.config.get.side_effect = lambda s, k, default=None: {
            ('rate_limits', 'max_votes_per_week'): 100,
            ('rate_limits', 'max_votes_per_day'): 15,
        }.get((s, k), default)
        allowed, reason = self.rate_limiter.check(account, self.mock_db)
        assert allowed is False
        assert "weekly" in reason.lower()

    def test_check_rejects_cooldown_not_met(self):
        """Test that account within cooldown period is rejected."""
        account = self._create_mock_account(
            last_vote_at=datetime.utcnow() - timedelta(seconds=60)
        )
        # Mock config to return 120 as min_seconds_between_votes
        self.rate_limiter.config = Mock()
        self.rate_limiter.config.get.side_effect = lambda s, k, default=None: {
            ('rate_limits', 'max_votes_per_day'): 15,
            ('rate_limits', 'max_votes_per_week'): 100,
            ('rate_limits', 'min_seconds_between_votes'): 120,
        }.get((s, k), default)
        allowed, reason = self.rate_limiter.check(account, self.mock_db)
        assert allowed is False
        assert "cooldown" in reason.lower()

    def test_check_allows_after_cooldown(self):
        """Test that account is allowed after cooldown period."""
        account = self._create_mock_account(
            last_vote_at=datetime.utcnow() - timedelta(seconds=130)
        )
        # Mock config to return 120 as min_seconds_between_votes
        self.rate_limiter.config = Mock()
        self.rate_limiter.config.get.side_effect = lambda s, k, default=None: {
            ('rate_limits', 'max_votes_per_day'): 15,
            ('rate_limits', 'max_votes_per_week'): 100,
            ('rate_limits', 'min_seconds_between_votes'): 120,
        }.get((s, k), default)
        # Mock vote ratio check to return False
        self.mock_db.query.return_value.join.return_value.filter.return_value.count.return_value = 0
        allowed, reason = self.rate_limiter.check(account, self.mock_db)
        assert allowed is True

    def test_record_vote_increments_counters(self):
        """Test that record_vote increments vote counters."""
        account = self._create_mock_account(
            votes_today=5,
            votes_this_week=20,
            last_vote_at=datetime.utcnow() - timedelta(hours=1)  # Within same day/week
        )
        self.rate_limiter.record_vote(account, self.mock_db)
        assert account.votes_today == 6
        assert account.votes_this_week == 21
        assert account.last_vote_at is not None
        self.mock_db.commit.assert_called_once()

    def test_record_vote_resets_daily_if_new_day(self):
        """Test that daily counter resets if last vote was yesterday."""
        account = self._create_mock_account(
            votes_today=10,
            votes_this_week=50,
            last_vote_at=datetime.utcnow() - timedelta(days=1)
        )
        self.rate_limiter.record_vote(account, self.mock_db)
        assert account.votes_today == 1  # Reset to 0, then incremented
        assert account.votes_this_week == 51

    def test_record_vote_resets_weekly_if_new_week(self):
        """Test that weekly counter resets if last vote was 7+ days ago."""
        account = self._create_mock_account(
            votes_today=5,
            votes_this_week=90,
            last_vote_at=datetime.utcnow() - timedelta(days=8)
        )
        self.rate_limiter.record_vote(account, self.mock_db)
        assert account.votes_today == 1  # Reset to 0, then incremented
        assert account.votes_this_week == 1  # Reset to 0, then incremented

    def test_get_stats_returns_account_stats(self):
        """Test that get_stats returns formatted account statistics."""
        account = self._create_mock_account(
            votes_today=5,
            votes_this_week=20,
            last_vote_at=datetime(2026, 6, 30, 12, 0, 0),
            active_hours_start=8,
            active_hours_end=22
        )
        stats = self.rate_limiter.get_stats(account)
        assert stats['votes_today'] == 5
        assert stats['votes_this_week'] == 20
        assert stats['last_vote_at'] == '2026-06-30T12:00:00'
        assert stats['active_hours'] == '8-22'

    def test_is_within_active_hours(self):
        """Test active hours check."""
        account = self._create_mock_account(active_hours_start=9, active_hours_end=17)
        # Mock datetime to return 12:00 (within hours)
        import app.services.rate_limiter as rl_module
        original_datetime = rl_module.datetime
        rl_module.datetime = Mock()
        rl_module.datetime.utcnow.return_value = Mock(hour=12)
        
        assert self.rate_limiter._is_within_active_hours(account) is True
        
        # Restore
        rl_module.datetime = original_datetime

    def test_is_outside_active_hours(self):
        """Test active hours check when outside hours."""
        account = self._create_mock_account(active_hours_start=9, active_hours_end=17)
        # Mock datetime to return 20:00 (outside hours)
        import app.services.rate_limiter as rl_module
        original_datetime = rl_module.datetime
        rl_module.datetime = Mock()
        rl_module.datetime.utcnow.return_value = Mock(hour=20)
        
        assert self.rate_limiter._is_within_active_hours(account) is False
        
        # Restore
        rl_module.datetime = original_datetime
