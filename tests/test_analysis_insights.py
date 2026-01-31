#!/usr/bin/env python3
"""
Tests for analysis.insight_extractor module.

Tests cover:
- Insight extraction enablement checks
- Git diff retrieval
- Changed file detection
- Commit message extraction
- Input gathering for extraction
- JSON parsing of insights
- LLM extraction mock testing
- Generic insight fallback
- Session insights integration
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add backend directory to path
_backend_dir = Path(__file__).parent.parent / "apps" / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from analysis.insight_extractor import (
    is_extraction_enabled,
    get_extraction_model,
    get_session_diff,
    get_changed_files,
    get_commit_messages,
    gather_extraction_inputs,
    parse_insights,
    extract_session_insights,
    MAX_DIFF_CHARS,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_recovery_manager():
    """Create a mock recovery manager."""
    manager = MagicMock()
    manager.get_subtask_history.return_value = {
        "attempts": [
            {
                "success": False,
                "approach": "First attempt with API",
                "error": "Connection timeout",
            },
            {
                "success": True,
                "approach": "Second attempt with retry logic",
                "error": "",
            },
        ]
    }
    return manager


@pytest.fixture
def sample_insights_json():
    """Sample insights JSON response."""
    return {
        "file_insights": [
            {
                "file": "app/auth.py",
                "purpose": "OAuth authentication handler",
                "key_components": ["GoogleOAuth", "TokenValidator"],
                "gotchas": ["Token refresh requires network call"],
            }
        ],
        "patterns_discovered": [
            {
                "pattern": "Retry with exponential backoff",
                "context": "API calls to external services",
                "reusability": "high",
            }
        ],
        "gotchas_discovered": [
            {
                "gotcha": "Google OAuth requires verified domain in production",
                "impact": "high",
                "mitigation": "Use localhost for development",
            }
        ],
        "approach_outcome": {
            "success": True,
            "approach_used": "Implemented OAuth with retry logic",
            "why_it_worked": "Exponential backoff handled transient failures",
            "why_it_failed": None,
            "alternatives_tried": ["Direct API call without retry"],
        },
        "recommendations": [
            "Add rate limiting to prevent API quota exhaustion",
            "Consider caching OAuth tokens",
        ],
    }


# =============================================================================
# EXTRACTION ENABLEMENT
# =============================================================================


class TestExtractionEnablement:
    """Tests for checking if insight extraction is enabled."""

    @patch("analysis.insight_extractor.SDK_AVAILABLE", True)
    @patch("analysis.insight_extractor.get_auth_token")
    def test_extraction_enabled_with_sdk_and_token(self, mock_get_token):
        """Test extraction enabled when SDK available and token present."""
        mock_get_token.return_value = "test-token"

        assert is_extraction_enabled() is True

    @patch("analysis.insight_extractor.SDK_AVAILABLE", False)
    def test_extraction_disabled_without_sdk(self):
        """Test extraction disabled when SDK not available."""
        assert is_extraction_enabled() is False

    @patch("analysis.insight_extractor.SDK_AVAILABLE", True)
    @patch("analysis.insight_extractor.get_auth_token")
    def test_extraction_disabled_without_token(self, mock_get_token):
        """Test extraction disabled when no auth token."""
        mock_get_token.return_value = None

        assert is_extraction_enabled() is False

    @patch("analysis.insight_extractor.SDK_AVAILABLE", True)
    @patch("analysis.insight_extractor.get_auth_token")
    @patch.dict("os.environ", {"INSIGHT_EXTRACTION_ENABLED": "false"})
    def test_extraction_disabled_by_env_var(self, mock_get_token):
        """Test extraction can be disabled via environment variable."""
        mock_get_token.return_value = "test-token"

        assert is_extraction_enabled() is False

    def test_get_extraction_model_default(self):
        """Test default extraction model."""
        model = get_extraction_model()

        assert model == "claude-haiku-4-5-20251001"

    @patch.dict("os.environ", {"INSIGHT_EXTRACTOR_MODEL": "claude-opus-4-5"})
    def test_get_extraction_model_custom(self):
        """Test custom extraction model from env var."""
        model = get_extraction_model()

        assert model == "claude-opus-4-5"


# =============================================================================
# GIT HELPERS
# =============================================================================


class TestGitHelpers:
    """Tests for Git helper functions."""

    def test_get_session_diff(self, temp_git_repo, make_commit):
        """Test getting diff between two commits."""
        # Create two commits
        commit1 = make_commit("file1.txt", "Initial content\n", "Initial commit")
        commit2 = make_commit(
            "file1.txt", "Initial content\nNew line\n", "Add new line"
        )

        diff = get_session_diff(temp_git_repo, commit1, commit2)

        assert "Initial content" in diff or "New line" in diff
        assert diff != "(No commits to diff)"

    def test_get_session_diff_no_commits(self, temp_git_repo):
        """Test diff when commits are None."""
        diff = get_session_diff(temp_git_repo, None, None)

        assert diff == "(No commits to diff)"

    def test_get_session_diff_same_commit(self, temp_git_repo, make_commit):
        """Test diff when commits are the same."""
        commit = make_commit("file.txt", "content\n", "Commit")

        diff = get_session_diff(temp_git_repo, commit, commit)

        assert diff == "(No changes - same commit)"

    @patch("subprocess.run")
    def test_get_session_diff_truncation(self, mock_run, temp_git_repo):
        """Test diff truncation when too large."""
        # Create a large diff
        large_diff = "a" * (MAX_DIFF_CHARS + 1000)
        mock_run.return_value = MagicMock(stdout=large_diff, returncode=0)

        diff = get_session_diff(temp_git_repo, "abc123", "def456")

        assert len(diff) < len(large_diff)
        assert "truncated" in diff

    @patch("subprocess.run")
    def test_get_session_diff_timeout(self, mock_run, temp_git_repo):
        """Test handling of git diff timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("git diff", 30)

        diff = get_session_diff(temp_git_repo, "abc123", "def456")

        assert "timed out" in diff

    def test_get_changed_files(self, temp_git_repo, make_commit):
        """Test getting list of changed files."""
        commit1 = make_commit("file1.txt", "content\n", "Commit 1")
        make_commit("file2.txt", "content\n", "Commit 2")
        commit2 = make_commit("file3.txt", "content\n", "Commit 3")

        files = get_changed_files(temp_git_repo, commit1, commit2)

        assert "file2.txt" in files
        assert "file3.txt" in files

    def test_get_changed_files_no_commits(self, temp_git_repo):
        """Test get_changed_files with None commits."""
        files = get_changed_files(temp_git_repo, None, None)

        assert files == []

    def test_get_changed_files_same_commit(self, temp_git_repo, make_commit):
        """Test get_changed_files with same commit."""
        commit = make_commit("file.txt", "content\n", "Commit")

        files = get_changed_files(temp_git_repo, commit, commit)

        assert files == []

    def test_get_commit_messages(self, temp_git_repo, make_commit):
        """Test getting commit messages."""
        commit1 = make_commit("file1.txt", "content\n", "First commit")
        make_commit("file2.txt", "content\n", "Second commit")
        commit2 = make_commit("file3.txt", "content\n", "Third commit")

        messages = get_commit_messages(temp_git_repo, commit1, commit2)

        assert "Second commit" in messages
        assert "Third commit" in messages

    def test_get_commit_messages_no_commits(self, temp_git_repo):
        """Test commit messages with None commits."""
        messages = get_commit_messages(temp_git_repo, None, None)

        assert messages == "(No commits)"

    def test_get_commit_messages_same_commit(self, temp_git_repo, make_commit):
        """Test commit messages with same commit."""
        commit = make_commit("file.txt", "content\n", "Commit")

        messages = get_commit_messages(temp_git_repo, commit, commit)

        assert messages == "(No commits)"


