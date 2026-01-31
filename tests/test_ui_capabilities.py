"""
Tests for the UI capabilities module
=====================================

Tests covering ui/capabilities.py - terminal capability detection
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

from ui.capabilities import (
    supports_unicode,
    supports_color,
    supports_interactive,
    _is_fancy_ui_enabled,
)


# =============================================================================
# _is_fancy_ui_enabled Tests
# =============================================================================

class TestIsFancyUIEnabled:
    """Tests for _is_fancy_ui_enabled function."""

    def test_default_enabled(self):
        """Test that fancy UI is enabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            # When ENABLE_FANCY_UI is not set, should default to true
            # Note: We need to import fresh or the cached value may be used
            result = _is_fancy_ui_enabled()
            assert result is True

    def test_explicit_true_values(self):
        """Test that various true values enable fancy UI."""
        true_values = ["true", "TRUE", "True", "1", "yes", "YES", "on", "ON"]
        for value in true_values:
            with patch.dict(os.environ, {"ENABLE_FANCY_UI": value}):
                result = _is_fancy_ui_enabled()
                assert result is True, f"Value '{value}' should enable fancy UI"

    def test_false_values(self):
        """Test that false values disable fancy UI."""
        false_values = ["false", "FALSE", "0", "no", "off", "disabled"]
        for value in false_values:
            with patch.dict(os.environ, {"ENABLE_FANCY_UI": value}):
                result = _is_fancy_ui_enabled()
                assert result is False, f"Value '{value}' should disable fancy UI"


# =============================================================================
# supports_unicode Tests
# =============================================================================

class TestSupportsUnicode:
    """Tests for supports_unicode function."""

    def test_utf8_encoding(self):
        """Test that UTF-8 encoding returns True."""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "utf-8"

        with patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"}):
            with patch.object(sys, 'stdout', mock_stdout):
                result = supports_unicode()
                assert result is True

    def test_utf8_uppercase(self):
        """Test that UTF8 (uppercase) encoding returns True."""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "UTF-8"

        with patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"}):
            with patch.object(sys, 'stdout', mock_stdout):
                result = supports_unicode()
                assert result is True

    def test_non_utf8_encoding(self):
        """Test that non-UTF8 encoding returns False."""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "cp1252"

        with patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"}):
            with patch.object(sys, 'stdout', mock_stdout):
                result = supports_unicode()
                assert result is False

    def test_no_encoding(self):
        """Test handling when encoding is None."""
        mock_stdout = MagicMock()
        mock_stdout.encoding = None

        with patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"}):
            with patch.object(sys, 'stdout', mock_stdout):
                result = supports_unicode()
                assert result is False

    def test_fancy_ui_disabled(self):
        """Test that Unicode is disabled when fancy UI is disabled."""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "utf-8"

        with patch.dict(os.environ, {"ENABLE_FANCY_UI": "false"}):
            with patch.object(sys, 'stdout', mock_stdout):
                result = supports_unicode()
                assert result is False


# =============================================================================
# supports_color Tests
# =============================================================================

class TestSupportsColor:
    """Tests for supports_color function."""

    def test_no_color_env(self):
        """Test that NO_COLOR environment variable disables color."""
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True

        with patch.dict(os.environ, {"ENABLE_FANCY_UI": "true", "NO_COLOR": "1"}):
            with patch.object(sys, 'stdout', mock_stdout):
                result = supports_color()
                assert result is False

    def test_force_color_env(self):
        """Test that FORCE_COLOR environment variable enables color."""
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = False  # Not a TTY

        with patch.dict(os.environ, {"ENABLE_FANCY_UI": "true", "FORCE_COLOR": "1"}, clear=True):
            with patch.object(sys, 'stdout', mock_stdout):
                result = supports_color()
                assert result is True

    def test_not_tty(self):
        """Test that non-TTY returns False."""
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = False

        with patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"}, clear=True):
            with patch.object(sys, 'stdout', mock_stdout):
                result = supports_color()
                assert result is False

    def test_tty_with_color_term(self):
        """Test that TTY with a color TERM returns True."""
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True

        with patch.dict(os.environ, {"ENABLE_FANCY_UI": "true", "TERM": "xterm-256color"}, clear=True):
            with patch.object(sys, 'stdout', mock_stdout):
                result = supports_color()
                assert result is True

    def test_dumb_term(self):
        """Test that TERM=dumb returns False."""
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True

        with patch.dict(os.environ, {"ENABLE_FANCY_UI": "true", "TERM": "dumb"}, clear=True):
            with patch.object(sys, 'stdout', mock_stdout):
                result = supports_color()
                assert result is False

    def test_fancy_ui_disabled(self):
        """Test that color is disabled when fancy UI is disabled."""
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True

        with patch.dict(os.environ, {"ENABLE_FANCY_UI": "false", "TERM": "xterm-256color"}, clear=True):
            with patch.object(sys, 'stdout', mock_stdout):
                result = supports_color()
                assert result is False

    def test_no_isatty_method(self):
        """Test handling when stdout has no isatty method."""
        mock_stdout = MagicMock(spec=[])  # No isatty

        with patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"}, clear=True):
            with patch.object(sys, 'stdout', mock_stdout):
                result = supports_color()
                assert result is False


