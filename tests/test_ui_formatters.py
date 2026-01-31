"""
Tests for the UI formatters module
===================================

Tests covering ui/formatters.py - formatted output helpers
"""

import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

from ui.formatters import (
    print_header,
    print_section,
    print_status,
    print_key_value,
    print_phase_status,
)
from ui.icons import Icons


# =============================================================================
# print_header Tests
# =============================================================================

class TestPrintHeader:
    """Tests for print_header function."""

    def test_basic_header(self, capsys):
        """Test basic header without subtitle."""
        print_header("Test Title")
        captured = capsys.readouterr()
        assert "Test Title" in captured.out

    def test_header_with_subtitle(self, capsys):
        """Test header with subtitle."""
        print_header("Title", "Subtitle text")
        captured = capsys.readouterr()
        assert "Title" in captured.out
        assert "Subtitle" in captured.out

    def test_header_with_icon(self, capsys):
        """Test header with icon."""
        print_header("Title", icon_tuple=Icons.SUCCESS)
        captured = capsys.readouterr()
        assert "Title" in captured.out

    def test_header_width(self, capsys):
        """Test header with custom width."""
        print_header("Title", width=50)
        captured = capsys.readouterr()
        assert len(captured.out) > 0


# =============================================================================
# print_section Tests
# =============================================================================

class TestPrintSection:
    """Tests for print_section function."""

    def test_basic_section(self, capsys):
        """Test basic section header."""
        print_section("Section Name")
        captured = capsys.readouterr()
        assert "Section Name" in captured.out

    def test_section_with_icon(self, capsys):
        """Test section with icon."""
        print_section("Section", icon_tuple=Icons.GEAR)
        captured = capsys.readouterr()
        assert "Section" in captured.out


# =============================================================================
# print_status Tests
# =============================================================================

class TestPrintStatus:
    """Tests for print_status function."""

    def test_success_status(self, capsys):
        """Test success status message."""
        print_status("Operation completed", "success")
        captured = capsys.readouterr()
        assert "Operation completed" in captured.out

    def test_error_status(self, capsys):
        """Test error status message."""
        print_status("Something went wrong", "error")
        captured = capsys.readouterr()
        assert "Something went wrong" in captured.out

    def test_warning_status(self, capsys):
        """Test warning status message."""
        print_status("Be careful", "warning")
        captured = capsys.readouterr()
        assert "Be careful" in captured.out

    def test_info_status(self, capsys):
        """Test info status message."""
        print_status("Information here", "info")
        captured = capsys.readouterr()
        assert "Information here" in captured.out

    def test_pending_status(self, capsys):
        """Test pending status message."""
        print_status("Waiting...", "pending")
        captured = capsys.readouterr()
        assert "Waiting" in captured.out

    def test_progress_status(self, capsys):
        """Test progress status message."""
        print_status("In progress", "progress")
        captured = capsys.readouterr()
        assert "In progress" in captured.out

    def test_custom_icon(self, capsys):
        """Test status with custom icon."""
        print_status("Custom message", "info", icon_tuple=Icons.LIGHTNING)
        captured = capsys.readouterr()
        assert "Custom message" in captured.out

    def test_unknown_status_defaults(self, capsys):
        """Test unknown status type uses default formatting."""
        print_status("Unknown status type", "nonexistent")
        captured = capsys.readouterr()
        assert "Unknown status type" in captured.out


# =============================================================================
# print_key_value Tests
# =============================================================================

class TestPrintKeyValue:
    """Tests for print_key_value function."""

    def test_basic_key_value(self, capsys):
        """Test basic key-value printing."""
        print_key_value("Name", "John Doe")
        captured = capsys.readouterr()
        assert "Name" in captured.out
        assert "John Doe" in captured.out

    def test_key_value_with_indent(self, capsys):
        """Test key-value with custom indent."""
        print_key_value("Status", "Active", indent=4)
        captured = capsys.readouterr()
        assert "Status" in captured.out
        # Check indentation
        assert captured.out.startswith("    ")

    def test_key_value_no_indent(self, capsys):
        """Test key-value with no indent."""
        print_key_value("Key", "Value", indent=0)
        captured = capsys.readouterr()
        assert "Key" in captured.out
        assert captured.out.startswith("Key")


# =============================================================================
# print_phase_status Tests
# =============================================================================

class TestPrintPhaseStatus:
    """Tests for print_phase_status function."""

    def test_complete_phase(self, capsys):
        """Test complete phase status."""
        print_phase_status("Build", 10, 10, "complete")
        captured = capsys.readouterr()
        assert "Build" in captured.out
        assert "10/10" in captured.out

    def test_in_progress_phase(self, capsys):
        """Test in-progress phase status."""
        print_phase_status("Testing", 5, 10, "in_progress")
        captured = capsys.readouterr()
        assert "Testing" in captured.out
        assert "5/10" in captured.out

    def test_pending_phase(self, capsys):
        """Test pending phase status."""
        print_phase_status("Deploy", 0, 5, "pending")
        captured = capsys.readouterr()
        assert "Deploy" in captured.out
        assert "0/5" in captured.out

    def test_blocked_phase(self, capsys):
        """Test blocked phase status."""
        print_phase_status("Review", 0, 3, "blocked")
        captured = capsys.readouterr()
        assert "Review" in captured.out
        assert "0/3" in captured.out

    def test_unknown_status_uses_pending(self, capsys):
        """Test unknown status uses pending icon."""
        print_phase_status("Unknown", 1, 2, "unknown_status")
        captured = capsys.readouterr()
        assert "Unknown" in captured.out
        assert "1/2" in captured.out


# =============================================================================
# Integration Tests
# =============================================================================

class TestFormattersIntegration:
    """Integration tests for formatters module."""

    def test_multiple_outputs(self, capsys):
        """Test multiple formatter outputs together."""
        print_header("Build Report", "v1.0.0")
        print_section("Phases")
        print_phase_status("Planning", 1, 1, "complete")
        print_phase_status("Building", 5, 10, "in_progress")
        print_phase_status("Testing", 0, 5, "pending")
        print_status("Build in progress", "progress")

        captured = capsys.readouterr()
        assert "Build Report" in captured.out
        assert "Phases" in captured.out
        assert "Planning" in captured.out
        assert "Building" in captured.out
        assert "Testing" in captured.out

    def test_key_values_sequence(self, capsys):
        """Test sequence of key-value pairs."""
        print_key_value("Project", "auto-claude")
        print_key_value("Version", "2.7.6")
        print_key_value("Status", "Active")

        captured = capsys.readouterr()
        assert "Project" in captured.out
        assert "auto-claude" in captured.out
        assert "Version" in captured.out
        assert "2.7.6" in captured.out

    def test_all_status_types(self, capsys):
        """Test all status types in sequence."""
        statuses = ["success", "error", "warning", "info", "pending", "progress"]
        for status in statuses:
            print_status(f"Message for {status}", status)

        captured = capsys.readouterr()
        for status in statuses:
            assert f"Message for {status}" in captured.out
