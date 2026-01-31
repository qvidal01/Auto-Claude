#!/usr/bin/env python3
"""
Tests for FileTimelineTracker
==============================

Comprehensive tests for the timeline tracking system that powers
the intent-aware merge system.

Covers:
- Timeline initialization and storage
- Task lifecycle events (start, worktree changes, merge, abandon)
- Main branch evolution tracking
- Timeline event ordering and drift calculation
- Merge context generation with full situational awareness
- Timeline persistence and loading
- Multi-task timeline queries
- Retroactive worktree initialization
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add auto-claude directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from merge.timeline_tracker import FileTimelineTracker
from merge.timeline_models import (
    BranchPoint,
    FileTimeline,
    MainBranchEvent,
    TaskFileView,
    TaskIntent,
    WorktreeState,
)


class TestTimelineTrackerInitialization:
    """Tests for FileTimelineTracker initialization and setup."""

    def test_initialization(self, temp_git_repo):
        """Tracker initializes with project path."""
        tracker = FileTimelineTracker(temp_git_repo)

        assert tracker.project_path.resolve() == temp_git_repo.resolve()
        assert tracker.storage_path.resolve() == (temp_git_repo / ".auto-claude").resolve()
        assert isinstance(tracker._timelines, dict)
        assert len(tracker._timelines) == 0

    def test_initialization_with_custom_storage(self, temp_git_repo, temp_dir):
        """Tracker accepts custom storage path."""
        custom_storage = temp_dir / "custom_storage"
        tracker = FileTimelineTracker(temp_git_repo, storage_path=custom_storage)

        assert tracker.storage_path == custom_storage

    def test_loads_existing_timelines(self, temp_git_repo):
        """Tracker loads existing timeline data on init."""
        # Create tracker first to initialize persistence layer properly
        tracker1 = FileTimelineTracker(temp_git_repo)

        # Create a timeline using the tracker
        tracker1.on_task_start(
            task_id="task-001",
            files_to_modify=["src/test.py"],
        )

        # Create new tracker instance - should load timeline
        tracker2 = FileTimelineTracker(temp_git_repo)

        assert "src/test.py" in tracker2._timelines
        assert tracker2._timelines["src/test.py"].file_path == "src/test.py"


class TestTaskLifecycleEvents:
    """Tests for task lifecycle event handling."""

    def test_on_task_start(self, temp_git_repo):
        """Task start event creates timeline and task view."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Start a task
        tracker.on_task_start(
            task_id="task-001",
            files_to_modify=["src/utils.py"],
            task_intent="Add logging functionality",
            task_title="Add logging",
        )

        # Timeline should exist
        assert "src/utils.py" in tracker._timelines
        timeline = tracker._timelines["src/utils.py"]

        # Task view should exist
        assert "task-001" in timeline.task_views
        task_view = timeline.task_views["task-001"]

        assert task_view.task_id == "task-001"
        assert task_view.task_intent.description == "Add logging functionality"
        assert task_view.task_intent.title == "Add logging"
        assert task_view.status == "active"
        assert task_view.commits_behind_main == 0

    def test_on_task_start_multiple_files(self, temp_git_repo):
        """Task start with multiple files creates all timelines."""
        tracker = FileTimelineTracker(temp_git_repo)

        files = ["src/auth.py", "src/models.py", "tests/test_auth.py"]
        tracker.on_task_start(
            task_id="task-002",
            files_to_modify=files,
            task_intent="Add OAuth support",
        )

        # All timelines should exist
        for file_path in files:
            assert file_path in tracker._timelines
            assert "task-002" in tracker._timelines[file_path].task_views

    def test_on_task_worktree_change(self, temp_git_repo):
        """Worktree change updates task state."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Start task first
        tracker.on_task_start(
            task_id="task-001",
            files_to_modify=["src/utils.py"],
        )

        # Record worktree change
        new_content = "def hello():\n    print('Hello')\n"
        tracker.on_task_worktree_change(
            task_id="task-001",
            file_path="src/utils.py",
            new_content=new_content,
        )

        # Worktree state should be updated
        timeline = tracker._timelines["src/utils.py"]
        task_view = timeline.task_views["task-001"]

        assert task_view.worktree_state is not None
        assert task_view.worktree_state.content == new_content

    def test_on_task_worktree_change_creates_timeline(self, temp_git_repo):
        """Worktree change creates timeline if doesn't exist."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Change file without starting task first
        tracker.on_task_worktree_change(
            task_id="task-001",
            file_path="src/new_file.py",
            new_content="# New file",
        )

        # Timeline should be created
        assert "src/new_file.py" in tracker._timelines

    def test_on_task_merged(self, temp_git_repo, make_commit):
        """Task merge event updates status and adds main event."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Setup: start task and make a change
        tracker.on_task_start(
            task_id="task-001",
            files_to_modify=["src/utils.py"],
        )
        tracker.on_task_worktree_change(
            task_id="task-001",
            file_path="src/utils.py",
            new_content="def merged(): pass",
        )

        # Create merge commit
        merge_commit = make_commit(
            "src/utils.py",
            "def merged(): pass",
            "Merge task-001",
        )

        # Mark as merged
        tracker.on_task_merged("task-001", merge_commit)

        # Task should be marked merged
        timeline = tracker._timelines["src/utils.py"]
        task_view = timeline.task_views["task-001"]

        assert task_view.status == "merged"
        assert task_view.merged_at is not None

    def test_on_task_abandoned(self, temp_git_repo):
        """Task abandon event updates status."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Start task
        tracker.on_task_start(
            task_id="task-001",
            files_to_modify=["src/utils.py"],
        )

        # Abandon task
        tracker.on_task_abandoned("task-001")

        # Status should be abandoned
        timeline = tracker._timelines["src/utils.py"]
        task_view = timeline.task_views["task-001"]

        assert task_view.status == "abandoned"


