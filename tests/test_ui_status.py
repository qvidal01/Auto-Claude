"""
Tests for the UI status module
===============================

Tests covering ui/status.py - BuildState, BuildStatus, StatusManager
"""

import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from ui.status import BuildState, BuildStatus, StatusManager


# =============================================================================
# BuildState Tests
# =============================================================================

class TestBuildState:
    """Tests for BuildState enum."""

    def test_all_states_exist(self):
        """Test that all expected build states exist."""
        expected_states = ["IDLE", "PLANNING", "BUILDING", "QA", "COMPLETE", "PAUSED", "ERROR"]
        for state in expected_states:
            assert hasattr(BuildState, state)

    def test_state_values(self):
        """Test state string values."""
        assert BuildState.IDLE.value == "idle"
        assert BuildState.PLANNING.value == "planning"
        assert BuildState.BUILDING.value == "building"
        assert BuildState.QA.value == "qa"
        assert BuildState.COMPLETE.value == "complete"
        assert BuildState.PAUSED.value == "paused"
        assert BuildState.ERROR.value == "error"

    def test_state_from_value(self):
        """Test creating state from string value."""
        assert BuildState("idle") == BuildState.IDLE
        assert BuildState("building") == BuildState.BUILDING
        assert BuildState("error") == BuildState.ERROR


# =============================================================================
# BuildStatus Tests
# =============================================================================

class TestBuildStatus:
    """Tests for BuildStatus dataclass."""

    def test_default_values(self):
        """Test default BuildStatus values."""
        status = BuildStatus()
        assert status.active is False
        assert status.spec == ""
        assert status.state == BuildState.IDLE
        assert status.subtasks_completed == 0
        assert status.subtasks_total == 0
        assert status.subtasks_in_progress == 0
        assert status.subtasks_failed == 0
        assert status.phase_current == ""
        assert status.phase_id == 0
        assert status.phase_total == 0
        assert status.workers_active == 0
        assert status.workers_max == 1
        assert status.session_number == 0

    def test_custom_values(self):
        """Test BuildStatus with custom values."""
        status = BuildStatus(
            active=True,
            spec="001-feature",
            state=BuildState.BUILDING,
            subtasks_completed=3,
            subtasks_total=10,
            subtasks_in_progress=2,
            workers_active=2,
            workers_max=4,
            phase_current="coding",
            phase_id=2,
            phase_total=5
        )
        assert status.active is True
        assert status.spec == "001-feature"
        assert status.state == BuildState.BUILDING
        assert status.subtasks_completed == 3
        assert status.subtasks_total == 10
        assert status.workers_active == 2
        assert status.workers_max == 4

    def test_to_dict(self):
        """Test converting BuildStatus to dictionary."""
        status = BuildStatus(
            active=True,
            spec="001-feature",
            state=BuildState.BUILDING,
            subtasks_completed=5,
            subtasks_total=10,
            subtasks_in_progress=2,
            subtasks_failed=1,
            phase_current="coding",
            phase_id=3,
            phase_total=5,
            workers_active=2,
            workers_max=4,
            session_number=1
        )

        result = status.to_dict()

        assert result["active"] is True
        assert result["spec"] == "001-feature"
        assert result["state"] == "building"
        assert result["subtasks"]["completed"] == 5
        assert result["subtasks"]["total"] == 10
        assert result["subtasks"]["in_progress"] == 2
        assert result["subtasks"]["failed"] == 1
        assert result["phase"]["current"] == "coding"
        assert result["phase"]["id"] == 3
        assert result["phase"]["total"] == 5
        assert result["workers"]["active"] == 2
        assert result["workers"]["max"] == 4
        assert result["session"]["number"] == 1
        assert "last_update" in result

    def test_from_dict(self):
        """Test creating BuildStatus from dictionary."""
        data = {
            "active": True,
            "spec": "002-bugfix",
            "state": "qa",
            "subtasks": {
                "completed": 8,
                "total": 10,
                "in_progress": 1,
                "failed": 0
            },
            "phase": {
                "current": "validation",
                "id": 4,
                "total": 5
            },
            "workers": {
                "active": 1,
                "max": 2
            },
            "session": {
                "number": 3,
                "started_at": "2025-01-01T12:00:00"
            },
            "last_update": "2025-01-01T12:30:00"
        }

        status = BuildStatus.from_dict(data)

        assert status.active is True
        assert status.spec == "002-bugfix"
        assert status.state == BuildState.QA
        assert status.subtasks_completed == 8
        assert status.subtasks_total == 10
        assert status.subtasks_in_progress == 1
        assert status.subtasks_failed == 0
        assert status.phase_current == "validation"
        assert status.phase_id == 4
        assert status.phase_total == 5
        assert status.workers_active == 1
        assert status.workers_max == 2
        assert status.session_number == 3

    def test_from_dict_with_defaults(self):
        """Test from_dict with missing fields uses defaults."""
        data = {"active": True}
        status = BuildStatus.from_dict(data)

        assert status.active is True
        assert status.spec == ""
        assert status.state == BuildState.IDLE
        assert status.subtasks_completed == 0

    def test_from_dict_empty(self):
        """Test from_dict with empty dictionary."""
        status = BuildStatus.from_dict({})

        assert status.active is False
        assert status.state == BuildState.IDLE

    def test_roundtrip(self):
        """Test to_dict and from_dict roundtrip."""
        original = BuildStatus(
            active=True,
            spec="test-spec",
            state=BuildState.COMPLETE,
            subtasks_completed=10,
            subtasks_total=10,
            phase_current="done",
            workers_active=0,
            workers_max=4
        )

        data = original.to_dict()
        restored = BuildStatus.from_dict(data)

        assert restored.active == original.active
        assert restored.spec == original.spec
        assert restored.state == original.state
        assert restored.subtasks_completed == original.subtasks_completed
        assert restored.subtasks_total == original.subtasks_total
        assert restored.phase_current == original.phase_current


