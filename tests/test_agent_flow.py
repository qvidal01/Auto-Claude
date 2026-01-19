#!/usr/bin/env python3
"""
Test Suite for Agent Flow Integration
======================================

Tests for planner→coder→QA state transitions including:
- Planner to coder transition logic
- Handoff data preservation
- Post-session processing for different subtask states
- State transition detection and handling
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))


# =============================================================================
# TEST ENVIRONMENT SETUP
# =============================================================================

def setup_test_environment():
    """Create temporary directories for testing.

    IMPORTANT: This function properly isolates git operations by clearing
    git environment variables that may be set by pre-commit hooks. Without
    this isolation, git operations could affect the parent repository when
    tests run inside a git worktree (e.g., during pre-commit validation).
    """
    temp_dir = Path(tempfile.mkdtemp())
    spec_dir = temp_dir / "spec"
    project_dir = temp_dir / "project"

    spec_dir.mkdir(parents=True)
    project_dir.mkdir(parents=True)

    # Clear git environment variables that may be set by pre-commit hooks
    # to avoid git operations affecting the parent repository
    git_vars_to_clear = [
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    ]

    saved_env = {}
    for key in git_vars_to_clear:
        saved_env[key] = os.environ.pop(key, None)

    # Set GIT_CEILING_DIRECTORIES to prevent git from discovering parent .git
    saved_env["GIT_CEILING_DIRECTORIES"] = os.environ.get("GIT_CEILING_DIRECTORIES")
    os.environ["GIT_CEILING_DIRECTORIES"] = str(temp_dir)

    # Initialize git repo in project dir
    subprocess.run(["git", "init"], cwd=project_dir, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_dir, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=project_dir, capture_output=True)

    # Create initial commit
    test_file = project_dir / "test.txt"
    test_file.write_text("Initial content")
    subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_dir, capture_output=True)

    # Ensure branch is named 'main' (some git configs default to 'master')
    subprocess.run(["git", "branch", "-M", "main"], cwd=project_dir, capture_output=True)

    return temp_dir, spec_dir, project_dir, saved_env


def cleanup_test_environment(temp_dir, saved_env=None):
    """Remove temporary directories and restore environment variables."""
    shutil.rmtree(temp_dir, ignore_errors=True)

    # Restore original environment variables if provided
    if saved_env is not None:
        for key, value in saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def create_implementation_plan(spec_dir: Path, subtasks: list[dict]) -> Path:
    """Create an implementation_plan.json with the given subtasks."""
    plan = {
        "feature": "Test Feature",
        "workflow_type": "feature",
        "status": "in_progress",
        "phases": [
            {
                "id": "phase-1",
                "name": "Test Phase",
                "type": "implementation",
                "subtasks": subtasks
            }
        ]
    }
    plan_file = spec_dir / "implementation_plan.json"
    plan_file.write_text(json.dumps(plan, indent=2))
    return plan_file


def get_latest_commit(project_dir: Path) -> str:
    """Get the hash of the latest git commit."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_dir,
        capture_output=True,
        text=True
    )
    return result.stdout.strip() if result.returncode == 0 else ""


# =============================================================================
# PLANNER TO CODER TRANSITION TESTS
# =============================================================================

class TestPlannerToCoderTransition:
    """Tests for the planner→coder state transition logic."""

    def test_first_run_flag_indicates_planner_mode(self):
        """Test that first_run=True indicates planner mode."""
        from prompts import is_first_run

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Empty spec directory - should be first run (planner mode)
            assert is_first_run(spec_dir) is True, "Empty spec should be first run"

            # Create implementation plan - should no longer be first run
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Test task", "status": "pending"}
            ])

            assert is_first_run(spec_dir) is False, "Spec with plan should not be first run"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_transition_from_planning_to_coding_phase(self):
        """Test that planning phase transitions to coding phase correctly."""
        from progress import get_next_subtask

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Create implementation plan with pending subtask
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Implement feature", "status": "pending"}
            ])

            # After planner creates plan, get_next_subtask should return the first pending subtask
            next_subtask = get_next_subtask(spec_dir)

            assert next_subtask is not None, "Should find next subtask after planning"
            assert next_subtask.get("id") == "subtask-1", "Should return first pending subtask"
            assert next_subtask.get("status") == "pending", "Subtask should be pending"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_planner_completion_enables_coder_session(self):
        """Test that planner completion (plan created) enables coder session."""
        from progress import is_build_complete, count_subtasks

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Create plan with pending subtasks
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Task 1", "status": "pending"},
                {"id": "subtask-2", "description": "Task 2", "status": "pending"}
            ])

            # Build should not be complete - coder needs to work
            assert is_build_complete(spec_dir) is False, "Build should not be complete with pending subtasks"

            # Should have subtasks to work on
            completed, total = count_subtasks(spec_dir)
            assert total == 2, "Should have 2 total subtasks"
            assert completed == 0, "Should have 0 completed subtasks"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_planning_to_coding_subtask_info_preserved(self):
        """Test that subtask information is preserved during phase transition."""
        from agents.utils import load_implementation_plan, find_subtask_in_plan

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Create plan with detailed subtask info
            subtask_data = {
                "id": "subtask-1",
                "description": "Implement user authentication",
                "status": "pending",
                "files_to_modify": ["app/auth.py", "app/routes.py"],
                "files_to_create": ["app/services/oauth.py"],
                "patterns_from": ["tests/test_auth.py"],
                "verification": {
                    "type": "command",
                    "command": "pytest tests/test_auth.py -v"
                }
            }
            create_implementation_plan(spec_dir, [subtask_data])

            # Load plan and find subtask
            plan = load_implementation_plan(spec_dir)
            subtask = find_subtask_in_plan(plan, "subtask-1")

            # Verify all data preserved
            assert subtask is not None, "Should find subtask in plan"
            assert subtask["id"] == "subtask-1", "ID should be preserved"
            assert subtask["description"] == "Implement user authentication", "Description preserved"
            assert subtask["files_to_modify"] == ["app/auth.py", "app/routes.py"], "Files to modify preserved"
            assert subtask["files_to_create"] == ["app/services/oauth.py"], "Files to create preserved"
            assert subtask["verification"]["command"] == "pytest tests/test_auth.py -v", "Verification preserved"

        finally:
            cleanup_test_environment(temp_dir, saved_env)