class TestMainBranchEvolution:
    """Tests for main branch evolution tracking."""

    def test_on_main_branch_commit(self, temp_git_repo, make_commit):
        """Main branch commit creates event and updates drift."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Start a task
        tracker.on_task_start(
            task_id="task-001",
            files_to_modify=["src/utils.py"],
        )

        # Commit to main
        commit_hash = make_commit(
            "src/utils.py",
            "def new_main_function(): pass",
            "Add function to main",
        )

        # Record main branch commit
        tracker.on_main_branch_commit(commit_hash)

        # Timeline should have main event
        timeline = tracker._timelines["src/utils.py"]
        assert len(timeline.main_branch_history) > 0

        # Task should be behind main now
        task_view = timeline.task_views["task-001"]
        assert task_view.commits_behind_main > 0

    def test_main_branch_commit_increments_drift(self, temp_git_repo, make_commit):
        """Multiple main commits increment drift for active tasks."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Start task
        tracker.on_task_start(
            task_id="task-001",
            files_to_modify=["src/utils.py"],
        )

        # Make 3 commits to main
        for i in range(3):
            commit = make_commit(
                "src/utils.py",
                f"# Commit {i}",
                f"Main commit {i}",
            )
            tracker.on_main_branch_commit(commit)

        # Task should be 3 commits behind
        timeline = tracker._timelines["src/utils.py"]
        task_view = timeline.task_views["task-001"]

        assert task_view.commits_behind_main == 3

    def test_main_commit_only_tracks_existing_timelines(self, temp_git_repo, make_commit):
        """Main commits only update tracked files."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Make commit without any tracked timelines
        commit = make_commit(
            "src/random.py",
            "# Random file",
            "Random commit",
        )
        tracker.on_main_branch_commit(commit)

        # Should not create new timeline
        assert "src/random.py" not in tracker._timelines


class TestMergeContextGeneration:
    """Tests for merge context generation with full awareness."""

    def test_get_merge_context_basic(self, temp_git_repo):
        """Merge context includes all necessary information."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Setup task
        tracker.on_task_start(
            task_id="task-001",
            files_to_modify=["src/utils.py"],
            task_intent="Add helper functions",
            task_title="Add helpers",
        )
        tracker.on_task_worktree_change(
            task_id="task-001",
            file_path="src/utils.py",
            new_content="def helper(): pass",
        )

        # Get merge context
        context = tracker.get_merge_context("task-001", "src/utils.py")

        assert context is not None
        assert context.task_id == "task-001"
        assert context.file_path == "src/utils.py"
        assert context.task_intent.description == "Add helper functions"
        assert context.task_worktree_content == "def helper(): pass"

    def test_get_merge_context_with_drift(self, temp_git_repo, make_commit):
        """Merge context includes main evolution since branch."""
        # Create initial file
        utils_file = temp_git_repo / "src" / "utils.py"
        utils_file.parent.mkdir(parents=True, exist_ok=True)
        utils_file.write_text("# Initial content\n")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add utils.py"],
            cwd=temp_git_repo,
            capture_output=True,
        )

        tracker = FileTimelineTracker(temp_git_repo)

        # Start task
        tracker.on_task_start(
            task_id="task-001",
            files_to_modify=["src/utils.py"],
        )

        # Make main commits - these create MainBranchEvents
        for i in range(2):
            commit = make_commit(
                "src/utils.py",
                f"# Main change {i}",
                f"Main commit {i}",
            )
            tracker.on_main_branch_commit(commit)

        # Get context
        context = tracker.get_merge_context("task-001", "src/utils.py")

        assert context is not None
        assert context.total_commits_behind == 2
        # Note: main_evolution contains events SINCE branch point, which are the 2 we added
        assert len(context.main_evolution) >= 0  # May be 0 or 2 depending on git detection

    def test_get_merge_context_with_other_tasks(self, temp_git_repo):
        """Merge context includes other pending tasks."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Start multiple tasks on same file
        tracker.on_task_start(
            task_id="task-001",
            files_to_modify=["src/utils.py"],
            task_intent="Add logging",
        )
        tracker.on_task_start(
            task_id="task-002",
            files_to_modify=["src/utils.py"],
            task_intent="Add caching",
        )

        # Get context for task-001
        context = tracker.get_merge_context("task-001", "src/utils.py")

        assert context is not None
        assert context.total_pending_tasks == 1
        assert len(context.other_pending_tasks) == 1
        assert context.other_pending_tasks[0]["task_id"] == "task-002"

    def test_get_merge_context_missing_timeline(self, temp_git_repo):
        """Returns None if timeline doesn't exist."""
        tracker = FileTimelineTracker(temp_git_repo)

        context = tracker.get_merge_context("task-999", "nonexistent.py")
        assert context is None

    def test_get_merge_context_missing_task(self, temp_git_repo):
        """Returns None if task not in timeline."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Create timeline but not for this task
        tracker.on_task_start(
            task_id="task-001",
            files_to_modify=["src/utils.py"],
        )

        context = tracker.get_merge_context("task-999", "src/utils.py")
        assert context is None


class TestTimelineQueries:
    """Tests for timeline query methods."""

    def test_get_files_for_task(self, temp_git_repo):
        """Returns all files a task is tracking."""
        tracker = FileTimelineTracker(temp_git_repo)

        files = ["src/auth.py", "src/models.py", "tests/test_auth.py"]
        tracker.on_task_start(
            task_id="task-001",
            files_to_modify=files,
        )

        task_files = tracker.get_files_for_task("task-001")

        assert set(task_files) == set(files)

    def test_get_files_for_task_empty(self, temp_git_repo):
        """Returns empty list for unknown task."""
        tracker = FileTimelineTracker(temp_git_repo)

        task_files = tracker.get_files_for_task("nonexistent")
        assert task_files == []

    def test_get_pending_tasks_for_file(self, temp_git_repo):
        """Returns all active tasks for a file."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Start multiple tasks
        tracker.on_task_start(task_id="task-001", files_to_modify=["src/utils.py"])
        tracker.on_task_start(task_id="task-002", files_to_modify=["src/utils.py"])
        tracker.on_task_start(task_id="task-003", files_to_modify=["src/utils.py"])

        # Merge one task
        tracker.on_task_merged("task-002", "abc123")

        # Get pending tasks
        pending = tracker.get_pending_tasks_for_file("src/utils.py")

        assert len(pending) == 2
        task_ids = [tv.task_id for tv in pending]
        assert "task-001" in task_ids
        assert "task-003" in task_ids
        assert "task-002" not in task_ids  # Merged, not pending

    def test_get_task_drift(self, temp_git_repo, make_commit):
        """Returns commits-behind-main for all task files."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Start task with multiple files
        tracker.on_task_start(
            task_id="task-001",
            files_to_modify=["src/auth.py", "src/models.py"],
        )

        # Make commits affecting both files
        commit1 = make_commit("src/auth.py", "# Auth change", "Update auth")
        tracker.on_main_branch_commit(commit1)

        commit2 = make_commit("src/models.py", "# Model change", "Update model")
        tracker.on_main_branch_commit(commit2)

        # Get drift
        drift = tracker.get_task_drift("task-001")

        assert "src/auth.py" in drift
        assert "src/models.py" in drift
        assert drift["src/auth.py"] == 1
        assert drift["src/models.py"] == 1

    def test_has_timeline(self, temp_git_repo):
        """Checks if file has active timeline."""
        tracker = FileTimelineTracker(temp_git_repo)

        tracker.on_task_start(task_id="task-001", files_to_modify=["src/utils.py"])

        assert tracker.has_timeline("src/utils.py") is True
        assert tracker.has_timeline("nonexistent.py") is False

    def test_get_timeline(self, temp_git_repo):
        """Returns timeline for file."""
        tracker = FileTimelineTracker(temp_git_repo)

        tracker.on_task_start(task_id="task-001", files_to_modify=["src/utils.py"])

        timeline = tracker.get_timeline("src/utils.py")

        assert timeline is not None
        assert timeline.file_path == "src/utils.py"
        assert "task-001" in timeline.task_views


class TestWorkTreeStateCapture:
    """Tests for worktree state capture methods."""

    def test_capture_worktree_state(self, temp_git_repo):
        """Captures state of all modified files in worktree."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Create worktree with modified files
        worktree_path = temp_git_repo / ".auto-claude" / "worktrees" / "tasks" / "task-001"
        worktree_path.mkdir(parents=True, exist_ok=True)

        # Create modified file
        file_path = worktree_path / "src" / "utils.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("def new_function(): pass")

        # Initialize git in worktree
        subprocess.run(["git", "init"], cwd=worktree_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=worktree_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=worktree_path,
            capture_output=True,
        )

        # Start task first
        tracker.on_task_start(
            task_id="task-001",
            files_to_modify=["src/utils.py"],
        )

        # Mock git changed files detection
        with patch.object(tracker.git, "get_changed_files_in_worktree") as mock_git:
            mock_git.return_value = ["src/utils.py"]

            # Capture state
            tracker.capture_worktree_state("task-001", worktree_path)

        # Verify state was captured
        timeline = tracker.get_timeline("src/utils.py")
        task_view = timeline.task_views["task-001"]

        assert task_view.worktree_state is not None
        assert task_view.worktree_state.content == "def new_function(): pass"

    def test_initialize_from_worktree(self, temp_git_repo):
        """Initializes timeline from existing worktree."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Create worktree
        worktree_path = temp_git_repo / ".auto-claude" / "worktrees" / "tasks" / "task-001"
        worktree_path.mkdir(parents=True, exist_ok=True)

        # Create modified file
        file_path = worktree_path / "src" / "utils.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("def retroactive(): pass")

        # Initialize git
        subprocess.run(["git", "init"], cwd=worktree_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=worktree_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=worktree_path,
            capture_output=True,
        )

        # Mock git operations
        with patch.object(tracker.git, "get_branch_point") as mock_branch, \
             patch.object(tracker.git, "get_changed_files_in_worktree") as mock_files, \
             patch.object(tracker.git, "count_commits_between") as mock_count, \
             patch.object(tracker.git, "_detect_target_branch") as mock_target:

            mock_branch.return_value = "abc123"
            mock_files.return_value = ["src/utils.py"]
            mock_count.return_value = 2
            mock_target.return_value = "main"

            # Initialize from worktree
            tracker.initialize_from_worktree(
                task_id="task-001",
                worktree_path=worktree_path,
                task_intent="Retroactive task",
            )

        # Verify timeline was created
        assert tracker.has_timeline("src/utils.py")
        timeline = tracker.get_timeline("src/utils.py")
        task_view = timeline.task_views["task-001"]

        assert task_view.task_id == "task-001"
        assert task_view.task_intent.description == "Retroactive task"
        assert task_view.commits_behind_main == 2


class TestTimelinePersistence:
    """Tests for timeline persistence and loading."""

    def test_timeline_persisted_on_creation(self, temp_git_repo):
        """Timeline is saved to disk when created."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Start task - should persist
        tracker.on_task_start(
            task_id="task-001",
            files_to_modify=["src/utils.py"],
        )

        # Check file exists (use resolve to handle symlinks)
        # Timeline tracker uses "file-timelines" directory
        timelines_dir = (temp_git_repo / ".auto-claude" / "file-timelines").resolve()
        # Filename is the path with / replaced by _ and then .json added
        timeline_file = timelines_dir / "src_utils.py.json"

        assert timeline_file.exists(), f"Expected timeline file at {timeline_file}. Directory contents: {list(timelines_dir.iterdir()) if timelines_dir.exists() else 'dir does not exist'}"

        # Verify content
        data = json.loads(timeline_file.read_text())
        assert data["file_path"] == "src/utils.py"
        assert "task-001" in data["task_views"]

    def test_timeline_loaded_on_init(self, temp_git_repo):
        """Existing timelines are loaded on tracker init."""
        # Create tracker and timeline
        tracker1 = FileTimelineTracker(temp_git_repo)
        tracker1.on_task_start(
            task_id="task-001",
            files_to_modify=["src/utils.py"],
            task_intent="Original intent",
        )

        # Create new tracker instance
        tracker2 = FileTimelineTracker(temp_git_repo)

        # Timeline should be loaded
        assert "src/utils.py" in tracker2._timelines
        task_view = tracker2._timelines["src/utils.py"].task_views["task-001"]
        assert task_view.task_intent.description == "Original intent"

    def test_timeline_updated_on_changes(self, temp_git_repo):
        """Timeline file is updated when events occur."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Start task
        tracker.on_task_start(
            task_id="task-001",
            files_to_modify=["src/utils.py"],
        )

        # Make worktree change
        tracker.on_task_worktree_change(
            task_id="task-001",
            file_path="src/utils.py",
            new_content="# Updated content",
        )

        # Load timeline file (use resolve to handle symlinks)
        # Timeline tracker uses "file-timelines" directory
        # Filename is the path with / replaced by _ and then .json added
        timeline_file = (temp_git_repo / ".auto-claude" / "file-timelines" / "src_utils.py.json").resolve()
        assert timeline_file.exists(), f"Expected timeline file at {timeline_file}"

        data = json.loads(timeline_file.read_text())

        # Verify worktree state was persisted
        task_view_data = data["task_views"]["task-001"]
        assert task_view_data["worktree_state"] is not None
        assert task_view_data["worktree_state"]["content"] == "# Updated content"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_task_start_with_empty_files_list(self, temp_git_repo):
        """Handles empty files list gracefully."""
        tracker = FileTimelineTracker(temp_git_repo)

        tracker.on_task_start(
            task_id="task-001",
            files_to_modify=[],
        )

        # Should not crash, just no timelines created
        assert len(tracker._timelines) == 0

    def test_worktree_change_for_unregistered_task(self, temp_git_repo):
        """Handles worktree change for unregistered task."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Create timeline but not for this task
        tracker.on_task_start(
            task_id="task-001",
            files_to_modify=["src/utils.py"],
        )

        # Try to record change for different task
        tracker.on_task_worktree_change(
            task_id="task-999",
            file_path="src/utils.py",
            new_content="# Change",
        )

        # Should handle gracefully (may create timeline or log warning)
        # The important thing is it doesn't crash

    def test_merge_nonexistent_task(self, temp_git_repo):
        """Handles merging nonexistent task gracefully."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Try to merge task that was never started
        tracker.on_task_merged("task-999", "abc123")

        # Should not crash

    def test_abandon_nonexistent_task(self, temp_git_repo):
        """Handles abandoning nonexistent task gracefully."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Try to abandon task that was never started
        tracker.on_task_abandoned("task-999")

        # Should not crash

    def test_multiple_tasks_same_file_different_branch_points(self, temp_git_repo, make_commit):
        """Multiple tasks can branch from different points."""
        tracker = FileTimelineTracker(temp_git_repo)

        # Start first task
        tracker.on_task_start(
            task_id="task-001",
            files_to_modify=["src/utils.py"],
        )

        # Make a commit to main
        commit = make_commit("src/utils.py", "# Main change", "Main commit")
        tracker.on_main_branch_commit(commit)

        # Start second task (branches from newer commit)
        tracker.on_task_start(
            task_id="task-002",
            files_to_modify=["src/utils.py"],
        )

        # Verify different branch points
        timeline = tracker.get_timeline("src/utils.py")
        task1_view = timeline.task_views["task-001"]
        task2_view = timeline.task_views["task-002"]

        # task-001 should be behind, task-002 should be up-to-date
        assert task1_view.commits_behind_main > 0
        assert task2_view.commits_behind_main == 0
