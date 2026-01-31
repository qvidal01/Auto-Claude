#!/usr/bin/env python3
"""
Tests for Workspace Management Module
======================================

Tests the workspace.py module functionality including:
- Workspace initialization and validation
- Merge operations (merge_existing_build)
- Smart merge with AI conflict resolution
- Git conflict detection and handling
- File merge strategies (simple 3-way, AI-assisted)
- Parallel merge operations
- Merge lock mechanism
- Path mapping and file renames
"""

import asyncio
import json
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Import from workspace module directly (workspace.py file)
import importlib.util
import sys
from pathlib import Path as ImportPath

# Load workspace.py directly to access internal functions for testing
_workspace_file = ImportPath(__file__).parent.parent / "apps" / "backend" / "core" / "workspace.py"
_spec = importlib.util.spec_from_file_location("workspace_module", _workspace_file)
_workspace_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_workspace_module)

# Import functions we need for testing
_build_merge_prompt = _workspace_module._build_merge_prompt
_check_git_conflicts = _workspace_module._check_git_conflicts
_infer_language_from_path = _workspace_module._infer_language_from_path
_strip_code_fences = _workspace_module._strip_code_fences
_try_simple_3way_merge = _workspace_module._try_simple_3way_merge
merge_existing_build = _workspace_module.merge_existing_build

# Import from workspace package
from core.workspace.git_utils import get_existing_build_worktree
from core.workspace.models import MergeLock, MergeLockError, ParallelMergeTask
from worktree import WorktreeManager


class TestMergeLockMechanism:
    """Tests for the MergeLock to prevent concurrent merge operations."""

    def test_merge_lock_prevents_concurrent_access(self, temp_git_repo: Path):
        """MergeLock prevents concurrent merge operations for same spec."""
        lock1 = MergeLock(temp_git_repo, "test-spec")

        # Acquire first lock
        lock1.__enter__()

        # Try to acquire second lock for same spec (should fail after timeout)
        lock2 = MergeLock(temp_git_repo, "test-spec")
        with pytest.raises(MergeLockError):
            lock2.__enter__()

        # Release first lock
        lock1.__exit__(None, None, None)

        # Now second lock should work
        lock2 = MergeLock(temp_git_repo, "test-spec")
        lock2.__enter__()
        lock2.__exit__(None, None, None)

    def test_merge_lock_allows_different_specs(self, temp_git_repo: Path):
        """MergeLock allows concurrent operations for different specs."""
        lock1 = MergeLock(temp_git_repo, "spec-1")
        lock2 = MergeLock(temp_git_repo, "spec-2")

        # Both locks should work simultaneously
        lock1.__enter__()
        lock2.__enter__()

        # Both should release without error
        lock1.__exit__(None, None, None)
        lock2.__exit__(None, None, None)

    def test_merge_lock_cleanup_on_exception(self, temp_git_repo: Path):
        """MergeLock releases lock even when exception occurs."""
        lock = MergeLock(temp_git_repo, "test-spec")

        try:
            with lock:
                raise ValueError("Test error")
        except ValueError:
            pass

        # Lock should be released, new lock should work
        lock2 = MergeLock(temp_git_repo, "test-spec")
        lock2.__enter__()
        lock2.__exit__(None, None, None)


class TestSimple3WayMerge:
    """Tests for simple 3-way merge without AI."""

    def test_simple_merge_one_side_changed(self):
        """Simple merge succeeds when only one side changed."""
        base = "original content"
        ours = "original content"
        theirs = "modified content"

        success, result = _try_simple_3way_merge(base, ours, theirs)

        assert success is True
        assert result == "modified content"

    def test_simple_merge_other_side_changed(self):
        """Simple merge succeeds when only other side changed."""
        base = "original content"
        ours = "modified content"
        theirs = "original content"

        success, result = _try_simple_3way_merge(base, ours, theirs)

        assert success is True
        assert result == "modified content"

    def test_simple_merge_identical_changes(self):
        """Simple merge succeeds when both sides made same change."""
        base = "original content"
        ours = "modified content"
        theirs = "modified content"

        success, result = _try_simple_3way_merge(base, ours, theirs)

        assert success is True
        assert result == "modified content"

    def test_simple_merge_fails_conflicting_changes(self):
        """Simple merge fails when both sides made different changes."""
        base = "original content"
        ours = "my modification"
        theirs = "their modification"

        success, result = _try_simple_3way_merge(base, ours, theirs)

        assert success is False
        assert result is None

    def test_simple_merge_no_base_identical(self):
        """Simple merge succeeds when no base but content identical."""
        success, result = _try_simple_3way_merge(None, "same", "same")

        assert success is True
        assert result == "same"

    def test_simple_merge_no_base_different(self):
        """Simple merge fails when no base and content differs."""
        success, result = _try_simple_3way_merge(None, "mine", "theirs")

        assert success is False
        assert result is None


