"""
Reddit action executors for the worker queue system.

All actions extend BaseAction and implement find_target_ref + verify_success.
"""

import re
from typing import Optional
import logging

from app.modules.executor.actions.base import BaseAction

logger = logging.getLogger("actions")


# ============================================================
# Vote actions (posts & comments)
# ============================================================


class UpvotePost(BaseAction):
    action_type = "upvote_post"
    target_pattern = r'button\s+"upvote"\s+\[e(\d+)\]'

    def action_blocked_by_banner(self, snapshot: str) -> Optional[str]:
        return None

    def verify_success(self, snapshot: str) -> tuple[bool, Optional[str]]:
        popup = self.detect_popup(snapshot)
        if popup:
            return False, popup.removeprefix("popup_")
        return True, None


class DownvotePost(BaseAction):
    action_type = "downvote_post"
    target_pattern = r'button\s+"downvote"\s+\[e(\d+)\]'

    def action_blocked_by_banner(self, snapshot: str) -> Optional[str]:
        return None

    def verify_success(self, snapshot: str) -> tuple[bool, Optional[str]]:
        popup = self.detect_popup(snapshot)
        if popup:
            return False, popup.removeprefix("popup_")
        return True, None


class UpvoteComment(BaseAction):
    action_type = "upvote_comment"
    marker = "single comment's thread"
    target_pattern = r'button\s+"upvote"\s+\[e(\d+)\]'

    def find_target_ref(self, snapshot: str) -> Optional[str]:
        return self.find_ref_after_text(snapshot, self.marker, self.target_pattern)

    def action_blocked_by_banner(self, snapshot: str) -> Optional[str]:
        return None

    def verify_success(self, snapshot: str) -> tuple[bool, Optional[str]]:
        popup = self.detect_popup(snapshot)
        if popup:
            return False, popup.removeprefix("popup_")
        return True, None


class DownvoteComment(BaseAction):
    action_type = "downvote_comment"
    marker = "single comment's thread"
    target_pattern = r'button\s+"downvote"\s+\[e(\d+)\]'

    def find_target_ref(self, snapshot: str) -> Optional[str]:
        return self.find_ref_after_text(snapshot, self.marker, self.target_pattern)

    def action_blocked_by_banner(self, snapshot: str) -> Optional[str]:
        return None

    def verify_success(self, snapshot: str) -> tuple[bool, Optional[str]]:
        popup = self.detect_popup(snapshot)
        if popup:
            return False, popup.removeprefix("popup_")
        return True, None


# ============================================================
# Follow / Unfollow user (must use www.reddit.com)
# ============================================================


class FollowUser(BaseAction):
    action_type = "follow_user"
    use_old_reddit = False
    target_pattern = r'button\s+"Follow"\s+\[e(\d+)\]'

    def verify_success(self, snapshot: str) -> tuple[bool, Optional[str]]:
        banner = self.detect_header_banner(snapshot)
        if banner:
            return False, f"header_{banner}"
        popup = self.detect_popup(snapshot)
        if popup:
            return False, popup.removeprefix("popup_")
        if 'button "Following"' in snapshot:
            return True, None
        return False, "Follow button did not change to Following"


class UnfollowUser(BaseAction):
    action_type = "unfollow_user"
    use_old_reddit = False
    target_pattern = r'button\s+"Unfollow"\s+\[e(\d+)\]'

    def verify_success(self, snapshot: str) -> tuple[bool, Optional[str]]:
        banner = self.detect_header_banner(snapshot)
        if banner:
            return False, f"header_{banner}"
        popup = self.detect_popup(snapshot)
        if popup:
            return False, popup.removeprefix("popup_")
        if 'button "Follow"' in snapshot and 'button "Following"' not in snapshot:
            return True, None
        return False, "Unfollow did not revert to Follow"


# ============================================================
# Join / Leave subreddit (old reddit, use link not button)
# ============================================================


class JoinSubreddit(BaseAction):
    action_type = "join_subreddit"
    target_pattern = r'link\s+"join"\s+\[e(\d+)\]'

    def verify_success(self, snapshot: str) -> tuple[bool, Optional[str]]:
        banner = self.detect_header_banner(snapshot)
        if banner:
            return False, f"header_{banner}"
        popup = self.detect_popup(snapshot)
        if popup:
            return False, popup.removeprefix("popup_")
        if 'link "joined"' in snapshot:
            return True, None
        return False, "join link did not change to joined"


class LeaveSubreddit(BaseAction):
    action_type = "leave_subreddit"
    target_pattern = r'link\s+"joined"\s+\[e(\d+)\]'

    def verify_success(self, snapshot: str) -> tuple[bool, Optional[str]]:
        banner = self.detect_header_banner(snapshot)
        if banner:
            return False, f"header_{banner}"
        popup = self.detect_popup(snapshot)
        if popup:
            return False, popup.removeprefix("popup_")
        if 'link "join"' in snapshot and 'link "joined"' not in snapshot:
            return True, None
        return False, "joined link did not revert to join"


# ============================================================
# Save post
# ============================================================


class SavePost(BaseAction):
    action_type = "save_post"
    target_pattern = r'button\s+"save"\s+\[e(\d+)\]'

    def verify_success(self, snapshot: str) -> tuple[bool, Optional[str]]:
        banner = self.detect_header_banner(snapshot)
        if banner:
            return False, f"header_{banner}"
        popup = self.detect_popup(snapshot)
        if popup:
            return False, popup.removeprefix("popup_")
        if 'button "unsave"' in snapshot:
            return True, None
        return False, "save button did not change to unsave"


# ============================================================
# Registry: action_type -> Action class
# ============================================================

ACTIONS = {
    "upvote_post": UpvotePost,
    "downvote_post": DownvotePost,
    "upvote_comment": UpvoteComment,
    "downvote_comment": DownvoteComment,
    "follow_user": FollowUser,
    "unfollow_user": UnfollowUser,
    "join_subreddit": JoinSubreddit,
    "leave_subreddit": LeaveSubreddit,
    "save_post": SavePost,
}


def get_action_class(action_type: str):
    return ACTIONS.get(action_type)
