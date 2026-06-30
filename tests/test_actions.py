"""Unit tests for action classes."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from app.services.queue_actions.base import BaseAction, ActionResult
from app.services.queue_actions.actions import (
    UpvotePost, DownvotePost, UpvoteComment, DownvoteComment,
    FollowUser, UnfollowUser, JoinSubreddit, LeaveSubreddit, SavePost
)


class TestBaseAction:
    """Tests for BaseAction class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.camofox = Mock()
        self.action = BaseAction(self.camofox)

    def test_find_ref_by_pattern_found(self):
        """Test finding element ref by pattern."""
        snapshot = 'button "upvote" [e12345] some text'
        ref = self.action.find_ref_by_pattern(snapshot, r'button\s+"upvote"\s+\[e(\d+)\]')
        assert ref == 'e12345'

    def test_find_ref_by_pattern_not_found(self):
        """Test finding element ref when not present."""
        snapshot = 'button "downvote" [e12345] some text'
        ref = self.action.find_ref_by_pattern(snapshot, r'button\s+"upvote"\s+\[e(\d+)\]')
        assert ref is None

    def test_find_ref_after_text_found(self):
        """Test finding element ref after specific text."""
        snapshot = 'some text single comment\'s thread button "upvote" [e12345]'
        ref = self.action.find_ref_after_text(snapshot, "single comment's thread", r'button\s+"upvote"\s+\[e(\d+)\]')
        assert ref == 'e12345'

    def test_find_ref_after_text_not_found(self):
        """Test finding element ref when marker not present."""
        snapshot = 'button "upvote" [e12345] some text'
        ref = self.action.find_ref_after_text(snapshot, "single comment's thread", r'button\s+"upvote"\s+\[e(\d+)\]')
        assert ref is None

    def test_detect_popup_suspended(self):
        """Test detecting suspended popup."""
        snapshot = 'Your account has been suspended due to unusual activity.'
        popup = self.action.detect_popup(snapshot)
        assert popup == 'popup_suspended'

    def test_detect_popup_locked(self):
        """Test detecting locked popup."""
        snapshot = 'This account has been locked. You will need to reset your password.'
        popup = self.action.detect_popup(snapshot)
        assert popup == 'popup_account_locked'

    def test_detect_popup_rate_limited(self):
        """Test detecting rate limited popup."""
        snapshot = 'You cannot vote right now. Please wait before voting again.'
        popup = self.action.detect_popup(snapshot)
        assert popup == 'popup_cannot_vote'

    def test_detect_popup_none(self):
        """Test no popup detected."""
        snapshot = 'Normal page content without any popups.'
        popup = self.action.detect_popup(snapshot)
        assert popup is None

    def test_detect_header_banner_suspended(self):
        """Test detecting suspended header banner."""
        snapshot = 'Reddit has suspended your account.'
        banner = self.action.detect_header_banner(snapshot)
        assert banner == 'suspended'

    def test_detect_header_banner_banned(self):
        """Test detecting banned header banner."""
        snapshot = 'You are banned from Reddit.'
        banner = self.action.detect_header_banner(snapshot)
        assert banner == 'banned'

    def test_detect_header_banner_none(self):
        """Test no header banner detected."""
        snapshot = 'Normal page content without any banners.'
        banner = self.action.detect_header_banner(snapshot)
        assert banner is None


class TestUpvotePost:
    """Tests for UpvotePost action."""

    def setup_method(self):
        """Set up test fixtures."""
        self.camofox = Mock()
        self.action = UpvotePost(self.camofox)

    def test_action_type(self):
        """Test action type is correct."""
        assert self.action.action_type == 'upvote_post'

    def test_target_pattern(self):
        """Test target pattern is correct."""
        assert 'upvote' in self.action.target_pattern

    def test_action_blocked_by_banner_returns_none(self):
        """Test that vote actions don't check banner before click."""
        snapshot = 'Reddit has suspended your account.'
        result = self.action.action_blocked_by_banner(snapshot)
        assert result is None

    def test_verify_success_no_popup(self):
        """Test verification succeeds when no popup."""
        snapshot = 'Normal content after upvote.'
        success, error = self.action.verify_success(snapshot)
        assert success is True
        assert error is None

    def test_verify_success_with_popup(self):
        """Test verification fails when popup detected."""
        snapshot = 'Your account has been suspended due to unusual activity.'
        success, error = self.action.verify_success(snapshot)
        assert success is False
        assert 'suspended' in error


class TestDownvotePost:
    """Tests for DownvotePost action."""

    def setup_method(self):
        """Set up test fixtures."""
        self.camofox = Mock()
        self.action = DownvotePost(self.camofox)

    def test_action_type(self):
        """Test action type is correct."""
        assert self.action.action_type == 'downvote_post'

    def test_target_pattern(self):
        """Test target pattern is correct."""
        assert 'downvote' in self.action.target_pattern


class TestUpvoteComment:
    """Tests for UpvoteComment action."""

    def setup_method(self):
        """Set up test fixtures."""
        self.camofox = Mock()
        self.action = UpvoteComment(self.camofox)

    def test_action_type(self):
        """Test action type is correct."""
        assert self.action.action_type == 'upvote_comment'

    def test_marker_present(self):
        """Test marker for comment context is present."""
        assert hasattr(self.action, 'marker')
        assert "single comment's thread" in self.action.marker


class TestFollowUser:
    """Tests for FollowUser action."""

    def setup_method(self):
        """Set up test fixtures."""
        self.camofox = Mock()
        self.action = FollowUser(self.camofox)

    def test_action_type(self):
        """Test action type is correct."""
        assert self.action.action_type == 'follow_user'

    def test_use_old_reddit_false(self):
        """Test that follow uses www.reddit.com, not old.reddit.com."""
        assert self.action.use_old_reddit is False

    def test_target_pattern(self):
        """Test target pattern is correct."""
        assert 'Follow' in self.action.target_pattern

    def test_verify_success_button_changed(self):
        """Test verification succeeds when button text changes."""
        snapshot = 'button "Following" [e12345]'
        success, error = self.action.verify_success(snapshot)
        assert success is True

    def test_verify_success_banner_detected(self):
        """Test verification fails when banner detected."""
        snapshot = 'Reddit has suspended your account. button "Follow" [e12345]'
        success, error = self.action.verify_success(snapshot)
        assert success is False
        assert 'suspended' in error


class TestJoinSubreddit:
    """Tests for JoinSubreddit action."""

    def setup_method(self):
        """Set up test fixtures."""
        self.camofox = Mock()
        self.action = JoinSubreddit(self.camofox)

    def test_action_type(self):
        """Test action type is correct."""
        assert self.action.action_type == 'join_subreddit'

    def test_target_pattern(self):
        """Test target pattern is correct."""
        assert 'join' in self.action.target_pattern.lower()

    def test_verify_success_link_changed(self):
        """Test verification succeeds when link text changes."""
        snapshot = 'link "joined" [e12345]'
        success, error = self.action.verify_success(snapshot)
        assert success is True


class TestSavePost:
    """Tests for SavePost action."""

    def setup_method(self):
        """Set up test fixtures."""
        self.camofox = Mock()
        self.action = SavePost(self.camofox)

    def test_action_type(self):
        """Test action type is correct."""
        assert self.action.action_type == 'save_post'

    def test_target_pattern(self):
        """Test target pattern is correct."""
        assert 'save' in self.action.target_pattern.lower()

    def test_verify_success_button_changed(self):
        """Test verification succeeds when button text changes."""
        snapshot = 'button "unsave" [e12345]'
        success, error = self.action.verify_success(snapshot)
        assert success is True
