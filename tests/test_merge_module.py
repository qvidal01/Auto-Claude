"""
Tests for the merge module
===========================

Tests covering merge/types.py and merge/compatibility_rules.py
"""

import pytest
from datetime import datetime
from merge.types import (
    ChangeType,
    ConflictSeverity,
    MergeStrategy,
    MergeDecision,
    SemanticChange,
    FileAnalysis,
    ConflictRegion,
    TaskSnapshot,
    FileEvolution,
    MergeResult,
    compute_content_hash,
    sanitize_path_for_storage,
)
from merge.compatibility_rules import (
    CompatibilityRule,
    build_default_rules,
    index_rules,
)


# =============================================================================
# ChangeType Enum Tests
# =============================================================================

class TestChangeType:
    """Tests for ChangeType enum."""

    def test_import_change_types(self):
        """Test import-related change types."""
        assert ChangeType.ADD_IMPORT.value == "add_import"
        assert ChangeType.REMOVE_IMPORT.value == "remove_import"
        assert ChangeType.MODIFY_IMPORT.value == "modify_import"

    def test_function_change_types(self):
        """Test function-related change types."""
        assert ChangeType.ADD_FUNCTION.value == "add_function"
        assert ChangeType.REMOVE_FUNCTION.value == "remove_function"
        assert ChangeType.MODIFY_FUNCTION.value == "modify_function"

    def test_react_change_types(self):
        """Test React-specific change types."""
        assert ChangeType.ADD_HOOK_CALL.value == "add_hook_call"
        assert ChangeType.WRAP_JSX.value == "wrap_jsx"
        assert ChangeType.MODIFY_JSX_PROPS.value == "modify_jsx_props"


# =============================================================================
# ConflictSeverity Enum Tests
# =============================================================================

class TestConflictSeverity:
    """Tests for ConflictSeverity enum."""

    def test_severity_levels(self):
        """Test all severity levels exist."""
        assert ConflictSeverity.NONE.value == "none"
        assert ConflictSeverity.LOW.value == "low"
        assert ConflictSeverity.MEDIUM.value == "medium"
        assert ConflictSeverity.HIGH.value == "high"
        assert ConflictSeverity.CRITICAL.value == "critical"


# =============================================================================
# MergeStrategy Enum Tests
# =============================================================================

class TestMergeStrategy:
    """Tests for MergeStrategy enum."""

    def test_import_strategies(self):
        """Test import merge strategies."""
        assert MergeStrategy.COMBINE_IMPORTS.value == "combine_imports"

    def test_function_strategies(self):
        """Test function merge strategies."""
        assert MergeStrategy.APPEND_FUNCTIONS.value == "append_functions"
        assert MergeStrategy.HOOKS_FIRST.value == "hooks_first"

    def test_fallback_strategies(self):
        """Test fallback strategies."""
        assert MergeStrategy.AI_REQUIRED.value == "ai_required"
        assert MergeStrategy.HUMAN_REQUIRED.value == "human_required"


# =============================================================================
# SemanticChange Tests
# =============================================================================

