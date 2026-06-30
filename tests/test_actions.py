import pytest
from unittest.mock import Mock, MagicMock
import time

from app.services.queue_actions import get_action_class


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


class TestActionRegistry:
    """Tests for action registry."""

    def test_all_action_types_registered(self):
        """Test that all expected action types are registered."""
        expected_actions = [
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
        for action_type in expected_actions:
            action_class = get_action_class(action_type)
            assert action_class is not None, f"Action {action_type} not registered"

    def test_unknown_action_returns_none(self):
        """Test that unknown action types return None."""
        action_class = get_action_class("unknown_action")
        assert action_class is None


class TestUpvoteActionDirect:
    """Test upvote_post action directly."""

    def test_upvote_success(self, db_session):
        """Test successful upvote."""
        snapshot = '''
        <html>
        <body>
        <button "upvote" [e12345]>Upvote</button>
        <button "downvote" [e12346]>Downvote</button>
        </body></html>
        '''
        camofox = MockCamofox(snapshot)
        action = get_action_class("upvote_post")(camofox)

        mock_worker = Mock()
        mock_worker.id = 1
        mock_worker.account_id = 1
        mock_worker.username = "test_user"

        result = action.execute(mock_worker, "http://test/post/test")
        assert result.success == True
        assert result.outcome == "success"


class TestDownvoteActionDirect:
    """Test downvote_post action directly."""

    def test_downvote_success(self, db_session):
        """Test successful downvote."""
        snapshot = '''
        <html>
        <body>
        <button "upvote" [e12345]>Upvote</button>
        <button "downvote" [e12346]>Downvote</button>
        </body></html>
        '''
        camofox = MockCamofox(snapshot)
        action = get_action_class("downvote_post")(camofox)

        mock_worker = Mock()
        mock_worker.id = 1
        mock_worker.account_id = 1
        mock_worker.username = "test_user"

        result = action.execute(mock_worker, "http://test/post/test")
        assert result.success == True
        assert result.outcome == "success"


class TestVoteDeduplication:
    """Test vote deduplication logic."""

    def test_dedup_hash(self, db_session):
        """Test dedup hash generation."""
        from app.services.queue_actions.base import dedup_hash

        hash1 = dedup_hash(1, "upvote_post", "http://test/post/123")
        hash2 = dedup_hash(1, "upvote_post", "http://test/post/123")
        hash3 = dedup_hash(1, "upvote_post", "http://test/post/456")

        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 16
