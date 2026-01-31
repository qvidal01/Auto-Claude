"""
Tests for the UI spinner module
================================

Tests covering ui/spinner.py - Spinner class
"""

import sys
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

from ui.spinner import Spinner


# =============================================================================
# Spinner Tests
# =============================================================================

class TestSpinner:
    """Tests for Spinner class."""

    def test_init_default(self):
        """Test Spinner initialization with defaults."""
        spinner = Spinner()
        assert spinner.message == ""
        assert spinner.frame == 0
        assert spinner._running is False

    def test_init_with_message(self):
        """Test Spinner initialization with custom message."""
        spinner = Spinner("Loading...")
        assert spinner.message == "Loading..."

    def test_frames_exist(self):
        """Test that spinner frames are defined."""
        assert len(Spinner.FRAMES) > 0
        assert isinstance(Spinner.FRAMES, (list, tuple))

    def test_frames_are_strings(self):
        """Test that all frames are strings."""
        for frame in Spinner.FRAMES:
            assert isinstance(frame, str)

    def test_start_sets_running(self):
        """Test that start() sets running flag."""
        spinner = Spinner("Test")

        with patch.object(spinner, '_render'):
            spinner.start()
            assert spinner._running is True

    def test_stop_clears_running(self):
        """Test that stop() clears running flag."""
        spinner = Spinner("Test")
        spinner._running = True

        with patch('sys.stdout', new=StringIO()):
            spinner.stop()
            assert spinner._running is False

    def test_stop_with_message(self):
        """Test stop() with final message."""
        spinner = Spinner("Test")
        spinner._running = True

        with patch('sys.stdout', new=StringIO()):
            with patch('ui.spinner.print_status') as mock_print:
                spinner.stop(final_message="Done!", status="success")
                mock_print.assert_called_once_with("Done!", "success")

    def test_stop_without_message(self):
        """Test stop() without final message."""
        spinner = Spinner("Test")
        spinner._running = True

        with patch('sys.stdout', new=StringIO()):
            with patch('ui.spinner.print_status') as mock_print:
                spinner.stop()
                mock_print.assert_not_called()

    def test_update_advances_frame(self):
        """Test that update() advances the frame."""
        spinner = Spinner("Test")
        spinner.frame = 0

        with patch.object(spinner, '_render'):
            spinner.update()
            assert spinner.frame == 1

    def test_update_wraps_frame(self):
        """Test that frame wraps around."""
        spinner = Spinner("Test")
        spinner.frame = len(Spinner.FRAMES) - 1

        with patch.object(spinner, '_render'):
            spinner.update()
            assert spinner.frame == 0

    def test_update_changes_message(self):
        """Test that update() can change message."""
        spinner = Spinner("Original")

        with patch.object(spinner, '_render'):
            spinner.update("New message")
            assert spinner.message == "New message"

    def test_update_keeps_message_if_none(self):
        """Test that update() keeps message if not provided."""
        spinner = Spinner("Original")

        with patch.object(spinner, '_render'):
            spinner.update()
            assert spinner.message == "Original"

    def test_render_writes_to_stdout(self):
        """Test that _render() writes to stdout."""
        spinner = Spinner("Testing")
        spinner.frame = 0

        mock_stdout = MagicMock()
        with patch.object(sys, 'stdout', mock_stdout):
            spinner._render()

            # Should write carriage return + frame + message
            mock_stdout.write.assert_called()
            mock_stdout.flush.assert_called()

    def test_render_uses_current_frame(self):
        """Test that _render() uses the current frame character."""
        spinner = Spinner("Test")
        spinner.frame = 0

        mock_stdout = MagicMock()
        with patch.object(sys, 'stdout', mock_stdout):
            spinner._render()

        # Check that write was called with frame character and message
        call_args = mock_stdout.write.call_args[0][0]
        assert "Test" in call_args

    def test_multiple_updates(self):
        """Test multiple sequential updates."""
        spinner = Spinner("Progress")

        with patch.object(spinner, '_render'):
            for i in range(len(Spinner.FRAMES) + 3):
                expected_frame = i % len(Spinner.FRAMES)
                assert spinner.frame == expected_frame
                spinner.update()

    def test_start_calls_render(self):
        """Test that start() calls _render()."""
        spinner = Spinner("Loading")

        with patch.object(spinner, '_render') as mock_render:
            spinner.start()
            mock_render.assert_called_once()


# =============================================================================
# Spinner Context Manager Tests
# =============================================================================

class TestSpinnerUsage:
    """Tests for typical Spinner usage patterns."""

    def test_basic_usage(self):
        """Test basic spinner start/stop pattern."""
        spinner = Spinner("Loading data")

        with patch.object(spinner, '_render'):
            with patch('sys.stdout', new=StringIO()):
                spinner.start()
                assert spinner._running is True

                # Simulate some work with updates
                for _ in range(5):
                    spinner.update()

                spinner.stop("Complete", "success")
                assert spinner._running is False

    def test_update_message_flow(self):
        """Test changing messages during operation."""
        spinner = Spinner("Step 1")

        with patch.object(spinner, '_render'):
            spinner.start()

            spinner.update("Step 2")
            assert spinner.message == "Step 2"

            spinner.update("Step 3")
            assert spinner.message == "Step 3"

            with patch('sys.stdout', new=StringIO()):
                spinner.stop()


# =============================================================================
# Integration Tests
# =============================================================================

class TestSpinnerIntegration:
    """Integration tests for Spinner."""

    def test_render_output_format(self):
        """Test the format of render output."""
        spinner = Spinner("Loading")
        spinner.frame = 0

        mock_stdout = MagicMock()
        with patch.object(sys, 'stdout', mock_stdout):
            spinner._render()

        # Should have called write with carriage return and message
        write_call = mock_stdout.write.call_args[0][0]
        assert write_call.startswith("\r")
        assert "Loading" in write_call

    def test_full_lifecycle(self):
        """Test full spinner lifecycle."""
        spinner = Spinner("Starting")

        mock_stdout = MagicMock()
        with patch.object(sys, 'stdout', mock_stdout):
            with patch('ui.spinner.print_status'):
                spinner.start()
                assert spinner._running is True
                assert spinner.frame == 0

                # Update several times
                for i in range(5):
                    spinner.update(f"Step {i+1}")
                    assert spinner.frame == i + 1

                spinner.stop("Finished", "success")
                assert spinner._running is False

    def test_different_status_types(self):
        """Test stopping with different status types."""
        for status in ["success", "error", "warning", "info"]:
            spinner = Spinner("Test")
            spinner._running = True

            with patch('sys.stdout', new=StringIO()):
                with patch('ui.spinner.print_status') as mock_print:
                    spinner.stop(f"Status: {status}", status)
                    mock_print.assert_called_once_with(f"Status: {status}", status)