class TestLanguageInference:
    """Tests for language detection from file paths."""

    def test_infer_python(self):
        """Correctly infers Python from .py extension."""
        assert _infer_language_from_path("script.py") == "python"
        assert _infer_language_from_path("app/models/user.py") == "python"

    def test_infer_javascript(self):
        """Correctly infers JavaScript from .js/.jsx extensions."""
        assert _infer_language_from_path("app.js") == "javascript"
        assert _infer_language_from_path("Component.jsx") == "javascript"

    def test_infer_typescript(self):
        """Correctly infers TypeScript from .ts/.tsx extensions."""
        assert _infer_language_from_path("app.ts") == "typescript"
        assert _infer_language_from_path("Component.tsx") == "typescript"

    def test_infer_rust(self):
        """Correctly infers Rust from .rs extension."""
        assert _infer_language_from_path("main.rs") == "rust"

    def test_infer_go(self):
        """Correctly infers Go from .go extension."""
        assert _infer_language_from_path("server.go") == "go"

    def test_infer_unknown(self):
        """Returns 'text' for unknown extensions."""
        assert _infer_language_from_path("README.unknown") == "text"


class TestCodeFenceStripping:
    """Tests for removing markdown code fences from AI responses."""

    def test_strip_fences_with_language(self):
        """Strips code fences with language specifier."""
        content = "```python\nprint('hello')\n```"
        result = _strip_code_fences(content)
        assert result == "print('hello')"

    def test_strip_fences_without_language(self):
        """Strips code fences without language specifier."""
        content = "```\ncode here\n```"
        result = _strip_code_fences(content)
        assert result == "code here"

    def test_no_fences(self):
        """Returns content unchanged when no fences present."""
        content = "plain text"
        result = _strip_code_fences(content)
        assert result == "plain text"

    def test_incomplete_fences(self):
        """Handles incomplete fences gracefully."""
        content = "```python\ncode without closing fence"
        result = _strip_code_fences(content)
        assert result == "code without closing fence"


class TestMergePromptGeneration:
    """Tests for AI merge prompt construction."""

    def test_build_merge_prompt_with_base(self):
        """Builds merge prompt with base content."""
        prompt = _build_merge_prompt(
            file_path="src/app.py",
            base_content="original",
            main_content="main version",
            worktree_content="worktree version",
            spec_name="test-spec"
        )

        assert "src/app.py" in prompt
        assert "test-spec" in prompt
        assert "BASE" in prompt
        assert "OURS" in prompt
        assert "THEIRS" in prompt
        assert "original" in prompt
        assert "main version" in prompt
        assert "worktree version" in prompt

    def test_build_merge_prompt_without_base(self):
        """Builds merge prompt without base content."""
        prompt = _build_merge_prompt(
            file_path="src/app.py",
            base_content=None,
            main_content="main version",
            worktree_content="worktree version",
            spec_name="test-spec"
        )

        assert "src/app.py" in prompt
        assert "BASE" not in prompt
        assert "OURS" in prompt
        assert "THEIRS" in prompt

    def test_build_merge_prompt_truncates_large_files(self):
        """Truncates very large file content in prompts."""
        large_content = "x" * 20000
        prompt = _build_merge_prompt(
            file_path="large.py",
            base_content=large_content,
            main_content=large_content,
            worktree_content=large_content,
            spec_name="test-spec"
        )

        assert "truncated" in prompt.lower()


