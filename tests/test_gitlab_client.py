#!/usr/bin/env python3
"""
Test suite for GitLab API client
=================================

Tests the GitLab client for API operations.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import json
import urllib.error
import urllib.request

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
from runners.gitlab.glab_client import (
    GitLabClient,
    GitLabConfig,
    encode_project_path,
    validate_endpoint,
    load_gitlab_config,
)


@pytest.fixture
def gitlab_config():
    """Create a GitLab config for testing."""
    return GitLabConfig(
        token="test-token-123",
        project="test-org/test-project",
        instance_url="https://gitlab.example.com",
    )


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    return project_dir


class TestEncodeProjectPath:
    """Test project path encoding."""

    def test_encode_simple_project(self):
        """Test encoding a simple project path."""
        result = encode_project_path("myorg/myproject")
        assert result == "myorg%2Fmyproject"

    def test_encode_nested_project(self):
        """Test encoding a nested project path."""
        result = encode_project_path("group/subgroup/project")
        assert result == "group%2Fsubgroup%2Fproject"

    def test_encode_special_characters(self):
        """Test encoding project with special characters."""
        result = encode_project_path("org/project-name")
        assert "/" not in result or result.count("/") == 0


class TestValidateEndpoint:
    """Test endpoint validation."""

    def test_validate_valid_project_endpoint(self):
        """Test validation of valid project endpoint."""
        # Should not raise
        validate_endpoint("/projects/123/merge_requests/1")

    def test_validate_valid_user_endpoint(self):
        """Test validation of valid user endpoint."""
        # Should not raise
        validate_endpoint("/user")

    def test_validate_empty_endpoint(self):
        """Test validation fails for empty endpoint."""
        with pytest.raises(ValueError, match="Endpoint cannot be empty"):
            validate_endpoint("")

    def test_validate_missing_leading_slash(self):
        """Test validation fails without leading slash."""
        with pytest.raises(ValueError, match="must start with /"):
            validate_endpoint("projects/123")

    def test_validate_path_traversal(self):
        """Test validation fails for path traversal attempts."""
        with pytest.raises(ValueError, match="path traversal"):
            validate_endpoint("/projects/../../../etc/passwd")

    def test_validate_null_byte(self):
        """Test validation fails for null bytes."""
        with pytest.raises(ValueError, match="null byte"):
            validate_endpoint("/projects/123\x00/merge_requests")

    def test_validate_unknown_pattern(self):
        """Test validation fails for unknown endpoint patterns."""
        with pytest.raises(ValueError, match="does not match known GitLab API patterns"):
            validate_endpoint("/malicious/endpoint")


class TestGitLabClientInitialization:
    """Test GitLab client initialization."""

    def test_client_init(self, temp_project_dir, gitlab_config):
        """Test client initialization."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        assert client.project_dir == temp_project_dir
        assert client.config == gitlab_config
        assert client.default_timeout == 30.0

    def test_client_init_custom_timeout(self, temp_project_dir, gitlab_config):
        """Test client initialization with custom timeout."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
            default_timeout=60.0,
        )

        assert client.default_timeout == 60.0


class TestApiUrl:
    """Test API URL construction."""

    def test_api_url_construction(self, temp_project_dir, gitlab_config):
        """Test API URL is constructed correctly."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        url = client._api_url("/projects/123")
        assert url == "https://gitlab.example.com/api/v4/projects/123"

    def test_api_url_adds_leading_slash(self, temp_project_dir, gitlab_config):
        """Test API URL adds leading slash if missing."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        url = client._api_url("projects/123")
        assert url == "https://gitlab.example.com/api/v4/projects/123"

    def test_api_url_strips_trailing_slash(self, temp_project_dir):
        """Test API URL strips trailing slash from instance URL."""
        config = GitLabConfig(
            token="test",
            project="org/proj",
            instance_url="https://gitlab.example.com/",
        )
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=config,
        )

        url = client._api_url("/projects/123")
        assert url == "https://gitlab.example.com/api/v4/projects/123"


class TestFetchMethod:
    """Test the _fetch method for API requests."""

    def test_fetch_validates_endpoint(self, temp_project_dir, gitlab_config):
        """Test that fetch validates endpoints."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        with pytest.raises(ValueError, match="does not match known GitLab API patterns"):
            client._fetch("/invalid/endpoint")

    def test_fetch_success_with_json_response(self, temp_project_dir, gitlab_config):
        """Test successful fetch with JSON response."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        mock_response_data = {"id": 123, "title": "Test MR"}
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(mock_response_data).encode('utf-8')
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = client._fetch("/projects/123/merge_requests/1")

        assert result == mock_response_data

    def test_fetch_success_with_204_no_content(self, temp_project_dir, gitlab_config):
        """Test successful fetch with 204 No Content response."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = client._fetch("/projects/123/merge_requests/1/approve", method="POST")

        assert result is None

    def test_fetch_with_post_data(self, temp_project_dir, gitlab_config):
        """Test fetch with POST data."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"success": true}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response) as mock_urlopen:
            client._fetch(
                "/projects/123/merge_requests/1/notes",
                method="POST",
                data={"body": "Test comment"}
            )

            # Verify request was made with data
            call_args = mock_urlopen.call_args
            request = call_args[0][0]
            assert request.method == "POST"
            assert request.data is not None

    def test_fetch_http_error_404(self, temp_project_dir, gitlab_config):
        """Test fetch with HTTP 404 error."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        error = urllib.error.HTTPError(
            url="test",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=MagicMock(read=lambda: b"Not found")
        )

        with patch('urllib.request.urlopen', side_effect=error):
            with pytest.raises(Exception, match="GitLab API error 404"):
                client._fetch("/projects/123/merge_requests/999")

    def test_fetch_rate_limit_with_retry(self, temp_project_dir, gitlab_config):
        """Test fetch handles rate limiting with retry."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        # First call returns 429, second call succeeds
        rate_limit_error = urllib.error.HTTPError(
            url="test",
            code=429,
            msg="Too Many Requests",
            hdrs={"Retry-After": "1"},
            fp=MagicMock(read=lambda: b"Rate limited")
        )

        mock_success_response = MagicMock()
        mock_success_response.status = 200
        mock_success_response.read.return_value = b'{"success": true}'
        mock_success_response.__enter__ = MagicMock(return_value=mock_success_response)
        mock_success_response.__exit__ = MagicMock(return_value=False)

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise rate_limit_error
            return mock_success_response

        with patch('urllib.request.urlopen', side_effect=side_effect):
            with patch('time.sleep'):  # Mock sleep to speed up test
                result = client._fetch("/projects/123")

        assert result == {"success": True}
        assert call_count == 2

    def test_fetch_rate_limit_max_retries_exceeded(self, temp_project_dir, gitlab_config):
        """Test fetch fails after max retries."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        rate_limit_error = urllib.error.HTTPError(
            url="test",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=MagicMock(read=lambda: b"Rate limited")
        )

        with patch('urllib.request.urlopen', side_effect=rate_limit_error):
            with patch('time.sleep'):
                with pytest.raises(Exception, match="GitLab API error 429"):
                    client._fetch("/projects/123", max_retries=2)

    def test_fetch_invalid_json_response(self, temp_project_dir, gitlab_config):
        """Test fetch handles invalid JSON response."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"Not valid JSON"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            with pytest.raises(Exception, match="Invalid JSON response"):
                client._fetch("/projects/123")


class TestGitLabClientMethods:
    """Test GitLab client API methods."""

    def test_get_mr(self, temp_project_dir, gitlab_config):
        """Test get_mr method."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        mock_mr = {"iid": 123, "title": "Test MR"}

        with patch.object(client, '_fetch', return_value=mock_mr) as mock_fetch:
            result = client.get_mr(123)

        assert result == mock_mr
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args[0][0]
        assert "merge_requests/123" in call_args

    def test_get_mr_changes(self, temp_project_dir, gitlab_config):
        """Test get_mr_changes method."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        mock_changes = {"changes": [{"diff": "+test"}]}

        with patch.object(client, '_fetch', return_value=mock_changes) as mock_fetch:
            result = client.get_mr_changes(123)

        assert result == mock_changes
        call_args = mock_fetch.call_args[0][0]
        assert "merge_requests/123/changes" in call_args

    def test_get_mr_diff(self, temp_project_dir, gitlab_config):
        """Test get_mr_diff method."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        mock_changes = {
            "changes": [
                {"diff": "+line1\n+line2"},
                {"diff": "+line3"},
            ]
        }

        with patch.object(client, 'get_mr_changes', return_value=mock_changes):
            result = client.get_mr_diff(123)

        assert result == "+line1\n+line2\n+line3"

    def test_get_mr_commits(self, temp_project_dir, gitlab_config):
        """Test get_mr_commits method."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        mock_commits = [{"id": "commit1"}, {"id": "commit2"}]

        with patch.object(client, '_fetch', return_value=mock_commits) as mock_fetch:
            result = client.get_mr_commits(123)

        assert result == mock_commits
        call_args = mock_fetch.call_args[0][0]
        assert "merge_requests/123/commits" in call_args

    def test_get_current_user(self, temp_project_dir, gitlab_config):
        """Test get_current_user method."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        mock_user = {"username": "testuser"}

        with patch.object(client, '_fetch', return_value=mock_user) as mock_fetch:
            result = client.get_current_user()

        assert result == mock_user
        mock_fetch.assert_called_with("/user")

    def test_post_mr_note(self, temp_project_dir, gitlab_config):
        """Test post_mr_note method."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        mock_note = {"id": 1, "body": "Test comment"}

        with patch.object(client, '_fetch', return_value=mock_note) as mock_fetch:
            result = client.post_mr_note(123, "Test comment")

        assert result == mock_note
        call_args = mock_fetch.call_args
        assert "merge_requests/123/notes" in call_args[0][0]
        assert call_args[1]["method"] == "POST"
        assert call_args[1]["data"] == {"body": "Test comment"}

    def test_approve_mr(self, temp_project_dir, gitlab_config):
        """Test approve_mr method."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        mock_approval = {"approved": True}

        with patch.object(client, '_fetch', return_value=mock_approval) as mock_fetch:
            result = client.approve_mr(123)

        assert result == mock_approval
        call_args = mock_fetch.call_args
        assert "merge_requests/123/approve" in call_args[0][0]
        assert call_args[1]["method"] == "POST"

    def test_merge_mr(self, temp_project_dir, gitlab_config):
        """Test merge_mr method."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        mock_merge = {"state": "merged"}

        with patch.object(client, '_fetch', return_value=mock_merge) as mock_fetch:
            result = client.merge_mr(123)

        assert result == mock_merge
        call_args = mock_fetch.call_args
        assert "merge_requests/123/merge" in call_args[0][0]
        assert call_args[1]["method"] == "PUT"

    def test_merge_mr_with_squash(self, temp_project_dir, gitlab_config):
        """Test merge_mr with squash option."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        with patch.object(client, '_fetch') as mock_fetch:
            client.merge_mr(123, squash=True)

        call_args = mock_fetch.call_args
        assert call_args[1]["data"] == {"squash": True}

    def test_assign_mr(self, temp_project_dir, gitlab_config):
        """Test assign_mr method."""
        client = GitLabClient(
            project_dir=temp_project_dir,
            config=gitlab_config,
        )

        mock_mr = {"assignees": [{"id": 1}, {"id": 2}]}

        with patch.object(client, '_fetch', return_value=mock_mr) as mock_fetch:
            result = client.assign_mr(123, [1, 2])

        assert result == mock_mr
        call_args = mock_fetch.call_args
        assert "merge_requests/123" in call_args[0][0]
        assert call_args[1]["method"] == "PUT"
        assert call_args[1]["data"] == {"assignee_ids": [1, 2]}


