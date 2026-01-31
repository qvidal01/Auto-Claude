"""
Tests for the services recovery module
=======================================

Tests covering services/recovery.py - Smart rollback and recovery system
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from services.recovery import (
    FailureType,
    RecoveryAction,
    RecoveryManager,
    check_and_recover,
    get_recovery_context,
)


# =============================================================================
# FailureType Tests
# =============================================================================

class TestFailureType:
    """Tests for FailureType enum."""

    def test_failure_types_exist(self):
        """Test that all failure types exist."""
        assert FailureType.BROKEN_BUILD.value == "broken_build"
        assert FailureType.VERIFICATION_FAILED.value == "verification_failed"
        assert FailureType.CIRCULAR_FIX.value == "circular_fix"
        assert FailureType.CONTEXT_EXHAUSTED.value == "context_exhausted"
        assert FailureType.UNKNOWN.value == "unknown"


# =============================================================================
# RecoveryAction Tests
# =============================================================================

class TestRecoveryAction:
    """Tests for RecoveryAction dataclass."""

    def test_creation(self):
        """Test creating a RecoveryAction."""
        action = RecoveryAction(
            action="rollback",
            target="abc123",
            reason="Build broken"
        )
        assert action.action == "rollback"
        assert action.target == "abc123"
        assert action.reason == "Build broken"

    def test_all_action_types(self):
        """Test all action types can be created."""
        for action_type in ["rollback", "retry", "skip", "escalate", "continue"]:
            action = RecoveryAction(action=action_type, target="test", reason="test")
            assert action.action == action_type


# =============================================================================
# RecoveryManager Tests
# =============================================================================

class TestRecoveryManager:
    """Tests for RecoveryManager class."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories."""
        with tempfile.TemporaryDirectory() as spec_td:
            with tempfile.TemporaryDirectory() as proj_td:
                yield Path(spec_td), Path(proj_td)

    @pytest.fixture
    def manager(self, temp_dirs):
        """Create a RecoveryManager instance."""
        spec_dir, project_dir = temp_dirs
        return RecoveryManager(spec_dir, project_dir)

    def test_initialization(self, manager, temp_dirs):
        """Test manager initializes files."""
        spec_dir, _ = temp_dirs
        memory_dir = spec_dir / "memory"

        assert memory_dir.exists()
        assert (memory_dir / "attempt_history.json").exists()
        assert (memory_dir / "build_commits.json").exists()

    def test_attempt_history_initialized(self, manager, temp_dirs):
        """Test attempt history is properly initialized."""
        spec_dir, _ = temp_dirs
        history_file = spec_dir / "memory" / "attempt_history.json"

        with open(history_file) as f:
            data = json.load(f)

        assert "subtasks" in data
        assert "stuck_subtasks" in data
        assert "metadata" in data

    def test_build_commits_initialized(self, manager, temp_dirs):
        """Test build commits is properly initialized."""
        spec_dir, _ = temp_dirs
        commits_file = spec_dir / "memory" / "build_commits.json"

        with open(commits_file) as f:
            data = json.load(f)

        assert "commits" in data
        assert "last_good_commit" in data
        assert data["last_good_commit"] is None


class TestRecoveryManagerClassifyFailure:
    """Tests for classify_failure method."""

    @pytest.fixture
    def manager(self):
        """Create a RecoveryManager instance."""
        with tempfile.TemporaryDirectory() as spec_td:
            with tempfile.TemporaryDirectory() as proj_td:
                yield RecoveryManager(Path(spec_td), Path(proj_td))

    def test_classify_syntax_error(self, manager):
        """Test classifying syntax errors."""
        # Implementation looks for "syntax error" with space
        result = manager.classify_failure("Syntax error at line 5: invalid", "1.1")
        assert result == FailureType.BROKEN_BUILD

    def test_classify_import_error(self, manager):
        """Test classifying import errors."""
        # Implementation looks for "import error" with space
        result = manager.classify_failure("Import error: No module named 'foo'", "1.1")
        assert result == FailureType.BROKEN_BUILD

    def test_classify_module_not_found(self, manager):
        """Test classifying module not found."""
        result = manager.classify_failure("Module not found: react", "1.1")
        assert result == FailureType.BROKEN_BUILD

    def test_classify_verification_failed(self, manager):
        """Test classifying verification failures."""
        result = manager.classify_failure("Verification failed: output mismatch", "1.1")
        assert result == FailureType.VERIFICATION_FAILED

    def test_classify_test_failed(self, manager):
        """Test classifying test failures."""
        result = manager.classify_failure("Test failed: expected 5 but got 3", "1.1")
        assert result == FailureType.VERIFICATION_FAILED

    def test_classify_context_exhausted(self, manager):
        """Test classifying context exhaustion."""
        result = manager.classify_failure("Context token limit exceeded", "1.1")
        assert result == FailureType.CONTEXT_EXHAUSTED

    def test_classify_unknown(self, manager):
        """Test classifying unknown errors."""
        result = manager.classify_failure("Something went wrong", "1.1")
        assert result == FailureType.UNKNOWN


