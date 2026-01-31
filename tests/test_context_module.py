"""
Tests for the context module
=============================

Tests covering context/models.py, context/categorizer.py, context/keyword_extractor.py
"""

import pytest
from context.models import FileMatch, TaskContext
from context.categorizer import FileCategorizer
from context.keyword_extractor import KeywordExtractor


# =============================================================================
# FileMatch Tests
# =============================================================================

class TestFileMatch:
    """Tests for FileMatch dataclass."""

    def test_file_match_creation(self):
        """Test basic FileMatch creation."""
        match = FileMatch(
            path="src/auth.py",
            service="auth",
            reason="Matched keyword 'login'",
            relevance_score=8.5
        )
        assert match.path == "src/auth.py"
        assert match.service == "auth"
        assert match.reason == "Matched keyword 'login'"
        assert match.relevance_score == 8.5
        assert match.matching_lines == []

    def test_file_match_with_matching_lines(self):
        """Test FileMatch with matching lines."""
        match = FileMatch(
            path="src/db.py",
            service="database",
            reason="Contains query methods",
            relevance_score=7.0,
            matching_lines=[(10, "def query():"), (20, "def execute():")]
        )
        assert len(match.matching_lines) == 2
        assert match.matching_lines[0] == (10, "def query():")

    def test_file_match_default_values(self):
        """Test FileMatch default values."""
        match = FileMatch(
            path="src/utils.py",
            service="utils",
            reason="Utility functions"
        )
        assert match.relevance_score == 0.0
        assert match.matching_lines == []


# =============================================================================
# TaskContext Tests
# =============================================================================

class TestTaskContext:
    """Tests for TaskContext dataclass."""

    def test_task_context_creation(self):
        """Test TaskContext creation."""
        context = TaskContext(
            task_description="Add authentication feature",
            scoped_services=["auth", "users"],
            files_to_modify=[{"path": "auth.py"}],
            files_to_reference=[{"path": "utils.py"}],
            patterns_discovered={"auth": "JWT pattern"},
            service_contexts={"auth": {"description": "Auth service"}}
        )
        assert context.task_description == "Add authentication feature"
        assert "auth" in context.scoped_services
        assert len(context.files_to_modify) == 1
        assert context.graph_hints == []

    def test_task_context_with_graph_hints(self):
        """Test TaskContext with graph hints."""
        context = TaskContext(
            task_description="Fix bug",
            scoped_services=[],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={},
            graph_hints=[{"hint": "Previous fix in auth.py"}]
        )
        assert len(context.graph_hints) == 1


# =============================================================================
# FileCategorizer Tests
# =============================================================================

class TestFileCategorizer:
    """Tests for FileCategorizer."""

    @pytest.fixture
    def categorizer(self):
        return FileCategorizer()

    @pytest.fixture
    def sample_matches(self):
        return [
            FileMatch(path="src/auth/login.py", service="auth", reason="login", relevance_score=8.0),
            FileMatch(path="src/auth/utils.py", service="auth", reason="utils", relevance_score=4.0),
            FileMatch(path="tests/test_auth.py", service="auth", reason="test", relevance_score=6.0),
            FileMatch(path="examples/auth_example.py", service="auth", reason="example", relevance_score=5.0),
            FileMatch(path="config/auth_config.json", service="auth", reason="config", relevance_score=3.0),
        ]

    def test_categorize_modification_task(self, categorizer, sample_matches):
        """Test categorization for modification task."""
        to_modify, to_reference = categorizer.categorize_matches(
            sample_matches,
            task="Add new login feature",
            max_modify=5,
            max_reference=10
        )

        # High relevance file should be in modify list
        modify_paths = [m.path for m in to_modify]
        assert "src/auth/login.py" in modify_paths

        # Test file should be in reference
        reference_paths = [m.path for m in to_reference]
        assert "tests/test_auth.py" in reference_paths

    def test_categorize_reference_task(self, categorizer, sample_matches):
        """Test categorization for non-modification task."""
        to_modify, to_reference = categorizer.categorize_matches(
            sample_matches,
            task="Understand the authentication system",
            max_modify=5,
            max_reference=10
        )

        # Non-modification task should have fewer modify files
        assert len(to_modify) < len(sample_matches)

    def test_test_files_are_references(self, categorizer):
        """Test that test files are categorized as references."""
        matches = [
            FileMatch(path="tests/test_auth.py", service="auth", reason="test", relevance_score=9.0),
            FileMatch(path="src/auth.spec.ts", service="auth", reason="spec", relevance_score=8.0),
        ]

        to_modify, to_reference = categorizer.categorize_matches(
            matches, task="Add feature", max_modify=5, max_reference=10
        )

        assert len(to_modify) == 0
        assert len(to_reference) == 2

    def test_example_files_are_references(self, categorizer):
        """Test that example files are categorized as references."""
        matches = [
            FileMatch(path="examples/sample.py", service="demo", reason="sample", relevance_score=9.0),
        ]

        to_modify, to_reference = categorizer.categorize_matches(
            matches, task="Add feature", max_modify=5, max_reference=10
        )

        assert len(to_modify) == 0
        assert len(to_reference) == 1

    def test_respects_max_limits(self, categorizer):
        """Test that max limits are respected."""
        matches = [
            FileMatch(path=f"src/file{i}.py", service="svc", reason="match", relevance_score=8.0)
            for i in range(20)
        ]

        to_modify, to_reference = categorizer.categorize_matches(
            matches, task="Add feature", max_modify=3, max_reference=5
        )

        assert len(to_modify) <= 3
        assert len(to_reference) <= 5

    def test_empty_matches(self, categorizer):
        """Test with empty matches list."""
        to_modify, to_reference = categorizer.categorize_matches(
            [], task="Add feature", max_modify=5, max_reference=10
        )

        assert to_modify == []
        assert to_reference == []

    def test_modify_keywords_detected(self, categorizer):
        """Test that modify keywords are properly detected."""
        matches = [
            FileMatch(path="src/auth.py", service="auth", reason="auth", relevance_score=8.0),
        ]

        # Test each modify keyword
        for keyword in ["add", "create", "implement", "fix", "update", "change", "modify", "new"]:
            to_modify, _ = categorizer.categorize_matches(
                matches, task=f"{keyword} authentication", max_modify=5, max_reference=10
            )
            # High relevance + modify keyword = modify list
            assert len(to_modify) > 0, f"Keyword '{keyword}' should trigger modify categorization"


