"""
Base action executor for the worker queue system.

Each action subclass implements `execute()` which:
1. Opens a Camofox tab
2. Navigates to the target URL
3. Locates the target element by scanning the snapshot
4. Clicks it
5. Checks for popups / verifies success
6. Closes the tab
7. Returns an ActionResult
"""

import re
import time
import random
import hashlib
from dataclasses import dataclass, field
from typing import Optional

from app.config import get_settings
from app.services.browser import CamofoxClient, Tab


@dataclass
class ActionResult:
    success: bool
    outcome: str = "failed"
    error: Optional[str] = None
    duration_ms: int = 0
    clicked_ref: Optional[str] = None


class BaseAction:
    """Base class for all Reddit actions."""

    # action_type identifier (e.g. "upvote_post")
    action_type: str = "base"

    # Whether to use old reddit (www.reddit.com -> old.reddit.com)
    # follow/unflow use www.reddit.com, everything else uses old
    use_old_reddit: bool = True

    # Regex pattern to find the target element in the snapshot
    # e.g. r'button\s+"upvote"\s+\[e(\d+)\]'
    target_pattern: str = ""

    def __init__(self, camofox: CamofoxClient):
        self.camofox = camofox

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

    def normalize_url(self, url: str) -> str:
        if not self.use_old_reddit:
            return url
        url = url.replace("https://www.reddit.com", "https://old.reddit.com")
        url = url.replace("https://reddit.com", "https://old.reddit.com")
        return url

    # ------------------------------------------------------------------
    # Snapshot scanning helpers
    # ------------------------------------------------------------------

    @staticmethod
    def find_ref_by_pattern(snapshot: str, pattern: str) -> Optional[str]:
        """Return the first ref (eNN) matching the regex pattern."""
        match = re.search(pattern, snapshot)
        if match:
            return f"e{match.group(1)}"
        return None

    @staticmethod
    def find_ref_after_text(snapshot: str, marker: str, pattern: str) -> Optional[str]:
        """Find the first ref matching `pattern` that appears AFTER `marker` text."""
        idx = snapshot.find(marker)
        if idx == -1:
            return None
        sub = snapshot[idx:]
        match = re.search(pattern, sub)
        if match:
            return f"e{match.group(1)}"
        return None

    # ------------------------------------------------------------------
    # Popup detection
    # ------------------------------------------------------------------

    @staticmethod
    def detect_popup(snapshot: str) -> Optional[str]:
        """
        Detects a popup AFTER an action click (vote actions).
        Popups appear as modal overlays with specific messaging.
        """
        lower = snapshot.lower()
        if "account has been locked" in lower or "password compromise" in lower:
            return "popup_account_locked"
        if "suspended" in lower or "unusual activity" in lower:
            return "popup_suspended"
        if "cannot vote" in lower:
            return "popup_cannot_vote"
        if "rate limit" in lower:
            return "popup_rate_limited"
        return None

    @staticmethod
    def detect_header_banner(snapshot: str) -> Optional[str]:
        """
        Detects the suspended/banned header banner BEFORE clicking (non-vote actions).
        Returns 'suspended', 'banned', or None.
        """
        lower = snapshot.lower()
        # Check for banned first since banned accounts can't be recovered
        if "banned from reddit" in lower or "account has been banned" in lower:
            return "banned"
        if "suspended your account" in lower or "account due to suspicious activity" in lower:
            return "suspended"
        return None

    def action_blocked_by_banner(self, snapshot: str) -> Optional[str]:
        """
        For non-vote actions: check header banner before clicking.
        Returns banner type if blocked, None if can proceed.
        Vote actions override this to always return None (they check after click).
        """
        return self.detect_header_banner(snapshot)

    # ------------------------------------------------------------------
    # Core execution flow
    # ------------------------------------------------------------------

    def execute(self, worker, target_url: str) -> ActionResult:
        """
        Default execution flow:
        1. Open tab & navigate
        2. Get snapshot
        3. Find target ref
        4. Click
        5. Verify
        6. Close tab
        """
        started = time.time()
        tab: Optional[Tab] = None
        try:
            url = self.normalize_url(target_url)
            session_key = f"wq_{worker.id}_{self.action_type}"
            user_id = f"s_{worker.account_id}"

            # Set on client BEFORE create_tab so the Tab gets correct user_id/session_key
            self.camofox.user_id = user_id
            self.camofox.session_key = session_key
            tab = self.camofox.create_tab(url=url)
            self.camofox.wait(tab)

            snapshot, current_url = self.camofox.snapshot_quick(tab)

            # For non-vote actions (follow/unfollow/join/leave/save): check banner BEFORE clicking
            banner = self.action_blocked_by_banner(snapshot)
            if banner:
                return ActionResult(
                    success=False,
                    outcome=f"header_{banner}",
                    error=f"Account {banner}",
                    duration_ms=int((time.time() - started) * 1000),
                )

            ref = self.find_target_ref(snapshot)
            if not ref:
                return ActionResult(
                    success=False,
                    outcome="failed",
                    error=f"Target element not found for {self.action_type}",
                    duration_ms=int((time.time() - started) * 1000),
                )

            self.camofox.click(tab, ref)
            self.camofox.wait(tab, timeout=get_settings().post_click_wait_ms)

            after_snapshot, _ = self.camofox.snapshot_quick(tab)
            verify_ok, verify_error = self.verify_success(after_snapshot)

            if verify_ok:
                return ActionResult(
                    success=True,
                    outcome="success",
                    clicked_ref=ref,
                    duration_ms=int((time.time() - started) * 1000),
                )

            popup = self.detect_popup(after_snapshot)
            if popup:
                return ActionResult(
                    success=False,
                    outcome=verify_error or f"popup_{popup}",
                    error=verify_error or popup,
                    duration_ms=int((time.time() - started) * 1000),
                )

            return ActionResult(
                success=False,
                outcome="failed",
                error=verify_error or "Verification failed",
                clicked_ref=ref,
                duration_ms=int((time.time() - started) * 1000),
            )

        except Exception as e:
            return ActionResult(
                success=False,
                outcome="failed",
                error=str(e),
                duration_ms=int((time.time() - started) * 1000),
            )
        finally:
            if tab is not None:
                self.camofox.close_tab(tab)

    # ------------------------------------------------------------------
    # Methods subclasses override
    # ------------------------------------------------------------------

    def find_target_ref(self, snapshot: str) -> Optional[str]:
        """Find the element ref to click. Override in subclass."""
        if self.target_pattern:
            return self.find_ref_by_pattern(snapshot, self.target_pattern)
        return None

    def verify_success(self, snapshot: str) -> tuple[bool, Optional[str]]:
        """Verify the action succeeded. Override in subclass."""
        popup = self.detect_popup(snapshot)
        if popup:
            return False, popup
        return True, None


def dedup_hash(worker_id: int, action_type: str, target_url: str) -> str:
    raw = f"{worker_id}:{action_type}:{target_url}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]