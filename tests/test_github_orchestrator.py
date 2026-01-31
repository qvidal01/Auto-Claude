#!/usr/bin/env python3
"""
Tests for GitHub Orchestrator
==============================

Tests for the main orchestrator coordinating all GitHub automation workflows.
"""

import sys
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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


@pytest.fixture
def github_dir(temp_dir):
    """Create GitHub directory structure."""
    github_dir = temp_dir / ".auto-claude" / "github"
    github_dir.mkdir(parents=True)
    (github_dir / "pr").mkdir()
    (github_dir / "issues").mkdir()
    (github_dir / "batches").mkdir()
    return github_dir


@pytest.fixture
def mock_config():
    """Create mock GitHub runner config."""
    config = MagicMock()
    config.repo = "test/repo"
    config.token = "test_token"
    config.auto_post_reviews = False
    config.bot_token = "test_bot_token"
    config.review_own_prs = False
    config.auto_fix_allowed_roles = ["admin", "write"]
    config.allow_external_contributors = False
    return config


@pytest.fixture
def mock_gh_client():
    """Create mock GH client."""
    client = MagicMock()
    client.pr_get = AsyncMock()
    client.pr_diff = AsyncMock()
    client.pr_review = AsyncMock()
    client.pr_comment_reply = AsyncMock()
    client.issue_get = AsyncMock()
    client.issue_list = AsyncMock()
    client.issue_comment = AsyncMock()
    client.issue_add_labels = AsyncMock()
    client.issue_remove_labels = AsyncMock()
    client.get_pr_checks_comprehensive = AsyncMock()
    client.get_pr_files = AsyncMock()
    client.get_pr_head_sha = AsyncMock()
    return client


@pytest.fixture
def mock_bot_detector():
    """Create mock bot detector."""
    detector = MagicMock()
    detector.should_skip_pr_review = MagicMock(return_value=(False, ""))
    detector.mark_review_started = MagicMock()
    detector.mark_reviewed = MagicMock()
    detector.mark_review_finished = MagicMock()
    detector.get_last_commit_sha = MagicMock(return_value="abc123")
    return detector


@pytest.fixture
def mock_pr_review_engine():
    """Create mock PR review engine."""
    engine = MagicMock()
    engine.run_multi_pass_review = AsyncMock(return_value=([], [], [], "Quick scan OK"))
    return engine


@pytest.fixture
def mock_triage_engine():
    """Create mock triage engine."""
    engine = MagicMock()
    engine.triage_single_issue = AsyncMock()
    return engine


@pytest.fixture
def mock_autofix_processor():
    """Create mock autofix processor."""
    processor = MagicMock()
    processor.process_issue = AsyncMock()
    processor.get_queue = AsyncMock(return_value=[])
    processor.check_labeled_issues = AsyncMock(return_value=[])
    return processor


@pytest.fixture
def mock_batch_processor():
    """Create mock batch processor."""
    processor = MagicMock()
    processor.batch_and_fix_issues = AsyncMock(return_value=[])
    processor.analyze_issues_preview = AsyncMock(return_value={})
    processor.approve_and_execute_batches = AsyncMock(return_value=[])
    processor.get_batch_status = AsyncMock(return_value={})
    processor.process_pending_batches = AsyncMock(return_value=0)
    return processor


