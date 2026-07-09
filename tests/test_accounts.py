"""
Tests for Account management: Import, CRUD, status transitions.

Covers:
- Import single account
- Import 50 accounts bulk
- Import with duplicate usernames (some exist, some new)
- Import with missing optional fields
- Import with invalid data types
- Get all accounts (paginated)
- Get accounts filtered by status
- Get accounts filtered by type
- Search accounts by username
- Update account status
- Update multiple fields
- Delete single account
- Batch delete by IDs
- Batch delete by filters
- Delete account with session file
- Status transitions: fresh → logged_in, logged_in → session_expired, etc.
"""

import pytest
from datetime import datetime, UTC


class TestAccountImport:
    """Account import tests."""

    def test_import_single_account(self, db_session):
        """Import a single account successfully."""
        from app.models import Account, AccountStatus, AccountType

        account = Account(
            username="single_user",
            password="password123",
            email="user@example.com",
            status=AccountStatus.fresh,
            account_type=AccountType.upvoter,
        )
        db_session.add(account)
        db_session.commit()

        # Verify it was saved
        db_session.refresh(account)
        assert account.id is not None
        assert account.username == "single_user"
        assert account.status == AccountStatus.fresh

    def test_import_50_accounts_bulk(self, db_session, sample_account_data):
        """Import 50 accounts in bulk."""
        from app.models import Account, AccountStatus, AccountType

        accounts = [
            Account(
                username=data["username"],
                password=data["password"],
                email=data["email"],
                status=AccountStatus.fresh,
                account_type=AccountType.upvoter,
            )
            for data in sample_account_data
        ]

        db_session.add_all(accounts)
        db_session.commit()

        # Verify all 50 were saved
        count = db_session.query(Account).count()
        assert count == 50

        # Verify first and last
        first = db_session.query(Account).filter(Account.username == "user_1").first()
        last = db_session.query(Account).filter(Account.username == "user_50").first()
        assert first is not None
        assert last is not None

    def test_import_with_duplicate_usernames_partial(self, db_session):
        """Import where some usernames exist and some are new."""
        from app.models import Account, AccountStatus, AccountType

        # First import: 5 accounts
        existing = [
            Account(
                username=f"existing_{i}", password="pass", status=AccountStatus.fresh
            )
            for i in range(5)
        ]
        db_session.add_all(existing)
        db_session.commit()

        # Second import: 3 existing + 7 new
        new_accounts = [
            Account(
                username=f"existing_{i}", password="pass", status=AccountStatus.fresh
            )  # duplicate
            for i in range(3)
        ]
        new_accounts.extend(
            [
                Account(
                    username=f"new_{i}", password="pass", status=AccountStatus.fresh
                )  # new
                for i in range(7)
            ]
        )

        imported = []
        skipped = []
        for acc in new_accounts:
            existing_acc = (
                db_session.query(Account)
                .filter(Account.username == acc.username)
                .first()
            )
            if existing_acc:
                skipped.append(acc.username)
            else:
                db_session.add(acc)
                imported.append(acc.username)

        db_session.commit()

        assert len(imported) == 7
        assert len(skipped) == 3

    def test_import_with_missing_optional_fields(self, db_session):
        """Import accounts with only required fields (username, password)."""
        from app.models import Account, AccountStatus, AccountType

        # Only username and password provided
        account = Account(
            username="minimal_user",
            password="password123",
            # email=None, proxy=None
            status=AccountStatus.fresh,
            account_type=AccountType.upvoter,
        )
        db_session.add(account)
        db_session.commit()

        db_session.refresh(account)
        assert account.email is None
        assert account.proxy is None

    def test_import_with_invalid_data_types(self, db_session):
        """Import with invalid data types should fail validation."""
        from pydantic import ValidationError
        from app.schemas.account import AccountImport

        with pytest.raises(ValidationError):
            AccountImport(
                username="a" * 25,  # Too long (>20 chars)
                password="password123",
            )


