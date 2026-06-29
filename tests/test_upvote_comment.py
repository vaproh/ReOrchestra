"""Test upvote_comment action."""
import time
import logging
import pytest

from app.models import TaskStatus, TaskActionLog

logger = logging.getLogger("tests.upvote_comment")


class TestUpvoteComment:
    """Tests for upvote_comment action."""

    def test_upvote_comment_success(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test successful upvote on comment."""
        target_url = f"{test_server}/comment/test-upvote"

        logger.info(f"[TEST] Starting test_upvote_comment_success")
        logger.info(f"[TEST] Account: {test_account.username}")
        logger.info(f"[TEST] Proxy: {test_account.proxy}")
        logger.info(f"[TEST] Target URL: {target_url}")

        task = queue_processor.create_task(
            action_type="upvote_comment",
            target_url=target_url,
            workers_needed=1,
        )

        logger.info(f"[TEST] Task created: id={task.id}")

        queue_processor.start()
        time.sleep(5)
        queue_processor.stop()

        db_session.expire_all()
        db_session.refresh(task)

        log = db_session.query(TaskActionLog).filter_by(task_id=task.id).first()

        if log:
            logger.info(f"[TEST] Log: success={log.success} outcome={log.outcome}")
        else:
            logger.error(f"[TEST] No action log found")

        assert task.status == TaskStatus.completed
        assert log is not None
        assert log.success == True
        assert log.outcome == "success"

        logger.info(f"[TEST] ✅ PASSED: test_upvote_comment_success")

    def test_upvote_comment_scenario_suspended(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test upvote comment with suspended scenario."""
        target_url = f"{test_server}/comment/test-upvote?scenario=suspended"

        logger.info(f"[TEST] Starting test_upvote_comment_scenario_suspended")
        logger.info(f"[TEST] Account: {test_account.username}")

        task = queue_processor.create_task(
            action_type="upvote_comment",
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

        logger.info(f"[TEST] ✅ PASSED: test_upvote_comment_scenario_suspended")

    def test_upvote_comment_scenario_locked(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test upvote comment with locked scenario."""
        target_url = f"{test_server}/comment/test-upvote?scenario=locked"

        logger.info(f"[TEST] Starting test_upvote_comment_scenario_locked")
        logger.info(f"[TEST] Account: {test_account.username}")

        task = queue_processor.create_task(
            action_type="upvote_comment",
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

        logger.info(f"[TEST] ✅ PASSED: test_upvote_comment_scenario_locked")