@pytest.fixture
def orchestrator(
    temp_dir,
    github_dir,
    mock_config,
    mock_gh_client,
    mock_bot_detector,
    mock_pr_review_engine,
    mock_triage_engine,
    mock_autofix_processor,
    mock_batch_processor,
):
    """Create orchestrator with mocked dependencies."""
    with patch("runners.github.orchestrator.GHClient", return_value=mock_gh_client):
        with patch("runners.github.orchestrator.BotDetector", return_value=mock_bot_detector):
            with patch(
                "runners.github.orchestrator.GitHubPermissionChecker"
            ):
                with patch("runners.github.orchestrator.PRReviewEngine", return_value=mock_pr_review_engine):
                    with patch("runners.github.orchestrator.TriageEngine", return_value=mock_triage_engine):
                        with patch(
                            "runners.github.orchestrator.AutoFixProcessor",
                            return_value=mock_autofix_processor,
                        ):
                            with patch(
                                "runners.github.orchestrator.BatchProcessor",
                                return_value=mock_batch_processor,
                            ):
                                from runners.github.orchestrator import GitHubOrchestrator

                                orch = GitHubOrchestrator(
                                    project_dir=temp_dir,
                                    config=mock_config,
                                )
                                # Replace with mocks
                                orch.gh_client = mock_gh_client
                                orch.bot_detector = mock_bot_detector
                                orch.pr_review_engine = mock_pr_review_engine
                                orch.triage_engine = mock_triage_engine
                                orch.autofix_processor = mock_autofix_processor
                                orch.batch_processor = mock_batch_processor
                                return orch


# =============================================================================
# ORCHESTRATOR INITIALIZATION TESTS
# =============================================================================


def test_orchestrator_initialization(orchestrator, temp_dir, github_dir, mock_config):
    """Test orchestrator initializes with correct structure."""
    assert orchestrator.project_dir == temp_dir
    assert orchestrator.config == mock_config
    assert orchestrator.github_dir == github_dir
    assert github_dir.exists()


def test_orchestrator_creates_directories(temp_dir, mock_config):
    """Test orchestrator creates required directories."""
    from runners.github.orchestrator import GitHubOrchestrator

    with patch("runners.github.orchestrator.GHClient"):
        with patch("runners.github.orchestrator.BotDetector"):
            with patch("runners.github.orchestrator.GitHubPermissionChecker"):
                with patch("runners.github.orchestrator.PRReviewEngine"):
                    with patch("runners.github.orchestrator.TriageEngine"):
                        with patch("runners.github.orchestrator.AutoFixProcessor"):
                            with patch("runners.github.orchestrator.BatchProcessor"):
                                orch = GitHubOrchestrator(
                                    project_dir=temp_dir,
                                    config=mock_config,
                                )

    github_dir = temp_dir / ".auto-claude" / "github"
    assert github_dir.exists()


# =============================================================================
# PR REVIEW WORKFLOW TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_review_pr_success(orchestrator, mock_gh_client, mock_bot_detector, mock_pr_review_engine):
    """Test successful PR review."""
    # Setup mocks
    pr_data = {
        "number": 123,
        "title": "Test PR",
        "body": "Test description",
        "author": {"login": "test-user"},
        "baseRefName": "main",
        "headRefName": "feature",
        "headRefOid": "abc123",
        "baseRefOid": "def456",
        "state": "open",
        "files": [],
        "additions": 10,
        "deletions": 5,
        "changedFiles": 2,
        "labels": [],
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "CLEAN",
    }

    commits = [{"sha": "abc123", "author": {"login": "test-user"}}]

    mock_gh_client.pr_get.return_value = pr_data
    mock_gh_client.pr_diff.return_value = "diff content"
    mock_gh_client.get_pr_checks_comprehensive.return_value = {
        "passing": 1,
        "failing": 0,
        "pending": 0,
        "awaiting_approval": 0,
    }
    mock_gh_client.get_pr_files.return_value = []

    mock_bot_detector.get_last_commit_sha.return_value = "abc123"

    with patch("runners.github.orchestrator.PRContextGatherer") as mock_gatherer_class:
        mock_gatherer = mock_gatherer_class.return_value
        mock_context = MagicMock()
        mock_context.pr_number = 123
        mock_context.title = "Test PR"
        mock_context.author = "test-user"
        mock_context.changed_files = []
        mock_context.commits = commits
        mock_context.has_merge_conflicts = False
        mock_context.merge_state_status = "CLEAN"
        mock_context.total_additions = 10
        mock_context.total_deletions = 5
        mock_gatherer.gather = AsyncMock(return_value=mock_context)

        result = await orchestrator.review_pr(pr_number=123)

    assert result.success is True
    assert result.pr_number == 123
    mock_bot_detector.mark_review_started.assert_called_once()
    mock_pr_review_engine.run_multi_pass_review.assert_called_once()


