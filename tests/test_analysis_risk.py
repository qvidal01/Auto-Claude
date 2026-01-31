#!/usr/bin/env python3
"""
Tests for analysis.risk_classifier module.

Tests cover:
- Loading complexity assessments from JSON
- Risk level classification
- Validation requirement determination
- Test type recommendations
- Security scan requirements
- Staging deployment requirements
- Backward compatibility with old assessment formats
- Caching behavior
"""

import json
import sys
from pathlib import Path

import pytest

# Add backend directory to path
_backend_dir = Path(__file__).parent.parent / "apps" / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from analysis.risk_classifier import (
    RiskClassifier,
    RiskAssessment,
    ValidationRecommendations,
    ComplexityAnalysis,
    load_risk_assessment,
    get_validation_requirements,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def classifier():
    """Create a fresh RiskClassifier instance."""
    return RiskClassifier()


@pytest.fixture
def sample_assessment_data():
    """Sample complexity assessment data."""
    return {
        "complexity": "standard",
        "workflow_type": "feature",
        "confidence": 0.85,
        "reasoning": "Standard feature with moderate complexity",
        "analysis": {
            "scope": {
                "estimated_files": 5,
                "estimated_services": 2,
                "is_cross_cutting": False,
                "notes": "Moderate scope",
            },
            "integrations": {
                "external_services": ["stripe", "sendgrid"],
                "new_dependencies": ["stripe-python"],
                "research_needed": True,
                "notes": "Payment integration",
            },
            "infrastructure": {
                "docker_changes": False,
                "database_changes": True,
                "config_changes": True,
                "notes": "New database tables",
            },
            "knowledge": {
                "patterns_exist": True,
                "research_required": False,
                "unfamiliar_tech": [],
                "notes": "Familiar patterns",
            },
            "risk": {
                "level": "medium",
                "concerns": ["payment processing", "data integrity"],
                "notes": "Financial transactions",
            },
        },
        "recommended_phases": [
            "discovery",
            "requirements",
            "context",
            "spec_writing",
            "planning",
        ],
        "flags": {
            "needs_research": True,
            "needs_self_critique": False,
            "needs_infrastructure_setup": False,
        },
        "validation_recommendations": {
            "risk_level": "medium",
            "skip_validation": False,
            "minimal_mode": False,
            "test_types_required": ["unit", "integration"],
            "security_scan_required": True,
            "staging_deployment_required": True,
            "reasoning": "Payment processing requires thorough testing",
        },
        "created_at": "2024-01-15T10:30:00",
    }


@pytest.fixture
def simple_assessment_data():
    """Sample trivial complexity assessment."""
    return {
        "complexity": "simple",
        "workflow_type": "simple",
        "confidence": 0.95,
        "reasoning": "Simple text change",
        "analysis": {
            "scope": {
                "estimated_files": 1,
                "estimated_services": 1,
                "is_cross_cutting": False,
                "notes": "Single file change",
            },
            "integrations": {
                "external_services": [],
                "new_dependencies": [],
                "research_needed": False,
                "notes": "",
            },
            "infrastructure": {
                "docker_changes": False,
                "database_changes": False,
                "config_changes": False,
                "notes": "",
            },
            "knowledge": {
                "patterns_exist": True,
                "research_required": False,
                "unfamiliar_tech": [],
                "notes": "",
            },
            "risk": {
                "level": "low",
                "concerns": [],
                "notes": "",
            },
        },
        "recommended_phases": ["requirements", "spec_writing"],
        "flags": {
            "needs_research": False,
            "needs_self_critique": False,
            "needs_infrastructure_setup": False,
        },
        "validation_recommendations": {
            "risk_level": "trivial",
            "skip_validation": True,
            "minimal_mode": True,
            "test_types_required": [],
            "security_scan_required": False,
            "staging_deployment_required": False,
            "reasoning": "Trivial change - skip validation",
        },
    }


@pytest.fixture
def high_risk_assessment_data():
    """Sample high-risk complexity assessment."""
    return {
        "complexity": "complex",
        "workflow_type": "migration",
        "confidence": 0.75,
        "reasoning": "Complex database migration with high risk",
        "analysis": {
            "scope": {
                "estimated_files": 15,
                "estimated_services": 3,
                "is_cross_cutting": True,
                "notes": "Major refactoring",
            },
            "integrations": {
                "external_services": ["postgres", "redis"],
                "new_dependencies": [],
                "research_needed": False,
                "notes": "",
            },
            "infrastructure": {
                "docker_changes": True,
                "database_changes": True,
                "config_changes": True,
                "notes": "Schema migration",
            },
            "knowledge": {
                "patterns_exist": False,
                "research_required": True,
                "unfamiliar_tech": ["new-orm"],
                "notes": "New ORM approach",
            },
            "risk": {
                "level": "high",
                "concerns": [
                    "data loss",
                    "downtime",
                    "rollback complexity",
                    "security",
                ],
                "notes": "Critical system changes",
            },
        },
        "recommended_phases": [
            "discovery",
            "research",
            "requirements",
            "context",
            "spec_writing",
            "self_critique",
            "planning",
        ],
        "flags": {
            "needs_research": True,
            "needs_self_critique": True,
            "needs_infrastructure_setup": True,
        },
        "validation_recommendations": {
            "risk_level": "critical",
            "skip_validation": False,
            "minimal_mode": False,
            "test_types_required": ["unit", "integration", "e2e"],
            "security_scan_required": True,
            "staging_deployment_required": True,
            "reasoning": "Critical migration requires comprehensive validation",
        },
    }


# =============================================================================
# LOADING ASSESSMENTS
# =============================================================================


class TestLoadingAssessments:
    """Tests for loading complexity assessments from files."""

    def test_load_assessment_from_file(
        self, classifier, temp_dir, sample_assessment_data
    ):
        """Test loading assessment from complexity_assessment.json."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        assessment_file = spec_dir / "complexity_assessment.json"
        assessment_file.write_text(json.dumps(sample_assessment_data, indent=2))

        result = classifier.load_assessment(spec_dir)

        assert result is not None
        assert result.complexity == "standard"
        assert result.workflow_type == "feature"
        assert result.confidence == 0.85

    def test_load_nonexistent_assessment(self, classifier, temp_dir):
        """Test loading when assessment file doesn't exist."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()

        result = classifier.load_assessment(spec_dir)

        assert result is None

    def test_load_invalid_json(self, classifier, temp_dir):
        """Test loading assessment with invalid JSON."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        assessment_file = spec_dir / "complexity_assessment.json"
        assessment_file.write_text("{ invalid json }")

        result = classifier.load_assessment(spec_dir)

        assert result is None

    def test_caching(self, classifier, temp_dir, sample_assessment_data):
        """Test that assessments are cached."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        assessment_file = spec_dir / "complexity_assessment.json"
        assessment_file.write_text(json.dumps(sample_assessment_data, indent=2))

        # First load
        result1 = classifier.load_assessment(spec_dir)

        # Second load should return cached result
        result2 = classifier.load_assessment(spec_dir)

        assert result1 is result2

    def test_clear_cache(self, classifier, temp_dir, sample_assessment_data):
        """Test clearing the assessment cache."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        assessment_file = spec_dir / "complexity_assessment.json"
        assessment_file.write_text(json.dumps(sample_assessment_data, indent=2))

        result1 = classifier.load_assessment(spec_dir)
        classifier.clear_cache()
        result2 = classifier.load_assessment(spec_dir)

        # Should be different instances after cache clear
        assert result1 is not result2


# =============================================================================
# RISK CLASSIFICATION
# =============================================================================


class TestRiskClassification:
    """Tests for risk level classification."""

    def test_get_risk_level_medium(
        self, classifier, temp_dir, sample_assessment_data
    ):
        """Test getting medium risk level."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (spec_dir / "complexity_assessment.json").write_text(
            json.dumps(sample_assessment_data, indent=2)
        )

        risk_level = classifier.get_risk_level(spec_dir)

        assert risk_level == "medium"

    def test_get_risk_level_trivial(
        self, classifier, temp_dir, simple_assessment_data
    ):
        """Test getting trivial risk level."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (spec_dir / "complexity_assessment.json").write_text(
            json.dumps(simple_assessment_data, indent=2)
        )

        risk_level = classifier.get_risk_level(spec_dir)

        assert risk_level == "trivial"

    def test_get_risk_level_critical(
        self, classifier, temp_dir, high_risk_assessment_data
    ):
        """Test getting critical risk level."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (spec_dir / "complexity_assessment.json").write_text(
            json.dumps(high_risk_assessment_data, indent=2)
        )

        risk_level = classifier.get_risk_level(spec_dir)

        assert risk_level == "critical"

    def test_get_risk_level_default(self, classifier, temp_dir):
        """Test default risk level when assessment missing."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()

        risk_level = classifier.get_risk_level(spec_dir)

        assert risk_level == "medium"  # Default


# =============================================================================
# VALIDATION REQUIREMENTS
# =============================================================================


class TestValidationRequirements:
    """Tests for validation requirement determination."""

    def test_should_skip_validation_true(
        self, classifier, temp_dir, simple_assessment_data
    ):
        """Test skip validation for trivial changes."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (spec_dir / "complexity_assessment.json").write_text(
            json.dumps(simple_assessment_data, indent=2)
        )

        should_skip = classifier.should_skip_validation(spec_dir)

        assert should_skip is True

    def test_should_skip_validation_false(
        self, classifier, temp_dir, sample_assessment_data
    ):
        """Test don't skip validation for normal changes."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (spec_dir / "complexity_assessment.json").write_text(
            json.dumps(sample_assessment_data, indent=2)
        )

        should_skip = classifier.should_skip_validation(spec_dir)

        assert should_skip is False

    def test_should_use_minimal_mode_true(
        self, classifier, temp_dir, simple_assessment_data
    ):
        """Test minimal mode for simple changes."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (spec_dir / "complexity_assessment.json").write_text(
            json.dumps(simple_assessment_data, indent=2)
        )

        minimal = classifier.should_use_minimal_mode(spec_dir)

        assert minimal is True

    def test_should_use_minimal_mode_false(
        self, classifier, temp_dir, sample_assessment_data
    ):
        """Test no minimal mode for standard changes."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (spec_dir / "complexity_assessment.json").write_text(
            json.dumps(sample_assessment_data, indent=2)
        )

        minimal = classifier.should_use_minimal_mode(spec_dir)

        assert minimal is False

    def test_get_required_test_types_comprehensive(
        self, classifier, temp_dir, high_risk_assessment_data
    ):
        """Test comprehensive test types for high risk."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (spec_dir / "complexity_assessment.json").write_text(
            json.dumps(high_risk_assessment_data, indent=2)
        )

        test_types = classifier.get_required_test_types(spec_dir)

        assert "unit" in test_types
        assert "integration" in test_types
        assert "e2e" in test_types

    def test_get_required_test_types_minimal(
        self, classifier, temp_dir, simple_assessment_data
    ):
        """Test minimal test types for trivial changes."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (spec_dir / "complexity_assessment.json").write_text(
            json.dumps(simple_assessment_data, indent=2)
        )

        test_types = classifier.get_required_test_types(spec_dir)

        assert test_types == []  # Trivial changes skip tests

    def test_get_required_test_types_default(self, classifier, temp_dir):
        """Test default test types when assessment missing."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()

        test_types = classifier.get_required_test_types(spec_dir)

        assert test_types == ["unit"]  # Default

    def test_requires_security_scan_true(
        self, classifier, temp_dir, sample_assessment_data
    ):
        """Test security scan required for medium+ risk."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (spec_dir / "complexity_assessment.json").write_text(
            json.dumps(sample_assessment_data, indent=2)
        )

        requires_scan = classifier.requires_security_scan(spec_dir)

        assert requires_scan is True

    def test_requires_security_scan_false(
        self, classifier, temp_dir, simple_assessment_data
    ):
        """Test no security scan for trivial changes."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (spec_dir / "complexity_assessment.json").write_text(
            json.dumps(simple_assessment_data, indent=2)
        )

        requires_scan = classifier.requires_security_scan(spec_dir)

        assert requires_scan is False

    def test_requires_staging_deployment_true(
        self, classifier, temp_dir, sample_assessment_data
    ):
        """Test staging deployment required for database changes."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (spec_dir / "complexity_assessment.json").write_text(
            json.dumps(sample_assessment_data, indent=2)
        )

        requires_staging = classifier.requires_staging_deployment(spec_dir)

        assert requires_staging is True

    def test_requires_staging_deployment_false(
        self, classifier, temp_dir, simple_assessment_data
    ):
        """Test no staging deployment for simple changes."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (spec_dir / "complexity_assessment.json").write_text(
            json.dumps(simple_assessment_data, indent=2)
        )

        requires_staging = classifier.requires_staging_deployment(spec_dir)

        assert requires_staging is False