# =============================================================================
# StatusManager Tests
# =============================================================================

class TestStatusManager:
    """Tests for StatusManager."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a StatusManager with a temp directory."""
        return StatusManager(temp_dir)

    def test_init(self, temp_dir):
        """Test StatusManager initialization."""
        manager = StatusManager(temp_dir)
        assert manager.project_dir == temp_dir
        assert manager.status_file == temp_dir / ".auto-claude-status"

    def test_read_nonexistent(self, manager):
        """Test reading when status file doesn't exist."""
        status = manager.read()
        assert status.active is False
        assert status.state == BuildState.IDLE

    def test_write_and_read(self, manager, temp_dir):
        """Test writing and reading status."""
        status = BuildStatus(
            active=True,
            spec="001-test",
            state=BuildState.BUILDING,
            subtasks_completed=5,
            subtasks_total=10
        )

        manager.write(status, immediate=True)

        # Verify file exists
        assert manager.status_file.exists()

        # Read back
        read_status = manager.read()
        assert read_status.active is True
        assert read_status.spec == "001-test"
        assert read_status.state == BuildState.BUILDING

    def test_update(self, manager):
        """Test updating specific fields."""
        # Set initial status
        manager.write(BuildStatus(active=True, spec="test"), immediate=True)

        # Update specific fields
        manager.update(subtasks_completed=3, subtasks_total=10)
        manager.flush()

        # Read back
        status = manager.read()
        assert status.subtasks_completed == 3
        assert status.subtasks_total == 10

    def test_set_active(self, manager):
        """Test setting build as active."""
        manager.set_active("001-feature", BuildState.BUILDING)

        status = manager.read()
        assert status.active is True
        assert status.spec == "001-feature"
        assert status.state == BuildState.BUILDING
        assert status.session_started != ""

    def test_set_inactive(self, manager):
        """Test setting build as inactive."""
        manager.set_active("001-feature", BuildState.BUILDING)
        manager.set_inactive()

        status = manager.read()
        assert status.active is False
        assert status.state == BuildState.IDLE

    def test_update_subtasks(self, manager):
        """Test updating subtask progress."""
        manager.write(BuildStatus(active=True), immediate=True)

        manager.update_subtasks(completed=5, total=10, in_progress=2, failed=1)
        manager.flush()

        status = manager.read()
        assert status.subtasks_completed == 5
        assert status.subtasks_total == 10
        assert status.subtasks_in_progress == 2
        assert status.subtasks_failed == 1

    def test_update_phase(self, manager):
        """Test updating phase information."""
        manager.write(BuildStatus(active=True), immediate=True)

        manager.update_phase("coding", phase_id=2, total=5)
        manager.flush()

        status = manager.read()
        assert status.phase_current == "coding"
        assert status.phase_id == 2
        assert status.phase_total == 5

    def test_update_workers(self, manager):
        """Test updating worker count."""
        manager.write(BuildStatus(active=True), immediate=True)

        manager.update_workers(active=3, max_workers=4)
        manager.flush()

        status = manager.read()
        assert status.workers_active == 3
        assert status.workers_max == 4

    def test_update_session(self, manager):
        """Test updating session number."""
        manager.write(BuildStatus(active=True), immediate=True)

        manager.update_session(5)
        manager.flush()

        status = manager.read()
        assert status.session_number == 5

    def test_clear(self, manager):
        """Test clearing status file."""
        manager.write(BuildStatus(active=True, spec="test"), immediate=True)
        assert manager.status_file.exists()

        manager.clear()
        assert not manager.status_file.exists()

    def test_clear_nonexistent(self, manager):
        """Test clearing when file doesn't exist."""
        # Should not raise
        manager.clear()

    def test_flush(self, manager):
        """Test flushing pending writes."""
        manager.write(BuildStatus(active=True, spec="test"))
        manager.flush()

        # File should exist and be written
        assert manager.status_file.exists()
        status = manager.read()
        assert status.active is True

    def test_read_invalid_json(self, manager, temp_dir):
        """Test reading corrupted status file."""
        # Write invalid JSON
        status_file = temp_dir / ".auto-claude-status"
        status_file.write_text("not valid json")

        status = manager.read()
        # Should return default status on error
        assert status.active is False
        assert status.state == BuildState.IDLE