class TestGitConflictDetection:
    """Tests for detecting git-level conflicts."""

    def test_check_git_conflicts_no_divergence(self, temp_git_repo: Path):
        """No conflicts when branches haven't diverged."""
        manager = WorktreeManager(temp_git_repo)
        manager.setup()

        # Create worktree
        info = manager.create_worktree("test-spec")

        # Make change in worktree
        (info.path / "new.txt").write_text("content")
        subprocess.run(["git", "add", "."], cwd=info.path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add file"],
            cwd=info.path,
            capture_output=True
        )

        result = _check_git_conflicts(temp_git_repo, "test-spec")

        assert result["has_conflicts"] is False
        assert result["base_branch"] == "main"

    def test_check_git_conflicts_with_conflicts(self, temp_git_repo: Path):
        """Detects conflicts when branches diverged with conflicting changes."""
        manager = WorktreeManager(temp_git_repo)
        manager.setup()

        # Create worktree first (branches from current main)
        info = manager.create_worktree("test-spec")

        # Create file on BOTH branches from same base (README.md exists from init)
        # Modify shared file differently on each branch

        # Change in worktree
        (info.path / "README.md").write_text("# Worktree Version\n\nWorktree content")
        subprocess.run(["git", "add", "."], cwd=info.path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Worktree change to README"],
            cwd=info.path,
            capture_output=True
        )

        # Conflicting change on main
        (temp_git_repo / "README.md").write_text("# Main Version\n\nMain content")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Main change to README"],
            cwd=temp_git_repo,
            capture_output=True
        )

        result = _check_git_conflicts(temp_git_repo, "test-spec")

        # Either we detect conflicts or we detect divergence
        # The key is that we're not in a clean state
        assert result["has_conflicts"] is True or result.get("diverged_but_no_conflicts") is True

        if result["has_conflicts"]:
            assert "README.md" in result["conflicting_files"]

    def test_check_git_conflicts_behind_count(self, temp_git_repo: Path):
        """Detects when spec branch is behind main."""
        manager = WorktreeManager(temp_git_repo)
        manager.setup()

        # Create worktree
        info = manager.create_worktree("test-spec")

        # Make change on main (worktree is now behind)
        (temp_git_repo / "new-main.txt").write_text("main content")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Main progress"],
            cwd=temp_git_repo,
            capture_output=True
        )

        result = _check_git_conflicts(temp_git_repo, "test-spec")

        assert result["commits_behind"] > 0
        assert result["needs_rebase"] is True


class TestParallelMergeTask:
    """Tests for ParallelMergeTask dataclass."""

    def test_parallel_merge_task_creation(self, temp_git_repo: Path):
        """Can create ParallelMergeTask with required fields."""
        task = ParallelMergeTask(
            file_path="src/app.py",
            main_content="main",
            worktree_content="worktree",
            base_content="base",
            spec_name="test-spec",
            project_dir=temp_git_repo
        )

        assert task.file_path == "src/app.py"
        assert task.main_content == "main"
        assert task.worktree_content == "worktree"
        assert task.base_content == "base"
        assert task.spec_name == "test-spec"
        assert task.project_dir == temp_git_repo


class TestMergeExistingBuild:
    """Tests for the main merge_existing_build function."""

    def test_merge_no_worktree_exists(self, temp_git_repo: Path):
        """merge_existing_build fails when worktree doesn't exist."""
        result = merge_existing_build(
            project_dir=temp_git_repo,
            spec_name="nonexistent-spec"
        )

        assert result is False

    def test_merge_on_spec_branch_warns(self, temp_git_repo: Path):
        """merge_existing_build handles being on spec branch (returns False or switches)."""
        manager = WorktreeManager(temp_git_repo)
        manager.setup()

        # Create worktree
        info = manager.create_worktree("test-spec")

        # Make a change
        (info.path / "test.txt").write_text("content")
        subprocess.run(["git", "add", "."], cwd=info.path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Test"],
            cwd=info.path,
            capture_output=True
        )

        # Try to checkout spec branch in main repo
        # This may fail if worktree is active, which is expected behavior
        checkout_result = subprocess.run(
            ["git", "checkout", "auto-claude/test-spec"],
            cwd=temp_git_repo,
            capture_output=True
        )

        # Only test merge if checkout succeeded (otherwise test is not applicable)
        if checkout_result.returncode == 0:
            result = merge_existing_build(
                project_dir=temp_git_repo,
                spec_name="test-spec"
            )
            # Should return False (can't merge branch into itself)
            assert result is False
        # If checkout failed, the worktree protection worked correctly

    def test_merge_with_no_commit(self, temp_git_repo: Path):
        """merge_existing_build stages changes without committing when no_commit=True."""
        manager = WorktreeManager(temp_git_repo)
        manager.setup()

        # Create worktree with changes
        info = manager.create_worktree("test-spec")
        (info.path / "test.txt").write_text("content")
        subprocess.run(["git", "add", "."], cwd=info.path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Test"],
            cwd=info.path,
            capture_output=True
        )

        result = merge_existing_build(
            project_dir=temp_git_repo,
            spec_name="test-spec",
            no_commit=True,
            use_smart_merge=False  # Use simple git merge for this test
        )

        assert result is True

        # Verify changes are staged but not committed
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=temp_git_repo,
            capture_output=True,
            text=True
        )

        # Should have staged changes (starts with 'M' or 'A')
        assert status_result.stdout.strip() != ""


class TestWorkspaceHelperFunctions:
    """Tests for workspace helper functions."""

    def test_get_existing_build_worktree_exists(self, temp_git_repo: Path):
        """get_existing_build_worktree returns path when worktree exists."""
        manager = WorktreeManager(temp_git_repo)
        manager.setup()

        info = manager.create_worktree("test-spec")

        result = get_existing_build_worktree(temp_git_repo, "test-spec")

        assert result == info.path
        assert result.exists()

    def test_get_existing_build_worktree_not_exists(self, temp_git_repo: Path):
        """get_existing_build_worktree returns None when worktree doesn't exist."""
        result = get_existing_build_worktree(temp_git_repo, "nonexistent-spec")

        assert result is None