# =============================================================================
# INPUT GATHERING
# =============================================================================


class TestInputGathering:
    """Tests for gathering extraction inputs."""

    def test_gather_extraction_inputs(
        self, temp_dir, temp_git_repo, make_commit, mock_recovery_manager
    ):
        """Test gathering all inputs for extraction."""
        # Create spec directory with implementation plan
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        plan = {
            "phases": [
                {
                    "subtasks": [
                        {
                            "id": "subtask-1",
                            "description": "Implement OAuth authentication",
                        }
                    ]
                }
            ]
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan, indent=2))

        # Create commits
        commit1 = make_commit("file1.txt", "initial\n", "Initial")
        commit2 = make_commit("file1.txt", "initial\nchanged\n", "Change")

        inputs = gather_extraction_inputs(
            spec_dir=spec_dir,
            project_dir=temp_git_repo,
            subtask_id="subtask-1",
            session_num=1,
            commit_before=commit1,
            commit_after=commit2,
            success=True,
            recovery_manager=mock_recovery_manager,
        )

        assert inputs["subtask_id"] == "subtask-1"
        assert inputs["subtask_description"] == "Implement OAuth authentication"
        assert inputs["session_num"] == 1
        assert inputs["success"] is True
        assert "diff" in inputs
        assert "changed_files" in inputs
        assert "commit_messages" in inputs
        assert "attempt_history" in inputs
        assert len(inputs["attempt_history"]) == 2

    def test_gather_inputs_missing_plan(
        self, temp_dir, temp_git_repo, make_commit, mock_recovery_manager
    ):
        """Test gathering inputs when implementation plan is missing."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()

        commit1 = make_commit("file.txt", "content\n", "Commit 1")
        commit2 = make_commit("file.txt", "content\nmore\n", "Commit 2")

        inputs = gather_extraction_inputs(
            spec_dir=spec_dir,
            project_dir=temp_git_repo,
            subtask_id="test-subtask",
            session_num=1,
            commit_before=commit1,
            commit_after=commit2,
            success=True,
            recovery_manager=mock_recovery_manager,
        )

        # Should use fallback description
        assert inputs["subtask_description"] == "Subtask: test-subtask"

    def test_gather_inputs_no_recovery_manager(
        self, temp_dir, temp_git_repo, make_commit
    ):
        """Test gathering inputs without recovery manager."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()

        commit1 = make_commit("file.txt", "content\n", "Commit 1")
        commit2 = make_commit("file.txt", "content\nmore\n", "Commit 2")

        inputs = gather_extraction_inputs(
            spec_dir=spec_dir,
            project_dir=temp_git_repo,
            subtask_id="test-subtask",
            session_num=1,
            commit_before=commit1,
            commit_after=commit2,
            success=True,
            recovery_manager=None,
        )

        assert inputs["attempt_history"] == []


