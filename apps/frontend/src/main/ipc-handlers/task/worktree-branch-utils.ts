/**
 * Pure utility functions for worktree branch validation.
 * This file contains no Electron imports and can be safely tested in unit tests.
 */

// Regex pattern for validating git branch names
export const GIT_BRANCH_REGEX = /^[a-zA-Z0-9][a-zA-Z0-9._/-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$/;

/**
 * Validates a detected branch name and returns the safe branch to delete.
 *
 * Why `auto-claude/` prefix is considered safe:
 * - All task worktrees use branches named `auto-claude/{specId}`
 * - This pattern is controlled by Auto-Claude, not user input
 * - If detected branch matches this pattern, it's a valid task branch
 * - If it doesn't match (e.g., `main`, `develop`, `feature/xxx`), it's likely
 *   the main project's branch being incorrectly detected from a corrupted worktree
 *
 * Issue #1479: When cleaning up a corrupted worktree, git rev-parse walks up
 * to the main project and returns its current branch instead of the worktree's branch.
 * This could cause deletion of the wrong branch.
 */
export function validateWorktreeBranch(
  detectedBranch: string | null,
  expectedBranch: string
): { branchToDelete: string; usedFallback: boolean; reason: string } {
  // If detection failed, use expected pattern
  if (detectedBranch === null) {
    return {
      branchToDelete: expectedBranch,
      usedFallback: true,
      reason: 'detection_failed',
    };
  }

  // Exact match - ideal case
  if (detectedBranch === expectedBranch) {
    return {
      branchToDelete: detectedBranch,
      usedFallback: false,
      reason: 'exact_match',
    };
  }

  // Matches auto-claude pattern with valid specId (not just "auto-claude/")
  // The specId must be non-empty for this to be a valid task branch
  if (detectedBranch.startsWith('auto-claude/') && detectedBranch.length > 'auto-claude/'.length) {
    return {
      branchToDelete: detectedBranch,
      usedFallback: false,
      reason: 'pattern_match',
    };
  }

  // Detected branch doesn't match expected pattern - use fallback
  // This is the critical security fix for issue #1479
  return {
    branchToDelete: expectedBranch,
    usedFallback: true,
    reason: 'invalid_pattern',
  };
}
