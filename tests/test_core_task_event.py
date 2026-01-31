"""
Tests for the core task event module
=====================================

Tests covering core/task_event.py - Task event protocol for XState synchronization
"""

import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO
from datetime import datetime

from core.task_event import (
    TaskEventContext,
    TaskEventEmitter,
    load_task_event_context,
    _load_task_metadata,
    _load_last_sequence,
    TASK_EVENT_PREFIX,
)


# =============================================================================
# TaskEventContext Tests
# =============================================================================

class TestTaskEventContext:
    """Tests for TaskEventContext dataclass."""

    def test_basic_creation(self):
        """Test basic TaskEventContext creation."""
        ctx = TaskEventContext(
            task_id="task-123",
            spec_id="spec-456",
            project_id="proj-789"
        )
        assert ctx.task_id == "task-123"
        assert ctx.spec_id == "spec-456"
        assert ctx.project_id == "proj-789"

    def test_default_sequence_start(self):
        """Test default sequence_start value."""
        ctx = TaskEventContext(
            task_id="task",
            spec_id="spec",
            project_id="proj"
        )
        assert ctx.sequence_start == 0

    def test_custom_sequence_start(self):
        """Test custom sequence_start value."""
        ctx = TaskEventContext(
            task_id="task",
            spec_id="spec",
            project_id="proj",
            sequence_start=42
        )
        assert ctx.sequence_start == 42

    def test_equality(self):
        """Test TaskEventContext equality."""
        ctx1 = TaskEventContext("a", "b", "c", 0)
        ctx2 = TaskEventContext("a", "b", "c", 0)
        assert ctx1 == ctx2

    def test_inequality(self):
        """Test TaskEventContext inequality."""
        ctx1 = TaskEventContext("a", "b", "c", 0)
        ctx2 = TaskEventContext("a", "b", "c", 1)
        assert ctx1 != ctx2


# =============================================================================
# _load_task_metadata Tests
# =============================================================================

class TestLoadTaskMetadata:
    """Tests for _load_task_metadata function."""

    @pytest.fixture
    def temp_spec_dir(self):
        """Create a temporary spec directory."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_no_metadata_file(self, temp_spec_dir):
        """Test when metadata file doesn't exist."""
        result = _load_task_metadata(temp_spec_dir)
        assert result == {}

    def test_valid_metadata(self, temp_spec_dir):
        """Test loading valid metadata."""
        metadata = {
            "taskId": "task-abc",
            "specId": "spec-def",
            "projectId": "proj-ghi"
        }
        (temp_spec_dir / "task_metadata.json").write_text(json.dumps(metadata))

        result = _load_task_metadata(temp_spec_dir)
        assert result["taskId"] == "task-abc"
        assert result["specId"] == "spec-def"
        assert result["projectId"] == "proj-ghi"

    def test_invalid_json(self, temp_spec_dir):
        """Test with invalid JSON file."""
        (temp_spec_dir / "task_metadata.json").write_text("not valid json {{{")

        result = _load_task_metadata(temp_spec_dir)
        assert result == {}

    def test_empty_file(self, temp_spec_dir):
        """Test with empty file."""
        (temp_spec_dir / "task_metadata.json").write_text("")

        result = _load_task_metadata(temp_spec_dir)
        assert result == {}

    def test_snake_case_keys(self, temp_spec_dir):
        """Test with snake_case keys."""
        metadata = {
            "task_id": "task-snake",
            "spec_id": "spec-snake",
            "project_id": "proj-snake"
        }
        (temp_spec_dir / "task_metadata.json").write_text(json.dumps(metadata))

        result = _load_task_metadata(temp_spec_dir)
        assert result["task_id"] == "task-snake"


# =============================================================================
# _load_last_sequence Tests
# =============================================================================

