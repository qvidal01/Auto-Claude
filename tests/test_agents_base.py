"""
Tests for the agents base module
=================================

Tests covering agents/base.py - constants and configuration
"""

import pytest

from agents.base import (
    AUTO_CONTINUE_DELAY_SECONDS,
    HUMAN_INTERVENTION_FILE,
    MAX_CONCURRENCY_RETRIES,
    INITIAL_RETRY_DELAY_SECONDS,
    MAX_RETRY_DELAY_SECONDS,
)


# =============================================================================
# Constants Tests
# =============================================================================

class TestAgentsBaseConstants:
    """Tests for agents/base.py constants."""

    def test_auto_continue_delay_is_positive(self):
        """Test that auto continue delay is positive."""
        assert AUTO_CONTINUE_DELAY_SECONDS > 0

    def test_auto_continue_delay_reasonable(self):
        """Test that delay is reasonable (not too long or short)."""
        assert 1 <= AUTO_CONTINUE_DELAY_SECONDS <= 30

    def test_human_intervention_file_name(self):
        """Test human intervention file name."""
        assert HUMAN_INTERVENTION_FILE == "PAUSE"
        assert isinstance(HUMAN_INTERVENTION_FILE, str)

    def test_max_concurrency_retries_is_positive(self):
        """Test that max retries is positive."""
        assert MAX_CONCURRENCY_RETRIES > 0

    def test_max_concurrency_retries_reasonable(self):
        """Test that max retries is reasonable."""
        assert 1 <= MAX_CONCURRENCY_RETRIES <= 20

    def test_initial_retry_delay_is_positive(self):
        """Test that initial retry delay is positive."""
        assert INITIAL_RETRY_DELAY_SECONDS > 0

    def test_initial_retry_delay_reasonable(self):
        """Test that initial delay is reasonable."""
        assert INITIAL_RETRY_DELAY_SECONDS <= 10

    def test_max_retry_delay_is_positive(self):
        """Test that max retry delay is positive."""
        assert MAX_RETRY_DELAY_SECONDS > 0

    def test_max_retry_delay_greater_than_initial(self):
        """Test that max delay is greater than initial."""
        assert MAX_RETRY_DELAY_SECONDS >= INITIAL_RETRY_DELAY_SECONDS

    def test_retry_delays_allow_exponential_backoff(self):
        """Test that delays support exponential backoff."""
        # Calculate what delays would be
        delays = []
        delay = INITIAL_RETRY_DELAY_SECONDS
        for _ in range(MAX_CONCURRENCY_RETRIES):
            delays.append(min(delay, MAX_RETRY_DELAY_SECONDS))
            delay *= 2

        # All delays should be capped at max
        assert all(d <= MAX_RETRY_DELAY_SECONDS for d in delays)

        # Should reach the max delay cap
        assert delays[-1] == MAX_RETRY_DELAY_SECONDS


# =============================================================================
# Integration Tests
# =============================================================================

class TestAgentsBaseIntegration:
    """Integration tests for agents base constants."""

    def test_total_retry_time_reasonable(self):
        """Test that total retry time is reasonable."""
        # Calculate total time with exponential backoff
        total_time = 0
        delay = INITIAL_RETRY_DELAY_SECONDS
        for _ in range(MAX_CONCURRENCY_RETRIES):
            total_time += min(delay, MAX_RETRY_DELAY_SECONDS)
            delay *= 2

        # Total time should be reasonable (under 5 minutes)
        assert total_time < 300  # Less than 5 minutes

    def test_intervention_file_is_simple_name(self):
        """Test that intervention file is a simple name (no path components)."""
        assert "/" not in HUMAN_INTERVENTION_FILE
        assert "\\" not in HUMAN_INTERVENTION_FILE
        assert HUMAN_INTERVENTION_FILE.isalpha() or HUMAN_INTERVENTION_FILE.replace("_", "").isalpha()
