"""
Tests for the QA report module
===============================

Tests covering qa/report.py - iteration tracking, recurring issues, escalation
"""

import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from qa.report import (
    get_iteration_history,
    record_iteration,
    has_recurring_issues,
    get_recurring_issue_summary,
    check_test_discovery,
    is_no_test_project,
    create_manual_test_plan,
    _normalize_issue_key,
    _issue_similarity,
    RECURRING_ISSUE_THRESHOLD,
    ISSUE_SIMILARITY_THRESHOLD,
)


# =============================================================================
# _normalize_issue_key Tests
# =============================================================================

class TestNormalizeIssueKey:
    """Tests for _normalize_issue_key function."""

    def test_basic_normalization(self):
        """Test basic issue key normalization."""
        issue = {"title": "Test Issue", "file": "src/app.py", "line": 10}
        result = _normalize_issue_key(issue)
        assert "test issue" in result
        assert "src/app.py" in result
        assert "10" in result

    def test_removes_common_prefixes(self):
        """Test that common prefixes are removed."""
        issue = {"title": "Error: Something went wrong", "file": "", "line": ""}
        result = _normalize_issue_key(issue)
        assert not result.startswith("error:")

    def test_handles_missing_fields(self):
        """Test handling of missing fields."""
        issue = {}
        result = _normalize_issue_key(issue)
        assert result == "||"

    def test_lowercase_conversion(self):
        """Test that title is lowercased."""
        issue = {"title": "UPPERCASE ISSUE", "file": "Test.py"}
        result = _normalize_issue_key(issue)
        assert "uppercase issue" in result


# =============================================================================
# _issue_similarity Tests
# =============================================================================

class TestIssueSimilarity:
    """Tests for _issue_similarity function."""

    def test_identical_issues(self):
        """Test similarity of identical issues."""
        issue = {"title": "Test bug", "file": "app.py", "line": 10}
        similarity = _issue_similarity(issue, issue)
        assert similarity == 1.0

    def test_different_issues(self):
        """Test similarity of completely different issues."""
        issue1 = {"title": "First issue", "file": "a.py", "line": 1}
        issue2 = {"title": "Completely unrelated", "file": "z.py", "line": 999}
        similarity = _issue_similarity(issue1, issue2)
        assert similarity < 0.5

    def test_similar_issues(self):
        """Test similarity of similar issues."""
        issue1 = {"title": "Error in authentication", "file": "auth.py", "line": 50}
        issue2 = {"title": "Error in authentication module", "file": "auth.py", "line": 50}
        similarity = _issue_similarity(issue1, issue2)
        assert similarity > ISSUE_SIMILARITY_THRESHOLD


# =============================================================================
# get_iteration_history Tests
# =============================================================================