@pytest.mark.asyncio
async def test_review_pr_skipped_bot_detection(orchestrator, mock_bot_detector):
    """Test PR review skipped by bot detection."""
    mock_bot_detector.should_skip_pr_review.return_value = (True, "Bot PR detected")

    with patch("runners.github.orchestrator.PRContextGatherer") as mock_gatherer_class:
        mock_gatherer = mock_gatherer_class.return_value
        mock_context = MagicMock()
        mock_context.pr_number = 123
        mock_context.author = "bot-user"
        mock_context.commits = []
        mock_gatherer.gather = AsyncMock(return_value=mock_context)

        result = await orchestrator.review_pr(pr_number=123)

    assert result.success is True
    assert "Skipped" in result.summary
    mock_pr_review_engine = orchestrator.pr_review_engine
    mock_pr_review_engine.run_multi_pass_review.assert_not_called()


@pytest.mark.asyncio
async def test_review_pr_with_error(orchestrator, mock_bot_detector):
    """Test PR review with error handling."""
    with patch("runners.github.orchestrator.PRContextGatherer") as mock_gatherer_class:
        mock_gatherer_class.return_value.gather = AsyncMock(side_effect=Exception("API Error"))

        result = await orchestrator.review_pr(pr_number=123)

    assert result.success is False
    assert "API Error" in result.error
    mock_bot_detector.mark_review_finished.assert_called_once_with(123, success=False)


@pytest.mark.asyncio
async def test_review_pr_force_review(orchestrator, mock_bot_detector):
    """Test force review bypasses already reviewed check."""
    mock_bot_detector.should_skip_pr_review.return_value = (True, "Already reviewed")

    with patch("runners.github.orchestrator.PRContextGatherer") as mock_gatherer_class:
        mock_gatherer = mock_gatherer_class.return_value
        mock_context = MagicMock()
        mock_context.pr_number = 123
        mock_context.title = "Test PR"
        mock_context.author = "test-user"
        mock_context.commits = []
        mock_context.changed_files = []
        mock_context.has_merge_conflicts = False
        mock_context.merge_state_status = "CLEAN"
        mock_context.total_additions = 10
        mock_context.total_deletions = 5
        mock_gatherer.gather = AsyncMock(return_value=mock_context)

        mock_gh_client = orchestrator.gh_client
        mock_gh_client.get_pr_checks_comprehensive.return_value = {
            "passing": 1,
            "failing": 0,
            "pending": 0,
            "awaiting_approval": 0,
        }
        mock_gh_client.get_pr_files.return_value = []

        result = await orchestrator.review_pr(pr_number=123, force_review=True)

    # Should not be skipped due to force_review
    assert result.success is True
    orchestrator.pr_review_engine.run_multi_pass_review.assert_called_once()


# =============================================================================
# FOLLOW-UP REVIEW TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_followup_review_no_previous(orchestrator):
    """Test follow-up review fails without previous review."""
    with patch("runners.github.orchestrator.PRReviewResult") as mock_result_class:
        mock_result_class.load.return_value = None

        with pytest.raises(ValueError, match="No previous review found"):
            await orchestrator.followup_review_pr(pr_number=123)