class TestLoadLastSequence:
    """Tests for _load_last_sequence function."""

    @pytest.fixture
    def temp_spec_dir(self):
        """Create a temporary spec directory."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_no_plan_file(self, temp_spec_dir):
        """Test when implementation plan doesn't exist."""
        result = _load_last_sequence(temp_spec_dir)
        assert result == 0

    def test_plan_without_last_event(self, temp_spec_dir):
        """Test plan without lastEvent field."""
        plan = {"subtasks": [], "status": "pending"}
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        result = _load_last_sequence(temp_spec_dir)
        assert result == 0

    def test_plan_with_last_event(self, temp_spec_dir):
        """Test plan with lastEvent containing sequence."""
        plan = {
            "lastEvent": {"sequence": 10, "type": "progress"}
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        result = _load_last_sequence(temp_spec_dir)
        assert result == 11  # Next sequence

    def test_plan_with_zero_sequence(self, temp_spec_dir):
        """Test plan with sequence 0."""
        plan = {"lastEvent": {"sequence": 0}}
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        result = _load_last_sequence(temp_spec_dir)
        assert result == 1

    def test_plan_with_null_last_event(self, temp_spec_dir):
        """Test plan with null lastEvent."""
        plan = {"lastEvent": None}
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        result = _load_last_sequence(temp_spec_dir)
        assert result == 0

    def test_invalid_json(self, temp_spec_dir):
        """Test with invalid JSON."""
        (temp_spec_dir / "implementation_plan.json").write_text("invalid json")

        result = _load_last_sequence(temp_spec_dir)
        assert result == 0


# =============================================================================
# load_task_event_context Tests
# =============================================================================

class TestLoadTaskEventContext:
    """Tests for load_task_event_context function."""

    @pytest.fixture
    def temp_spec_dir(self):
        """Create a temporary spec directory."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_no_files(self, temp_spec_dir):
        """Test with no metadata or plan files."""
        ctx = load_task_event_context(temp_spec_dir)

        # Should use spec_dir name as fallback
        assert ctx.task_id == temp_spec_dir.name
        assert ctx.spec_id == temp_spec_dir.name
        assert ctx.project_id == ""
        assert ctx.sequence_start == 0

    def test_with_metadata(self, temp_spec_dir):
        """Test loading context from metadata."""
        metadata = {
            "taskId": "my-task",
            "specId": "my-spec",
            "projectId": "my-project"
        }
        (temp_spec_dir / "task_metadata.json").write_text(json.dumps(metadata))

        ctx = load_task_event_context(temp_spec_dir)
        assert ctx.task_id == "my-task"
        assert ctx.spec_id == "my-spec"
        assert ctx.project_id == "my-project"

    def test_with_plan_sequence(self, temp_spec_dir):
        """Test loading sequence from implementation plan."""
        plan = {"lastEvent": {"sequence": 5}}
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        ctx = load_task_event_context(temp_spec_dir)
        assert ctx.sequence_start == 6

    def test_combined_metadata_and_plan(self, temp_spec_dir):
        """Test loading from both metadata and plan."""
        metadata = {"taskId": "combined-task", "specId": "combined-spec"}
        plan = {"lastEvent": {"sequence": 100}}

        (temp_spec_dir / "task_metadata.json").write_text(json.dumps(metadata))
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        ctx = load_task_event_context(temp_spec_dir)
        assert ctx.task_id == "combined-task"
        assert ctx.spec_id == "combined-spec"
        assert ctx.sequence_start == 101


# =============================================================================
# TaskEventEmitter Tests
# =============================================================================

class TestTaskEventEmitter:
    """Tests for TaskEventEmitter class."""

    def test_init(self):
        """Test TaskEventEmitter initialization."""
        ctx = TaskEventContext("task", "spec", "proj", 0)
        emitter = TaskEventEmitter(ctx)

        assert emitter._context == ctx
        assert emitter._sequence == 0

    def test_init_with_sequence_start(self):
        """Test initialization respects sequence_start."""
        ctx = TaskEventContext("task", "spec", "proj", 50)
        emitter = TaskEventEmitter(ctx)

        assert emitter._sequence == 50

    def test_from_spec_dir(self):
        """Test creating emitter from spec directory."""
        with tempfile.TemporaryDirectory() as td:
            spec_dir = Path(td)
            metadata = {"taskId": "from-dir", "specId": "spec-from-dir"}
            (spec_dir / "task_metadata.json").write_text(json.dumps(metadata))

            emitter = TaskEventEmitter.from_spec_dir(spec_dir)
            assert emitter._context.task_id == "from-dir"

    def test_emit_basic(self, capsys):
        """Test basic event emission."""
        ctx = TaskEventContext("t", "s", "p", 0)
        emitter = TaskEventEmitter(ctx)

        emitter.emit("test_event")

        captured = capsys.readouterr()
        assert TASK_EVENT_PREFIX in captured.out
        assert "test_event" in captured.out

    def test_emit_with_payload(self, capsys):
        """Test event emission with payload."""
        ctx = TaskEventContext("t", "s", "p", 0)
        emitter = TaskEventEmitter(ctx)

        emitter.emit("progress", {"percent": 50, "message": "Halfway"})

        captured = capsys.readouterr()
        output = captured.out
        assert TASK_EVENT_PREFIX in output

        # Parse the JSON from output
        json_str = output.replace(TASK_EVENT_PREFIX, "").strip()
        event = json.loads(json_str)
        assert event["percent"] == 50
        assert event["message"] == "Halfway"

    def test_emit_increments_sequence(self, capsys):
        """Test that emit increments sequence."""
        ctx = TaskEventContext("t", "s", "p", 0)
        emitter = TaskEventEmitter(ctx)

        emitter.emit("event1")
        assert emitter._sequence == 1

        emitter.emit("event2")
        assert emitter._sequence == 2

        emitter.emit("event3")
        assert emitter._sequence == 3

    def test_emit_includes_context_fields(self, capsys):
        """Test that emitted event includes context fields."""
        ctx = TaskEventContext("task-id-123", "spec-id-456", "proj-id-789", 5)
        emitter = TaskEventEmitter(ctx)

        emitter.emit("test")

        captured = capsys.readouterr()
        json_str = captured.out.replace(TASK_EVENT_PREFIX, "").strip()
        event = json.loads(json_str)

        assert event["taskId"] == "task-id-123"
        assert event["specId"] == "spec-id-456"
        assert event["projectId"] == "proj-id-789"
        assert event["sequence"] == 5

    def test_emit_includes_timestamp(self, capsys):
        """Test that emitted event includes timestamp."""
        ctx = TaskEventContext("t", "s", "p", 0)
        emitter = TaskEventEmitter(ctx)

        emitter.emit("test")

        captured = capsys.readouterr()
        json_str = captured.out.replace(TASK_EVENT_PREFIX, "").strip()
        event = json.loads(json_str)

        assert "timestamp" in event
        # Should be ISO format
        datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))

    def test_emit_includes_event_id(self, capsys):
        """Test that emitted event includes unique eventId."""
        ctx = TaskEventContext("t", "s", "p", 0)
        emitter = TaskEventEmitter(ctx)

        emitter.emit("test1")
        emitter.emit("test2")

        captured = capsys.readouterr()
        lines = [l for l in captured.out.strip().split("\n") if l]

        event_ids = []
        for line in lines:
            json_str = line.replace(TASK_EVENT_PREFIX, "")
            event = json.loads(json_str)
            event_ids.append(event["eventId"])

        # All event IDs should be unique
        assert len(event_ids) == len(set(event_ids))

    def test_emit_handles_os_error(self):
        """Test that emit handles OSError gracefully."""
        ctx = TaskEventContext("t", "s", "p", 0)
        emitter = TaskEventEmitter(ctx)

        with patch('builtins.print', side_effect=OSError("Write error")):
            # Should not raise
            emitter.emit("test")

        # Sequence should not increment on error
        assert emitter._sequence == 0


# =============================================================================
# Integration Tests
# =============================================================================

class TestTaskEventIntegration:
    """Integration tests for task event module."""

    def test_full_workflow(self, capsys):
        """Test complete task event workflow."""
        with tempfile.TemporaryDirectory() as td:
            spec_dir = Path(td)

            # Setup metadata and plan
            metadata = {
                "taskId": "integration-task",
                "specId": "integration-spec",
                "projectId": "integration-project"
            }
            plan = {"lastEvent": {"sequence": 10}}

            (spec_dir / "task_metadata.json").write_text(json.dumps(metadata))
            (spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

            # Load context and create emitter
            emitter = TaskEventEmitter.from_spec_dir(spec_dir)

            # Emit several events
            emitter.emit("started", {"phase": "planning"})
            emitter.emit("progress", {"percent": 25})
            emitter.emit("progress", {"percent": 50})
            emitter.emit("progress", {"percent": 75})
            emitter.emit("completed", {"result": "success"})

            captured = capsys.readouterr()
            lines = [l for l in captured.out.strip().split("\n") if l]

            # Should have 5 events
            assert len(lines) == 5

            # Parse all events
            events = []
            for line in lines:
                json_str = line.replace(TASK_EVENT_PREFIX, "")
                events.append(json.loads(json_str))

            # Check sequence progression (started at 11)
            sequences = [e["sequence"] for e in events]
            assert sequences == [11, 12, 13, 14, 15]

            # Check event types
            types = [e["type"] for e in events]
            assert types == ["started", "progress", "progress", "progress", "completed"]

    def test_event_prefix_format(self, capsys):
        """Test that event prefix is correct."""
        ctx = TaskEventContext("t", "s", "p", 0)
        emitter = TaskEventEmitter(ctx)

        emitter.emit("test")

        captured = capsys.readouterr()
        assert captured.out.startswith(TASK_EVENT_PREFIX)
        assert TASK_EVENT_PREFIX == "__TASK_EVENT__:"

    def test_payload_merged_with_event(self, capsys):
        """Test that payload is merged with event."""
        ctx = TaskEventContext("t", "s", "p", 0)
        emitter = TaskEventEmitter(ctx)

        # Emit with complex payload
        emitter.emit("complex", {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "number": 42
        })

        captured = capsys.readouterr()
        json_str = captured.out.replace(TASK_EVENT_PREFIX, "").strip()
        event = json.loads(json_str)

        # Core fields present
        assert event["type"] == "complex"
        assert event["taskId"] == "t"

        # Payload merged
        assert event["nested"]["key"] == "value"
        assert event["list"] == [1, 2, 3]
        assert event["number"] == 42