# =============================================================================
# INSIGHT PARSING
# =============================================================================


class TestInsightParsing:
    """Tests for parsing LLM responses into insights."""

    def test_parse_valid_json(self, sample_insights_json):
        """Test parsing valid JSON response."""
        json_str = json.dumps(sample_insights_json)

        insights = parse_insights(json_str)

        assert insights is not None
        assert "file_insights" in insights
        assert "patterns_discovered" in insights
        assert "gotchas_discovered" in insights
        assert len(insights["file_insights"]) == 1

    def test_parse_json_with_markdown_code_block(self, sample_insights_json):
        """Test parsing JSON wrapped in markdown code blocks."""
        json_str = "```json\n" + json.dumps(sample_insights_json) + "\n```"

        insights = parse_insights(json_str)

        assert insights is not None
        assert "file_insights" in insights

    def test_parse_json_with_plain_code_block(self, sample_insights_json):
        """Test parsing JSON with plain code block markers."""
        json_str = "```\n" + json.dumps(sample_insights_json) + "\n```"

        insights = parse_insights(json_str)

        assert insights is not None

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        invalid_json = "{ this is not valid json }"

        insights = parse_insights(invalid_json)

        assert insights is None

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        insights = parse_insights("")

        assert insights is None

    def test_parse_non_dict_json(self):
        """Test parsing JSON that's not a dictionary."""
        json_str = json.dumps(["array", "not", "object"])

        insights = parse_insights(json_str)

        assert insights is None

    def test_parse_adds_default_keys(self):
        """Test that parsing adds default keys if missing."""
        minimal_json = json.dumps({"file_insights": []})

        insights = parse_insights(minimal_json)

        assert insights is not None
        assert "file_insights" in insights
        assert "patterns_discovered" in insights
        assert "gotchas_discovered" in insights
        assert "approach_outcome" in insights
        assert "recommendations" in insights

    def test_parse_empty_code_block(self):
        """Test parsing empty code block."""
        empty_code_block = "```json\n```"

        insights = parse_insights(empty_code_block)

        assert insights is None