# =============================================================================
# KeywordExtractor Tests
# =============================================================================

class TestKeywordExtractor:
    """Tests for KeywordExtractor."""

    def test_extract_basic_keywords(self):
        """Test basic keyword extraction."""
        keywords = KeywordExtractor.extract_keywords("authentication login user session")

        assert "authentication" in keywords
        assert "login" in keywords
        assert "user" in keywords
        assert "session" in keywords

    def test_filters_stopwords(self):
        """Test that stopwords are filtered out."""
        keywords = KeywordExtractor.extract_keywords("add the new authentication feature to the system")

        # Stopwords should be filtered
        assert "the" not in keywords
        assert "to" not in keywords
        assert "add" not in keywords  # 'add' is in stopwords
        assert "new" not in keywords  # 'new' is in stopwords

        # Content words should remain
        assert "authentication" in keywords
        assert "feature" in keywords
        assert "system" in keywords

    def test_respects_max_keywords(self):
        """Test that max_keywords limit is respected."""
        long_task = "authentication login user session token jwt oauth password reset email verification"

        keywords = KeywordExtractor.extract_keywords(long_task, max_keywords=3)
        assert len(keywords) == 3

    def test_deduplicates_keywords(self):
        """Test that duplicate keywords are removed."""
        keywords = KeywordExtractor.extract_keywords("login login login authentication login")

        # Should only have unique keywords
        assert keywords.count("login") == 1
        assert keywords.count("authentication") == 1

    def test_preserves_order(self):
        """Test that keyword order is preserved."""
        keywords = KeywordExtractor.extract_keywords("first second third fourth")

        assert keywords[0] == "first"
        assert keywords[1] == "second"
        assert keywords[2] == "third"
        assert keywords[3] == "fourth"

    def test_filters_short_words(self):
        """Test that very short words are filtered."""
        keywords = KeywordExtractor.extract_keywords("a to in authentication db")

        # Single and two-letter words should be filtered
        assert "authentication" in keywords
        # 'db' is only 2 chars, should be filtered
        assert "db" not in keywords

    def test_handles_underscores(self):
        """Test that words with underscores are handled."""
        keywords = KeywordExtractor.extract_keywords("user_authentication user_session")

        assert "user_authentication" in keywords
        assert "user_session" in keywords

    def test_case_insensitive(self):
        """Test that extraction is case insensitive."""
        keywords = KeywordExtractor.extract_keywords("Authentication LOGIN User")

        # All should be lowercase
        assert "authentication" in keywords
        assert "login" in keywords
        assert "user" in keywords
        assert "Authentication" not in keywords

    def test_empty_string(self):
        """Test with empty string."""
        keywords = KeywordExtractor.extract_keywords("")
        assert keywords == []

    def test_only_stopwords(self):
        """Test with only stopwords."""
        keywords = KeywordExtractor.extract_keywords("the and or but if then")
        assert keywords == []

    def test_alphanumeric_words(self):
        """Test words with numbers."""
        keywords = KeywordExtractor.extract_keywords("oauth2 http3 version1")

        assert "oauth2" in keywords
        assert "http3" in keywords
        assert "version1" in keywords


# =============================================================================
# Integration Tests
# =============================================================================

class TestContextIntegration:
    """Integration tests for context module."""

    def test_full_workflow(self):
        """Test complete workflow: extract keywords -> match files -> categorize."""
        # Extract keywords
        task = "Add new user authentication feature with JWT tokens"
        keywords = KeywordExtractor.extract_keywords(task)

        assert "authentication" in keywords
        assert "jwt" in keywords
        assert "tokens" in keywords

        # Create matches based on keywords
        matches = [
            FileMatch(path="src/auth/jwt.py", service="auth", reason="jwt", relevance_score=9.0),
            FileMatch(path="src/auth/tokens.py", service="auth", reason="tokens", relevance_score=8.0),
            FileMatch(path="tests/test_jwt.py", service="auth", reason="test", relevance_score=7.0),
        ]

        # Categorize
        categorizer = FileCategorizer()
        to_modify, to_reference = categorizer.categorize_matches(
            matches, task, max_modify=5, max_reference=10
        )

        # jwt.py and tokens.py should be in modify
        modify_paths = [m.path for m in to_modify]
        assert "src/auth/jwt.py" in modify_paths
        assert "src/auth/tokens.py" in modify_paths

        # test file should be in reference
        reference_paths = [m.path for m in to_reference]
        assert "tests/test_jwt.py" in reference_paths
