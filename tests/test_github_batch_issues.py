#!/usr/bin/env python3
"""
Tests for GitHub Issue Batching
================================

Tests for the batch issue processing system that groups similar issues
for combined auto-fix.
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


@pytest.fixture
def github_dir(temp_dir):
    """Create GitHub directory structure."""
    github_dir = temp_dir / ".auto-claude" / "github"
    github_dir.mkdir(parents=True)
    (github_dir / "batches").mkdir()
    return github_dir


@pytest.fixture
def sample_issues():
    """Sample GitHub issues for testing."""
    return [
        {
            "number": 1,
            "title": "Login button not working",
            "body": "The login button doesn't respond to clicks",
            "labels": [{"name": "bug"}],
        },
        {
            "number": 2,
            "title": "Logout functionality broken",
            "body": "Users can't log out properly",
            "labels": [{"name": "bug"}],
        },
        {
            "number": 3,
            "title": "Add dark mode",
            "body": "Need dark theme support",
            "labels": [{"name": "feature"}],
        },
        {
            "number": 4,
            "title": "Authentication timeout",
            "body": "Sessions expire too quickly",
            "labels": [{"name": "bug"}, {"name": "security"}],
        },
    ]


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


def test_issue_batch_item_to_dict():
    """Test serializing issue batch item to dict."""
    from runners.github.batch_issues import IssueBatchItem

    item = IssueBatchItem(
        issue_number=123,
        title="Test",
        body="Body",
        labels=["bug"],
    )

    data = item.to_dict()

    assert data["issue_number"] == 123
    assert data["title"] == "Test"
    assert data["labels"] == ["bug"]


def test_issue_batch_item_from_dict():
    """Test deserializing issue batch item from dict."""
    from runners.github.batch_issues import IssueBatchItem

    data = {
        "issue_number": 123,
        "title": "Test",
        "body": "Body",
        "labels": ["bug"],
        "similarity_to_primary": 0.9,
    }

    item = IssueBatchItem.from_dict(data)

    assert item.issue_number == 123
    assert item.similarity_to_primary == 0.9


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


@pytest.mark.asyncio
async def test_issue_batch_save_and_load(github_dir):
    """Test saving and loading issue batch."""
    from runners.github.batch_issues import IssueBatch, IssueBatchItem

    items = [
        IssueBatchItem(1, "Issue 1", "Body 1", ["bug"]),
    ]

    batch = IssueBatch(
        batch_id="test_001",
        repo="test/repo",
        primary_issue=1,
        issues=items,
        common_themes=["test"],
    )

    await batch.save(github_dir)

    loaded = IssueBatch.load(github_dir, "test_001")

    assert loaded is not None
    assert loaded.batch_id == "test_001"
    assert loaded.primary_issue == 1
    assert len(loaded.issues) == 1


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

    batch.update_status(BatchStatus.BUILDING, error=None)

    assert batch.status == BatchStatus.BUILDING


# =============================================================================
# CLAUDE BATCH ANALYZER TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_claude_batch_analyzer_single_issue():
    """Test analyzer with single issue."""
    from runners.github.batch_issues import ClaudeBatchAnalyzer

    analyzer = ClaudeBatchAnalyzer()

    issues = [
        {"number": 1, "title": "Bug", "body": "Description", "labels": []}
    ]

    batches = await analyzer.analyze_and_batch_issues(issues)

    assert len(batches) == 1
    assert batches[0]["issue_numbers"] == [1]
    assert batches[0]["confidence"] == 1.0


@pytest.mark.asyncio
async def test_claude_batch_analyzer_empty_issues():
    """Test analyzer with empty issues list."""
    from runners.github.batch_issues import ClaudeBatchAnalyzer

    analyzer = ClaudeBatchAnalyzer()
    batches = await analyzer.analyze_and_batch_issues([])

    assert batches == []


def test_parse_json_response_simple():
    """Test parsing simple JSON response."""
    from runners.github.batch_issues import ClaudeBatchAnalyzer

    analyzer = ClaudeBatchAnalyzer()

    response = '{"batches": [{"issue_numbers": [1, 2]}]}'
    result = analyzer._parse_json_response(response)

    assert "batches" in result
    assert len(result["batches"]) == 1


def test_parse_json_response_with_markdown():
    """Test parsing JSON wrapped in markdown."""
    from runners.github.batch_issues import ClaudeBatchAnalyzer

    analyzer = ClaudeBatchAnalyzer()

    response = '```json\n{"batches": [{"issue_numbers": [1]}]}\n```'
    result = analyzer._parse_json_response(response)

    assert "batches" in result


# =============================================================================
# ISSUE BATCHER INITIALIZATION TESTS
# =============================================================================


def test_issue_batcher_initialization(github_dir):
    """Test issue batcher initialization."""
    from runners.github.batch_issues import IssueBatcher

    batcher = IssueBatcher(
        github_dir=github_dir,
        repo="test/repo",
        min_batch_size=2,
        max_batch_size=5,
    )

    assert batcher.github_dir == github_dir
    assert batcher.repo == "test/repo"
    assert batcher.min_batch_size == 2
    assert batcher.max_batch_size == 5


# =============================================================================
# PRE-GROUPING TESTS
# =============================================================================


def test_pre_group_by_labels(github_dir, sample_issues):
    """Test pre-grouping issues by labels."""
    from runners.github.batch_issues import IssueBatcher

    batcher = IssueBatcher(
        github_dir=github_dir,
        repo="test/repo",
    )

    pre_groups = batcher._pre_group_by_labels_and_keywords(sample_issues)

    # Should have at least 2 groups (bug and feature)
    assert len(pre_groups) >= 2

    # Bug issues should be grouped together
    bug_group = next((g for g in pre_groups if len(g) > 1), None)
    assert bug_group is not None


def test_group_by_title_keywords(github_dir):
    """Test grouping by title keywords."""
    from runners.github.batch_issues import IssueBatcher

    batcher = IssueBatcher(
        github_dir=github_dir,
        repo="test/repo",
    )

    # Use titles that only match a single specific keyword to avoid
    # set iteration order issues (keywords are stored in a set)
    issues = [
        {"number": 1, "title": "Login page broken", "body": "", "labels": []},
        {"number": 2, "title": "Login button missing", "body": "", "labels": []},
        {"number": 3, "title": "Dashboard widget", "body": "", "labels": []},
    ]

    groups = batcher._group_by_title_keywords(issues)

    # Should group login-related issues together (both match "login" keyword)
    login_group = next((g for g in groups if len(g) == 2), None)
    assert login_group is not None
    # Verify both login issues are in the same group
    group_numbers = {i["number"] for i in login_group}
    assert group_numbers == {1, 2}


# =============================================================================
# BATCH CREATION TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_create_batches_success(github_dir, sample_issues):
    """Test creating batches from issues."""
    from runners.github.batch_issues import IssueBatcher

    with patch("runners.github.batch_issues.ClaudeBatchAnalyzer") as mock_analyzer_class:
        with patch("runners.github.batch_issues.BatchValidator"):
            mock_analyzer = mock_analyzer_class.return_value
            mock_analyzer.analyze_and_batch_issues = AsyncMock(
                return_value=[
                    {
                        "issue_numbers": [1, 2],
                        "theme": "Login issues",
                        "reasoning": "Both related to auth",
                        "confidence": 0.9,
                    },
                    {
                        "issue_numbers": [3],
                        "theme": "Dark mode",
                        "reasoning": "Feature request",
                        "confidence": 1.0,
                    },
                ]
            )

            batcher = IssueBatcher(
                github_dir=github_dir,
                repo="test/repo",
                validate_batches=False,  # Disable validation for this test
            )

            batches = await batcher.create_batches(sample_issues)

    # Should create batches
    assert len(batches) >= 1
    assert all(b.repo == "test/repo" for b in batches)


@pytest.mark.asyncio
async def test_create_batches_excludes_existing(github_dir, sample_issues):
    """Test batch creation excludes already-batched issues."""
    from runners.github.batch_issues import IssueBatcher, IssueBatch, IssueBatchItem

    # Create existing batch with issue 1
    existing_batch = IssueBatch(
        batch_id="existing",
        repo="test/repo",
        primary_issue=1,
        issues=[IssueBatchItem(1, "Issue 1", "Body", [])],
    )
    await existing_batch.save(github_dir)

    with patch("runners.github.batch_issues.ClaudeBatchAnalyzer") as mock_analyzer_class:
        with patch("runners.github.batch_issues.BatchValidator"):
            # Set up analyzer to return batches for issues 2, 3
            mock_analyzer = mock_analyzer_class.return_value
            mock_analyzer.analyze_and_batch_issues = AsyncMock(
                return_value=[
                    {
                        "issue_numbers": [2, 3],
                        "theme": "Test theme",
                        "reasoning": "Test reasoning",
                        "confidence": 0.9,
                    }
                ]
            )

            batcher = IssueBatcher(
                github_dir=github_dir,
                repo="test/repo",
                validate_batches=False,
            )

            # Load existing batches
            batcher._load_batch_index()

            # Exclude issue 1
            exclude = {1}
            batches = await batcher.create_batches(sample_issues, exclude_issue_numbers=exclude)

    # Should not include issue 1 in new batches
    for batch in batches:
        assert 1 not in batch.get_issue_numbers()


# =============================================================================
# BATCH RETRIEVAL TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_get_batch_for_issue(github_dir):
    """Test retrieving batch containing an issue."""
    from runners.github.batch_issues import IssueBatcher, IssueBatch, IssueBatchItem

    # Create batch
    batch = IssueBatch(
        batch_id="test_batch",
        repo="test/repo",
        primary_issue=1,
        issues=[
            IssueBatchItem(1, "Issue 1", "Body", []),
            IssueBatchItem(2, "Issue 2", "Body", []),
        ],
    )
    await batch.save(github_dir)

    batcher = IssueBatcher(
        github_dir=github_dir,
        repo="test/repo",
    )

    # Update index manually
    batcher._batch_index[1] = "test_batch"
    batcher._batch_index[2] = "test_batch"

    retrieved = batcher.get_batch_for_issue(1)

    assert retrieved is not None
    assert retrieved.batch_id == "test_batch"
    assert 1 in retrieved.get_issue_numbers()


def test_get_batch_for_nonexistent_issue(github_dir):
    """Test retrieving batch for non-existent issue."""
    from runners.github.batch_issues import IssueBatcher

    batcher = IssueBatcher(
        github_dir=github_dir,
        repo="test/repo",
    )

    batch = batcher.get_batch_for_issue(999)

    assert batch is None


@pytest.mark.asyncio
async def test_get_all_batches(github_dir):
    """Test retrieving all batches."""
    from runners.github.batch_issues import IssueBatcher, IssueBatch, IssueBatchItem

    # Create multiple batches
    batch1 = IssueBatch(
        batch_id="batch_001",
        repo="test/repo",
        primary_issue=1,
        issues=[IssueBatchItem(1, "Issue 1", "Body", [])],
    )
    batch2 = IssueBatch(
        batch_id="batch_002",
        repo="test/repo",
        primary_issue=2,
        issues=[IssueBatchItem(2, "Issue 2", "Body", [])],
    )

    await batch1.save(github_dir)
    await batch2.save(github_dir)

    batcher = IssueBatcher(
        github_dir=github_dir,
        repo="test/repo",
    )

    all_batches = batcher.get_all_batches()

    assert len(all_batches) == 2
    batch_ids = {b.batch_id for b in all_batches}
    assert "batch_001" in batch_ids
    assert "batch_002" in batch_ids


# =============================================================================
# BATCH STATUS FILTERING TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_get_pending_batches(github_dir):
    """Test retrieving pending batches."""
    from runners.github.batch_issues import IssueBatcher, IssueBatch, BatchStatus, IssueBatchItem

    # Create batches with different statuses
    pending = IssueBatch(
        batch_id="pending",
        repo="test/repo",
        primary_issue=1,
        issues=[IssueBatchItem(1, "Issue 1", "Body", [])],
        status=BatchStatus.PENDING,
    )
    building = IssueBatch(
        batch_id="building",
        repo="test/repo",
        primary_issue=2,
        issues=[IssueBatchItem(2, "Issue 2", "Body", [])],
        status=BatchStatus.BUILDING,
    )
    completed = IssueBatch(
        batch_id="completed",
        repo="test/repo",
        primary_issue=3,
        issues=[IssueBatchItem(3, "Issue 3", "Body", [])],
        status=BatchStatus.COMPLETED,
    )

    await pending.save(github_dir)
    await building.save(github_dir)
    await completed.save(github_dir)

    batcher = IssueBatcher(
        github_dir=github_dir,
        repo="test/repo",
    )

    pending_batches = batcher.get_pending_batches()

    assert len(pending_batches) == 1
    assert pending_batches[0].status == BatchStatus.PENDING


@pytest.mark.asyncio
async def test_get_active_batches(github_dir):
    """Test retrieving active batches."""
    from runners.github.batch_issues import IssueBatcher, IssueBatch, BatchStatus, IssueBatchItem

    # Create batches
    building = IssueBatch(
        batch_id="building",
        repo="test/repo",
        primary_issue=1,
        issues=[IssueBatchItem(1, "Issue 1", "Body", [])],
        status=BatchStatus.BUILDING,
    )
    qa_review = IssueBatch(
        batch_id="qa",
        repo="test/repo",
        primary_issue=2,
        issues=[IssueBatchItem(2, "Issue 2", "Body", [])],
        status=BatchStatus.QA_REVIEW,
    )
    completed = IssueBatch(
        batch_id="completed",
        repo="test/repo",
        primary_issue=3,
        issues=[IssueBatchItem(3, "Issue 3", "Body", [])],
        status=BatchStatus.COMPLETED,
    )

    await building.save(github_dir)
    await qa_review.save(github_dir)
    await completed.save(github_dir)

    batcher = IssueBatcher(
        github_dir=github_dir,
        repo="test/repo",
    )

    active = batcher.get_active_batches()

    assert len(active) == 2
    assert all(b.status in (BatchStatus.BUILDING, BatchStatus.QA_REVIEW) for b in active)


# =============================================================================
# BATCH REMOVAL TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_remove_batch(github_dir):
    """Test removing a batch."""
    from runners.github.batch_issues import IssueBatcher, IssueBatch, IssueBatchItem

    # Create batch
    batch = IssueBatch(
        batch_id="to_remove",
        repo="test/repo",
        primary_issue=1,
        issues=[
            IssueBatchItem(1, "Issue 1", "Body", []),
            IssueBatchItem(2, "Issue 2", "Body", []),
        ],
    )
    await batch.save(github_dir)

    batcher = IssueBatcher(
        github_dir=github_dir,
        repo="test/repo",
    )

    # Add to index
    batcher._batch_index[1] = "to_remove"
    batcher._batch_index[2] = "to_remove"
    batcher._save_batch_index()

    # Remove batch
    removed = batcher.remove_batch("to_remove")

    assert removed is True
    assert 1 not in batcher._batch_index
    assert 2 not in batcher._batch_index

    # File should be deleted
    batch_file = github_dir / "batches" / "batch_to_remove.json"
    assert not batch_file.exists()


# =============================================================================
# ISSUE MEMBERSHIP TESTS
# =============================================================================


def test_is_issue_in_batch(github_dir):
    """Test checking if issue is in a batch."""
    from runners.github.batch_issues import IssueBatcher

    batcher = IssueBatcher(
        github_dir=github_dir,
        repo="test/repo",
    )

    # Add issue to index
    batcher._batch_index[123] = "batch_001"

    assert batcher.is_issue_in_batch(123) is True
    assert batcher.is_issue_in_batch(456) is False


# =============================================================================
# THEME EXTRACTION TESTS
# =============================================================================


def test_extract_common_themes(github_dir):
    """Test extracting common themes from issues."""
    from runners.github.batch_issues import IssueBatcher

    batcher = IssueBatcher(
        github_dir=github_dir,
        repo="test/repo",
    )

    issues = [
        {"title": "Login API timeout", "body": "The authentication endpoint is slow"},
        {"title": "OAuth login failing", "body": "Users can't log in with OAuth"},
    ]

    themes = batcher._extract_common_themes(issues)

    # Should identify common themes like "authentication", "login", "api", "oauth"
    assert any(theme in ["authentication", "login", "api", "oauth"] for theme in themes)


# =============================================================================
# CLUSTERING TESTS
# =============================================================================


def test_cluster_issues(github_dir):
    """Test clustering issues by similarity."""
    from runners.github.batch_issues import IssueBatcher

    batcher = IssueBatcher(
        github_dir=github_dir,
        repo="test/repo",
        similarity_threshold=0.7,
        max_batch_size=5,
    )

    issues = [
        {"number": 1, "title": "Issue 1", "body": "", "labels": []},
        {"number": 2, "title": "Issue 2", "body": "", "labels": []},
        {"number": 3, "title": "Issue 3", "body": "", "labels": []},
    ]

    # Create similarity matrix (1 and 2 are similar, 3 is different)
    similarity_matrix = {
        (1, 2): 0.9,
        (2, 1): 0.9,
        (1, 3): 0.3,
        (3, 1): 0.3,
        (2, 3): 0.3,
        (3, 2): 0.3,
    }

    clusters = batcher._cluster_issues(issues, similarity_matrix)

    # Should create 2 clusters: [1, 2] and [3]
    assert len(clusters) >= 1

    # Find cluster with issues 1 and 2
    large_cluster = max(clusters, key=len)
    if len(large_cluster) > 1:
        assert 1 in large_cluster and 2 in large_cluster


# =============================================================================
# BATCH INDEX MANAGEMENT TESTS
# =============================================================================


def test_save_and_load_batch_index(github_dir):
    """Test saving and loading batch index."""
    from runners.github.batch_issues import IssueBatcher

    batcher = IssueBatcher(
        github_dir=github_dir,
        repo="test/repo",
    )

    # Add entries
    batcher._batch_index[1] = "batch_001"
    batcher._batch_index[2] = "batch_001"
    batcher._batch_index[3] = "batch_002"

    # Save
    batcher._save_batch_index()

    # Create new batcher and load
    new_batcher = IssueBatcher(
        github_dir=github_dir,
        repo="test/repo",
    )
    new_batcher._load_batch_index()

    assert new_batcher._batch_index[1] == "batch_001"
    assert new_batcher._batch_index[2] == "batch_001"
    assert new_batcher._batch_index[3] == "batch_002"


def test_generate_batch_id(github_dir):
    """Test batch ID generation."""
    from runners.github.batch_issues import IssueBatcher

    batcher = IssueBatcher(
        github_dir=github_dir,
        repo="test/repo",
    )

    batch_id = batcher._generate_batch_id(primary_issue=123)

    assert batch_id.startswith("123_")
    assert len(batch_id) > 4  # Should have timestamp