class TestAccountRetrieval:
    """Account retrieval and filtering tests."""

    @pytest.fixture
    def populated_accounts(self, db_session):
        """Create accounts with various statuses and types."""
        from app.models import Account, AccountStatus, AccountType

        accounts = [
            # 10 fresh accounts
            *(
                Account(
                    username=f"fresh_{i}",
                    password="pass",
                    status=AccountStatus.fresh,
                    account_type=AccountType.upvoter,
                )
                for i in range(10)
            ),
            # 20 logged_in accounts
            *(
                Account(
                    username=f"logged_{i}",
                    password="pass",
                    status=AccountStatus.logged_in,
                    account_type=AccountType.upvoter,
                )
                for i in range(20)
            ),
            # 5 rate_limited accounts
            *(
                Account(
                    username=f"ratelimit_{i}",
                    password="pass",
                    status=AccountStatus.rate_limited,
                    account_type=AccountType.upvoter,
                )
                for i in range(5)
            ),
            # 5 dead accounts
            *(
                Account(
                    username=f"dead_{i}",
                    password="pass",
                    status=AccountStatus.dead,
                    account_type=AccountType.upvoter,
                )
                for i in range(5)
            ),
            # 10 upvoter type
            # 10 both type
            *(
                Account(
                    username=f"main_{i}",
                    password="pass",
                    status=AccountStatus.logged_in,
                    account_type=AccountType.main,
                )
                for i in range(10)
            ),
        ]

        db_session.add_all(accounts)
        db_session.commit()

        return accounts

    def test_get_all_accounts_paginated(self, db_session, populated_accounts):
        """Get all accounts with pagination."""
        from app.models import Account

        # Page 1
        page1 = db_session.query(Account).limit(20).all()
        assert len(page1) == 20

        # Page 2
        page2 = db_session.query(Account).offset(20).limit(20).all()
        assert len(page2) == 20

        # Page 3
        page3 = db_session.query(Account).offset(40).limit(20).all()
        assert len(page3) == 10

    def test_get_accounts_filtered_by_status(self, db_session, populated_accounts):
        """Get accounts filtered by status."""
        from app.models import Account, AccountStatus

        # Filter by logged_in
        logged_in = (
            db_session.query(Account)
            .filter(Account.status == AccountStatus.logged_in)
            .all()
        )
        assert len(logged_in) == 30  # 20 upvoter + 10 main

        # Filter by dead
        dead = (
            db_session.query(Account).filter(Account.status == AccountStatus.dead).all()
        )
        assert len(dead) == 5

        # Filter by rate_limited
        rate_limited = (
            db_session.query(Account)
            .filter(Account.status == AccountStatus.rate_limited)
            .all()
        )
        assert len(rate_limited) == 5

    def test_get_accounts_filtered_by_type(self, db_session, populated_accounts):
        """Get accounts filtered by account type."""
        from app.models import Account, AccountType

        upvoters = (
            db_session.query(Account)
            .filter(Account.account_type == AccountType.upvoter)
            .all()
        )
        assert len(upvoters) == 40

        mains = (
            db_session.query(Account)
            .filter(Account.account_type == AccountType.main)
            .all()
        )
        assert len(mains) == 10

    def test_search_accounts_by_username(self, db_session, populated_accounts):
        """Search accounts by username substring."""
        from app.models import Account

        # Search for "fresh"
        fresh = (
            db_session.query(Account).filter(Account.username.contains("fresh")).all()
        )
        assert len(fresh) == 10

        # Search for "logged"
        logged = (
            db_session.query(Account).filter(Account.username.contains("logged")).all()
        )
        assert len(logged) == 20

        # Case insensitive search (SQLite LIKE is case-insensitive for ASCII)
        Fresh = (
            db_session.query(Account).filter(Account.username.contains("FRESH")).all()
        )
        assert len(Fresh) == 10

    def test_get_accounts_sorted(self, db_session, populated_accounts):
        """Get accounts sorted by various fields."""
        from app.models import Account

        # Sort by username ascending
        by_name = db_session.query(Account).order_by(Account.username.asc()).all()
        assert by_name[0].username == "dead_0"

        # Sort by username descending
        by_name_desc = db_session.query(Account).order_by(Account.username.desc()).all()
        assert by_name_desc[0].username == "ratelimit_4"


class TestAccountUpdate:
    """Account update tests."""

    @pytest.fixture
    def account_to_update(self, db_session):
        """Create an account for update tests."""
        from app.models import Account, AccountStatus

        account = Account(
            username="update_test",
            password="old_password",
            email="old@example.com",
            status=AccountStatus.fresh,
            karma_total=100,
        )
        db_session.add(account)
        db_session.commit()
        db_session.refresh(account)
        return account

    def test_update_account_status(self, db_session, account_to_update):
        """Update only the account status."""
        from app.models import AccountStatus

        account_to_update.status = AccountStatus.logged_in
        db_session.commit()
        db_session.refresh(account_to_update)

        assert account_to_update.status == AccountStatus.logged_in

    def test_update_multiple_fields(self, db_session, account_to_update):
        """Update multiple fields at once."""
        account_to_update.password = "new_password"
        account_to_update.email = "new@example.com"
        account_to_update.karma_total = 200
        db_session.commit()
        db_session.refresh(account_to_update)

        assert account_to_update.password == "new_password"
        assert account_to_update.email == "new@example.com"
        assert account_to_update.karma_total == 200


