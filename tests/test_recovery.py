#!/usr/bin/env python3
"""
Test Suite for Smart Rollback and Recovery System
==================================================

Tests the recovery system functionality including:
- Attempt tracking
- Circular fix detection
- Recovery action determination
- Rollback functionality
"""

import json
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from recovery import RecoveryManager, FailureType


def setup_test_environment():
    """Create temporary directories for testing.

    IMPORTANT: This function properly isolates git operations by clearing
    git environment variables that may be set by pre-commit hooks. Without
    this isolation, git operations could affect the parent repository when
    tests run inside a git worktree (e.g., during pre-commit validation).
    """
    temp_dir = Path(tempfile.mkdtemp())
    spec_dir = temp_dir / "spec"
    project_dir = temp_dir / "project"

    spec_dir.mkdir(parents=True)
    project_dir.mkdir(parents=True)

    # Clear git environment variables that may be set by pre-commit hooks
    # to avoid git operations affecting the parent repository
    import subprocess
    git_vars_to_clear = [
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    ]

    saved_env = {}
    for key in git_vars_to_clear:
        saved_env[key] = os.environ.pop(key, None)

    # Set GIT_CEILING_DIRECTORIES to prevent git from discovering parent .git
    saved_env["GIT_CEILING_DIRECTORIES"] = os.environ.get("GIT_CEILING_DIRECTORIES")
    os.environ["GIT_CEILING_DIRECTORIES"] = str(temp_dir)

    # Initialize git repo in project dir
    subprocess.run(["git", "init"], cwd=project_dir, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_dir, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=project_dir, capture_output=True)

    # Create initial commit
    test_file = project_dir / "test.txt"
    test_file.write_text("Initial content")
    subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_dir, capture_output=True)

    # Ensure branch is named 'main' (some git configs default to 'master')
    subprocess.run(["git", "branch", "-M", "main"], cwd=project_dir, capture_output=True)

    # Return saved_env so caller can restore it in cleanup
    return temp_dir, spec_dir, project_dir, saved_env


def cleanup_test_environment(temp_dir, saved_env=None):
    """Remove temporary directories and restore environment variables."""
    shutil.rmtree(temp_dir, ignore_errors=True)

    # Restore original environment variables if provided
    if saved_env is not None:
        for key, value in saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_initialization():
    """Test RecoveryManager initialization."""
    print("TEST: Initialization")

    temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

    try:
        # Initialize manager to trigger directory creation (manager instance not needed)
        _manager = RecoveryManager(spec_dir, project_dir)

        # Check that memory directory was created
        assert (spec_dir / "memory").exists(), "Memory directory not created"

        # Check that attempt history file was created
        assert (spec_dir / "memory" / "attempt_history.json").exists(), "attempt_history.json not created"

        # Check that build commits file was created
        assert (spec_dir / "memory" / "build_commits.json").exists(), "build_commits.json not created"

        # Verify initial structure
        with open(spec_dir / "memory" / "attempt_history.json") as f:
            history = json.load(f)
            assert "subtasks" in history, "subtasks key missing"
            assert "stuck_subtasks" in history, "stuck_subtasks key missing"
            assert "metadata" in history, "metadata key missing"

        print("  ✓ Initialization successful")
        print()

    finally:
        cleanup_test_environment(temp_dir, saved_env)


def test_record_attempt():
    """Test recording chunk attempts."""
    print("TEST: Recording Attempts")

    temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

    try:
        manager = RecoveryManager(spec_dir, project_dir)

        # Record failed attempt
        manager.record_attempt(
            subtask_id="subtask-1",
            session=1,
            success=False,
            approach="First approach using async/await",
            error="Import error - asyncio not found"
        )

        # Verify recorded
        assert manager.get_attempt_count("subtask-1") == 1, "Attempt not recorded"

        history = manager.get_subtask_history("subtask-1")
        assert len(history["attempts"]) == 1, "Wrong number of attempts"
        assert history["attempts"][0]["success"] is False, "Success flag wrong"
        assert history["status"] == "failed", "Status not updated"

        # Record successful attempt
        manager.record_attempt(
            subtask_id="subtask-1",
            session=2,
            success=True,
            approach="Second approach using callbacks",
            error=None
        )

        assert manager.get_attempt_count("subtask-1") == 2, "Second attempt not recorded"

        history = manager.get_subtask_history("subtask-1")
        assert len(history["attempts"]) == 2, "Wrong number of attempts"
        assert history["attempts"][1]["success"] is True, "Success flag wrong"
        assert history["status"] == "completed", "Status not updated to completed"

        print("  ✓ Attempt recording works")
        print()

    finally:
        cleanup_test_environment(temp_dir, saved_env)


