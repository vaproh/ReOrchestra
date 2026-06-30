"""
Integration tests for upvote_post action using real Camofox + test server.
Tests simulate production: real browser, real queue, real DB.
"""
import time
import logging
import pytest
import requests

from app.config import get_settings
from app.models import TaskStatus, TaskActionLog
from app.services.browser import CamofoxClient
from app.services.queue_processor import QueueProcessor

logger = logging.getLogger("tests.upvote_post")


def is_camofox_running():
    """Check if Camofox is accessible and browser is connected."""
    try:
        resp = requests.get(f"http://localhost:{get_settings().camofox_port}/", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("browserConnected", False)
        return False
    except:
        return False


def is_server_running(url):
    """Check if test server is accessible."""
    try:
        resp = requests.get(url, timeout=2)
        return resp.status_code == 200
    except:
        return False


class TestUpvotePostIntegration:
    """Integration tests for upvote_post with real Camofox."""

    @pytest.fixture(scope="class", autouse=True)
    def check_services(self, test_server):
        """Skip tests if Camofox or test server not running."""
        settings = get_settings()
        if not is_camofox_running():
            pytest.skip(f"Camofox not running on port {settings.camofox_port}")
        if not is_server_running(test_server):
            pytest.skip(f"Test server not running at {test_server}")

    def test_upvote_success(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test successful upvote via real Camofox + test server."""
        target_url = f"{test_server}/post/test-upvote"

        logger.info(f"[TEST] Starting test_upvote_success")
        logger.info(f"[TEST] Account: {test_account.username} (id={test_account.id})")
        logger.info(f"[TEST] Worker: {test_worker.id} for account {test_worker.username}")
        logger.info(f"[TEST] Proxy: {test_account.proxy}")
        logger.info(f"[TEST] Target URL: {target_url}")

        task = queue_processor.create_task(
            action_type="upvote_post",
            target_url=target_url,
            workers_needed=1,
        )

        logger.info(f"[TEST] Task created: id={task.id} action={task.action_type}")
        logger.info(f"[TEST] Starting queue processor...")

        queue_processor.start()
        time.sleep(8)
        queue_processor.stop()

        db_session.expire_all()
        db_session.refresh(task)

        logger.info(f"[TEST] Task status: {task.status}")
        logger.info(f"[TEST] Workers completed: {task.workers_completed}")

        log = db_session.query(TaskActionLog).filter_by(task_id=task.id).first()

        if log:
            logger.info(f"[TEST] Log found: success={log.success} outcome={log.outcome}")
            logger.info(f"[TEST] Duration: {log.duration_ms}ms")
        else:
            logger.error(f"[TEST] No action log found for task_id={task.id}")

        assert task.status == TaskStatus.completed, f"Expected completed, got {task.status}"
        assert log is not None, "No action log found"
        assert log.success == True, f"Expected success=True, got {log.success}"
        assert log.outcome == "success", f"Expected outcome='success', got '{log.outcome}'"

        logger.info(f"[TEST] ✅ PASSED: test_upvote_success")

    def test_upvote_scenario_suspended(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test upvote with suspended scenario via real Camofox."""
        target_url = f"{test_server}/post/test-upvote?scenario=suspended"

        logger.info(f"[TEST] Starting test_upvote_scenario_suspended")
        logger.info(f"[TEST] Account: {test_account.username}")
        logger.info(f"[TEST] Proxy: {test_account.proxy}")
        logger.info(f"[TEST] Target URL: {target_url}")

        task = queue_processor.create_task(
            action_type="upvote_post",
            target_url=target_url,
            workers_needed=1,
        )

        logger.info(f"[TEST] Task created: id={task.id}")
        logger.info(f"[TEST] Starting queue processor...")

        queue_processor.start()
        time.sleep(8)
        queue_processor.stop()

        db_session.expire_all()
        log = db_session.query(TaskActionLog).filter_by(task_id=task.id).first()

        if log:
            logger.info(f"[TEST] Log: success={log.success} outcome={log.outcome}")
        else:
            logger.error(f"[TEST] No action log found for task_id={task.id}")

        assert log is not None, "No action log found"
        assert log.outcome == "popup_suspended", f"Expected outcome='popup_suspended', got '{log.outcome}'"

        logger.info(f"[TEST] ✅ PASSED: test_upvote_scenario_suspended")

    def test_upvote_scenario_locked(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test upvote with locked scenario via real Camofox."""
        target_url = f"{test_server}/post/test-upvote?scenario=locked"

        logger.info(f"[TEST] Starting test_upvote_scenario_locked")
        logger.info(f"[TEST] Account: {test_account.username}")
        logger.info(f"[TEST] Proxy: {test_account.proxy}")
        logger.info(f"[TEST] Target URL: {target_url}")

        task = queue_processor.create_task(
            action_type="upvote_post",
            target_url=target_url,
            workers_needed=1,
        )

        logger.info(f"[TEST] Task created: id={task.id}")
        logger.info(f"[TEST] Starting queue processor...")

        queue_processor.start()
        time.sleep(8)
        queue_processor.stop()

        db_session.expire_all()
        log = db_session.query(TaskActionLog).filter_by(task_id=task.id).first()

        if log:
            logger.info(f"[TEST] Log: success={log.success} outcome={log.outcome}")
        else:
            logger.error(f"[TEST] No action log found for task_id={task.id}")

        assert log is not None, "No action log found"
        assert log.outcome == "popup_account_locked", f"Expected outcome='popup_account_locked', got '{log.outcome}'"

        logger.info(f"[TEST] ✅ PASSED: test_upvote_scenario_locked")
