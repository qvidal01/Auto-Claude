#!/usr/bin/env python3
"""
Tests for CLI Command Handlers
================================

Tests the CLI modules (workspace_commands.py, build_commands.py, followup_commands.py)
covering:
- Command argument parsing and validation
- Workspace creation/listing/cleanup commands
- Build command execution flows
- Followup review commands
- Error handling for invalid arguments
"""

import sys
from pathlib import Path

# Add apps/backend directory to path for imports
_backend_dir = Path(__file__).parent.parent / "apps" / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import json
import subprocess
from unittest.mock import MagicMock, Mock, patch, call

import pytest


# =============================================================================
# WORKSPACE COMMANDS TESTS
# =============================================================================


class TestWorkspaceCommands:
    """Tests for workspace_commands.py functions."""

    def test_detect_default_branch_env_var(self, temp_git_repo, monkeypatch):
        """Detects default branch from DEFAULT_BRANCH environment variable."""
        from cli.workspace_commands import _detect_default_branch

        # Set env var
        monkeypatch.setenv("DEFAULT_BRANCH", "develop")

        # Create develop branch
        subprocess.run(["git", "checkout", "-b", "develop"], cwd=temp_git_repo, capture_output=True)

        branch = _detect_default_branch(temp_git_repo)
        assert branch == "develop"

    def test_detect_default_branch_main(self, temp_git_repo):
        """Detects main as default branch when it exists."""
        from cli.workspace_commands import _detect_default_branch

        # temp_git_repo already has main branch
        branch = _detect_default_branch(temp_git_repo)
        assert branch == "main"

    def test_detect_default_branch_master(self, temp_git_repo):
        """Detects master as default branch when main doesn't exist."""
        from cli.workspace_commands import _detect_default_branch

        # Rename main to master
        subprocess.run(["git", "branch", "-m", "main", "master"], cwd=temp_git_repo, capture_output=True)

        branch = _detect_default_branch(temp_git_repo)
        assert branch == "master"

    def test_detect_default_branch_fallback(self, temp_git_repo):
        """Falls back to 'main' when no branches exist."""
        from cli.workspace_commands import _detect_default_branch

        # Delete all branches (edge case)
        # Since we can't delete the current branch, this tests the fallback logic
        # when neither main nor master exist
        subprocess.run(["git", "branch", "-m", "main", "feature"], cwd=temp_git_repo, capture_output=True)

        branch = _detect_default_branch(temp_git_repo)
        # Should fall back to "main" as final default
        assert branch == "main"

    def test_get_changed_files_from_git(self, temp_git_repo, make_commit):
        """Gets list of files changed in a worktree using merge-base."""
        from cli.workspace_commands import _get_changed_files_from_git

        # Create a branch
        subprocess.run(["git", "checkout", "-b", "feature"], cwd=temp_git_repo, capture_output=True)

        # Make changes in the branch
        make_commit("new_file.py", "# New file", "Add new file")
        make_commit("another.py", "# Another", "Add another")

        # Get changed files
        files = _get_changed_files_from_git(temp_git_repo, base_branch="main")

        assert "new_file.py" in files
        assert "another.py" in files
        assert len(files) == 2

    def test_get_changed_files_git_error(self, temp_git_repo):
        """Handles git errors gracefully when merge-base fails."""
        from cli.workspace_commands import _get_changed_files_from_git

        # Try to get changed files against non-existent branch
        files = _get_changed_files_from_git(temp_git_repo, base_branch="nonexistent")

        # Should return empty list on error
        assert files == []

    def test_detect_worktree_base_branch_from_config(self, temp_git_repo):
        """Detects base branch from worktree config file."""
        from cli.workspace_commands import _detect_worktree_base_branch

        # Create .auto-claude directory with worktree config
        auto_claude_dir = temp_git_repo / ".auto-claude"
        auto_claude_dir.mkdir(parents=True)

        config = {"base_branch": "develop", "spec_name": "001-test"}
        config_file = auto_claude_dir / "worktree-config.json"
        config_file.write_text(json.dumps(config))

        branch = _detect_worktree_base_branch(temp_git_repo, temp_git_repo, "001-test")
        assert branch == "develop"

    def test_detect_worktree_base_branch_from_git_history(self, temp_git_repo):
        """Detects base branch from git merge-base analysis."""
        from cli.workspace_commands import _detect_worktree_base_branch

        # Create a spec branch
        subprocess.run(["git", "checkout", "-b", "auto-claude/001-test"], cwd=temp_git_repo, capture_output=True)

        branch = _detect_worktree_base_branch(temp_git_repo, temp_git_repo, "001-test")
        # Should detect main as the base
        assert branch == "main"

    def test_detect_worktree_base_branch_no_detection(self, temp_git_repo):
        """Returns None when base branch cannot be detected."""
        from cli.workspace_commands import _detect_worktree_base_branch

        # Try to detect for non-existent spec
        branch = _detect_worktree_base_branch(temp_git_repo, temp_git_repo, "nonexistent")
        assert branch is None

    @patch("cli.workspace_commands.merge_existing_build")
    def test_handle_merge_command_success(self, mock_merge, temp_git_repo, spec_dir):
        """Successfully handles merge command."""
        from cli.workspace_commands import handle_merge_command

        mock_merge.return_value = True

        result = handle_merge_command(temp_git_repo, "001-test", no_commit=False)

        assert result is True
        mock_merge.assert_called_once_with(temp_git_repo, "001-test", no_commit=False, base_branch=None)

    @patch("cli.workspace_commands.merge_existing_build")
    @patch("cli.workspace_commands._generate_and_save_commit_message")
    def test_handle_merge_command_no_commit(self, mock_generate_msg, mock_merge, temp_git_repo, spec_dir):
        """Generates commit message when no_commit mode is used."""
        from cli.workspace_commands import handle_merge_command

        mock_merge.return_value = True

        result = handle_merge_command(temp_git_repo, "001-test", no_commit=True)

        assert result is True
        mock_merge.assert_called_once()
        mock_generate_msg.assert_called_once_with(temp_git_repo, "001-test")

    @patch("cli.workspace_commands.review_existing_build")
    def test_handle_review_command(self, mock_review, temp_git_repo):
        """Handles review command."""
        from cli.workspace_commands import handle_review_command

        handle_review_command(temp_git_repo, "001-test")

        mock_review.assert_called_once_with(temp_git_repo, "001-test")

    @patch("cli.workspace_commands.discard_existing_build")
    def test_handle_discard_command(self, mock_discard, temp_git_repo):
        """Handles discard command."""
        from cli.workspace_commands import handle_discard_command

        handle_discard_command(temp_git_repo, "001-test")

        mock_discard.assert_called_once_with(temp_git_repo, "001-test")

    @patch("cli.workspace_commands.list_all_worktrees")
    @patch("cli.workspace_commands.print_banner")
    def test_handle_list_worktrees_command_empty(self, mock_banner, mock_list, temp_git_repo, capsys):
        """Lists worktrees when none exist."""
        from cli.workspace_commands import handle_list_worktrees_command

        mock_list.return_value = []

        handle_list_worktrees_command(temp_git_repo)

        mock_banner.assert_called_once()
        mock_list.assert_called_once_with(temp_git_repo)

        captured = capsys.readouterr()
        assert "No worktrees found" in captured.out

    @patch("cli.workspace_commands.list_all_worktrees")
    @patch("cli.workspace_commands.print_banner")
    def test_handle_list_worktrees_command_with_worktrees(self, mock_banner, mock_list, temp_git_repo, capsys):
        """Lists worktrees when they exist."""
        from cli.workspace_commands import handle_list_worktrees_command

        # Mock worktree data
        mock_worktree = MagicMock()
        mock_worktree.spec_name = "001-test-feature"
        mock_worktree.branch = "auto-claude/001-test-feature"
        mock_worktree.path = str(temp_git_repo / ".auto-claude" / "worktrees" / "001-test-feature")
        mock_worktree.commit_count = 5
        mock_worktree.files_changed = 10

        mock_list.return_value = [mock_worktree]

        handle_list_worktrees_command(temp_git_repo)

        mock_list.assert_called_once_with(temp_git_repo)

        captured = capsys.readouterr()
        assert "001-test-feature" in captured.out
        assert "auto-claude/001-test-feature" in captured.out

    @patch("cli.workspace_commands.cleanup_all_worktrees")
    @patch("cli.workspace_commands.print_banner")
    def test_handle_cleanup_worktrees_command(self, mock_banner, mock_cleanup, temp_git_repo):
        """Handles cleanup worktrees command."""
        from cli.workspace_commands import handle_cleanup_worktrees_command

        handle_cleanup_worktrees_command(temp_git_repo)

        mock_banner.assert_called_once()
        mock_cleanup.assert_called_once_with(temp_git_repo, confirm=True)

    def test_check_git_merge_conflicts_no_conflicts(self, temp_git_repo):
        """Detects when no git conflicts exist."""
        from cli.workspace_commands import _check_git_merge_conflicts

        # Create a feature branch with no conflicts
        subprocess.run(["git", "checkout", "-b", "auto-claude/001-test"], cwd=temp_git_repo, capture_output=True)

        result = _check_git_merge_conflicts(temp_git_repo, "001-test", base_branch="main")

        assert result["has_conflicts"] is False
        assert result["conflicting_files"] == []

    def test_check_git_merge_conflicts_with_conflicts(self, temp_git_repo, make_commit):
        """Detects when git conflicts exist."""
        from cli.workspace_commands import _check_git_merge_conflicts

        # Create conflicting changes on main
        make_commit("conflict.py", "# Main version", "Main commit")

        # Create feature branch from before main changes
        subprocess.run(["git", "checkout", "HEAD~1"], cwd=temp_git_repo, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "auto-claude/001-test"], cwd=temp_git_repo, capture_output=True)
        make_commit("conflict.py", "# Feature version", "Feature commit")

        # Switch back to main
        subprocess.run(["git", "checkout", "main"], cwd=temp_git_repo, capture_output=True)

        result = _check_git_merge_conflicts(temp_git_repo, "001-test", base_branch="main")

        assert result["has_conflicts"] is True
        assert "conflict.py" in result["conflicting_files"]

    @patch("workspace.get_existing_build_worktree")
    @patch("cli.workspace_commands._get_changed_files_from_git")
    @patch("cli.workspace_commands._check_git_merge_conflicts")
    @patch("cli.workspace_commands._detect_parallel_task_conflicts")
    def test_handle_merge_preview_command_success(
        self, mock_parallel, mock_git_conflicts, mock_changed_files, mock_get_worktree, temp_git_repo, spec_dir
    ):
        """Handles merge preview command successfully."""
        from cli.workspace_commands import handle_merge_preview_command

        # Setup mocks
        mock_get_worktree.return_value = temp_git_repo
        mock_changed_files.return_value = ["file1.py", "file2.py"]
        mock_git_conflicts.return_value = {
            "has_conflicts": False,
            "conflicting_files": [],
            "needs_rebase": False,
            "base_branch": "main",
            "spec_branch": "auto-claude/001-test",
            "commits_behind": 0,
        }
        mock_parallel.return_value = []

        result = handle_merge_preview_command(temp_git_repo, "001-test")

        # Check that success is True
        assert result["success"] is True
        assert result["files"] == ["file1.py", "file2.py"]
        assert result["summary"]["totalFiles"] == 2

    @patch("workspace.get_existing_build_worktree")
    def test_handle_merge_preview_command_no_worktree(self, mock_get_worktree, temp_git_repo):
        """Returns error when no worktree exists."""
        from cli.workspace_commands import handle_merge_preview_command

        mock_get_worktree.return_value = None

        result = handle_merge_preview_command(temp_git_repo, "001-test")

        assert result["success"] is False
        assert "No existing build found" in result["error"]

    @patch("cli.workspace_commands.get_existing_build_worktree")
    @patch("cli.workspace_commands.print_banner")
    def test_handle_create_pr_command_creates_manager(self, mock_banner, mock_get_worktree, temp_git_repo):
        """Verifies create PR command initializes WorktreeManager when worktree exists."""
        from cli.workspace_commands import handle_create_pr_command

        # Return a valid worktree path
        mock_get_worktree.return_value = temp_git_repo

        # Mock WorktreeManager - must patch at core.worktree since it's imported inside the function
        with patch("core.worktree.WorktreeManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.base_branch = "main"
            # Simulate PR creation error (since we don't have real git setup)
            mock_manager.push_and_create_pr.side_effect = Exception("Test error")
            mock_manager_class.return_value = mock_manager

            result = handle_create_pr_command(temp_git_repo, "001-test", title="Test PR")

            # Should initialize WorktreeManager and attempt PR creation
            mock_manager_class.assert_called_once()
            mock_manager.push_and_create_pr.assert_called_once()
            # Result should indicate failure due to exception
            assert result["success"] is False

    @patch("cli.workspace_commands.get_existing_build_worktree")
    @patch("cli.workspace_commands.print_banner")
    def test_handle_create_pr_command_no_worktree(self, mock_banner, mock_get_worktree, temp_git_repo):
        """Returns error when no worktree exists for PR creation."""
        from cli.workspace_commands import handle_create_pr_command

        mock_get_worktree.return_value = None

        result = handle_create_pr_command(temp_git_repo, "001-test")

        assert result["success"] is False
        assert "No build found" in result["error"]

    def test_cleanup_old_worktrees_command_success(self, temp_git_repo):
        """Handles cleanup old worktrees command successfully."""
        from cli.workspace_commands import cleanup_old_worktrees_command

        with patch("cli.workspace_commands.WorktreeManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.cleanup_old_worktrees.return_value = (["001-old"], [])
            mock_manager_class.return_value = mock_manager

            result = cleanup_old_worktrees_command(temp_git_repo, days=30, dry_run=False)

            assert result["success"] is True
            assert result["removed"] == ["001-old"]
            assert result["days_threshold"] == 30

    def test_worktree_summary_command(self, temp_git_repo):
        """Handles worktree summary command."""
        from cli.workspace_commands import worktree_summary_command

        with patch("cli.workspace_commands.WorktreeManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_worktree = MagicMock()
            mock_worktree.spec_name = "001-test"
            mock_worktree.days_since_last_commit = 5
            mock_worktree.commit_count = 3

            mock_manager.list_all_worktrees.return_value = [mock_worktree]
            mock_manager.get_worktree_count_warning.return_value = None
            mock_manager_class.return_value = mock_manager

            result = worktree_summary_command(temp_git_repo)

            assert result["success"] is True
            assert result["total_worktrees"] == 1
            assert len(result["categories"]["recent"]) == 1


# =============================================================================
# BUILD COMMANDS TESTS
# =============================================================================


class TestBuildCommands:
    """Tests for build_commands.py functions."""

    @patch("cli.build_commands.ReviewState")
    @patch("cli.utils.validate_environment")
    @patch("workspace.get_existing_build_worktree")
    @patch("workspace.choose_workspace")
    @patch("agent.run_autonomous_agent")
    @patch("qa_loop.should_run_qa")
    @patch("cli.utils.print_banner")
    def test_handle_build_command_success(
        self,
        mock_banner,
        mock_should_qa,
        mock_run_agent,
        mock_choose_workspace,
        mock_get_worktree,
        mock_validate,
        mock_review_state_class,
        temp_git_repo,
        spec_dir,
    ):
        """Handles build command successfully."""
        from cli.build_commands import handle_build_command
        from workspace import WorkspaceMode

        # Setup mocks
        mock_review_state = MagicMock()
        mock_review_state.is_approval_valid.return_value = True
        mock_review_state.approved = True
        mock_review_state_class.load.return_value = mock_review_state

        mock_validate.return_value = True
        mock_get_worktree.return_value = None
        mock_choose_workspace.return_value = WorkspaceMode.DIRECT
        mock_should_qa.return_value = False

        # Mock asyncio.run to avoid actually running the agent
        with patch("cli.build_commands.asyncio.run"):
            handle_build_command(
                project_dir=temp_git_repo,
                spec_dir=spec_dir,
                model="sonnet",
                max_iterations=None,
                verbose=False,
                force_isolated=False,
                force_direct=True,
                auto_continue=False,
                skip_qa=True,
                force_bypass_approval=False,
            )

        mock_validate.assert_called_once_with(spec_dir)

    @patch("cli.build_commands.ReviewState")
    @patch("cli.utils.print_banner")
    def test_handle_build_command_approval_required(
        self, mock_banner, mock_review_state_class, temp_git_repo, spec_dir
    ):
        """Exits when spec approval is required."""
        from cli.build_commands import handle_build_command

        # Setup mock to fail approval
        mock_review_state = MagicMock()
        mock_review_state.is_approval_valid.return_value = False
        mock_review_state.approved = False
        mock_review_state_class.load.return_value = mock_review_state

        with pytest.raises(SystemExit):
            handle_build_command(
                project_dir=temp_git_repo,
                spec_dir=spec_dir,
                model="sonnet",
                max_iterations=None,
                verbose=False,
                force_isolated=False,
                force_direct=False,
                auto_continue=False,
                skip_qa=False,
                force_bypass_approval=False,
            )

    @patch("cli.build_commands.ReviewState")
    @patch("cli.utils.print_banner")
    def test_handle_build_command_force_bypass_approval(
        self, mock_banner, mock_review_state_class, temp_git_repo, spec_dir
    ):
        """Allows bypassing approval check with --force flag."""
        from cli.build_commands import handle_build_command

        # Setup mock to fail approval
        mock_review_state = MagicMock()
        mock_review_state.is_approval_valid.return_value = False
        mock_review_state.approved = False
        mock_review_state_class.load.return_value = mock_review_state

        # Should not raise SystemExit when force_bypass_approval=True
        with patch("cli.utils.validate_environment", return_value=True), \
             patch("workspace.get_existing_build_worktree", return_value=None), \
             patch("workspace.choose_workspace"), \
             patch("cli.build_commands.asyncio.run"):
            handle_build_command(
                project_dir=temp_git_repo,
                spec_dir=spec_dir,
                model="sonnet",
                max_iterations=None,
                verbose=False,
                force_isolated=False,
                force_direct=True,
                auto_continue=False,
                skip_qa=True,
                force_bypass_approval=True,  # Bypass approval
            )

    @patch("cli.build_commands.StatusManager")
    @patch("cli.build_commands.select_menu")
    @patch("cli.build_commands.read_multiline_input")
    def test_handle_build_interrupt_with_input(
        self, mock_read_input, mock_select_menu, mock_status_manager_class, temp_git_repo, spec_dir
    ):
        """Handles keyboard interrupt and saves user input."""
        from cli.build_commands import _handle_build_interrupt

        mock_status_manager = MagicMock()
        mock_status_manager_class.return_value = mock_status_manager

        mock_select_menu.return_value = "type"
        mock_read_input.return_value = "Fix the bug in file.py"

        # Should not raise when input is provided (only when quit is selected)
        _handle_build_interrupt(
            spec_dir=spec_dir,
            project_dir=temp_git_repo,
            worktree_manager=None,
            working_dir=temp_git_repo,
            model="sonnet",
            max_iterations=None,
            verbose=False,
        )

        # Check that input was saved
        input_file = spec_dir / "HUMAN_INPUT.md"
        assert input_file.exists()
        assert input_file.read_text() == "Fix the bug in file.py"

    @patch("cli.build_commands.StatusManager")
    @patch("cli.build_commands.select_menu")
    def test_handle_build_interrupt_quit(self, mock_select_menu, mock_status_manager_class, temp_git_repo, spec_dir):
        """Handles keyboard interrupt when user quits."""
        from cli.build_commands import _handle_build_interrupt

        mock_status_manager = MagicMock()
        mock_status_manager_class.return_value = mock_status_manager

        mock_select_menu.return_value = "quit"

        with pytest.raises(SystemExit):
            _handle_build_interrupt(
                spec_dir=spec_dir,
                project_dir=temp_git_repo,
                worktree_manager=None,
                working_dir=temp_git_repo,
                model="sonnet",
                max_iterations=None,
                verbose=False,
            )

        mock_status_manager.set_inactive.assert_called_once()


# =============================================================================
# FOLLOWUP COMMANDS TESTS
# =============================================================================


class TestFollowupCommands:
    """Tests for followup_commands.py functions."""

    @patch("cli.followup_commands.select_menu")
    @patch("builtins.input")
    def test_collect_followup_task_type(self, mock_input, mock_select_menu, spec_dir):
        """Collects followup task by typing."""
        from cli.followup_commands import collect_followup_task

        mock_select_menu.return_value = "type"
        # Simulate multiline input: two lines then empty line
        mock_input.side_effect = ["Add user profile page", ""]

        result = collect_followup_task(spec_dir)

        assert result == "Add user profile page"
        assert (spec_dir / "FOLLOWUP_REQUEST.md").exists()

    @patch("cli.followup_commands.select_menu")
    @patch("builtins.input")
    def test_collect_followup_task_file(self, mock_input, mock_select_menu, spec_dir, temp_dir):
        """Collects followup task from file."""
        from cli.followup_commands import collect_followup_task

        # Create a file with task description
        task_file = temp_dir / "task.txt"
        task_file.write_text("Add search functionality")

        mock_select_menu.return_value = "file"
        mock_input.return_value = str(task_file)

        result = collect_followup_task(spec_dir)

        assert result == "Add search functionality"

    @patch("cli.followup_commands.select_menu")
    def test_collect_followup_task_cancel(self, mock_select_menu, spec_dir):
        """Returns None when user cancels."""
        from cli.followup_commands import collect_followup_task

        mock_select_menu.return_value = "quit"

        result = collect_followup_task(spec_dir)

        assert result is None

    @patch("cli.followup_commands.select_menu")
    @patch("builtins.input")
    def test_collect_followup_task_empty_retry(self, mock_input, mock_select_menu, spec_dir):
        """Retries when empty input is provided."""
        from cli.followup_commands import collect_followup_task

        # First return empty, then valid input
        mock_select_menu.side_effect = ["type", "type"]
        # First: empty line, Second: "Valid task" + empty line
        mock_input.side_effect = ["", "Valid task", ""]

        result = collect_followup_task(spec_dir, max_retries=3)

        assert result == "Valid task"
        assert mock_select_menu.call_count == 2

    @patch("agent.run_followup_planner")
    @patch("cli.followup_commands.collect_followup_task")
    @patch("cli.utils.validate_environment")
    @patch("cli.followup_commands.is_build_complete")
    @patch("cli.utils.print_banner")
    def test_handle_followup_command_success(
        self,
        mock_banner,
        mock_build_complete,
        mock_validate,
        mock_collect_task,
        mock_run_planner,
        temp_git_repo,
        spec_dir,
    ):
        """Handles followup command successfully."""
        from cli.followup_commands import handle_followup_command

        # Create implementation_plan.json
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps({"phases": []}))

        mock_build_complete.return_value = True
        mock_validate.return_value = True
        mock_collect_task.return_value = "Add feature X"

        # Mock asyncio.run
        with patch("cli.followup_commands.asyncio.run", return_value=True):
            handle_followup_command(temp_git_repo, spec_dir, model="sonnet", verbose=False)

        mock_collect_task.assert_called_once()

    @patch("cli.utils.print_banner")
    def test_handle_followup_command_no_plan(self, mock_banner, temp_git_repo, spec_dir):
        """Exits when no implementation plan exists."""
        from cli.followup_commands import handle_followup_command

        # Don't create implementation_plan.json

        with pytest.raises(SystemExit):
            handle_followup_command(temp_git_repo, spec_dir, model="sonnet", verbose=False)

    @patch("cli.followup_commands.is_build_complete")
    @patch("cli.followup_commands.count_subtasks")
    @patch("cli.utils.print_banner")
    def test_handle_followup_command_build_not_complete(
        self, mock_banner, mock_count_subtasks, mock_build_complete, temp_git_repo, spec_dir
    ):
        """Exits when build is not complete."""
        from cli.followup_commands import handle_followup_command

        # Create implementation_plan.json
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps({"phases": []}))

        mock_build_complete.return_value = False
        mock_count_subtasks.return_value = (3, 5)  # 3 completed, 5 total

        with pytest.raises(SystemExit):
            handle_followup_command(temp_git_repo, spec_dir, model="sonnet", verbose=False)

    @patch("agent.run_followup_planner")
    @patch("cli.followup_commands.collect_followup_task")
    @patch("cli.utils.validate_environment")
    @patch("cli.followup_commands.is_build_complete")
    @patch("cli.utils.print_banner")
    def test_handle_followup_command_user_cancelled(
        self,
        mock_banner,
        mock_build_complete,
        mock_validate,
        mock_collect_task,
        mock_run_planner,
        temp_git_repo,
        spec_dir,
    ):
        """Exits gracefully when user cancels followup collection."""
        from cli.followup_commands import handle_followup_command

        # Create implementation_plan.json
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps({"phases": []}))

        mock_build_complete.return_value = True
        mock_collect_task.return_value = None  # User cancelled

        handle_followup_command(temp_git_repo, spec_dir, model="sonnet", verbose=False)

        # Should not call run_followup_planner
        mock_run_planner.assert_not_called()