# =============================================================================
# POST-SESSION PROCESSING TESTS
# =============================================================================

class TestPostSessionProcessing:
    """Tests for post_session_processing function."""

    def test_completed_subtask_records_success(self):
        """Test that completed subtask is recorded as successful."""
        from recovery import RecoveryManager
        from agents.session import post_session_processing

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Create plan with completed subtask
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Test task", "status": "completed"}
            ])

            recovery_manager = RecoveryManager(spec_dir, project_dir)
            commit_before = get_latest_commit(project_dir)

            # Mock memory-related functions to avoid side effects
            with patch("agents.session.extract_session_insights", new_callable=AsyncMock) as mock_insights, \
                 patch("agents.session.save_session_memory", new_callable=AsyncMock) as mock_memory:

                mock_insights.return_value = {"file_insights": [], "patterns_discovered": []}
                mock_memory.return_value = (True, "file")

                # Run async function using asyncio.run()
                async def run_test():
                    return await post_session_processing(
                        spec_dir=spec_dir,
                        project_dir=project_dir,
                        subtask_id="subtask-1",
                        session_num=1,
                        commit_before=commit_before,
                        commit_count_before=1,
                        recovery_manager=recovery_manager,
                        linear_enabled=False,
                    )

                result = asyncio.run(run_test())

            assert result is True, "Completed subtask should return True"

            # Verify attempt was recorded
            history = recovery_manager.get_subtask_history("subtask-1")
            assert len(history["attempts"]) == 1, "Should have 1 attempt"
            assert history["attempts"][0]["success"] is True, "Attempt should be successful"
            assert history["status"] == "completed", "Status should be completed"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_in_progress_subtask_records_failure(self):
        """Test that in_progress subtask is recorded as incomplete."""
        from recovery import RecoveryManager
        from agents.session import post_session_processing

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Create plan with in_progress subtask
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Test task", "status": "in_progress"}
            ])

            recovery_manager = RecoveryManager(spec_dir, project_dir)
            commit_before = get_latest_commit(project_dir)

            with patch("agents.session.extract_session_insights", new_callable=AsyncMock) as mock_insights, \
                 patch("agents.session.save_session_memory", new_callable=AsyncMock) as mock_memory:

                mock_insights.return_value = {"file_insights": [], "patterns_discovered": []}
                mock_memory.return_value = (True, "file")

                # Run async function using asyncio.run()
                async def run_test():
                    return await post_session_processing(
                        spec_dir=spec_dir,
                        project_dir=project_dir,
                        subtask_id="subtask-1",
                        session_num=1,
                        commit_before=commit_before,
                        commit_count_before=1,
                        recovery_manager=recovery_manager,
                        linear_enabled=False,
                    )

                result = asyncio.run(run_test())

            assert result is False, "In-progress subtask should return False"

            # Verify attempt was recorded as failed
            history = recovery_manager.get_subtask_history("subtask-1")
            assert len(history["attempts"]) == 1, "Should have 1 attempt"
            assert history["attempts"][0]["success"] is False, "Attempt should be unsuccessful"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_pending_subtask_records_failure(self):
        """Test that pending (no progress) subtask is recorded as failure."""
        from recovery import RecoveryManager
        from agents.session import post_session_processing

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Create plan with pending subtask (no progress made)
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Test task", "status": "pending"}
            ])

            recovery_manager = RecoveryManager(spec_dir, project_dir)
            commit_before = get_latest_commit(project_dir)

            with patch("agents.session.extract_session_insights", new_callable=AsyncMock) as mock_insights, \
                 patch("agents.session.save_session_memory", new_callable=AsyncMock) as mock_memory:

                mock_insights.return_value = {"file_insights": [], "patterns_discovered": []}
                mock_memory.return_value = (True, "file")

                # Run async function using asyncio.run()
                async def run_test():
                    return await post_session_processing(
                        spec_dir=spec_dir,
                        project_dir=project_dir,
                        subtask_id="subtask-1",
                        session_num=1,
                        commit_before=commit_before,
                        commit_count_before=1,
                        recovery_manager=recovery_manager,
                        linear_enabled=False,
                    )

                result = asyncio.run(run_test())

            assert result is False, "Pending subtask should return False"

        finally:
            cleanup_test_environment(temp_dir, saved_env)


# =============================================================================
# SUBTASK STATE TRANSITION TESTS
# =============================================================================

