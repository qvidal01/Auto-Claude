"""
Tests for the context models module
===================================

Tests covering context/models.py - FileMatch and TaskContext dataclasses
"""

import pytest
from dataclasses import asdict

from context.models import FileMatch, TaskContext


# =============================================================================
# FileMatch Tests
# =============================================================================

class TestFileMatch:
    """Tests for FileMatch dataclass."""

    def test_basic_creation(self):
        """Test basic FileMatch creation."""
        match = FileMatch(
            path="src/app.py",
            service="backend",
            reason="Contains: login, auth"
        )
        assert match.path == "src/app.py"
        assert match.service == "backend"
        assert match.reason == "Contains: login, auth"

    def test_default_values(self):
        """Test default values for optional fields."""
        match = FileMatch(
            path="test.py",
            service="core",
            reason="keyword match"
        )
        assert match.relevance_score == 0.0
        assert match.matching_lines == []

    def test_with_relevance_score(self):
        """Test FileMatch with relevance score."""
        match = FileMatch(
            path="src/auth.py",
            service="auth-service",
            reason="Contains auth logic",
            relevance_score=15.5
        )
        assert match.relevance_score == 15.5

    def test_with_matching_lines(self):
        """Test FileMatch with matching lines."""
        match = FileMatch(
            path="src/login.py",
            service="auth",
            reason="Contains login",
            matching_lines=[(10, "def login(user):"), (25, "if authenticate(user):")]
        )
        assert len(match.matching_lines) == 2
        assert match.matching_lines[0] == (10, "def login(user):")
        assert match.matching_lines[1][0] == 25

    def test_asdict_conversion(self):
        """Test conversion to dict."""
        match = FileMatch(
            path="test.py",
            service="api",
            reason="keyword",
            relevance_score=5.0,
            matching_lines=[(1, "line")]
        )
        d = asdict(match)
        assert d["path"] == "test.py"
        assert d["service"] == "api"
        assert d["reason"] == "keyword"
        assert d["relevance_score"] == 5.0
        assert d["matching_lines"] == [(1, "line")]

    def test_equality(self):
        """Test FileMatch equality."""
        match1 = FileMatch(path="a.py", service="s", reason="r")
        match2 = FileMatch(path="a.py", service="s", reason="r")
        assert match1 == match2

    def test_inequality(self):
        """Test FileMatch inequality."""
        match1 = FileMatch(path="a.py", service="s", reason="r")
        match2 = FileMatch(path="b.py", service="s", reason="r")
        assert match1 != match2


# =============================================================================
# TaskContext Tests
# =============================================================================