@pytest.mark.asyncio
async def test_followup_review_success(orchestrator, github_dir):
    """Test successful follow-up review."""
    from runners.github.models import PRReviewResult

    # Create previous review
    previous_review = PRReviewResult(
        pr_number=123,
        repo="test/repo",
        success=True,
        findings=[],
        summary="Previous review",
        overall_status="approve",
        reviewed_commit_sha="old123",
    )
    await previous_review.save(github_dir)

    # Mock the gh_client.get_pr_checks_comprehensive to return proper dict
    orchestrator.gh_client.get_pr_checks_comprehensive = AsyncMock(
        return_value={"passing": 1, "failing": 0, "pending": 0, "awaiting_approval": 0}
    )

    with patch("runners.github.context_gatherer.FollowupContextGatherer") as mock_gatherer_class:
        with patch("runners.github.services.parallel_followup_reviewer.ParallelFollowupReviewer") as mock_reviewer_class:
            mock_gatherer = mock_gatherer_class.return_value
            mock_context = MagicMock()
            mock_context.pr_number = 123
            mock_context.commits_since_review = [{"sha": "new123"}]
            mock_context.files_changed_since_review = ["file.py"]
            mock_context.current_commit_sha = "new123"
            mock_context.error = None
            mock_context.ci_status = {"passing": 1, "failing": 0, "pending": 0, "awaiting_approval": 0}
            mock_context.total_additions = 10
            mock_context.total_deletions = 5
            mock_gatherer.gather = AsyncMock(return_value=mock_context)

            mock_reviewer = mock_reviewer_class.return_value
            followup_result = PRReviewResult(
                pr_number=123,
                repo="test/repo",
                success=True,
                findings=[],
                summary="Follow-up review",
                overall_status="approve",
                reviewed_commit_sha="new123",
                is_followup_review=True,
            )
            mock_reviewer.review = AsyncMock(return_value=followup_result)

            result = await orchestrator.followup_review_pr(pr_number=123)

    assert result.success is True
    assert result.is_followup_review is True


# =============================================================================
# VERDICT GENERATION TESTS
# =============================================================================


def test_generate_verdict_no_issues(orchestrator):
    """Test verdict generation with no issues."""
    verdict, reasoning, blockers = orchestrator._generate_verdict(
        findings=[],
        structural_issues=[],
        ai_triages=[],
        ci_status={"passing": 1, "failing": 0, "pending": 0, "awaiting_approval": 0},
        has_merge_conflicts=False,
        merge_state_status="CLEAN",
    )

    from runners.github.models import MergeVerdict

    assert verdict == MergeVerdict.READY_TO_MERGE
    assert "No blocking issues" in reasoning
    assert len(blockers) == 0


def test_generate_verdict_with_merge_conflicts(orchestrator):
    """Test verdict blocked by merge conflicts."""
    verdict, reasoning, blockers = orchestrator._generate_verdict(
        findings=[],
        structural_issues=[],
        ai_triages=[],
        ci_status={"passing": 1, "failing": 0, "pending": 0, "awaiting_approval": 0},
        has_merge_conflicts=True,
        merge_state_status="CONFLICTING",
    )

    from runners.github.models import MergeVerdict

    assert verdict == MergeVerdict.BLOCKED
    assert "merge conflicts" in reasoning.lower()
    assert any("Merge Conflicts" in b for b in blockers)


def test_generate_verdict_with_failing_ci(orchestrator):
    """Test verdict blocked by failing CI."""
    verdict, reasoning, blockers = orchestrator._generate_verdict(
        findings=[],
        structural_issues=[],
        ai_triages=[],
        ci_status={
            "passing": 0,
            "failing": 2,
            "pending": 0,
            "awaiting_approval": 0,
            "failed_checks": ["test", "lint"],
        },
        has_merge_conflicts=False,
        merge_state_status="CLEAN",
    )

    from runners.github.models import MergeVerdict

    assert verdict == MergeVerdict.BLOCKED
    assert "CI" in reasoning
    assert any("CI Failed" in b for b in blockers)


def test_generate_verdict_branch_behind(orchestrator):
    """Test verdict with branch behind base."""
    verdict, reasoning, blockers = orchestrator._generate_verdict(
        findings=[],
        structural_issues=[],
        ai_triages=[],
        ci_status={"passing": 1, "failing": 0, "pending": 0, "awaiting_approval": 0},
        has_merge_conflicts=False,
        merge_state_status="BEHIND",
    )

    from runners.github.models import MergeVerdict

    assert verdict == MergeVerdict.NEEDS_REVISION
    assert "behind" in reasoning.lower() or "out of date" in reasoning.lower()


