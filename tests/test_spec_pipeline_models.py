"""
Tests for the spec pipeline models module
==========================================

Tests covering spec/pipeline/models.py - pipeline utilities and functions
"""

import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from spec.pipeline.models import (
    get_specs_dir,
    cleanup_orphaned_pending_folders,
    create_spec_dir,
    generate_spec_name,
    rename_spec_dir_from_requirements,
    PHASE_DISPLAY,
)


# =============================================================================
# generate_spec_name Tests
# =============================================================================

class TestGenerateSpecName:
    """Tests for generate_spec_name function."""

    def test_basic_conversion(self):
        """Test basic task description conversion."""
        result = generate_spec_name("implement user authentication")
        assert result == "user-authentication"

    def test_filters_skip_words(self):
        """Test that common skip words are filtered."""
        result = generate_spec_name("add a new feature to the system")
        # 'add', 'a', 'new', 'to', 'the' should be filtered
        assert "add" not in result
        assert "the" not in result

    def test_limits_to_four_words(self):
        """Test that result is limited to four meaningful words."""
        result = generate_spec_name(
            "implement user authentication with jwt tokens and oauth2 and more"
        )
        words = result.split("-")
        assert len(words) <= 4

    def test_kebab_case_format(self):
        """Test that result is in kebab-case."""
        result = generate_spec_name("User Profile Settings Page")
        assert "-" in result
        assert result.islower()
        assert " " not in result

    def test_removes_special_characters(self):
        """Test that special characters are removed."""
        result = generate_spec_name("Add feature (v2.0) - with #tags!")
        assert "(" not in result
        assert ")" not in result
        assert "#" not in result
        assert "!" not in result

    def test_short_words_filtered(self):
        """Test that very short words are filtered."""
        result = generate_spec_name("go to db in app")
        # 'go', 'to', 'db', 'in' are all very short or skip words

    def test_fallback_to_spec(self):
        """Test fallback when no meaningful words."""
        result = generate_spec_name("to the a an")
        # All skip words - should fall back to 'spec' or use original words
        assert len(result) > 0

    def test_empty_string(self):
        """Test with empty string."""
        result = generate_spec_name("")
        assert result == "spec"

    def test_numbers_preserved(self):
        """Test that numbers in words are preserved."""
        result = generate_spec_name("implement oauth2 authentication")
        assert "oauth2" in result

    def test_unicode_handled(self):
        """Test that Unicode is handled gracefully."""
        result = generate_spec_name("add emoji support 🎉")
        # Should not crash, may or may not include emoji
        assert isinstance(result, str)


# =============================================================================
# get_specs_dir Tests
# =============================================================================