class TestTaskContext:
    """Tests for TaskContext dataclass."""

    def test_basic_creation(self):
        """Test basic TaskContext creation."""
        ctx = TaskContext(
            task_description="Add login feature",
            scoped_services=["auth", "api"],
            files_to_modify=[{"path": "auth.py"}],
            files_to_reference=[{"path": "utils.py"}],
            patterns_discovered={"error_handling": "try/except"},
            service_contexts={"auth": {"type": "service"}}
        )
        assert ctx.task_description == "Add login feature"
        assert ctx.scoped_services == ["auth", "api"]
        assert len(ctx.files_to_modify) == 1
        assert len(ctx.files_to_reference) == 1

    def test_default_graph_hints(self):
        """Test default value for graph_hints."""
        ctx = TaskContext(
            task_description="test",
            scoped_services=[],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={}
        )
        assert ctx.graph_hints == []

    def test_with_graph_hints(self):
        """Test TaskContext with graph hints."""
        hints = [
            {"type": "similar_task", "content": "Previous auth work"},
            {"type": "pattern", "content": "Use JWT tokens"}
        ]
        ctx = TaskContext(
            task_description="Auth feature",
            scoped_services=["auth"],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={},
            graph_hints=hints
        )
        assert len(ctx.graph_hints) == 2
        assert ctx.graph_hints[0]["type"] == "similar_task"

    def test_multiple_services(self):
        """Test TaskContext with multiple services."""
        ctx = TaskContext(
            task_description="API integration",
            scoped_services=["frontend", "backend", "api-gateway"],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={
                "frontend": {"framework": "react"},
                "backend": {"language": "python"},
                "api-gateway": {"type": "gateway"}
            }
        )
        assert len(ctx.scoped_services) == 3
        assert "frontend" in ctx.service_contexts
        assert ctx.service_contexts["backend"]["language"] == "python"

    def test_patterns_discovered(self):
        """Test patterns discovered field."""
        ctx = TaskContext(
            task_description="test",
            scoped_services=[],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={
                "error_handling": "Custom exception classes",
                "logging": "structlog with JSON",
                "testing": "pytest with fixtures"
            },
            service_contexts={}
        )
        assert len(ctx.patterns_discovered) == 3
        assert "error_handling" in ctx.patterns_discovered

    def test_asdict_conversion(self):
        """Test conversion to dict."""
        ctx = TaskContext(
            task_description="test task",
            scoped_services=["svc"],
            files_to_modify=[{"path": "a.py"}],
            files_to_reference=[{"path": "b.py"}],
            patterns_discovered={"p": "v"},
            service_contexts={"svc": {}},
            graph_hints=[{"hint": "value"}]
        )
        d = asdict(ctx)
        assert d["task_description"] == "test task"
        assert d["scoped_services"] == ["svc"]
        assert d["graph_hints"] == [{"hint": "value"}]

    def test_empty_context(self):
        """Test TaskContext with empty collections."""
        ctx = TaskContext(
            task_description="Empty task",
            scoped_services=[],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={}
        )
        assert ctx.task_description == "Empty task"
        assert len(ctx.scoped_services) == 0
        assert len(ctx.files_to_modify) == 0


# =============================================================================
# Integration Tests
# =============================================================================

class TestContextModelsIntegration:
    """Integration tests for context models."""

    def test_file_match_in_task_context(self):
        """Test using FileMatch objects with TaskContext."""
        match1 = FileMatch(
            path="src/auth.py",
            service="auth",
            reason="Contains login",
            relevance_score=10.0
        )
        match2 = FileMatch(
            path="src/utils.py",
            service="core",
            reason="Helper functions",
            relevance_score=5.0
        )

        # Convert to dicts as TaskContext expects
        ctx = TaskContext(
            task_description="Auth feature",
            scoped_services=["auth", "core"],
            files_to_modify=[asdict(match1)],
            files_to_reference=[asdict(match2)],
            patterns_discovered={},
            service_contexts={}
        )

        assert ctx.files_to_modify[0]["path"] == "src/auth.py"
        assert ctx.files_to_reference[0]["relevance_score"] == 5.0

    def test_sorting_file_matches(self):
        """Test sorting FileMatch objects by relevance."""
        matches = [
            FileMatch(path="a.py", service="s", reason="r", relevance_score=5),
            FileMatch(path="b.py", service="s", reason="r", relevance_score=15),
            FileMatch(path="c.py", service="s", reason="r", relevance_score=10),
        ]
        sorted_matches = sorted(matches, key=lambda m: m.relevance_score, reverse=True)

        assert sorted_matches[0].path == "b.py"
        assert sorted_matches[1].path == "c.py"
        assert sorted_matches[2].path == "a.py"

    def test_filter_high_relevance(self):
        """Test filtering matches by relevance threshold."""
        matches = [
            FileMatch(path="high.py", service="s", reason="r", relevance_score=20),
            FileMatch(path="medium.py", service="s", reason="r", relevance_score=10),
            FileMatch(path="low.py", service="s", reason="r", relevance_score=2),
        ]

        threshold = 5.0
        high_relevance = [m for m in matches if m.relevance_score >= threshold]

        assert len(high_relevance) == 2
        assert all(m.relevance_score >= threshold for m in high_relevance)
