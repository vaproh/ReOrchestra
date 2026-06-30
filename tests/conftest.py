import os
import sys
import uuid
import time
import itertools
import logging
import subprocess
import signal
import shutil
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.models import Base, Account, Worker, AccountStatus, WorkerStatus
from app.services.queue_processor import QueueProcessor
from app.logging_config import setup_logging

settings = get_settings()

setup_logging()
logger = logging.getLogger("tests")

test_log_dir = Path(__file__).parent.parent / "data" / "test_logs"
test_log_dir.mkdir(parents=True, exist_ok=True)
test_log_file = test_log_dir / f"test_{int(time.time())}.log"
logger.info(f"Test logs will also be saved to {test_log_file}")


def load_proxies():
    """Load proxies from proxy file."""
    proxy_file = settings.proxy_file
    if not os.path.exists(proxy_file):
        raise RuntimeError(f"Proxy file not found: {proxy_file}")
    with open(proxy_file, "r") as f:
        proxies = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    if len(proxies) < 27:
        raise RuntimeError(
            f"Need at least 27 proxies for full test isolation, found {len(proxies)}. "
            f"Add more proxies to {proxy_file}"
        )
    logger.info(f"Loaded {len(proxies)} proxies from {proxy_file}")
    return proxies


# Proxy allocation: one fresh proxy per test (not cycled)
_proxy_pool = None
_proxy_index = 0


def get_next_proxy():
    """Get next proxy from pool (fresh proxy per test for full isolation)."""
    global _proxy_pool, _proxy_index
    if _proxy_pool is None:
        _proxy_pool = load_proxies()
        _proxy_index = 0
    proxy = _proxy_pool[_proxy_index]
    _proxy_index += 1
    logger.debug(f"Allocating proxy: {proxy} (index={_proxy_index}/{len(_proxy_pool)})")
    return proxy


def reset_proxy_index():
    """Reset proxy index for fresh allocation."""
    global _proxy_index
    _proxy_index = 0


# =============================================================================
# Session Cleanup
# =============================================================================

def cleanup_test_sessions():
    """Clean up test sessions from Camofox data directory."""
    logger.info("Cleaning up test sessions from Camofox data directory...")

    camofox_data = os.path.join(settings.camofox_path, "data")
    if not os.path.exists(camofox_data):
        logger.warning(f"Camofox data directory not found: {camofox_data}")
        return

    cleaned = 0

    # Clean sessions directory
    sessions_path = os.path.join(camofox_data, "sessions")
    if os.path.exists(sessions_path):
        for item in os.listdir(sessions_path):
            if item.startswith("test_") or "wq_" in item:
                item_path = os.path.join(sessions_path, item)
                try:
                    os.remove(item_path)
                    cleaned += 1
                    logger.debug(f"Removed session: {item}")
                except Exception as e:
                    logger.error(f"Failed to remove {item}: {e}")

    # Clean user profiles
    users_path = os.path.join(camofox_data, "users")
    if os.path.exists(users_path):
        for item in os.listdir(users_path):
            if "test" in item.lower() or item.startswith("s_test_"):
                item_path = os.path.join(users_path, item)
                try:
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    cleaned += 1
                    logger.debug(f"Removed user: {item}")
                except Exception as e:
                    logger.error(f"Failed to remove {item}: {e}")

    logger.info(f"Cleaned up {cleaned} test sessions/users")


def cleanup_local_test_sessions():
    """Clean up local test session files."""
    test_session_dir = settings.test_session_dir
    if os.path.exists(test_session_dir):
        for item in os.listdir(test_session_dir):
            item_path = os.path.join(test_session_dir, item)
            try:
                if item.startswith("test_"):
                    os.remove(item_path)
                    logger.debug(f"Removed local session: {item}")
            except Exception as e:
                logger.error(f"Failed to remove {item}: {e}")


# =============================================================================
# Pytest Fixtures
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment before all tests."""
    logger.info("=" * 60)
    logger.info("TEST MODE ENVIRONMENT")
    logger.info("=" * 60)
    logger.info(f"App Mode: {settings.app_mode}")
    logger.info(f"Test Server URL: {settings.test_server_url}")
    logger.info(f"Test DB: {settings.test_db_url}")
    logger.info(f"Camofox Path: {settings.camofox_path}")
    logger.info(f"Proxy File: {settings.proxy_file}")
    logger.info(f"Tunnel Domain: {settings.tunnel_domain}")
    logger.info("=" * 60)

    # Create test directories
    os.makedirs(settings.test_session_dir, exist_ok=True)

    # Reset proxy index for fresh allocation
    reset_proxy_index()

    yield

    # Cleanup after all tests
    logger.info("=" * 60)
    logger.info("CLEANUP AFTER TESTS")
    logger.info("=" * 60)
    cleanup_test_sessions()
    cleanup_local_test_sessions()
    logger.info("Cleanup complete")


@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine."""
    db_path = settings.test_db_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    engine = create_engine(settings.test_db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    logger.info(f"Test DB created: {settings.test_db_url}")
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_session(db_engine):
    """Create session-scoped DB session."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    logger.debug("DB session created")
    yield session
    session.close()
    logger.debug("DB session closed")


@pytest.fixture(scope="function")
def test_account(db_session):
    """Create a test account with fresh proxy (1:1 allocation)."""
    proxy = get_next_proxy()
    username = f"test_{uuid.uuid4().hex[:8]}"

    logger.info(f"Creating test account: {username} with proxy: {proxy}")

    account = Account(
        username=username,
        password="test_password",
        proxy=proxy,
        status=AccountStatus.logged_in,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)

    logger.info(f"Created account id={account.id} username={username} proxy={proxy}")

    yield account


@pytest.fixture(scope="function")
def test_worker(db_session, test_account):
    """Create a test worker from test account."""
    logger.info(f"Creating worker for account: {test_account.username} (id={test_account.id})")

    worker = Worker(
        account_id=test_account.id,
        username=test_account.username,
        status=WorkerStatus.idle,
    )
    db_session.add(worker)
    db_session.commit()
    db_session.refresh(worker)

    logger.info(f"Created worker id={worker.id} for account={test_account.username}")

    yield worker


@pytest.fixture(scope="session")
def queue_processor(db_session):
    """Create QueueProcessor instance."""
    processor = QueueProcessor(db_session)
    logger.info("QueueProcessor created")
    yield processor
    if processor.is_running():
        processor.stop()
    logger.info("QueueProcessor stopped")


@pytest.fixture(scope="session")
def test_server():
    """Start test server as subprocess."""
    port = settings.test_server_port or 8080

    logger.info(f"Starting test server on port {port}...")

    proc = subprocess.Popen(
        [
            "uvicorn",
            "tests.server:app",
            "--host", "0.0.0.0",
            "--port", str(port),
        ],
        cwd=str(Path(__file__).parent.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2)

    if settings.test_server_url and settings.test_server_url != "http://localhost:8080":
        url = settings.test_server_url
    else:
        url = f"http://localhost:{port}"

    logger.info(f"Test server started: {url}")
    yield url

    logger.info("Stopping test server...")
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    logger.info("Test server stopped")