class TestSemanticChange:
    """Tests for SemanticChange dataclass."""

    @pytest.fixture
    def sample_change(self):
        return SemanticChange(
            change_type=ChangeType.ADD_FUNCTION,
            target="handleLogin",
            location="function:App",
            line_start=10,
            line_end=20,
            content_before=None,
            content_after="function handleLogin() { ... }",
            metadata={"async": True}
        )

    def test_semantic_change_creation(self, sample_change):
        """Test SemanticChange creation."""
        assert sample_change.change_type == ChangeType.ADD_FUNCTION
        assert sample_change.target == "handleLogin"
        assert sample_change.line_start == 10
        assert sample_change.line_end == 20

    def test_to_dict(self, sample_change):
        """Test converting to dictionary."""
        result = sample_change.to_dict()

        assert result["change_type"] == "add_function"
        assert result["target"] == "handleLogin"
        assert result["location"] == "function:App"
        assert result["metadata"]["async"] is True

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "change_type": "modify_function",
            "target": "updateUser",
            "location": "file_top",
            "line_start": 5,
            "line_end": 15,
            "content_before": "old code",
            "content_after": "new code",
            "metadata": {}
        }
        change = SemanticChange.from_dict(data)

        assert change.change_type == ChangeType.MODIFY_FUNCTION
        assert change.target == "updateUser"

    def test_overlaps_with_same_location(self):
        """Test overlap detection with same location."""
        change1 = SemanticChange(
            change_type=ChangeType.ADD_FUNCTION,
            target="func1",
            location="function:App",
            line_start=10,
            line_end=20
        )
        change2 = SemanticChange(
            change_type=ChangeType.MODIFY_FUNCTION,
            target="func2",
            location="function:App",
            line_start=25,
            line_end=35
        )

        assert change1.overlaps_with(change2) is True

    def test_overlaps_with_line_overlap(self):
        """Test overlap detection with overlapping lines."""
        change1 = SemanticChange(
            change_type=ChangeType.ADD_FUNCTION,
            target="func1",
            location="location1",
            line_start=10,
            line_end=20
        )
        change2 = SemanticChange(
            change_type=ChangeType.MODIFY_FUNCTION,
            target="func2",
            location="location2",
            line_start=15,
            line_end=25
        )

        assert change1.overlaps_with(change2) is True

    def test_no_overlap(self):
        """Test no overlap detection."""
        change1 = SemanticChange(
            change_type=ChangeType.ADD_FUNCTION,
            target="func1",
            location="location1",
            line_start=10,
            line_end=20
        )
        change2 = SemanticChange(
            change_type=ChangeType.MODIFY_FUNCTION,
            target="func2",
            location="location2",
            line_start=30,
            line_end=40
        )

        assert change1.overlaps_with(change2) is False

    def test_is_additive_true(self):
        """Test is_additive for additive change types."""
        additive_types = [
            ChangeType.ADD_IMPORT,
            ChangeType.ADD_FUNCTION,
            ChangeType.ADD_HOOK_CALL,
            ChangeType.ADD_CLASS,
            ChangeType.ADD_METHOD,
        ]

        for ct in additive_types:
            change = SemanticChange(
                change_type=ct,
                target="test",
                location="test",
                line_start=1,
                line_end=10
            )
            assert change.is_additive is True, f"{ct} should be additive"

    def test_is_additive_false(self):
        """Test is_additive for non-additive change types."""
        non_additive = [
            ChangeType.MODIFY_FUNCTION,
            ChangeType.REMOVE_FUNCTION,
            ChangeType.MODIFY_IMPORT,
        ]

        for ct in non_additive:
            change = SemanticChange(
                change_type=ct,
                target="test",
                location="test",
                line_start=1,
                line_end=10
            )
            assert change.is_additive is False, f"{ct} should not be additive"


# =============================================================================
# FileAnalysis Tests
# =============================================================================

