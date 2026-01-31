"""
Tests for the prediction module
================================

Tests covering prediction/models.py, prediction/patterns.py
"""

import pytest
from prediction.models import PredictedIssue, PreImplementationChecklist
from prediction.patterns import get_common_issues, detect_work_type


# =============================================================================
# PredictedIssue Tests
# =============================================================================

class TestPredictedIssue:
    """Tests for PredictedIssue dataclass."""

    def test_predicted_issue_creation(self):
        """Test basic PredictedIssue creation."""
        issue = PredictedIssue(
            category="security",
            description="SQL injection vulnerability",
            likelihood="high",
            prevention="Use parameterized queries"
        )
        assert issue.category == "security"
        assert issue.description == "SQL injection vulnerability"
        assert issue.likelihood == "high"
        assert issue.prevention == "Use parameterized queries"

    def test_predicted_issue_to_dict(self):
        """Test converting PredictedIssue to dictionary."""
        issue = PredictedIssue(
            category="integration",
            description="API mismatch",
            likelihood="medium",
            prevention="Check API docs"
        )
        result = issue.to_dict()

        assert isinstance(result, dict)
        assert result["category"] == "integration"
        assert result["description"] == "API mismatch"
        assert result["likelihood"] == "medium"
        assert result["prevention"] == "Check API docs"

    def test_all_categories(self):
        """Test all valid issue categories."""
        categories = ["integration", "pattern", "edge_case", "security", "performance"]
        for cat in categories:
            issue = PredictedIssue(
                category=cat,
                description="Test",
                likelihood="low",
                prevention="Test"
            )
            assert issue.category == cat

    def test_all_likelihoods(self):
        """Test all valid likelihood levels."""
        likelihoods = ["high", "medium", "low"]
        for likelihood in likelihoods:
            issue = PredictedIssue(
                category="security",
                description="Test",
                likelihood=likelihood,
                prevention="Test"
            )
            assert issue.likelihood == likelihood


# =============================================================================
# PreImplementationChecklist Tests
# =============================================================================

class TestPreImplementationChecklist:
    """Tests for PreImplementationChecklist dataclass."""

    def test_checklist_creation_minimal(self):
        """Test minimal checklist creation."""
        checklist = PreImplementationChecklist(
            subtask_id="1",
            subtask_description="Add login endpoint"
        )
        assert checklist.subtask_id == "1"
        assert checklist.subtask_description == "Add login endpoint"
        assert checklist.predicted_issues == []
        assert checklist.patterns_to_follow == []
        assert checklist.files_to_reference == []
        assert checklist.common_mistakes == []
        assert checklist.verification_reminders == []

    def test_checklist_creation_full(self):
        """Test full checklist creation with all fields."""
        issue = PredictedIssue(
            category="security",
            description="Password not hashed",
            likelihood="high",
            prevention="Use bcrypt"
        )
        checklist = PreImplementationChecklist(
            subtask_id="auth-1",
            subtask_description="Implement user login",
            predicted_issues=[issue],
            patterns_to_follow=["Use JWT tokens", "Hash passwords"],
            files_to_reference=["auth/utils.py", "auth/tokens.py"],
            common_mistakes=["Storing plaintext passwords"],
            verification_reminders=["Check token expiration"]
        )

        assert checklist.subtask_id == "auth-1"
        assert len(checklist.predicted_issues) == 1
        assert len(checklist.patterns_to_follow) == 2
        assert len(checklist.files_to_reference) == 2
        assert len(checklist.common_mistakes) == 1
        assert len(checklist.verification_reminders) == 1


# =============================================================================
# get_common_issues Tests
# =============================================================================

class TestGetCommonIssues:
    """Tests for get_common_issues function."""

    def test_returns_dict(self):
        """Test that function returns a dictionary."""
        result = get_common_issues()
        assert isinstance(result, dict)

    def test_all_work_types_present(self):
        """Test that all expected work types are present."""
        result = get_common_issues()
        expected_types = [
            "api_endpoint",
            "database_model",
            "frontend_component",
            "celery_task",
            "authentication",
            "database_query",
            "file_upload"
        ]
        for work_type in expected_types:
            assert work_type in result, f"Missing work type: {work_type}"

    def test_issues_are_predicted_issue_objects(self):
        """Test that all issues are PredictedIssue objects."""
        result = get_common_issues()
        for work_type, issues in result.items():
            for issue in issues:
                assert isinstance(issue, PredictedIssue), f"Invalid issue in {work_type}"

    def test_api_endpoint_issues(self):
        """Test API endpoint issues."""
        result = get_common_issues()
        api_issues = result["api_endpoint"]

        assert len(api_issues) > 0
        categories = [issue.category for issue in api_issues]
        assert "integration" in categories
        assert "security" in categories

    def test_authentication_issues(self):
        """Test authentication issues."""
        result = get_common_issues()
        auth_issues = result["authentication"]

        assert len(auth_issues) > 0
        # All auth issues should be security category
        for issue in auth_issues:
            assert issue.category == "security"
            assert issue.likelihood in ["high", "medium", "low"]

    def test_database_query_issues(self):
        """Test database query issues include SQL injection warning."""
        result = get_common_issues()
        db_issues = result["database_query"]

        descriptions = [issue.description.lower() for issue in db_issues]
        has_sql_injection = any("sql injection" in desc for desc in descriptions)
        assert has_sql_injection, "Should warn about SQL injection"

    def test_file_upload_issues(self):
        """Test file upload issues include security warnings."""
        result = get_common_issues()
        upload_issues = result["file_upload"]

        assert len(upload_issues) > 0
        security_issues = [i for i in upload_issues if i.category == "security"]
        assert len(security_issues) >= 2  # File type and size validation


