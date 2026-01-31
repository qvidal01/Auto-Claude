"""
Tests for the spec requirements module
=======================================

Tests covering spec/requirements.py - requirements gathering and management
"""

import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from spec.requirements import (
    create_requirements_from_task,
    save_requirements,
    load_requirements,
)


# =============================================================================
# create_requirements_from_task Tests
# =============================================================================

class TestCreateRequirementsFromTask:
    """Tests for create_requirements_from_task function."""

    def test_creates_dict(self):
        """Test that function returns a dictionary."""
        result = create_requirements_from_task("Add login feature")
        assert isinstance(result, dict)

    def test_task_description_set(self):
        """Test that task description is set correctly."""
        result = create_requirements_from_task("Add user authentication")
        assert result["task_description"] == "Add user authentication"

    def test_default_workflow_type(self):
        """Test default workflow type is 'feature'."""
        result = create_requirements_from_task("Some task")
        assert result["workflow_type"] == "feature"

    def test_empty_services_involved(self):
        """Test services_involved starts empty."""
        result = create_requirements_from_task("Some task")
        assert result["services_involved"] == []

    def test_created_at_timestamp(self):
        """Test that created_at is a valid ISO timestamp."""
        result = create_requirements_from_task("Some task")
        assert "created_at" in result
        # Should parse as valid datetime
        datetime.fromisoformat(result["created_at"])

    def test_empty_task_description(self):
        """Test with empty task description."""
        result = create_requirements_from_task("")
        assert result["task_description"] == ""

    def test_long_task_description(self):
        """Test with long task description."""
        long_desc = "A" * 1000
        result = create_requirements_from_task(long_desc)
        assert result["task_description"] == long_desc

    def test_special_characters(self):
        """Test with special characters in task description."""
        special_desc = "Add feature with 'quotes', \"double quotes\", & special chars <>"
        result = create_requirements_from_task(special_desc)
        assert result["task_description"] == special_desc

    def test_unicode_task_description(self):
        """Test with Unicode characters."""
        unicode_desc = "Add 功能 with émojis 🚀"
        result = create_requirements_from_task(unicode_desc)
        assert result["task_description"] == unicode_desc


# =============================================================================
# save_requirements Tests
# =============================================================================

class TestSaveRequirements:
    """Tests for save_requirements function."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_creates_file(self, temp_dir):
        """Test that file is created."""
        requirements = create_requirements_from_task("Test task")
        result_path = save_requirements(temp_dir, requirements)

        assert result_path.exists()
        assert result_path.name == "requirements.json"

    def test_returns_correct_path(self, temp_dir):
        """Test that correct path is returned."""
        requirements = {"task_description": "Test"}
        result_path = save_requirements(temp_dir, requirements)

        assert result_path == temp_dir / "requirements.json"

    def test_file_contains_valid_json(self, temp_dir):
        """Test that file contains valid JSON."""
        requirements = create_requirements_from_task("Test task")
        result_path = save_requirements(temp_dir, requirements)

        with open(result_path, encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded == requirements

    def test_overwrites_existing_file(self, temp_dir):
        """Test that existing file is overwritten."""
        # Create initial file
        initial_req = {"task_description": "Initial"}
        save_requirements(temp_dir, initial_req)

        # Overwrite
        new_req = {"task_description": "Updated"}
        result_path = save_requirements(temp_dir, new_req)

        with open(result_path, encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded["task_description"] == "Updated"

    def test_creates_subdirectory(self, temp_dir):
        """Test saving to nested directory."""
        spec_dir = temp_dir / "specs" / "001-feature"
        spec_dir.mkdir(parents=True)

        requirements = {"task_description": "Test"}
        result_path = save_requirements(spec_dir, requirements)

        assert result_path.exists()

    def test_preserves_unicode(self, temp_dir):
        """Test that Unicode is preserved."""
        requirements = {"task_description": "Test with 功能 🚀"}
        result_path = save_requirements(temp_dir, requirements)

        with open(result_path, encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded["task_description"] == "Test with 功能 🚀"

    def test_formatted_json(self, temp_dir):
        """Test that JSON is formatted with indentation."""
        requirements = {"task_description": "Test", "workflow_type": "feature"}
        result_path = save_requirements(temp_dir, requirements)

        with open(result_path, encoding="utf-8") as f:
            content = f.read()

        # Should be indented (multi-line)
        assert "\n" in content


# =============================================================================
# load_requirements Tests
# =============================================================================

class TestLoadRequirements:
    """Tests for load_requirements function."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_loads_existing_file(self, temp_dir):
        """Test loading an existing requirements file."""
        requirements = {"task_description": "Test task", "workflow_type": "bugfix"}
        save_requirements(temp_dir, requirements)

        result = load_requirements(temp_dir)

        assert result == requirements

    def test_returns_none_if_not_exists(self, temp_dir):
        """Test that None is returned if file doesn't exist."""
        result = load_requirements(temp_dir)
        assert result is None

    def test_roundtrip(self, temp_dir):
        """Test save/load roundtrip."""
        original = {
            "task_description": "Full test",
            "workflow_type": "feature",
            "services_involved": ["auth", "api"],
            "additional_context": "Some context",
            "created_at": datetime.now().isoformat()
        }

        save_requirements(temp_dir, original)
        loaded = load_requirements(temp_dir)

        assert loaded == original

    def test_loads_unicode(self, temp_dir):
        """Test loading requirements with Unicode."""
        requirements = {"task_description": "功能 emoji 🎉"}
        save_requirements(temp_dir, requirements)

        result = load_requirements(temp_dir)
        assert result["task_description"] == "功能 emoji 🎉"


# =============================================================================
# Integration Tests
# =============================================================================

class TestRequirementsIntegration:
    """Integration tests for requirements module."""

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_full_workflow(self, temp_dir):
        """Test complete requirements workflow."""
        # Create from task
        task = "Implement user authentication with OAuth2"
        requirements = create_requirements_from_task(task)

        # Verify structure
        assert requirements["task_description"] == task
        assert requirements["workflow_type"] == "feature"
        assert requirements["services_involved"] == []
        assert "created_at" in requirements

        # Save to file
        spec_dir = temp_dir / "001-auth"
        spec_dir.mkdir()
        file_path = save_requirements(spec_dir, requirements)

        # Verify file exists
        assert file_path.exists()

        # Load back
        loaded = load_requirements(spec_dir)

        # Verify roundtrip
        assert loaded == requirements

    def test_modify_and_save(self, temp_dir):
        """Test modifying requirements and saving."""
        # Create initial
        requirements = create_requirements_from_task("Initial task")
        save_requirements(temp_dir, requirements)

        # Load, modify, save
        loaded = load_requirements(temp_dir)
        loaded["workflow_type"] = "bugfix"
        loaded["services_involved"] = ["api", "database"]
        save_requirements(temp_dir, loaded)

        # Load again
        final = load_requirements(temp_dir)

        assert final["workflow_type"] == "bugfix"
        assert final["services_involved"] == ["api", "database"]

    def test_multiple_spec_dirs(self, temp_dir):
        """Test managing requirements for multiple specs."""
        specs = ["001-feature", "002-bugfix", "003-refactor"]

        for i, spec_name in enumerate(specs):
            spec_dir = temp_dir / spec_name
            spec_dir.mkdir()

            requirements = create_requirements_from_task(f"Task for {spec_name}")
            save_requirements(spec_dir, requirements)

        # Load each
        for spec_name in specs:
            spec_dir = temp_dir / spec_name
            loaded = load_requirements(spec_dir)

            assert loaded is not None
            assert spec_name in loaded["task_description"]