# =============================================================================
# ISSUE TRIAGE TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_triage_issues_success(orchestrator, mock_gh_client, mock_triage_engine):
    """Test successful issue triage."""
    from runners.github.models import TriageResult, TriageCategory

    issues = [
        {"number": 1, "title": "Bug", "body": "Description", "labels": []},
        {"number": 2, "title": "Feature", "body": "Description", "labels": []},
    ]

    mock_gh_client.issue_list.return_value = issues

    triage_results = [
        TriageResult(
            issue_number=1,
            repo="test/repo",
            category=TriageCategory.BUG,
            confidence=0.9,
            is_duplicate=False,
            labels_to_add=["bug"],
            labels_to_remove=[],
        ),
        TriageResult(
            issue_number=2,
            repo="test/repo",
            category=TriageCategory.FEATURE,
            confidence=0.85,
            is_duplicate=False,
            labels_to_add=["enhancement"],
            labels_to_remove=[],
        ),
    ]

    mock_triage_engine.triage_single_issue.side_effect = triage_results

    results = await orchestrator.triage_issues()

    assert len(results) == 2
    assert results[0].issue_number == 1
    assert results[1].issue_number == 2
    mock_gh_client.issue_list.assert_called_once()


@pytest.mark.asyncio
async def test_triage_specific_issues(orchestrator, mock_gh_client, mock_triage_engine):
    """Test triage of specific issue numbers."""
    from runners.github.models import TriageResult, TriageCategory

    mock_gh_client.issue_get.side_effect = [
        {"number": 1, "title": "Bug", "body": "Description", "labels": []},
    ]

    triage_result = TriageResult(
        issue_number=1,
        repo="test/repo",
        category=TriageCategory.BUG,
        confidence=0.9,
        is_duplicate=False,
        labels_to_add=["bug"],
        labels_to_remove=[],
    )
    mock_triage_engine.triage_single_issue.return_value = triage_result

    results = await orchestrator.triage_issues(issue_numbers=[1])

    assert len(results) == 1
    assert results[0].issue_number == 1
    mock_gh_client.issue_get.assert_called_once_with(1)


# =============================================================================
# AUTO-FIX WORKFLOW TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_auto_fix_issue(orchestrator, mock_gh_client, mock_autofix_processor):
    """Test auto-fix issue workflow."""
    from runners.github.models import AutoFixState

    issue = {"number": 123, "title": "Bug", "body": "Description", "labels": []}

    mock_gh_client.issue_get.return_value = issue

    autofix_state = AutoFixState(
        issue_number=123,
        issue_url="https://github.com/test/repo/issues/123",
        repo="test/repo",
        status="pending",
    )
    mock_autofix_processor.process_issue.return_value = autofix_state

    result = await orchestrator.auto_fix_issue(issue_number=123)

    assert result.issue_number == 123
    mock_gh_client.issue_get.assert_called_once_with(123)
    mock_autofix_processor.process_issue.assert_called_once()


@pytest.mark.asyncio
async def test_get_auto_fix_queue(orchestrator, mock_autofix_processor):
    """Test getting auto-fix queue."""
    from runners.github.models import AutoFixState

    queue = [
        AutoFixState(issue_number=1, issue_url="https://github.com/test/repo/issues/1", repo="test/repo", status="pending"),
        AutoFixState(issue_number=2, issue_url="https://github.com/test/repo/issues/2", repo="test/repo", status="building"),
    ]

    mock_autofix_processor.get_queue.return_value = queue

    result = await orchestrator.get_auto_fix_queue()

    assert len(result) == 2
    assert result[0].issue_number == 1
    mock_autofix_processor.get_queue.assert_called_once()