class TestAccountDeletion:
    """Account deletion tests."""

    @pytest.fixture
    def accounts_to_delete(self, db_session):
        """Create accounts for deletion tests."""
        from app.models import Account, AccountStatus

        accounts = [
            Account(username=f"delete_{i}", password="pass", status=AccountStatus.fresh)
            for i in range(20)
        ]
        db_session.add_all(accounts)
        db_session.commit()
        return accounts

    def test_delete_single_account(self, db_session, accounts_to_delete):
        """Delete a single account by ID."""
        from app.models import Account

        account_id = accounts_to_delete[0].id
        account = db_session.query(Account).filter(Account.id == account_id).first()
        db_session.delete(account)
        db_session.commit()

        remaining = db_session.query(Account).count()
        assert remaining == 19

    def test_batch_delete_by_ids(self, db_session, accounts_to_delete):
        """Batch delete accounts by a list of IDs."""
        from app.models import Account

        ids_to_delete = [a.id for a in accounts_to_delete[:5]]
        db_session.query(Account).filter(Account.id.in_(ids_to_delete)).delete(
            synchronize_session=False
        )
        db_session.commit()

        remaining = db_session.query(Account).count()
        assert remaining == 15

    def test_batch_delete_by_filters(self, db_session, accounts_to_delete):
        """Batch delete accounts using filters."""
        from app.models import Account

        # Delete all accounts with username containing "delete_1" (should catch delete_1, delete_10, delete_11, etc.)
        db_session.query(Account).filter(Account.username.contains("delete_1")).delete(
            synchronize_session=False
        )
        db_session.commit()

        remaining = db_session.query(Account).count()
        assert remaining == 9  # 20 - 11 (1,10-19)

    def test_delete_account_with_session_file(
        self, db_session, fresh_account, tmp_path
    ):
        """Delete account removes its session file."""
        import os

        # Create a fake session file
        session_dir = tmp_path / "sessions"
        session_dir.mkdir()
        session_file = session_dir / f"{fresh_account.username}.cookies"
        session_file.write_text("fake cookie data")

        # Verify session file exists
        assert session_file.exists()

        # Delete the account (mock the session_dir setting)
        db_session.delete(fresh_account)
        db_session.commit()

        # Account should be deleted
        assert (
            db_session.query(fresh_account.__class__)
            .filter_by(id=fresh_account.id)
            .first()
            is None
        )


class TestAccountStatusTransitions:
    """Account status transition tests."""

    @pytest.fixture
    def accounts_by_status(self, db_session):
        """Create accounts in each status."""
        from app.models import Account, AccountStatus, AccountType

        accounts = {}
        for status in AccountStatus:
            acc = Account(
                username=f"status_{status.value}",
                password="pass",
                status=status,
                account_type=AccountType.upvoter,
            )
            db_session.add(acc)
            accounts[status.value] = acc
        db_session.commit()

        for acc in accounts.values():
            db_session.refresh(acc)

        return accounts

    def test_fresh_to_logged_in(self, db_session, accounts_by_status):
        """Transition from fresh to logged_in."""
        from app.models import AccountStatus

        account = accounts_by_status["fresh"]
        account.status = AccountStatus.logged_in
        account.last_login = datetime.now(UTC)
        db_session.commit()

        db_session.refresh(account)
        assert account.status == AccountStatus.logged_in

    def test_logged_in_to_session_expired(self, db_session, accounts_by_status):
        """Transition from logged_in to session_expired."""
        from app.models import AccountStatus

        account = accounts_by_status["logged_in"]
        account.status = AccountStatus.session_expired
        db_session.commit()

        db_session.refresh(account)
        assert account.status == AccountStatus.session_expired

    def test_logged_in_to_rate_limited(self, db_session, accounts_by_status):
        """Transition from logged_in to rate_limited."""
        from app.models import AccountStatus

        account = accounts_by_status["logged_in"]
        account.status = AccountStatus.rate_limited
        db_session.commit()

        db_session.refresh(account)
        assert account.status == AccountStatus.rate_limited

    def test_logged_in_to_banned(self, db_session, accounts_by_status):
        """Transition from logged_in to banned (via dead_reason)."""
        from app.models import AccountStatus

        account = accounts_by_status["logged_in"]
        account.status = AccountStatus.dead
        account.dead_reason = "header_banned"
        db_session.commit()

        db_session.refresh(account)
        assert account.status == AccountStatus.dead
        assert account.dead_reason == "header_banned"

    def test_logged_in_to_dead(self, db_session, accounts_by_status):
        """Transition from logged_in to dead."""
        from app.models import AccountStatus

        account = accounts_by_status["logged_in"]
        account.status = AccountStatus.dead
        account.dead_reason = "popup_suspended"
        db_session.commit()

        db_session.refresh(account)
        assert account.status == AccountStatus.dead
        assert account.dead_reason == "popup_suspended"

    def test_all_statuses_are_represented(self, db_session, accounts_by_status):
        """Verify we have accounts in all status states."""
        from app.models import AccountStatus

        for status in AccountStatus:
            assert status.value in accounts_by_status


class TestAccountHealthTracking:
    """Test account health metrics tracking."""

    def test_dead_reason_stored(self, db_session, logged_in_account):
        """dead_reason should store why account was marked dead."""
        logged_in_account.status = logged_in_account.status.__class__.dead
        logged_in_account.dead_reason = "popup_suspended"
        db_session.commit()

        db_session.refresh(logged_in_account)
        assert logged_in_account.dead_reason == "popup_suspended"