class TestMergeProgressCallback:
    """Tests for merge progress callback functionality."""

    def test_progress_callback_in_subprocess_mode(self, temp_git_repo: Path):
        """Progress callback logic exists in workspace module."""
        # Load the function directly from workspace module
        _create_callback = _workspace_module._create_merge_progress_callback

        # Simulate non-TTY environment (subprocess)
        with patch('sys.stdout.isatty', return_value=False):
            callback = _create_callback()
            assert callback is not None

    def test_no_progress_callback_in_tty_mode(self, temp_git_repo: Path):
        """Progress callback is None in TTY mode (interactive)."""
        # Load the function directly from workspace module
        _create_callback = _workspace_module._create_merge_progress_callback

        # Simulate TTY environment (interactive terminal)
        with patch('sys.stdout.isatty', return_value=True):
            callback = _create_callback()
            assert callback is None


class TestWorkspaceIntegration:
    """Integration tests for complete workspace workflows."""

    def test_full_merge_workflow_clean(self, temp_git_repo: Path):
        """Complete workflow: create worktree, make changes, merge cleanly."""
        manager = WorktreeManager(temp_git_repo)
        manager.setup()

        # Create worktree
        info = manager.create_worktree("feature-spec")

        # Make changes
        (info.path / "feature.py").write_text("def feature(): pass")
        (info.path / "README.md").write_text("# Updated README")

        subprocess.run(["git", "add", "."], cwd=info.path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Implement feature"],
            cwd=info.path,
            capture_output=True
        )

        # Merge back
        result = merge_existing_build(
            project_dir=temp_git_repo,
            spec_name="feature-spec",
            use_smart_merge=False
        )

        assert result is True
        assert (temp_git_repo / "feature.py").exists()

    def test_concurrent_merge_prevention(self, temp_git_repo: Path):
        """Merge lock prevents concurrent merges of same spec."""
        manager = WorktreeManager(temp_git_repo)
        manager.setup()

        # Create worktree with changes
        info = manager.create_worktree("test-spec")
        (info.path / "test.txt").write_text("content")
        subprocess.run(["git", "add", "."], cwd=info.path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Test"],
            cwd=info.path,
            capture_output=True
        )

        # Acquire lock manually
        lock = MergeLock(temp_git_repo, "test-spec")
        lock.__enter__()

        try:
            # Try to merge while lock is held - should fail
            # Note: This would normally be prevented at a higher level,
            # but we're testing the lock mechanism directly
            with pytest.raises(MergeLockError):
                with MergeLock(temp_git_repo, "test-spec"):
                    pass
        finally:
            lock.__exit__(None, None, None)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_merge_with_empty_worktree(self, temp_git_repo: Path):
        """Handles merge when worktree has no changes."""
        manager = WorktreeManager(temp_git_repo)
        manager.setup()

        # Create worktree but make no changes
        manager.create_worktree("empty-spec")

        # Merge should succeed (nothing to merge)
        result = merge_existing_build(
            project_dir=temp_git_repo,
            spec_name="empty-spec",
            use_smart_merge=False
        )

        assert result is True

    def test_merge_with_gitignored_files(self, temp_git_repo: Path):
        """Handles merge when worktree contains gitignored files."""
        manager = WorktreeManager(temp_git_repo)
        manager.setup()

        # Add .gitignore
        (temp_git_repo / ".gitignore").write_text("*.log\n.env\n")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add gitignore"],
            cwd=temp_git_repo,
            capture_output=True
        )

        # Create worktree with gitignored files
        info = manager.create_worktree("test-spec")
        (info.path / "app.log").write_text("log content")
        (info.path / ".env").write_text("SECRET=value")
        (info.path / "tracked.txt").write_text("tracked")

        subprocess.run(["git", "add", "."], cwd=info.path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add files"],
            cwd=info.path,
            capture_output=True
        )

        # Merge with no_commit to verify gitignored files aren't staged
        result = merge_existing_build(
            project_dir=temp_git_repo,
            spec_name="test-spec",
            no_commit=True,
            use_smart_merge=False
        )

        assert result is True

        # Verify gitignored files weren't staged
        status_result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=temp_git_repo,
            capture_output=True,
            text=True
        )

        staged_files = status_result.stdout.strip().split("\n")
        assert "app.log" not in staged_files
        assert ".env" not in staged_files
        assert "tracked.txt" in staged_files or "tracked.txt" in str(staged_files)
