"""
Tests for leave_subreddit action - direct action testing without QueueProcessor.
"""
import time
import logging
import pytest
from unittest.mock import Mock

from app.models import TaskActionLog

logger = logging.getLogger("tests.leave_subreddit")


class MockCamofox:
    """Mock CamofoxClient for testing."""

    def __init__(self, pre_click_snapshot, post_click_snapshot):
        self.pre_click_snapshot = pre_click_snapshot
        self.post_click_snapshot = post_click_snapshot
        self.snapshot_count = 0
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
        self.snapshot_count += 1
        if self.snapshot_count == 1:
            return self.pre_click_snapshot, "http://test"
        return self.post_click_snapshot, "http://test"

    def click(self, tab, ref):
        self.clicks.append(ref)

    def close_tab(self, tab):
        pass


def get_mock_snapshots(scenario=None):
    """Get pre_click and post_click snapshots based on scenario."""
    pre_click_base = '''
    <html>
    <body>
    <div class="header">Reddit Header</div>
    '''
    post_click_success = '''
    <html>
    <body>
    <div class="header">Reddit Header</div>
    <link "join" [e12345]>join</link>
    </body></html>
    '''
    post_click_locked = '''
    <html>
    <body>
    <div class="header">Reddit Header</div>
    <link "joined" [e12345]>joined</link>
    <div class="modal">
    <p>This account has been locked. You will need to reset your password.</p>
    </div>
    </body></html>
    '''

    if scenario == "banned":
        pre_click_base += '''
        <div class="banner">
        <p>You are banned from Reddit.</p>
        </div>
        <link "joined" [e12345]>joined</link>
        '''
        return pre_click_base + '</body></html>', pre_click_base + '</body></html>'
    elif scenario == "suspended":
        pre_click_base += '''
        <div class="banner">
        <p>Your account has been suspended due to suspicious activity.</p>
        </div>
        <link "joined" [e12345]>joined</link>
        '''
        return pre_click_base + '</body></html>', pre_click_base + '</body></html>'
    elif scenario == "locked":
        pre_click_base += '<link "joined" [e12345]>joined</link></body></html>'
        return pre_click_base, post_click_locked
    else:
        pre_click_base += '<link "joined" [e12345]>joined</link></body></html>'
        return pre_click_base, post_click_success


class TestLeaveSubredditDirect:
    """Tests for leave_subreddit action - direct execution."""

    def test_leave_success(self, db_session):
        """Test successful leave."""
        from app.services.queue_actions import get_action_class

        logger.info(f"[TEST] Starting test_leave_success")

        pre_snap, post_snap = get_mock_snapshots()
        camofox = MockCamofox(pre_snap, post_snap)

        action = get_action_class("leave_subreddit")(camofox)

        mock_worker = Mock()
        mock_worker.id = 1
        mock_worker.account_id = 1
        mock_worker.username = "test_user"

        result = action.execute(mock_worker, "http://test/r/test")

        logger.info(f"[TEST] Result: success={result.success} outcome={result.outcome}")

        assert result.success == True, f"Expected success=True, got {result.success}"
        assert result.outcome == "success", f"Expected outcome='success', got '{result.outcome}'"

        logger.info(f"[TEST] ✅ PASSED: test_leave_success")

    def test_leave_scenario_banned(self, db_session):
        """Test leave with banned scenario."""
        from app.services.queue_actions import get_action_class

        logger.info(f"[TEST] Starting test_leave_scenario_banned")

        pre_snap, post_snap = get_mock_snapshots(scenario="banned")
        camofox = MockCamofox(pre_snap, post_snap)

        action = get_action_class("leave_subreddit")(camofox)

        mock_worker = Mock()
        mock_worker.id = 1
        mock_worker.account_id = 1
        mock_worker.username = "test_user"

        result = action.execute(mock_worker, "http://test/r/test?scenario=banned")

        logger.info(f"[TEST] Result: success={result.success} outcome={result.outcome}")

        assert result.success == False, f"Expected success=False, got {result.success}"
        assert "banned" in result.outcome.lower(), f"Expected banned in outcome, got '{result.outcome}'"

        logger.info(f"[TEST] ✅ PASSED: test_leave_scenario_banned")

    def test_leave_scenario_suspended(self, db_session):
        """Test leave with suspended scenario."""
        from app.services.queue_actions import get_action_class

        logger.info(f"[TEST] Starting test_leave_scenario_suspended")

        pre_snap, post_snap = get_mock_snapshots(scenario="suspended")
        camofox = MockCamofox(pre_snap, post_snap)

        action = get_action_class("leave_subreddit")(camofox)

        mock_worker = Mock()
        mock_worker.id = 1
        mock_worker.account_id = 1
        mock_worker.username = "test_user"

        result = action.execute(mock_worker, "http://test/r/test?scenario=suspended")

        logger.info(f"[TEST] Result: success={result.success} outcome={result.outcome}")

        assert result.success == False, f"Expected success=False, got {result.success}"
        assert "suspended" in result.outcome.lower(), f"Expected suspended in outcome, got '{result.outcome}'"

        logger.info(f"[TEST] ✅ PASSED: test_leave_scenario_suspended")

    def test_leave_scenario_locked(self, db_session):
        """Test leave with locked scenario (popup after click)."""
        from app.services.queue_actions import get_action_class

        logger.info(f"[TEST] Starting test_leave_scenario_locked")

        pre_snap, post_snap = get_mock_snapshots(scenario="locked")
        camofox = MockCamofox(pre_snap, post_snap)

        action = get_action_class("leave_subreddit")(camofox)

        mock_worker = Mock()
        mock_worker.id = 1
        mock_worker.account_id = 1
        mock_worker.username = "test_user"

        result = action.execute(mock_worker, "http://test/r/test?scenario=locked")

        logger.info(f"[TEST] Result: success={result.success} outcome={result.outcome}")

        assert result.success == False, f"Expected success=False, got {result.success}"
        assert "locked" in result.outcome.lower() or "account_locked" in result.outcome, f"Expected locked in outcome, got '{result.outcome}'"

        logger.info(f"[TEST] ✅ PASSED: test_leave_scenario_locked")