class TestRecoveryManagerAttemptTracking:
    """Tests for attempt tracking methods."""

    @pytest.fixture
    def manager(self):
        """Create a RecoveryManager instance."""
        with tempfile.TemporaryDirectory() as spec_td:
            with tempfile.TemporaryDirectory() as proj_td:
                yield RecoveryManager(Path(spec_td), Path(proj_td))

    def test_get_attempt_count_no_history(self, manager):
        """Test getting count with no history."""
        count = manager.get_attempt_count("1.1")
        assert count == 0

    def test_record_attempt(self, manager):
        """Test recording an attempt."""
        manager.record_attempt(
            subtask_id="1.1",
            session=1,
            success=False,
            approach="Try using async/await",
            error="Test failed"
        )

        count = manager.get_attempt_count("1.1")
        assert count == 1

    def test_record_multiple_attempts(self, manager):
        """Test recording multiple attempts."""
        for i in range(3):
            manager.record_attempt(
                subtask_id="1.1",
                session=i,
                success=False,
                approach=f"Attempt {i}",
            )

        count = manager.get_attempt_count("1.1")
        assert count == 3

    def test_record_successful_attempt(self, manager):
        """Test recording a successful attempt."""
        manager.record_attempt(
            subtask_id="1.1",
            session=1,
            success=True,
            approach="Final solution",
        )

        history = manager.get_subtask_history("1.1")
        assert history["status"] == "completed"


class TestRecoveryManagerCircularFix:
    """Tests for circular fix detection."""

    @pytest.fixture
    def manager(self):
        """Create a RecoveryManager instance."""
        with tempfile.TemporaryDirectory() as spec_td:
            with tempfile.TemporaryDirectory() as proj_td:
                yield RecoveryManager(Path(spec_td), Path(proj_td))

    def test_no_circular_on_first_attempt(self, manager):
        """Test no circular fix on first attempt."""
        result = manager.is_circular_fix("1.1", "Using async patterns")
        assert result is False

    def test_no_circular_with_different_approaches(self, manager):
        """Test no circular fix with different approaches."""
        manager.record_attempt("1.1", 1, False, "Using async patterns")
        manager.record_attempt("1.1", 2, False, "Using callbacks instead")

        result = manager.is_circular_fix("1.1", "Synchronous approach")
        assert result is False

    def test_detects_circular_fix(self, manager):
        """Test detecting circular fix."""
        # Record similar approaches
        manager.record_attempt("1.1", 1, False, "Fix authentication with JWT tokens")
        manager.record_attempt("1.1", 2, False, "Update authentication using JWT")
        manager.record_attempt("1.1", 3, False, "Implement JWT authentication")

        # Similar approach
        result = manager.is_circular_fix("1.1", "JWT authentication implementation")
        assert result is True