class TestFileAnalysis:
    """Tests for FileAnalysis dataclass."""

    def test_file_analysis_creation(self):
        """Test FileAnalysis creation."""
        analysis = FileAnalysis(
            file_path="src/auth.py",
            functions_modified={"login", "logout"},
            functions_added={"reset_password"},
            imports_added={"jwt"},
            total_lines_changed=50
        )

        assert analysis.file_path == "src/auth.py"
        assert "login" in analysis.functions_modified
        assert "reset_password" in analysis.functions_added

    def test_file_analysis_to_dict(self):
        """Test FileAnalysis to_dict."""
        change = SemanticChange(
            change_type=ChangeType.ADD_FUNCTION,
            target="test",
            location="top",
            line_start=1,
            line_end=10
        )
        analysis = FileAnalysis(
            file_path="test.py",
            changes=[change],
            functions_added={"test"}
        )

        result = analysis.to_dict()
        assert result["file_path"] == "test.py"
        assert len(result["changes"]) == 1
        assert "test" in result["functions_added"]

    def test_get_changes_at_location(self):
        """Test getting changes at specific location."""
        change1 = SemanticChange(
            change_type=ChangeType.ADD_FUNCTION,
            target="func1",
            location="function:App",
            line_start=1,
            line_end=10
        )
        change2 = SemanticChange(
            change_type=ChangeType.MODIFY_FUNCTION,
            target="func2",
            location="function:Other",
            line_start=20,
            line_end=30
        )

        analysis = FileAnalysis(
            file_path="test.py",
            changes=[change1, change2]
        )

        result = analysis.get_changes_at_location("function:App")
        assert len(result) == 1
        assert result[0].target == "func1"

    def test_is_additive_only_true(self):
        """Test is_additive_only when all changes are additive."""
        changes = [
            SemanticChange(
                change_type=ChangeType.ADD_FUNCTION,
                target="f1",
                location="top",
                line_start=1,
                line_end=10
            ),
            SemanticChange(
                change_type=ChangeType.ADD_IMPORT,
                target="i1",
                location="top",
                line_start=1,
                line_end=1
            )
        ]

        analysis = FileAnalysis(file_path="test.py", changes=changes)
        assert analysis.is_additive_only is True

    def test_is_additive_only_false(self):
        """Test is_additive_only when some changes are modifications."""
        changes = [
            SemanticChange(
                change_type=ChangeType.ADD_FUNCTION,
                target="f1",
                location="top",
                line_start=1,
                line_end=10
            ),
            SemanticChange(
                change_type=ChangeType.MODIFY_FUNCTION,
                target="f2",
                location="top",
                line_start=20,
                line_end=30
            )
        ]

        analysis = FileAnalysis(file_path="test.py", changes=changes)
        assert analysis.is_additive_only is False

    def test_locations_changed(self):
        """Test getting unique locations changed."""
        changes = [
            SemanticChange(
                change_type=ChangeType.ADD_FUNCTION,
                target="f1",
                location="location1",
                line_start=1,
                line_end=10
            ),
            SemanticChange(
                change_type=ChangeType.ADD_FUNCTION,
                target="f2",
                location="location2",
                line_start=20,
                line_end=30
            ),
            SemanticChange(
                change_type=ChangeType.MODIFY_FUNCTION,
                target="f3",
                location="location1",
                line_start=40,
                line_end=50
            )
        ]

        analysis = FileAnalysis(file_path="test.py", changes=changes)
        locations = analysis.locations_changed

        assert len(locations) == 2
        assert "location1" in locations
        assert "location2" in locations


# =============================================================================
# ConflictRegion Tests
# =============================================================================