# =============================================================================
# LLM EXTRACTION (MOCKED)
# =============================================================================


class TestLLMExtraction:
    """Tests for LLM-based insight extraction (mocked)."""

    @pytest.mark.asyncio
    @patch("analysis.insight_extractor.SDK_AVAILABLE", True)
    @patch("analysis.insight_extractor.get_auth_token")
    @patch("analysis.insight_extractor.ensure_claude_code_oauth_token")
    @patch("core.simple_client.create_simple_client")
    async def test_run_insight_extraction_success(
        self,
        mock_create_client,
        mock_ensure_token,
        mock_get_token,
        temp_dir,
        sample_insights_json,
    ):
        """Test successful insight extraction."""
        mock_get_token.return_value = "test-token"

        # Mock the SDK client
        mock_client = AsyncMock()
        mock_message = MagicMock()

        # Create a proper TextBlock mock with __name__ for type checking
        mock_text_block = MagicMock()
        mock_text_block.__class__.__name__ = "TextBlock"
        type(mock_text_block).__name__ = "TextBlock"
        mock_text_block.text = json.dumps(sample_insights_json)

        # Set up the message mock
        mock_message.__class__.__name__ = "AssistantMessage"
        mock_message.content = [mock_text_block]

        # Mock receive_response to yield the message
        async def mock_receive():
            yield mock_message

        mock_client.receive_response = mock_receive
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.query = AsyncMock()

        mock_create_client.return_value = mock_client

        inputs = {
            "subtask_id": "test",
            "subtask_description": "Test subtask",
            "session_num": 1,
            "success": True,
            "diff": "test diff",
            "changed_files": ["file.py"],
            "commit_messages": "test commit",
            "attempt_history": [],
        }

        from analysis.insight_extractor import run_insight_extraction

        result = await run_insight_extraction(inputs, project_dir=temp_dir)

        assert result is not None
        assert "file_insights" in result

    @pytest.mark.asyncio
    @patch("analysis.insight_extractor.SDK_AVAILABLE", False)
    async def test_run_extraction_sdk_not_available(self, temp_dir):
        """Test extraction when SDK not available."""
        from analysis.insight_extractor import run_insight_extraction

        inputs = {"subtask_id": "test"}
        result = await run_insight_extraction(inputs, project_dir=temp_dir)

        assert result is None

    @pytest.mark.asyncio
    @patch("analysis.insight_extractor.SDK_AVAILABLE", True)
    @patch("analysis.insight_extractor.get_auth_token")
    async def test_run_extraction_no_auth_token(self, mock_get_token, temp_dir):
        """Test extraction when no auth token."""
        mock_get_token.return_value = None

        from analysis.insight_extractor import run_insight_extraction

        inputs = {"subtask_id": "test"}
        result = await run_insight_extraction(inputs, project_dir=temp_dir)

        assert result is None