class TestLoadGitLabConfig:
    """Test loading GitLab config from project."""

    def test_load_gitlab_config_success(self, temp_project_dir):
        """Test successfully loading GitLab config."""
        config_dir = temp_project_dir / ".auto-claude" / "gitlab"
        config_dir.mkdir(parents=True)

        config_file = config_dir / "config.json"
        config_data = {
            "token": "test-token",
            "project": "org/project",
            "instance_url": "https://gitlab.example.com",
        }
        config_file.write_text(json.dumps(config_data))

        config = load_gitlab_config(temp_project_dir)

        assert config is not None
        assert config.token == "test-token"
        assert config.project == "org/project"
        assert config.instance_url == "https://gitlab.example.com"

    def test_load_gitlab_config_defaults_instance_url(self, temp_project_dir):
        """Test loading config uses default instance URL."""
        config_dir = temp_project_dir / ".auto-claude" / "gitlab"
        config_dir.mkdir(parents=True)

        config_file = config_dir / "config.json"
        config_data = {
            "token": "test-token",
            "project": "org/project",
        }
        config_file.write_text(json.dumps(config_data))

        config = load_gitlab_config(temp_project_dir)

        assert config.instance_url == "https://gitlab.com"

    def test_load_gitlab_config_file_not_found(self, temp_project_dir):
        """Test loading config when file doesn't exist."""
        config = load_gitlab_config(temp_project_dir)
        assert config is None

    def test_load_gitlab_config_missing_required_fields(self, temp_project_dir):
        """Test loading config with missing required fields."""
        config_dir = temp_project_dir / ".auto-claude" / "gitlab"
        config_dir.mkdir(parents=True)

        config_file = config_dir / "config.json"
        config_data = {"token": "test-token"}  # Missing project
        config_file.write_text(json.dumps(config_data))

        config = load_gitlab_config(temp_project_dir)
        assert config is None

    def test_load_gitlab_config_invalid_json(self, temp_project_dir):
        """Test loading config with invalid JSON."""
        config_dir = temp_project_dir / ".auto-claude" / "gitlab"
        config_dir.mkdir(parents=True)

        config_file = config_dir / "config.json"
        config_file.write_text("invalid json{")

        config = load_gitlab_config(temp_project_dir)
        assert config is None
