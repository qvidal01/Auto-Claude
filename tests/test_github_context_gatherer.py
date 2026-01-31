#!/usr/bin/env python3
"""
Tests for PR Context Gatherer
==============================

Tests for the PR context gathering module that collects all necessary
information before AI review starts.
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
def mock_gh_client():
    """Create mock GH client for context gatherer."""
    client = MagicMock()
    client.pr_get = AsyncMock()
    client.pr_diff = AsyncMock()
    client.run = AsyncMock()
    client.get_pr_head_sha = AsyncMock()
    client.get_pr_files_changed_since = AsyncMock()
    client.compare_commits = AsyncMock()
    client.get_comments_since = AsyncMock()
    client.get_reviews_since = AsyncMock()
    return client


@pytest.fixture
def sample_pr_data():
    """Sample PR data from GitHub API."""
    return {
        "number": 123,
        "title": "Add user authentication",
        "body": "Implements OAuth2 authentication",
        "state": "open",
        "author": {"login": "test-user"},
        "baseRefName": "main",
        "headRefName": "feature/auth",
        "headRefOid": "abc123def",
        "baseRefOid": "def456ghi",
        "files": [
            {
                "path": "src/auth.py",
                "status": "added",
                "additions": 50,
                "deletions": 0,
            },
            {
                "path": "src/user.py",
                "status": "modified",
                "additions": 10,
                "deletions": 5,
            },
        ],
        "additions": 60,
        "deletions": 5,
        "changedFiles": 2,
        "labels": [{"name": "feature"}],
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "CLEAN",
    }


# =============================================================================
# CONTEXT GATHERER INITIALIZATION TESTS
# =============================================================================


def test_context_gatherer_initialization(temp_dir):
    """Test context gatherer initialization."""
    from runners.github.context_gatherer import PRContextGatherer

    gatherer = PRContextGatherer(
        project_dir=temp_dir,
        pr_number=123,
        repo="test/repo",
    )

    assert gatherer.project_dir == temp_dir
    assert gatherer.pr_number == 123
    assert gatherer.repo == "test/repo"


# =============================================================================
# PR CONTEXT GATHERING TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_gather_pr_context_success(temp_dir, sample_pr_data, mock_gh_client):
    """Test successful PR context gathering."""
    from runners.github.context_gatherer import PRContextGatherer

    # Setup mocks
    mock_gh_client.pr_get.return_value = sample_pr_data
    mock_gh_client.pr_diff.return_value = "diff content here"

    # Mock review comments API
    mock_gh_client.run.return_value = MagicMock(
        returncode=0,
        stdout="[]",
    )

    with patch("runners.github.context_gatherer.GHClient", return_value=mock_gh_client):
        # Mock file content reading
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"file content", b""))
            mock_subprocess.return_value = mock_proc

            gatherer = PRContextGatherer(
                project_dir=temp_dir,
                pr_number=123,
            )

            context = await gatherer.gather()

    assert context.pr_number == 123
    assert context.title == "Add user authentication"
    assert context.author == "test-user"
    assert context.base_branch == "main"
    assert context.head_branch == "feature/auth"
    assert len(context.changed_files) == 2
    assert context.total_additions == 60
    assert context.total_deletions == 5
    assert context.has_merge_conflicts is False


@pytest.mark.asyncio
async def test_gather_pr_context_with_merge_conflicts(temp_dir, sample_pr_data, mock_gh_client):
    """Test PR context gathering with merge conflicts."""
    from runners.github.context_gatherer import PRContextGatherer

    # Set merge conflict status
    sample_pr_data["mergeable"] = "CONFLICTING"
    sample_pr_data["mergeStateStatus"] = "DIRTY"

    mock_gh_client.pr_get.return_value = sample_pr_data
    mock_gh_client.pr_diff.return_value = "diff content"
    mock_gh_client.run.return_value = MagicMock(returncode=0, stdout="[]")

    with patch("runners.github.context_gatherer.GHClient", return_value=mock_gh_client):
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"content", b""))
            mock_subprocess.return_value = mock_proc

            gatherer = PRContextGatherer(temp_dir, 123)
            context = await gatherer.gather()

    assert context.has_merge_conflicts is True
    assert context.merge_state_status == "DIRTY"


@pytest.mark.asyncio
async def test_gather_pr_context_large_diff(temp_dir, sample_pr_data, mock_gh_client):
    """Test PR context gathering with large diff (> 20K lines)."""
    from runners.github.context_gatherer import PRContextGatherer
    from runners.github.gh_client import PRTooLargeError

    mock_gh_client.pr_get.return_value = sample_pr_data
    mock_gh_client.pr_diff.side_effect = PRTooLargeError("PR exceeds 20,000 line limit")
    mock_gh_client.run.return_value = MagicMock(returncode=0, stdout="[]")

    with patch("runners.github.context_gatherer.GHClient", return_value=mock_gh_client):
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"content", b""))
            mock_subprocess.return_value = mock_proc

            gatherer = PRContextGatherer(temp_dir, 123)
            context = await gatherer.gather()

    # Diff should be empty, but files should be present
    assert context.diff == ""
    assert context.diff_truncated is True
    assert len(context.changed_files) > 0


# =============================================================================
# FILE CONTENT READING TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_read_file_content_success(temp_dir):
    """Test reading file content from git."""
    from runners.github.context_gatherer import PRContextGatherer

    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"file content here", b""))
        mock_subprocess.return_value = mock_proc

        gatherer = PRContextGatherer(temp_dir, 123)
        content = await gatherer._read_file_content("src/file.py", "abc123")

    assert content == "file content here"


@pytest.mark.asyncio
async def test_read_file_content_not_found(temp_dir):
    """Test reading non-existent file returns empty string."""
    from runners.github.context_gatherer import PRContextGatherer

    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_proc = MagicMock()
        mock_proc.returncode = 128  # File not found
        mock_proc.communicate = AsyncMock(return_value=(b"", b"not found"))
        mock_subprocess.return_value = mock_proc

        gatherer = PRContextGatherer(temp_dir, 123)
        content = await gatherer._read_file_content("missing.py", "abc123")

    assert content == ""


@pytest.mark.asyncio
async def test_read_file_content_invalid_path(temp_dir):
    """Test reading file with invalid path."""
    from runners.github.context_gatherer import PRContextGatherer

    gatherer = PRContextGatherer(temp_dir, 123)

    # Path with traversal attempt
    content = await gatherer._read_file_content("../../../etc/passwd", "abc123")
    assert content == ""

    # Path with absolute path
    content = await gatherer._read_file_content("/etc/passwd", "abc123")
    assert content == ""


# =============================================================================
# AI BOT COMMENT DETECTION TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_ai_bot_comments(temp_dir, mock_gh_client):
    """Test fetching AI bot comments."""
    from runners.github.context_gatherer import PRContextGatherer

    # Mock review comments (inline)
    review_comments = [
        {
            "id": 1,
            "author": {"login": "coderabbitai"},
            "body": "Consider using async/await here",
            "path": "src/file.py",
            "line": 10,
            "createdAt": "2024-01-01T00:00:00Z",
        },
        {
            "id": 2,
            "author": {"login": "human-reviewer"},
            "body": "Looks good",
            "path": "src/file.py",
            "line": 20,
            "createdAt": "2024-01-01T00:01:00Z",
        },
    ]

    # Mock issue comments (general)
    issue_comments = [
        {
            "id": 3,
            "author": {"login": "greptile[bot]"},
            "body": "This PR looks great!",
            "createdAt": "2024-01-01T00:02:00Z",
        }
    ]

    mock_gh_client.run.side_effect = [
        MagicMock(returncode=0, stdout=json.dumps(review_comments)),
        MagicMock(returncode=0, stdout=json.dumps(issue_comments)),
    ]

    gatherer = PRContextGatherer(temp_dir, 123)
    gatherer.gh_client = mock_gh_client

    ai_comments = await gatherer._fetch_ai_bot_comments()

    # Should have 2 AI comments (CodeRabbit and Greptile), not the human one
    assert len(ai_comments) == 2
    assert ai_comments[0].tool_name == "CodeRabbit"
    assert ai_comments[1].tool_name == "Greptile"


def test_parse_ai_comment_recognized_bot():
    """Test parsing comment from recognized AI bot."""
    from runners.github.context_gatherer import PRContextGatherer

    gatherer = PRContextGatherer(Path("/tmp"), 123)

    comment = {
        "id": 1,
        "author": {"login": "coderabbitai"},
        "body": "Consider refactoring",
        "path": "src/file.py",
        "line": 10,
        "createdAt": "2024-01-01T00:00:00Z",
    }

    result = gatherer._parse_ai_comment(comment, is_review_comment=True)

    assert result is not None
    assert result.tool_name == "CodeRabbit"
    assert result.file == "src/file.py"
    assert result.line == 10


def test_parse_ai_comment_human_user():
    """Test parsing comment from human user returns None."""
    from runners.github.context_gatherer import PRContextGatherer

    gatherer = PRContextGatherer(Path("/tmp"), 123)

    comment = {
        "id": 1,
        "author": {"login": "john-doe"},
        "body": "Looks good",
        "createdAt": "2024-01-01T00:00:00Z",
    }

    result = gatherer._parse_ai_comment(comment, is_review_comment=False)

    assert result is None


# =============================================================================
# REPOSITORY STRUCTURE DETECTION TESTS
# =============================================================================


def test_detect_repo_structure_monorepo(temp_dir):
    """Test detecting monorepo structure."""
    from runners.github.context_gatherer import PRContextGatherer

    # Create monorepo structure
    (temp_dir / "apps").mkdir()
    (temp_dir / "apps" / "backend").mkdir()
    (temp_dir / "apps" / "frontend").mkdir()
    (temp_dir / "packages").mkdir()
    (temp_dir / "packages" / "shared").mkdir()

    gatherer = PRContextGatherer(temp_dir, 123)
    structure = gatherer._detect_repo_structure()

    assert "backend" in structure
    assert "frontend" in structure
    assert "shared" in structure


def test_detect_repo_structure_python(temp_dir):
    """Test detecting Python project."""
    from runners.github.context_gatherer import PRContextGatherer

    (temp_dir / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (temp_dir / "requirements.txt").write_text("flask\n")

    gatherer = PRContextGatherer(temp_dir, 123)
    structure = gatherer._detect_repo_structure()

    assert "Python Project" in structure
    assert "requirements.txt" in structure


def test_detect_repo_structure_nextjs(temp_dir):
    """Test detecting Next.js framework."""
    from runners.github.context_gatherer import PRContextGatherer

    (temp_dir / "next.config.js").write_text("module.exports = {}\n")

    gatherer = PRContextGatherer(temp_dir, 123)
    structure = gatherer._detect_repo_structure()

    assert "Next.js" in structure


# =============================================================================
# IMPORT RESOLUTION TESTS
# =============================================================================


def test_resolve_import_path_relative(temp_dir):
    """Test resolving relative imports."""
    from runners.github.context_gatherer import PRContextGatherer

    # Create file structure
    (temp_dir / "src").mkdir()
    (temp_dir / "src" / "utils.ts").write_text("export const helper = () => {}")

    gatherer = PRContextGatherer(temp_dir, 123)

    # Import from src/index.ts -> ./utils
    source_path = Path("src/index.ts")
    resolved = gatherer._resolve_import_path("./utils", source_path)

    assert resolved == "src/utils.ts"


def test_resolve_import_path_with_extensions(temp_dir):
    """Test resolving imports with different extensions."""
    from runners.github.context_gatherer import PRContextGatherer

    # Create files
    (temp_dir / "src").mkdir()
    (temp_dir / "src" / "component.tsx").write_text("export const Component = () => {}")

    gatherer = PRContextGatherer(temp_dir, 123)

    source_path = Path("src/index.ts")
    resolved = gatherer._resolve_import_path("./component", source_path)

    assert resolved == "src/component.tsx"


def test_resolve_import_path_index_file(temp_dir):
    """Test resolving directory imports to index files."""
    from runners.github.context_gatherer import PRContextGatherer

    # Create directory with index
    (temp_dir / "src" / "utils").mkdir(parents=True)
    (temp_dir / "src" / "utils" / "index.ts").write_text("export * from './helper'")

    gatherer = PRContextGatherer(temp_dir, 123)

    source_path = Path("src/index.ts")
    resolved = gatherer._resolve_import_path("./utils", source_path)

    assert resolved == "src/utils/index.ts"


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
# FOLLOWUP CONTEXT GATHERER TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_followup_gather_no_changes(temp_dir, mock_gh_client):
    """Test follow-up gathering when no changes since review."""
    from runners.github.context_gatherer import FollowupContextGatherer
    from runners.github.models import PRReviewResult

    previous_review = PRReviewResult(
        pr_number=123,
        repo="test/repo",
        success=True,
        findings=[],
        summary="Previous review",
        overall_status="approve",
        reviewed_commit_sha="abc123",
    )

    mock_gh_client.get_pr_head_sha.return_value = "abc123"  # Same SHA

    with patch("runners.github.context_gatherer.GHClient", return_value=mock_gh_client):
        gatherer = FollowupContextGatherer(temp_dir, 123, previous_review)
        context = await gatherer.gather()

    assert context.previous_commit_sha == "abc123"
    assert context.current_commit_sha == "abc123"
    assert len(context.commits_since_review) == 0


@pytest.mark.asyncio
async def test_followup_gather_with_changes(temp_dir, mock_gh_client):
    """Test follow-up gathering with new changes."""
    from runners.github.context_gatherer import FollowupContextGatherer
    from runners.github.models import PRReviewResult

    previous_review = PRReviewResult(
        pr_number=123,
        repo="test/repo",
        success=True,
        findings=[],
        summary="Previous review",
        overall_status="approve",
        reviewed_commit_sha="abc123",
        reviewed_at="2024-01-01T00:00:00Z",
    )

    mock_gh_client.get_pr_head_sha.return_value = "def456"
    mock_gh_client.get_pr_files_changed_since.return_value = (
        [{"filename": "src/file.py", "patch": "diff content"}],
        [{"sha": "def456", "author": {"login": "test"}}],
    )
    mock_gh_client.get_comments_since.return_value = {
        "review_comments": [],
        "issue_comments": [],
    }
    mock_gh_client.get_reviews_since.return_value = []
    mock_gh_client.pr_get.return_value = {
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "CLEAN",
    }

    with patch("runners.github.context_gatherer.GHClient", return_value=mock_gh_client):
        gatherer = FollowupContextGatherer(temp_dir, 123, previous_review)
        context = await gatherer.gather()

    assert context.previous_commit_sha == "abc123"
    assert context.current_commit_sha == "def456"
    assert len(context.commits_since_review) == 1
    assert len(context.files_changed_since_review) == 1


@pytest.mark.asyncio
async def test_followup_gather_separates_ai_comments(temp_dir, mock_gh_client):
    """Test follow-up gatherer separates AI and contributor comments."""
    from runners.github.context_gatherer import FollowupContextGatherer
    from runners.github.models import PRReviewResult

    previous_review = PRReviewResult(
        pr_number=123,
        repo="test/repo",
        success=True,
        findings=[],
        summary="Previous review",
        overall_status="approve",
        reviewed_commit_sha="abc123",
        reviewed_at="2024-01-01T00:00:00Z",
    )

    mock_gh_client.get_pr_head_sha.return_value = "def456"
    mock_gh_client.get_pr_files_changed_since.return_value = (
        [{"filename": "src/file.py"}],
        [{"sha": "def456"}],
    )

    # Comments from both AI bots and humans
    mock_gh_client.get_comments_since.return_value = {
        "review_comments": [
            {"user": {"login": "coderabbitai"}, "body": "AI comment"},
            {"user": {"login": "john-doe"}, "body": "Human comment"},
        ],
        "issue_comments": [],
    }
    mock_gh_client.get_reviews_since.return_value = []
    mock_gh_client.pr_get.return_value = {
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "CLEAN",
    }

    with patch("runners.github.context_gatherer.GHClient", return_value=mock_gh_client):
        gatherer = FollowupContextGatherer(temp_dir, 123, previous_review)
        context = await gatherer.gather()

    # Should separate AI from contributor comments
    assert len(context.ai_bot_comments_since_review) == 1
    assert len(context.contributor_comments_since_review) == 1


# =============================================================================
# TSCONFIG PATH RESOLUTION TESTS
# =============================================================================


def test_load_tsconfig_paths(temp_dir):
    """Test loading path aliases from tsconfig.json."""
    from runners.github.context_gatherer import PRContextGatherer

    tsconfig = {
        "compilerOptions": {
            "paths": {
                "@/*": ["src/*"],
                "@shared/*": ["src/shared/*"],
            }
        }
    }

    (temp_dir / "tsconfig.json").write_text(json.dumps(tsconfig))

    gatherer = PRContextGatherer(temp_dir, 123)
    paths = gatherer._load_tsconfig_paths()

    assert paths is not None
    assert "@/*" in paths
    assert paths["@/*"] == ["src/*"]
    assert "@shared/*" in paths


def test_resolve_path_alias(temp_dir):
    """Test resolving path aliases."""
    from runners.github.context_gatherer import PRContextGatherer

    gatherer = PRContextGatherer(temp_dir, 123)

    paths = {
        "@/*": ["src/*"],
        "@shared/*": ["src/shared/*"],
    }

    # Resolve @/utils/helper
    resolved = gatherer._resolve_path_alias("@/utils/helper", paths)
    assert resolved == "src/utils/helper"

    # Resolve @shared/types
    resolved = gatherer._resolve_path_alias("@shared/types", paths)
    assert resolved == "src/shared/types"

    # No match
    resolved = gatherer._resolve_path_alias("~/config", paths)
    assert resolved is None
