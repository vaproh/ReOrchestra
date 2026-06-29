"""Test downvote_comment action."""
import time
import logging
import pytest

from app.models import TaskStatus, TaskActionLog

logger = logging.getLogger("tests.downvote_comment")


class TestDownvoteComment:
    """Tests for downvote_comment action."""

    def test_downvote_comment_success(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test successful downvote on comment."""
        target_url = f"{test_server}/comment/test-downvote"

        logger.info(f"[TEST] Starting test_downvote_comment_success")
        logger.info(f"[TEST] Account: {test_account.username}")
        logger.info(f"[TEST] Proxy: {test_account.proxy}")
        logger.info(f"[TEST] Target URL: {target_url}")

        task = queue_processor.create_task(
            action_type="downvote_comment",
            target_url=target_url,
            workers_needed=1,
        )

        queue_processor.start()
        time.sleep(5)
        queue_processor.stop()

        db_session.expire_all()
        db_session.refresh(task)

        log = db_session.query(TaskActionLog).filter_by(task_id=task.id).first()

        assert task.status == TaskStatus.completed
        assert log is not None
        assert log.success == True
        assert log.outcome == "success"

        logger.info(f"[TEST] ✅ PASSED: test_downvote_comment_success")

    def test_downvote_comment_scenario_suspended(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test downvote comment with suspended scenario."""
        target_url = f"{test_server}/comment/test-downvote?scenario=suspended"

        logger.info(f"[TEST] Starting test_downvote_comment_scenario_suspended")

        task = queue_processor.create_task(
            action_type="downvote_comment",
            target_url=target_url,
            workers_needed=1,
        )

        queue_processor.start()
        time.sleep(5)
        queue_processor.stop()

        db_session.expire_all()
        log = db_session.query(TaskActionLog).filter_by(task_id=task.id).first()

        assert log is not None
        assert log.outcome == "popup_suspended"

        logger.info(f"[TEST] ✅ PASSED: test_downvote_comment_scenario_suspended")

    def test_downvote_comment_scenario_locked(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test downvote comment with locked scenario."""
        target_url = f"{test_server}/comment/test-downvote?scenario=locked"

        logger.info(f"[TEST] Starting test_downvote_comment_scenario_locked")

        task = queue_processor.create_task(
            action_type="downvote_comment",
            target_url=target_url,
            workers_needed=1,
        )

        queue_processor.start()
        time.sleep(5)
        queue_processor.stop()

        db_session.expire_all()
        log = db_session.query(TaskActionLog).filter_by(task_id=task.id).first()

        assert log is not None
        assert log.outcome == "popup_account_locked"

        logger.info(f"[TEST] ✅ PASSED: test_downvote_comment_scenario_locked")
