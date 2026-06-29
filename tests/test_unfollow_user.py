"""Test unfollow_user action."""
import pytest
import time
from app.models import TaskStatus, TaskActionLog

class TestUnfollowUser:
    def test_unfollow_success(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test successful unfollow on test server."""
        task = queue_processor.create_task(
            action_type="unfollow_user",
            target_url=f"{test_server}/user/test-unfollow",
            workers_needed=1,
        )
        queue_processor.start()
        time.sleep(5)
        queue_processor.stop()
        
        db_session.expire_all()
        db_session.refresh(task)
        
        assert task.status == TaskStatus.completed
        log = db_session.query(TaskActionLog).filter_by(task_id=task.id).first()
        assert log is not None
        assert log.success == True
        assert log.outcome == "success"
    
    def test_unfollow_scenario_suspended(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test unfollow with suspended scenario."""
        task = queue_processor.create_task(
            action_type="unfollow_user",
            target_url=f"{test_server}/user/test-unfollow?scenario=suspended",
            workers_needed=1,
        )
        queue_processor.start()
        time.sleep(5)
        queue_processor.stop()
        
        db_session.expire_all()
        log = db_session.query(TaskActionLog).filter_by(task_id=task.id).first()
        assert log is not None
        assert log.outcome == "header_suspended"
    
    def test_unfollow_scenario_locked(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test unfollow with locked scenario."""
        task = queue_processor.create_task(
            action_type="unfollow_user",
            target_url=f"{test_server}/user/test-unfollow?scenario=locked",
            workers_needed=1,
        )
        queue_processor.start()
        time.sleep(5)
        queue_processor.stop()
        
        db_session.expire_all()
        log = db_session.query(TaskActionLog).filter_by(task_id=task.id).first()
        assert log is not None
        assert log.outcome == "header_banned"