# =============================================================================
# CLI UTILS TESTS
# =============================================================================


class TestCliUtils:
    """Tests for cli/utils.py functions."""

    def test_find_spec_exact_match(self, temp_git_repo):
        """Finds spec by exact name match."""
        from cli.utils import find_spec

        # Create specs directory
        specs_dir = temp_git_repo / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)

        spec_dir = specs_dir / "001-test-feature"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Test")

        result = find_spec(temp_git_repo, "001-test-feature")
        assert result == spec_dir

    def test_find_spec_by_number_prefix(self, temp_git_repo):
        """Finds spec by number prefix."""
        from cli.utils import find_spec

        specs_dir = temp_git_repo / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)

        spec_dir = specs_dir / "001-test-feature"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Test")

        result = find_spec(temp_git_repo, "001")
        assert result == spec_dir

    def test_find_spec_not_found(self, temp_git_repo):
        """Returns None when spec not found."""
        from cli.utils import find_spec

        result = find_spec(temp_git_repo, "999")
        assert result is None

    @patch("core.auth.get_auth_token")
    @patch("core.auth.get_auth_token_source")
    @patch("core.dependency_validator.validate_platform_dependencies")
    @patch("linear_updater.is_linear_enabled")
    @patch("graphiti_config.get_graphiti_status")
    def test_validate_environment_success(
        self, mock_graphiti, mock_linear, mock_validate_deps, mock_token_source, mock_token, spec_dir
    ):
        """Validates environment successfully."""
        from cli.utils import validate_environment

        # Create spec.md
        (spec_dir / "spec.md").write_text("# Test")

        mock_token.return_value = "sk-ant-oat01-test"
        mock_token_source.return_value = "CLAUDE_CODE_OAUTH_TOKEN"
        mock_linear.return_value = False
        mock_graphiti.return_value = {"available": False, "enabled": False}

        result = validate_environment(spec_dir)
        assert result is True

    @patch("cli.utils.get_auth_token")
    @patch("core.dependency_validator.validate_platform_dependencies")
    def test_validate_environment_no_token(self, mock_validate_deps, mock_token, spec_dir):
        """Fails validation when no auth token."""
        from cli.utils import validate_environment

        (spec_dir / "spec.md").write_text("# Test")
        mock_token.return_value = None

        result = validate_environment(spec_dir)
        assert result is False

    @patch("core.auth.get_auth_token")
    @patch("core.auth.get_auth_token_source")
    @patch("core.dependency_validator.validate_platform_dependencies")
    @patch("linear_updater.is_linear_enabled")
    @patch("graphiti_config.get_graphiti_status")
    def test_validate_environment_no_spec_file(
        self, mock_graphiti, mock_linear, mock_validate_deps, mock_token_source, mock_token, spec_dir
    ):
        """Fails validation when spec.md missing."""
        from cli.utils import validate_environment

        # Don't create spec.md
        mock_token.return_value = "sk-ant-oat01-test"
        mock_token_source.return_value = "CLAUDE_CODE_OAUTH_TOKEN"

        result = validate_environment(spec_dir)
        assert result is False


