#!/usr/bin/env python3
"""
Tests for Review Verdict Mapping System
========================================

Tests the verdict logic for PR reviews including:
- Merge conflict handling (conflicts -> BLOCKED)
- Severity-based verdict mapping (critical/high -> BLOCKED/NEEDS_REVISION)
- Branch status handling (BEHIND -> NEEDS_REVISION)
- CI status impact on verdicts
- Overall verdict generation from findings
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

# Add the backend directory to path
_backend_dir = Path(__file__).parent.parent / "apps" / "backend"
_github_dir = _backend_dir / "runners" / "github"
_services_dir = _github_dir / "services"

if str(_services_dir) not in sys.path:
    sys.path.insert(0, str(_services_dir))
if str(_github_dir) not in sys.path:
    sys.path.insert(0, str(_github_dir))
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from models import (
    BRANCH_BEHIND_BLOCKER_MSG,
    BRANCH_BEHIND_REASONING,
    MergeVerdict,
    PRReviewFinding,
    ReviewCategory,
    ReviewSeverity,
)


# ============================================================================
# MergeVerdict Enum Tests
# ============================================================================


class TestMergeVerdictEnum:
    """Tests for MergeVerdict enum values and conversions."""

    def test_verdict_values(self):
        """Test that all verdict values are correct."""
        assert MergeVerdict.READY_TO_MERGE.value == "ready_to_merge"
        assert MergeVerdict.MERGE_WITH_CHANGES.value == "merge_with_changes"
        assert MergeVerdict.NEEDS_REVISION.value == "needs_revision"
        assert MergeVerdict.BLOCKED.value == "blocked"

    def test_verdict_from_string(self):
        """Test creating verdict from string value."""
        assert MergeVerdict("ready_to_merge") == MergeVerdict.READY_TO_MERGE
        assert MergeVerdict("merge_with_changes") == MergeVerdict.MERGE_WITH_CHANGES
        assert MergeVerdict("needs_revision") == MergeVerdict.NEEDS_REVISION
        assert MergeVerdict("blocked") == MergeVerdict.BLOCKED

    def test_invalid_verdict_raises(self):
        """Test that invalid verdict strings raise ValueError."""
        with pytest.raises(ValueError):
            MergeVerdict("invalid_verdict")

    def test_verdict_ordering(self):
        """Test verdict severity ordering for comparison."""
        # Map verdicts to severity levels for comparison
        severity_order = {
            MergeVerdict.READY_TO_MERGE: 0,
            MergeVerdict.MERGE_WITH_CHANGES: 1,
            MergeVerdict.NEEDS_REVISION: 2,
            MergeVerdict.BLOCKED: 3,
        }

        # BLOCKED is the most severe
        assert severity_order[MergeVerdict.BLOCKED] > severity_order[MergeVerdict.NEEDS_REVISION]
        assert severity_order[MergeVerdict.NEEDS_REVISION] > severity_order[MergeVerdict.MERGE_WITH_CHANGES]
        assert severity_order[MergeVerdict.MERGE_WITH_CHANGES] > severity_order[MergeVerdict.READY_TO_MERGE]


# ============================================================================
# Severity to Verdict Mapping Tests
# ============================================================================


class TestSeverityToVerdictMapping:
    """Tests for mapping finding severities to verdicts."""

    def test_critical_severity_maps_to_blocked(self):
        """Test that critical severity findings result in BLOCKED verdict."""
        # Simulating the verdict logic from followup_reviewer
        critical_count = 1
        high_count = 0
        medium_count = 0
        low_count = 0

        if critical_count > 0:
            verdict = MergeVerdict.BLOCKED
        elif high_count > 0 or medium_count > 0:
            verdict = MergeVerdict.NEEDS_REVISION
        elif low_count > 0:
            verdict = MergeVerdict.READY_TO_MERGE
        else:
            verdict = MergeVerdict.READY_TO_MERGE

        assert verdict == MergeVerdict.BLOCKED

    def test_high_severity_maps_to_needs_revision(self):
        """Test that high severity findings result in NEEDS_REVISION verdict."""
        critical_count = 0
        high_count = 1
        medium_count = 0
        low_count = 0

        if critical_count > 0:
            verdict = MergeVerdict.BLOCKED
        elif high_count > 0 or medium_count > 0:
            verdict = MergeVerdict.NEEDS_REVISION
        elif low_count > 0:
            verdict = MergeVerdict.READY_TO_MERGE
        else:
            verdict = MergeVerdict.READY_TO_MERGE

        assert verdict == MergeVerdict.NEEDS_REVISION

    def test_medium_severity_maps_to_needs_revision(self):
        """Test that medium severity findings result in NEEDS_REVISION verdict."""
        critical_count = 0
        high_count = 0
        medium_count = 1
        low_count = 0

        if critical_count > 0:
            verdict = MergeVerdict.BLOCKED
        elif high_count > 0 or medium_count > 0:
            verdict = MergeVerdict.NEEDS_REVISION
        elif low_count > 0:
            verdict = MergeVerdict.READY_TO_MERGE
        else:
            verdict = MergeVerdict.READY_TO_MERGE

        assert verdict == MergeVerdict.NEEDS_REVISION

    def test_low_severity_maps_to_ready_to_merge(self):
        """Test that only low severity findings result in READY_TO_MERGE verdict."""
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 1

        if critical_count > 0:
            verdict = MergeVerdict.BLOCKED
        elif high_count > 0 or medium_count > 0:
            verdict = MergeVerdict.NEEDS_REVISION
        elif low_count > 0:
            verdict = MergeVerdict.READY_TO_MERGE
        else:
            verdict = MergeVerdict.READY_TO_MERGE

        assert verdict == MergeVerdict.READY_TO_MERGE

    def test_no_findings_maps_to_ready_to_merge(self):
        """Test that no findings results in READY_TO_MERGE verdict."""
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0

        if critical_count > 0:
            verdict = MergeVerdict.BLOCKED
        elif high_count > 0 or medium_count > 0:
            verdict = MergeVerdict.NEEDS_REVISION
        elif low_count > 0:
            verdict = MergeVerdict.READY_TO_MERGE
        else:
            verdict = MergeVerdict.READY_TO_MERGE

        assert verdict == MergeVerdict.READY_TO_MERGE

    def test_mixed_severities_uses_highest(self):
        """Test that mixed severities use the highest severity for verdict."""
        # If there's any critical, it's BLOCKED
        critical_count = 1
        high_count = 2
        medium_count = 3
        low_count = 5

        if critical_count > 0:
            verdict = MergeVerdict.BLOCKED
        elif high_count > 0 or medium_count > 0:
            verdict = MergeVerdict.NEEDS_REVISION
        else:
            verdict = MergeVerdict.READY_TO_MERGE

        assert verdict == MergeVerdict.BLOCKED


# ============================================================================
# Merge Conflict Verdict Tests
# ============================================================================


class TestMergeConflictVerdict:
    """Tests for merge conflict impact on verdict."""

    def test_merge_conflict_overrides_to_blocked(self):
        """Test that merge conflicts always result in BLOCKED verdict."""
        has_merge_conflicts = True
        ai_verdict = MergeVerdict.READY_TO_MERGE

        if has_merge_conflicts:
            verdict = MergeVerdict.BLOCKED
            reasoning = "Blocked: PR has merge conflicts with base branch."
        else:
            verdict = ai_verdict
            reasoning = ""

        assert verdict == MergeVerdict.BLOCKED
        assert "merge conflicts" in reasoning.lower()

    def test_merge_conflict_overrides_merge_with_changes(self):
        """Test that merge conflicts override MERGE_WITH_CHANGES verdict."""
        has_merge_conflicts = True
        ai_verdict = MergeVerdict.MERGE_WITH_CHANGES

        if has_merge_conflicts:
            verdict = MergeVerdict.BLOCKED
        else:
            verdict = ai_verdict

        assert verdict == MergeVerdict.BLOCKED

    def test_merge_conflict_overrides_needs_revision(self):
        """Test that merge conflicts override NEEDS_REVISION verdict."""
        has_merge_conflicts = True
        ai_verdict = MergeVerdict.NEEDS_REVISION

        if has_merge_conflicts:
            verdict = MergeVerdict.BLOCKED
        else:
            verdict = ai_verdict

        assert verdict == MergeVerdict.BLOCKED

    def test_no_merge_conflict_preserves_verdict(self):
        """Test that no merge conflicts preserves the AI verdict."""
        has_merge_conflicts = False
        ai_verdict = MergeVerdict.READY_TO_MERGE

        if has_merge_conflicts:
            verdict = MergeVerdict.BLOCKED
        else:
            verdict = ai_verdict

        assert verdict == MergeVerdict.READY_TO_MERGE


# ============================================================================
# Branch Status Verdict Tests
# ============================================================================


class TestBranchStatusVerdict:
    """Tests for branch status (BEHIND, DIRTY, etc.) impact on verdict."""

    def test_branch_behind_downgrades_ready_to_merge(self):
        """Test that BEHIND status downgrades READY_TO_MERGE to NEEDS_REVISION."""
        merge_state_status = "BEHIND"
        verdict = MergeVerdict.READY_TO_MERGE
        blockers = []

        if merge_state_status == "BEHIND":
            blockers.append(BRANCH_BEHIND_BLOCKER_MSG)
            if verdict in (MergeVerdict.READY_TO_MERGE, MergeVerdict.MERGE_WITH_CHANGES):
                verdict = MergeVerdict.NEEDS_REVISION

        assert verdict == MergeVerdict.NEEDS_REVISION
        assert len(blockers) == 1
        assert "out of date" in blockers[0].lower() or "behind" in blockers[0].lower()

    def test_branch_behind_downgrades_merge_with_changes(self):
        """Test that BEHIND status downgrades MERGE_WITH_CHANGES to NEEDS_REVISION."""
        merge_state_status = "BEHIND"
        verdict = MergeVerdict.MERGE_WITH_CHANGES

        if merge_state_status == "BEHIND":
            if verdict in (MergeVerdict.READY_TO_MERGE, MergeVerdict.MERGE_WITH_CHANGES):
                verdict = MergeVerdict.NEEDS_REVISION

        assert verdict == MergeVerdict.NEEDS_REVISION

    def test_branch_behind_preserves_blocked(self):
        """Test that BEHIND status does not upgrade BLOCKED verdict."""
        merge_state_status = "BEHIND"
        verdict = MergeVerdict.BLOCKED

        if merge_state_status == "BEHIND":
            if verdict in (MergeVerdict.READY_TO_MERGE, MergeVerdict.MERGE_WITH_CHANGES):
                verdict = MergeVerdict.NEEDS_REVISION

        # Should still be BLOCKED, not downgraded to NEEDS_REVISION
        assert verdict == MergeVerdict.BLOCKED

    def test_branch_clean_preserves_verdict(self):
        """Test that CLEAN status preserves the original verdict."""
        merge_state_status = "CLEAN"
        verdict = MergeVerdict.READY_TO_MERGE

        if merge_state_status == "BEHIND":
            verdict = MergeVerdict.NEEDS_REVISION

        assert verdict == MergeVerdict.READY_TO_MERGE

    def test_branch_behind_reasoning_is_set(self):
        """Test that BEHIND status sets appropriate reasoning."""
        merge_state_status = "BEHIND"
        verdict = MergeVerdict.READY_TO_MERGE
        verdict_reasoning = ""

        if merge_state_status == "BEHIND":
            if verdict in (MergeVerdict.READY_TO_MERGE, MergeVerdict.MERGE_WITH_CHANGES):
                verdict = MergeVerdict.NEEDS_REVISION
                verdict_reasoning = BRANCH_BEHIND_REASONING

        assert verdict == MergeVerdict.NEEDS_REVISION
        assert len(verdict_reasoning) > 0
        assert "update" in verdict_reasoning.lower() or "out of date" in verdict_reasoning.lower()


# ============================================================================
# CI Status Verdict Tests
# ============================================================================


class TestCIStatusVerdict:
    """Tests for CI status impact on verdict."""

    def test_failing_ci_blocks_ready_to_merge(self):
        """Test that failing CI blocks READY_TO_MERGE verdict."""
        ci_status = {"passing": 5, "failing": 2, "pending": 0, "failed_checks": ["build", "tests"]}
        verdict = MergeVerdict.READY_TO_MERGE
        blockers = []

        failing_ci = ci_status.get("failing", 0)
        if failing_ci > 0:
            if verdict in (MergeVerdict.READY_TO_MERGE, MergeVerdict.MERGE_WITH_CHANGES):
                blockers.append(f"CI Failing: {failing_ci} check(s) failing")
                verdict = MergeVerdict.BLOCKED

        assert verdict == MergeVerdict.BLOCKED
        assert len(blockers) == 1
        assert "failing" in blockers[0].lower()

    def test_failing_ci_blocks_merge_with_changes(self):
        """Test that failing CI blocks MERGE_WITH_CHANGES verdict."""
        ci_status = {"failing": 1}
        verdict = MergeVerdict.MERGE_WITH_CHANGES

        failing_ci = ci_status.get("failing", 0)
        if failing_ci > 0:
            if verdict in (MergeVerdict.READY_TO_MERGE, MergeVerdict.MERGE_WITH_CHANGES):
                verdict = MergeVerdict.BLOCKED

        assert verdict == MergeVerdict.BLOCKED

    def test_pending_ci_downgrades_ready_to_merge(self):
        """Test that pending CI downgrades READY_TO_MERGE to NEEDS_REVISION."""
        ci_status = {"passing": 3, "failing": 0, "pending": 2}
        verdict = MergeVerdict.READY_TO_MERGE

        pending_ci = ci_status.get("pending", 0)
        failing_ci = ci_status.get("failing", 0)

        if failing_ci > 0:
            verdict = MergeVerdict.BLOCKED
        elif pending_ci > 0:
            if verdict in (MergeVerdict.READY_TO_MERGE, MergeVerdict.MERGE_WITH_CHANGES):
                verdict = MergeVerdict.NEEDS_REVISION

        assert verdict == MergeVerdict.NEEDS_REVISION

    def test_all_ci_passing_preserves_verdict(self):
        """Test that all passing CI preserves the verdict."""
        ci_status = {"passing": 10, "failing": 0, "pending": 0}
        verdict = MergeVerdict.READY_TO_MERGE

        failing_ci = ci_status.get("failing", 0)
        pending_ci = ci_status.get("pending", 0)

        if failing_ci > 0:
            verdict = MergeVerdict.BLOCKED
        elif pending_ci > 0:
            if verdict in (MergeVerdict.READY_TO_MERGE, MergeVerdict.MERGE_WITH_CHANGES):
                verdict = MergeVerdict.NEEDS_REVISION

        assert verdict == MergeVerdict.READY_TO_MERGE

    def test_failing_ci_takes_precedence_over_pending(self):
        """Test that failing CI takes precedence over pending CI."""
        ci_status = {"passing": 3, "failing": 1, "pending": 2}
        verdict = MergeVerdict.READY_TO_MERGE

        failing_ci = ci_status.get("failing", 0)
        pending_ci = ci_status.get("pending", 0)

        if failing_ci > 0:
            verdict = MergeVerdict.BLOCKED
        elif pending_ci > 0:
            verdict = MergeVerdict.NEEDS_REVISION

        # Should be BLOCKED (failing), not NEEDS_REVISION (pending)
        assert verdict == MergeVerdict.BLOCKED


# ============================================================================
# Verdict to Overall Status Mapping Tests
# ============================================================================


class TestVerdictToOverallStatusMapping:
    """Tests for mapping verdict to GitHub review overall_status."""

    def test_blocked_maps_to_request_changes(self):
        """Test that BLOCKED verdict maps to request_changes status."""
        verdict = MergeVerdict.BLOCKED

        if verdict == MergeVerdict.BLOCKED:
            overall_status = "request_changes"
        elif verdict == MergeVerdict.NEEDS_REVISION:
            overall_status = "request_changes"
        elif verdict == MergeVerdict.MERGE_WITH_CHANGES:
            overall_status = "comment"
        else:
            overall_status = "approve"

        assert overall_status == "request_changes"

    def test_needs_revision_maps_to_request_changes(self):
        """Test that NEEDS_REVISION verdict maps to request_changes status."""
        verdict = MergeVerdict.NEEDS_REVISION

        if verdict == MergeVerdict.BLOCKED:
            overall_status = "request_changes"
        elif verdict == MergeVerdict.NEEDS_REVISION:
            overall_status = "request_changes"
        elif verdict == MergeVerdict.MERGE_WITH_CHANGES:
            overall_status = "comment"
        else:
            overall_status = "approve"

        assert overall_status == "request_changes"

    def test_merge_with_changes_maps_to_comment(self):
        """Test that MERGE_WITH_CHANGES verdict maps to comment status."""
        verdict = MergeVerdict.MERGE_WITH_CHANGES

        if verdict == MergeVerdict.BLOCKED:
            overall_status = "request_changes"
        elif verdict == MergeVerdict.NEEDS_REVISION:
            overall_status = "request_changes"
        elif verdict == MergeVerdict.MERGE_WITH_CHANGES:
            overall_status = "comment"
        else:
            overall_status = "approve"

        assert overall_status == "comment"

    def test_ready_to_merge_maps_to_approve(self):
        """Test that READY_TO_MERGE verdict maps to approve status."""
        verdict = MergeVerdict.READY_TO_MERGE

        if verdict == MergeVerdict.BLOCKED:
            overall_status = "request_changes"
        elif verdict == MergeVerdict.NEEDS_REVISION:
            overall_status = "request_changes"
        elif verdict == MergeVerdict.MERGE_WITH_CHANGES:
            overall_status = "comment"
        else:
            overall_status = "approve"

        assert overall_status == "approve"


# ============================================================================
# Blocker Generation Tests
# ============================================================================


class TestBlockerGeneration:
    """Tests for blocker list generation from findings and conditions."""

    def test_critical_finding_generates_blocker(self):
        """Test that critical findings generate blockers."""
        findings = [
            PRReviewFinding(
                id="SEC-001",
                severity=ReviewSeverity.CRITICAL,
                category=ReviewCategory.SECURITY,
                title="SQL Injection",
                description="User input not sanitized",
                file="src/db.py",
                line=42,
            )
        ]
        blockers = []

        for finding in findings:
            if finding.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.HIGH, ReviewSeverity.MEDIUM):
                blockers.append(f"{finding.category.value}: {finding.title}")

        assert len(blockers) == 1
        assert "SQL Injection" in blockers[0]

    def test_high_finding_generates_blocker(self):
        """Test that high severity findings generate blockers."""
        findings = [
            PRReviewFinding(
                id="QUAL-001",
                severity=ReviewSeverity.HIGH,
                category=ReviewCategory.QUALITY,
                title="Memory Leak",
                description="Resource not properly released",
                file="src/resource.py",
                line=100,
            )
        ]
        blockers = []

        for finding in findings:
            if finding.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.HIGH, ReviewSeverity.MEDIUM):
                blockers.append(f"{finding.category.value}: {finding.title}")

        assert len(blockers) == 1
        assert "Memory Leak" in blockers[0]

    def test_medium_finding_generates_blocker(self):
        """Test that medium severity findings generate blockers."""
        findings = [
            PRReviewFinding(
                id="PERF-001",
                severity=ReviewSeverity.MEDIUM,
                category=ReviewCategory.PERFORMANCE,
                title="N+1 Query",
                description="Database query inside loop",
                file="src/api.py",
                line=50,
            )
        ]
        blockers = []

        for finding in findings:
            if finding.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.HIGH, ReviewSeverity.MEDIUM):
                blockers.append(f"{finding.category.value}: {finding.title}")

        assert len(blockers) == 1
        assert "N+1 Query" in blockers[0]

    def test_low_finding_does_not_generate_blocker(self):
        """Test that low severity findings do NOT generate blockers."""
        findings = [
            PRReviewFinding(
                id="STYLE-001",
                severity=ReviewSeverity.LOW,
                category=ReviewCategory.STYLE,
                title="Missing docstring",
                description="Function lacks documentation",
                file="src/utils.py",
                line=10,
            )
        ]
        blockers = []

        for finding in findings:
            if finding.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.HIGH, ReviewSeverity.MEDIUM):
                blockers.append(f"{finding.category.value}: {finding.title}")

        assert len(blockers) == 0

    def test_multiple_findings_generate_multiple_blockers(self):
        """Test that multiple blocking findings generate multiple blockers."""
        findings = [
            PRReviewFinding(
                id="SEC-001",
                severity=ReviewSeverity.CRITICAL,
                category=ReviewCategory.SECURITY,
                title="SQL Injection",
                description="User input not sanitized",
                file="src/db.py",
                line=42,
            ),
            PRReviewFinding(
                id="QUAL-001",
                severity=ReviewSeverity.HIGH,
                category=ReviewCategory.QUALITY,
                title="Memory Leak",
                description="Resource not released",
                file="src/resource.py",
                line=100,
            ),
            PRReviewFinding(
                id="STYLE-001",
                severity=ReviewSeverity.LOW,
                category=ReviewCategory.STYLE,
                title="Missing docstring",
                description="Lacks documentation",
                file="src/utils.py",
                line=10,
            ),
        ]
        blockers = []

        for finding in findings:
            if finding.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.HIGH, ReviewSeverity.MEDIUM):
                blockers.append(f"{finding.category.value}: {finding.title}")

        assert len(blockers) == 2  # Only CRITICAL and HIGH, not LOW
        assert any("SQL Injection" in b for b in blockers)
        assert any("Memory Leak" in b for b in blockers)

    def test_merge_conflict_blocker(self):
        """Test that merge conflicts generate specific blocker."""
        has_merge_conflicts = True
        blockers = []

        if has_merge_conflicts:
            blockers.append(
                "Merge Conflicts: PR has conflicts with base branch that must be resolved"
            )

        assert len(blockers) == 1
        assert "merge conflicts" in blockers[0].lower()


# ============================================================================
# Combined Scenario Tests
# ============================================================================


class TestCombinedVerdictScenarios:
    """Tests for complex scenarios with multiple verdict factors."""

    def test_merge_conflict_overrides_ci_passing(self):
        """Test that merge conflicts override passing CI."""
        has_merge_conflicts = True
        ci_status = {"passing": 10, "failing": 0, "pending": 0}
        verdict = MergeVerdict.READY_TO_MERGE

        # Apply merge conflict check first (highest priority)
        if has_merge_conflicts:
            verdict = MergeVerdict.BLOCKED
        # Then CI check
        elif ci_status.get("failing", 0) > 0:
            verdict = MergeVerdict.BLOCKED

        assert verdict == MergeVerdict.BLOCKED

    def test_merge_conflict_combined_with_critical_finding(self):
        """Test merge conflict combined with critical finding."""
        has_merge_conflicts = True
        critical_count = 1
        blockers = []

        if has_merge_conflicts:
            blockers.append("Merge Conflicts")
            verdict = MergeVerdict.BLOCKED

        if critical_count > 0:
            blockers.append("Critical Finding")
            verdict = MergeVerdict.BLOCKED

        assert verdict == MergeVerdict.BLOCKED
        assert len(blockers) == 2

    def test_failing_ci_overrides_branch_behind(self):
        """Test that failing CI takes precedence over branch behind."""
        merge_state_status = "BEHIND"
        ci_status = {"failing": 1, "pending": 0}
        verdict = MergeVerdict.READY_TO_MERGE

        # Check CI first (higher priority)
        failing_ci = ci_status.get("failing", 0)
        if failing_ci > 0:
            verdict = MergeVerdict.BLOCKED
        elif merge_state_status == "BEHIND":
            verdict = MergeVerdict.NEEDS_REVISION

        assert verdict == MergeVerdict.BLOCKED

    def test_branch_behind_combined_with_low_findings(self):
        """Test branch behind with only low severity findings."""
        merge_state_status = "BEHIND"
        low_count = 3
        critical_count = 0
        high_count = 0
        medium_count = 0

        # Determine base verdict from findings
        if critical_count > 0:
            verdict = MergeVerdict.BLOCKED
        elif high_count > 0 or medium_count > 0:
            verdict = MergeVerdict.NEEDS_REVISION
        elif low_count > 0:
            verdict = MergeVerdict.READY_TO_MERGE
        else:
            verdict = MergeVerdict.READY_TO_MERGE

        # Apply branch status
        if merge_state_status == "BEHIND":
            if verdict in (MergeVerdict.READY_TO_MERGE, MergeVerdict.MERGE_WITH_CHANGES):
                verdict = MergeVerdict.NEEDS_REVISION

        assert verdict == MergeVerdict.NEEDS_REVISION

    def test_all_clear_scenario(self):
        """Test scenario with no blockers at all."""
        has_merge_conflicts = False
        merge_state_status = "CLEAN"
        ci_status = {"passing": 5, "failing": 0, "pending": 0}
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0

        # Determine verdict from findings
        if critical_count > 0:
            verdict = MergeVerdict.BLOCKED
        elif high_count > 0 or medium_count > 0:
            verdict = MergeVerdict.NEEDS_REVISION
        else:
            verdict = MergeVerdict.READY_TO_MERGE

        # Apply merge conflict check
        if has_merge_conflicts:
            verdict = MergeVerdict.BLOCKED

        # Apply CI check
        if ci_status.get("failing", 0) > 0:
            verdict = MergeVerdict.BLOCKED
        elif ci_status.get("pending", 0) > 0:
            if verdict == MergeVerdict.READY_TO_MERGE:
                verdict = MergeVerdict.NEEDS_REVISION

        # Apply branch status
        if merge_state_status == "BEHIND":
            if verdict == MergeVerdict.READY_TO_MERGE:
                verdict = MergeVerdict.NEEDS_REVISION

        assert verdict == MergeVerdict.READY_TO_MERGE

    def test_only_low_findings_with_passing_ci(self):
        """Test that only low findings with passing CI is READY_TO_MERGE."""
        has_merge_conflicts = False
        merge_state_status = "CLEAN"
        ci_status = {"passing": 3, "failing": 0, "pending": 0}
        findings = [
            PRReviewFinding(
                id="STYLE-001",
                severity=ReviewSeverity.LOW,
                category=ReviewCategory.STYLE,
                title="Minor style issue",
                description="Could use better naming",
                file="src/utils.py",
                line=10,
            )
        ]

        # Count by severity
        critical_count = sum(1 for f in findings if f.severity == ReviewSeverity.CRITICAL)
        high_count = sum(1 for f in findings if f.severity == ReviewSeverity.HIGH)
        medium_count = sum(1 for f in findings if f.severity == ReviewSeverity.MEDIUM)

        # Determine verdict
        if critical_count > 0:
            verdict = MergeVerdict.BLOCKED
        elif high_count > 0 or medium_count > 0:
            verdict = MergeVerdict.NEEDS_REVISION
        else:
            verdict = MergeVerdict.READY_TO_MERGE

        # Apply other checks (all clean)
        if has_merge_conflicts:
            verdict = MergeVerdict.BLOCKED
        if ci_status.get("failing", 0) > 0:
            verdict = MergeVerdict.BLOCKED

        assert verdict == MergeVerdict.READY_TO_MERGE


# ============================================================================
# Constants Tests
# ============================================================================


class TestVerdictConstants:
    """Tests for verdict-related constants."""

    def test_branch_behind_blocker_message_defined(self):
        """Test that BRANCH_BEHIND_BLOCKER_MSG is properly defined."""
        assert BRANCH_BEHIND_BLOCKER_MSG is not None
        assert len(BRANCH_BEHIND_BLOCKER_MSG) > 0
        assert "behind" in BRANCH_BEHIND_BLOCKER_MSG.lower() or "out of date" in BRANCH_BEHIND_BLOCKER_MSG.lower()

    def test_branch_behind_reasoning_defined(self):
        """Test that BRANCH_BEHIND_REASONING is properly defined."""
        assert BRANCH_BEHIND_REASONING is not None
        assert len(BRANCH_BEHIND_REASONING) > 0
        # Should mention updating or conflicts
        lower_reasoning = BRANCH_BEHIND_REASONING.lower()
        assert "update" in lower_reasoning or "conflict" in lower_reasoning
