"""Unit tests for deduplication logic."""
import pytest
from app.services.queue_actions import dedup_hash


class TestDeduplication:
    """Tests for deduplication hash function."""

    def test_dedup_hash_consistent(self):
        """Test that same inputs produce same hash."""
        hash1 = dedup_hash(1, 'upvote_post', 'https://reddit.com/r/test/123')
        hash2 = dedup_hash(1, 'upvote_post', 'https://reddit.com/r/test/123')
        assert hash1 == hash2

    def test_dedup_hash_different_worker(self):
        """Test that different worker IDs produce different hashes."""
        hash1 = dedup_hash(1, 'upvote_post', 'https://reddit.com/r/test/123')
        hash2 = dedup_hash(2, 'upvote_post', 'https://reddit.com/r/test/123')
        assert hash1 != hash2

    def test_dedup_hash_different_action(self):
        """Test that different action types produce different hashes."""
        hash1 = dedup_hash(1, 'upvote_post', 'https://reddit.com/r/test/123')
        hash2 = dedup_hash(1, 'downvote_post', 'https://reddit.com/r/test/123')
        assert hash1 != hash2

    def test_dedup_hash_different_target(self):
        """Test that different target URLs produce different hashes."""
        hash1 = dedup_hash(1, 'upvote_post', 'https://reddit.com/r/test/123')
        hash2 = dedup_hash(1, 'upvote_post', 'https://reddit.com/r/test/456')
        assert hash1 != hash2

    def test_dedup_hash_format(self):
        """Test that hash is a hex string of expected length."""
        hash_value = dedup_hash(1, 'upvote_post', 'https://reddit.com/r/test/123')
        assert isinstance(hash_value, str)
        assert len(hash_value) == 16  # Truncated to 16 hex characters
        assert all(c in '0123456789abcdef' for c in hash_value)

    def test_dedup_hash_with_special_chars(self):
        """Test that hash works with special characters in URL."""
        hash1 = dedup_hash(1, 'upvote_post', 'https://reddit.com/r/test/123?param=value&other=123')
        hash2 = dedup_hash(1, 'upvote_post', 'https://reddit.com/r/test/123?param=value&other=123')
        assert hash1 == hash2

    def test_dedup_hash_with_unicode(self):
        """Test that hash works with unicode characters."""
        hash1 = dedup_hash(1, 'upvote_post', 'https://reddit.com/r/测试/123')
        hash2 = dedup_hash(1, 'upvote_post', 'https://reddit.com/r/测试/123')
        assert hash1 == hash2

    def test_dedup_hash_order_matters(self):
        """Test that parameter order affects hash."""
        hash1 = dedup_hash(1, 'upvote_post', 'https://reddit.com/r/test/123')
        hash2 = dedup_hash(1, 'https://reddit.com/r/test/123', 'upvote_post')
        assert hash1 != hash2

    def test_dedup_hash_empty_string(self):
        """Test that hash works with empty strings."""
        hash1 = dedup_hash(1, '', '')
        hash2 = dedup_hash(1, '', '')
        assert hash1 == hash2

    def test_dedup_hash_large_worker_id(self):
        """Test that hash works with large worker IDs."""
        hash1 = dedup_hash(999999, 'upvote_post', 'https://reddit.com/r/test/123')
        hash2 = dedup_hash(999999, 'upvote_post', 'https://reddit.com/r/test/123')
        assert hash1 == hash2