# =============================================================================
# INPUT HANDLERS TESTS
# =============================================================================


class TestInputHandlers:
    """Tests for cli/input_handlers.py functions."""

    @patch("builtins.input")
    def test_read_from_file_success(self, mock_input, temp_dir):
        """Reads file successfully."""
        from cli.input_handlers import read_from_file

        # Create a test file
        test_file = temp_dir / "input.txt"
        test_file.write_text("Test content")

        mock_input.return_value = str(test_file)

        result = read_from_file()
        assert result == "Test content"

    @patch("builtins.input")
    def test_read_from_file_not_found(self, mock_input):
        """Returns None when file not found."""
        from cli.input_handlers import read_from_file

        mock_input.return_value = "/nonexistent/file.txt"

        result = read_from_file()
        assert result is None

    @patch("builtins.input")
    def test_read_from_file_cancelled(self, mock_input):
        """Returns None when user cancels."""
        from cli.input_handlers import read_from_file

        mock_input.side_effect = KeyboardInterrupt()

        result = read_from_file()
        assert result is None

    @patch("builtins.input")
    def test_read_multiline_input_success(self, mock_input):
        """Reads multiline input successfully."""
        from cli.input_handlers import read_multiline_input

        # Simulate user typing multiple lines then empty line
        mock_input.side_effect = ["Line 1", "Line 2", ""]

        result = read_multiline_input("Enter text:")
        assert result == "Line 1\nLine 2"

    @patch("builtins.input")
    def test_read_multiline_input_cancelled(self, mock_input):
        """Returns None when user cancels."""
        from cli.input_handlers import read_multiline_input

        mock_input.side_effect = KeyboardInterrupt()

        result = read_multiline_input("Enter text:")
        assert result is None

    @patch("cli.input_handlers.select_menu")
    @patch("builtins.input")
    def test_collect_user_input_interactive_type(self, mock_input, mock_select_menu):
        """Collects input via typing."""
        from cli.input_handlers import collect_user_input_interactive

        mock_select_menu.return_value = "type"
        mock_input.side_effect = ["User input", ""]

        result = collect_user_input_interactive("Title", "Subtitle", "Prompt")
        assert result == "User input"

    @patch("cli.input_handlers.select_menu")
    def test_collect_user_input_interactive_skip(self, mock_select_menu):
        """Returns empty string when user skips."""
        from cli.input_handlers import collect_user_input_interactive

        mock_select_menu.return_value = "skip"

        result = collect_user_input_interactive("Title", "Subtitle", "Prompt")
        assert result == ""

    @patch("cli.input_handlers.select_menu")
    def test_collect_user_input_interactive_quit(self, mock_select_menu):
        """Returns None when user quits."""
        from cli.input_handlers import collect_user_input_interactive

        mock_select_menu.return_value = "quit"

        result = collect_user_input_interactive("Title", "Subtitle", "Prompt")
        assert result is None
