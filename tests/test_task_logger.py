"""
Tests for the task_logger module
=================================

Tests covering task_logger/logger.py - TaskLogger class
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from task_logger.logger import TaskLogger
from task_logger.models import LogEntry, LogEntryType, LogPhase


# =============================================================================
# TaskLogger Initialization Tests
# =============================================================================

class TestTaskLoggerInit:
    """Tests for TaskLogger initialization."""

    @pytest.fixture
    def temp_spec_dir(self):
        """Create a temporary spec directory."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_init_creates_logger(self, temp_spec_dir):
        """Test logger initialization."""
        logger = TaskLogger(temp_spec_dir, emit_markers=False)

        assert logger.spec_dir == temp_spec_dir
        assert logger.emit_markers is False
        assert logger.current_phase is None
        assert logger.current_session is None

    def test_init_with_markers(self, temp_spec_dir):
        """Test initialization with markers enabled."""
        logger = TaskLogger(temp_spec_dir, emit_markers=True)
        assert logger.emit_markers is True

    def test_log_file_path(self, temp_spec_dir):
        """Test log file path is set correctly."""
        logger = TaskLogger(temp_spec_dir, emit_markers=False)
        assert logger.log_file == temp_spec_dir / "task_logs.json"


# =============================================================================
# TaskLogger Session Tests
# =============================================================================

class TestTaskLoggerSession:
    """Tests for session management."""

    @pytest.fixture
    def logger(self):
        """Create a TaskLogger instance."""
        with tempfile.TemporaryDirectory() as td:
            yield TaskLogger(Path(td), emit_markers=False)

    def test_set_session(self, logger):
        """Test setting session number."""
        logger.set_session(5)
        assert logger.current_session == 5

    def test_set_subtask(self, logger):
        """Test setting subtask ID."""
        logger.set_subtask("1.1")
        assert logger.current_subtask == "1.1"

    def test_set_subtask_none(self, logger):
        """Test clearing subtask."""
        logger.set_subtask("1.1")
        logger.set_subtask(None)
        assert logger.current_subtask is None


# =============================================================================
# TaskLogger Phase Tests
# =============================================================================

class TestTaskLoggerPhases:
    """Tests for phase management."""

    @pytest.fixture
    def logger(self):
        """Create a TaskLogger instance."""
        with tempfile.TemporaryDirectory() as td:
            yield TaskLogger(Path(td), emit_markers=False)

    def test_start_phase(self, logger, capsys):
        """Test starting a phase."""
        logger.start_phase(LogPhase.CODING)

        assert logger.current_phase == LogPhase.CODING
        captured = capsys.readouterr()
        assert "coding" in captured.out.lower()

    def test_start_phase_with_message(self, logger, capsys):
        """Test starting a phase with custom message."""
        logger.start_phase(LogPhase.PLANNING, message="Starting planning phase")

        captured = capsys.readouterr()
        assert "Starting planning phase" in captured.out

    def test_end_phase_success(self, logger, capsys):
        """Test ending a phase successfully."""
        logger.start_phase(LogPhase.CODING)
        capsys.readouterr()  # Clear start message

        logger.end_phase(LogPhase.CODING, success=True)

        assert logger.current_phase is None
        captured = capsys.readouterr()
        assert "Completed" in captured.out

    def test_end_phase_failure(self, logger, capsys):
        """Test ending a phase with failure."""
        logger.start_phase(LogPhase.CODING)
        capsys.readouterr()

        logger.end_phase(LogPhase.CODING, success=False)

        captured = capsys.readouterr()
        assert "Failed" in captured.out


# =============================================================================
# TaskLogger Logging Tests
# =============================================================================

class TestTaskLoggerLogging:
    """Tests for log message methods."""

    @pytest.fixture
    def logger(self):
        """Create a TaskLogger instance."""
        with tempfile.TemporaryDirectory() as td:
            yield TaskLogger(Path(td), emit_markers=False)

    def test_log_text(self, logger, capsys):
        """Test logging a text message."""
        logger.start_phase(LogPhase.CODING)
        capsys.readouterr()

        logger.log("Test message")

        captured = capsys.readouterr()
        assert "Test message" in captured.out

    def test_log_no_print(self, logger, capsys):
        """Test logging without printing to console."""
        logger.start_phase(LogPhase.CODING)
        capsys.readouterr()

        logger.log("Silent message", print_to_console=False)

        captured = capsys.readouterr()
        assert "Silent message" not in captured.out

    def test_log_error(self, logger, capsys):
        """Test logging an error."""
        logger.start_phase(LogPhase.CODING)
        capsys.readouterr()

        logger.log_error("Error occurred")

        captured = capsys.readouterr()
        assert "Error occurred" in captured.out

    def test_log_success(self, logger, capsys):
        """Test logging a success."""
        logger.start_phase(LogPhase.CODING)
        capsys.readouterr()

        logger.log_success("Operation successful")

        captured = capsys.readouterr()
        assert "Operation successful" in captured.out

    def test_log_info(self, logger, capsys):
        """Test logging info."""
        logger.start_phase(LogPhase.CODING)
        capsys.readouterr()

        logger.log_info("Information here")

        captured = capsys.readouterr()
        assert "Information here" in captured.out