class TestSubtaskStateTransitions:
    """Tests for subtask state transition handling."""

    def test_find_subtask_in_plan(self):
        """Test finding a subtask by ID in the plan."""
        from agents.utils import load_implementation_plan, find_subtask_in_plan

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "First task", "status": "completed"},
                {"id": "subtask-2", "description": "Second task", "status": "pending"},
                {"id": "subtask-3", "description": "Third task", "status": "pending"}
            ])

            plan = load_implementation_plan(spec_dir)

            # Test finding existing subtasks
            subtask1 = find_subtask_in_plan(plan, "subtask-1")
            assert subtask1 is not None, "Should find subtask-1"
            assert subtask1["description"] == "First task"

            subtask2 = find_subtask_in_plan(plan, "subtask-2")
            assert subtask2 is not None, "Should find subtask-2"
            assert subtask2["status"] == "pending"

            # Test finding non-existent subtask
            missing = find_subtask_in_plan(plan, "subtask-999")
            assert missing is None, "Should return None for missing subtask"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_find_phase_for_subtask(self):
        """Test finding the phase containing a subtask."""
        from agents.utils import load_implementation_plan, find_phase_for_subtask

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Create plan with multiple phases
            plan = {
                "feature": "Test Feature",
                "workflow_type": "feature",
                "status": "in_progress",
                "phases": [
                    {
                        "id": "phase-1",
                        "name": "Setup Phase",
                        "type": "setup",
                        "subtasks": [
                            {"id": "subtask-1-1", "description": "Setup DB", "status": "completed"}
                        ]
                    },
                    {
                        "id": "phase-2",
                        "name": "Implementation Phase",
                        "type": "implementation",
                        "subtasks": [
                            {"id": "subtask-2-1", "description": "Implement feature", "status": "pending"},
                            {"id": "subtask-2-2", "description": "Add tests", "status": "pending"}
                        ]
                    }
                ]
            }
            plan_file = spec_dir / "implementation_plan.json"
            plan_file.write_text(json.dumps(plan, indent=2))

            loaded_plan = load_implementation_plan(spec_dir)

            # Find phase for subtask in first phase
            phase1 = find_phase_for_subtask(loaded_plan, "subtask-1-1")
            assert phase1 is not None, "Should find phase for subtask-1-1"
            assert phase1["name"] == "Setup Phase", "Should be setup phase"

            # Find phase for subtask in second phase
            phase2 = find_phase_for_subtask(loaded_plan, "subtask-2-1")
            assert phase2 is not None, "Should find phase for subtask-2-1"
            assert phase2["name"] == "Implementation Phase", "Should be implementation phase"

            # Find phase for non-existent subtask
            missing_phase = find_phase_for_subtask(loaded_plan, "subtask-999")
            assert missing_phase is None, "Should return None for missing subtask"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_get_next_subtask_skips_completed(self):
        """Test that get_next_subtask skips completed subtasks."""
        from progress import get_next_subtask

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "First task", "status": "completed"},
                {"id": "subtask-2", "description": "Second task", "status": "completed"},
                {"id": "subtask-3", "description": "Third task", "status": "pending"}
            ])

            next_subtask = get_next_subtask(spec_dir)

            assert next_subtask is not None, "Should find pending subtask"
            assert next_subtask["id"] == "subtask-3", "Should skip completed and return first pending"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_build_complete_when_all_subtasks_done(self):
        """Test that build is complete when all subtasks are completed."""
        from progress import is_build_complete

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "First task", "status": "completed"},
                {"id": "subtask-2", "description": "Second task", "status": "completed"},
                {"id": "subtask-3", "description": "Third task", "status": "completed"}
            ])

            assert is_build_complete(spec_dir) is True, "Build should be complete when all subtasks done"

        finally:
            cleanup_test_environment(temp_dir, saved_env)


# =============================================================================
# HANDOFF DATA PRESERVATION TESTS
# =============================================================================

class TestHandoffDataPreservation:
    """Tests for data preservation during agent handoffs."""

    def test_subtask_context_loading(self):
        """Test that subtask context is properly loaded for coder."""
        from prompt_generator import load_subtask_context

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Create spec.md
            (spec_dir / "spec.md").write_text("# Test Spec\n\nTest content")

            # Create context.json
            context = {
                "files_to_modify": [
                    {"path": "app/main.py", "reason": "Add feature"}
                ],
                "files_to_reference": [
                    {"path": "app/utils.py", "reason": "Pattern reference"}
                ]
            }
            (spec_dir / "context.json").write_text(json.dumps(context))

            subtask = {
                "id": "subtask-1",
                "description": "Implement feature",
                "files_to_modify": ["app/main.py"],
                "patterns_from": ["app/utils.py"]
            }

            loaded_context = load_subtask_context(spec_dir, project_dir, subtask)

            # Verify context structure
            assert "patterns" in loaded_context or "files_to_modify" in loaded_context, \
                "Context should have patterns or files"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_recovery_hints_passed_to_coder(self):
        """Test that recovery hints are available for retry attempts."""
        from recovery import RecoveryManager

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            recovery_manager = RecoveryManager(spec_dir, project_dir)

            # Record a failed attempt
            recovery_manager.record_attempt(
                subtask_id="subtask-1",
                session=1,
                success=False,
                approach="First approach using async/await",
                error="Import error - module not found"
            )

            # Get recovery hints
            hints = recovery_manager.get_recovery_hints("subtask-1")

            assert len(hints) > 0, "Should have recovery hints after failure"
            assert any("Previous attempts: 1" in hint for hint in hints), "Should mention attempt count"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_commit_tracking_across_sessions(self):
        """Test that commit tracking works across sessions."""
        from recovery import RecoveryManager

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            recovery_manager = RecoveryManager(spec_dir, project_dir)

            # Get initial commit
            initial_commit = get_latest_commit(project_dir)

            # Record it as good
            recovery_manager.record_good_commit(initial_commit, "subtask-1")

            # Create a new commit
            test_file = project_dir / "new_file.txt"
            test_file.write_text("New content")
            subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Add new file"], cwd=project_dir, capture_output=True)

            new_commit = get_latest_commit(project_dir)

            # Record new commit
            recovery_manager.record_good_commit(new_commit, "subtask-2")

            # Verify last good commit is the new one
            last_good = recovery_manager.get_last_good_commit()
            assert last_good == new_commit, "Last good commit should be the newest"

        finally:
            cleanup_test_environment(temp_dir, saved_env)


