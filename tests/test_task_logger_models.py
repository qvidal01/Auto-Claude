"""
Tests for the task logger models module
========================================

Tests covering task_logger/models.py, task_logger/ansi.py, task_logger/utils.py
"""

import pytest
from datetime import datetime
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from task_logger.models import LogPhase, LogEntryType, LogEntry, PhaseLog
from task_logger.ansi import strip_ansi_codes


# =============================================================================
# LogPhase Tests
# =============================================================================

class TestLogPhase:
    """Tests for LogPhase enum."""

    def test_all_phases_exist(self):
        """Test that all expected phases exist."""
        expected_phases = ["PLANNING", "CODING", "VALIDATION"]
        for phase in expected_phases:
            assert hasattr(LogPhase, phase)

    def test_phase_values(self):
        """Test phase string values."""
        assert LogPhase.PLANNING.value == "planning"
        assert LogPhase.CODING.value == "coding"
        assert LogPhase.VALIDATION.value == "validation"

    def test_phase_is_str(self):
        """Test that LogPhase inherits from str."""
        assert isinstance(LogPhase.PLANNING, str)
        assert LogPhase.PLANNING == "planning"

    def test_phase_from_value(self):
        """Test creating phase from string value."""
        assert LogPhase("planning") == LogPhase.PLANNING
        assert LogPhase("coding") == LogPhase.CODING
        assert LogPhase("validation") == LogPhase.VALIDATION


# =============================================================================
# LogEntryType Tests
# =============================================================================

class TestLogEntryType:
    """Tests for LogEntryType enum."""

    def test_all_types_exist(self):
        """Test that all expected entry types exist."""
        expected_types = [
            "TEXT", "TOOL_START", "TOOL_END",
            "PHASE_START", "PHASE_END",
            "ERROR", "SUCCESS", "INFO"
        ]
        for entry_type in expected_types:
            assert hasattr(LogEntryType, entry_type)

    def test_type_values(self):
        """Test entry type string values."""
        assert LogEntryType.TEXT.value == "text"
        assert LogEntryType.TOOL_START.value == "tool_start"
        assert LogEntryType.TOOL_END.value == "tool_end"
        assert LogEntryType.PHASE_START.value == "phase_start"
        assert LogEntryType.PHASE_END.value == "phase_end"
        assert LogEntryType.ERROR.value == "error"
        assert LogEntryType.SUCCESS.value == "success"
        assert LogEntryType.INFO.value == "info"

    def test_type_is_str(self):
        """Test that LogEntryType inherits from str."""
        assert isinstance(LogEntryType.TEXT, str)


# =============================================================================
# LogEntry Tests
# =============================================================================

class TestLogEntry:
    """Tests for LogEntry dataclass."""

    def test_minimal_creation(self):
        """Test minimal LogEntry creation."""
        entry = LogEntry(
            timestamp="2025-01-01T12:00:00",
            type="text",
            content="Test message",
            phase="coding"
        )
        assert entry.timestamp == "2025-01-01T12:00:00"
        assert entry.type == "text"
        assert entry.content == "Test message"
        assert entry.phase == "coding"

    def test_default_values(self):
        """Test default values are None."""
        entry = LogEntry(
            timestamp="2025-01-01T12:00:00",
            type="text",
            content="Test",
            phase="coding"
        )
        assert entry.tool_name is None
        assert entry.tool_input is None
        assert entry.subtask_id is None
        assert entry.session is None
        assert entry.detail is None
        assert entry.subphase is None
        assert entry.collapsed is None

    def test_full_creation(self):
        """Test LogEntry with all fields."""
        entry = LogEntry(
            timestamp="2025-01-01T12:00:00",
            type="tool_start",
            content="Reading file",
            phase="coding",
            tool_name="Read",
            tool_input="src/main.py",
            subtask_id="1",
            session=1,
            detail="Full file content...",
            subphase="IMPLEMENTATION",
            collapsed=True
        )
        assert entry.tool_name == "Read"
        assert entry.tool_input == "src/main.py"
        assert entry.subtask_id == "1"
        assert entry.session == 1
        assert entry.detail == "Full file content..."
        assert entry.subphase == "IMPLEMENTATION"
        assert entry.collapsed is True

    def test_to_dict_excludes_none(self):
        """Test to_dict excludes None values."""
        entry = LogEntry(
            timestamp="2025-01-01T12:00:00",
            type="text",
            content="Test",
            phase="coding"
        )
        result = entry.to_dict()

        assert "timestamp" in result
        assert "type" in result
        assert "content" in result
        assert "phase" in result
        # None values should be excluded
        assert "tool_name" not in result
        assert "tool_input" not in result
        assert "subtask_id" not in result

    def test_to_dict_includes_values(self):
        """Test to_dict includes non-None values."""
        entry = LogEntry(
            timestamp="2025-01-01T12:00:00",
            type="tool_end",
            content="Done",
            phase="coding",
            tool_name="Read",
            session=2
        )
        result = entry.to_dict()

        assert result["tool_name"] == "Read"
        assert result["session"] == 2

    def test_to_dict_returns_dict(self):
        """Test that to_dict returns a dictionary."""
        entry = LogEntry(
            timestamp="2025-01-01T12:00:00",
            type="text",
            content="Test",
            phase="coding"
        )
        assert isinstance(entry.to_dict(), dict)


