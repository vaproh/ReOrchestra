from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import DeclarativeBase, sessionmaker, relationship
from datetime import datetime
import enum

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class AccountStatus(str, enum.Enum):
    fresh = "fresh"
    logged_in = "logged_in"
    session_expired = "session_expired"
    banned = "banned"
    dead = "dead"


class AccountType(str, enum.Enum):
    upvoter = "upvoter"
    main = "main"
    both = "both"


class PostStatus(str, enum.Enum):
    draft = "draft"
    posted = "posted"
    failed = "failed"
    deleted = "deleted"


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(20), unique=True, nullable=False)
    password = Column(String(128), nullable=False)
    email = Column(String(128), nullable=True)
    email_password = Column(String(128), nullable=True)
    email_verified = Column(Boolean, default=False)

    cookies = Column(Text, nullable=True)
    bearer_token = Column(String(512), nullable=True)
    user_agent = Column(String(256), nullable=True)
    proxy = Column(String(64), nullable=True)
    profile_id = Column(String(32), nullable=True)

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

    csrf_token = Column(String(128), nullable=True)
    session_valid = Column(Boolean, default=False)

    consecutive_failures = Column(Integer, default=0)
    last_failure_at = Column(DateTime, nullable=True)
    dead_reason = Column(String(64), nullable=True)

    last_used = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    fail_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    posts = relationship("Post", back_populates="account")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    account_username = Column(String(20), nullable=False)

    post_type = Column(String(16), nullable=False)
    target_type = Column(String(16), nullable=False)
    target = Column(String(128), nullable=False)
    title = Column(String(300), nullable=False)
    body = Column(Text, nullable=True)
    flair_id = Column(String(64), nullable=True)

    post_url = Column(String(512), nullable=True)
    post_id = Column(String(16), nullable=True)
    status = Column(SQLEnum(PostStatus), default=PostStatus.draft)

    karma_gained = Column(Integer, default=0)
    upvotes_received = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)

    scheduled_for = Column(DateTime, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="posts")


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
    country = Column(String(10), nullable=True)
    region = Column(String(50), nullable=True)

    assigned_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    session_id = Column(String(32), nullable=True)

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


class ActionLog(Base):
    __tablename__ = "action_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    target_id = Column(String(64), nullable=True)
    target_url = Column(Text, nullable=True)
    action_type = Column(String(20), nullable=False)
    action_value = Column(String(16), nullable=True)
    success = Column(Boolean, default=True)
    error = Column(Text, nullable=True)
    http_status = Column(Integer, nullable=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    dedup_hash = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Config(Base):
    __tablename__ = "config"

    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=False)
    source = Column(String(20), default="runtime")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# Worker Queue System Models
# ============================================================


class WorkerStatus(str, enum.Enum):
    idle = "idle"
    working = "working"
    paused = "paused"


class TaskStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    partial = "partial"
    failed = "failed"
    cancelled = "cancelled"
    dead_letter = "dead_letter"


class ActionOutcome(str, enum.Enum):
    success = "success"
    failed = "failed"
    duplicate = "duplicate"
    popup_suspended = "popup_suspended"
    popup_rate_limited = "popup_rate_limited"


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


class Worker(Base):
    __tablename__ = "queue_workers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    username = Column(String(20), nullable=False)

    status = Column(SQLEnum(WorkerStatus), default=WorkerStatus.idle)
    current_task_id = Column(Integer, nullable=True)

    total_actions = Column(Integer, default=0)
    failed_actions = Column(Integer, default=0)
    last_action_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    account = relationship("Account")


class Task(Base):
    __tablename__ = "queue_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action_type = Column(String(32), nullable=False)
    target_url = Column(Text, nullable=False)

    workers_needed = Column(Integer, nullable=False, default=1)
    workers_assigned = Column(Text, default="[]")          # JSON list of worker ids
    failed_workers = Column(Text, default="[]")             # JSON list of worker ids
    workers_completed = Column(Integer, default=0)

    status = Column(SQLEnum(TaskStatus), default=TaskStatus.queued)
    priority = Column(Integer, default=0)                  # higher = sooner

    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Dead Letter Queue fields
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    dlq_reason = Column(String(128), nullable=True)
    dlq_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    logs = relationship("TaskActionLog", back_populates="task", order_by="TaskActionLog.created_at")


class TaskActionLog(Base):
    __tablename__ = "queue_action_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("queue_tasks.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("queue_workers.id"), nullable=False)

    action_type = Column(String(32), nullable=False)
    target_url = Column(Text, nullable=False)

    success = Column(Boolean, default=False)
    outcome = Column(String(32), default=ActionOutcome.failed.value)
    error = Column(Text, nullable=True)
    attempts = Column(Integer, default=1)
    duration_ms = Column(Integer, nullable=True)

    dedup_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="logs")
    worker = relationship("Worker")


settings = get_settings()
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
