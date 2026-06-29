"""Test follow_user action."""
import time
import logging
import pytest

from app.models import TaskStatus, TaskActionLog

logger = logging.getLogger("tests.follow_user")


class TestFollowUser:
    """Tests for follow_user action."""

    def test_follow_success(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test successful follow."""
        target_url = f"{test_server}/user/test-follow"

        logger.info(f"[TEST] Starting test_follow_success")
        logger.info(f"[TEST] Account: {test_account.username}")
        logger.info(f"[TEST] Proxy: {test_account.proxy}")
        logger.info(f"[TEST] Target URL: {target_url}")

        task = queue_processor.create_task(
            action_type="follow_user",
            target_url=target_url,
            workers_needed=1,
        )

        queue_processor.start()
        time.sleep(5)
        queue_processor.stop()

        db_session.expire_all()
        db_session.refresh(task)

        log = db_session.query(TaskActionLog).filter_by(task_id=task.id).first()

        if log:
            logger.info(f"[TEST] Log: success={log.success} outcome={log.outcome}")

        assert task.status == TaskStatus.completed
        assert log is not None
        assert log.success == True
        assert log.outcome == "success"

        logger.info(f"[TEST] ✅ PASSED: test_follow_success")

    def test_follow_scenario_banned(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test follow with banned scenario."""
        target_url = f"{test_server}/user/test-follow?scenario=banned"

        logger.info(f"[TEST] Starting test_follow_scenario_banned")
        logger.info(f"[TEST] Account: {test_account.username}")

        task = queue_processor.create_task(
            action_type="follow_user",
            target_url=target_url,
            workers_needed=1,
        )

        queue_processor.start()
        time.sleep(5)
        queue_processor.stop()

        db_session.expire_all()
        log = db_session.query(TaskActionLog).filter_by(task_id=task.id).first()

        assert log is not None
        assert log.outcome == "header_banned"

        logger.info(f"[TEST] ✅ PASSED: test_follow_scenario_banned")

    def test_follow_scenario_suspended(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test follow with suspended scenario."""
        target_url = f"{test_server}/user/test-follow?scenario=suspended"

        logger.info(f"[TEST] Starting test_follow_scenario_suspended")
        logger.info(f"[TEST] Account: {test_account.username}")

        task = queue_processor.create_task(
            action_type="follow_user",
            target_url=target_url,
            workers_needed=1,
        )

        queue_processor.start()
        time.sleep(5)
        queue_processor.stop()

        db_session.expire_all()
        log = db_session.query(TaskActionLog).filter_by(task_id=task.id).first()

        assert log is not None
        assert log.outcome == "header_suspended"

        logger.info(f"[TEST] ✅ PASSED: test_follow_scenario_suspended")