class TestRecoveryManagerDetermineAction:
    """Tests for determine_recovery_action method."""

    @pytest.fixture
    def manager(self):
        """Create a RecoveryManager instance."""
        with tempfile.TemporaryDirectory() as spec_td:
            with tempfile.TemporaryDirectory() as proj_td:
                yield RecoveryManager(Path(spec_td), Path(proj_td))

    def test_broken_build_with_good_commit(self, manager):
        """Test broken build recovery with good commit."""
        manager.record_good_commit("abc123", "1.0")

        action = manager.determine_recovery_action(FailureType.BROKEN_BUILD, "1.1")

        assert action.action == "rollback"
        assert action.target == "abc123"

    def test_broken_build_no_good_commit(self, manager):
        """Test broken build with no good commit."""
        action = manager.determine_recovery_action(FailureType.BROKEN_BUILD, "1.1")

        assert action.action == "escalate"

    def test_verification_failed_retry(self, manager):
        """Test verification failed triggers retry."""
        action = manager.determine_recovery_action(FailureType.VERIFICATION_FAILED, "1.1")

        assert action.action == "retry"
        assert "attempt 1/3" in action.reason

    def test_verification_failed_skip_after_attempts(self, manager):
        """Test verification failed skips after 3 attempts."""
        for i in range(3):
            manager.record_attempt("1.1", i, False, f"Attempt {i}")

        action = manager.determine_recovery_action(FailureType.VERIFICATION_FAILED, "1.1")

        assert action.action == "skip"

    def test_circular_fix(self, manager):
        """Test circular fix detection."""
        action = manager.determine_recovery_action(FailureType.CIRCULAR_FIX, "1.1")

        assert action.action == "skip"
        assert "Circular fix" in action.reason

    def test_context_exhausted(self, manager):
        """Test context exhausted handling."""
        action = manager.determine_recovery_action(FailureType.CONTEXT_EXHAUSTED, "1.1")

        assert action.action == "continue"

    def test_unknown_retry(self, manager):
        """Test unknown error triggers retry."""
        action = manager.determine_recovery_action(FailureType.UNKNOWN, "1.1")

        assert action.action == "retry"

    def test_unknown_escalate_after_attempts(self, manager):
        """Test unknown error escalates after attempts."""
        manager.record_attempt("1.1", 1, False, "Attempt 1")
        manager.record_attempt("1.1", 2, False, "Attempt 2")

        action = manager.determine_recovery_action(FailureType.UNKNOWN, "1.1")

        assert action.action == "escalate"


class TestRecoveryManagerCommitTracking:
    """Tests for commit tracking methods."""

    @pytest.fixture
    def manager(self):
        """Create a RecoveryManager instance."""
        with tempfile.TemporaryDirectory() as spec_td:
            with tempfile.TemporaryDirectory() as proj_td:
                yield RecoveryManager(Path(spec_td), Path(proj_td))

    def test_no_last_good_commit(self, manager):
        """Test getting last good commit when none exists."""
        result = manager.get_last_good_commit()
        assert result is None

    def test_record_good_commit(self, manager):
        """Test recording a good commit."""
        manager.record_good_commit("abc123", "1.1")

        result = manager.get_last_good_commit()
        assert result == "abc123"

    def test_multiple_good_commits(self, manager):
        """Test recording multiple good commits."""
        manager.record_good_commit("abc123", "1.1")
        manager.record_good_commit("def456", "1.2")
        manager.record_good_commit("ghi789", "1.3")

        result = manager.get_last_good_commit()
        assert result == "ghi789"


