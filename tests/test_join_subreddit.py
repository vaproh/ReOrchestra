"""Test join_subreddit action."""
import time
import logging
import pytest

from app.models import TaskStatus, TaskActionLog

logger = logging.getLogger("tests.join_subreddit")


class TestJoinSubreddit:
    """Tests for join_subreddit action."""

    def test_join_success(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test successful join."""
        target_url = f"{test_server}/r/test-join"

        logger.info(f"[TEST] Starting test_join_success")
        logger.info(f"[TEST] Account: {test_account.username}")
        logger.info(f"[TEST] Proxy: {test_account.proxy}")
        logger.info(f"[TEST] Target URL: {target_url}")

        task = queue_processor.create_task(
            action_type="join_subreddit",
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

        logger.info(f"[TEST] ✅ PASSED: test_join_success")

    def test_join_scenario_banned(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test join with banned scenario."""
        target_url = f"{test_server}/r/test-join?scenario=banned"

        logger.info(f"[TEST] Starting test_join_scenario_banned")

        task = queue_processor.create_task(
            action_type="join_subreddit",
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

        logger.info(f"[TEST] ✅ PASSED: test_join_scenario_banned")

    def test_join_scenario_suspended(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test join with suspended scenario."""
        target_url = f"{test_server}/r/test-join?scenario=suspended"

        logger.info(f"[TEST] Starting test_join_scenario_suspended")

        task = queue_processor.create_task(
            action_type="join_subreddit",
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

        logger.info(f"[TEST] ✅ PASSED: test_join_scenario_suspended")
