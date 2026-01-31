"""
Tests for the agents utils module
==================================

Tests covering agents/utils.py - git operations, plan management, and file syncing
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from agents.utils import (
    load_implementation_plan,
    find_subtask_in_plan,
    find_phase_for_subtask,
    sync_spec_to_source,
    _sync_directory,
    sync_plan_to_source,
)


# =============================================================================
# load_implementation_plan Tests
# =============================================================================

class TestLoadImplementationPlan:
    """Tests for load_implementation_plan function."""

    @pytest.fixture
    def temp_spec_dir(self):
        """Create a temporary spec directory."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_no_plan_file(self, temp_spec_dir):
        """Test when implementation plan doesn't exist."""
        result = load_implementation_plan(temp_spec_dir)
        assert result is None

    def test_valid_plan(self, temp_spec_dir):
        """Test loading a valid implementation plan."""
        plan = {
            "spec_name": "test-feature",
            "phases": [
                {
                    "id": "1",
                    "name": "Setup",
                    "subtasks": [{"id": "1.1", "status": "pending"}]
                }
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        result = load_implementation_plan(temp_spec_dir)
        assert result is not None
        assert result["spec_name"] == "test-feature"
        assert len(result["phases"]) == 1

    def test_invalid_json(self, temp_spec_dir):
        """Test with invalid JSON file."""
        (temp_spec_dir / "implementation_plan.json").write_text("not valid json {{{")

        result = load_implementation_plan(temp_spec_dir)
        assert result is None

    def test_empty_file(self, temp_spec_dir):
        """Test with empty file."""
        (temp_spec_dir / "implementation_plan.json").write_text("")

        result = load_implementation_plan(temp_spec_dir)
        assert result is None


# =============================================================================
# find_subtask_in_plan Tests
# =============================================================================

class TestFindSubtaskInPlan:
    """Tests for find_subtask_in_plan function."""

    def test_find_existing_subtask(self):
        """Test finding an existing subtask."""
        plan = {
            "phases": [
                {
                    "id": "1",
                    "subtasks": [
                        {"id": "1.1", "description": "First subtask"},
                        {"id": "1.2", "description": "Second subtask"},
                    ]
                },
                {
                    "id": "2",
                    "subtasks": [
                        {"id": "2.1", "description": "Third subtask"},
                    ]
                }
            ]
        }

        result = find_subtask_in_plan(plan, "1.2")
        assert result is not None
        assert result["description"] == "Second subtask"

    def test_find_subtask_in_second_phase(self):
        """Test finding a subtask in the second phase."""
        plan = {
            "phases": [
                {"id": "1", "subtasks": [{"id": "1.1"}]},
                {"id": "2", "subtasks": [{"id": "2.1", "name": "target"}]},
            ]
        }

        result = find_subtask_in_plan(plan, "2.1")
        assert result is not None
        assert result["name"] == "target"

    def test_subtask_not_found(self):
        """Test when subtask doesn't exist."""
        plan = {
            "phases": [
                {"id": "1", "subtasks": [{"id": "1.1"}]},
            ]
        }

        result = find_subtask_in_plan(plan, "99.99")
        assert result is None

    def test_empty_plan(self):
        """Test with empty plan."""
        plan = {"phases": []}

        result = find_subtask_in_plan(plan, "1.1")
        assert result is None

    def test_no_phases_key(self):
        """Test with no phases key."""
        plan = {"other_key": "value"}

        result = find_subtask_in_plan(plan, "1.1")
        assert result is None


# =============================================================================
# find_phase_for_subtask Tests
# =============================================================================

class TestFindPhaseForSubtask:
    """Tests for find_phase_for_subtask function."""

    def test_find_phase_for_existing_subtask(self):
        """Test finding the phase for an existing subtask."""
        plan = {
            "phases": [
                {
                    "id": "1",
                    "name": "Setup Phase",
                    "subtasks": [{"id": "1.1"}, {"id": "1.2"}]
                },
                {
                    "id": "2",
                    "name": "Implementation Phase",
                    "subtasks": [{"id": "2.1"}]
                }
            ]
        }

        result = find_phase_for_subtask(plan, "1.2")
        assert result is not None
        assert result["name"] == "Setup Phase"
        assert result["id"] == "1"

    def test_find_phase_second_phase(self):
        """Test finding the phase for a subtask in the second phase."""
        plan = {
            "phases": [
                {"id": "1", "subtasks": [{"id": "1.1"}]},
                {"id": "2", "name": "Phase Two", "subtasks": [{"id": "2.1"}]},
            ]
        }

        result = find_phase_for_subtask(plan, "2.1")
        assert result is not None
        assert result["name"] == "Phase Two"

    def test_phase_not_found(self):
        """Test when subtask doesn't exist."""
        plan = {
            "phases": [
                {"id": "1", "subtasks": [{"id": "1.1"}]},
            ]
        }

        result = find_phase_for_subtask(plan, "99.99")
        assert result is None


# =============================================================================
# sync_spec_to_source Tests
# =============================================================================

class TestSyncSpecToSource:
    """Tests for sync_spec_to_source function."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary source and worktree directories."""
        with tempfile.TemporaryDirectory() as worktree_td:
            with tempfile.TemporaryDirectory() as source_td:
                worktree_dir = Path(worktree_td).resolve()
                source_dir = Path(source_td).resolve()
                yield worktree_dir, source_dir

    def test_no_source_dir(self, temp_dirs):
        """Test when no source directory is provided."""
        worktree_dir, _ = temp_dirs
        result = sync_spec_to_source(worktree_dir, None)
        assert result is False

    def test_same_directory(self, temp_dirs):
        """Test when source and worktree are the same."""
        worktree_dir, _ = temp_dirs
        result = sync_spec_to_source(worktree_dir, worktree_dir)
        assert result is False

    def test_sync_single_file(self, temp_dirs):
        """Test syncing a single file."""
        worktree_dir, source_dir = temp_dirs

        # Create a file in worktree
        (worktree_dir / "implementation_plan.json").write_text('{"test": true}')

        result = sync_spec_to_source(worktree_dir, source_dir)
        assert result is True

        # Check file was synced
        synced_file = source_dir / "implementation_plan.json"
        assert synced_file.exists()
        assert json.loads(synced_file.read_text()) == {"test": True}

    def test_sync_multiple_files(self, temp_dirs):
        """Test syncing multiple files."""
        worktree_dir, source_dir = temp_dirs

        # Create multiple files
        (worktree_dir / "file1.json").write_text('{"a": 1}')
        (worktree_dir / "file2.txt").write_text("content")
        (worktree_dir / "file3.md").write_text("# Header")

        result = sync_spec_to_source(worktree_dir, source_dir)
        assert result is True

        # Check all files synced
        assert (source_dir / "file1.json").exists()
        assert (source_dir / "file2.txt").exists()
        assert (source_dir / "file3.md").exists()

    def test_sync_nested_directory(self, temp_dirs):
        """Test syncing a nested directory."""
        worktree_dir, source_dir = temp_dirs

        # Create nested structure
        memory_dir = worktree_dir / "memory"
        memory_dir.mkdir()
        (memory_dir / "session1.json").write_text('{"session": 1}')
        (memory_dir / "session2.json").write_text('{"session": 2}')

        result = sync_spec_to_source(worktree_dir, source_dir)
        assert result is True

        # Check nested files synced
        synced_memory = source_dir / "memory"
        assert synced_memory.exists()
        assert (synced_memory / "session1.json").exists()
        assert (synced_memory / "session2.json").exists()

    def test_skip_symlinks(self, temp_dirs):
        """Test that symlinks are skipped."""
        worktree_dir, source_dir = temp_dirs

        # Create a regular file
        (worktree_dir / "real_file.txt").write_text("real content")

        # Create a symlink (if platform supports it)
        symlink_path = worktree_dir / "symlink"
        try:
            symlink_path.symlink_to(worktree_dir / "real_file.txt")
        except OSError:
            pytest.skip("Platform doesn't support symlinks")

        result = sync_spec_to_source(worktree_dir, source_dir)
        assert result is True

        # Real file should be synced, symlink should not
        assert (source_dir / "real_file.txt").exists()
        assert not (source_dir / "symlink").exists()


# =============================================================================
# _sync_directory Tests
# =============================================================================

class TestSyncDirectory:
    """Tests for _sync_directory function."""

    def test_sync_simple_directory(self):
        """Test syncing a simple directory."""
        with tempfile.TemporaryDirectory() as source_td:
            with tempfile.TemporaryDirectory() as target_td:
                source = Path(source_td).resolve()
                target = Path(target_td).resolve() / "subdir"

                # Create files in source
                (source / "file1.txt").write_text("content1")
                (source / "file2.txt").write_text("content2")

                _sync_directory(source, target)

                # Check files synced
                assert target.exists()
                assert (target / "file1.txt").read_text() == "content1"
                assert (target / "file2.txt").read_text() == "content2"

    def test_sync_recursive_directory(self):
        """Test syncing nested directories."""
        with tempfile.TemporaryDirectory() as source_td:
            with tempfile.TemporaryDirectory() as target_td:
                source = Path(source_td).resolve()
                target = Path(target_td).resolve() / "sync"

                # Create nested structure
                nested = source / "level1" / "level2"
                nested.mkdir(parents=True)
                (nested / "deep_file.txt").write_text("deep")

                _sync_directory(source, target)

                # Check nested sync
                assert (target / "level1" / "level2" / "deep_file.txt").exists()
                assert (target / "level1" / "level2" / "deep_file.txt").read_text() == "deep"


# =============================================================================
# sync_plan_to_source (Alias) Tests
# =============================================================================

class TestSyncPlanToSource:
    """Tests for sync_plan_to_source alias function."""

    def test_alias_works(self):
        """Test that the alias function works."""
        with tempfile.TemporaryDirectory() as td:
            worktree_dir = Path(td).resolve() / "worktree"
            source_dir = Path(td).resolve() / "source"
            worktree_dir.mkdir()
            source_dir.mkdir()

            # Create a file to sync
            (worktree_dir / "test.txt").write_text("test")

            result = sync_plan_to_source(worktree_dir, source_dir)
            assert result is True
            assert (source_dir / "test.txt").exists()

    def test_alias_returns_false_for_same_dir(self):
        """Test alias with same directory."""
        with tempfile.TemporaryDirectory() as td:
            dir_path = Path(td).resolve()
            result = sync_plan_to_source(dir_path, dir_path)
            assert result is False


# =============================================================================
# Integration Tests
# =============================================================================

class TestAgentsUtilsIntegration:
    """Integration tests for agents utils module."""

    def test_plan_workflow(self):
        """Test loading plan and finding subtasks."""
        with tempfile.TemporaryDirectory() as td:
            spec_dir = Path(td)

            # Create a realistic plan
            plan = {
                "spec_name": "auth-feature",
                "phases": [
                    {
                        "id": "1",
                        "name": "Setup",
                        "subtasks": [
                            {"id": "1.1", "description": "Create models", "status": "completed"},
                            {"id": "1.2", "description": "Create migrations", "status": "pending"},
                        ]
                    },
                    {
                        "id": "2",
                        "name": "Implementation",
                        "subtasks": [
                            {"id": "2.1", "description": "Implement login", "status": "pending"},
                            {"id": "2.2", "description": "Implement logout", "status": "pending"},
                        ]
                    }
                ]
            }
            (spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

            # Load the plan
            loaded_plan = load_implementation_plan(spec_dir)
            assert loaded_plan is not None

            # Find subtask
            subtask = find_subtask_in_plan(loaded_plan, "2.1")
            assert subtask is not None
            assert subtask["description"] == "Implement login"

            # Find phase for subtask
            phase = find_phase_for_subtask(loaded_plan, "2.1")
            assert phase is not None
            assert phase["name"] == "Implementation"

    def test_sync_realistic_spec_directory(self):
        """Test syncing a realistic spec directory structure."""
        with tempfile.TemporaryDirectory() as worktree_td:
            with tempfile.TemporaryDirectory() as source_td:
                worktree_dir = Path(worktree_td).resolve()
                source_dir = Path(source_td).resolve()

                # Create realistic spec structure
                (worktree_dir / "implementation_plan.json").write_text('{"status": "in_progress"}')
                (worktree_dir / "spec.md").write_text("# Specification")
                (worktree_dir / "context.json").write_text('{"files": []}')
                (worktree_dir / "build-progress.txt").write_text("Session 1: Started work")

                # Memory directory
                memory_dir = worktree_dir / "memory"
                memory_dir.mkdir()
                (memory_dir / "codebase_map.json").write_text('{"structure": {}}')
                (memory_dir / "patterns.json").write_text('{"patterns": []}')

                # Sync
                result = sync_spec_to_source(worktree_dir, source_dir)
                assert result is True

                # Verify all files synced
                assert (source_dir / "implementation_plan.json").exists()
                assert (source_dir / "spec.md").exists()
                assert (source_dir / "context.json").exists()
                assert (source_dir / "build-progress.txt").exists()
                assert (source_dir / "memory" / "codebase_map.json").exists()
                assert (source_dir / "memory" / "patterns.json").exists()
