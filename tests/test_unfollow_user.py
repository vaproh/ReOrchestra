"""Test unfollow_user action."""
import time
import logging
import pytest

from app.models import TaskStatus, TaskActionLog

logger = logging.getLogger("tests.unfollow_user")


class TestUnfollowUser:
    """Tests for unfollow_user action."""

    def test_unfollow_success(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test successful unfollow."""
        target_url = f"{test_server}/user/test-unfollow"

        logger.info(f"[TEST] Starting test_unfollow_success")
        logger.info(f"[TEST] Account: {test_account.username}")
        logger.info(f"[TEST] Proxy: {test_account.proxy}")
        logger.info(f"[TEST] Target URL: {target_url}")

        task = queue_processor.create_task(
            action_type="unfollow_user",
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

        logger.info(f"[TEST] ✅ PASSED: test_unfollow_success")

    def test_unfollow_scenario_banned(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test unfollow with banned scenario."""
        target_url = f"{test_server}/user/test-unfollow?scenario=banned"

        logger.info(f"[TEST] Starting test_unfollow_scenario_banned")

        task = queue_processor.create_task(
            action_type="unfollow_user",
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

        logger.info(f"[TEST] ✅ PASSED: test_unfollow_scenario_banned")

    def test_unfollow_scenario_suspended(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test unfollow with suspended scenario."""
        target_url = f"{test_server}/user/test-unfollow?scenario=suspended"

        logger.info(f"[TEST] Starting test_unfollow_scenario_suspended")

        task = queue_processor.create_task(
            action_type="unfollow_user",
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

        logger.info(f"[TEST] ✅ PASSED: test_unfollow_scenario_suspended")
