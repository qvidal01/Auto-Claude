"""
Tests for the agents session module
====================================

Tests covering agents/session.py - is_tool_concurrency_error function
"""

import pytest

from agents.session import is_tool_concurrency_error


# =============================================================================
# is_tool_concurrency_error Tests
# =============================================================================

class TestIsToolConcurrencyError:
    """Tests for is_tool_concurrency_error function."""

    def test_400_with_tool_concurrency(self):
        """Test 400 error with tool concurrency keywords."""
        error = Exception("API Error: 400 - tool concurrency limit exceeded")
        assert is_tool_concurrency_error(error) is True

    def test_400_with_too_many_tools(self):
        """Test 400 error with 'too many tools' message."""
        error = Exception("400 Bad Request: too many tools in request")
        assert is_tool_concurrency_error(error) is True

    def test_400_with_concurrent_tool(self):
        """Test 400 error with 'concurrent tool' message."""
        error = Exception("Error 400: concurrent tool use limit hit")
        assert is_tool_concurrency_error(error) is True

    def test_400_without_concurrency_keywords(self):
        """Test 400 error without concurrency keywords."""
        error = Exception("400 Bad Request: invalid JSON")
        assert is_tool_concurrency_error(error) is False

    def test_non_400_error(self):
        """Test non-400 error codes."""
        error = Exception("500 Internal Server Error: tool concurrency")
        assert is_tool_concurrency_error(error) is False

    def test_rate_limit_error(self):
        """Test rate limit error (not concurrency)."""
        error = Exception("429 Rate Limited: too many requests")
        assert is_tool_concurrency_error(error) is False

    def test_empty_error_message(self):
        """Test empty error message."""
        error = Exception("")
        assert is_tool_concurrency_error(error) is False

    def test_case_insensitive(self):
        """Test case insensitivity."""
        error = Exception("400 BAD REQUEST: TOOL CONCURRENCY LIMIT")
        assert is_tool_concurrency_error(error) is True

    def test_mixed_case(self):
        """Test mixed case error message."""
        error = Exception("400 Error: Tool Concurrency exceeded")
        assert is_tool_concurrency_error(error) is True

    def test_tool_without_concurrency(self):
        """Test '400' and 'tool' but not concurrency."""
        error = Exception("400: tool not found")
        assert is_tool_concurrency_error(error) is False

    def test_concurrency_without_400(self):
        """Test concurrency keywords without 400 status."""
        error = Exception("Error: tool concurrency issue")
        assert is_tool_concurrency_error(error) is False

    def test_typical_anthropic_error(self):
        """Test typical Anthropic API error format."""
        error = Exception(
            "anthropic.APIStatusError: 400 - Error code: tool_use_concurrency_exceeded - "
            "Too many tool uses in a single request"
        )
        # This should match because it has '400' and 'tool' and 'concurrency'
        assert is_tool_concurrency_error(error) is True


# =============================================================================
# Edge Cases
# =============================================================================

class TestIsToolConcurrencyErrorEdgeCases:
    """Edge case tests for is_tool_concurrency_error."""

    def test_none_like_error(self):
        """Test error that converts to 'None' string."""
        # Exception with None message would be empty string
        error = Exception()
        assert is_tool_concurrency_error(error) is False

    def test_unicode_error_message(self):
        """Test error with unicode characters."""
        error = Exception("400: tool concurrency 工具并发")
        assert is_tool_concurrency_error(error) is True

    def test_multiline_error(self):
        """Test multiline error message."""
        error = Exception(
            "HTTP Error 400\n"
            "Reason: tool concurrency limit exceeded\n"
            "Details: Maximum 3 tools allowed"
        )
        assert is_tool_concurrency_error(error) is True

    def test_json_error_format(self):
        """Test JSON-formatted error message."""
        error = Exception(
            '{"status": 400, "error": {"type": "tool_concurrency", "message": "limit exceeded"}}'
        )
        assert is_tool_concurrency_error(error) is True

    def test_very_long_error(self):
        """Test very long error message."""
        prefix = "Some long context " * 100
        error = Exception(f"{prefix}400 tool concurrency error")
        assert is_tool_concurrency_error(error) is True
