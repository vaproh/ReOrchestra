"""
Tests for upvote_comment action - direct action testing without QueueProcessor.
"""
import time
import logging
import pytest
from unittest.mock import Mock

from app.models import TaskActionLog

logger = logging.getLogger("tests.upvote_comment")


class MockCamofox:
    """Mock CamofoxClient for testing."""

    def __init__(self, snapshot_content):
        self.snapshot_content = snapshot_content
        self.user_id = None
        self.session_key = None
        self.tabs_created = []
        self.clicks = []

    def create_tab(self, url):
        tab = Mock()
        tab.id = f"tab_{len(self.tabs_created)}"
        self.tabs_created.append(tab)
        return tab

    def wait(self, tab, timeout=None):
        time.sleep(0.1)

    def snapshot_quick(self, tab):
        return self.snapshot_content, "http://test"

    def click(self, tab, ref):
        self.clicks.append(ref)

    def close_tab(self, tab):
        pass


def get_mock_snapshot(scenario=None):
    """Get mock snapshot based on scenario."""
    base = '''
    <html>
    <body>
    <div class="single comment's thread">
    <button "upvote" [e12345]>Upvote</button>
    <button "downvote" [e12346]>Downvote</button>
    </div>
    '''
    if scenario == "suspended":
        base += '''
        <div class="modal">
        <p>Your account has been suspended due to unusual activity.</p>
        </div>
        '''
    elif scenario == "locked":
        base += '''
        <div class="modal">
        <p>This account has been locked. You will need to reset your password.</p>
        </div>
        '''
    elif scenario == "rate_limited":
        base += '''
        <div class="modal">
        <p>rate limit exceeded</p>
        </div>
        '''
    base += '</body></html>'
    return base


class TestUpvoteCommentDirect:
    """Tests for upvote_comment action - direct execution."""

    def test_upvote_comment_success(self, db_session):
        """Test successful upvote on comment."""
        from app.services.queue_actions import get_action_class

        logger.info(f"[TEST] Starting test_upvote_comment_success")

        snapshot = get_mock_snapshot()
        camofox = MockCamofox(snapshot)

        action = get_action_class("upvote_comment")(camofox)

        mock_worker = Mock()
        mock_worker.id = 1
        mock_worker.account_id = 1
        mock_worker.username = "test_user"

        result = action.execute(mock_worker, "http://test/comment/test")

        logger.info(f"[TEST] Result: success={result.success} outcome={result.outcome}")

        assert result.success == True, f"Expected success=True, got {result.success}"
        assert result.outcome == "success", f"Expected outcome='success', got '{result.outcome}'"

        logger.info(f"[TEST] ✅ PASSED: test_upvote_comment_success")

    def test_upvote_comment_scenario_suspended(self, db_session):
        """Test upvote comment with suspended scenario."""
        from app.services.queue_actions import get_action_class

        logger.info(f"[TEST] Starting test_upvote_comment_scenario_suspended")

        snapshot = get_mock_snapshot(scenario="suspended")
        camofox = MockCamofox(snapshot)

        action = get_action_class("upvote_comment")(camofox)

        mock_worker = Mock()
        mock_worker.id = 1
        mock_worker.account_id = 1
        mock_worker.username = "test_user"

        result = action.execute(mock_worker, "http://test/comment/test?scenario=suspended")

        logger.info(f"[TEST] Result: success={result.success} outcome={result.outcome}")

        assert result.success == False, f"Expected success=False, got {result.success}"
        assert "suspended" in result.outcome.lower(), f"Expected suspended in outcome, got '{result.outcome}'"

        logger.info(f"[TEST] ✅ PASSED: test_upvote_comment_scenario_suspended")

    def test_upvote_comment_scenario_locked(self, db_session):
        """Test upvote comment with locked scenario."""
        from app.services.queue_actions import get_action_class

        logger.info(f"[TEST] Starting test_upvote_comment_scenario_locked")

        snapshot = get_mock_snapshot(scenario="locked")
        camofox = MockCamofox(snapshot)

        action = get_action_class("upvote_comment")(camofox)

        mock_worker = Mock()
        mock_worker.id = 1
        mock_worker.account_id = 1
        mock_worker.username = "test_user"

        result = action.execute(mock_worker, "http://test/comment/test?scenario=locked")

        logger.info(f"[TEST] Result: success={result.success} outcome={result.outcome}")

        assert result.success == False, f"Expected success=False, got {result.success}"
        assert "locked" in result.outcome.lower() or "account_locked" in result.outcome, f"Expected locked in outcome, got '{result.outcome}'"

        logger.info(f"[TEST] ✅ PASSED: test_upvote_comment_scenario_locked")

    def test_upvote_comment_scenario_rate_limited(self, db_session):
        """Test upvote comment with rate limited scenario."""
        from app.services.queue_actions import get_action_class

        logger.info(f"[TEST] Starting test_upvote_comment_scenario_rate_limited")

        snapshot = get_mock_snapshot(scenario="rate_limited")
        camofox = MockCamofox(snapshot)

        action = get_action_class("upvote_comment")(camofox)

        mock_worker = Mock()
        mock_worker.id = 1
        mock_worker.account_id = 1
        mock_worker.username = "test_user"

        result = action.execute(mock_worker, "http://test/comment/test?scenario=rate_limited")

        logger.info(f"[TEST] Result: success={result.success} outcome={result.outcome}")

        assert result.success == False, f"Expected success=False, got {result.success}"
        assert "rate" in result.outcome.lower(), f"Expected rate in outcome, got '{result.outcome}'"

        logger.info(f"[TEST] ✅ PASSED: test_upvote_comment_scenario_rate_limited")
