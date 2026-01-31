#!/usr/bin/env python3
"""
Test suite for GitLab MR review engine
=======================================

Tests the MR review engine AI logic and parsing.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import json

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

# Now safe to import runners modules
from runners.gitlab.services.mr_review_engine import (
    MRReviewEngine,
    ProgressCallback,
    sanitize_user_content,
)
from runners.gitlab.models import (
    GitLabRunnerConfig,
    MRContext,
    MRReviewFinding,
    MergeVerdict,
    ReviewCategory,
    ReviewSeverity,
)


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def gitlab_dir(tmp_path):
    """Create a GitLab directory."""
    gitlab_dir = tmp_path / ".auto-claude" / "gitlab"
    gitlab_dir.mkdir(parents=True)
    return gitlab_dir


@pytest.fixture
def gitlab_config():
    """Create a GitLabRunnerConfig for testing."""
    return GitLabRunnerConfig(
        token="test-token",
        project="test-org/test-project",
        instance_url="https://gitlab.example.com",
        model="claude-sonnet-4-5-20250929",
        thinking_level="medium",
    )


@pytest.fixture
def mock_progress_callback():
    """Create a mock progress callback."""
    return MagicMock()


class TestSanitizeUserContent:
    """Test user content sanitization."""

    def test_sanitize_removes_null_bytes(self):
        """Test that null bytes are removed."""
        content = "Hello\x00World"
        result = sanitize_user_content(content)
        assert "\x00" not in result
        assert "HelloWorld" == result

    def test_sanitize_removes_control_characters(self):
        """Test that control characters are removed."""
        content = "Hello\x01\x02\x03World"
        result = sanitize_user_content(content)
        assert "HelloWorld" == result

    def test_sanitize_preserves_newlines_and_tabs(self):
        """Test that newlines and tabs are preserved."""
        content = "Hello\nWorld\tTest"
        result = sanitize_user_content(content)
        assert result == "Hello\nWorld\tTest"

    def test_sanitize_truncates_long_content(self):
        """Test that content longer than max_length is truncated."""
        content = "A" * 1000
        result = sanitize_user_content(content, max_length=500)
        assert len(result) < 600
        assert "truncated" in result

    def test_sanitize_empty_content(self):
        """Test sanitization of empty content."""
        assert sanitize_user_content("") == ""
        assert sanitize_user_content(None) == ""


class TestMRReviewEngineInitialization:
    """Test MR review engine initialization."""

    def test_engine_init(
        self, temp_project_dir, gitlab_dir, gitlab_config, mock_progress_callback
    ):
        """Test engine initialization."""
        engine = MRReviewEngine(
            project_dir=temp_project_dir,
            gitlab_dir=gitlab_dir,
            config=gitlab_config,
            progress_callback=mock_progress_callback,
        )

        assert engine.project_dir == temp_project_dir
        assert engine.gitlab_dir == gitlab_dir
        assert engine.config == gitlab_config
        assert engine.progress_callback == mock_progress_callback

    def test_engine_init_without_callback(
        self, temp_project_dir, gitlab_dir, gitlab_config
    ):
        """Test engine initialization without progress callback."""
        engine = MRReviewEngine(
            project_dir=temp_project_dir,
            gitlab_dir=gitlab_dir,
            config=gitlab_config,
        )

        assert engine.progress_callback is None


class TestProgressReporting:
    """Test progress reporting."""

    def test_report_progress_with_callback(
        self, temp_project_dir, gitlab_dir, gitlab_config, mock_progress_callback
    ):
        """Test progress reporting with callback."""
        engine = MRReviewEngine(
            project_dir=temp_project_dir,
            gitlab_dir=gitlab_dir,
            config=gitlab_config,
            progress_callback=mock_progress_callback,
        )

        engine._report_progress("test", 50, "Test message", mr_iid=123)

        mock_progress_callback.assert_called_once()
        call_args = mock_progress_callback.call_args[0][0]
        assert call_args.phase == "test"
        assert call_args.progress == 50
        assert call_args.message == "Test message"

    def test_report_progress_without_callback(
        self, temp_project_dir, gitlab_dir, gitlab_config
    ):
        """Test progress reporting without callback."""
        engine = MRReviewEngine(
            project_dir=temp_project_dir,
            gitlab_dir=gitlab_dir,
            config=gitlab_config,
            progress_callback=None,
        )

        # Should not raise errors
        engine._report_progress("test", 50, "Test message")


class TestGetReviewPrompt:
    """Test review prompt generation."""

    def test_get_review_prompt_returns_string(
        self, temp_project_dir, gitlab_dir, gitlab_config
    ):
        """Test that review prompt is a non-empty string."""
        engine = MRReviewEngine(
            project_dir=temp_project_dir,
            gitlab_dir=gitlab_dir,
            config=gitlab_config,
        )

        prompt = engine._get_review_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "review" in prompt.lower()
        assert "json" in prompt.lower()

    def test_review_prompt_contains_guidelines(
        self, temp_project_dir, gitlab_dir, gitlab_config
    ):
        """Test that review prompt contains review guidelines."""
        engine = MRReviewEngine(
            project_dir=temp_project_dir,
            gitlab_dir=gitlab_dir,
            config=gitlab_config,
        )

        prompt = engine._get_review_prompt()

        assert "Security" in prompt
        assert "Quality" in prompt
        assert "verdict" in prompt.lower()
        assert "findings" in prompt.lower()


class TestParseReviewResult:
    """Test parsing of AI review results."""

    def test_parse_valid_json_response(
        self, temp_project_dir, gitlab_dir, gitlab_config
    ):
        """Test parsing a valid JSON response."""
        engine = MRReviewEngine(
            project_dir=temp_project_dir,
            gitlab_dir=gitlab_dir,
            config=gitlab_config,
        )

        response = """```json
{
  "summary": "Review looks good",
  "verdict": "ready_to_merge",
  "verdict_reasoning": "No major issues found",
  "findings": [
    {
      "severity": "low",
      "category": "style",
      "title": "Minor style issue",
      "description": "Consider using const instead of let",
      "file": "src/app.ts",
      "line": 42,
      "end_line": 42,
      "suggested_fix": "const value = 1;",
      "fixable": true
    }
  ]
}
```"""

        findings, verdict, summary, blockers = engine._parse_review_result(response)

        assert len(findings) == 1
        assert verdict == MergeVerdict.READY_TO_MERGE
        assert summary == "Review looks good"
        assert len(blockers) == 0

        finding = findings[0]
        assert finding.severity == ReviewSeverity.LOW
        assert finding.category == ReviewCategory.STYLE
        assert finding.title == "Minor style issue"
        assert finding.file == "src/app.ts"
        assert finding.line == 42

    def test_parse_critical_findings(
        self, temp_project_dir, gitlab_dir, gitlab_config
    ):
        """Test parsing critical findings that create blockers."""
        engine = MRReviewEngine(
            project_dir=temp_project_dir,
            gitlab_dir=gitlab_dir,
            config=gitlab_config,
        )

        response = """```json
{
  "summary": "Critical issues found",
  "verdict": "blocked",
  "verdict_reasoning": "Security vulnerabilities must be fixed",
  "findings": [
    {
      "severity": "critical",
      "category": "security",
      "title": "SQL Injection vulnerability",
      "description": "User input not sanitized",
      "file": "src/db.py",
      "line": 10,
      "fixable": false
    },
    {
      "severity": "high",
      "category": "security",
      "title": "XSS vulnerability",
      "description": "Output not escaped",
      "file": "src/view.py",
      "line": 20,
      "fixable": false
    }
  ]
}
```"""

        findings, verdict, summary, blockers = engine._parse_review_result(response)

        assert len(findings) == 2
        assert verdict == MergeVerdict.BLOCKED
        assert len(blockers) == 2
        assert "SQL Injection" in blockers[0]
        assert "XSS vulnerability" in blockers[1]

    def test_parse_invalid_json(self, temp_project_dir, gitlab_dir, gitlab_config):
        """Test parsing invalid JSON response."""
        engine = MRReviewEngine(
            project_dir=temp_project_dir,
            gitlab_dir=gitlab_dir,
            config=gitlab_config,
        )

        response = """```json
{
  "summary": "This is invalid JSON
  "verdict": "ready_to_merge"
}
```"""

        findings, verdict, summary, blockers = engine._parse_review_result(response)

        assert len(findings) == 0
        assert verdict == MergeVerdict.MERGE_WITH_CHANGES
        assert "failed to parse" in summary.lower()

    def test_parse_no_json_block(self, temp_project_dir, gitlab_dir, gitlab_config):
        """Test parsing response without JSON block."""
        engine = MRReviewEngine(
            project_dir=temp_project_dir,
            gitlab_dir=gitlab_dir,
            config=gitlab_config,
        )

        response = "This is just plain text without any JSON"

        findings, verdict, summary, blockers = engine._parse_review_result(response)

        assert len(findings) == 0
        assert verdict == MergeVerdict.READY_TO_MERGE
        assert summary == ""

    def test_parse_invalid_severity(self, temp_project_dir, gitlab_dir, gitlab_config):
        """Test parsing finding with invalid severity."""
        engine = MRReviewEngine(
            project_dir=temp_project_dir,
            gitlab_dir=gitlab_dir,
            config=gitlab_config,
        )

        response = """```json
{
  "summary": "Test",
  "verdict": "ready_to_merge",
  "findings": [
    {
      "severity": "invalid_severity",
      "category": "quality",
      "title": "Test",
      "description": "Test",
      "file": "test.py",
      "line": 1
    }
  ]
}
```"""

        findings, verdict, summary, blockers = engine._parse_review_result(response)

        # Invalid finding should be skipped
        assert len(findings) == 0


class TestRunReview:
    """Test running MR review."""

    @pytest.mark.asyncio
    async def test_run_review_success(
        self, temp_project_dir, gitlab_dir, gitlab_config, mock_progress_callback
    ):
        """Test successful MR review."""
        engine = MRReviewEngine(
            project_dir=temp_project_dir,
            gitlab_dir=gitlab_dir,
            config=gitlab_config,
            progress_callback=mock_progress_callback,
        )

        context = MRContext(
            mr_iid=123,
            title="Add new feature",
            description="This adds a new feature",
            author="testuser",
            source_branch="feature",
            target_branch="main",
            state="opened",
            changed_files=[
                {"new_path": "src/app.py", "diff": "+new code"}
            ],
            diff="+new code",
            total_additions=1,
            total_deletions=0,
        )

        # Mock the Claude client
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.query = AsyncMock()

        # Mock response with TextBlock
        mock_text_block = MagicMock()
        mock_text_block.text = """```json
{
  "summary": "Review complete",
  "verdict": "ready_to_merge",
  "verdict_reasoning": "All good",
  "findings": []
}
```"""
        type(mock_text_block).__name__ = "TextBlock"

        mock_message = MagicMock()
        mock_message.content = [mock_text_block]
        type(mock_message).__name__ = "AssistantMessage"

        async def mock_receive():
            yield mock_message

        mock_client.receive_response = mock_receive

        with patch("core.client.create_client", return_value=mock_client):
            findings, verdict, summary, blockers = await engine.run_review(context)

        assert verdict == MergeVerdict.READY_TO_MERGE
        assert summary == "Review complete"
        assert len(findings) == 0
        assert len(blockers) == 0

    @pytest.mark.asyncio
    async def test_run_review_sanitizes_user_content(
        self, temp_project_dir, gitlab_dir, gitlab_config
    ):
        """Test that user content is sanitized before sending to AI."""
        engine = MRReviewEngine(
            project_dir=temp_project_dir,
            gitlab_dir=gitlab_dir,
            config=gitlab_config,
        )

        # Create context with potentially malicious content
        context = MRContext(
            mr_iid=123,
            title="Test\x00Title\x01",
            description="Description\x00with\x01control\x02chars",
            author="testuser",
            source_branch="feature",
            target_branch="main",
            state="opened",
            diff="+code\x00here",
        )

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        query_prompt = None

        async def capture_query(prompt):
            nonlocal query_prompt
            query_prompt = prompt

        mock_client.query = capture_query

        mock_text_block = MagicMock()
        mock_text_block.text = """```json
{
  "summary": "Test",
  "verdict": "ready_to_merge",
  "findings": []
}
```"""
        type(mock_text_block).__name__ = "TextBlock"

        mock_message = MagicMock()
        mock_message.content = [mock_text_block]
        type(mock_message).__name__ = "AssistantMessage"

        async def mock_receive():
            yield mock_message

        mock_client.receive_response = mock_receive

        with patch("core.client.create_client", return_value=mock_client):
            await engine.run_review(context)

        # Verify that null bytes were removed from the prompt
        assert query_prompt is not None
        assert "\x00" not in query_prompt
        assert "\x01" not in query_prompt
        assert "\x02" not in query_prompt

    @pytest.mark.asyncio
    async def test_run_review_handles_errors(
        self, temp_project_dir, gitlab_dir, gitlab_config
    ):
        """Test that run_review handles errors properly."""
        engine = MRReviewEngine(
            project_dir=temp_project_dir,
            gitlab_dir=gitlab_dir,
            config=gitlab_config,
        )

        context = MRContext(
            mr_iid=123,
            title="Test",
            description="Test",
            author="testuser",
            source_branch="feature",
            target_branch="main",
            state="opened",
        )

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.query = AsyncMock(side_effect=Exception("API Error"))

        with patch("core.client.create_client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="Review failed"):
                await engine.run_review(context)


class TestGenerateSummary:
    """Test summary generation."""

    def test_generate_summary_ready_to_merge(
        self, temp_project_dir, gitlab_dir, gitlab_config
    ):
        """Test summary for ready to merge verdict."""
        engine = MRReviewEngine(
            project_dir=temp_project_dir,
            gitlab_dir=gitlab_dir,
            config=gitlab_config,
        )

        findings = []
        summary = engine.generate_summary(
            findings=findings,
            verdict=MergeVerdict.READY_TO_MERGE,
            verdict_reasoning="All checks passed",
            blockers=[],
        )

        assert "✅" in summary
        assert "READY TO MERGE" in summary
        assert "All checks passed" in summary

    def test_generate_summary_with_blockers(
        self, temp_project_dir, gitlab_dir, gitlab_config
    ):
        """Test summary with blocking issues."""
        engine = MRReviewEngine(
            project_dir=temp_project_dir,
            gitlab_dir=gitlab_dir,
            config=gitlab_config,
        )

        findings = [
            MRReviewFinding(
                id="f1",
                severity=ReviewSeverity.CRITICAL,
                category=ReviewCategory.SECURITY,
                title="Security issue",
                description="Test",
                file="test.py",
                line=10,
            )
        ]

        blockers = ["Security issue (test.py:10)"]

        summary = engine.generate_summary(
            findings=findings,
            verdict=MergeVerdict.BLOCKED,
            verdict_reasoning="Critical security issues",
            blockers=blockers,
        )

        assert "🔴" in summary
        assert "BLOCKED" in summary
        assert "🚨 Blocking Issues" in summary
        assert "Security issue" in summary

    def test_generate_summary_with_findings(
        self, temp_project_dir, gitlab_dir, gitlab_config
    ):
        """Test summary with various severity findings."""
        engine = MRReviewEngine(
            project_dir=temp_project_dir,
            gitlab_dir=gitlab_dir,
            config=gitlab_config,
        )

        findings = [
            MRReviewFinding(
                id="f1",
                severity=ReviewSeverity.CRITICAL,
                category=ReviewCategory.SECURITY,
                title="Critical issue",
                description="Test",
                file="test.py",
                line=10,
            ),
            MRReviewFinding(
                id="f2",
                severity=ReviewSeverity.HIGH,
                category=ReviewCategory.QUALITY,
                title="High issue",
                description="Test",
                file="test.py",
                line=20,
            ),
            MRReviewFinding(
                id="f3",
                severity=ReviewSeverity.MEDIUM,
                category=ReviewCategory.STYLE,
                title="Medium issue",
                description="Test",
                file="test.py",
                line=30,
            ),
            MRReviewFinding(
                id="f4",
                severity=ReviewSeverity.LOW,
                category=ReviewCategory.DOCS,
                title="Low issue",
                description="Test",
                file="test.py",
                line=40,
            ),
        ]

        summary = engine.generate_summary(
            findings=findings,
            verdict=MergeVerdict.NEEDS_REVISION,
            verdict_reasoning="Multiple issues found",
            blockers=[],
        )

        assert "Findings Summary" in summary
        assert "**Critical**: 1 issue(s)" in summary
        assert "**High**: 1 issue(s)" in summary
        assert "**Medium**: 1 issue(s)" in summary
        assert "**Low**: 1 issue(s)" in summary
        assert "Generated by Auto Claude" in summary