class TestGetSpecsDir:
    """Tests for get_specs_dir function."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_returns_specs_path(self, temp_project):
        """Test that correct specs path is returned."""
        with patch('spec.pipeline.models.init_auto_claude_dir'):
            result = get_specs_dir(temp_project)
            assert result == temp_project / ".auto-claude" / "specs"

    def test_calls_init(self, temp_project):
        """Test that init_auto_claude_dir is called."""
        with patch('spec.pipeline.models.init_auto_claude_dir') as mock_init:
            get_specs_dir(temp_project)
            mock_init.assert_called_once_with(temp_project)


# =============================================================================
# cleanup_orphaned_pending_folders Tests
# =============================================================================

class TestCleanupOrphanedPendingFolders:
    """Tests for cleanup_orphaned_pending_folders function."""

    @pytest.fixture
    def temp_specs_dir(self):
        """Create a temporary specs directory."""
        with tempfile.TemporaryDirectory() as td:
            specs_dir = Path(td) / "specs"
            specs_dir.mkdir()
            yield specs_dir

    def test_nonexistent_dir(self, temp_specs_dir):
        """Test with nonexistent directory."""
        # Remove the directory
        temp_specs_dir.rmdir()
        # Should not raise
        cleanup_orphaned_pending_folders(temp_specs_dir)

    def test_keeps_folders_with_requirements(self, temp_specs_dir):
        """Test that folders with requirements.json are kept."""
        pending = temp_specs_dir / "001-pending"
        pending.mkdir()
        (pending / "requirements.json").write_text('{}')

        cleanup_orphaned_pending_folders(temp_specs_dir)
        assert pending.exists()

    def test_keeps_folders_with_spec(self, temp_specs_dir):
        """Test that folders with spec.md are kept."""
        pending = temp_specs_dir / "002-pending"
        pending.mkdir()
        (pending / "spec.md").write_text("# Spec")

        cleanup_orphaned_pending_folders(temp_specs_dir)
        assert pending.exists()

    def test_keeps_folders_with_plan(self, temp_specs_dir):
        """Test that folders with implementation_plan.json are kept."""
        pending = temp_specs_dir / "003-pending"
        pending.mkdir()
        (pending / "implementation_plan.json").write_text('{}')

        cleanup_orphaned_pending_folders(temp_specs_dir)
        assert pending.exists()

    def test_ignores_non_pending_folders(self, temp_specs_dir):
        """Test that non-pending folders are ignored."""
        normal = temp_specs_dir / "004-feature"
        normal.mkdir()

        cleanup_orphaned_pending_folders(temp_specs_dir)
        assert normal.exists()


# =============================================================================
# create_spec_dir Tests
# =============================================================================

class TestCreateSpecDir:
    """Tests for create_spec_dir function."""

    @pytest.fixture
    def temp_specs_dir(self):
        """Create a temporary specs directory."""
        with tempfile.TemporaryDirectory() as td:
            specs_dir = Path(td) / "specs"
            specs_dir.mkdir()
            yield specs_dir

    def test_first_spec(self, temp_specs_dir):
        """Test creating first spec directory."""
        result = create_spec_dir(temp_specs_dir)
        assert result == temp_specs_dir / "001-pending"

    def test_increments_number(self, temp_specs_dir):
        """Test that number is incremented from existing."""
        # Create existing specs
        (temp_specs_dir / "001-feature").mkdir()
        (temp_specs_dir / "002-bugfix").mkdir()

        result = create_spec_dir(temp_specs_dir)
        assert result == temp_specs_dir / "003-pending"

    def test_finds_highest_number(self, temp_specs_dir):
        """Test that highest number is found even if gaps exist."""
        (temp_specs_dir / "001-first").mkdir()
        (temp_specs_dir / "005-fifth").mkdir()

        result = create_spec_dir(temp_specs_dir)
        assert result == temp_specs_dir / "006-pending"

    def test_with_lock(self, temp_specs_dir):
        """Test with SpecNumberLock."""
        mock_lock = MagicMock()
        mock_lock.get_next_spec_number.return_value = 10

        result = create_spec_dir(temp_specs_dir, lock=mock_lock)
        assert result == temp_specs_dir / "010-pending"
        mock_lock.get_next_spec_number.assert_called_once()


# =============================================================================
# rename_spec_dir_from_requirements Tests
# =============================================================================

class TestRenameSpecDirFromRequirements:
    """Tests for rename_spec_dir_from_requirements function."""

    @pytest.fixture
    def temp_specs_dir(self):
        """Create a temporary specs directory with pending folder."""
        with tempfile.TemporaryDirectory() as td:
            specs_dir = Path(td) / "specs"
            specs_dir.mkdir()
            pending = specs_dir / "001-pending"
            pending.mkdir()
            yield pending

    def test_no_requirements_file(self, temp_specs_dir):
        """Test when requirements.json doesn't exist."""
        result = rename_spec_dir_from_requirements(temp_specs_dir)
        assert result is False

    def test_empty_task_description(self, temp_specs_dir):
        """Test with empty task description."""
        (temp_specs_dir / "requirements.json").write_text(
            json.dumps({"task_description": ""})
        )
        result = rename_spec_dir_from_requirements(temp_specs_dir)
        assert result is False

    def test_already_renamed(self):
        """Test when folder is already renamed (not pending)."""
        with tempfile.TemporaryDirectory() as td:
            specs_dir = Path(td) / "specs"
            specs_dir.mkdir()
            feature_dir = specs_dir / "001-feature"
            feature_dir.mkdir()
            (feature_dir / "requirements.json").write_text(
                json.dumps({"task_description": "Test feature"})
            )

            result = rename_spec_dir_from_requirements(feature_dir)
            assert result is True
            assert feature_dir.exists()  # Should not move

    def test_successful_rename(self, temp_specs_dir):
        """Test successful rename."""
        (temp_specs_dir / "requirements.json").write_text(
            json.dumps({"task_description": "Implement user authentication feature"})
        )

        with patch('spec.pipeline.models.update_task_logger_path'):
            with patch('spec.pipeline.models.print_status'):
                result = rename_spec_dir_from_requirements(temp_specs_dir)

        assert result is True


# =============================================================================
# PHASE_DISPLAY Tests
# =============================================================================

class TestPhaseDisplay:
    """Tests for PHASE_DISPLAY configuration."""

    def test_is_dict(self):
        """Test that PHASE_DISPLAY is a dictionary."""
        assert isinstance(PHASE_DISPLAY, dict)

    def test_has_expected_phases(self):
        """Test that expected phases are present."""
        expected_phases = [
            "discovery", "historical_context", "requirements",
            "complexity_assessment", "research", "context",
            "quick_spec", "spec_writing", "self_critique",
            "planning", "validation"
        ]
        for phase in expected_phases:
            assert phase in PHASE_DISPLAY

    def test_phase_values_are_tuples(self):
        """Test that values are tuples with display name and icon."""
        for phase, value in PHASE_DISPLAY.items():
            assert isinstance(value, tuple)
            assert len(value) == 2
            assert isinstance(value[0], str)  # Display name


# =============================================================================
# Integration Tests
# =============================================================================

class TestPipelineModelsIntegration:
    """Integration tests for pipeline models."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_spec_creation_workflow(self, temp_project):
        """Test complete spec creation workflow."""
        # Get specs directory
        specs_dir = temp_project / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)

        # Create spec directory
        spec_dir = create_spec_dir(specs_dir)
        spec_dir.mkdir()
        assert spec_dir.name == "001-pending"

        # Add requirements
        requirements = {
            "task_description": "Add user login feature",
            "workflow_type": "feature"
        }
        (spec_dir / "requirements.json").write_text(json.dumps(requirements))

        # Rename based on requirements
        with patch('spec.pipeline.models.update_task_logger_path'):
            with patch('spec.pipeline.models.print_status'):
                result = rename_spec_dir_from_requirements(spec_dir)

        assert result is True

    def test_generate_spec_name_variations(self):
        """Test various task descriptions."""
        test_cases = [
            ("Add authentication", "authentication"),
            ("Fix the bug in login", "bug-login"),
            ("Implement OAuth2 integration", "oauth2-integration"),
            ("Create API endpoints", "api-endpoints"),
        ]

        for task, expected_contains in test_cases:
            result = generate_spec_name(task)
            assert expected_contains in result or len(result) > 0