class TestGetIterationHistory:
    """Tests for get_iteration_history function."""

    @pytest.fixture
    def temp_spec_dir(self):
        """Create a temporary spec directory."""
        with tempfile.TemporaryDirectory() as td:
            spec_dir = Path(td)
            yield spec_dir

    def test_empty_history(self, temp_spec_dir):
        """Test with no implementation plan."""
        result = get_iteration_history(temp_spec_dir)
        assert result == []

    def test_with_history(self, temp_spec_dir):
        """Test with existing history."""
        plan = {
            "qa_iteration_history": [
                {"iteration": 1, "status": "rejected", "issues": []},
                {"iteration": 2, "status": "approved", "issues": []},
            ]
        }
        (temp_spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

        result = get_iteration_history(temp_spec_dir)
        assert len(result) == 2
        assert result[0]["iteration"] == 1
        assert result[1]["status"] == "approved"


# =============================================================================
# record_iteration Tests
# =============================================================================

class TestRecordIteration:
    """Tests for record_iteration function."""

    @pytest.fixture
    def temp_spec_dir(self):
        """Create a temporary spec directory."""
        with tempfile.TemporaryDirectory() as td:
            spec_dir = Path(td)
            (spec_dir / "implementation_plan.json").write_text("{}")
            yield spec_dir

    def test_record_first_iteration(self, temp_spec_dir):
        """Test recording first iteration."""
        issues = [{"title": "Bug 1", "type": "error"}]
        result = record_iteration(temp_spec_dir, 1, "rejected", issues)
        assert result is True

        history = get_iteration_history(temp_spec_dir)
        assert len(history) == 1
        assert history[0]["iteration"] == 1
        assert history[0]["status"] == "rejected"

    def test_record_with_duration(self, temp_spec_dir):
        """Test recording iteration with duration."""
        result = record_iteration(temp_spec_dir, 1, "approved", [], duration_seconds=123.456)
        assert result is True

        history = get_iteration_history(temp_spec_dir)
        assert history[0]["duration_seconds"] == 123.46

    def test_record_updates_stats(self, temp_spec_dir):
        """Test that recording updates qa_stats."""
        record_iteration(temp_spec_dir, 1, "rejected", [{"type": "error"}])

        with open(temp_spec_dir / "implementation_plan.json") as f:
            plan = json.load(f)

        assert "qa_stats" in plan
        assert plan["qa_stats"]["total_iterations"] == 1
        assert plan["qa_stats"]["last_status"] == "rejected"


# =============================================================================
# has_recurring_issues Tests
# =============================================================================

class TestHasRecurringIssues:
    """Tests for has_recurring_issues function."""

    def test_no_history(self):
        """Test with no history."""
        current = [{"title": "New issue"}]
        has_recurring, recurring = has_recurring_issues(current, [])
        assert has_recurring is False
        assert recurring == []

    def test_no_recurring(self):
        """Test with issues that don't recur."""
        current = [{"title": "New issue", "file": "new.py"}]
        history = [
            {"issues": [{"title": "Old issue", "file": "old.py"}]}
        ]
        has_recurring, recurring = has_recurring_issues(current, history)
        assert has_recurring is False

    def test_recurring_detected(self):
        """Test detection of recurring issues."""
        recurring_issue = {"title": "Same bug", "file": "app.py", "line": 10}
        current = [recurring_issue]

        # Create history with same issue appearing multiple times
        history = [
            {"issues": [recurring_issue]},
            {"issues": [recurring_issue]},
            {"issues": [recurring_issue]},
        ]

        has_recurring, recurring = has_recurring_issues(current, history)
        assert has_recurring is True
        assert len(recurring) == 1
        assert recurring[0]["occurrence_count"] >= RECURRING_ISSUE_THRESHOLD


# =============================================================================
# get_recurring_issue_summary Tests
# =============================================================================

class TestGetRecurringIssueSummary:
    """Tests for get_recurring_issue_summary function."""

    def test_empty_history(self):
        """Test with empty history."""
        result = get_recurring_issue_summary([])
        assert result["total_issues"] == 0
        assert result["unique_issues"] == 0
        assert result["most_common"] == []

    def test_summary_stats(self):
        """Test summary statistics."""
        history = [
            {"status": "rejected", "issues": [{"title": "Bug 1"}]},
            {"status": "rejected", "issues": [{"title": "Bug 2"}]},
            {"status": "approved", "issues": []},
        ]
        result = get_recurring_issue_summary(history)

        assert result["total_issues"] == 2
        assert result["iterations_approved"] == 1
        assert result["iterations_rejected"] == 2
        assert result["fix_success_rate"] == 1/3

    def test_most_common_issues(self):
        """Test most common issues detection."""
        same_issue = {"title": "Common bug", "file": "app.py"}
        history = [
            {"status": "rejected", "issues": [same_issue, {"title": "Other"}]},
            {"status": "rejected", "issues": [same_issue]},
            {"status": "rejected", "issues": [same_issue]},
        ]
        result = get_recurring_issue_summary(history)

        assert len(result["most_common"]) > 0
        most_common = result["most_common"][0]
        assert most_common["occurrences"] >= 3


# =============================================================================
# check_test_discovery Tests
# =============================================================================

class TestCheckTestDiscovery:
    """Tests for check_test_discovery function."""

    @pytest.fixture
    def temp_spec_dir(self):
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_no_discovery_file(self, temp_spec_dir):
        """Test when discovery file doesn't exist."""
        result = check_test_discovery(temp_spec_dir)
        assert result is None

    def test_with_discovery_file(self, temp_spec_dir):
        """Test with existing discovery file."""
        discovery = {"frameworks": ["pytest"], "test_dirs": ["tests"]}
        (temp_spec_dir / "test_discovery.json").write_text(json.dumps(discovery))

        result = check_test_discovery(temp_spec_dir)
        assert result is not None
        assert result["frameworks"] == ["pytest"]

    def test_invalid_json(self, temp_spec_dir):
        """Test with invalid JSON file."""
        (temp_spec_dir / "test_discovery.json").write_text("not valid json")
        result = check_test_discovery(temp_spec_dir)
        assert result is None


# =============================================================================
# is_no_test_project Tests
# =============================================================================

class TestIsNoTestProject:
    """Tests for is_no_test_project function."""

    @pytest.fixture
    def temp_dirs(self):
        with tempfile.TemporaryDirectory() as spec_td:
            with tempfile.TemporaryDirectory() as project_td:
                yield Path(spec_td), Path(project_td)

    def test_with_pytest_config(self, temp_dirs):
        """Test with pytest.ini present."""
        spec_dir, project_dir = temp_dirs
        (project_dir / "pytest.ini").touch()

        result = is_no_test_project(spec_dir, project_dir)
        assert result is False

    def test_with_tests_directory(self, temp_dirs):
        """Test with tests directory containing test files."""
        spec_dir, project_dir = temp_dirs
        tests_dir = project_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_example.py").touch()

        result = is_no_test_project(spec_dir, project_dir)
        assert result is False

    def test_no_test_infrastructure(self, temp_dirs):
        """Test with no test infrastructure."""
        spec_dir, project_dir = temp_dirs
        # Empty project
        result = is_no_test_project(spec_dir, project_dir)
        assert result is True

    def test_with_cached_discovery(self, temp_dirs):
        """Test using cached discovery file."""
        spec_dir, project_dir = temp_dirs
        discovery = {"frameworks": ["jest"]}
        (spec_dir / "test_discovery.json").write_text(json.dumps(discovery))

        result = is_no_test_project(spec_dir, project_dir)
        assert result is False

    def test_with_empty_cached_discovery(self, temp_dirs):
        """Test with cached discovery showing no frameworks."""
        spec_dir, project_dir = temp_dirs
        discovery = {"frameworks": []}
        (spec_dir / "test_discovery.json").write_text(json.dumps(discovery))

        result = is_no_test_project(spec_dir, project_dir)
        assert result is True


# =============================================================================
# create_manual_test_plan Tests
# =============================================================================

class TestCreateManualTestPlan:
    """Tests for create_manual_test_plan function."""

    @pytest.fixture
    def temp_spec_dir(self):
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_creates_file(self, temp_spec_dir):
        """Test that manual test plan file is created."""
        result_path = create_manual_test_plan(temp_spec_dir, "test-spec")

        assert result_path.exists()
        assert result_path.name == "MANUAL_TEST_PLAN.md"

    def test_file_content(self, temp_spec_dir):
        """Test manual test plan content."""
        result_path = create_manual_test_plan(temp_spec_dir, "my-feature")

        content = result_path.read_text()
        assert "my-feature" in content
        assert "Manual Test Plan" in content
        assert "Pre-Test Setup" in content
        assert "Functional Tests" in content

    def test_extracts_acceptance_criteria(self, temp_spec_dir):
        """Test extraction of acceptance criteria from spec."""
        spec_content = """# Test Spec

## Overview
This is a test spec.

## Acceptance Criteria
- First criterion
- Second criterion
- Third criterion

## Other Section
More content.
"""
        (temp_spec_dir / "spec.md").write_text(spec_content)

        result_path = create_manual_test_plan(temp_spec_dir, "test-spec")
        content = result_path.read_text()

        assert "First criterion" in content
        assert "Second criterion" in content
        assert "Third criterion" in content


# =============================================================================
# Integration Tests
# =============================================================================

class TestQAReportIntegration:
    """Integration tests for QA report module."""

    @pytest.fixture
    def temp_spec_dir(self):
        with tempfile.TemporaryDirectory() as td:
            spec_dir = Path(td)
            (spec_dir / "implementation_plan.json").write_text("{}")
            yield spec_dir

    def test_full_qa_iteration_workflow(self, temp_spec_dir):
        """Test complete QA iteration recording workflow."""
        # First iteration - rejected
        issues1 = [
            {"title": "Missing validation", "type": "error", "file": "forms.py"},
        ]
        record_iteration(temp_spec_dir, 1, "rejected", issues1, duration_seconds=120)

        # Second iteration - same issue recurs
        record_iteration(temp_spec_dir, 2, "rejected", issues1, duration_seconds=90)

        # Third iteration - approved
        record_iteration(temp_spec_dir, 3, "approved", [], duration_seconds=60)

        # Check history
        history = get_iteration_history(temp_spec_dir)
        assert len(history) == 3
        assert history[2]["status"] == "approved"

        # Check summary
        summary = get_recurring_issue_summary(history)
        assert summary["total_issues"] == 2
        assert summary["iterations_approved"] == 1
        assert summary["iterations_rejected"] == 2

    def test_recurring_issue_detection_workflow(self, temp_spec_dir):
        """Test recurring issue detection across iterations."""
        recurring_issue = {"title": "Authentication bug", "file": "auth.py", "line": 100}

        # Record the same issue multiple times
        for i in range(RECURRING_ISSUE_THRESHOLD):
            record_iteration(temp_spec_dir, i + 1, "rejected", [recurring_issue])

        # New iteration with same issue
        current_issues = [recurring_issue]
        history = get_iteration_history(temp_spec_dir)

        has_recurring, recurring = has_recurring_issues(current_issues, history)

        assert has_recurring is True
        assert len(recurring) == 1
        assert recurring[0]["occurrence_count"] >= RECURRING_ISSUE_THRESHOLD