# =============================================================================
# detect_work_type Tests
# =============================================================================

class TestDetectWorkType:
    """Tests for detect_work_type function."""

    def test_api_endpoint_by_description(self):
        """Test API endpoint detection by description keywords."""
        subtask = {"description": "Create new API endpoint for user login"}
        result = detect_work_type(subtask)
        assert "api_endpoint" in result

    def test_api_endpoint_by_files(self):
        """Test API endpoint detection by file paths."""
        subtask = {
            "description": "Add new feature",
            "files_to_modify": ["src/routes/users.py"]
        }
        result = detect_work_type(subtask)
        assert "api_endpoint" in result

    def test_database_model_by_description(self):
        """Test database model detection by description."""
        subtask = {"description": "Create User model with fields"}
        result = detect_work_type(subtask)
        assert "database_model" in result

    def test_database_model_by_files(self):
        """Test database model detection by file paths."""
        subtask = {
            "description": "Add new fields",
            "files_to_modify": ["src/models/user.py"]
        }
        result = detect_work_type(subtask)
        assert "database_model" in result

    def test_frontend_component_by_service(self):
        """Test frontend component detection by service."""
        subtask = {"description": "Add button", "service": "frontend"}
        result = detect_work_type(subtask)
        assert "frontend_component" in result

    def test_frontend_component_by_files(self):
        """Test frontend component detection by file extensions."""
        subtask = {
            "description": "Create component",
            "files_to_create": ["src/components/Button.tsx"]
        }
        result = detect_work_type(subtask)
        assert "frontend_component" in result

    def test_celery_task_detection(self):
        """Test Celery task detection."""
        subtask = {"description": "Create celery task for email sending"}
        result = detect_work_type(subtask)
        assert "celery_task" in result

    def test_authentication_detection(self):
        """Test authentication work detection."""
        subtask = {"description": "Implement user login with password validation"}
        result = detect_work_type(subtask)
        assert "authentication" in result

    def test_database_query_detection(self):
        """Test database query detection."""
        subtask = {"description": "Add search functionality to filter users"}
        result = detect_work_type(subtask)
        assert "database_query" in result

    def test_file_upload_detection(self):
        """Test file upload detection."""
        subtask = {"description": "Add image upload for profile pictures"}
        result = detect_work_type(subtask)
        assert "file_upload" in result

    def test_multiple_work_types(self):
        """Test detecting multiple work types."""
        subtask = {
            "description": "Create API endpoint to upload files with authentication",
            "files_to_modify": ["src/routes/upload.py"]
        }
        result = detect_work_type(subtask)

        assert "api_endpoint" in result
        assert "file_upload" in result
        assert "authentication" in result

    def test_empty_subtask(self):
        """Test with empty subtask."""
        subtask = {}
        result = detect_work_type(subtask)
        assert result == []

    def test_no_matching_types(self):
        """Test subtask with no matching work types."""
        subtask = {"description": "Update documentation"}
        result = detect_work_type(subtask)
        # Should return empty or just the types it can detect
        # In this case, none of the keywords match
        assert isinstance(result, list)

    def test_case_insensitive(self):
        """Test that detection is case insensitive."""
        subtask = {"description": "CREATE NEW API ENDPOINT FOR AUTH"}
        result = detect_work_type(subtask)
        assert "api_endpoint" in result
        assert "authentication" in result

    def test_vue_file_detection(self):
        """Test Vue.js file detection."""
        subtask = {
            "description": "Add component",
            "files_to_create": ["src/components/Modal.vue"]
        }
        result = detect_work_type(subtask)
        assert "frontend_component" in result

    def test_jsx_file_detection(self):
        """Test JSX file detection."""
        subtask = {
            "description": "Add component",
            "files_to_create": ["src/components/Button.jsx"]
        }
        result = detect_work_type(subtask)
        assert "frontend_component" in result

    def test_svelte_file_detection(self):
        """Test Svelte file detection."""
        subtask = {
            "description": "Add component",
            "files_to_create": ["src/components/Counter.svelte"]
        }
        result = detect_work_type(subtask)
        assert "frontend_component" in result


# =============================================================================
# Integration Tests
# =============================================================================

class TestPredictionIntegration:
    """Integration tests for prediction module."""

    def test_get_issues_for_detected_work_types(self):
        """Test getting issues for detected work types."""
        subtask = {
            "description": "Create API endpoint for user authentication",
            "files_to_modify": ["src/routes/auth.py"]
        }

        work_types = detect_work_type(subtask)
        common_issues = get_common_issues()

        # Collect all issues for detected work types
        all_issues = []
        for wt in work_types:
            if wt in common_issues:
                all_issues.extend(common_issues[wt])

        assert len(all_issues) > 0
        # Should have both API and auth issues
        categories = [issue.category for issue in all_issues]
        assert "security" in categories

    def test_full_checklist_workflow(self):
        """Test creating a full checklist from subtask."""
        subtask = {
            "description": "Add login endpoint with password validation",
            "files_to_modify": ["src/routes/auth.py"],
            "files_to_create": []
        }

        # Detect work types
        work_types = detect_work_type(subtask)

        # Get issues for those work types
        common_issues = get_common_issues()
        issues = []
        for wt in work_types:
            if wt in common_issues:
                issues.extend(common_issues[wt])

        # Create checklist
        checklist = PreImplementationChecklist(
            subtask_id="auth-1",
            subtask_description=subtask["description"],
            predicted_issues=issues,
            patterns_to_follow=["Use JWT", "Hash passwords"],
            files_to_reference=subtask["files_to_modify"]
        )

        assert checklist.subtask_id == "auth-1"
        assert len(checklist.predicted_issues) > 0
        assert "src/routes/auth.py" in checklist.files_to_reference