def test_circular_fix_detection():
    """Test circular fix detection."""
    print("TEST: Circular Fix Detection")

    temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

    try:
        manager = RecoveryManager(spec_dir, project_dir)

        # Record similar attempts
        manager.record_attempt("subtask-1", 1, False, "Using async await pattern", "Error 1")
        manager.record_attempt("subtask-1", 2, False, "Using async await with different import", "Error 2")
        manager.record_attempt("subtask-1", 3, False, "Trying async await again", "Error 3")

        # Check if circular fix is detected
        is_circular = manager.is_circular_fix("subtask-1", "Using async await pattern once more")

        assert is_circular, "Circular fix not detected"
        print("  ✓ Circular fix detected correctly")

        # Test with different approach
        is_circular = manager.is_circular_fix("subtask-1", "Using completely different callback-based approach")

        # This might be detected as circular if word overlap is high
        # But "callback-based" is sufficiently different from "async await"
        print(f"  ✓ Different approach circular check: {is_circular}")
        print()

    finally:
        cleanup_test_environment(temp_dir, saved_env)


def test_failure_classification():
    """Test failure type classification."""
    print("TEST: Failure Classification")

    temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

    try:
        manager = RecoveryManager(spec_dir, project_dir)

        # Test broken build detection
        failure = manager.classify_failure("SyntaxError: unexpected token", "subtask-1")
        assert failure == FailureType.BROKEN_BUILD, "Broken build not detected"
        print("  ✓ Broken build classified correctly")

        # Test verification failed detection
        failure = manager.classify_failure("Verification failed: expected 200 got 500", "subtask-2")
        assert failure == FailureType.VERIFICATION_FAILED, "Verification failure not detected"
        print("  ✓ Verification failure classified correctly")

        # Test context exhaustion
        failure = manager.classify_failure("Context length exceeded", "subtask-3")
        assert failure == FailureType.CONTEXT_EXHAUSTED, "Context exhaustion not detected"
        print("  ✓ Context exhaustion classified correctly")

        print()

    finally:
        cleanup_test_environment(temp_dir, saved_env)


def test_recovery_action_determination():
    """Test recovery action determination."""
    print("TEST: Recovery Action Determination")

    temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

    try:
        manager = RecoveryManager(spec_dir, project_dir)

        # Test verification failed with < 3 attempts
        manager.record_attempt("subtask-1", 1, False, "First try", "Error")

        action = manager.determine_recovery_action(FailureType.VERIFICATION_FAILED, "subtask-1")
        assert action.action == "retry", "Should retry for first verification failure"
        print("  ✓ Retry action for first failure")

        # Test verification failed with >= 3 attempts
        manager.record_attempt("subtask-1", 2, False, "Second try", "Error")
        manager.record_attempt("subtask-1", 3, False, "Third try", "Error")

        action = manager.determine_recovery_action(FailureType.VERIFICATION_FAILED, "subtask-1")
        assert action.action == "skip", "Should skip after 3 attempts"
        print("  ✓ Skip action after 3 attempts")

        # Test circular fix
        action = manager.determine_recovery_action(FailureType.CIRCULAR_FIX, "subtask-1")
        assert action.action == "skip", "Should skip for circular fix"
        print("  ✓ Skip action for circular fix")

        # Test context exhausted
        action = manager.determine_recovery_action(FailureType.CONTEXT_EXHAUSTED, "subtask-2")
        assert action.action == "continue", "Should continue for context exhaustion"
        print("  ✓ Continue action for context exhaustion")

        print()

    finally:
        cleanup_test_environment(temp_dir, saved_env)


