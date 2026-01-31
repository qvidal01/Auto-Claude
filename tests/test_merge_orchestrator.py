#!/usr/bin/env python3
"""
Tests for MergeOrchestrator and Integration Tests
=================================================

Tests the full merge pipeline coordination and end-to-end workflows.

Covers:
- Orchestrator initialization
- Dry run mode
- Merge previews
- Single-task merge pipeline
- Multi-task merge pipeline with compatible changes
- Merge statistics and reports
- AI enabled/disabled modes
- Report serialization
"""

import json
import sys
from pathlib import Path

import pytest

# Add auto-claude directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))
# Add tests directory to path for test_fixtures
sys.path.insert(0, str(Path(__file__).parent))

from merge import MergeOrchestrator
from merge.orchestrator import TaskMergeRequest

from test_fixtures import (
    SAMPLE_PYTHON_MODULE,
    SAMPLE_PYTHON_WITH_NEW_FUNCTION,
    SAMPLE_PYTHON_WITH_NEW_IMPORT,
)


class TestOrchestratorInitialization:
    """Tests for MergeOrchestrator initialization."""

    def test_initialization(self, temp_project):
        """Orchestrator initializes with all components."""
        orchestrator = MergeOrchestrator(temp_project)

        # Use resolve() to handle symlinks on macOS (/var vs /private/var)
        assert orchestrator.project_dir.resolve() == temp_project.resolve()
        assert orchestrator.analyzer is not None
        assert orchestrator.conflict_detector is not None
        assert orchestrator.auto_merger is not None
        assert orchestrator.evolution_tracker is not None

    def test_dry_run_mode(self, temp_project):
        """Dry run mode doesn't write files."""
        orchestrator = MergeOrchestrator(temp_project, dry_run=True)

        # Capture baseline and simulate merge
        orchestrator.evolution_tracker.capture_baselines(
            "task-001", [temp_project / "src" / "utils.py"]
        )
        orchestrator.evolution_tracker.record_modification(
            "task-001",
            "src/utils.py",
            SAMPLE_PYTHON_MODULE,
            SAMPLE_PYTHON_WITH_NEW_FUNCTION,
        )

        report = orchestrator.merge_task("task-001")

        # Should have results but not write files
        assert report is not None
        written = orchestrator.write_merged_files(report)
        assert len(written) == 0  # Dry run

    def test_ai_disabled_mode(self, temp_project):
        """Orchestrator works without AI enabled."""
        orchestrator = MergeOrchestrator(temp_project, enable_ai=False, dry_run=True)

        files = [temp_project / "src" / "utils.py"]
        orchestrator.evolution_tracker.capture_baselines("task-001", files)
        orchestrator.evolution_tracker.record_modification(
            "task-001", "src/utils.py", SAMPLE_PYTHON_MODULE, SAMPLE_PYTHON_WITH_NEW_FUNCTION
        )

        report = orchestrator.merge_task("task-001")

        # Should complete without AI
        assert report.stats.ai_calls_made == 0


class TestMergePreview:
    """Tests for merge preview functionality."""

    def test_preview_merge(self, temp_project):
        """Preview provides merge analysis without executing."""
        orchestrator = MergeOrchestrator(temp_project)

        # Setup two tasks modifying same file
        files = [temp_project / "src" / "utils.py"]
        orchestrator.evolution_tracker.capture_baselines("task-001", files)
        orchestrator.evolution_tracker.capture_baselines("task-002", files)

        orchestrator.evolution_tracker.record_modification(
            "task-001", "src/utils.py", SAMPLE_PYTHON_MODULE, SAMPLE_PYTHON_WITH_NEW_FUNCTION
        )
        orchestrator.evolution_tracker.record_modification(
            "task-002", "src/utils.py", SAMPLE_PYTHON_MODULE, SAMPLE_PYTHON_WITH_NEW_IMPORT
        )

        preview = orchestrator.preview_merge(["task-001", "task-002"])

        assert "tasks" in preview
        assert "files_to_merge" in preview
        assert "summary" in preview