# =============================================================================
# Integration Tests
# =============================================================================

class TestStatusIntegration:
    """Integration tests for status management."""

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_full_build_workflow(self, temp_dir):
        """Test a full build workflow with status updates."""
        manager = StatusManager(temp_dir)

        # Start build
        manager.set_active("001-feature", BuildState.PLANNING)
        status = manager.read()
        assert status.active is True
        assert status.state == BuildState.PLANNING

        # Move to building
        manager.update(state=BuildState.BUILDING)
        manager.update_subtasks(total=10)
        manager.update_workers(active=2, max_workers=4)
        manager.flush()

        status = manager.read()
        assert status.state == BuildState.BUILDING
        assert status.subtasks_total == 10
        assert status.workers_active == 2

        # Progress through subtasks
        for i in range(1, 11):
            manager.update_subtasks(completed=i)
            manager.flush()

        status = manager.read()
        assert status.subtasks_completed == 10

        # Move to QA
        manager.update(state=BuildState.QA)
        manager.flush()
        status = manager.read()
        assert status.state == BuildState.QA

        # Complete
        manager.update(state=BuildState.COMPLETE)
        manager.set_inactive()

        status = manager.read()
        assert status.active is False

    def test_status_file_format(self, temp_dir):
        """Test that status file is valid JSON with expected structure."""
        manager = StatusManager(temp_dir)
        manager.set_active("001-test", BuildState.BUILDING)
        manager.update_subtasks(completed=5, total=10)
        manager.update_phase("coding", 2, 5)
        manager.flush()

        # Read file directly
        with open(temp_dir / ".auto-claude-status") as f:
            data = json.load(f)

        # Check structure
        assert "active" in data
        assert "spec" in data
        assert "state" in data
        assert "subtasks" in data
        assert "phase" in data
        assert "workers" in data
        assert "session" in data
        assert "last_update" in data

        # Check nested structures
        assert "completed" in data["subtasks"]
        assert "total" in data["subtasks"]
        assert "current" in data["phase"]