# =============================================================================
# TaskLogger Tool Logging Tests
# =============================================================================

class TestTaskLoggerToolLogging:
    """Tests for tool logging."""

    @pytest.fixture
    def logger(self):
        """Create a TaskLogger instance."""
        with tempfile.TemporaryDirectory() as td:
            yield TaskLogger(Path(td), emit_markers=False)

    def test_tool_start(self, logger, capsys):
        """Test logging tool start."""
        logger.start_phase(LogPhase.CODING)
        capsys.readouterr()

        logger.tool_start("Read", "/path/to/file.py")

        captured = capsys.readouterr()
        assert "[Tool: Read]" in captured.out

    def test_tool_start_no_input(self, logger, capsys):
        """Test tool start without input."""
        logger.start_phase(LogPhase.CODING)
        capsys.readouterr()

        logger.tool_start("Glob")

        captured = capsys.readouterr()
        assert "[Tool: Glob]" in captured.out

    def test_tool_end_success(self, logger, capsys):
        """Test logging tool end with success."""
        logger.start_phase(LogPhase.CODING)
        logger.tool_start("Read", "/file.py")
        capsys.readouterr()

        logger.tool_end("Read", success=True, print_to_console=True)

        captured = capsys.readouterr()
        assert "[Done]" in captured.out

    def test_tool_end_failure(self, logger, capsys):
        """Test logging tool end with failure."""
        logger.start_phase(LogPhase.CODING)
        logger.tool_start("Bash", "command")
        capsys.readouterr()

        logger.tool_end("Bash", success=False, result="Command failed", print_to_console=True)

        captured = capsys.readouterr()
        assert "[Error]" in captured.out

    def test_tool_end_with_result(self, logger, capsys):
        """Test tool end with result."""
        logger.start_phase(LogPhase.CODING)
        logger.tool_start("Read")
        capsys.readouterr()

        logger.tool_end("Read", success=True, result="100 lines", print_to_console=True)

        captured = capsys.readouterr()
        assert "100 lines" in captured.out


# =============================================================================
# TaskLogger Log With Detail Tests
# =============================================================================

class TestTaskLoggerLogWithDetail:
    """Tests for log_with_detail method."""

    @pytest.fixture
    def logger(self):
        """Create a TaskLogger instance."""
        with tempfile.TemporaryDirectory() as td:
            yield TaskLogger(Path(td), emit_markers=False)

    def test_log_with_detail(self, logger, capsys):
        """Test logging with detail."""
        logger.start_phase(LogPhase.CODING)
        capsys.readouterr()

        logger.log_with_detail(
            content="File read",
            detail="Full file content here...",
            entry_type=LogEntryType.TEXT,
        )

        captured = capsys.readouterr()
        assert "File read" in captured.out

    def test_log_with_subphase(self, logger, capsys):
        """Test logging with subphase."""
        logger.start_phase(LogPhase.CODING)
        capsys.readouterr()

        logger.log_with_detail(
            content="Discovery complete",
            detail="Found 10 files",
            subphase="PROJECT DISCOVERY",
        )

        captured = capsys.readouterr()
        assert "Discovery complete" in captured.out


# =============================================================================
# TaskLogger Subphase Tests
# =============================================================================

class TestTaskLoggerSubphase:
    """Tests for subphase management."""

    @pytest.fixture
    def logger(self):
        """Create a TaskLogger instance."""
        with tempfile.TemporaryDirectory() as td:
            yield TaskLogger(Path(td), emit_markers=False)

    def test_start_subphase(self, logger, capsys):
        """Test starting a subphase."""
        logger.start_phase(LogPhase.CODING)
        capsys.readouterr()

        logger.start_subphase("CONTEXT GATHERING")

        captured = capsys.readouterr()
        assert "CONTEXT GATHERING" in captured.out


# =============================================================================
# TaskLogger Data Retrieval Tests
# =============================================================================