# =============================================================================
# VALIDATION SUMMARY
# =============================================================================


class TestValidationSummary:
    """Tests for validation summary generation."""

    def test_get_validation_summary(
        self, classifier, temp_dir, sample_assessment_data
    ):
        """Test getting complete validation summary."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (spec_dir / "complexity_assessment.json").write_text(
            json.dumps(sample_assessment_data, indent=2)
        )

        summary = classifier.get_validation_summary(spec_dir)

        assert summary["risk_level"] == "medium"
        assert summary["complexity"] == "standard"
        assert summary["skip_validation"] is False
        assert summary["minimal_mode"] is False
        assert "unit" in summary["test_types"]
        assert "integration" in summary["test_types"]
        assert summary["security_scan"] is True
        assert summary["staging_deployment"] is True
        assert summary["confidence"] == 0.85
        assert "reasoning" in summary

    def test_validation_summary_missing_assessment(self, classifier, temp_dir):
        """Test validation summary when assessment is missing."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()

        summary = classifier.get_validation_summary(spec_dir)

        assert summary["risk_level"] == "unknown"
        assert summary["complexity"] == "unknown"
        assert summary["skip_validation"] is False
        assert summary["test_types"] == ["unit"]
        assert summary["confidence"] == 0.0


# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================


class TestBackwardCompatibility:
    """Tests for backward compatibility with old assessment formats."""

    def test_load_old_format_without_validation_recommendations(
        self, classifier, temp_dir
    ):
        """Test loading old assessment format without validation_recommendations."""
        old_format_data = {
            "complexity": "standard",
            "workflow_type": "feature",
            "confidence": 0.8,
            "reasoning": "Standard feature",
            "analysis": {
                "scope": {
                    "estimated_files": 3,
                    "estimated_services": 1,
                    "is_cross_cutting": False,
                    "notes": "",
                },
                "integrations": {
                    "external_services": [],
                    "new_dependencies": [],
                    "research_needed": False,
                    "notes": "",
                },
                "infrastructure": {
                    "docker_changes": False,
                    "database_changes": True,
                    "config_changes": False,
                    "notes": "",
                },
                "knowledge": {
                    "patterns_exist": True,
                    "research_required": False,
                    "unfamiliar_tech": [],
                    "notes": "",
                },
                "risk": {
                    "level": "medium",
                    "concerns": ["database migration"],
                    "notes": "",
                },
            },
            "recommended_phases": [],
            "flags": {
                "needs_research": False,
                "needs_self_critique": False,
                "needs_infrastructure_setup": False,
            },
            # No validation_recommendations section
        }

        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (spec_dir / "complexity_assessment.json").write_text(
            json.dumps(old_format_data, indent=2)
        )

        result = classifier.load_assessment(spec_dir)

        # Should infer validation recommendations
        assert result is not None
        assert result.validation.risk_level == "medium"
        assert "unit" in result.validation.test_types_required
        assert "integration" in result.validation.test_types_required

    def test_infer_security_scan_from_concerns(self, classifier, temp_dir):
        """Test inferring security scan requirement from risk concerns."""
        data_with_security_concern = {
            "complexity": "standard",
            "workflow_type": "feature",
            "confidence": 0.8,
            "reasoning": "Auth feature",
            "analysis": {
                "scope": {
                    "estimated_files": 2,
                    "estimated_services": 1,
                    "is_cross_cutting": False,
                    "notes": "",
                },
                "integrations": {
                    "external_services": [],
                    "new_dependencies": [],
                    "research_needed": False,
                    "notes": "",
                },
                "infrastructure": {
                    "docker_changes": False,
                    "database_changes": False,
                    "config_changes": False,
                    "notes": "",
                },
                "knowledge": {
                    "patterns_exist": True,
                    "research_required": False,
                    "unfamiliar_tech": [],
                    "notes": "",
                },
                "risk": {
                    "level": "low",
                    "concerns": ["security", "authentication"],
                    "notes": "Auth changes",
                },
            },
            "recommended_phases": [],
            "flags": {
                "needs_research": False,
                "needs_self_critique": False,
                "needs_infrastructure_setup": False,
            },
        }

        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (spec_dir / "complexity_assessment.json").write_text(
            json.dumps(data_with_security_concern, indent=2)
        )

        result = classifier.load_assessment(spec_dir)

        # Should infer security scan needed due to security concerns
        assert result.validation.security_scan_required is True


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_load_risk_assessment(self, temp_dir, sample_assessment_data):
        """Test load_risk_assessment convenience function."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (spec_dir / "complexity_assessment.json").write_text(
            json.dumps(sample_assessment_data, indent=2)
        )

        result = load_risk_assessment(spec_dir)

        assert result is not None
        assert result.complexity == "standard"

    def test_get_validation_requirements(self, temp_dir, sample_assessment_data):
        """Test get_validation_requirements convenience function."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (spec_dir / "complexity_assessment.json").write_text(
            json.dumps(sample_assessment_data, indent=2)
        )

        requirements = get_validation_requirements(spec_dir)

        assert requirements["risk_level"] == "medium"
        assert requirements["complexity"] == "standard"
        assert "test_types" in requirements


# =============================================================================
# DATA CLASS PROPERTIES
# =============================================================================


class TestDataClassProperties:
    """Tests for data class properties and methods."""

    def test_risk_assessment_risk_level_property(
        self, classifier, temp_dir, sample_assessment_data
    ):
        """Test risk_level property on RiskAssessment."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (spec_dir / "complexity_assessment.json").write_text(
            json.dumps(sample_assessment_data, indent=2)
        )

        assessment = classifier.load_assessment(spec_dir)

        # Should access validation.risk_level via property
        assert assessment.risk_level == "medium"
        assert assessment.risk_level == assessment.validation.risk_level

    def test_get_complexity(self, classifier, temp_dir, sample_assessment_data):
        """Test getting complexity level."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()
        (spec_dir / "complexity_assessment.json").write_text(
            json.dumps(sample_assessment_data, indent=2)
        )

        complexity = classifier.get_complexity(spec_dir)

        assert complexity == "standard"

    def test_get_complexity_default(self, classifier, temp_dir):
        """Test default complexity when assessment missing."""
        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()

        complexity = classifier.get_complexity(spec_dir)

        assert complexity == "standard"