# =============================================================================
# PLAN VALIDATION TESTS (for planner output)
# =============================================================================

class TestPlannerOutputValidation:
    """Tests for validating planner output before transition to coder."""

    def test_plan_must_have_pending_subtasks(self):
        """Test that valid plan has at least one pending subtask."""
        from progress import get_next_subtask

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Create plan with only completed subtasks
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Done task", "status": "completed"}
            ])

            next_subtask = get_next_subtask(spec_dir)
            assert next_subtask is None, "No pending subtasks should return None"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_plan_without_phases_returns_none(self):
        """Test that plan without phases returns None for next subtask."""
        from progress import get_next_subtask

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Create empty plan
            plan = {
                "feature": "Test Feature",
                "workflow_type": "feature",
                "status": "in_progress",
                "phases": []
            }
            plan_file = spec_dir / "implementation_plan.json"
            plan_file.write_text(json.dumps(plan, indent=2))

            next_subtask = get_next_subtask(spec_dir)
            assert next_subtask is None, "Empty phases should return None"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_missing_plan_returns_none(self):
        """Test that missing plan file returns None."""
        from progress import get_next_subtask

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Don't create any plan file
            next_subtask = get_next_subtask(spec_dir)
            assert next_subtask is None, "Missing plan should return None"

        finally:
            cleanup_test_environment(temp_dir, saved_env)


# =============================================================================
# SUBTASK COMPLETION DETECTION TESTS
# =============================================================================

