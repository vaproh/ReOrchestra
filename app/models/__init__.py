from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    Enum as SQLEnum,
    ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker, relationship, validates
from datetime import datetime
import enum

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class AccountStatus(str, enum.Enum):
    fresh = "fresh"
    logged_in = "logged_in"
    session_expired = "session_expired"
    rate_limited = "rate_limited"
    banned = "banned"
    dead = "dead"


class AccountType(str, enum.Enum):
    upvoter = "upvoter"
    main = "main"
    both = "both"


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(20), unique=True, nullable=False)
    password = Column(String(128), nullable=False)
    email = Column(String(128), nullable=True)
    proxy = Column(String(64), nullable=True)

    status = Column(SQLEnum(AccountStatus), default=AccountStatus.fresh)
    account_type = Column(SQLEnum(AccountType), default=AccountType.upvoter)

    karma_total = Column(Integer, default=0)
    karma_post = Column(Integer, default=0)
    karma_comment = Column(Integer, default=0)

    votes_today = Column(Integer, default=0)
    votes_this_week = Column(Integer, default=0)
    total_votes = Column(Integer, default=0)
    last_vote_at = Column(DateTime, nullable=True)

    active_hours_start = Column(Integer, default=7)
    active_hours_end = Column(Integer, default=23)

    dead_reason = Column(String(64), nullable=True)

    last_used = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    fail_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Proxy(Base):
    __tablename__ = "proxies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proxy_string = Column(String(256), unique=True, nullable=False)

    proxy_type = Column(String(20), default="bulk")

    host = Column(String(128), nullable=True)
    port = Column(Integer, nullable=True)
    username = Column(String(128), nullable=True)
    password = Column(String(128), nullable=True)

    provider = Column(String(50), nullable=True)

    assigned_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)

    status = Column(String(20), default="active")
    is_active = Column(Boolean, default=True)
    fail_count = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)


class CamofoxSlot(Base):
    __tablename__ = "camofox_slots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    port = Column(Integer, unique=True, nullable=False)
    status = Column(String(20), default="stopped")
    max_concurrent = Column(Integer, default=10)
    current_load = Column(Integer, default=0)

    process_id = Column(Integer, nullable=True)
    started_at = Column(DateTime, nullable=True)
    last_health_check = Column(DateTime, nullable=True)

    memory_mb = Column(Integer, nullable=True)
    cpu_percent = Column(Integer, nullable=True)


# ============================================================
# Queue System Models (task-based, accounts are the workers)
# ============================================================


class TaskStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    partial = "partial"
    failed = "failed"
    cancelled = "cancelled"


# Supported Reddit action types
ACTION_TYPES = [
    "upvote_post",
    "downvote_post",
    "upvote_comment",
    "downvote_comment",
    "follow_user",
    "unfollow_user",
    "join_subreddit",
    "leave_subreddit",
    "save_post",
]


class Task(Base):
    __tablename__ = "queue_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action_type = Column(String(32), nullable=False)
    target_url = Column(Text, nullable=False)

    workers_needed = Column(Integer, nullable=False, default=1)

    @validates("workers_needed")
    def validate_workers_needed(self, key, value):
        if value < 1:
            raise ValueError("workers_needed must be at least 1")
        return value

    workers_completed = Column(Integer, default=0)  # successful executions
    workers_failed = Column(Integer, default=0)  # failed/replaced executions

    status = Column(SQLEnum(TaskStatus), default=TaskStatus.queued)
    priority = Column(Integer, default=0)  # higher = sooner

    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    logs = relationship(
        "TaskExecutionLog",
        back_populates="task",
        order_by="TaskExecutionLog.created_at",
    )

    @validates("workers_needed")
    def validate_workers_needed(self, key, value):
        if value < 1:
            raise ValueError("workers_needed must be a positive integer")
        return value


class TaskExecutionLog(Base):
    """Per-account execution record for a task.

    Replaces the old TaskActionLog/Worker-based model.
    Deduplication key: account_id + action_type + target_url.
    """

    __tablename__ = "queue_execution_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("queue_tasks.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)

    action_type = Column(String(32), nullable=False)
    target_url = Column(Text, nullable=False)

    success = Column(Boolean, default=False)
    # outcome codes: success | popup_suspended | popup_rate_limited |
    #                header_banned | header_suspended | click_timeout |
    #                element_not_found | failed | cancelled
    outcome = Column(String(32), nullable=False, default="failed")
    error = Column(Text, nullable=True)
    attempts = Column(Integer, default=1)
    duration_ms = Column(Integer, nullable=True)

    # SHA-256[:16] of "{account_id}:{action_type}:{target_url}"
    # Unique constraint prevents the same account from succeeding the same
    # action on the same target twice.
    dedup_hash = Column(String(64), nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="logs")
    account = relationship("Account")


_settings = get_settings()
engine = create_engine(
    _settings.database_url,
    connect_args={"check_same_thread": False, "timeout": 30}
    if "sqlite" in _settings.database_url
    else {},
)

if "sqlite" in _settings.database_url:
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