# =============================================================================
# PhaseLog Tests
# =============================================================================

class TestPhaseLog:
    """Tests for PhaseLog dataclass."""

    def test_minimal_creation(self):
        """Test minimal PhaseLog creation."""
        phase_log = PhaseLog(
            phase="coding",
            status="active"
        )
        assert phase_log.phase == "coding"
        assert phase_log.status == "active"

    def test_default_entries(self):
        """Test that entries defaults to empty list."""
        phase_log = PhaseLog(phase="coding", status="pending")
        assert phase_log.entries == []

    def test_post_init_creates_list(self):
        """Test that __post_init__ creates entries list if None."""
        phase_log = PhaseLog(phase="coding", status="pending", entries=None)
        assert phase_log.entries == []
        assert isinstance(phase_log.entries, list)

    def test_full_creation(self):
        """Test PhaseLog with all fields."""
        entries = [{"type": "text", "content": "Test"}]
        phase_log = PhaseLog(
            phase="validation",
            status="completed",
            started_at="2025-01-01T12:00:00",
            completed_at="2025-01-01T12:30:00",
            entries=entries
        )
        assert phase_log.started_at == "2025-01-01T12:00:00"
        assert phase_log.completed_at == "2025-01-01T12:30:00"
        assert phase_log.entries == entries

    def test_to_dict(self):
        """Test to_dict method."""
        phase_log = PhaseLog(
            phase="coding",
            status="active",
            started_at="2025-01-01T12:00:00"
        )
        result = phase_log.to_dict()

        assert result["phase"] == "coding"
        assert result["status"] == "active"
        assert result["started_at"] == "2025-01-01T12:00:00"
        assert result["completed_at"] is None
        assert result["entries"] == []

    def test_to_dict_with_entries(self):
        """Test to_dict with entries."""
        entries = [
            {"type": "text", "content": "Entry 1"},
            {"type": "text", "content": "Entry 2"}
        ]
        phase_log = PhaseLog(
            phase="coding",
            status="completed",
            entries=entries
        )
        result = phase_log.to_dict()

        assert len(result["entries"]) == 2

    def test_status_values(self):
        """Test different status values."""
        statuses = ["pending", "active", "completed", "failed"]
        for status in statuses:
            phase_log = PhaseLog(phase="coding", status=status)
            assert phase_log.status == status


# =============================================================================
# strip_ansi_codes Tests
# =============================================================================