class TestTaskLoggerDataRetrieval:
    """Tests for data retrieval methods."""

    @pytest.fixture
    def logger(self):
        """Create a TaskLogger instance."""
        with tempfile.TemporaryDirectory() as td:
            yield TaskLogger(Path(td), emit_markers=False)

    def test_get_logs(self, logger):
        """Test getting all logs."""
        logger.start_phase(LogPhase.CODING)
        logger.log("Test message", print_to_console=False)

        logs = logger.get_logs()

        assert "phases" in logs
        # Entries are inside phases, not at root level
        assert "coding" in logs["phases"]
        assert "entries" in logs["phases"]["coding"]

    def test_get_phase_logs(self, logger):
        """Test getting logs for a specific phase."""
        logger.start_phase(LogPhase.CODING)
        logger.log("Coding message", print_to_console=False)

        phase_logs = logger.get_phase_logs(LogPhase.CODING)

        assert phase_logs is not None

    def test_clear_logs(self, logger):
        """Test clearing all logs."""
        logger.start_phase(LogPhase.CODING)
        logger.log("Test", print_to_console=False)

        logger.clear()

        logs = logger.get_logs()
        # Should have reset storage
        assert logs is not None


# =============================================================================
# TaskLogger ANSI Stripping Tests
# =============================================================================

class TestTaskLoggerAnsiStripping:
    """Tests for ANSI code stripping."""

    @pytest.fixture
    def logger(self):
        """Create a TaskLogger instance."""
        with tempfile.TemporaryDirectory() as td:
            yield TaskLogger(Path(td), emit_markers=False)

    def test_strips_ansi_from_log(self, logger):
        """Test that ANSI codes are stripped from logs."""
        logger.start_phase(LogPhase.CODING)

        # Log with ANSI codes
        logger.log("\x1b[32mGreen text\x1b[0m", print_to_console=False)

        logs = logger.get_logs()
        # Check entries don't contain ANSI codes
        for entry in logs.get("entries", []):
            if entry.get("type") == "text":
                assert "\x1b[" not in entry.get("content", "")


# =============================================================================
# Integration Tests
# =============================================================================

class TestTaskLoggerIntegration:
    """Integration tests for TaskLogger."""

    def test_full_workflow(self, capsys):
        """Test a complete logging workflow."""
        with tempfile.TemporaryDirectory() as td:
            logger = TaskLogger(Path(td), emit_markers=False)

            # Set session
            logger.set_session(1)
            logger.set_subtask("1.1")

            # Start phase
            logger.start_phase(LogPhase.CODING, message="Starting coding phase")

            # Log some messages
            logger.log_info("Reading files...")
            logger.tool_start("Read", "src/app.py")
            logger.tool_end("Read", success=True)
            logger.log("File processed", print_to_console=False)

            # Start subphase
            logger.start_subphase("IMPLEMENTATION")
            logger.tool_start("Write", "src/new.py")
            logger.tool_end("Write", success=True)

            # End phase
            logger.end_phase(LogPhase.CODING, success=True)

            # Verify logs
            logs = logger.get_logs()
            assert "phases" in logs
            assert "coding" in logs["phases"]
            assert len(logs["phases"]["coding"]["entries"]) > 0

    def test_multiple_phases(self):
        """Test logging across multiple phases."""
        with tempfile.TemporaryDirectory() as td:
            logger = TaskLogger(Path(td), emit_markers=False)

            # Planning phase
            logger.start_phase(LogPhase.PLANNING)
            logger.log("Planning...", print_to_console=False)
            logger.end_phase(LogPhase.PLANNING, success=True)

            # Coding phase
            logger.start_phase(LogPhase.CODING)
            logger.log("Coding...", print_to_console=False)
            logger.end_phase(LogPhase.CODING, success=True)

            # Validation phase (LogPhase.VALIDATION, not QA)
            logger.start_phase(LogPhase.VALIDATION)
            logger.log("Validating...", print_to_console=False)
            logger.end_phase(LogPhase.VALIDATION, success=True)

            logs = logger.get_logs()
            # Check that all phases have entries
            assert len(logs["phases"]["planning"]["entries"]) >= 2
            assert len(logs["phases"]["coding"]["entries"]) >= 2
            assert len(logs["phases"]["validation"]["entries"]) >= 2

    def test_tool_workflow(self):
        """Test tool start/end workflow."""
        with tempfile.TemporaryDirectory() as td:
            logger = TaskLogger(Path(td), emit_markers=False)
            logger.start_phase(LogPhase.CODING)

            # Multiple tools
            tools = ["Read", "Write", "Bash", "Glob"]
            for tool in tools:
                logger.tool_start(tool, f"input for {tool}", print_to_console=False)
                logger.tool_end(tool, success=True, print_to_console=False)

            logger.end_phase(LogPhase.CODING, success=True)

            logs = logger.get_logs()
            # Each tool has start and end entries
            coding_entries = logs["phases"]["coding"]["entries"]
            tool_entries = [
                e for e in coding_entries
                if e.get("type") in ("tool_start", "tool_end")
            ]
            assert len(tool_entries) == 8  # 4 tools * 2 (start + end)