def test_good_commit_tracking():
    """Test tracking of good commits."""
    print("TEST: Good Commit Tracking")

    temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

    try:
        manager = RecoveryManager(spec_dir, project_dir)

        # Get current commit hash
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_dir,
            capture_output=True,
            text=True
        )
        commit_hash = result.stdout.strip()

        # Record good commit
        manager.record_good_commit(commit_hash, "subtask-1")

        # Verify recorded
        last_good = manager.get_last_good_commit()
        assert last_good == commit_hash, "Good commit not recorded correctly"
        print(f"  ✓ Good commit tracked: {commit_hash[:8]}")

        # Record another commit
        test_file = project_dir / "test2.txt"
        test_file.write_text("Second content")
        subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Second commit"], cwd=project_dir, capture_output=True)

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_dir,
            capture_output=True,
            text=True
        )
        commit_hash2 = result.stdout.strip()

        manager.record_good_commit(commit_hash2, "subtask-2")

        # Last good should be updated
        last_good = manager.get_last_good_commit()
        assert last_good == commit_hash2, "Last good commit not updated"
        print(f"  ✓ Last good commit updated: {commit_hash2[:8]}")
        print()

    finally:
        cleanup_test_environment(temp_dir, saved_env)


def test_mark_subtask_stuck():
    """Test marking chunks as stuck."""
    print("TEST: Mark Chunk Stuck")

    temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

    try:
        manager = RecoveryManager(spec_dir, project_dir)

        # Record some attempts
        manager.record_attempt("subtask-1", 1, False, "Try 1", "Error 1")
        manager.record_attempt("subtask-1", 2, False, "Try 2", "Error 2")
        manager.record_attempt("subtask-1", 3, False, "Try 3", "Error 3")

        # Mark as stuck
        manager.mark_subtask_stuck("subtask-1", "Circular fix after 3 attempts")

        # Verify stuck
        stuck_subtasks = manager.get_stuck_subtasks()
        assert len(stuck_subtasks) == 1, "Stuck subtask not recorded"
        assert stuck_subtasks[0]["subtask_id"] == "subtask-1", "Wrong subtask marked as stuck"
        assert "Circular fix" in stuck_subtasks[0]["reason"], "Reason not recorded"

        # Check subtask status
        history = manager.get_subtask_history("subtask-1")
        assert history["status"] == "stuck", "Chunk status not updated to stuck"

        print("  ✓ Chunk marked as stuck correctly")
        print()

    finally:
        cleanup_test_environment(temp_dir, saved_env)


def test_recovery_hints():
    """Test recovery hints generation."""
    print("TEST: Recovery Hints")

    temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

    try:
        manager = RecoveryManager(spec_dir, project_dir)

        # Record some attempts
        manager.record_attempt("subtask-1", 1, False, "Async/await approach", "Import error")
        manager.record_attempt("subtask-1", 2, False, "Threading approach", "Thread safety error")

        # Get hints
        hints = manager.get_recovery_hints("subtask-1")

        assert len(hints) > 0, "No hints generated"
        assert "Previous attempts: 2" in hints[0], "Attempt count not in hints"

        # Check for warning about different approach
        hint_text = " ".join(hints)
        assert "DIFFERENT" in hint_text or "different" in hint_text, "Warning about different approach missing"

        print("  ✓ Recovery hints generated correctly")
        for hint in hints[:3]:  # Show first 3 hints
            print(f"    - {hint}")
        print()

    finally:
        cleanup_test_environment(temp_dir, saved_env)


def test_checkpoint_persistence_across_sessions():
    """Test that session state persists when manager is recreated (checkpoint persistence)."""
    print("TEST: Checkpoint Persistence Across Sessions")

    temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

    try:
        # Session 1: Create manager and record some attempts
        manager1 = RecoveryManager(spec_dir, project_dir)

        manager1.record_attempt(
            subtask_id="subtask-1",
            session=1,
            success=False,
            approach="First approach using REST API",
            error="Connection timeout"
        )
        manager1.record_attempt(
            subtask_id="subtask-1",
            session=1,
            success=False,
            approach="Second approach using WebSocket",
            error="Auth failure"
        )

        # Verify state in session 1
        assert manager1.get_attempt_count("subtask-1") == 2, "Session 1: attempts not recorded"
        print("  ✓ Session 1: recorded 2 attempts")

        # Session 2: Create NEW manager instance (simulating session restart)
        manager2 = RecoveryManager(spec_dir, project_dir)

        # Verify checkpoint was restored
        assert manager2.get_attempt_count("subtask-1") == 2, "Session 2: checkpoint not restored"

        history = manager2.get_subtask_history("subtask-1")
        assert len(history["attempts"]) == 2, "Session 2: attempt history missing"
        assert history["attempts"][0]["approach"] == "First approach using REST API", "Session 2: first approach lost"
        assert history["attempts"][1]["approach"] == "Second approach using WebSocket", "Session 2: second approach lost"
        assert history["status"] == "failed", "Session 2: status not preserved"

        print("  ✓ Session 2: checkpoint restored correctly")
        print("  ✓ All attempt details preserved across sessions")
        print()

    finally:
        cleanup_test_environment(temp_dir, saved_env)