class TestStripAnsiCodes:
    """Tests for strip_ansi_codes function."""

    def test_no_codes(self):
        """Test string without ANSI codes."""
        result = strip_ansi_codes("Hello World")
        assert result == "Hello World"

    def test_empty_string(self):
        """Test empty string."""
        result = strip_ansi_codes("")
        assert result == ""

    def test_none_input(self):
        """Test None input returns empty string."""
        result = strip_ansi_codes(None)
        assert result == ""

    def test_color_codes(self):
        """Test stripping color codes."""
        # Red text
        result = strip_ansi_codes("\x1b[31mRed Text\x1b[0m")
        assert result == "Red Text"

    def test_multiple_color_codes(self):
        """Test stripping multiple color codes."""
        result = strip_ansi_codes("\x1b[31mRed\x1b[0m \x1b[32mGreen\x1b[0m")
        assert result == "Red Green"

    def test_formatting_codes(self):
        """Test stripping formatting codes (bold, underline)."""
        # Bold
        result = strip_ansi_codes("\x1b[1mBold\x1b[0m")
        assert result == "Bold"

    def test_cursor_codes(self):
        """Test stripping cursor movement codes."""
        # Hide cursor
        result = strip_ansi_codes("\x1b[?25lHidden\x1b[?25h")
        assert result == "Hidden"

    def test_complex_sequence(self):
        """Test complex ANSI sequence from logging."""
        input_text = "\x1b[90m[21:40:22.196]\x1b[0m \x1b[36m[DEBUG]\x1b[0m Message"
        result = strip_ansi_codes(input_text)
        assert result == "[21:40:22.196] [DEBUG] Message"

    def test_osc_with_bel(self):
        """Test stripping OSC sequences with BEL terminator."""
        # Set window title
        result = strip_ansi_codes("\x1b]0;Window Title\x07Text")
        assert result == "Text"

    def test_osc_with_st(self):
        """Test stripping OSC sequences with ST terminator."""
        result = strip_ansi_codes("\x1b]0;Title\x1b\\Text")
        assert result == "Text"

    def test_preserves_non_ansi(self):
        """Test that non-ANSI content is preserved."""
        result = strip_ansi_codes("Line 1\nLine 2\tTabbed")
        assert result == "Line 1\nLine 2\tTabbed"

    def test_unicode_content(self):
        """Test preserving Unicode content."""
        result = strip_ansi_codes("\x1b[32m功能 🚀\x1b[0m")
        assert result == "功能 🚀"

    def test_bracketed_paste(self):
        """Test stripping bracketed paste sequences."""
        result = strip_ansi_codes("\x1b[200~pasted text\x1b[201~")
        assert result == "pasted text"


# =============================================================================
# Integration Tests
# =============================================================================

class TestTaskLoggerIntegration:
    """Integration tests for task logger models."""

    def test_log_entry_with_ansi_stripped(self):
        """Test creating log entry with ANSI-stripped content."""
        raw_content = "\x1b[32mSuccess:\x1b[0m Task completed"
        clean_content = strip_ansi_codes(raw_content)

        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            type=LogEntryType.SUCCESS.value,
            content=clean_content,
            phase=LogPhase.CODING.value
        )

        assert entry.content == "Success: Task completed"
        result = entry.to_dict()
        assert "Success: Task completed" in result["content"]

    def test_phase_log_with_entries(self):
        """Test PhaseLog with multiple LogEntry objects."""
        entries = []
        for i in range(3):
            entry = LogEntry(
                timestamp=datetime.now().isoformat(),
                type=LogEntryType.TEXT.value,
                content=f"Entry {i}",
                phase=LogPhase.CODING.value
            )
            entries.append(entry.to_dict())

        phase_log = PhaseLog(
            phase=LogPhase.CODING.value,
            status="completed",
            started_at=datetime.now().isoformat(),
            entries=entries
        )

        result = phase_log.to_dict()
        assert len(result["entries"]) == 3
        assert result["status"] == "completed"

    def test_tool_execution_log_flow(self):
        """Test logging a tool execution flow."""
        # Tool start
        start_entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            type=LogEntryType.TOOL_START.value,
            content="Reading file",
            phase=LogPhase.CODING.value,
            tool_name="Read",
            tool_input="src/app.py"
        )

        # Tool end
        end_entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            type=LogEntryType.TOOL_END.value,
            content="File read successfully",
            phase=LogPhase.CODING.value,
            tool_name="Read",
            detail="def main():\n    pass"
        )

        start_dict = start_entry.to_dict()
        end_dict = end_entry.to_dict()

        assert start_dict["tool_name"] == "Read"
        assert start_dict["tool_input"] == "src/app.py"
        assert end_dict["detail"] == "def main():\n    pass"