class TestSubtaskCompletionDetection:
    """Tests for subtask completion detection and status counting."""

    def test_count_subtasks_basic(self):
        """Test basic subtask counting."""
        from progress import count_subtasks

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Task 1", "status": "completed"},
                {"id": "subtask-2", "description": "Task 2", "status": "pending"},
                {"id": "subtask-3", "description": "Task 3", "status": "pending"}
            ])

            completed, total = count_subtasks(spec_dir)

            assert total == 3, "Should have 3 total subtasks"
            assert completed == 1, "Should have 1 completed subtask"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_count_subtasks_empty_plan(self):
        """Test counting with empty plan returns zeros."""
        from progress import count_subtasks

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # No plan file exists
            completed, total = count_subtasks(spec_dir)
            assert completed == 0, "Empty plan should have 0 completed"
            assert total == 0, "Empty plan should have 0 total"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_count_subtasks_detailed_all_statuses(self):
        """Test detailed counting with all status types."""
        from progress import count_subtasks_detailed

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Task 1", "status": "completed"},
                {"id": "subtask-2", "description": "Task 2", "status": "in_progress"},
                {"id": "subtask-3", "description": "Task 3", "status": "pending"},
                {"id": "subtask-4", "description": "Task 4", "status": "failed"}
            ])

            counts = count_subtasks_detailed(spec_dir)

            assert counts["total"] == 4, "Should have 4 total subtasks"
            assert counts["completed"] == 1, "Should have 1 completed"
            assert counts["in_progress"] == 1, "Should have 1 in_progress"
            assert counts["pending"] == 1, "Should have 1 pending"
            assert counts["failed"] == 1, "Should have 1 failed"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_count_subtasks_detailed_unknown_status_treated_as_pending(self):
        """Test that unknown status values are treated as pending."""
        from progress import count_subtasks_detailed

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Task 1", "status": "unknown_status"},
                {"id": "subtask-2", "description": "Task 2", "status": "completed"}
            ])

            counts = count_subtasks_detailed(spec_dir)

            assert counts["total"] == 2, "Should have 2 total subtasks"
            assert counts["completed"] == 1, "Should have 1 completed"
            assert counts["pending"] == 1, "Unknown status should count as pending"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_is_build_complete_true_when_all_done(self):
        """Test is_build_complete returns True when all subtasks completed."""
        from progress import is_build_complete

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Task 1", "status": "completed"},
                {"id": "subtask-2", "description": "Task 2", "status": "completed"}
            ])

            assert is_build_complete(spec_dir) is True, "Build should be complete"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_is_build_complete_false_with_in_progress(self):
        """Test is_build_complete returns False with in_progress subtask."""
        from progress import is_build_complete

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Task 1", "status": "completed"},
                {"id": "subtask-2", "description": "Task 2", "status": "in_progress"}
            ])

            assert is_build_complete(spec_dir) is False, "Build should not be complete with in_progress"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_is_build_complete_false_with_failed(self):
        """Test is_build_complete returns False with failed subtask."""
        from progress import is_build_complete

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Task 1", "status": "completed"},
                {"id": "subtask-2", "description": "Task 2", "status": "failed"}
            ])

            assert is_build_complete(spec_dir) is False, "Build should not be complete with failed task"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_is_build_complete_false_with_empty_plan(self):
        """Test is_build_complete returns False for empty plan."""
        from progress import is_build_complete

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # No plan file
            assert is_build_complete(spec_dir) is False, "Empty plan should not be complete"

            # Empty phases
            plan = {
                "feature": "Test Feature",
                "workflow_type": "feature",
                "status": "in_progress",
                "phases": []
            }
            (spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

            assert is_build_complete(spec_dir) is False, "Plan with no subtasks should not be complete"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_get_progress_percentage(self):
        """Test progress percentage calculation."""
        from progress import get_progress_percentage

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # 50% complete
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Task 1", "status": "completed"},
                {"id": "subtask-2", "description": "Task 2", "status": "pending"}
            ])

            percentage = get_progress_percentage(spec_dir)
            assert percentage == 50.0, "Should be 50% complete"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_get_progress_percentage_empty_plan(self):
        """Test progress percentage for empty plan is 0."""
        from progress import get_progress_percentage

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # No plan file
            percentage = get_progress_percentage(spec_dir)
            assert percentage == 0.0, "Empty plan should be 0%"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_subtask_status_transition_to_completed(self):
        """Test detecting subtask transition from pending to completed."""
        from agents.utils import load_implementation_plan, find_subtask_in_plan
        from progress import is_build_complete

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Start with pending subtask
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Task 1", "status": "pending"}
            ])

            plan = load_implementation_plan(spec_dir)
            subtask = find_subtask_in_plan(plan, "subtask-1")
            assert subtask["status"] == "pending", "Initial status should be pending"
            assert is_build_complete(spec_dir) is False, "Should not be complete"

            # Update to completed
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Task 1", "status": "completed"}
            ])

            plan = load_implementation_plan(spec_dir)
            subtask = find_subtask_in_plan(plan, "subtask-1")
            assert subtask["status"] == "completed", "Updated status should be completed"
            assert is_build_complete(spec_dir) is True, "Should now be complete"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_subtask_status_transition_through_in_progress(self):
        """Test detecting subtask transition through in_progress state."""
        from agents.utils import load_implementation_plan, find_subtask_in_plan
        from progress import count_subtasks_detailed

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Start pending
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Task 1", "status": "pending"}
            ])

            counts = count_subtasks_detailed(spec_dir)
            assert counts["pending"] == 1, "Should have 1 pending"
            assert counts["in_progress"] == 0, "Should have 0 in_progress"

            # Move to in_progress
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Task 1", "status": "in_progress"}
            ])

            counts = count_subtasks_detailed(spec_dir)
            assert counts["pending"] == 0, "Should have 0 pending"
            assert counts["in_progress"] == 1, "Should have 1 in_progress"

            # Complete
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Task 1", "status": "completed"}
            ])

            counts = count_subtasks_detailed(spec_dir)
            assert counts["in_progress"] == 0, "Should have 0 in_progress"
            assert counts["completed"] == 1, "Should have 1 completed"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_multiple_subtasks_completion_sequence(self):
        """Test completion detection as subtasks complete one by one."""
        from progress import count_subtasks, is_build_complete

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Start with all pending
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Task 1", "status": "pending"},
                {"id": "subtask-2", "description": "Task 2", "status": "pending"},
                {"id": "subtask-3", "description": "Task 3", "status": "pending"}
            ])

            completed, total = count_subtasks(spec_dir)
            assert completed == 0 and total == 3, "Initial: 0/3"
            assert is_build_complete(spec_dir) is False

            # Complete first subtask
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Task 1", "status": "completed"},
                {"id": "subtask-2", "description": "Task 2", "status": "pending"},
                {"id": "subtask-3", "description": "Task 3", "status": "pending"}
            ])

            completed, total = count_subtasks(spec_dir)
            assert completed == 1 and total == 3, "After first: 1/3"
            assert is_build_complete(spec_dir) is False

            # Complete second subtask
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Task 1", "status": "completed"},
                {"id": "subtask-2", "description": "Task 2", "status": "completed"},
                {"id": "subtask-3", "description": "Task 3", "status": "pending"}
            ])

            completed, total = count_subtasks(spec_dir)
            assert completed == 2 and total == 3, "After second: 2/3"
            assert is_build_complete(spec_dir) is False

            # Complete all subtasks
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Task 1", "status": "completed"},
                {"id": "subtask-2", "description": "Task 2", "status": "completed"},
                {"id": "subtask-3", "description": "Task 3", "status": "completed"}
            ])

            completed, total = count_subtasks(spec_dir)
            assert completed == 3 and total == 3, "Final: 3/3"
            assert is_build_complete(spec_dir) is True

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_get_next_subtask_returns_first_pending_after_completed(self):
        """Test get_next_subtask returns correct subtask after completions."""
        from progress import get_next_subtask

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # First and second completed, third pending
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Task 1", "status": "completed"},
                {"id": "subtask-2", "description": "Task 2", "status": "completed"},
                {"id": "subtask-3", "description": "Task 3", "status": "pending"}
            ])

            next_subtask = get_next_subtask(spec_dir)
            assert next_subtask is not None, "Should find next subtask"
            assert next_subtask["id"] == "subtask-3", "Should return subtask-3"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_get_next_subtask_none_when_all_complete(self):
        """Test get_next_subtask returns None when all complete."""
        from progress import get_next_subtask

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            create_implementation_plan(spec_dir, [
                {"id": "subtask-1", "description": "Task 1", "status": "completed"},
                {"id": "subtask-2", "description": "Task 2", "status": "completed"}
            ])

            next_subtask = get_next_subtask(spec_dir)
            assert next_subtask is None, "Should return None when all complete"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_completion_detection_with_multi_phase_plan(self):
        """Test completion detection across multiple phases."""
        from progress import is_build_complete, count_subtasks

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Multi-phase plan
            plan = {
                "feature": "Test Feature",
                "workflow_type": "feature",
                "status": "in_progress",
                "phases": [
                    {
                        "id": "phase-1",
                        "name": "Setup Phase",
                        "type": "setup",
                        "subtasks": [
                            {"id": "subtask-1-1", "description": "Setup DB", "status": "completed"}
                        ]
                    },
                    {
                        "id": "phase-2",
                        "name": "Implementation Phase",
                        "type": "implementation",
                        "subtasks": [
                            {"id": "subtask-2-1", "description": "Implement feature", "status": "pending"},
                            {"id": "subtask-2-2", "description": "Add tests", "status": "pending"}
                        ]
                    }
                ]
            }
            (spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

            completed, total = count_subtasks(spec_dir)
            assert completed == 1 and total == 3, "Should count across phases: 1/3"
            assert is_build_complete(spec_dir) is False, "Should not be complete"

            # Complete all in second phase
            plan["phases"][1]["subtasks"][0]["status"] = "completed"
            plan["phases"][1]["subtasks"][1]["status"] = "completed"
            (spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

            completed, total = count_subtasks(spec_dir)
            assert completed == 3 and total == 3, "All phases complete: 3/3"
            assert is_build_complete(spec_dir) is True, "Should be complete"

        finally:
            cleanup_test_environment(temp_dir, saved_env)


# =============================================================================
# QA LOOP AND FIXER INTERACTION TESTS
# =============================================================================

class TestQALoopStateTransitions:
    """Tests for QA loop state transitions in agent flow context."""

    def test_qa_not_required_when_build_incomplete(self):
        """QA should not run when build is incomplete."""
        from qa_loop import should_run_qa, save_implementation_plan

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Create plan with pending subtasks
            plan = {
                "feature": "Test Feature",
                "phases": [
                    {
                        "phase": 1,
                        "name": "Test",
                        "subtasks": [
                            {"id": "c1", "description": "Task 1", "status": "completed"},
                            {"id": "c2", "description": "Task 2", "status": "pending"},
                        ],
                    },
                ],
            }
            save_implementation_plan(spec_dir, plan)

            assert should_run_qa(spec_dir) is False, "QA should not run with pending subtasks"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_qa_required_when_build_complete(self):
        """QA should run when build is complete and not yet approved."""
        from qa_loop import should_run_qa, save_implementation_plan

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Create plan with all completed subtasks
            plan = {
                "feature": "Test Feature",
                "phases": [
                    {
                        "phase": 1,
                        "name": "Test",
                        "subtasks": [
                            {"id": "c1", "description": "Task 1", "status": "completed"},
                            {"id": "c2", "description": "Task 2", "status": "completed"},
                        ],
                    },
                ],
            }
            save_implementation_plan(spec_dir, plan)

            assert should_run_qa(spec_dir) is True, "QA should run when build complete"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_qa_not_required_when_already_approved(self):
        """QA should not run when build is already approved."""
        from qa_loop import should_run_qa, save_implementation_plan

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            plan = {
                "feature": "Test Feature",
                "phases": [
                    {
                        "phase": 1,
                        "name": "Test",
                        "subtasks": [
                            {"id": "c1", "description": "Task 1", "status": "completed"},
                        ],
                    },
                ],
                "qa_signoff": {
                    "status": "approved",
                    "qa_session": 1,
                    "timestamp": "2024-01-01T12:00:00",
                },
            }
            save_implementation_plan(spec_dir, plan)

            assert should_run_qa(spec_dir) is False, "QA should not run when already approved"

        finally:
            cleanup_test_environment(temp_dir, saved_env)


class TestQAFixerInteraction:
    """Tests for QA reviewer to fixer handoff and interaction."""

    def test_fixer_should_run_when_qa_rejected(self):
        """Fixer should run when QA rejected the build."""
        from qa_loop import should_run_fixes, save_implementation_plan

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            plan = {
                "feature": "Test Feature",
                "qa_signoff": {
                    "status": "rejected",
                    "qa_session": 1,
                    "issues_found": [{"title": "Missing test", "type": "unit_test"}],
                },
            }
            save_implementation_plan(spec_dir, plan)

            assert should_run_fixes(spec_dir) is True, "Fixer should run when QA rejected"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_fixer_should_not_run_when_qa_approved(self):
        """Fixer should not run when QA approved the build."""
        from qa_loop import should_run_fixes, save_implementation_plan

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            plan = {
                "feature": "Test Feature",
                "qa_signoff": {
                    "status": "approved",
                    "qa_session": 1,
                    "tests_passed": {"unit": True, "integration": True, "e2e": True},
                },
            }
            save_implementation_plan(spec_dir, plan)

            assert should_run_fixes(spec_dir) is False, "Fixer should not run when approved"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_fixer_should_not_run_at_max_iterations(self):
        """Fixer should not run when max iterations reached."""
        from qa_loop import should_run_fixes, save_implementation_plan, MAX_QA_ITERATIONS

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            plan = {
                "feature": "Test Feature",
                "qa_signoff": {
                    "status": "rejected",
                    "qa_session": MAX_QA_ITERATIONS,
                    "issues_found": [{"title": "Recurring issue", "type": "unit_test"}],
                },
            }
            save_implementation_plan(spec_dir, plan)

            assert should_run_fixes(spec_dir) is False, "Fixer should not run at max iterations"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_fixer_fixes_applied_state(self):
        """Test transition to fixes_applied state after fixer runs."""
        from qa_loop import is_fixes_applied, save_implementation_plan

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Simulate fixer completing and setting fixes_applied
            plan = {
                "feature": "Test Feature",
                "qa_signoff": {
                    "status": "fixes_applied",
                    "ready_for_qa_revalidation": True,
                    "qa_session": 1,
                },
            }
            save_implementation_plan(spec_dir, plan)

            assert is_fixes_applied(spec_dir) is True, "Should detect fixes_applied state"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_fixer_fixes_not_ready_for_revalidation(self):
        """Test fixes_applied but not ready for revalidation."""
        from qa_loop import is_fixes_applied, save_implementation_plan

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            plan = {
                "feature": "Test Feature",
                "qa_signoff": {
                    "status": "fixes_applied",
                    "ready_for_qa_revalidation": False,
                    "qa_session": 1,
                },
            }
            save_implementation_plan(spec_dir, plan)

            assert is_fixes_applied(spec_dir) is False, "Should not be ready when flag is False"

        finally:
            cleanup_test_environment(temp_dir, saved_env)


class TestQAVerdictHandling:
    """Tests for QA verdict handling and status management."""

    def test_qa_approved_verdict(self):
        """Test QA approved verdict is correctly detected."""
        from qa_loop import is_qa_approved, is_qa_rejected, save_implementation_plan

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            plan = {
                "feature": "Test Feature",
                "qa_signoff": {
                    "status": "approved",
                    "qa_session": 1,
                    "timestamp": "2024-01-01T12:00:00",
                    "tests_passed": {"unit": True, "integration": True, "e2e": True},
                },
            }
            save_implementation_plan(spec_dir, plan)

            assert is_qa_approved(spec_dir) is True, "Should detect approved status"
            assert is_qa_rejected(spec_dir) is False, "Should not detect rejected when approved"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_qa_rejected_verdict(self):
        """Test QA rejected verdict is correctly detected."""
        from qa_loop import is_qa_approved, is_qa_rejected, save_implementation_plan

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            plan = {
                "feature": "Test Feature",
                "qa_signoff": {
                    "status": "rejected",
                    "qa_session": 1,
                    "timestamp": "2024-01-01T12:00:00",
                    "issues_found": [{"title": "Missing test", "type": "unit_test"}],
                },
            }
            save_implementation_plan(spec_dir, plan)

            assert is_qa_rejected(spec_dir) is True, "Should detect rejected status"
            assert is_qa_approved(spec_dir) is False, "Should not detect approved when rejected"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_qa_no_verdict_yet(self):
        """Test when no QA verdict has been made yet."""
        from qa_loop import is_qa_approved, is_qa_rejected, get_qa_signoff_status, save_implementation_plan

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            plan = {
                "feature": "Test Feature",
                "phases": [],
            }
            save_implementation_plan(spec_dir, plan)

            assert get_qa_signoff_status(spec_dir) is None, "Should have no signoff status"
            assert is_qa_approved(spec_dir) is False, "Should not be approved with no verdict"
            assert is_qa_rejected(spec_dir) is False, "Should not be rejected with no verdict"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_qa_iteration_count_tracking(self):
        """Test QA iteration count is tracked correctly."""
        from qa_loop import get_qa_iteration_count, save_implementation_plan

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # First iteration
            plan = {
                "feature": "Test Feature",
                "qa_signoff": {"status": "rejected", "qa_session": 1},
            }
            save_implementation_plan(spec_dir, plan)
            assert get_qa_iteration_count(spec_dir) == 1, "Should be iteration 1"

            # Second iteration
            plan["qa_signoff"]["qa_session"] = 2
            save_implementation_plan(spec_dir, plan)
            assert get_qa_iteration_count(spec_dir) == 2, "Should be iteration 2"

            # Third iteration
            plan["qa_signoff"]["qa_session"] = 3
            save_implementation_plan(spec_dir, plan)
            assert get_qa_iteration_count(spec_dir) == 3, "Should be iteration 3"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_qa_iteration_count_zero_when_no_signoff(self):
        """Test iteration count is 0 when no QA sessions yet."""
        from qa_loop import get_qa_iteration_count, save_implementation_plan

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            plan = {"feature": "Test Feature", "phases": []}
            save_implementation_plan(spec_dir, plan)

            assert get_qa_iteration_count(spec_dir) == 0, "Should be 0 with no signoff"

        finally:
            cleanup_test_environment(temp_dir, saved_env)


class TestQALoopWorkflow:
    """Integration tests for complete QA loop workflow."""

    def test_full_qa_workflow_approved_first_try(self):
        """Test complete QA workflow where build passes on first try."""
        from qa_loop import (
            should_run_qa,
            should_run_fixes,
            is_qa_approved,
            save_implementation_plan,
        )

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Build complete, QA should run
            plan = {
                "feature": "Test Feature",
                "phases": [
                    {
                        "phase": 1,
                        "name": "Test",
                        "subtasks": [
                            {"id": "c1", "description": "Task 1", "status": "completed"},
                        ],
                    },
                ],
            }
            save_implementation_plan(spec_dir, plan)
            assert should_run_qa(spec_dir) is True, "QA should run initially"

            # QA approves
            plan["qa_signoff"] = {
                "status": "approved",
                "qa_session": 1,
                "tests_passed": {"unit": True, "integration": True, "e2e": True},
            }
            save_implementation_plan(spec_dir, plan)

            # Verify end state
            assert is_qa_approved(spec_dir) is True, "Should be approved"
            assert should_run_qa(spec_dir) is False, "QA should not run again"
            assert should_run_fixes(spec_dir) is False, "Fixer should not run"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_full_qa_workflow_with_one_rejection(self):
        """Test QA workflow with one rejection followed by approval."""
        from qa_loop import (
            should_run_qa,
            should_run_fixes,
            is_qa_approved,
            is_qa_rejected,
            is_fixes_applied,
            get_qa_iteration_count,
            save_implementation_plan,
        )

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            # Build complete
            plan = {
                "feature": "Test Feature",
                "phases": [
                    {
                        "phase": 1,
                        "name": "Test",
                        "subtasks": [
                            {"id": "c1", "description": "Task 1", "status": "completed"},
                        ],
                    },
                ],
            }
            save_implementation_plan(spec_dir, plan)

            # First QA session - rejected
            plan["qa_signoff"] = {
                "status": "rejected",
                "qa_session": 1,
                "issues_found": [{"title": "Missing test", "type": "unit_test"}],
            }
            save_implementation_plan(spec_dir, plan)

            assert is_qa_rejected(spec_dir) is True, "Should be rejected"
            assert should_run_fixes(spec_dir) is True, "Fixer should run"
            assert get_qa_iteration_count(spec_dir) == 1, "Should be iteration 1"

            # Fixer applies fixes
            plan["qa_signoff"] = {
                "status": "fixes_applied",
                "ready_for_qa_revalidation": True,
                "qa_session": 1,
            }
            save_implementation_plan(spec_dir, plan)

            assert is_fixes_applied(spec_dir) is True, "Fixes should be applied"

            # Second QA session - approved
            plan["qa_signoff"] = {
                "status": "approved",
                "qa_session": 2,
                "tests_passed": {"unit": True, "integration": True, "e2e": True},
            }
            save_implementation_plan(spec_dir, plan)

            assert is_qa_approved(spec_dir) is True, "Should be approved"
            assert get_qa_iteration_count(spec_dir) == 2, "Should be iteration 2"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_qa_workflow_multiple_rejections(self):
        """Test QA workflow with multiple rejections until max iterations."""
        from qa_loop import (
            should_run_fixes,
            is_qa_rejected,
            get_qa_iteration_count,
            save_implementation_plan,
            MAX_QA_ITERATIONS,
        )

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            plan = {"feature": "Test Feature", "phases": []}

            # Simulate multiple rejections
            for i in range(1, MAX_QA_ITERATIONS + 1):
                plan["qa_signoff"] = {
                    "status": "rejected",
                    "qa_session": i,
                    "issues_found": [{"title": f"Issue {i}", "type": "unit_test"}],
                }
                save_implementation_plan(spec_dir, plan)

                assert is_qa_rejected(spec_dir) is True, f"Should be rejected at iteration {i}"
                assert get_qa_iteration_count(spec_dir) == i, f"Should be iteration {i}"

                if i < MAX_QA_ITERATIONS:
                    assert should_run_fixes(spec_dir) is True, f"Fixer should run at iteration {i}"
                else:
                    assert should_run_fixes(spec_dir) is False, "Fixer should not run at max iterations"

        finally:
            cleanup_test_environment(temp_dir, saved_env)


class TestQASignoffDataStructure:
    """Tests for QA signoff data structure validation."""

    def test_approved_signoff_has_tests_passed(self):
        """Test approved signoff includes tests_passed field."""
        from qa_loop import get_qa_signoff_status, save_implementation_plan

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            plan = {
                "feature": "Test Feature",
                "qa_signoff": {
                    "status": "approved",
                    "qa_session": 1,
                    "timestamp": "2024-01-01T12:00:00",
                    "tests_passed": {
                        "unit": True,
                        "integration": True,
                        "e2e": True,
                    },
                },
            }
            save_implementation_plan(spec_dir, plan)

            status = get_qa_signoff_status(spec_dir)
            assert status is not None, "Should have signoff status"
            assert "tests_passed" in status, "Approved signoff should have tests_passed"
            assert status["tests_passed"]["unit"] is True, "Unit tests should be True"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_rejected_signoff_has_issues_found(self):
        """Test rejected signoff includes issues_found field."""
        from qa_loop import get_qa_signoff_status, save_implementation_plan

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            plan = {
                "feature": "Test Feature",
                "qa_signoff": {
                    "status": "rejected",
                    "qa_session": 1,
                    "timestamp": "2024-01-01T12:00:00",
                    "issues_found": [
                        {"title": "Missing test", "type": "unit_test"},
                        {"title": "Validation error", "type": "acceptance"},
                    ],
                },
            }
            save_implementation_plan(spec_dir, plan)

            status = get_qa_signoff_status(spec_dir)
            assert status is not None, "Should have signoff status"
            assert "issues_found" in status, "Rejected signoff should have issues_found"
            assert len(status["issues_found"]) == 2, "Should have 2 issues"

        finally:
            cleanup_test_environment(temp_dir, saved_env)

    def test_issues_have_title_and_type(self):
        """Test that issues in rejected signoff have required fields."""
        from qa_loop import get_qa_signoff_status, save_implementation_plan

        temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

        try:
            plan = {
                "feature": "Test Feature",
                "qa_signoff": {
                    "status": "rejected",
                    "qa_session": 1,
                    "issues_found": [
                        {"title": "Test failure", "type": "unit_test"},
                    ],
                },
            }
            save_implementation_plan(spec_dir, plan)

            status = get_qa_signoff_status(spec_dir)
            issue = status["issues_found"][0]
            assert "title" in issue, "Issue should have title"
            assert "type" in issue, "Issue should have type"
            assert issue["title"] == "Test failure", "Title should match"
            assert issue["type"] == "unit_test", "Type should match"

        finally:
            cleanup_test_environment(temp_dir, saved_env)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def run_all_tests():
    """Run all tests using pytest."""
    import sys
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))


if __name__ == "__main__":
    run_all_tests()