# =============================================================================
# BATCH PROCESSING TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_batch_and_fix_issues(orchestrator, mock_gh_client, mock_batch_processor):
    """Test batch and fix issues workflow."""
    issues = [
        {"number": 1, "title": "Bug A", "body": "Description", "labels": []},
        {"number": 2, "title": "Bug B", "body": "Description", "labels": []},
    ]

    mock_gh_client.issue_list.return_value = issues
    mock_batch_processor.batch_and_fix_issues.return_value = []

    result = await orchestrator.batch_and_fix_issues()

    assert isinstance(result, list)
    mock_gh_client.issue_list.assert_called_once()
    mock_batch_processor.batch_and_fix_issues.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_issues_preview(orchestrator, mock_gh_client, mock_batch_processor):
    """Test analyze issues preview."""
    issues = [
        {"number": 1, "title": "Bug A", "body": "Description", "labels": []},
        {"number": 2, "title": "Bug B", "body": "Description", "labels": []},
    ]

    mock_gh_client.issue_list.return_value = issues

    preview = {
        "batches": [
            {"issue_numbers": [1, 2], "theme": "Similar bugs", "confidence": 0.9}
        ],
        "stats": {"total_issues": 2, "proposed_batches": 1},
    }
    mock_batch_processor.analyze_issues_preview.return_value = preview

    result = await orchestrator.analyze_issues_preview()

    assert "batches" in result
    assert "stats" in result
    mock_batch_processor.analyze_issues_preview.assert_called_once()


# =============================================================================
# PROGRESS CALLBACK TESTS
# =============================================================================


def test_report_progress(orchestrator):
    """Test progress reporting."""
    progress_calls = []

    def callback(progress):
        progress_calls.append(progress)

    orchestrator.progress_callback = callback
    orchestrator._report_progress("testing", 50, "Test message", pr_number=123)

    assert len(progress_calls) == 1
    assert progress_calls[0].phase == "testing"
    assert progress_calls[0].progress == 50
    assert progress_calls[0].message == "Test message"
    assert progress_calls[0].pr_number == 123


def test_report_progress_no_callback(orchestrator):
    """Test progress reporting with no callback."""
    orchestrator.progress_callback = None
    # Should not raise exception
    orchestrator._report_progress("testing", 50, "Test message")


# =============================================================================
# HELPER METHOD TESTS
# =============================================================================


def test_calculate_risk_assessment_high(orchestrator):
    """Test risk assessment with high complexity."""
    from runners.github.context_gatherer import PRContext

    context = PRContext(
        pr_number=123,
        title="Test",
        description="Test",
        author="test",
        base_branch="main",
        head_branch="feature",
        state="open",
        changed_files=[],
        diff="",
        repo_structure="",
        related_files=[],
        total_additions=1000,
        total_deletions=500,
    )

    risk = orchestrator._calculate_risk_assessment(context, [], [])

    assert risk["complexity"] == "high"
    assert risk["security_impact"] == "none"
    assert risk["scope_coherence"] == "good"


def test_calculate_risk_assessment_with_security(orchestrator):
    """Test risk assessment with security findings."""
    from runners.github.context_gatherer import PRContext
    from runners.github.models import PRReviewFinding, ReviewCategory, ReviewSeverity

    context = PRContext(
        pr_number=123,
        title="Test",
        description="Test",
        author="test",
        base_branch="main",
        head_branch="feature",
        state="open",
        changed_files=[],
        diff="",
        repo_structure="",
        related_files=[],
        total_additions=100,
        total_deletions=50,
    )

    findings = [
        PRReviewFinding(
            id="finding-001",
            title="SQL Injection",
            description="Unsafe query",
            file="db.py",
            line=10,
            category=ReviewCategory.SECURITY,
            severity=ReviewSeverity.CRITICAL,
        )
    ]

    risk = orchestrator._calculate_risk_assessment(context, findings, [])

    # 100 + 50 = 150 total changes, which is < 200, so complexity is "low"
    assert risk["complexity"] == "low"
    assert risk["security_impact"] == "critical"
