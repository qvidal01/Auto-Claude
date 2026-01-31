#!/usr/bin/env python3
"""
Test suite for GitLab runner CLI
=================================

Tests the GitLab runner CLI interface and configuration.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import json
import os

import pytest

# Add backend directory to path
_backend_dir = Path(__file__).parent.parent / "apps" / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

# Mock SDK modules before any runners imports to avoid import chain issues
if 'claude_agent_sdk' not in sys.modules:
    _mock_sdk = MagicMock()
    _mock_sdk.ClaudeSDKClient = MagicMock
    sys.modules['claude_agent_sdk'] = _mock_sdk
    sys.modules['claude_agent_sdk.types'] = MagicMock()

# Mock safe_print before importing runner
with patch('runners.gitlab.runner.safe_print'):
    from runners.gitlab.runner import get_config, print_progress
    from runners.gitlab.orchestrator import ProgressCallback
    from runners.gitlab.models import GitLabRunnerConfig


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def mock_args(temp_project_dir):
    """Create mock CLI arguments."""
    args = MagicMock()
    args.project_dir = temp_project_dir
    args.token = None
    args.project = None
    args.instance = "https://gitlab.com"
    args.model = "claude-sonnet-4-5-20250929"
    args.thinking_level = "medium"
    return args


class TestGetConfig:
    """Test configuration building from CLI args and environment."""

    def test_get_config_from_cli_args(self, mock_args):
        """Test config building from CLI arguments."""
        mock_args.token = "cli-token"
        mock_args.project = "cli-org/cli-project"

        config = get_config(mock_args)

        assert config.token == "cli-token"
        assert config.project == "cli-org/cli-project"
        assert config.instance_url == "https://gitlab.com"
        assert config.model == "claude-sonnet-4-5-20250929"
        assert config.thinking_level == "medium"

    def test_get_config_from_environment(self, mock_args, monkeypatch):
        """Test config building from environment variables."""
        monkeypatch.setenv("GITLAB_TOKEN", "env-token")
        monkeypatch.setenv("GITLAB_PROJECT", "env-org/env-project")
        # Note: GITLAB_INSTANCE_URL env var is not used by get_config,
        # only --instance CLI arg is used (defaults to https://gitlab.com)

        config = get_config(mock_args)

        assert config.token == "env-token"
        assert config.project == "env-org/env-project"
        # Default instance URL is used when not in config file
        assert config.instance_url == "https://gitlab.com"

    def test_get_config_from_project_file(self, mock_args, temp_project_dir):
        """Test config building from project config file."""
        config_dir = temp_project_dir / ".auto-claude" / "gitlab"
        config_dir.mkdir(parents=True)

        config_file = config_dir / "config.json"
        config_data = {
            "token": "file-token",
            "project": "file-org/file-project",
            "instance_url": "https://gitlab.file.com",
        }
        config_file.write_text(json.dumps(config_data))

        config = get_config(mock_args)

        assert config.token == "file-token"
        assert config.project == "file-org/file-project"
        assert config.instance_url == "https://gitlab.file.com"

    def test_get_config_cli_overrides_file(self, mock_args, temp_project_dir):
        """Test that CLI args override file config."""
        # Create file config
        config_dir = temp_project_dir / ".auto-claude" / "gitlab"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.json"
        config_data = {
            "token": "file-token",
            "project": "file-org/file-project",
        }
        config_file.write_text(json.dumps(config_data))

        # Set CLI args
        mock_args.token = "cli-token"
        mock_args.project = "cli-org/cli-project"

        config = get_config(mock_args)

        # CLI args should win
        assert config.token == "cli-token"
        assert config.project == "cli-org/cli-project"

    def test_get_config_file_overrides_env(self, mock_args, temp_project_dir, monkeypatch):
        """Test that file config overrides environment variables."""
        # Set env vars
        monkeypatch.setenv("GITLAB_TOKEN", "env-token")
        monkeypatch.setenv("GITLAB_PROJECT", "env-org/env-project")

        # Create file config
        config_dir = temp_project_dir / ".auto-claude" / "gitlab"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.json"
        config_data = {
            "project": "file-org/file-project",
        }
        config_file.write_text(json.dumps(config_data))

        config = get_config(mock_args)

        # File project should win, env token should be used
        assert config.token == "env-token"
        assert config.project == "file-org/file-project"

    def test_get_config_missing_token_exits(self, mock_args, capsys):
        """Test that missing token causes exit."""
        with pytest.raises(SystemExit) as exc_info:
            get_config(mock_args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        # Error is printed to stdout, not stderr
        output = captured.out + captured.err
        assert "No GitLab token found" in output

    def test_get_config_missing_project_exits(self, mock_args, monkeypatch, capsys):
        """Test that missing project causes exit."""
        monkeypatch.setenv("GITLAB_TOKEN", "test-token")

        with pytest.raises(SystemExit) as exc_info:
            get_config(mock_args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        # Error is printed to stdout, not stderr
        output = captured.out + captured.err
        assert "No GitLab project found" in output

    def test_get_config_from_glab_cli(self, mock_args, monkeypatch):
        """Test config retrieval from glab CLI."""
        # Remove env token
        monkeypatch.delenv("GITLAB_TOKEN", raising=False)
        monkeypatch.setenv("GITLAB_PROJECT", "test-org/test-project")

        # Mock glab auth status command
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Token: glab-cli-token\n"

        with patch('subprocess.run', return_value=mock_result):
            config = get_config(mock_args)

        assert config.token == "glab-cli-token"

    def test_get_config_glab_cli_not_found(self, mock_args, monkeypatch):
        """Test config when glab CLI is not installed."""
        monkeypatch.delenv("GITLAB_TOKEN", raising=False)
        monkeypatch.setenv("GITLAB_PROJECT", "test-org/test-project")

        with patch('subprocess.run', side_effect=FileNotFoundError()):
            with pytest.raises(SystemExit):
                get_config(mock_args)

    def test_get_config_invalid_json_in_file(self, mock_args, temp_project_dir, monkeypatch):
        """Test config handles invalid JSON in file gracefully."""
        monkeypatch.setenv("GITLAB_TOKEN", "env-token")
        monkeypatch.setenv("GITLAB_PROJECT", "env-project")

        config_dir = temp_project_dir / ".auto-claude" / "gitlab"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.json"
        config_file.write_text("invalid json{")

        # Should fall back to env vars without crashing
        config = get_config(mock_args)

        assert config.token == "env-token"
        assert config.project == "env-project"


class TestPrintProgress:
    """Test progress printing."""

    def test_print_progress_with_mr_iid(self):
        """Test progress printing with MR IID."""
        callback = ProgressCallback(
            phase="test",
            progress=50,
            message="Testing",
            mr_iid=123,
        )

        with patch('runners.gitlab.runner.safe_print') as mock_print:
            print_progress(callback)

        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "[MR !123]" in call_args
        assert "50%" in call_args
        assert "Testing" in call_args

    def test_print_progress_without_mr_iid(self):
        """Test progress printing without MR IID."""
        callback = ProgressCallback(
            phase="test",
            progress=75,
            message="Processing",
        )

        with patch('runners.gitlab.runner.safe_print') as mock_print:
            print_progress(callback)

        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "[MR !" not in call_args
        assert "75%" in call_args
        assert "Processing" in call_args


class TestCmdReviewMR:
    """Test review-mr command."""

    @pytest.mark.asyncio
    async def test_cmd_review_mr_success(self, mock_args, monkeypatch):
        """Test successful MR review command."""
        # Import here to avoid issues with mocked safe_print
        from runners.gitlab.runner import cmd_review_mr

        monkeypatch.setenv("GITLAB_TOKEN", "test-token")
        monkeypatch.setenv("GITLAB_PROJECT", "test-org/test-project")
        mock_args.mr_iid = 123

        # Mock orchestrator
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.mr_iid = 123
        mock_result.overall_status = "approve"
        mock_result.verdict = MagicMock(value="ready_to_merge")
        mock_result.findings = []

        mock_orchestrator = MagicMock()
        mock_orchestrator.review_mr = AsyncMock(return_value=mock_result)

        with patch('runners.gitlab.runner.GitLabOrchestrator', return_value=mock_orchestrator):
            with patch('runners.gitlab.runner.safe_print'):
                exit_code = await cmd_review_mr(mock_args)

        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_cmd_review_mr_failure(self, mock_args, monkeypatch):
        """Test MR review command with failure."""
        from runners.gitlab.runner import cmd_review_mr

        monkeypatch.setenv("GITLAB_TOKEN", "test-token")
        monkeypatch.setenv("GITLAB_PROJECT", "test-org/test-project")
        mock_args.mr_iid = 123

        # Mock orchestrator with failure
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "Review failed"

        mock_orchestrator = MagicMock()
        mock_orchestrator.review_mr = AsyncMock(return_value=mock_result)

        with patch('runners.gitlab.runner.GitLabOrchestrator', return_value=mock_orchestrator):
            with patch('runners.gitlab.runner.safe_print'):
                exit_code = await cmd_review_mr(mock_args)

        assert exit_code == 1


class TestCmdFollowupReviewMR:
    """Test followup-review-mr command."""

    @pytest.mark.asyncio
    async def test_cmd_followup_review_mr_success(self, mock_args, monkeypatch):
        """Test successful follow-up review command."""
        from runners.gitlab.runner import cmd_followup_review_mr

        monkeypatch.setenv("GITLAB_TOKEN", "test-token")
        monkeypatch.setenv("GITLAB_PROJECT", "test-org/test-project")
        mock_args.mr_iid = 123

        # Mock orchestrator
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.mr_iid = 123
        mock_result.overall_status = "approve"
        mock_result.is_followup_review = True
        mock_result.resolved_findings = ["finding1"]
        mock_result.unresolved_findings = []
        mock_result.new_findings_since_last_review = []
        mock_result.summary = "Follow-up review complete"
        mock_result.findings = []

        mock_orchestrator = MagicMock()
        mock_orchestrator.followup_review_mr = AsyncMock(return_value=mock_result)

        with patch('runners.gitlab.runner.GitLabOrchestrator', return_value=mock_orchestrator):
            with patch('runners.gitlab.runner.safe_print'):
                exit_code = await cmd_followup_review_mr(mock_args)

        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_cmd_followup_review_mr_no_previous_review(self, mock_args, monkeypatch):
        """Test follow-up review when no previous review exists."""
        from runners.gitlab.runner import cmd_followup_review_mr

        monkeypatch.setenv("GITLAB_TOKEN", "test-token")
        monkeypatch.setenv("GITLAB_PROJECT", "test-org/test-project")
        mock_args.mr_iid = 123

        # Mock orchestrator raising ValueError
        mock_orchestrator = MagicMock()
        mock_orchestrator.followup_review_mr = AsyncMock(
            side_effect=ValueError("No previous review found")
        )

        with patch('runners.gitlab.runner.GitLabOrchestrator', return_value=mock_orchestrator):
            with patch('runners.gitlab.runner.safe_print'):
                exit_code = await cmd_followup_review_mr(mock_args)

        assert exit_code == 1

    @pytest.mark.asyncio
    async def test_cmd_followup_review_mr_failure(self, mock_args, monkeypatch):
        """Test follow-up review command with failure."""
        from runners.gitlab.runner import cmd_followup_review_mr

        monkeypatch.setenv("GITLAB_TOKEN", "test-token")
        monkeypatch.setenv("GITLAB_PROJECT", "test-org/test-project")
        mock_args.mr_iid = 123

        # Mock orchestrator with failure
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "Follow-up review failed"

        mock_orchestrator = MagicMock()
        mock_orchestrator.followup_review_mr = AsyncMock(return_value=mock_result)

        with patch('runners.gitlab.runner.GitLabOrchestrator', return_value=mock_orchestrator):
            with patch('runners.gitlab.runner.safe_print'):
                exit_code = await cmd_followup_review_mr(mock_args)

        assert exit_code == 1
