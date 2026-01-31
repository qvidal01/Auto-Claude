#!/usr/bin/env python3
"""
Simplified Tests for GitHub Modules
====================================

Focused tests for GitHub orchestrator, context gatherer, and batch issues
that avoid complex import issues and test core logic.
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


# =============================================================================
# MODELS AND ENUMS TESTS
# =============================================================================


def test_merge_verdict_enum():
    """Test merge verdict enum values."""
    # Import directly from models module to avoid orchestrator init
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend" / "runners" / "github"))
    from models import MergeVerdict

    assert MergeVerdict.READY_TO_MERGE.value == "ready_to_merge"
    assert MergeVerdict.BLOCKED.value == "blocked"
    assert MergeVerdict.NEEDS_REVISION.value == "needs_revision"
    assert MergeVerdict.MERGE_WITH_CHANGES.value == "merge_with_changes"


def test_review_severity_enum():
    """Test review severity enum."""
    from runners.github.models import ReviewSeverity

    assert ReviewSeverity.CRITICAL.value == "critical"
    assert ReviewSeverity.HIGH.value == "high"
    assert ReviewSeverity.MEDIUM.value == "medium"
    assert ReviewSeverity.LOW.value == "low"


def test_review_category_enum():
    """Test review category enum."""
    from runners.github.models import ReviewCategory

    assert ReviewCategory.SECURITY.value == "security"
    assert ReviewCategory.QUALITY.value == "quality"
    assert ReviewCategory.VERIFICATION_FAILED.value == "verification_failed"
    assert ReviewCategory.REDUNDANCY.value == "redundancy"


# =============================================================================
# VERDICT HELPER FUNCTION TESTS
# =============================================================================


def test_verdict_from_severity_counts_critical():
    """Test verdict with critical findings."""
    from runners.github.models import verdict_from_severity_counts, MergeVerdict

    verdict = verdict_from_severity_counts(critical_count=1)
    assert verdict == MergeVerdict.BLOCKED


def test_verdict_from_severity_counts_high():
    """Test verdict with high severity findings."""
    from runners.github.models import verdict_from_severity_counts, MergeVerdict

    verdict = verdict_from_severity_counts(high_count=2)
    assert verdict == MergeVerdict.NEEDS_REVISION


def test_verdict_from_severity_counts_medium():
    """Test verdict with medium severity findings."""
    from runners.github.models import verdict_from_severity_counts, MergeVerdict

    verdict = verdict_from_severity_counts(medium_count=3)
    assert verdict == MergeVerdict.NEEDS_REVISION


def test_verdict_from_severity_counts_low_only():
    """Test verdict with only low severity findings."""
    from runners.github.models import verdict_from_severity_counts, MergeVerdict

    verdict = verdict_from_severity_counts(low_count=5)
    assert verdict == MergeVerdict.READY_TO_MERGE


def test_verdict_from_severity_counts_no_findings():
    """Test verdict with no findings."""
    from runners.github.models import verdict_from_severity_counts, MergeVerdict

    verdict = verdict_from_severity_counts()
    assert verdict == MergeVerdict.READY_TO_MERGE


def test_apply_merge_conflict_override():
    """Test merge conflict override."""
    from runners.github.models import apply_merge_conflict_override, MergeVerdict

    # Merge conflicts should override any verdict
    verdict = apply_merge_conflict_override(MergeVerdict.READY_TO_MERGE, has_merge_conflicts=True)
    assert verdict == MergeVerdict.BLOCKED

    # No conflicts should preserve verdict
    verdict = apply_merge_conflict_override(MergeVerdict.READY_TO_MERGE, has_merge_conflicts=False)
    assert verdict == MergeVerdict.READY_TO_MERGE


def test_apply_branch_behind_downgrade():
    """Test branch behind downgrade."""
    from runners.github.models import apply_branch_behind_downgrade, MergeVerdict

    # Behind should downgrade READY_TO_MERGE
    verdict = apply_branch_behind_downgrade(MergeVerdict.READY_TO_MERGE, merge_state_status="BEHIND")
    assert verdict == MergeVerdict.NEEDS_REVISION

    # Behind should downgrade MERGE_WITH_CHANGES
    verdict = apply_branch_behind_downgrade(MergeVerdict.MERGE_WITH_CHANGES, merge_state_status="BEHIND")
    assert verdict == MergeVerdict.NEEDS_REVISION

    # Behind should NOT downgrade BLOCKED
    verdict = apply_branch_behind_downgrade(MergeVerdict.BLOCKED, merge_state_status="BEHIND")
    assert verdict == MergeVerdict.BLOCKED

    # CLEAN should not change verdict
    verdict = apply_branch_behind_downgrade(MergeVerdict.READY_TO_MERGE, merge_state_status="CLEAN")
    assert verdict == MergeVerdict.READY_TO_MERGE


def test_apply_ci_status_override():
    """Test CI status override."""
    from runners.github.models import apply_ci_status_override, MergeVerdict

    # Failing CI should block READY_TO_MERGE
    verdict = apply_ci_status_override(MergeVerdict.READY_TO_MERGE, failing_count=1)
    assert verdict == MergeVerdict.BLOCKED

    # Failing CI should block MERGE_WITH_CHANGES
    verdict = apply_ci_status_override(MergeVerdict.MERGE_WITH_CHANGES, failing_count=1)
    assert verdict == MergeVerdict.BLOCKED

    # Failing CI should NOT override NEEDS_REVISION
    verdict = apply_ci_status_override(MergeVerdict.NEEDS_REVISION, failing_count=1)
    assert verdict == MergeVerdict.NEEDS_REVISION

    # Pending CI should cause NEEDS_REVISION
    verdict = apply_ci_status_override(MergeVerdict.READY_TO_MERGE, pending_count=1)
    assert verdict == MergeVerdict.NEEDS_REVISION


def test_verdict_to_github_status():
    """Test verdict to GitHub status mapping."""
    from runners.github.models import verdict_to_github_status, MergeVerdict

    assert verdict_to_github_status(MergeVerdict.READY_TO_MERGE) == "approve"
    assert verdict_to_github_status(MergeVerdict.MERGE_WITH_CHANGES) == "comment"
    assert verdict_to_github_status(MergeVerdict.NEEDS_REVISION) == "request_changes"
    assert verdict_to_github_status(MergeVerdict.BLOCKED) == "request_changes"


# =============================================================================
# PATH VALIDATION TESTS
# =============================================================================


def test_validate_file_path():
    """Test file path validation."""
    from runners.github.context_gatherer import _validate_file_path

    # Valid paths
    assert _validate_file_path("src/file.py") is True
    assert _validate_file_path("apps/backend/main.py") is True
    assert _validate_file_path("@types/node/index.d.ts") is True

    # Invalid paths
    assert _validate_file_path("../../../etc/passwd") is False
    assert _validate_file_path("/etc/passwd") is False
    assert _validate_file_path("") is False
    assert _validate_file_path("a" * 2000) is False


def test_validate_git_ref():
    """Test git ref validation."""
    from runners.github.context_gatherer import _validate_git_ref

    # Valid refs
    assert _validate_git_ref("abc123def") is True
    assert _validate_git_ref("main") is True
    assert _validate_git_ref("feature/auth") is True
    assert _validate_git_ref("v1.0.0") is True

    # Invalid refs
    assert _validate_git_ref("") is False
    assert _validate_git_ref("a" * 300) is False
    assert _validate_git_ref("ref;rm -rf /") is False


# =============================================================================
# PR REVIEW FINDING TESTS
# =============================================================================


def test_pr_review_finding_creation():
    """Test creating PR review finding."""
    from runners.github.models import PRReviewFinding, ReviewSeverity, ReviewCategory

    finding = PRReviewFinding(
        id="test-001",
        severity=ReviewSeverity.HIGH,
        category=ReviewCategory.SECURITY,
        title="SQL Injection",
        description="Unsafe query construction",
        file="src/db.py",
        line=42,
        evidence="WHERE id = ' + user_input",
    )

    assert finding.id == "test-001"
    assert finding.severity == ReviewSeverity.HIGH
    assert finding.category == ReviewCategory.SECURITY
    assert "SQL Injection" in finding.title


def test_pr_review_finding_to_dict():
    """Test serializing finding to dict."""
    from runners.github.models import PRReviewFinding, ReviewSeverity, ReviewCategory

    finding = PRReviewFinding(
        id="test-001",
        severity=ReviewSeverity.MEDIUM,
        category=ReviewCategory.QUALITY,
        title="Test finding",
        description="Test",
        file="test.py",
        line=10,
    )

    data = finding.to_dict()

    assert data["id"] == "test-001"
    assert data["severity"] == "medium"
    assert data["category"] == "quality"


def test_pr_review_finding_from_dict():
    """Test deserializing finding from dict."""
    from runners.github.models import PRReviewFinding

    data = {
        "id": "test-001",
        "severity": "high",
        "category": "security",
        "title": "Test",
        "description": "Test desc",
        "file": "test.py",
        "line": 10,
    }

    finding = PRReviewFinding.from_dict(data)

    assert finding.id == "test-001"
    assert finding.severity.value == "high"
    assert finding.category.value == "security"


# =============================================================================
# BATCH STATUS ENUM TESTS
# =============================================================================


def test_batch_status_enum():
    """Test batch status enum."""
    from runners.github.batch_issues import BatchStatus

    assert BatchStatus.PENDING.value == "pending"
    assert BatchStatus.BUILDING.value == "building"
    assert BatchStatus.COMPLETED.value == "completed"
    assert BatchStatus.FAILED.value == "failed"


# =============================================================================
# ISSUE BATCH ITEM TESTS
# =============================================================================


def test_issue_batch_item_creation():
    """Test creating issue batch item."""
    from runners.github.batch_issues import IssueBatchItem

    item = IssueBatchItem(
        issue_number=123,
        title="Test issue",
        body="Test body",
        labels=["bug", "critical"],
        similarity_to_primary=0.85,
    )

    assert item.issue_number == 123
    assert item.title == "Test issue"
    assert item.similarity_to_primary == 0.85
    assert len(item.labels) == 2


def test_issue_batch_item_serialization():
    """Test issue batch item serialization."""
    from runners.github.batch_issues import IssueBatchItem

    item = IssueBatchItem(
        issue_number=123,
        title="Test",
        body="Body",
        labels=["bug"],
    )

    # To dict
    data = item.to_dict()
    assert data["issue_number"] == 123

    # From dict
    restored = IssueBatchItem.from_dict(data)
    assert restored.issue_number == 123
    assert restored.title == "Test"


# =============================================================================
# ISSUE BATCH TESTS
# =============================================================================


def test_issue_batch_creation():
    """Test creating issue batch."""
    from runners.github.batch_issues import IssueBatch, IssueBatchItem

    items = [
        IssueBatchItem(1, "Issue 1", "Body 1", ["bug"]),
        IssueBatchItem(2, "Issue 2", "Body 2", ["bug"]),
    ]

    batch = IssueBatch(
        batch_id="001",
        repo="test/repo",
        primary_issue=1,
        issues=items,
        common_themes=["authentication", "login"],
    )

    assert batch.batch_id == "001"
    assert batch.primary_issue == 1
    assert len(batch.issues) == 2
    assert len(batch.common_themes) == 2


def test_issue_batch_get_issue_numbers():
    """Test getting issue numbers from batch."""
    from runners.github.batch_issues import IssueBatch, IssueBatchItem

    items = [
        IssueBatchItem(1, "Issue 1", "Body 1", []),
        IssueBatchItem(2, "Issue 2", "Body 2", []),
        IssueBatchItem(3, "Issue 3", "Body 3", []),
    ]

    batch = IssueBatch(
        batch_id="001",
        repo="test/repo",
        primary_issue=1,
        issues=items,
    )

    numbers = batch.get_issue_numbers()
    assert numbers == [1, 2, 3]


def test_issue_batch_update_status():
    """Test updating batch status."""
    from runners.github.batch_issues import IssueBatch, BatchStatus

    batch = IssueBatch(
        batch_id="001",
        repo="test/repo",
        primary_issue=1,
        issues=[],
    )

    assert batch.status == BatchStatus.PENDING

    batch.update_status(BatchStatus.BUILDING)
    assert batch.status == BatchStatus.BUILDING


@pytest.mark.asyncio
async def test_issue_batch_save_and_load(temp_dir):
    """Test saving and loading issue batch."""
    from runners.github.batch_issues import IssueBatch, IssueBatchItem

    github_dir = temp_dir / ".auto-claude" / "github"
    github_dir.mkdir(parents=True)
    (github_dir / "batches").mkdir()

    items = [IssueBatchItem(1, "Issue 1", "Body 1", ["bug"])]

    batch = IssueBatch(
        batch_id="test_batch",
        repo="test/repo",
        primary_issue=1,
        issues=items,
        common_themes=["test"],
    )

    await batch.save(github_dir)

    loaded = IssueBatch.load(github_dir, "test_batch")

    assert loaded is not None
    assert loaded.batch_id == "test_batch"
    assert loaded.primary_issue == 1
    assert len(loaded.issues) == 1


# =============================================================================
# AUTO FIX STATUS TESTS
# =============================================================================


def test_autofix_status_terminal_states():
    """Test auto-fix terminal states."""
    from runners.github.models import AutoFixStatus

    terminal = AutoFixStatus.terminal_states()

    assert AutoFixStatus.COMPLETED in terminal
    assert AutoFixStatus.FAILED in terminal
    assert AutoFixStatus.CANCELLED in terminal
    assert AutoFixStatus.PENDING not in terminal


def test_autofix_status_active_states():
    """Test auto-fix active states."""
    from runners.github.models import AutoFixStatus

    active = AutoFixStatus.active_states()

    assert AutoFixStatus.PENDING in active
    assert AutoFixStatus.BUILDING in active
    assert AutoFixStatus.COMPLETED not in active


def test_autofix_status_transitions():
    """Test auto-fix status transition validation."""
    from runners.github.models import AutoFixStatus

    # Valid transition
    assert AutoFixStatus.PENDING.can_transition_to(AutoFixStatus.ANALYZING) is True

    # Invalid transition
    assert AutoFixStatus.COMPLETED.can_transition_to(AutoFixStatus.PENDING) is False

    # Allow retry from FAILED
    assert AutoFixStatus.FAILED.can_transition_to(AutoFixStatus.PENDING) is True


# =============================================================================
# AI BOT PATTERN TESTS
# =============================================================================


def test_ai_bot_patterns():
    """Test AI bot pattern recognition."""
    from runners.github.context_gatherer import AI_BOT_PATTERNS

    assert "coderabbitai" in AI_BOT_PATTERNS
    assert "greptile[bot]" in AI_BOT_PATTERNS
    assert "copilot[bot]" in AI_BOT_PATTERNS
    assert "dependabot[bot]" in AI_BOT_PATTERNS

    assert AI_BOT_PATTERNS["coderabbitai"] == "CodeRabbit"
    assert AI_BOT_PATTERNS["greptile[bot]"] == "Greptile"


# =============================================================================
# SIMILARITY THRESHOLD TESTS
# =============================================================================


def test_similar_threshold_constant():
    """Test similarity threshold constant."""
    from runners.github.batch_issues import SIMILAR_THRESHOLD

    # Should be a reasonable threshold for similarity
    assert 0.0 < SIMILAR_THRESHOLD < 1.0
    assert isinstance(SIMILAR_THRESHOLD, float)