def test_restoration_after_failure():
    """Test that state can be restored from checkpoints after simulated failures."""
    print("TEST: Restoration After Failure")

    temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

    try:
        # Simulate multiple sessions with failures
        manager1 = RecoveryManager(spec_dir, project_dir)

        # Session 1: Initial work
        manager1.record_attempt("subtask-1", 1, False, "Attempt 1", "Error 1")
        manager1.record_attempt("subtask-2", 1, True, "Successful approach", None)

        # Get current commit
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_dir,
            capture_output=True,
            text=True
        )
        commit_hash = result.stdout.strip()
        manager1.record_good_commit(commit_hash, "subtask-2")

        print("  ✓ Session 1: recorded mixed results")

        # Session 2: Continue work with new manager (simulates restart after crash)
        manager2 = RecoveryManager(spec_dir, project_dir)

        # Verify complete state restored
        assert manager2.get_attempt_count("subtask-1") == 1, "subtask-1 attempts not restored"
        assert manager2.get_attempt_count("subtask-2") == 1, "subtask-2 attempts not restored"

        subtask1_history = manager2.get_subtask_history("subtask-1")
        assert subtask1_history["status"] == "failed", "subtask-1 status not restored"

        subtask2_history = manager2.get_subtask_history("subtask-2")
        assert subtask2_history["status"] == "completed", "subtask-2 status not restored"

        # Verify good commit was restored
        last_good = manager2.get_last_good_commit()
        assert last_good == commit_hash, "Last good commit not restored"

        print("  ✓ Session 2: all state restored after simulated failure")

        # Session 3: Continue from restored state
        manager3 = RecoveryManager(spec_dir, project_dir)
        manager3.record_attempt("subtask-1", 2, True, "Fixed approach", None)

        # Final verification
        assert manager3.get_attempt_count("subtask-1") == 2, "Session 3: attempt not added"
        history_final = manager3.get_subtask_history("subtask-1")
        assert history_final["status"] == "completed", "Session 3: status not updated"

        print("  ✓ Session 3: continued from restored state successfully")
        print()

    finally:
        cleanup_test_environment(temp_dir, saved_env)


def test_checkpoint_multiple_subtasks():
    """Test checkpoint persistence with multiple subtasks in various states."""
    print("TEST: Checkpoint Multiple Subtasks")

    temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

    try:
        manager1 = RecoveryManager(spec_dir, project_dir)

        # Create diverse subtask states
        manager1.record_attempt("subtask-1", 1, True, "Completed on first try", None)

        manager1.record_attempt("subtask-2", 1, False, "Failed first", "Error")
        manager1.record_attempt("subtask-2", 2, True, "Fixed second try", None)

        manager1.record_attempt("subtask-3", 1, False, "Try 1", "Error 1")
        manager1.record_attempt("subtask-3", 2, False, "Try 2", "Error 2")
        manager1.record_attempt("subtask-3", 3, False, "Try 3", "Error 3")
        manager1.mark_subtask_stuck("subtask-3", "After 3 failed attempts")

        manager1.record_attempt("subtask-4", 1, False, "In progress", "Partial error")

        print("  ✓ Session 1: created 4 subtasks in different states")

        # New session - verify all states restored
        manager2 = RecoveryManager(spec_dir, project_dir)

        # Verify subtask-1 (completed first try)
        assert manager2.get_attempt_count("subtask-1") == 1
        assert manager2.get_subtask_history("subtask-1")["status"] == "completed"
        print("  ✓ subtask-1: completed state restored")

        # Verify subtask-2 (completed after retry)
        assert manager2.get_attempt_count("subtask-2") == 2
        assert manager2.get_subtask_history("subtask-2")["status"] == "completed"
        print("  ✓ subtask-2: completed-after-retry state restored")

        # Verify subtask-3 (stuck)
        assert manager2.get_attempt_count("subtask-3") == 3
        assert manager2.get_subtask_history("subtask-3")["status"] == "stuck"
        stuck_list = manager2.get_stuck_subtasks()
        assert len(stuck_list) == 1
        assert stuck_list[0]["subtask_id"] == "subtask-3"
        print("  ✓ subtask-3: stuck state restored")

        # Verify subtask-4 (in progress/failed)
        assert manager2.get_attempt_count("subtask-4") == 1
        assert manager2.get_subtask_history("subtask-4")["status"] == "failed"
        print("  ✓ subtask-4: failed state restored")

        print()

    finally:
        cleanup_test_environment(temp_dir, saved_env)


