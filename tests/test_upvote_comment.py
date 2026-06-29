"""Test upvote_comment action."""
import pytest
import time
from app.models import TaskStatus, TaskActionLog

class TestUpvoteComment:
    def test_upvote_success(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test successful upvote on test server."""
        task = queue_processor.create_task(
            action_type="upvote_comment",
            target_url=f"{test_server}/comment/test-upvote",
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
    
    def test_upvote_scenario_suspended(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test upvote with suspended scenario."""
        task = queue_processor.create_task(
            action_type="upvote_comment",
            target_url=f"{test_server}/comment/test-upvote?scenario=suspended",
            workers_needed=1,
        )
        queue_processor.start()
        time.sleep(5)
        queue_processor.stop()
        
        db_session.expire_all()
        log = db_session.query(TaskActionLog).filter_by(task_id=task.id).first()
        assert log is not None
        assert log.outcome == "popup_suspended"
    
    def test_upvote_scenario_locked(self, test_server, db_session, test_account, test_worker, queue_processor):
        """Test upvote with locked scenario."""
        task = queue_processor.create_task(
            action_type="upvote_comment",
            target_url=f"{test_server}/comment/test-upvote?scenario=locked",
            workers_needed=1,
        )
        queue_processor.start()
        time.sleep(5)
        queue_processor.stop()
        
        db_session.expire_all()
        log = db_session.query(TaskActionLog).filter_by(task_id=task.id).first()
        assert log is not None
        assert log.outcome == "popup_account_locked"