class TestRecoveryManagerStuckSubtasks:
    """Tests for stuck subtask management."""

    @pytest.fixture
    def manager(self):
        """Create a RecoveryManager instance."""
        with tempfile.TemporaryDirectory() as spec_td:
            with tempfile.TemporaryDirectory() as proj_td:
                yield RecoveryManager(Path(spec_td), Path(proj_td))

    def test_no_stuck_subtasks(self, manager):
        """Test getting stuck subtasks when none exist."""
        result = manager.get_stuck_subtasks()
        assert result == []

    def test_mark_subtask_stuck(self, manager):
        """Test marking a subtask as stuck."""
        manager.mark_subtask_stuck("1.1", "Circular fix detected")

        stuck = manager.get_stuck_subtasks()
        assert len(stuck) == 1
        assert stuck[0]["subtask_id"] == "1.1"
        assert stuck[0]["reason"] == "Circular fix detected"

    def test_mark_same_subtask_twice(self, manager):
        """Test marking same subtask stuck twice."""
        manager.mark_subtask_stuck("1.1", "Reason 1")
        manager.mark_subtask_stuck("1.1", "Reason 2")

        stuck = manager.get_stuck_subtasks()
        assert len(stuck) == 1  # Should not duplicate

    def test_clear_stuck_subtasks(self, manager):
        """Test clearing stuck subtasks."""
        manager.mark_subtask_stuck("1.1", "Stuck")
        manager.mark_subtask_stuck("1.2", "Also stuck")

        manager.clear_stuck_subtasks()

        stuck = manager.get_stuck_subtasks()
        assert stuck == []

    def test_reset_subtask(self, manager):
        """Test resetting a subtask."""
        manager.record_attempt("1.1", 1, False, "Failed")
        manager.mark_subtask_stuck("1.1", "Stuck")

        manager.reset_subtask("1.1")

        count = manager.get_attempt_count("1.1")
        assert count == 0

        stuck = manager.get_stuck_subtasks()
        assert len(stuck) == 0


class TestRecoveryManagerRecoveryHints:
    """Tests for recovery hints generation."""

    @pytest.fixture
    def manager(self):
        """Create a RecoveryManager instance."""
        with tempfile.TemporaryDirectory() as spec_td:
            with tempfile.TemporaryDirectory() as proj_td:
                yield RecoveryManager(Path(spec_td), Path(proj_td))

    def test_hints_first_attempt(self, manager):
        """Test hints for first attempt."""
        hints = manager.get_recovery_hints("1.1")
        assert "first attempt" in hints[0].lower()

    def test_hints_with_history(self, manager):
        """Test hints with previous attempts."""
        manager.record_attempt("1.1", 1, False, "Using sync approach", "Test failed")
        manager.record_attempt("1.1", 2, False, "Using async approach", "Still failed")

        hints = manager.get_recovery_hints("1.1")

        assert "Previous attempts: 2" in hints[0]
        assert any("sync approach" in h.lower() for h in hints)

    def test_hints_include_warning(self, manager):
        """Test hints include warning after multiple attempts."""
        manager.record_attempt("1.1", 1, False, "Attempt 1")
        manager.record_attempt("1.1", 2, False, "Attempt 2")

        hints = manager.get_recovery_hints("1.1")

        assert any("DIFFERENT approach" in h for h in hints)


# =============================================================================
# Utility Function Tests
# =============================================================================

class TestCheckAndRecover:
    """Tests for check_and_recover function."""

    def test_no_error_returns_none(self):
        """Test that no error returns None."""
        with tempfile.TemporaryDirectory() as spec_td:
            with tempfile.TemporaryDirectory() as proj_td:
                result = check_and_recover(Path(spec_td), Path(proj_td), "1.1", None)
                assert result is None

    def test_with_error(self):
        """Test check_and_recover with an error."""
        with tempfile.TemporaryDirectory() as spec_td:
            with tempfile.TemporaryDirectory() as proj_td:
                result = check_and_recover(
                    Path(spec_td),
                    Path(proj_td),
                    "1.1",
                    "SyntaxError: invalid"
                )
                assert result is not None
                assert isinstance(result, RecoveryAction)


class TestGetRecoveryContext:
    """Tests for get_recovery_context function."""

    def test_returns_context(self):
        """Test getting recovery context."""
        with tempfile.TemporaryDirectory() as spec_td:
            with tempfile.TemporaryDirectory() as proj_td:
                context = get_recovery_context(Path(spec_td), Path(proj_td), "1.1")

                assert "attempt_count" in context
                assert "hints" in context
                assert "subtask_history" in context
                assert "stuck_subtasks" in context

    def test_context_with_history(self):
        """Test recovery context with history."""
        with tempfile.TemporaryDirectory() as spec_td:
            with tempfile.TemporaryDirectory() as proj_td:
                # Create manager and add history
                manager = RecoveryManager(Path(spec_td), Path(proj_td))
                manager.record_attempt("1.1", 1, False, "Failed attempt")

                context = get_recovery_context(Path(spec_td), Path(proj_td), "1.1")

                assert context["attempt_count"] == 1