def test_restoration_with_build_commits():
    """Test restoration of build commit checkpoints across sessions."""
    print("TEST: Restoration with Build Commits")

    temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

    try:
        import subprocess

        manager1 = RecoveryManager(spec_dir, project_dir)

        # Create multiple commits and track them
        commits = []

        for i in range(3):
            test_file = project_dir / f"test_file_{i}.txt"
            test_file.write_text(f"Content {i}")
            subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True)
            subprocess.run(["git", "commit", "-m", f"Commit {i}"], cwd=project_dir, capture_output=True)

            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=project_dir,
                capture_output=True,
                text=True
            )
            commit_hash = result.stdout.strip()
            commits.append(commit_hash)

            manager1.record_good_commit(commit_hash, f"subtask-{i}")
            manager1.record_attempt(f"subtask-{i}", 1, True, f"Approach {i}", None)

        print(f"  ✓ Session 1: recorded {len(commits)} commits")

        # New session - verify commit history restored
        manager2 = RecoveryManager(spec_dir, project_dir)

        last_good = manager2.get_last_good_commit()
        assert last_good == commits[-1], "Last good commit not restored correctly"
        print(f"  ✓ Session 2: last good commit restored ({commits[-1][:8]})")

        # Verify we can continue building from restored state
        manager2.record_attempt("subtask-3", 1, False, "New work after restore", "New error")
        assert manager2.get_attempt_count("subtask-3") == 1

        print("  ✓ Session 2: can continue work from restored checkpoint")
        print()

    finally:
        cleanup_test_environment(temp_dir, saved_env)


def test_checkpoint_recovery_hints_restoration():
    """Test that recovery hints are correctly generated from restored checkpoint data."""
    print("TEST: Checkpoint Recovery Hints Restoration")

    temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

    try:
        manager1 = RecoveryManager(spec_dir, project_dir)

        # Record detailed attempt history
        manager1.record_attempt(
            "subtask-1", 1, False,
            "Using synchronous database calls",
            "Database connection pooling exhausted"
        )
        manager1.record_attempt(
            "subtask-1", 2, False,
            "Using asynchronous database with asyncio",
            "Event loop already running error"
        )

        print("  ✓ Session 1: recorded 2 attempts with detailed errors")

        # New session
        manager2 = RecoveryManager(spec_dir, project_dir)

        # Get recovery hints (should be based on restored data)
        hints = manager2.get_recovery_hints("subtask-1")

        assert len(hints) > 0, "No hints generated from restored data"
        assert "Previous attempts: 2" in hints[0], "Attempt count not in restored hints"

        # Verify attempt details are in hints
        hint_text = " ".join(hints)
        assert "synchronous" in hint_text.lower() or "FAILED" in hint_text, "Previous approach not reflected in hints"

        print("  ✓ Session 2: recovery hints generated from restored checkpoint")

        # Check circular fix detection with restored data
        is_circular = manager2.is_circular_fix("subtask-1", "Using async database with asyncio again")
        # Note: May or may not detect as circular depending on word overlap
        print(f"  ✓ Session 2: circular fix detection works ({is_circular})")
        print()

    finally:
        cleanup_test_environment(temp_dir, saved_env)