# =============================================================================
# supports_interactive Tests
# =============================================================================

class TestSupportsInteractive:
    """Tests for supports_interactive function."""

    def test_interactive_tty(self):
        """Test that TTY stdin returns True."""
        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True

        with patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"}):
            with patch.object(sys, 'stdin', mock_stdin):
                result = supports_interactive()
                assert result is True

    def test_non_interactive(self):
        """Test that non-TTY stdin returns False."""
        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False

        with patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"}):
            with patch.object(sys, 'stdin', mock_stdin):
                result = supports_interactive()
                assert result is False

    def test_no_isatty_method(self):
        """Test handling when stdin has no isatty method."""
        mock_stdin = MagicMock(spec=[])  # No isatty

        with patch.dict(os.environ, {"ENABLE_FANCY_UI": "true"}):
            with patch.object(sys, 'stdin', mock_stdin):
                result = supports_interactive()
                assert result is False

    def test_fancy_ui_disabled(self):
        """Test that interactive is disabled when fancy UI is disabled."""
        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True

        with patch.dict(os.environ, {"ENABLE_FANCY_UI": "false"}):
            with patch.object(sys, 'stdin', mock_stdin):
                result = supports_interactive()
                assert result is False


# =============================================================================
# Integration Tests
# =============================================================================

class TestCapabilitiesIntegration:
    """Integration tests for capability detection."""

    def test_all_capabilities_respect_fancy_ui(self):
        """Test that all capabilities respect ENABLE_FANCY_UI setting."""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "utf-8"
        mock_stdout.isatty.return_value = True

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True

        # With fancy UI disabled, all should return False
        with patch.dict(os.environ, {"ENABLE_FANCY_UI": "false", "TERM": "xterm"}, clear=True):
            with patch.object(sys, 'stdout', mock_stdout):
                with patch.object(sys, 'stdin', mock_stdin):
                    assert supports_unicode() is False
                    assert supports_color() is False
                    assert supports_interactive() is False

    def test_typical_terminal_environment(self):
        """Test typical terminal environment detection."""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "utf-8"
        mock_stdout.isatty.return_value = True

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True

        with patch.dict(os.environ, {"ENABLE_FANCY_UI": "true", "TERM": "xterm-256color"}, clear=True):
            with patch.object(sys, 'stdout', mock_stdout):
                with patch.object(sys, 'stdin', mock_stdin):
                    assert supports_unicode() is True
                    assert supports_color() is True
                    assert supports_interactive() is True

    def test_piped_output_environment(self):
        """Test piped output environment (non-TTY)."""
        mock_stdout = MagicMock()
        mock_stdout.encoding = "utf-8"
        mock_stdout.isatty.return_value = False  # Piped

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False  # Piped

        with patch.dict(os.environ, {"ENABLE_FANCY_UI": "true", "TERM": "xterm"}, clear=True):
            with patch.object(sys, 'stdout', mock_stdout):
                with patch.object(sys, 'stdin', mock_stdin):
                    # Unicode depends on encoding, not TTY
                    assert supports_unicode() is True
                    # Color requires TTY
                    assert supports_color() is False
                    # Interactive requires TTY
                    assert supports_interactive() is False
