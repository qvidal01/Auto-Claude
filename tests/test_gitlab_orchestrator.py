#!/usr/bin/env python3
"""
Test suite for GitLab orchestrator
===================================

Tests the GitLab orchestrator workflow for MR reviews.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import json
import urllib.error

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
from runners.gitlab.orchestrator import GitLabOrchestrator, ProgressCallback
from runners.gitlab.models import (
    GitLabRunnerConfig,
    MRContext,
    MRReviewFinding,
    MRReviewResult,
    MergeVerdict,
    ReviewCategory,
    ReviewSeverity,
)
from runners.gitlab.glab_client import GitLabConfig


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def gitlab_config():
    """Create a GitLabRunnerConfig for testing."""
    return GitLabRunnerConfig(
        token="test-token-123",
        project="test-org/test-project",
        instance_url="https://gitlab.example.com",
        model="claude-sonnet-4-5-20250929",
        thinking_level="medium",
    )


@pytest.fixture
def mock_progress_callback():
    """Create a mock progress callback."""
    return MagicMock()


class TestGitLabOrchestratorInitialization:
    """Test orchestrator initialization."""

    def test_orchestrator_init_creates_gitlab_dir(
        self, temp_project_dir, gitlab_config
    ):
        """Test that orchestrator creates .auto-claude/gitlab directory."""
        orchestrator = GitLabOrchestrator(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        gitlab_dir = temp_project_dir / ".auto-claude" / "gitlab"
        assert gitlab_dir.exists()
        assert gitlab_dir.is_dir()
        assert orchestrator.gitlab_dir == gitlab_dir

    def test_orchestrator_init_with_progress_callback(
        self, temp_project_dir, gitlab_config, mock_progress_callback
    ):
        """Test orchestrator initialization with progress callback."""
        orchestrator = GitLabOrchestrator(
            project_dir=temp_project_dir,
            config=gitlab_config,
            progress_callback=mock_progress_callback,
        )

        assert orchestrator.progress_callback == mock_progress_callback

    def test_orchestrator_creates_client_and_engine(
        self, temp_project_dir, gitlab_config
    ):
        """Test that orchestrator creates GitLab client and review engine."""
        orchestrator = GitLabOrchestrator(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        assert orchestrator.client is not None
        assert orchestrator.review_engine is not None
        assert orchestrator.gitlab_config.token == "test-token-123"
        assert orchestrator.gitlab_config.project == "test-org/test-project"


class TestProgressReporting:
    """Test progress reporting functionality."""

    def test_report_progress_calls_callback(
        self, temp_project_dir, gitlab_config, mock_progress_callback
    ):
        """Test that _report_progress calls the callback."""
        orchestrator = GitLabOrchestrator(
            project_dir=temp_project_dir,
            config=gitlab_config,
            progress_callback=mock_progress_callback,
        )

        orchestrator._report_progress("test_phase", 50, "Testing progress", mr_iid=123)

        mock_progress_callback.assert_called_once()
        call_args = mock_progress_callback.call_args[0][0]
        assert isinstance(call_args, ProgressCallback)
        assert call_args.phase == "test_phase"
        assert call_args.progress == 50
        assert call_args.message == "Testing progress"
        assert call_args.mr_iid == 123

    def test_report_progress_no_callback(self, temp_project_dir, gitlab_config):
        """Test that _report_progress handles no callback gracefully."""
        orchestrator = GitLabOrchestrator(
            project_dir=temp_project_dir,
            config=gitlab_config,
            progress_callback=None,
        )

        # Should not raise any errors
        orchestrator._report_progress("test_phase", 50, "Testing progress")


class TestGatherMRContext:
    """Test MR context gathering."""

    @pytest.mark.asyncio
    async def test_gather_mr_context_success(self, temp_project_dir, gitlab_config):
        """Test successfully gathering MR context."""
        orchestrator = GitLabOrchestrator(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        # Mock GitLab client responses
        mock_mr_data = {
            "title": "Add new feature",
            "description": "This adds a new feature",
            "author": {"username": "testuser"},
            "source_branch": "feature-branch",
            "target_branch": "main",
            "state": "opened",
            "sha": "abc123def456",
        }

        mock_changes_data = {
            "changes": [
                {
                    "new_path": "src/file1.py",
                    "old_path": "src/file1.py",
                    "diff": "+new line\n-old line",
                },
                {
                    "new_path": "src/file2.py",
                    "old_path": None,
                    "diff": "+new file content",
                },
            ]
        }

        mock_commits = [
            {"id": "commit1", "message": "First commit"},
            {"id": "commit2", "message": "Second commit"},
        ]

        orchestrator.client.get_mr = MagicMock(return_value=mock_mr_data)
        orchestrator.client.get_mr_changes = MagicMock(return_value=mock_changes_data)
        orchestrator.client.get_mr_commits = MagicMock(return_value=mock_commits)

        context = await orchestrator._gather_mr_context(123)

        assert isinstance(context, MRContext)
        assert context.mr_iid == 123
        assert context.title == "Add new feature"
        assert context.description == "This adds a new feature"
        assert context.author == "testuser"
        assert context.source_branch == "feature-branch"
        assert context.target_branch == "main"
        assert context.state == "opened"
        assert len(context.changed_files) == 2
        assert context.total_additions == 2
        assert context.total_deletions == 1
        assert context.head_sha == "abc123def456"

    @pytest.mark.asyncio
    async def test_gather_mr_context_no_sha_uses_diff_refs(
        self, temp_project_dir, gitlab_config
    ):
        """Test gathering context when sha is in diff_refs."""
        orchestrator = GitLabOrchestrator(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        mock_mr_data = {
            "title": "Test MR",
            "description": "Test",
            "author": {"username": "testuser"},
            "source_branch": "feature",
            "target_branch": "main",
            "state": "opened",
            "diff_refs": {"head_sha": "xyz789"},
        }

        orchestrator.client.get_mr = MagicMock(return_value=mock_mr_data)
        orchestrator.client.get_mr_changes = MagicMock(return_value={"changes": []})
        orchestrator.client.get_mr_commits = MagicMock(return_value=[])

        context = await orchestrator._gather_mr_context(123)

        assert context.head_sha == "xyz789"


class TestReviewMR:
    """Test MR review functionality."""

    @pytest.mark.asyncio
    async def test_review_mr_success(
        self, temp_project_dir, gitlab_config, mock_progress_callback
    ):
        """Test successful MR review."""
        orchestrator = GitLabOrchestrator(
            project_dir=temp_project_dir,
            config=gitlab_config,
            progress_callback=mock_progress_callback,
        )

        # Mock context gathering
        mock_context = MRContext(
            mr_iid=123,
            title="Test MR",
            description="Test description",
            author="testuser",
            source_branch="feature",
            target_branch="main",
            state="opened",
            changed_files=[{"new_path": "test.py", "diff": "+test"}],
            diff="+test",
            total_additions=1,
            total_deletions=0,
            commits=[{"id": "commit1"}],
            head_sha="abc123",
        )

        # Mock review engine
        mock_findings = [
            MRReviewFinding(
                id="finding-1",
                severity=ReviewSeverity.MEDIUM,
                category=ReviewCategory.QUALITY,
                title="Test finding",
                description="This is a test finding",
                file="test.py",
                line=10,
            )
        ]

        with patch.object(
            orchestrator, "_gather_mr_context", return_value=mock_context
        ) as mock_gather:
            with patch.object(
                orchestrator.review_engine,
                "run_review",
                new_callable=AsyncMock,
                return_value=(
                    mock_findings,
                    MergeVerdict.MERGE_WITH_CHANGES,
                    "Review summary",
                    [],
                ),
            ) as mock_review:
                with patch.object(
                    orchestrator.review_engine,
                    "generate_summary",
                    return_value="Full summary",
                ):
                    result = await orchestrator.review_mr(123)

        assert result.success is True
        assert result.mr_iid == 123
        assert result.project == "test-org/test-project"
        assert len(result.findings) == 1
        assert result.overall_status == "comment"
        assert result.verdict == MergeVerdict.MERGE_WITH_CHANGES
        assert result.reviewed_commit_sha == "abc123"

        # Verify progress callbacks were made
        assert mock_progress_callback.call_count >= 3

    @pytest.mark.asyncio
    async def test_review_mr_blocked_verdict(self, temp_project_dir, gitlab_config):
        """Test MR review with blocked verdict."""
        orchestrator = GitLabOrchestrator(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        mock_context = MRContext(
            mr_iid=123,
            title="Test MR",
            description="Test",
            author="testuser",
            source_branch="feature",
            target_branch="main",
            state="opened",
            head_sha="abc123",
        )

        mock_findings = [
            MRReviewFinding(
                id="finding-1",
                severity=ReviewSeverity.CRITICAL,
                category=ReviewCategory.SECURITY,
                title="Security issue",
                description="Critical security vulnerability",
                file="test.py",
                line=10,
            )
        ]

        with patch.object(
            orchestrator, "_gather_mr_context", return_value=mock_context
        ):
            with patch.object(
                orchestrator.review_engine,
                "run_review",
                new_callable=AsyncMock,
                return_value=(
                    mock_findings,
                    MergeVerdict.BLOCKED,
                    "Security issues found",
                    ["Security issue (test.py:10)"],
                ),
            ):
                with patch.object(
                    orchestrator.review_engine,
                    "generate_summary",
                    return_value="Full summary",
                ):
                    result = await orchestrator.review_mr(123)

        assert result.overall_status == "request_changes"
        assert result.verdict == MergeVerdict.BLOCKED
        assert len(result.blockers) == 1

    @pytest.mark.asyncio
    async def test_review_mr_http_404_error(self, temp_project_dir, gitlab_config):
        """Test MR review with HTTP 404 error."""
        orchestrator = GitLabOrchestrator(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        # Mock 404 error
        error = urllib.error.HTTPError(
            url="test", code=404, msg="Not Found", hdrs={}, fp=None
        )

        with patch.object(
            orchestrator.client, "get_mr", side_effect=error
        ):
            result = await orchestrator.review_mr(123)

        assert result.success is False
        assert "not found" in result.error.lower()
        assert result.mr_iid == 123

    @pytest.mark.asyncio
    async def test_review_mr_http_401_error(self, temp_project_dir, gitlab_config):
        """Test MR review with HTTP 401 authentication error."""
        orchestrator = GitLabOrchestrator(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        error = urllib.error.HTTPError(
            url="test", code=401, msg="Unauthorized", hdrs={}, fp=None
        )

        with patch.object(
            orchestrator.client, "get_mr", side_effect=error
        ):
            result = await orchestrator.review_mr(123)

        assert result.success is False
        assert "authentication failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_review_mr_json_decode_error(self, temp_project_dir, gitlab_config):
        """Test MR review with JSON decode error."""
        orchestrator = GitLabOrchestrator(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        with patch.object(
            orchestrator.client, "get_mr", side_effect=json.JSONDecodeError("msg", "doc", 0)
        ):
            result = await orchestrator.review_mr(123)

        assert result.success is False
        assert "invalid json" in result.error.lower()

    @pytest.mark.asyncio
    async def test_review_mr_saves_result(self, temp_project_dir, gitlab_config):
        """Test that review result is saved to disk."""
        orchestrator = GitLabOrchestrator(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        mock_context = MRContext(
            mr_iid=123,
            title="Test MR",
            description="Test",
            author="testuser",
            source_branch="feature",
            target_branch="main",
            state="opened",
            head_sha="abc123",
        )

        with patch.object(
            orchestrator, "_gather_mr_context", return_value=mock_context
        ):
            with patch.object(
                orchestrator.review_engine,
                "run_review",
                new_callable=AsyncMock,
                return_value=([], MergeVerdict.READY_TO_MERGE, "All good", []),
            ):
                with patch.object(
                    orchestrator.review_engine,
                    "generate_summary",
                    return_value="Summary",
                ):
                    result = await orchestrator.review_mr(123)

        # Check that result file was created
        result_file = temp_project_dir / ".auto-claude" / "gitlab" / "mr" / "review_123.json"
        assert result_file.exists()

        # Verify content
        with open(result_file) as f:
            saved_data = json.load(f)
        assert saved_data["mr_iid"] == 123
        assert saved_data["success"] is True


class TestFollowupReviewMR:
    """Test follow-up MR review functionality."""

    @pytest.mark.asyncio
    async def test_followup_review_no_previous_review(
        self, temp_project_dir, gitlab_config
    ):
        """Test follow-up review fails without previous review."""
        orchestrator = GitLabOrchestrator(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        with pytest.raises(ValueError, match="No previous review found"):
            await orchestrator.followup_review_mr(123)

    @pytest.mark.asyncio
    async def test_followup_review_no_commit_sha(self, temp_project_dir, gitlab_config):
        """Test follow-up review fails without previous commit SHA."""
        orchestrator = GitLabOrchestrator(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        # Create previous review without commit SHA
        previous_review = MRReviewResult(
            mr_iid=123,
            project="test-org/test-project",
            success=True,
            reviewed_commit_sha=None,
        )
        previous_review.save(orchestrator.gitlab_dir)

        with pytest.raises(ValueError, match="doesn't have commit SHA"):
            await orchestrator.followup_review_mr(123)

    @pytest.mark.asyncio
    async def test_followup_review_no_new_commits(
        self, temp_project_dir, gitlab_config
    ):
        """Test follow-up review when no new commits exist."""
        orchestrator = GitLabOrchestrator(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        # Create previous review
        previous_review = MRReviewResult(
            mr_iid=123,
            project="test-org/test-project",
            success=True,
            reviewed_commit_sha="abc123",
            findings=[
                MRReviewFinding(
                    id="finding-1",
                    severity=ReviewSeverity.MEDIUM,
                    category=ReviewCategory.QUALITY,
                    title="Old finding",
                    description="Test",
                    file="test.py",
                    line=10,
                )
            ],
        )
        previous_review.save(orchestrator.gitlab_dir)

        # Mock context with same commit SHA
        mock_context = MRContext(
            mr_iid=123,
            title="Test MR",
            description="Test",
            author="testuser",
            source_branch="feature",
            target_branch="main",
            state="opened",
            head_sha="abc123",  # Same as previous
        )

        with patch.object(
            orchestrator, "_gather_mr_context", return_value=mock_context
        ):
            result = await orchestrator.followup_review_mr(123)

        assert result.success is True
        assert result.is_followup_review is True
        assert "No new commits" in result.summary
        assert len(result.unresolved_findings) == 1

    @pytest.mark.asyncio
    async def test_followup_review_with_new_commits(
        self, temp_project_dir, gitlab_config
    ):
        """Test follow-up review with new commits."""
        orchestrator = GitLabOrchestrator(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        # Create previous review
        previous_review = MRReviewResult(
            mr_iid=123,
            project="test-org/test-project",
            success=True,
            reviewed_commit_sha="abc123",
            findings=[
                MRReviewFinding(
                    id="finding-1",
                    severity=ReviewSeverity.MEDIUM,
                    category=ReviewCategory.QUALITY,
                    title="Old finding",
                    description="Test",
                    file="test.py",
                    line=10,
                )
            ],
        )
        previous_review.save(orchestrator.gitlab_dir)

        # Mock context with new commit
        mock_context = MRContext(
            mr_iid=123,
            title="Test MR",
            description="Test",
            author="testuser",
            source_branch="feature",
            target_branch="main",
            state="opened",
            head_sha="def456",  # New commit
        )

        # Mock review engine - finding is resolved
        new_findings = [
            MRReviewFinding(
                id="finding-2",
                severity=ReviewSeverity.LOW,
                category=ReviewCategory.STYLE,
                title="New style issue",
                description="Test",
                file="test2.py",
                line=5,
            )
        ]

        with patch.object(
            orchestrator, "_gather_mr_context", return_value=mock_context
        ):
            with patch.object(
                orchestrator.review_engine,
                "run_review",
                new_callable=AsyncMock,
                return_value=(
                    new_findings,
                    MergeVerdict.MERGE_WITH_CHANGES,
                    "New commits reviewed",
                    [],
                ),
            ):
                with patch.object(
                    orchestrator.review_engine,
                    "generate_summary",
                    return_value="Full summary",
                ):
                    result = await orchestrator.followup_review_mr(123)

        assert result.success is True
        assert result.is_followup_review is True
        assert result.reviewed_commit_sha == "def456"
        assert len(result.resolved_findings) == 1
        assert "Old finding" in result.resolved_findings[0]
        assert len(result.new_findings_since_last_review) == 1
        assert "New style issue" in result.new_findings_since_last_review[0]
        assert "Follow-up Review" in result.summary
