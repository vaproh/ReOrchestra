import pytest
from app.database import Base, init_db, Account, AccountStatus, AccountType


def test_database_tables():
    init_db()
    assert hasattr(Account, "__tablename__")
    assert Account.__tablename__ == "accounts"


def test_account_model_fields():
    assert hasattr(Account, "id")
    assert hasattr(Account, "username")
    assert hasattr(Account, "password")
    assert hasattr(Account, "email")
    assert hasattr(Account, "status")
    assert hasattr(Account, "account_type")
    assert hasattr(Account, "karma_total")
    assert hasattr(Account, "proxy")
    assert hasattr(Account, "profile_id")