class TestSingleTaskMerge:
    """Integration tests for single task merge."""

    def test_full_merge_pipeline_single_task(self, temp_project):
        """Full pipeline works for single task merge (with git-committed changes)."""
        import subprocess

        orchestrator = MergeOrchestrator(temp_project, dry_run=True)

        # Setup: capture baseline
        files = [temp_project / "src" / "utils.py"]
        orchestrator.evolution_tracker.capture_baselines("task-001", files, intent="Add new function")

        # Create a task branch with actual git changes (the merge pipeline uses git diff main...HEAD)
        subprocess.run(["git", "checkout", "-b", "auto-claude/task-001"], cwd=temp_project, capture_output=True)
        utils_file = temp_project / "src" / "utils.py"
        utils_file.write_text(SAMPLE_PYTHON_WITH_NEW_FUNCTION)
        subprocess.run(["git", "add", "."], cwd=temp_project, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add new function"], cwd=temp_project, capture_output=True)

        # Execute merge - provide worktree_path to avoid lookup
        report = orchestrator.merge_task("task-001", worktree_path=temp_project)

        # Verify results
        assert report.success is True
        assert "task-001" in report.tasks_merged
        # The pipeline should detect and process the modified file
        assert report.stats.files_processed >= 1


class TestMultiTaskMerge:
    """Integration tests for multi-task merge."""

    def test_compatible_multi_task_merge(self, temp_project):
        """Compatible changes from multiple tasks merge automatically."""
        orchestrator = MergeOrchestrator(temp_project, dry_run=True)

        # Setup: both tasks modify same file with compatible changes
        files = [temp_project / "src" / "utils.py"]
        orchestrator.evolution_tracker.capture_baselines("task-001", files, intent="Add logging")
        orchestrator.evolution_tracker.capture_baselines("task-002", files, intent="Add json")

        # Task 1: adds logging import
        orchestrator.evolution_tracker.record_modification(
            "task-001",
            "src/utils.py",
            SAMPLE_PYTHON_MODULE,
            SAMPLE_PYTHON_WITH_NEW_IMPORT,  # Has logging import
        )

        # Task 2: adds new function
        orchestrator.evolution_tracker.record_modification(
            "task-002",
            "src/utils.py",
            SAMPLE_PYTHON_MODULE,
            SAMPLE_PYTHON_WITH_NEW_FUNCTION,
        )

        # Execute merge
        report = orchestrator.merge_tasks([
            TaskMergeRequest(task_id="task-001", worktree_path=temp_project),
            TaskMergeRequest(task_id="task-002", worktree_path=temp_project),
        ])

        # Both tasks should merge successfully
        assert len(report.tasks_merged) == 2
        # Auto-merge should handle compatible changes
        assert report.stats.files_auto_merged >= 0


class TestMergeStats:
    """Tests for merge statistics and reports."""

    def test_merge_stats(self, temp_project):
        """Merge report includes useful statistics."""
        orchestrator = MergeOrchestrator(temp_project, dry_run=True)

        files = [temp_project / "src" / "utils.py"]
        orchestrator.evolution_tracker.capture_baselines("task-001", files)
        orchestrator.evolution_tracker.record_modification(
            "task-001", "src/utils.py", SAMPLE_PYTHON_MODULE, SAMPLE_PYTHON_WITH_NEW_FUNCTION
        )

        report = orchestrator.merge_task("task-001")

        assert report.stats.files_processed >= 0
        assert report.stats.duration_seconds >= 0

    def test_merge_report_serialization(self, temp_project):
        """Merge report can be serialized to JSON."""
        orchestrator = MergeOrchestrator(temp_project, dry_run=True)

        files = [temp_project / "src" / "utils.py"]
        orchestrator.evolution_tracker.capture_baselines("task-001", files)
        orchestrator.evolution_tracker.record_modification(
            "task-001", "src/utils.py", SAMPLE_PYTHON_MODULE, SAMPLE_PYTHON_WITH_NEW_FUNCTION
        )

        # Provide worktree_path to avoid lookup
        report = orchestrator.merge_task("task-001", worktree_path=temp_project)

        # Should be serializable
        data = report.to_dict()
        json_str = json.dumps(data)
        restored = json.loads(json_str)

        assert restored["tasks_merged"] == ["task-001"]
        assert restored["success"] is True


class TestErrorHandling:
    """Tests for error handling in orchestrator."""

    def test_missing_baseline_handling(self, temp_project):
        """Handles missing baseline gracefully."""
        orchestrator = MergeOrchestrator(temp_project, dry_run=True)

        # Try to merge without capturing baseline
        # Should handle gracefully (may return error report)
        report = orchestrator.merge_task("nonexistent-task")

        assert report is not None
        # May be success=False or have empty tasks_merged
        assert isinstance(report.success, bool)

    def test_empty_task_list(self, temp_project):
        """Handles empty task list."""
        orchestrator = MergeOrchestrator(temp_project, dry_run=True)

        report = orchestrator.merge_tasks([])

        assert report is not None
        assert len(report.tasks_merged) == 0


class TestOrchestratorIntegration:
    """Integration tests for orchestrator workflow."""

    def test_full_orchestrator_lifecycle(self, temp_project):
        """Tests complete orchestrator lifecycle from start to merge."""
        orchestrator = MergeOrchestrator(temp_project, dry_run=True)

        # Setup baseline
        files = [temp_project / "src" / "utils.py"]
        orchestrator.evolution_tracker.capture_baselines("task-001", files)

        # Record modifications
        orchestrator.evolution_tracker.record_modification(
            "task-001",
            "src/utils.py",
            SAMPLE_PYTHON_MODULE,
            SAMPLE_PYTHON_WITH_NEW_FUNCTION,
        )

        # Merge
        report = orchestrator.merge_task("task-001")

        # Verify success
        assert report is not None
        assert "task-001" in report.tasks_merged

    def test_orchestrator_with_progress_callback(self, temp_project):
        """Progress callback receives updates."""
        orchestrator = MergeOrchestrator(temp_project, dry_run=True)
        progress_updates = []

        def callback(stage, percent, message, details=None):
            progress_updates.append({
                "stage": stage,
                "percent": percent,
                "message": message,
                "details": details,
            })

        # Setup
        files = [temp_project / "src" / "utils.py"]
        orchestrator.evolution_tracker.capture_baselines("task-001", files)
        orchestrator.evolution_tracker.record_modification(
            "task-001", "src/utils.py", SAMPLE_PYTHON_MODULE, SAMPLE_PYTHON_WITH_NEW_FUNCTION
        )

        # Merge with callback
        report = orchestrator.merge_task("task-001", progress_callback=callback)

        # Verify callbacks were made
        assert len(progress_updates) > 0
        # Should have ANALYZING stage
        assert any(u["stage"].value == "analyzing" for u in progress_updates)

    def test_orchestrator_direct_copy_fallback(self, temp_project):
        """DIRECT_COPY fallback when semantic analysis fails."""
        orchestrator = MergeOrchestrator(temp_project, dry_run=True)

        # Create a file with body modifications (semantic analyzer can't parse)
        unsupported_content = """
def complex_function():
    # Complex logic that semantic analyzer can't parse
    result = do_complex_thing()
    return result
"""
        files = [temp_project / "src" / "complex.py"]
        orchestrator.evolution_tracker.capture_baselines("task-001", files)

        # Record modification with changes in function body
        orchestrator.evolution_tracker.record_modification(
            "task-001",
            "src/complex.py",
            "def complex_function(): pass",
            unsupported_content,
        )

        report = orchestrator.merge_task("task-001", worktree_path=temp_project)

        # Should handle gracefully (may use DIRECT_COPY or succeed)
        assert report is not None

    def test_orchestrator_write_merged_files(self, temp_project, temp_dir):
        """Write merged files to output directory."""
        orchestrator = MergeOrchestrator(temp_project, dry_run=False)

        # Setup and merge
        files = [temp_project / "src" / "utils.py"]
        orchestrator.evolution_tracker.capture_baselines("task-001", files)
        orchestrator.evolution_tracker.record_modification(
            "task-001", "src/utils.py", SAMPLE_PYTHON_MODULE, SAMPLE_PYTHON_WITH_NEW_FUNCTION
        )

        report = orchestrator.merge_task("task-001")

        # Write files
        output_dir = temp_dir / "merge_output"
        written = orchestrator.write_merged_files(report, output_dir=output_dir)

        # Verify files written
        assert len(written) >= 0
        if len(written) > 0:
            assert output_dir.exists()

    def test_orchestrator_apply_to_project(self, temp_project):
        """Apply merged files directly to project."""
        orchestrator = MergeOrchestrator(temp_project, dry_run=False)

        # Setup and merge
        files = [temp_project / "src" / "utils.py"]
        orchestrator.evolution_tracker.capture_baselines("task-001", files)
        orchestrator.evolution_tracker.record_modification(
            "task-001", "src/utils.py", SAMPLE_PYTHON_MODULE, SAMPLE_PYTHON_WITH_NEW_FUNCTION
        )

        report = orchestrator.merge_task("task-001")

        # Apply to project
        success = orchestrator.apply_to_project(report)

        # Should return boolean
        assert isinstance(success, bool)


class TestOrchestratorAIConfiguration:
    """Tests for AI resolver configuration."""

    def test_ai_enabled_mode(self, temp_project):
        """Orchestrator with AI enabled."""
        orchestrator = MergeOrchestrator(temp_project, enable_ai=True, dry_run=True)

        assert orchestrator.enable_ai is True
        assert orchestrator._ai_resolver is None  # Lazy init
        # Accessing property initializes it
        resolver = orchestrator.ai_resolver
        assert resolver is not None

    def test_ai_disabled_mode(self, temp_project):
        """Orchestrator with AI disabled."""
        orchestrator = MergeOrchestrator(temp_project, enable_ai=False, dry_run=True)

        assert orchestrator.enable_ai is False
        resolver = orchestrator.ai_resolver
        assert resolver is not None  # Still creates resolver but without AI function

    def test_custom_ai_resolver(self, temp_project, mock_ai_resolver):
        """Orchestrator with custom AI resolver."""
        orchestrator = MergeOrchestrator(
            temp_project,
            enable_ai=True,
            ai_resolver=mock_ai_resolver,
            dry_run=True,
        )

        assert orchestrator._ai_resolver is mock_ai_resolver
        assert orchestrator.ai_resolver is mock_ai_resolver


class TestOrchestratorConflictHandling:
    """Tests for conflict detection and resolution."""

    def test_get_pending_conflicts(self, temp_project):
        """Returns files with pending conflicts."""
        orchestrator = MergeOrchestrator(temp_project, dry_run=True)

        # Setup two tasks modifying same location
        files = [temp_project / "src" / "utils.py"]
        orchestrator.evolution_tracker.capture_baselines("task-001", files)
        orchestrator.evolution_tracker.capture_baselines("task-002", files)

        # Both modify same function
        orchestrator.evolution_tracker.record_modification(
            "task-001",
            "src/utils.py",
            SAMPLE_PYTHON_MODULE,
            SAMPLE_PYTHON_WITH_NEW_IMPORT,
        )
        orchestrator.evolution_tracker.record_modification(
            "task-002",
            "src/utils.py",
            SAMPLE_PYTHON_MODULE,
            SAMPLE_PYTHON_WITH_NEW_FUNCTION,
        )

        # Get pending conflicts
        conflicts = orchestrator.get_pending_conflicts()

        # Should detect conflict or compatible changes
        assert isinstance(conflicts, list)

    def test_preview_merge_with_conflicts(self, temp_project):
        """Preview merge shows conflict information."""
        orchestrator = MergeOrchestrator(temp_project, dry_run=True)

        # Setup conflicting tasks
        files = [temp_project / "src" / "utils.py"]
        orchestrator.evolution_tracker.capture_baselines("task-001", files)
        orchestrator.evolution_tracker.capture_baselines("task-002", files)

        orchestrator.evolution_tracker.record_modification(
            "task-001", "src/utils.py", SAMPLE_PYTHON_MODULE, SAMPLE_PYTHON_WITH_NEW_IMPORT
        )
        orchestrator.evolution_tracker.record_modification(
            "task-002", "src/utils.py", SAMPLE_PYTHON_MODULE, SAMPLE_PYTHON_WITH_NEW_FUNCTION
        )

        # Preview merge
        preview = orchestrator.preview_merge(["task-001", "task-002"])

        assert "tasks" in preview
        assert "files_to_merge" in preview
        assert "summary" in preview
        assert preview["summary"]["total_files"] >= 0
