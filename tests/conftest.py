import os
import uuid
import subprocess
import time
import signal
import shutil
import pytest
import warnings
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.models import Base, Account, Worker, AccountStatus, WorkerStatus
from app.services.queue_processor import QueueProcessor

settings = get_settings()


def cleanup_test_sessions():
    """Clean up test sessions from Camofox data directory."""
    if not settings.is_test_mode:
        return
    
    camofox_data = os.path.join(settings.camofox_path, "data")
    if not os.path.exists(camofox_data):
        return
    
    # Clean sessions directory
    sessions_path = os.path.join(camofox_data, "sessions")
    if os.path.exists(sessions_path):
        for item in os.listdir(sessions_path):
            item_path = os.path.join(sessions_path, item)
            if os.path.isfile(item_path) and item.startswith("test_"):
                try:
                    os.remove(item_path)
                    print(f"Cleaned test session: {item}")
                except Exception as e:
                    print(f"Failed to clean {item}: {e}")
    
    # Clean user profiles for test accounts
    users_path = os.path.join(camofox_data, "users")
    if os.path.exists(users_path):
        for item in os.listdir(users_path):
            if item.startswith("s_test_") or "test" in item.lower():
                item_path = os.path.join(users_path, item)
                try:
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    print(f"Cleaned test user: {item}")
                except Exception as e:
                    print(f"Failed to clean {item}: {e}")


def cleanup_local_test_sessions():
    """Clean up local test session files."""
    test_session_dir = settings.test_session_dir
    if os.path.exists(test_session_dir):
        for item in os.listdir(test_session_dir):
            item_path = os.path.join(test_session_dir, item)
            try:
                if item.startswith("test_"):
                    os.remove(item_path)
                    print(f"Cleaned local session: {item}")
            except Exception as e:
                print(f"Failed to clean {item}: {e}")


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment before all tests."""
    print(f"\n{'='*60}")
    print(f"Test Mode: {settings.app_mode}")
    print(f"Test Server URL: {settings.test_server_url}")
    print(f"Test DB: {settings.test_db_url}")
    print(f"Camofox Path: {settings.camofox_path}")
    print(f"Tunnel Domain: {settings.tunnel_domain}")
    print(f"{'='*60}\n")
    
    # Create test directories
    os.makedirs(settings.test_session_dir, exist_ok=True)
    
    yield
    
    # Cleanup after all tests
    print("\nCleaning up test environment...")
    cleanup_test_sessions()
    cleanup_local_test_sessions()


@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine."""
    # Extract file path from SQLite URL
    db_path = settings.test_db_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    
    engine = create_engine(settings.test_db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_session(db_engine):
    """Create session-scoped DB session."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="session")
def test_proxy():
    """Get test proxy from settings or environment."""
    proxy = os.environ.get("TEST_PROXY", settings.test_proxy)
    if proxy == "http://test_proxy:8080":
        warnings.warn(
            "Using default test proxy. Set TEST_PROXY env var or TEST_PROXY in .env to override.",
            UserWarning
        )
    return proxy


@pytest.fixture
def test_account(db_session, test_proxy):
    """Create a test account with auto-generated username."""
    username = f"test_user_{uuid.uuid4().hex[:8]}"
    account = Account(
        username=username,
        password="test_password",
        proxy=test_proxy,
        status=AccountStatus.logged_in,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    yield account


@pytest.fixture
def test_worker(db_session, test_account):
    """Create a test worker from test account."""
    worker = Worker(
        account_id=test_account.id,
        username=test_account.username,
        status=WorkerStatus.idle,
    )
    db_session.add(worker)
    db_session.commit()
    db_session.refresh(worker)
    yield worker


@pytest.fixture(scope="session")
def queue_processor(db_session):
    """Create QueueProcessor instance."""
    processor = QueueProcessor(db_session)
    yield processor
    if processor.is_running():
        processor.stop()


@pytest.fixture(scope="session")
def test_server():
    """Start test server as subprocess."""
    port = settings.test_server_port or 8080
    
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
    
    # Determine URL based on settings
    if settings.test_server_url and settings.test_server_url != "http://localhost:8080":
        url = settings.test_server_url
    else:
        url = f"http://localhost:{port}"
    
    yield url
    
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="function")
def clean_test_worker(db_session):
    """Clean up workers before each test function."""
    # This runs before each test
    yield
    # Optionally clean up test workers after test
    # (Session-scoped DB means data persists between tests)
