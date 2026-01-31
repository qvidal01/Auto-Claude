"""
Tests for the core progress module
===================================

Tests covering core/progress.py - Progress tracking utilities
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from core.progress import (
    count_subtasks,
    count_subtasks_detailed,
    is_build_complete,
    get_progress_percentage,
    get_plan_summary,
    get_current_phase,
    get_next_subtask,
    format_duration,
)


# =============================================================================
# count_subtasks Tests
# =============================================================================

class TestCountSubtasks:
    """Tests for count_subtasks function."""

    @pytest.fixture
    def temp_spec_dir(self):
        """Create a temporary spec directory."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_no_plan_file(self, temp_spec_dir):
        """Test with no implementation plan."""
        completed, total = count_subtasks(temp_spec_dir)
        assert completed == 0
        assert total == 0

    def test_empty_plan(self, temp_spec_dir):
        """Test with empty phases."""
        plan = {"phases": []}
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        completed, total = count_subtasks(temp_spec_dir)
        assert completed == 0
        assert total == 0

    def test_all_pending(self, temp_spec_dir):
        """Test with all subtasks pending."""
        plan = {
            "phases": [
                {"id": "1", "subtasks": [
                    {"id": "1.1", "status": "pending"},
                    {"id": "1.2", "status": "pending"},
                ]}
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        completed, total = count_subtasks(temp_spec_dir)
        assert completed == 0
        assert total == 2

    def test_some_completed(self, temp_spec_dir):
        """Test with some subtasks completed."""
        plan = {
            "phases": [
                {"id": "1", "subtasks": [
                    {"id": "1.1", "status": "completed"},
                    {"id": "1.2", "status": "pending"},
                    {"id": "1.3", "status": "completed"},
                ]}
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        completed, total = count_subtasks(temp_spec_dir)
        assert completed == 2
        assert total == 3

    def test_all_completed(self, temp_spec_dir):
        """Test with all subtasks completed."""
        plan = {
            "phases": [
                {"id": "1", "subtasks": [
                    {"id": "1.1", "status": "completed"},
                    {"id": "1.2", "status": "completed"},
                ]}
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        completed, total = count_subtasks(temp_spec_dir)
        assert completed == 2
        assert total == 2

    def test_multiple_phases(self, temp_spec_dir):
        """Test counting across multiple phases."""
        plan = {
            "phases": [
                {"id": "1", "subtasks": [
                    {"id": "1.1", "status": "completed"},
                ]},
                {"id": "2", "subtasks": [
                    {"id": "2.1", "status": "pending"},
                    {"id": "2.2", "status": "completed"},
                ]},
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        completed, total = count_subtasks(temp_spec_dir)
        assert completed == 2
        assert total == 3

    def test_invalid_json(self, temp_spec_dir):
        """Test with invalid JSON file."""
        (temp_spec_dir / "implementation_plan.json").write_text("not valid json")

        completed, total = count_subtasks(temp_spec_dir)
        assert completed == 0
        assert total == 0


# =============================================================================
# count_subtasks_detailed Tests
# =============================================================================

class TestCountSubtasksDetailed:
    """Tests for count_subtasks_detailed function."""

    @pytest.fixture
    def temp_spec_dir(self):
        """Create a temporary spec directory."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_no_plan_file(self, temp_spec_dir):
        """Test with no implementation plan."""
        result = count_subtasks_detailed(temp_spec_dir)
        assert result["completed"] == 0
        assert result["in_progress"] == 0
        assert result["pending"] == 0
        assert result["failed"] == 0
        assert result["total"] == 0

    def test_all_statuses(self, temp_spec_dir):
        """Test counting all status types."""
        plan = {
            "phases": [
                {"id": "1", "subtasks": [
                    {"id": "1.1", "status": "completed"},
                    {"id": "1.2", "status": "in_progress"},
                    {"id": "1.3", "status": "pending"},
                    {"id": "1.4", "status": "failed"},
                ]}
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        result = count_subtasks_detailed(temp_spec_dir)
        assert result["completed"] == 1
        assert result["in_progress"] == 1
        assert result["pending"] == 1
        assert result["failed"] == 1
        assert result["total"] == 4

    def test_unknown_status_counts_as_pending(self, temp_spec_dir):
        """Test that unknown status counts as pending."""
        plan = {
            "phases": [
                {"id": "1", "subtasks": [
                    {"id": "1.1", "status": "unknown_status"},
                ]}
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        result = count_subtasks_detailed(temp_spec_dir)
        assert result["pending"] == 1
        assert result["total"] == 1

    def test_missing_status_defaults_to_pending(self, temp_spec_dir):
        """Test that missing status defaults to pending."""
        plan = {
            "phases": [
                {"id": "1", "subtasks": [
                    {"id": "1.1"},  # No status key
                ]}
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        result = count_subtasks_detailed(temp_spec_dir)
        assert result["pending"] == 1


# =============================================================================
# is_build_complete Tests
# =============================================================================

class TestIsBuildComplete:
    """Tests for is_build_complete function."""

    @pytest.fixture
    def temp_spec_dir(self):
        """Create a temporary spec directory."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_no_plan(self, temp_spec_dir):
        """Test with no plan file."""
        assert is_build_complete(temp_spec_dir) is False

    def test_all_completed(self, temp_spec_dir):
        """Test when all subtasks are completed."""
        plan = {
            "phases": [
                {"id": "1", "subtasks": [
                    {"id": "1.1", "status": "completed"},
                    {"id": "1.2", "status": "completed"},
                ]}
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        assert is_build_complete(temp_spec_dir) is True

    def test_some_pending(self, temp_spec_dir):
        """Test when some subtasks are pending."""
        plan = {
            "phases": [
                {"id": "1", "subtasks": [
                    {"id": "1.1", "status": "completed"},
                    {"id": "1.2", "status": "pending"},
                ]}
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        assert is_build_complete(temp_spec_dir) is False

    def test_empty_plan(self, temp_spec_dir):
        """Test with empty phases."""
        plan = {"phases": []}
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        assert is_build_complete(temp_spec_dir) is False


# =============================================================================
# get_progress_percentage Tests
# =============================================================================

class TestGetProgressPercentage:
    """Tests for get_progress_percentage function."""

    @pytest.fixture
    def temp_spec_dir(self):
        """Create a temporary spec directory."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_no_plan(self, temp_spec_dir):
        """Test with no plan file."""
        assert get_progress_percentage(temp_spec_dir) == 0.0

    def test_zero_progress(self, temp_spec_dir):
        """Test with no completed subtasks."""
        plan = {
            "phases": [
                {"id": "1", "subtasks": [
                    {"id": "1.1", "status": "pending"},
                    {"id": "1.2", "status": "pending"},
                ]}
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        assert get_progress_percentage(temp_spec_dir) == 0.0

    def test_partial_progress(self, temp_spec_dir):
        """Test with partial progress."""
        plan = {
            "phases": [
                {"id": "1", "subtasks": [
                    {"id": "1.1", "status": "completed"},
                    {"id": "1.2", "status": "pending"},
                ]}
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        assert get_progress_percentage(temp_spec_dir) == 50.0

    def test_complete_progress(self, temp_spec_dir):
        """Test with complete progress."""
        plan = {
            "phases": [
                {"id": "1", "subtasks": [
                    {"id": "1.1", "status": "completed"},
                    {"id": "1.2", "status": "completed"},
                ]}
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        assert get_progress_percentage(temp_spec_dir) == 100.0


# =============================================================================
# get_plan_summary Tests
# =============================================================================

class TestGetPlanSummary:
    """Tests for get_plan_summary function."""

    @pytest.fixture
    def temp_spec_dir(self):
        """Create a temporary spec directory."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_no_plan_file(self, temp_spec_dir):
        """Test with no plan file."""
        summary = get_plan_summary(temp_spec_dir)
        assert summary["total_phases"] == 0
        assert summary["total_subtasks"] == 0

    def test_full_summary(self, temp_spec_dir):
        """Test complete summary."""
        plan = {
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "1",
                    "name": "Setup",
                    "depends_on": [],
                    "subtasks": [
                        {"id": "1.1", "description": "First", "status": "completed", "service": "core"},
                        {"id": "1.2", "description": "Second", "status": "in_progress", "service": "api"},
                    ]
                },
                {
                    "id": "2",
                    "name": "Implementation",
                    "depends_on": ["1"],
                    "subtasks": [
                        {"id": "2.1", "description": "Third", "status": "pending"},
                        {"id": "2.2", "description": "Fourth", "status": "failed"},
                    ]
                }
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        summary = get_plan_summary(temp_spec_dir)

        assert summary["workflow_type"] == "feature"
        assert summary["total_phases"] == 2
        assert summary["total_subtasks"] == 4
        assert summary["completed_subtasks"] == 1
        assert summary["in_progress_subtasks"] == 1
        assert summary["pending_subtasks"] == 1
        assert summary["failed_subtasks"] == 1
        assert len(summary["phases"]) == 2


# =============================================================================
# get_current_phase Tests
# =============================================================================

class TestGetCurrentPhase:
    """Tests for get_current_phase function."""

    @pytest.fixture
    def temp_spec_dir(self):
        """Create a temporary spec directory."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_no_plan(self, temp_spec_dir):
        """Test with no plan file."""
        result = get_current_phase(temp_spec_dir)
        assert result is None

    def test_first_phase_in_progress(self, temp_spec_dir):
        """Test when first phase is in progress."""
        plan = {
            "phases": [
                {"id": "1", "name": "Setup", "subtasks": [
                    {"id": "1.1", "status": "completed"},
                    {"id": "1.2", "status": "pending"},
                ]}
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        result = get_current_phase(temp_spec_dir)
        assert result is not None
        assert result["name"] == "Setup"
        assert result["completed"] == 1
        assert result["total"] == 2

    def test_second_phase_current(self, temp_spec_dir):
        """Test when second phase is current."""
        plan = {
            "phases": [
                {"id": "1", "name": "Setup", "subtasks": [
                    {"id": "1.1", "status": "completed"},
                ]},
                {"id": "2", "name": "Build", "subtasks": [
                    {"id": "2.1", "status": "pending"},
                ]}
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        result = get_current_phase(temp_spec_dir)
        assert result["name"] == "Build"

    def test_all_complete(self, temp_spec_dir):
        """Test when all phases are complete."""
        plan = {
            "phases": [
                {"id": "1", "name": "Setup", "subtasks": [
                    {"id": "1.1", "status": "completed"},
                ]}
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        result = get_current_phase(temp_spec_dir)
        assert result is None


# =============================================================================
# get_next_subtask Tests
# =============================================================================

class TestGetNextSubtask:
    """Tests for get_next_subtask function."""

    @pytest.fixture
    def temp_spec_dir(self):
        """Create a temporary spec directory."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_no_plan(self, temp_spec_dir):
        """Test with no plan file."""
        result = get_next_subtask(temp_spec_dir)
        assert result is None

    def test_first_pending_subtask(self, temp_spec_dir):
        """Test finding first pending subtask."""
        plan = {
            "phases": [
                {"id": "1", "name": "Setup", "subtasks": [
                    {"id": "1.1", "description": "First task", "status": "pending"},
                    {"id": "1.2", "description": "Second task", "status": "pending"},
                ]}
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        result = get_next_subtask(temp_spec_dir)
        assert result is not None
        assert result["id"] == "1.1"
        assert result["description"] == "First task"

    def test_skips_completed(self, temp_spec_dir):
        """Test that completed subtasks are skipped."""
        plan = {
            "phases": [
                {"id": "1", "name": "Setup", "subtasks": [
                    {"id": "1.1", "status": "completed"},
                    {"id": "1.2", "status": "pending"},
                ]}
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        result = get_next_subtask(temp_spec_dir)
        assert result["id"] == "1.2"

    def test_respects_dependencies(self, temp_spec_dir):
        """Test that phase dependencies are respected."""
        plan = {
            "phases": [
                {"id": "1", "name": "Setup", "depends_on": [], "subtasks": [
                    {"id": "1.1", "status": "pending"},
                ]},
                {"id": "2", "name": "Build", "depends_on": ["1"], "subtasks": [
                    {"id": "2.1", "status": "pending"},
                ]}
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        result = get_next_subtask(temp_spec_dir)
        # Should return from first phase since phase 2 depends on phase 1
        assert result["id"] == "1.1"

    def test_moves_to_next_phase(self, temp_spec_dir):
        """Test moving to next phase when current is complete."""
        plan = {
            "phases": [
                {"id": "1", "name": "Setup", "depends_on": [], "subtasks": [
                    {"id": "1.1", "status": "completed"},
                ]},
                {"id": "2", "name": "Build", "depends_on": ["1"], "subtasks": [
                    {"id": "2.1", "status": "pending"},
                ]}
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        result = get_next_subtask(temp_spec_dir)
        # Should return from second phase since first is complete
        assert result["id"] == "2.1"

    def test_all_complete(self, temp_spec_dir):
        """Test when all subtasks are complete."""
        plan = {
            "phases": [
                {"id": "1", "subtasks": [
                    {"id": "1.1", "status": "completed"},
                ]}
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        result = get_next_subtask(temp_spec_dir)
        assert result is None


# =============================================================================
# format_duration Tests
# =============================================================================

class TestFormatDuration:
    """Tests for format_duration function."""

    def test_seconds(self):
        """Test formatting seconds."""
        assert format_duration(30) == "30s"
        assert format_duration(59) == "59s"

    def test_minutes(self):
        """Test formatting minutes."""
        assert format_duration(60) == "1.0m"
        assert format_duration(90) == "1.5m"
        assert format_duration(120) == "2.0m"

    def test_hours(self):
        """Test formatting hours."""
        assert format_duration(3600) == "1.0h"
        assert format_duration(5400) == "1.5h"
        assert format_duration(7200) == "2.0h"

    def test_edge_cases(self):
        """Test edge cases."""
        assert format_duration(0) == "0s"
        assert format_duration(59.9) == "60s"
        assert format_duration(3599) == "60.0m"


# =============================================================================
# Integration Tests
# =============================================================================

class TestProgressIntegration:
    """Integration tests for progress module."""

    def test_complete_workflow(self):
        """Test complete progress tracking workflow."""
        with tempfile.TemporaryDirectory() as td:
            spec_dir = Path(td)

            # Create initial plan
            plan = {
                "workflow_type": "feature",
                "phases": [
                    {
                        "id": "1",
                        "name": "Setup",
                        "depends_on": [],
                        "subtasks": [
                            {"id": "1.1", "description": "Create models", "status": "pending"},
                            {"id": "1.2", "description": "Create migrations", "status": "pending"},
                        ]
                    },
                    {
                        "id": "2",
                        "name": "Implementation",
                        "depends_on": ["1"],
                        "subtasks": [
                            {"id": "2.1", "description": "Implement feature", "status": "pending"},
                        ]
                    }
                ]
            }
            (spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

            # Check initial state
            assert is_build_complete(spec_dir) is False
            assert get_progress_percentage(spec_dir) == 0.0

            next_task = get_next_subtask(spec_dir)
            assert next_task["id"] == "1.1"

            # Simulate completing first subtask
            plan["phases"][0]["subtasks"][0]["status"] = "completed"
            (spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

            assert get_progress_percentage(spec_dir) == pytest.approx(33.33, rel=0.1)

            next_task = get_next_subtask(spec_dir)
            assert next_task["id"] == "1.2"

            # Complete all
            plan["phases"][0]["subtasks"][1]["status"] = "completed"
            plan["phases"][1]["subtasks"][0]["status"] = "completed"
            (spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

            assert is_build_complete(spec_dir) is True
            assert get_progress_percentage(spec_dir) == 100.0
            assert get_next_subtask(spec_dir) is None
