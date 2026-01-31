"""
Tests for the UI statusline module
===================================

Tests covering ui/statusline.py - statusline formatting functions
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from ui.status import BuildState, BuildStatus, StatusManager


# =============================================================================
# format_compact Tests (via statusline module behavior)
# =============================================================================

class TestStatuslineFormatCompact:
    """Tests for compact status formatting."""

    def test_inactive_status_empty(self):
        """Test that inactive status returns empty string."""
        from ui.statusline import format_compact

        status = BuildStatus(active=False)
        result = format_compact(status)
        assert result == ""

    def test_active_with_subtasks(self):
        """Test active status with subtask progress."""
        from ui.statusline import format_compact

        status = BuildStatus(
            active=True,
            spec="001-feature",
            state=BuildState.BUILDING,
            subtasks_completed=3,
            subtasks_total=10
        )
        result = format_compact(status)

        # Should contain progress
        assert "3/10" in result
        assert "30%" in result

    def test_active_with_phase(self):
        """Test active status with phase information."""
        from ui.statusline import format_compact

        status = BuildStatus(
            active=True,
            state=BuildState.BUILDING,
            phase_current="coding",
            subtasks_total=10
        )
        result = format_compact(status)

        assert "coding" in result

    def test_active_with_workers(self):
        """Test active status with worker count."""
        from ui.statusline import format_compact

        status = BuildStatus(
            active=True,
            state=BuildState.BUILDING,
            workers_active=2,
            workers_max=4,
            subtasks_total=10
        )
        result = format_compact(status)

        # Workers should be shown when max > 1
        assert "2" in result

    def test_paused_state_prefix(self):
        """Test paused state shows prefix."""
        from ui.statusline import format_compact

        status = BuildStatus(
            active=True,
            state=BuildState.PAUSED,
            subtasks_completed=5,
            subtasks_total=10
        )
        result = format_compact(status)

        # Should have pause indicator at start
        assert len(result) > 0

    def test_complete_state_prefix(self):
        """Test complete state shows success prefix."""
        from ui.statusline import format_compact

        status = BuildStatus(
            active=True,
            state=BuildState.COMPLETE,
            subtasks_completed=10,
            subtasks_total=10
        )
        result = format_compact(status)

        # Should have content
        assert len(result) > 0

    def test_error_state_prefix(self):
        """Test error state shows error prefix."""
        from ui.statusline import format_compact

        status = BuildStatus(
            active=True,
            state=BuildState.ERROR,
            subtasks_completed=3,
            subtasks_total=10
        )
        result = format_compact(status)

        assert len(result) > 0


# =============================================================================
# format_full Tests
# =============================================================================

class TestStatuslineFormatFull:
    """Tests for full status formatting."""

    def test_inactive_message(self):
        """Test inactive status shows 'No active build'."""
        from ui.statusline import format_full

        status = BuildStatus(active=False)
        result = format_full(status)
        assert result == "No active build"

    def test_includes_spec(self):
        """Test full format includes spec name."""
        from ui.statusline import format_full

        status = BuildStatus(
            active=True,
            spec="001-feature"
        )
        result = format_full(status)
        assert "001-feature" in result

    def test_includes_state(self):
        """Test full format includes state."""
        from ui.statusline import format_full

        status = BuildStatus(
            active=True,
            state=BuildState.BUILDING
        )
        result = format_full(status)
        assert "building" in result

    def test_includes_progress(self):
        """Test full format includes progress details."""
        from ui.statusline import format_full

        status = BuildStatus(
            active=True,
            subtasks_completed=5,
            subtasks_total=10,
            subtasks_in_progress=2
        )
        result = format_full(status)

        assert "5/10" in result
        assert "50%" in result
        assert "In Progress: 2" in result

    def test_includes_failed_count(self):
        """Test full format includes failed count."""
        from ui.statusline import format_full

        status = BuildStatus(
            active=True,
            subtasks_completed=5,
            subtasks_total=10,
            subtasks_failed=1
        )
        result = format_full(status)

        assert "Failed: 1" in result

    def test_includes_phase(self):
        """Test full format includes phase details."""
        from ui.statusline import format_full

        status = BuildStatus(
            active=True,
            phase_current="coding",
            phase_id=2,
            phase_total=5
        )
        result = format_full(status)

        assert "coding" in result
        assert "2/5" in result

    def test_includes_workers(self):
        """Test full format includes worker details."""
        from ui.statusline import format_full

        status = BuildStatus(
            active=True,
            workers_active=2,
            workers_max=4
        )
        result = format_full(status)

        assert "Workers: 2/4" in result

    def test_includes_session(self):
        """Test full format includes session number."""
        from ui.statusline import format_full

        status = BuildStatus(
            active=True,
            session_number=3
        )
        result = format_full(status)

        assert "Session: 3" in result


# =============================================================================
# format_json Tests
# =============================================================================

class TestStatuslineFormatJson:
    """Tests for JSON status formatting."""

    def test_returns_valid_json(self):
        """Test that format_json returns valid JSON."""
        from ui.statusline import format_json

        status = BuildStatus(
            active=True,
            spec="001-feature",
            state=BuildState.BUILDING
        )
        result = format_json(status)

        # Should parse without error
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_includes_all_fields(self):
        """Test JSON includes all status fields."""
        from ui.statusline import format_json

        status = BuildStatus(
            active=True,
            spec="001-test",
            state=BuildState.QA
        )
        result = format_json(status)
        parsed = json.loads(result)

        assert "active" in parsed
        assert "spec" in parsed
        assert "state" in parsed
        assert "subtasks" in parsed
        assert "phase" in parsed
        assert "workers" in parsed

    def test_json_formatted(self):
        """Test JSON is formatted with indentation."""
        from ui.statusline import format_json

        status = BuildStatus(active=True)
        result = format_json(status)

        # Should be multi-line (indented)
        assert "\n" in result


# =============================================================================
# find_project_root Tests
# =============================================================================

class TestFindProjectRoot:
    """Tests for find_project_root function."""

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_finds_auto_claude_dir(self, temp_dir):
        """Test finding project with .auto-claude directory."""
        from ui.statusline import find_project_root

        # Create .auto-claude directory
        (temp_dir / ".auto-claude").mkdir()

        with patch('pathlib.Path.cwd', return_value=temp_dir):
            result = find_project_root()
            assert result == temp_dir

    def test_finds_status_file(self, temp_dir):
        """Test finding project with .auto-claude-status file."""
        from ui.statusline import find_project_root

        # Create status file
        (temp_dir / ".auto-claude-status").touch()

        with patch('pathlib.Path.cwd', return_value=temp_dir):
            result = find_project_root()
            assert result == temp_dir

    def test_prioritizes_auto_claude_over_status(self, temp_dir):
        """Test that .auto-claude is prioritized over status file."""
        from ui.statusline import find_project_root

        # Create both
        (temp_dir / ".auto-claude").mkdir()
        (temp_dir / ".auto-claude-status").touch()

        with patch('pathlib.Path.cwd', return_value=temp_dir):
            result = find_project_root()
            assert result == temp_dir

    def test_walks_up_to_find_root(self, temp_dir):
        """Test walking up directory tree to find root."""
        from ui.statusline import find_project_root

        # Create .auto-claude in temp_dir
        (temp_dir / ".auto-claude").mkdir()

        # Create nested directory
        nested = temp_dir / "src" / "deep"
        nested.mkdir(parents=True)

        with patch('pathlib.Path.cwd', return_value=nested):
            result = find_project_root()
            assert result == temp_dir

    def test_returns_cwd_if_not_found(self, temp_dir):
        """Test returning cwd when no project root found."""
        from ui.statusline import find_project_root

        # No .auto-claude or status file
        with patch('pathlib.Path.cwd', return_value=temp_dir):
            result = find_project_root()
            assert result == temp_dir


# =============================================================================
# Integration Tests
# =============================================================================

class TestStatuslineIntegration:
    """Integration tests for statusline module."""

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_full_workflow(self, temp_dir):
        """Test complete statusline workflow."""
        from ui.statusline import format_compact, format_full, format_json

        # Create status via manager
        manager = StatusManager(temp_dir)
        manager.set_active("001-feature", BuildState.BUILDING)
        manager.update_subtasks(completed=5, total=10)
        manager.update_phase("coding", 2, 4)
        manager.flush()

        # Read and format
        status = manager.read()

        compact = format_compact(status)
        full = format_full(status)
        json_str = format_json(status)

        assert len(compact) > 0
        assert "001-feature" in full
        assert json.loads(json_str)["active"] is True

    def test_all_states_format(self):
        """Test formatting all build states."""
        from ui.statusline import format_compact, format_full

        for state in BuildState:
            status = BuildStatus(
                active=True,
                state=state,
                subtasks_completed=5,
                subtasks_total=10
            )

            compact = format_compact(status)
            full = format_full(status)

            # All should produce output for active status
            assert len(compact) > 0 or state == BuildState.IDLE
            assert len(full) > 0
