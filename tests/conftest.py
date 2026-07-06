"""
Pytest fixtures for ReOrchestra tests.

All tests use an in-memory SQLite database that is fresh per test.
Camofox is fully mocked — no real browser needed.
"""

import os
import sys
import random
import threading
import time
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import pytest

# Ensure app is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment variables BEFORE any app imports
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SESSION_DIR", "/tmp/reorchestra_test_sessions")
os.environ.setdefault("LOG_DIR", "/tmp/reorchestra_test_logs")
os.environ.setdefault("LOG_LEVEL", "CRITICAL")


# =============================================================================
# In-memory database session
# =============================================================================

@pytest.fixture(scope="function")
def db_engine(tmp_path):
    """Create a fresh SQLite engine per test using a temp file."""
    from sqlalchemy import create_engine
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    if "sqlite" in str(engine.url):
        from sqlalchemy import event

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a fresh DB session per test with all tables created."""
    from sqlalchemy.orm import sessionmaker
    from app.models import Base
    
    # Create all tables
    Base.metadata.create_all(bind=db_engine)
    
    Session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = Session()
    
    yield session
    
    session.rollback()
    session.close()


# =============================================================================
# Mock Camofox Client
# =============================================================================

class Tab:
    """Mock Tab object matching CamofoxClient.Tab structure."""
    def __init__(self, tab_id: str, user_id: str, session_key: str):
        self.tab_id = tab_id
        self.user_id = user_id
        self.session_key = session_key


class ActionResult:
    """Mock ActionResult for the mock executor."""
    def __init__(self, success: bool, outcome: str = "failed", 
                 error: Optional[str] = None, duration_ms: int = 0,
                 clicked_ref: Optional[str] = None):
        self.success = success
        self.outcome = outcome
        self.error = error
        self.duration_ms = duration_ms
        self.clicked_ref = clicked_ref


class MockCamofoxClient:
    """
    Fully mocked CamofoxClient for testing without a real browser.

    Configure behavior per-instance using configure():

        mock = MockCamofoxClient()
        mock.configure(
            success_rate=0.7,           # 70% success
            popup_suspended_rate=0.2,    # 20% popup_suspended
            element_not_found_rate=0.1,  # 10% element_not_found
        )

    Or use response_queue to have full control:

        mock = MockCamofoxClient()
        mock.response_queue = ["success", "popup_suspended", "element_not_found", ...]
    """

    SNAPSHOT_TEMPLATES = {
        "upvote_post": 'button "upvote" [e1]',
        "downvote_post": 'button "downvote" [e1]',
        "upvote_comment": 'button "upvote" [e1]',
        "downvote_comment": 'button "downvote" [e1]',
        "follow_user": 'button "Follow" [e2]',
        "unfollow_user": 'button "Unfollow" [e2]',
        "join_subreddit": 'link "join" [e3]',
        "leave_subreddit": 'link "leave" [e3]',
        "save_post": 'button "save" [e4]',
    }

    POPUP_TEMPLATES = {
        "popup_suspended": 'button "upvote" [e1]\nAccount suspended due to unusual activity',
        "popup_rate_limited": 'button "upvote" [e1]\nRate limit exceeded',
        "header_banned": 'banned from reddit\nbutton "upvote" [e1]',
        "header_suspended": 'Account suspended\nbutton "upvote" [e1]',
    }

    def __init__(self, *args, **kwargs):
        self.user_id = kwargs.get("user_id", "u1")
        self.session_key = kwargs.get("session_key", "s1")
        self.BASE_URL = "http://localhost:9377"

        # Configuration
        self.config = {
            "success_rate": 1.0,
            "popup_suspended_rate": 0.0,
            "popup_rate_limited_rate": 0.0,
            "header_banned_rate": 0.0,
            "header_suspended_rate": 0.0,
            "element_not_found_rate": 0.0,
            "click_timeout_rate": 0.0,
            "fail_count": 0,
            "fail_remaining": 0,
        }

        # Response queue for precise control (overrides config)
        self.response_queue: list[str] = []
        self._queue_index = 0

        # Call history for assertions
        self.calls: list[dict] = []

        # Tab storage
        self._tabs: dict[str, Tab] = {}

        # Per-tab state
        self._tab_snapshots: dict[str, str] = {}
        self._tab_urls: dict[str, str] = {}
        self._tab_action_type: dict[str, str] = {}

        # Account-to-response mapping for deterministic behavior
        self._account_responses: dict[int, str] = {}

    def _get_action_type_from_session(self, session_key: str) -> str:
        """Extract action_type from session_key like 'wq_42_upvote_post'."""
        parts = session_key.split("_")
        if len(parts) >= 3:
            return parts[-1]  # Last part is action_type
        return "upvote_post"  # Default
        
    def configure(
        self,
        success_rate: float = 1.0,
        popup_suspended_rate: float = 0.0,
        popup_rate_limited_rate: float = 0.0,
        header_banned_rate: float = 0.0,
        header_suspended_rate: float = 0.0,
        element_not_found_rate: float = 0.0,
        click_timeout_rate: float = 0.0,
        fail_count: int = 0,
    ):
        """Configure the mock behavior."""
        self.config = {
            "success_rate": success_rate,
            "popup_suspended_rate": popup_suspended_rate,
            "popup_rate_limited_rate": popup_rate_limited_rate,
            "header_banned_rate": header_banned_rate,
            "header_suspended_rate": header_suspended_rate,
            "element_not_found_rate": element_not_found_rate,
            "click_timeout_rate": click_timeout_rate,
            "fail_count": fail_count,
            "fail_remaining": fail_count,
        }
        
    def set_account_response(self, account_id: int, response: str):
        """Set a deterministic response for a specific account."""
        self._account_responses[account_id] = response
        
    def _generate_response(self, account_id: Optional[int] = None) -> str:
        """Generate a response based on config or queue."""
        # Check queue first
        if self.response_queue:
            if self._queue_index < len(self.response_queue):
                response = self.response_queue[self._queue_index]
                self._queue_index += 1
                return response
            return "success"  # Default to success when queue exhausted
            
        # Check per-account deterministic mapping
        if account_id and account_id in self._account_responses:
            return self._account_responses[account_id]
            
        # Check if we're in "fail mode"
        if self.config["fail_remaining"] > 0:
            self.config["fail_remaining"] -= 1
            return "element_not_found"
        
        # Random based on configured rates
        r = random.random()
        cumulative = 0.0
        
        cumulative += self.config["success_rate"]
        if r < cumulative:
            return "success"
        
        cumulative += self.config["popup_suspended_rate"]
        if r < cumulative:
            return "popup_suspended"
        
        cumulative += self.config["popup_rate_limited_rate"]
        if r < cumulative:
            return "popup_rate_limited"
        
        cumulative += self.config["header_banned_rate"]
        if r < cumulative:
            return "header_banned"
        
        cumulative += self.config["header_suspended_rate"]
        if r < cumulative:
            return "header_suspended"
        
        cumulative += self.config["element_not_found_rate"]
        if r < cumulative:
            return "element_not_found"
        
        cumulative += self.config["click_timeout_rate"]
        if r < cumulative:
            return "click_timeout"
        
        return "success"
    
    def create_tab(self, url: str = "about:blank") -> Tab:
        """Mock create_tab."""
        tab_id = f"tab_{uuid.uuid4().hex[:8]}"
        tab = Tab(tab_id=tab_id, user_id=self.user_id, session_key=self.session_key)
        self._tabs[tab_id] = tab
        self._tab_urls[tab_id] = url

        # Auto-generate snapshot based on action_type from session_key
        action_type = self._get_action_type_from_session(self.session_key)
        self._tab_action_type[tab_id] = action_type
        base_snapshot = self.SNAPSHOT_TEMPLATES.get(action_type, 'button "upvote" [e1]')
        self._tab_snapshots[tab_id] = base_snapshot

        self.calls.append({"method": "create_tab", "url": url, "tab_id": tab_id})
        return tab
    
    def navigate(self, tab: Tab, url: str, wait: float = 5.0) -> str:
        """Mock navigate."""
        self._tab_urls[tab.tab_id] = url
        self.calls.append({"method": "navigate", "tab_id": tab.tab_id, "url": url})
        return url
    
    def wait(self, tab: Tab, timeout: int = 5000, wait_network: bool = True) -> dict:
        """Mock wait."""
        self.calls.append({"method": "wait", "tab_id": tab.tab_id, "timeout": timeout})
        return {"ok": True, "ready": True}
    
    def snapshot_quick(self, tab: Tab) -> tuple[str, str]:
        """Mock snapshot_quick - returns snapshot and URL."""
        self.calls.append({"method": "snapshot_quick", "tab_id": tab.tab_id})
        snapshot = self._tab_snapshots.get(tab.tab_id, "")
        url = self._tab_urls.get(tab.tab_id, "https://reddit.com")
        return snapshot, url
    
    def set_snapshot(self, tab: Tab, snapshot: str, url: Optional[str] = None):
        """Set a specific snapshot for a tab (for testing)."""
        self._tab_snapshots[tab.tab_id] = snapshot
        if url:
            self._tab_urls[tab.tab_id] = url
    
    def snapshot(self, tab: Tab, wait_ready: bool = True, timeout: int = 5000) -> tuple[str, str]:
        """Mock snapshot."""
        return self.snapshot_quick(tab)
    
    def type_text(self, tab: Tab, ref: str, text: str, delay: float = 0.5) -> None:
        """Mock type_text."""
        self.calls.append({"method": "type_text", "tab_id": tab.tab_id, "ref": ref})
    
    def click(self, tab: Tab, ref: str, delay: float = 2.0) -> None:
        """Mock click."""
        self.calls.append({"method": "click", "tab_id": tab.tab_id, "ref": ref})
    
    def scroll(self, tab: Tab, direction: str = "down", amount: int = 800, delay: float = 1.0) -> None:
        """Mock scroll."""
        self.calls.append({"method": "scroll", "tab_id": tab.tab_id})
    
    def close_tab(self, tab: Tab) -> None:
        """Mock close_tab."""
        self.calls.append({"method": "close_tab", "tab_id": tab.tab_id})
        self._tabs.pop(tab.tab_id, None)
    
    def health(self) -> dict:
        """Mock health check."""
        return {"ok": True, "status": "running"}
    
    def set_user_proxy(self, user_id: str, proxy: str) -> dict:
        """Mock set_user_proxy."""
        self.calls.append({"method": "set_user_proxy", "user_id": user_id, "proxy": proxy})
        return {"ok": True}
    
    def get_last_tab(self) -> Optional[Tab]:
        """Get the most recently created tab (for testing)."""
        return list(self._tabs.values())[-1] if self._tabs else None
    
    def clear_calls(self):
        """Clear call history."""
        self.calls = []
    
    def reset(self):
        """Reset all state."""
        self._tabs.clear()
        self._tab_snapshots.clear()
        self._tab_urls.clear()
        self._queue_index = 0
        self.calls.clear()
        self._account_responses.clear()
        self.config["fail_remaining"] = self.config["fail_count"]


# =============================================================================
# Mock Rate Limiter
# =============================================================================

class MockRateLimiter:
    """
    Mock RateLimiter for testing.
    
    Configure to allow/deny specific accounts:
    
        mock = MockRateLimiter()
        mock.denied_accounts = {5, 10, 15}  # Account IDs to deny
    """
    
    def __init__(self):
        self.denied_accounts: set[int] = set()
        self.denied_reasons: dict[int, str] = {}
        self.check_count = 0
        self.vote_record_count = 0
        
    def check(self, account, db) -> tuple[bool, str]:
        """Check if account is rate limited."""
        self.check_count += 1
        if account.id in self.denied_accounts:
            reason = self.denied_reasons.get(account.id, "rate_limit_exceeded")
            return False, reason
        return True, ""
    
    def record_vote(self, account, db) -> None:
        """Record a vote for account."""
        self.vote_record_count += 1
    
    def get_stats(self, account) -> dict:
        return {"votes_today": 0, "votes_this_week": 0}
    
    def reset(self):
        self.denied_accounts.clear()
        self.denied_reasons.clear()
        self.check_count = 0
        self.vote_record_count = 0


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_camofox():
    """Create a fully configured MockCamofoxClient."""
    return MockCamofoxClient()


@pytest.fixture
def mock_rate_limiter():
    """Create a MockRateLimiter."""
    return MockRateLimiter()


@pytest.fixture
def rate_limit_config():
    """Set up test config overrides for rate limiting."""
    from app.modules.shared.config import get_config
    config = get_config()

    overrides = {
        "rate_limits.max_votes_per_day": 15,
        "rate_limits.max_votes_per_week": 100,
        "rate_limits.min_seconds_between_votes": 120,
        "rate_limits.max_vote_only_ratio": 0.3,
    }

    for key, value in overrides.items():
        config.set_runtime_override(key, value)

    yield config

    config.clear_runtime_overrides()


@pytest.fixture
def real_rate_limiter(rate_limit_config):
    """Create a real RateLimiter with test config."""
    from app.modules.executor.rate_limiter import RateLimiter
    return RateLimiter()


@pytest.fixture
def fresh_account(db_session):
    """Create a single fresh account."""
    from app.models import Account, AccountStatus, AccountType
    
    account = Account(
        username="testuser1",
        password="testpass123",
        email="test1@example.com",
        status=AccountStatus.fresh,
        account_type=AccountType.upvoter,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def logged_in_account(db_session):
    """Create a single logged-in account."""
    from app.models import Account, AccountStatus, AccountType
    
    account = Account(
        username="loggedin1",
        password="testpass123",
        status=AccountStatus.logged_in,
        account_type=AccountType.upvoter,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def fifty_accounts(db_session):
    """Create 50 logged-in accounts."""
    from app.models import Account, AccountStatus, AccountType
    
    accounts = []
    for i in range(1, 51):
        account = Account(
            username=f"account_{i:03d}",
            password=f"password_{i}",
            status=AccountStatus.logged_in,
            account_type=AccountType.upvoter,
            votes_today=0,
            votes_this_week=0,
        )
        db_session.add(account)
        accounts.append(account)
    
    db_session.commit()
    for acc in accounts:
        db_session.refresh(acc)
    
    return accounts


@pytest.fixture
def queued_task(db_session, fifty_accounts):
    """Create a task with workers_needed=10 using the fifty_accounts fixture."""
    from app.models import Task, TaskStatus
    
    task = Task(
        action_type="upvote_post",
        target_url="https://old.reddit.com/r/test/comments/abc123/",
        workers_needed=10,
        status=TaskStatus.queued,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


@pytest.fixture
def queued_task_noaccounts(db_session):
    """Create an empty queued task with no accounts."""
    from app.models import Task, TaskStatus
    
    task = Task(
        action_type="upvote_post",
        target_url="https://old.reddit.com/r/test/comments/abc123/",
        workers_needed=10,
        status=TaskStatus.queued,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


@pytest.fixture
def running_task(db_session, fifty_accounts):
    """Create a running task."""
    from app.models import Task, TaskStatus
    
    task = Task(
        action_type="upvote_post",
        target_url="https://old.reddit.com/r/test/comments/abc123/",
        workers_needed=10,
        status=TaskStatus.running,
        started_at=datetime.utcnow(),
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


@pytest.fixture
def completed_task(db_session, fifty_accounts):
    """Create a completed task."""
    from app.models import Task, TaskStatus
    
    task = Task(
        action_type="upvote_post",
        target_url="https://old.reddit.com/r/test/comments/abc123/",
        workers_needed=10,
        workers_completed=10,
        status=TaskStatus.completed,
        started_at=datetime.utcnow() - timedelta(minutes=5),
        completed_at=datetime.utcnow(),
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


@pytest.fixture
def processor(db_session, mock_camofox, mock_rate_limiter):
    """Create a QueueProcessor with mocked dependencies."""
    from app.modules.queue.processor import QueueProcessor
    
    proc = QueueProcessor.__new__(QueueProcessor)
    proc._session_factory = db_session.get_bind().__class__
    proc.camofox = mock_camofox
    proc.rate_limiter = mock_rate_limiter
    from app.config import get_settings
    settings = get_settings()
    proc.max_concurrent = getattr(settings, "max_concurrent_per_task", 3)
    proc.max_retries = 3
    proc._stop_event = threading.Event()
    proc._cancel_events = {}
    proc._thread = None
    proc._loop_errors = 0
    
    # Create a proper session factory
    from sqlalchemy.orm import sessionmaker
    from app.models import Base
    
    engine = db_session.get_bind()
    SessionFactory = sessionmaker(bind=engine)
    
    # Override the session factory
    proc._session_factory = SessionFactory
    
    return proc


@pytest.fixture
def all_action_types():
    """List of all valid action types."""
    return [
        "upvote_post",
        "downvote_post",
        "upvote_comment",
        "downvote_comment",
        "follow_user",
        "unfollow_user",
        "join_subreddit",
        "leave_subreddit",
        "save_post",
    ]


@pytest.fixture
def sample_account_data():
    """Sample account data for import tests."""
    return [
        {"username": f"user_{i}", "password": f"pass_{i}", "email": f"user_{i}@example.com"}
        for i in range(1, 51)
    ]
