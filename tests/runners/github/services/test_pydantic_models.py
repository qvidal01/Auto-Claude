"""
Unit tests for pydantic model normalization functions.

Tests the normalize_category() and normalize_verdict() helper functions
that map common synonyms and formatting variations to valid schema values.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

# Add the backend directory to the path to allow direct module import
backend_path = Path(__file__).parent.parent.parent.parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))

# Import the normalization functions directly from the file
# This avoids importing the full module hierarchy which has complex dependencies
spec = importlib.util.spec_from_file_location(
    "pydantic_models",
    backend_path / "runners" / "github" / "services" / "pydantic_models.py"
)
pydantic_models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pydantic_models)

normalize_category = pydantic_models.normalize_category
normalize_verdict = pydantic_models.normalize_verdict


class TestNormalizeCategory:
    """Tests for normalize_category() function."""

    def test_synonyms_duplication_to_redundancy(self):
        """Test that 'duplication' synonym maps to 'redundancy'."""
        assert normalize_category("duplication") == "redundancy"

    def test_synonyms_code_duplication_to_redundancy(self):
        """Test that 'code duplication' synonym maps to 'redundancy'."""
        assert normalize_category("code duplication") == "redundancy"

    def test_synonyms_duplicate_to_redundancy(self):
        """Test that 'duplicate' synonym maps to 'redundancy'."""
        assert normalize_category("duplicate") == "redundancy"

    def test_synonyms_duplicated_to_redundancy(self):
        """Test that 'duplicated' synonym maps to 'redundancy'."""
        assert normalize_category("duplicated") == "redundancy"

    def test_synonyms_copy_to_redundancy(self):
        """Test that 'copy' synonym maps to 'redundancy'."""
        assert normalize_category("copy") == "redundancy"

    def test_synonyms_copied_to_redundancy(self):
        """Test that 'copied' synonym maps to 'redundancy'."""
        assert normalize_category("copied") == "redundancy"

    def test_case_insensitivity_security_uppercase(self):
        """Test that uppercase 'SECURITY' normalizes to 'security'."""
        assert normalize_category("SECURITY") == "security"

    def test_case_insensitivity_security_mixed(self):
        """Test that mixed case 'Security' normalizes to 'security'."""
        assert normalize_category("Security") == "security"

    def test_case_insensitivity_quality_uppercase(self):
        """Test that uppercase 'QUALITY' normalizes to 'quality'."""
        assert normalize_category("QUALITY") == "quality"

    def test_pass_through_valid_security(self):
        """Test that valid 'security' passes through unchanged."""
        assert normalize_category("security") == "security"

    def test_pass_through_valid_quality(self):
        """Test that valid 'quality' passes through unchanged."""
        assert normalize_category("quality") == "quality"

    def test_pass_through_valid_redundancy(self):
        """Test that valid 'redundancy' passes through unchanged."""
        assert normalize_category("redundancy") == "redundancy"

    def test_pass_through_valid_performance(self):
        """Test that valid 'performance' passes through unchanged."""
        assert normalize_category("performance") == "performance"

    def test_pass_through_valid_logic(self):
        """Test that valid 'logic' passes through unchanged."""
        assert normalize_category("logic") == "logic"

    def test_pass_through_valid_test(self):
        """Test that valid 'test' passes through unchanged."""
        assert normalize_category("test") == "test"

    def test_pass_through_valid_docs(self):
        """Test that valid 'docs' passes through unchanged."""
        assert normalize_category("docs") == "docs"

    def test_pass_through_valid_pattern(self):
        """Test that valid 'pattern' passes through unchanged."""
        assert normalize_category("pattern") == "pattern"

    def test_whitespace_handling_leading(self):
        """Test that leading whitespace is stripped."""
        assert normalize_category("  quality") == "quality"

    def test_whitespace_handling_trailing(self):
        """Test that trailing whitespace is stripped."""
        assert normalize_category("quality  ") == "quality"

    def test_whitespace_handling_both(self):
        """Test that both leading and trailing whitespace is stripped."""
        assert normalize_category("  quality  ") == "quality"

    def test_whitespace_handling_synonym(self):
        """Test whitespace stripping with synonym mapping."""
        assert normalize_category("  duplication  ") == "redundancy"

    def test_non_string_input_integer(self):
        """Test that non-string input (integer) returns unchanged."""
        assert normalize_category(42) == 42

    def test_non_string_input_none(self):
        """Test that non-string input (None) returns unchanged."""
        assert normalize_category(None) is None

    def test_non_string_input_list(self):
        """Test that non-string input (list) returns unchanged."""
        test_list = ["quality"]
        assert normalize_category(test_list) == test_list

    def test_performance_synonyms(self):
        """Test performance-related synonyms."""
        assert normalize_category("perf") == "performance"
        assert normalize_category("slow") == "performance"
        assert normalize_category("optimization") == "performance"

    def test_quality_synonyms(self):
        """Test quality-related synonyms."""
        assert normalize_category("code quality") == "quality"
        assert normalize_category("maintainability") == "quality"
        assert normalize_category("style") == "quality"
        assert normalize_category("formatting") == "quality"

    def test_logic_synonyms(self):
        """Test logic-related synonyms."""
        assert normalize_category("correctness") == "logic"
        assert normalize_category("bug") == "logic"

    def test_test_synonyms(self):
        """Test test-related synonyms."""
        assert normalize_category("testing") == "test"
        assert normalize_category("tests") == "test"

    def test_docs_synonyms(self):
        """Test documentation-related synonyms."""
        assert normalize_category("documentation") == "docs"
        assert normalize_category("doc") == "docs"

    def test_security_synonyms(self):
        """Test security-related synonyms."""
        assert normalize_category("sec") == "security"
        assert normalize_category("vulnerability") == "security"

    def test_unknown_category_passes_through(self):
        """Test that unknown category values pass through normalized."""
        assert normalize_category("unknown") == "unknown"

    def test_empty_string(self):
        """Test that empty string passes through as empty."""
        assert normalize_category("") == ""

    def test_whitespace_only_string(self):
        """Test that whitespace-only string normalizes to empty."""
        assert normalize_category("   ") == ""


class TestNormalizeVerdict:
    """Tests for normalize_verdict() function."""

    def test_space_to_underscore_needs_revision(self):
        """Test that 'NEEDS REVISION' converts spaces to underscores."""
        assert normalize_verdict("NEEDS REVISION") == "NEEDS_REVISION"

    def test_space_to_underscore_ready_to_merge(self):
        """Test that 'READY TO MERGE' converts spaces to underscores."""
        assert normalize_verdict("READY TO MERGE") == "READY_TO_MERGE"

    def test_space_to_underscore_merge_with_changes(self):
        """Test that 'MERGE WITH CHANGES' converts spaces to underscores."""
        assert normalize_verdict("MERGE WITH CHANGES") == "MERGE_WITH_CHANGES"

    def test_hyphen_to_underscore_needs_revision(self):
        """Test that 'NEEDS-REVISION' converts hyphens to underscores."""
        assert normalize_verdict("NEEDS-REVISION") == "NEEDS_REVISION"

    def test_hyphen_to_underscore_ready_to_merge(self):
        """Test that 'READY-TO-MERGE' converts hyphens to underscores."""
        assert normalize_verdict("READY-TO-MERGE") == "READY_TO_MERGE"

    def test_lowercase_conversion_needs_revision(self):
        """Test that lowercase 'needs_revision' converts to uppercase."""
        assert normalize_verdict("needs_revision") == "NEEDS_REVISION"

    def test_lowercase_conversion_ready_to_merge(self):
        """Test that lowercase 'ready_to_merge' converts to uppercase."""
        assert normalize_verdict("ready_to_merge") == "READY_TO_MERGE"

    def test_lowercase_conversion_blocked(self):
        """Test that lowercase 'blocked' converts to uppercase."""
        assert normalize_verdict("blocked") == "BLOCKED"

    def test_mixed_case_conversion(self):
        """Test that mixed case 'Needs_Revision' converts to uppercase."""
        assert normalize_verdict("Needs_Revision") == "NEEDS_REVISION"

    def test_synonym_ready_to_ready_to_merge(self):
        """Test that 'READY' synonym maps to 'READY_TO_MERGE'."""
        assert normalize_verdict("READY") == "READY_TO_MERGE"

    def test_synonym_ready_case_insensitive(self):
        """Test that 'ready' (lowercase) maps to 'READY_TO_MERGE'."""
        assert normalize_verdict("ready") == "READY_TO_MERGE"

    def test_synonym_merge_to_ready_to_merge(self):
        """Test that 'MERGE' synonym maps to 'READY_TO_MERGE'."""
        assert normalize_verdict("MERGE") == "READY_TO_MERGE"

    def test_synonym_needs_changes_to_needs_revision(self):
        """Test that 'NEEDS_CHANGES' synonym maps to 'NEEDS_REVISION'."""
        assert normalize_verdict("NEEDS_CHANGES") == "NEEDS_REVISION"

    def test_synonym_needs_changes_with_spaces(self):
        """Test that 'NEEDS CHANGES' (with spaces) maps to 'NEEDS_REVISION'."""
        assert normalize_verdict("NEEDS CHANGES") == "NEEDS_REVISION"

    def test_synonym_request_changes_to_needs_revision(self):
        """Test that 'REQUEST_CHANGES' synonym maps to 'NEEDS_REVISION'."""
        assert normalize_verdict("REQUEST_CHANGES") == "NEEDS_REVISION"

    def test_synonym_changes_requested_to_needs_revision(self):
        """Test that 'CHANGES_REQUESTED' synonym maps to 'NEEDS_REVISION'."""
        assert normalize_verdict("CHANGES_REQUESTED") == "NEEDS_REVISION"

    def test_synonym_approved_to_approve(self):
        """Test that 'APPROVED' synonym maps to 'APPROVE'."""
        assert normalize_verdict("APPROVED") == "APPROVE"

    def test_synonym_block_to_blocked(self):
        """Test that 'BLOCK' synonym maps to 'BLOCKED'."""
        assert normalize_verdict("BLOCK") == "BLOCKED"

    def test_synonym_reject_to_blocked(self):
        """Test that 'REJECT' synonym maps to 'BLOCKED'."""
        assert normalize_verdict("REJECT") == "BLOCKED"

    def test_pass_through_ready_to_merge(self):
        """Test that valid 'READY_TO_MERGE' passes through unchanged."""
        assert normalize_verdict("READY_TO_MERGE") == "READY_TO_MERGE"

    def test_pass_through_needs_revision(self):
        """Test that valid 'NEEDS_REVISION' passes through unchanged."""
        assert normalize_verdict("NEEDS_REVISION") == "NEEDS_REVISION"

    def test_pass_through_blocked(self):
        """Test that valid 'BLOCKED' passes through unchanged."""
        assert normalize_verdict("BLOCKED") == "BLOCKED"

    def test_pass_through_approve(self):
        """Test that valid 'APPROVE' passes through unchanged."""
        assert normalize_verdict("APPROVE") == "APPROVE"

    def test_pass_through_comment(self):
        """Test that valid 'COMMENT' passes through unchanged."""
        assert normalize_verdict("COMMENT") == "COMMENT"

    def test_pass_through_merge_with_changes(self):
        """Test that valid 'MERGE_WITH_CHANGES' passes through unchanged."""
        assert normalize_verdict("MERGE_WITH_CHANGES") == "MERGE_WITH_CHANGES"

    def test_whitespace_handling_leading(self):
        """Test that leading whitespace is stripped."""
        assert normalize_verdict("  BLOCKED") == "BLOCKED"

    def test_whitespace_handling_trailing(self):
        """Test that trailing whitespace is stripped."""
        assert normalize_verdict("BLOCKED  ") == "BLOCKED"

    def test_whitespace_handling_both(self):
        """Test that both leading and trailing whitespace is stripped."""
        assert normalize_verdict("  BLOCKED  ") == "BLOCKED"

    def test_whitespace_handling_with_synonym(self):
        """Test whitespace stripping with synonym mapping."""
        assert normalize_verdict("  ready  ") == "READY_TO_MERGE"

    def test_non_string_input_integer(self):
        """Test that non-string input (integer) returns unchanged."""
        assert normalize_verdict(42) == 42

    def test_non_string_input_none(self):
        """Test that non-string input (None) returns unchanged."""
        assert normalize_verdict(None) is None

    def test_non_string_input_list(self):
        """Test that non-string input (list) returns unchanged."""
        test_list = ["BLOCKED"]
        assert normalize_verdict(test_list) == test_list

    def test_combined_transformations_space_and_lowercase(self):
        """Test combined space replacement and case conversion."""
        assert normalize_verdict("needs revision") == "NEEDS_REVISION"

    def test_combined_transformations_hyphen_and_lowercase(self):
        """Test combined hyphen replacement and case conversion."""
        assert normalize_verdict("ready-to-merge") == "READY_TO_MERGE"

    def test_combined_transformations_mixed_separators(self):
        """Test mixed space and hyphen separators."""
        assert normalize_verdict("ready to-merge") == "READY_TO_MERGE"

    def test_empty_string(self):
        """Test that empty string passes through as empty."""
        assert normalize_verdict("") == ""

    def test_whitespace_only_string(self):
        """Test that whitespace-only string normalizes to empty."""
        assert normalize_verdict("   ") == ""

    def test_unknown_verdict_passes_through_normalized(self):
        """Test that unknown verdict values pass through normalized."""
        assert normalize_verdict("unknown") == "UNKNOWN"

    def test_multiple_spaces_to_single_underscore(self):
        """Test that multiple consecutive spaces become single underscore."""
        assert normalize_verdict("NEEDS  REVISION") == "NEEDS__REVISION"