# =============================================================================
# SESSION INSIGHTS INTEGRATION
# =============================================================================


class TestSessionInsightsIntegration:
    """Tests for extract_session_insights integration."""

    @pytest.mark.asyncio
    @patch("analysis.insight_extractor.is_extraction_enabled")
    async def test_extract_insights_disabled(
        self, mock_is_enabled, temp_dir, temp_git_repo, make_commit
    ):
        """Test extraction when disabled returns generic insights."""
        mock_is_enabled.return_value = False

        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()

        commit = make_commit("file.txt", "content\n", "Commit")

        insights = await extract_session_insights(
            spec_dir=spec_dir,
            project_dir=temp_git_repo,
            subtask_id="test-subtask",
            session_num=1,
            commit_before=commit,
            commit_after=commit,
            success=True,
            recovery_manager=None,
        )

        # Should return generic insights
        assert "file_insights" in insights
        assert insights["file_insights"] == []
        assert insights["subtask_id"] == "test-subtask"
        assert insights["success"] is True

    @pytest.mark.asyncio
    @patch("analysis.insight_extractor.is_extraction_enabled")
    async def test_extract_insights_no_changes(
        self, mock_is_enabled, temp_dir, temp_git_repo, make_commit
    ):
        """Test extraction with no changes returns generic insights."""
        mock_is_enabled.return_value = True

        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()

        commit = make_commit("file.txt", "content\n", "Commit")

        insights = await extract_session_insights(
            spec_dir=spec_dir,
            project_dir=temp_git_repo,
            subtask_id="test-subtask",
            session_num=1,
            commit_before=commit,
            commit_after=commit,  # Same commit
            success=True,
            recovery_manager=None,
        )

        # Should return generic insights for no changes
        assert insights["file_insights"] == []

    @pytest.mark.asyncio
    @patch("analysis.insight_extractor.is_extraction_enabled")
    @patch("analysis.insight_extractor.run_insight_extraction")
    @patch("analysis.insight_extractor.gather_extraction_inputs")
    async def test_extract_insights_success(
        self,
        mock_gather_inputs,
        mock_run_extraction,
        mock_is_enabled,
        temp_dir,
        temp_git_repo,
        sample_insights_json,
    ):
        """Test successful insight extraction."""
        mock_is_enabled.return_value = True
        mock_gather_inputs.return_value = {
            "subtask_id": "test",
            "changed_files": ["app/auth.py"],
        }
        mock_run_extraction.return_value = sample_insights_json

        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()

        insights = await extract_session_insights(
            spec_dir=spec_dir,
            project_dir=temp_git_repo,
            subtask_id="test-subtask",
            session_num=1,
            commit_before="abc123",
            commit_after="def456",
            success=True,
            recovery_manager=None,
        )

        assert insights is not None
        assert "file_insights" in insights
        assert len(insights["file_insights"]) > 0

    @pytest.mark.asyncio
    @patch("analysis.insight_extractor.is_extraction_enabled")
    @patch("analysis.insight_extractor.run_insight_extraction")
    @patch("analysis.insight_extractor.gather_extraction_inputs")
    async def test_extract_insights_failure_fallback(
        self,
        mock_gather_inputs,
        mock_run_extraction,
        mock_is_enabled,
        temp_dir,
        temp_git_repo,
    ):
        """Test fallback to generic insights on extraction failure."""
        mock_is_enabled.return_value = True
        mock_gather_inputs.return_value = {"subtask_id": "test"}
        mock_run_extraction.side_effect = Exception("Extraction failed")

        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()

        insights = await extract_session_insights(
            spec_dir=spec_dir,
            project_dir=temp_git_repo,
            subtask_id="test-subtask",
            session_num=1,
            commit_before="abc123",
            commit_after="def456",
            success=False,
            recovery_manager=None,
        )

        # Should return generic insights on failure
        assert insights["file_insights"] == []
        assert insights["success"] is False