def test_restoration_stuck_subtasks_list():
    """Test that stuck subtasks list is restored correctly across sessions."""
    print("TEST: Restoration Stuck Subtasks List")

    temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

    try:
        manager1 = RecoveryManager(spec_dir, project_dir)

        # Mark multiple subtasks as stuck
        for i in range(3):
            subtask_id = f"subtask-stuck-{i}"
            for j in range(3):
                manager1.record_attempt(subtask_id, j + 1, False, f"Try {j + 1}", f"Error {j + 1}")
            manager1.mark_subtask_stuck(subtask_id, f"Reason {i}: circular fix detected")

        print("  ✓ Session 1: marked 3 subtasks as stuck")

        # New session
        manager2 = RecoveryManager(spec_dir, project_dir)

        stuck = manager2.get_stuck_subtasks()
        assert len(stuck) == 3, f"Expected 3 stuck subtasks, got {len(stuck)}"

        stuck_ids = {s["subtask_id"] for s in stuck}
        expected_ids = {"subtask-stuck-0", "subtask-stuck-1", "subtask-stuck-2"}
        assert stuck_ids == expected_ids, "Stuck subtask IDs not restored correctly"

        # Verify stuck reasons preserved
        for s in stuck:
            assert "circular fix detected" in s["reason"], "Stuck reason not preserved"
            assert s["attempt_count"] == 3, "Stuck attempt count not preserved"

        print("  ✓ Session 2: all 3 stuck subtasks restored with reasons")
        print()

    finally:
        cleanup_test_environment(temp_dir, saved_env)


def test_checkpoint_clear_and_reset():
    """Test that clearing stuck subtasks and resetting subtasks persists across sessions."""
    print("TEST: Checkpoint Clear and Reset")

    temp_dir, spec_dir, project_dir, saved_env = setup_test_environment()

    try:
        manager1 = RecoveryManager(spec_dir, project_dir)

        # Create some state
        manager1.record_attempt("subtask-1", 1, False, "Try 1", "Error 1")
        manager1.record_attempt("subtask-1", 2, False, "Try 2", "Error 2")
        manager1.mark_subtask_stuck("subtask-1", "Stuck reason")

        manager1.record_attempt("subtask-2", 1, False, "Only try", "Error")

        # Clear stuck subtasks
        manager1.clear_stuck_subtasks()
        assert len(manager1.get_stuck_subtasks()) == 0, "Stuck subtasks not cleared"
        print("  ✓ Session 1: cleared stuck subtasks")

        # Reset subtask-2
        manager1.reset_subtask("subtask-2")
        assert manager1.get_attempt_count("subtask-2") == 0, "Subtask not reset"
        print("  ✓ Session 1: reset subtask-2")

        # New session - verify clear/reset persisted
        manager2 = RecoveryManager(spec_dir, project_dir)

        assert len(manager2.get_stuck_subtasks()) == 0, "Stuck subtasks clear not persisted"
        print("  ✓ Session 2: stuck subtasks clear persisted")

        assert manager2.get_attempt_count("subtask-2") == 0, "Subtask reset not persisted"
        print("  ✓ Session 2: subtask reset persisted")

        # But subtask-1 history should still exist (just not marked stuck)
        assert manager2.get_attempt_count("subtask-1") == 2, "subtask-1 history lost"
        print("  ✓ Session 2: subtask-1 history preserved (not reset)")
        print()

    finally:
        cleanup_test_environment(temp_dir, saved_env)


def run_all_tests():
    """Run all tests."""
    print("=" * 70)
    print("SMART ROLLBACK AND RECOVERY - TEST SUITE")
    print("=" * 70)
    print()

    tests = [
        test_initialization,
        test_record_attempt,
        test_circular_fix_detection,
        test_failure_classification,
        test_recovery_action_determination,
        test_good_commit_tracking,
        test_mark_subtask_stuck,
        test_recovery_hints,
        # Session checkpoint and restoration tests
        test_checkpoint_persistence_across_sessions,
        test_restoration_after_failure,
        test_checkpoint_multiple_subtasks,
        test_restoration_with_build_commits,
        test_checkpoint_recovery_hints_restoration,
        test_restoration_stuck_subtasks_list,
        test_checkpoint_clear_and_reset,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}")
            print()
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            print()
            failed += 1

    print("=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