class TestConflictRegion:
    """Tests for ConflictRegion dataclass."""

    def test_conflict_region_creation(self):
        """Test ConflictRegion creation."""
        region = ConflictRegion(
            file_path="src/auth.py",
            location="function:login",
            tasks_involved=["task-1", "task-2"],
            change_types=[ChangeType.MODIFY_FUNCTION, ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.MEDIUM,
            can_auto_merge=False,
            merge_strategy=MergeStrategy.AI_REQUIRED,
            reason="Both tasks modified the same function"
        )

        assert region.file_path == "src/auth.py"
        assert len(region.tasks_involved) == 2
        assert region.severity == ConflictSeverity.MEDIUM

    def test_conflict_region_to_dict(self):
        """Test ConflictRegion to_dict."""
        region = ConflictRegion(
            file_path="test.py",
            location="function:test",
            tasks_involved=["task-1"],
            change_types=[ChangeType.ADD_FUNCTION],
            severity=ConflictSeverity.LOW,
            can_auto_merge=True,
            merge_strategy=MergeStrategy.APPEND_FUNCTIONS
        )

        result = region.to_dict()
        assert result["file_path"] == "test.py"
        assert result["severity"] == "low"
        assert result["can_auto_merge"] is True

    def test_conflict_region_from_dict(self):
        """Test ConflictRegion from_dict."""
        data = {
            "file_path": "test.py",
            "location": "top",
            "tasks_involved": ["t1", "t2"],
            "change_types": ["add_function", "modify_function"],
            "severity": "high",
            "can_auto_merge": False,
            "merge_strategy": "ai_required",
            "reason": "Conflict"
        }

        region = ConflictRegion.from_dict(data)
        assert region.severity == ConflictSeverity.HIGH
        assert ChangeType.ADD_FUNCTION in region.change_types


# =============================================================================
# TaskSnapshot Tests
# =============================================================================

class TestTaskSnapshot:
    """Tests for TaskSnapshot dataclass."""

    def test_task_snapshot_creation(self):
        """Test TaskSnapshot creation."""
        snapshot = TaskSnapshot(
            task_id="task-123",
            task_intent="Add login feature",
            started_at=datetime(2024, 1, 1, 12, 0, 0),
            content_hash_before="abc123",
            content_hash_after="def456"
        )

        assert snapshot.task_id == "task-123"
        assert snapshot.task_intent == "Add login feature"

    def test_has_modifications_with_changes(self):
        """Test has_modifications with semantic changes."""
        change = SemanticChange(
            change_type=ChangeType.ADD_FUNCTION,
            target="test",
            location="top",
            line_start=1,
            line_end=10
        )
        snapshot = TaskSnapshot(
            task_id="task-1",
            task_intent="Add feature",
            started_at=datetime.now(),
            semantic_changes=[change]
        )

        assert snapshot.has_modifications is True

    def test_has_modifications_with_hash_change(self):
        """Test has_modifications with content hash change."""
        snapshot = TaskSnapshot(
            task_id="task-1",
            task_intent="Modify feature",
            started_at=datetime.now(),
            content_hash_before="hash1",
            content_hash_after="hash2"
        )

        assert snapshot.has_modifications is True

    def test_has_modifications_new_file(self):
        """Test has_modifications for new file."""
        snapshot = TaskSnapshot(
            task_id="task-1",
            task_intent="Create file",
            started_at=datetime.now(),
            content_hash_before="",
            content_hash_after="newhash"
        )

        assert snapshot.has_modifications is True

    def test_has_modifications_no_change(self):
        """Test has_modifications with no changes."""
        snapshot = TaskSnapshot(
            task_id="task-1",
            task_intent="No op",
            started_at=datetime.now(),
            content_hash_before="same",
            content_hash_after="same"
        )

        assert snapshot.has_modifications is False


# =============================================================================
# FileEvolution Tests
# =============================================================================

class TestFileEvolution:
    """Tests for FileEvolution dataclass."""

    def test_file_evolution_creation(self):
        """Test FileEvolution creation."""
        evolution = FileEvolution(
            file_path="src/auth.py",
            baseline_commit="abc123",
            baseline_captured_at=datetime.now(),
            baseline_content_hash="hash123",
            baseline_snapshot_path="/snapshots/auth.py"
        )

        assert evolution.file_path == "src/auth.py"
        assert evolution.baseline_commit == "abc123"

    def test_add_task_snapshot(self):
        """Test adding task snapshots."""
        evolution = FileEvolution(
            file_path="test.py",
            baseline_commit="abc",
            baseline_captured_at=datetime(2024, 1, 1),
            baseline_content_hash="hash",
            baseline_snapshot_path="/path"
        )

        snapshot1 = TaskSnapshot(
            task_id="task-1",
            task_intent="First",
            started_at=datetime(2024, 1, 1, 12, 0)
        )
        snapshot2 = TaskSnapshot(
            task_id="task-2",
            task_intent="Second",
            started_at=datetime(2024, 1, 1, 13, 0)
        )

        evolution.add_task_snapshot(snapshot2)
        evolution.add_task_snapshot(snapshot1)

        # Should be sorted by start time
        assert len(evolution.task_snapshots) == 2
        assert evolution.task_snapshots[0].task_id == "task-1"
        assert evolution.task_snapshots[1].task_id == "task-2"

    def test_get_task_snapshot(self):
        """Test getting specific task snapshot."""
        evolution = FileEvolution(
            file_path="test.py",
            baseline_commit="abc",
            baseline_captured_at=datetime.now(),
            baseline_content_hash="hash",
            baseline_snapshot_path="/path"
        )

        snapshot = TaskSnapshot(
            task_id="task-123",
            task_intent="Test",
            started_at=datetime.now()
        )
        evolution.add_task_snapshot(snapshot)

        result = evolution.get_task_snapshot("task-123")
        assert result is not None
        assert result.task_id == "task-123"

        result = evolution.get_task_snapshot("nonexistent")
        assert result is None

    def test_tasks_involved(self):
        """Test getting list of involved tasks."""
        evolution = FileEvolution(
            file_path="test.py",
            baseline_commit="abc",
            baseline_captured_at=datetime.now(),
            baseline_content_hash="hash",
            baseline_snapshot_path="/path"
        )

        for i in range(3):
            snapshot = TaskSnapshot(
                task_id=f"task-{i}",
                task_intent=f"Task {i}",
                started_at=datetime(2024, 1, 1, i)
            )
            evolution.add_task_snapshot(snapshot)

        tasks = evolution.tasks_involved
        assert len(tasks) == 3
        assert "task-0" in tasks
        assert "task-1" in tasks
        assert "task-2" in tasks


# =============================================================================
# MergeResult Tests
# =============================================================================

class TestMergeResult:
    """Tests for MergeResult dataclass."""

    def test_merge_result_success(self):
        """Test successful merge result."""
        result = MergeResult(
            decision=MergeDecision.AUTO_MERGED,
            file_path="test.py",
            merged_content="merged code",
            explanation="Successfully merged imports"
        )

        assert result.success is True
        assert result.needs_human_review is False

    def test_merge_result_needs_review(self):
        """Test merge result needing review."""
        conflict = ConflictRegion(
            file_path="test.py",
            location="function:test",
            tasks_involved=["t1", "t2"],
            change_types=[ChangeType.MODIFY_FUNCTION, ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.HIGH,
            can_auto_merge=False
        )

        result = MergeResult(
            decision=MergeDecision.NEEDS_HUMAN_REVIEW,
            file_path="test.py",
            conflicts_remaining=[conflict]
        )

        assert result.success is False
        assert result.needs_human_review is True

    def test_merge_result_to_dict(self):
        """Test MergeResult to_dict."""
        result = MergeResult(
            decision=MergeDecision.AI_MERGED,
            file_path="test.py",
            merged_content="code",
            ai_calls_made=2,
            tokens_used=1500
        )

        data = result.to_dict()
        assert data["decision"] == "ai_merged"
        assert data["ai_calls_made"] == 2
        assert data["tokens_used"] == 1500


# =============================================================================
# Utility Function Tests
# =============================================================================

class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_compute_content_hash(self):
        """Test content hash computation."""
        content = "test content"
        hash1 = compute_content_hash(content)
        hash2 = compute_content_hash(content)

        assert hash1 == hash2
        assert len(hash1) == 16

    def test_compute_content_hash_different(self):
        """Test content hash is different for different content."""
        hash1 = compute_content_hash("content 1")
        hash2 = compute_content_hash("content 2")

        assert hash1 != hash2

    def test_sanitize_path_for_storage(self):
        """Test path sanitization."""
        path = "src/auth/login.py"
        result = sanitize_path_for_storage(path)

        assert "/" not in result
        assert "." not in result
        assert result == "src_auth_login_py"

    def test_sanitize_path_windows(self):
        """Test path sanitization for Windows paths."""
        path = "src\\auth\\login.py"
        result = sanitize_path_for_storage(path)

        assert "\\" not in result


# =============================================================================
# CompatibilityRule Tests
# =============================================================================

class TestCompatibilityRule:
    """Tests for CompatibilityRule dataclass."""

    def test_rule_creation(self):
        """Test CompatibilityRule creation."""
        rule = CompatibilityRule(
            change_type_a=ChangeType.ADD_IMPORT,
            change_type_b=ChangeType.ADD_IMPORT,
            compatible=True,
            strategy=MergeStrategy.COMBINE_IMPORTS,
            reason="Adding imports is compatible"
        )

        assert rule.compatible is True
        assert rule.bidirectional is True

    def test_rule_non_bidirectional(self):
        """Test non-bidirectional rule."""
        rule = CompatibilityRule(
            change_type_a=ChangeType.ADD_FUNCTION,
            change_type_b=ChangeType.REMOVE_FUNCTION,
            compatible=False,
            bidirectional=False
        )

        assert rule.bidirectional is False


# =============================================================================
# build_default_rules Tests
# =============================================================================

class TestBuildDefaultRules:
    """Tests for build_default_rules function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        rules = build_default_rules()
        assert isinstance(rules, list)
        assert len(rules) > 0

    def test_all_rules_are_compatibility_rules(self):
        """Test that all items are CompatibilityRule instances."""
        rules = build_default_rules()
        for rule in rules:
            assert isinstance(rule, CompatibilityRule)

    def test_import_rules_exist(self):
        """Test that import-related rules exist."""
        rules = build_default_rules()
        import_rules = [r for r in rules if r.change_type_a == ChangeType.ADD_IMPORT]
        assert len(import_rules) > 0

    def test_function_rules_exist(self):
        """Test that function-related rules exist."""
        rules = build_default_rules()
        func_rules = [r for r in rules if r.change_type_a == ChangeType.ADD_FUNCTION]
        assert len(func_rules) > 0

    def test_hook_rules_exist(self):
        """Test that React hook rules exist."""
        rules = build_default_rules()
        hook_rules = [r for r in rules if r.change_type_a == ChangeType.ADD_HOOK_CALL]
        assert len(hook_rules) > 0


# =============================================================================
# index_rules Tests
# =============================================================================

class TestIndexRules:
    """Tests for index_rules function."""

    def test_creates_index(self):
        """Test that index is created."""
        rules = build_default_rules()
        index = index_rules(rules)

        assert isinstance(index, dict)
        assert len(index) > 0

    def test_bidirectional_rules_indexed_both_ways(self):
        """Test that bidirectional rules are indexed both ways."""
        rule = CompatibilityRule(
            change_type_a=ChangeType.ADD_FUNCTION,
            change_type_b=ChangeType.MODIFY_FUNCTION,
            compatible=True,
            bidirectional=True
        )

        index = index_rules([rule])

        assert (ChangeType.ADD_FUNCTION, ChangeType.MODIFY_FUNCTION) in index
        assert (ChangeType.MODIFY_FUNCTION, ChangeType.ADD_FUNCTION) in index

    def test_non_bidirectional_rules_indexed_one_way(self):
        """Test that non-bidirectional rules are indexed one way."""
        rule = CompatibilityRule(
            change_type_a=ChangeType.ADD_FUNCTION,
            change_type_b=ChangeType.REMOVE_FUNCTION,
            compatible=False,
            bidirectional=False
        )

        index = index_rules([rule])

        assert (ChangeType.ADD_FUNCTION, ChangeType.REMOVE_FUNCTION) in index
        assert (ChangeType.REMOVE_FUNCTION, ChangeType.ADD_FUNCTION) not in index

    def test_same_type_rules_not_duplicated(self):
        """Test that same-type rules are not duplicated."""
        rule = CompatibilityRule(
            change_type_a=ChangeType.ADD_IMPORT,
            change_type_b=ChangeType.ADD_IMPORT,
            compatible=True,
            bidirectional=True
        )

        index = index_rules([rule])

        # Should only have one entry since a==b
        assert len(index) == 1
        assert (ChangeType.ADD_IMPORT, ChangeType.ADD_IMPORT) in index


# =============================================================================
# Integration Tests
# =============================================================================

class TestMergeIntegration:
    """Integration tests for merge module."""

    def test_full_workflow(self):
        """Test complete merge workflow with types."""
        # Create changes
        change1 = SemanticChange(
            change_type=ChangeType.ADD_IMPORT,
            target="jwt",
            location="file_top",
            line_start=1,
            line_end=1,
            content_after="import jwt"
        )
        change2 = SemanticChange(
            change_type=ChangeType.ADD_FUNCTION,
            target="verify_token",
            location="file_body",
            line_start=10,
            line_end=20,
            content_after="def verify_token(): ..."
        )

        # Create file analysis
        analysis = FileAnalysis(
            file_path="src/auth.py",
            changes=[change1, change2],
            imports_added={"jwt"},
            functions_added={"verify_token"}
        )

        assert analysis.is_additive_only is True

        # Create task snapshot
        snapshot = TaskSnapshot(
            task_id="auth-task",
            task_intent="Add JWT authentication",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            semantic_changes=[change1, change2]
        )

        assert snapshot.has_modifications is True

        # Build rules and check compatibility
        rules = build_default_rules()
        index = index_rules(rules)

        key = (ChangeType.ADD_IMPORT, ChangeType.ADD_FUNCTION)
        # Note: This combination may not have a direct rule
        # but the test validates the workflow

    def test_conflict_detection_workflow(self):
        """Test conflict detection between two tasks."""
        # Two tasks modifying the same function
        change1 = SemanticChange(
            change_type=ChangeType.MODIFY_FUNCTION,
            target="login",
            location="function:login",
            line_start=10,
            line_end=30
        )
        change2 = SemanticChange(
            change_type=ChangeType.MODIFY_FUNCTION,
            target="login",
            location="function:login",
            line_start=15,
            line_end=25
        )

        # Check overlap
        assert change1.overlaps_with(change2) is True

        # Build rules and check compatibility
        rules = build_default_rules()
        index = index_rules(rules)

        key = (ChangeType.MODIFY_FUNCTION, ChangeType.MODIFY_FUNCTION)
        if key in index:
            rule = index[key]
            assert rule.compatible is False
            assert rule.strategy == MergeStrategy.AI_REQUIRED
